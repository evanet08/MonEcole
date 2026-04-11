
from django.http import HttpResponse
from django.contrib import messages
from django.utils.text import slugify
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, PageBreak
from io import BytesIO
from MonEcole_app.views.rdc_structure import *
from MonEcole_app.models.campus import Campus
from functools import wraps

# module_required decorator
try:
    from MonEcole_app.views.decorators.decorators import module_required
except ImportError:
    def module_required(module_name):
        def decorator(view_func):
            return view_func
        return decorator


def login_required(view_func):
    """Session-based login check (non-parameterized for @login_required usage)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('personnel_id'):
            return redirect('/login/')
        return view_func(request, *args, **kwargs)
    return wrapper

@csrf_exempt
@login_required
@module_required("Evaluation")
def generer_bulletin_pdf(request):
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        id_annee  = request.POST.get('id_annee')
        idCampus = request.POST.get('idCampus')
        id_cycle  = request.POST.get('id_cycle')
        id_classe = request.POST.get('id_classe')
        id_eleves = request.POST.getlist('id_eleve')
    else:
        id_annee  = request.GET.get('id_annee')
        idCampus = request.GET.get('idCampus')
        id_cycle  = request.GET.get('id_cycle')
        id_classe = request.GET.get('id_classe')
        # Support comma-separated IDs: ?id_eleve=2,3,5
        raw_eleves = request.GET.get('id_eleve', '')
        id_eleves = [e.strip() for e in raw_eleves.split(',') if e.strip()]

    logger.warning(f"[BULLETIN PDF] Initial params: annee={id_annee}, campus={idCampus}, cycle={id_cycle}, classe={id_classe}, eleves={id_eleves[:3]}...")

    # Auto-résolution des paramètres manquants via EAC
    if id_classe and (not id_annee or not idCampus or not id_cycle):
        try:
            from MonEcole_app.models.country_structure import EtablissementAnneeClasse
            eac = EtablissementAnneeClasse.objects.select_related(
                'etablissement_annee', 'etablissement_annee__annee', 'classe', 'classe__cycle'
            ).get(id=int(id_classe))
            logger.warning(f"[BULLETIN PDF] EAC found: {eac}, etab_annee={eac.etablissement_annee}, classe={eac.classe}")
            if not id_annee:
                id_annee = str(eac.etablissement_annee.annee_id)
            if not id_cycle and eac.classe and eac.classe.cycle:
                id_cycle = str(eac.classe.cycle_id)
            if not idCampus:
                etab_id = eac.etablissement_annee.etablissement_id
                campus = Campus.objects.filter(id_etablissement=etab_id).first()
                idCampus = str(campus.idCampus) if campus else '1'
            # Extract business keys for inscription filtering
            bk_classe_id = eac.classe_id
            bk_groupe = eac.groupe
            bk_section_id = eac.section_id
            logger.warning(f"[BULLETIN PDF] After auto-resolve: annee={id_annee}, campus={idCampus}, cycle={id_cycle}, bk_classe={bk_classe_id}, bk_groupe={bk_groupe}, bk_section={bk_section_id}")
        except Exception as e:
            logger.error(f"[BULLETIN PDF] Auto-resolve FAILED: {e}")

    if not all([id_annee, idCampus, id_cycle, id_classe]) or not id_eleves or not id_eleves[0]:
        logger.error(f"[BULLETIN PDF] MISSING PARAMS: annee={id_annee}, campus={idCampus}, cycle={id_cycle}, classe={id_classe}, eleves={id_eleves}")
        messages.error(request, "Paramètres manquants ou invalides.")
        return HttpResponse('<script>window.location.href="/dashboard/evaluations/?section=bulletins";</script>')

    try:
        id_annee  = int(id_annee)
        idCampus = int(idCampus)
        id_cycle  = int(id_cycle)
        id_classe = int(id_classe)
        id_eleves = [int(e) for e in id_eleves if e and str(e).isdigit()]
    except ValueError:
        messages.error(request, "Paramètres numériques invalides.")
        return HttpResponse('<script>history.back();</script>', status=400)

    if not id_eleves:
        messages.error(request, "Aucun élève sélectionné.")
        return HttpResponse('<script>history.back();</script>', status=400)

    # Resolve EAC → business keys (if not already done above)
    if 'bk_classe_id' not in locals():
        try:
            from MonEcole_app.models.country_structure import EtablissementAnneeClasse as _EAC
            _eac = _EAC.objects.get(id=id_classe)
            bk_classe_id = _eac.classe_id
            bk_groupe = _eac.groupe
            bk_section_id = _eac.section_id
        except Exception:
            bk_classe_id = id_classe
            bk_groupe = None
            bk_section_id = None

    # Trier les élèves par classement (1er → dernier)
    # Cascade: annuelle → trimestrielle → periodique
    try:
        from MonEcole_app.models.evaluations.note import (
            Deliberation_annuelle_resultat,
            Deliberation_trimistrielle_resultat,
            Deliberation_periodique_resultat,
        )
        import re
        rank_map = {}

        base_filter = {
            'id_classe_id': bk_classe_id,
            'groupe': bk_groupe,
            'section_id': bk_section_id,
            'id_eleve_id__in': id_eleves,
        }

        # Trouver la délibération la plus AVANCÉE structurellement
        # Ordre : P1 < P2 < S1/T1 < P3 < P4 < S2/T2 < P5 < P6 < S3/T3 < Annuel
        # La 1e période du trimestre suivant > tout ce qui concerne le précédent
        CODE_POSITION = {
            'P1': 1, 'P2': 2,
            'S1': 5, 'T1': 5,
            'P3': 6, 'P4': 7,
            'S2': 10, 'T2': 10,
            'P5': 11, 'P6': 12,
            'S3': 15, 'T3': 15,
        }
        ANNUAL_POSITION = 100

        # Résoudre config_id → code via le Hub
        from django.db import connections
        config_to_code = {}
        try:
            eac_obj = None
            from MonEcole_app.models.country_structure import EtablissementAnneeClasse as _EAC2
            eac_obj = _EAC2.objects.get(id=id_classe)
            with connections['countryStructure'].cursor() as cur:
                cur.execute("""
                    SELECT rc.id, ri.code
                    FROM repartition_configs_etab_annee rc
                    JOIN repartition_instances ri ON ri.id_instance = rc.repartition_id
                    WHERE rc.etablissement_annee_id = %s
                """, [eac_obj.etablissement_annee_id])
                for row in cur.fetchall():
                    config_to_code[row[0]] = row[1]
        except Exception as e:
            logger.warning(f"[BULLETIN PDF] Could not resolve config codes: {e}")

        candidates = []  # (position, type, ref_id, model)

        # Annuelle
        if Deliberation_annuelle_resultat.objects.filter(**base_filter).exists():
            candidates.append((ANNUAL_POSITION, 'annuelle', None, Deliberation_annuelle_resultat))

        # Trimestrielle — chaque trimestre délibéré
        for trim_delib in Deliberation_trimistrielle_resultat.objects.filter(
            **base_filter
        ).values('id_trimestre_id').distinct():
            trim_id = trim_delib['id_trimestre_id']
            code = config_to_code.get(trim_id, '')
            pos = CODE_POSITION.get(code, 0)
            if pos:
                candidates.append((pos, 'trimestrielle', trim_id, Deliberation_trimistrielle_resultat))

        # Périodique — chaque période délibérée
        for per_delib in Deliberation_periodique_resultat.objects.filter(
            **base_filter
        ).values('id_periode_id').distinct():
            per_id = per_delib['id_periode_id']
            code = config_to_code.get(per_id, '')
            pos = CODE_POSITION.get(code, 0)
            if pos:
                candidates.append((pos, 'periodique', per_id, Deliberation_periodique_resultat))

        if candidates:
            # Prendre la plus avancée structurellement
            candidates.sort(key=lambda x: x[0], reverse=True)
            winner_pos, winner_type, winner_ref, winner_model = candidates[0]
            winner_code = config_to_code.get(winner_ref, 'Annual') if winner_ref else 'Annual'
            logger.warning(f"[BULLETIN PDF] Most advanced deliberation: type={winner_type}, code={winner_code}, pos={winner_pos}")

            if winner_type == 'annuelle':
                qs = winner_model.objects.filter(**base_filter)
            elif winner_type == 'trimestrielle':
                qs = winner_model.objects.filter(id_trimestre_id=winner_ref, **base_filter)
            else:  # periodique
                qs = winner_model.objects.filter(id_periode_id=winner_ref, **base_filter)

            for eleve_id, place in qs.values_list('id_eleve_id', 'place'):
                match = re.search(r'(\d+)', place or '')
                if match:
                    rank_map[eleve_id] = int(match.group(1))

        # Sort: ranked students first (by rank), then unranked
        id_eleves.sort(key=lambda eid: rank_map.get(eid, 99999))
        logger.warning(f"[BULLETIN PDF] Sorted by rank ({len(rank_map)} ranked): {[(eid, rank_map.get(eid, '?')) for eid in id_eleves[:5]]}...")
    except Exception as e:
        logger.warning(f"[BULLETIN PDF] Could not sort by rank: {e}")

    logger.warning(f"[BULLETIN PDF] Resolved params OK: annee={id_annee}, campus={idCampus}, cycle={id_cycle}, classe={id_classe}, eleves_count={len(id_eleves)}")

    # ───────────────────────────────────────────────
    # Déterminer la localisation
    # ───────────────────────────────────────────────
    try:
        campus = Campus.objects.get(idCampus=idCampus)
        localisation = campus.localisation.strip().upper()
    except Campus.DoesNotExist:
        logger.error(f"[BULLETIN PDF] Campus NOT FOUND: idCampus={idCampus}")
        messages.error(request, "Campus introuvable.")
        return HttpResponse('<script>history.back();</script>', status=404)

    buffer = BytesIO()
    filename_parts = []
    elements = []

    styles, style_normal, style_center, style_title, style_right = get_styles()

    # ───────────────────────────────────────────────
    # CAS BDI
    # ───────────────────────────────────────────────
    if localisation == "BDI":
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=20, leftMargin=20,
            topMargin=20, bottomMargin=20,
        )

        for idx, id_eleve in enumerate(id_eleves):
            try:
                eleve = Eleve.objects.get(id_eleve=id_eleve)
                inscription = Eleve_inscription.objects.filter(
                    id_eleve=id_eleve,
                    id_annee=id_annee,
                    idCampus=idCampus,
                    id_cycle=id_cycle,
                    id_classe_id=bk_classe_id,
                    groupe=bk_groupe,
                    section_id=bk_section_id,
                    status=1
                ).first()

                if not inscription:
                    continue

                if idx > 0:
                    elements.append(PageBreak())
                elements.extend(create_header_elements())
                student_info, nom_eleve = create_student_info_tables(
                    id_eleve, id_annee, idCampus, id_cycle, id_classe
                )
                elements.extend(student_info)

                results_table, total_pct = create_results_table(
                    id_eleve, id_annee, idCampus, id_cycle, id_classe
                )
                elements.extend(results_table)

                elements.extend(create_signature_table())
                elements.append(PageBreak())

                elements.extend(create_back_page(
                    id_annee, idCampus, id_cycle, id_eleve, id_classe, total_pct
                ))

                filename_parts.append(slugify(nom_eleve))

            except Exception as e:
                logger.exception(f"Erreur bulletin BDI élève {id_eleve}")
                continue

        if not elements:
            messages.error(request, "Aucun bulletin valide généré pour BDI.")
            return HttpResponse('<script>history.back();</script>', status=400)

        doc.build(elements, onFirstPage=page_template, onLaterPages=page_template)

    # ───────────────────────────────────────────────
    # CAS RDC
    # ───────────────────────────────────────────────
    else:
        # ─── Récupérer le modèle de bulletin via BulletinClasseModel ───
        from MonEcole_app.models.evaluations.bulletin_model import BulletinClasseModel
        from MonEcole_app.models.country_structure import EtablissementAnneeClasse

        try:
            eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
            classe_name = eac.classe.classe.strip()
            hub_classe_id = eac.classe_id  # ID de la classe dans le catalogue Hub
        except EtablissementAnneeClasse.DoesNotExist:
            messages.error(request, "Classe introuvable.")
            return HttpResponse('<script>history.back();</script>', status=404)

        # Chercher l'association bulletin/classe via l'ID Hub de la classe
        bcm = BulletinClasseModel.objects.filter(
            id_classe_id=hub_classe_id
        ).select_related('id_model').first()

        if not bcm:
            messages.error(request, f"Aucun modèle de bulletin associé à la classe : {classe_name}")
            return HttpResponse('<script>history.back();</script>', status=400)

        model_name = bcm.id_model.model_name.strip()
        code_model = (bcm.id_model.code_model or '').strip()
        code_lower = code_model.lower()
        margin = 5 * mm

        # Déterminer le cycle par code_model (Hub: bulletin_model.code_model)
        cycle_model = ''

        if code_lower:
            if 'maternelle' in code_lower:
                cycle_model = 'Maternel'
            elif 'primaire' in code_lower:
                cycle_model = 'Primaire'
            elif 'education de base' in code_lower or 'ecole de base' in code_lower:
                cycle_model = 'Ecole de Base'
            elif 'humanit' in code_lower or 'cfp' in code_lower:
                cycle_model = 'Humanités/CFP'
        
        if not cycle_model:
            # Fallback sur model_name si code_model vide
            mn_lower = model_name.lower()
            if 'maternelle' in mn_lower:
                cycle_model = 'Maternel'
            elif 'primaire' in mn_lower:
                cycle_model = 'Primaire'
            elif 'education de base' in mn_lower or 'ecole de base' in mn_lower:
                cycle_model = 'Ecole de Base'
            elif 'humanit' in mn_lower or 'cfp' in mn_lower:
                cycle_model = 'Humanités/CFP'

        # ─── Dispatch selon le cycle du modèle ───
        if cycle_model == 'Maternel':
            # Structure maternelle
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=margin,
                bottomMargin=margin,
                leftMargin=margin,
                rightMargin=margin
            )

            for idx, id_eleve in enumerate(id_eleves):
                try:
                    eleve = Eleve.objects.get(id_eleve=id_eleve)
                    if idx > 0:
                        elements.append(PageBreak())

                    elements.append(Spacer(1, 3*mm))
                    institution = Institution.objects.get(id_ecole=idCampus)
                    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                    check_image_paths(logo_path, emblem_path)

                    create_header(elements, logo_path, emblem_path, style_title, style_center, eleve=eleve)
                    create_nid_section(elements, style_normal)
                    left_table = create_line2_left(elements, style_normal, id_campus=idCampus)
                    right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
                    create_line2_section__secondaire_rdc(elements, left_table, right_table)
                    create_bulletin_title__secondaire_superieur(elements, style_title, style_right, id_classe=id_classe, id_annee=id_annee)
                    create_bulletin_maternelle(
                        elements, style_normal, style_center, style_title,
                        id_annee, idCampus, id_cycle, id_classe, id_eleve
                    )

                    filename_parts.append(slugify(eleve.nom or f"eleve_{id_eleve}"))
                except Exception as e:
                    logger.exception(f"Erreur bulletin maternelle élève {id_eleve}")
                    continue

        elif cycle_model == 'Primaire':
            # Structure primaire (toutes les classes du cycle Primaire)
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=0,
                bottomMargin=5*mm,
                leftMargin=5*mm,
                rightMargin=5*mm
            )

            for idx, id_eleve in enumerate(id_eleves):
                try:
                    eleve = Eleve.objects.get(id_eleve=id_eleve)
                    if idx > 0:
                        elements.append(PageBreak())

                    elements.append(Spacer(1, 3*mm))
                    institution = Institution.objects.get(id_ecole=idCampus)
                    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                    check_image_paths(logo_path, emblem_path)

                    create_header(elements, logo_path, emblem_path, style_title, style_center, eleve=eleve)
                    create_nid_section(elements, style_normal, eleve=eleve, id_campus=idCampus)
                    left_table = create_line2_left(elements, style_normal, id_campus=idCampus)
                    right_table = create_line2_right(elements, eleve, style_normal, id_classe)
                    create_line2_section(elements, left_table, right_table)
                    create_bulletin_title(elements, style_title, id_annee, id_classe)
                    create_notes_table(
                        elements, style_center, style_normal,
                        id_annee, idCampus, id_cycle, id_classe, id_eleve
                    )
                    create_footer(elements, style_normal, style_center, id_classe=id_classe)

                    filename_parts.append(slugify(eleve.nom or f"eleve_{id_eleve}"))
                except Exception as e:
                    logger.exception(f"Erreur bulletin primaire élève {id_eleve}")
                    continue

        elif cycle_model == 'Ecole de Base':
            # Structure école de base (toutes les classes du cycle Ecole de Base)
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                topMargin=0,
                bottomMargin=5*mm,
                leftMargin=5*mm,
                rightMargin=5*mm
            )

            # Fetch logos from Pays table via Campus → Etablissement → Pays
            logo_path = None
            emblem_path = None
            try:
                from MonEcole_app.models.country_structure import Etablissement, Pays
                campus_obj = Campus.objects.get(idCampus=idCampus)
                etab = Etablissement.objects.select_related('pays').get(
                    id_etablissement=campus_obj.id_etablissement
                )
                pays = etab.pays
                media_root = getattr(settings, 'MEDIA_ROOT', '')
                if not media_root:
                    import os
                    media_root = os.path.join(settings.BASE_DIR, 'media')
                if pays.logo_pays:
                    lp = os.path.join(media_root, pays.logo_pays)
                    if os.path.exists(lp):
                        logo_path = lp
                if pays.logo_ministere:
                    ep = os.path.join(media_root, pays.logo_ministere)
                    if os.path.exists(ep):
                        emblem_path = ep
            except Exception as e:
                logger.warning(f"[BULLETIN PDF] Could not fetch Pays logos: {e}")

            for idx, id_eleve in enumerate(id_eleves):
                try:
                    eleve = Eleve.objects.get(id_eleve=id_eleve)
                    if idx > 0:
                        elements.append(PageBreak())

                    elements.append(Spacer(1, 3*mm))

                    create_header(elements, logo_path, emblem_path, style_title, style_center, eleve=eleve)
                    create_nid_section(elements, style_normal, eleve=eleve, id_campus=idCampus)
                    left_table = create_line2_left(elements, style_normal, id_campus=idCampus)
                    right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
                    create_line2_section__secondaire_rdc(elements, left_table, right_table)
                    create_bulletin_title__secondaire_rdc(elements, style_title, style_right, id_annee, id_classe)
                    create_notes_table__secondaire_rdc(
                        elements, style_center, style_normal,
                        id_annee, idCampus, id_cycle, id_classe, id_eleve
                    )
                    # Footer: 8ème année utilise un pied spécifique avec RESULTAT FINAL
                    # Détection via code_model (Hub: bulletin_model)
                    if '8eme' in code_lower or '8ème' in code_lower:
                        create_footer_8eme(elements, style_normal, style_center, id_classe=id_classe)
                    else:
                        create_footer__secondaire_rdc(elements, style_normal, style_center, id_classe)

                    filename_parts.append(slugify(eleve.nom or f"eleve_{id_eleve}"))
                except Exception as e:
                    logger.exception(f"Erreur bulletin école de base élève {id_eleve}")
                    continue

        elif cycle_model == 'Humanités/CFP':
            # Structure Humanités/CFP
            # Si classe commence par "4" → structure supérieur (4ème construction)
            # Sinon (1, 2, 3...) → structure cycle supérieur (semestres)
            if classe_name.startswith('4'):
                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=A4,
                    topMargin=0,
                    bottomMargin=5*mm,
                    leftMargin=5*mm,
                    rightMargin=5*mm
                )

                for idx, id_eleve in enumerate(id_eleves):
                    try:
                        eleve = Eleve.objects.get(id_eleve=id_eleve)
                        if idx > 0:
                            elements.append(PageBreak())

                        elements.append(Spacer(1, 3*mm))
                        institution = Institution.objects.get(id_ecole=idCampus)
                        logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                        emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                        check_image_paths(logo_path, emblem_path)

                        create_header(elements, logo_path, emblem_path, style_title, style_center, eleve=eleve)
                        create_nid_section(elements, style_normal, eleve=eleve, id_campus=idCampus)
                        left_table = create_line2_left(elements, style_normal, id_campus=idCampus)
                        right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
                        create_line2_section__secondaire_rdc(elements, left_table, right_table)
                        create_bulletin_title__secondaire_superieur(elements, style_title, style_right, id_classe=id_classe, id_annee=id_annee)
                        create_notes_table_superieur(
                            elements, style_center, style_normal,
                            id_annee, idCampus, id_cycle, id_classe, id_eleve
                        )
                        create_footer__secondaire_rdc(elements, style_normal, style_center, id_classe)

                        filename_parts.append(slugify(eleve.nom or f"eleve_{id_eleve}"))
                    except Exception as e:
                        logger.exception(f"Erreur bulletin Humanités/CFP 4ème élève {id_eleve}")
                        continue
            else:
                # Classes 1er, 2ème, 3ème du cycle Humanités/CFP
                doc = SimpleDocTemplate(
                    buffer,
                    pagesize=A4,
                    topMargin=margin,
                    bottomMargin=margin,
                    leftMargin=margin,
                    rightMargin=margin
                )

                for idx, id_eleve in enumerate(id_eleves):
                    try:
                        eleve = Eleve.objects.get(id_eleve=id_eleve)
                        if idx > 0:
                            elements.append(PageBreak())

                        institution = Institution.objects.get(id_ecole=idCampus)
                        logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                        emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                        check_image_paths(logo_path, emblem_path)

                        create_header(elements, logo_path, emblem_path, style_title, style_center, eleve=eleve)
                        create_nid_section(elements, style_normal, eleve=eleve, id_campus=idCampus)
                        left_table = create_line2_left(elements, style_normal, id_campus=idCampus)
                        right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
                        create_line2_section__secondaire_rdc(elements, left_table, right_table)
                        create_bulletin_title__secondaire_superieur(elements, style_title, style_right, id_classe=id_classe, id_annee=id_annee)
                        create_bulletin_content_cycle_superieur(
                            elements, style_normal, style_center,
                            id_annee, idCampus, id_cycle, id_classe, id_eleve,
                            get_semestres=get_semestres
                        )

                        filename_parts.append(slugify(eleve.nom or f"eleve_{id_eleve}"))
                    except Exception as e:
                        logger.exception(f"Erreur bulletin Humanités/CFP élève {id_eleve}")
                        continue

        else:
            messages.error(request, f"Cycle modèle non pris en charge pour le modèle : {model_name}")
            return HttpResponse('<script>history.back();</script>', status=400)

        if not elements:
            messages.error(request, "Aucun bulletin valide généré pour RDC.")
            return HttpResponse('<script>history.back();</script>', status=400)

        # Fetch armoirePays watermark from Pays table
        watermark_path = None
        try:
            from MonEcole_app.models.country_structure import Etablissement, Pays
            import os as _os
            campus_obj = Campus.objects.get(idCampus=idCampus)
            etab = Etablissement.objects.select_related('pays').get(
                id_etablissement=campus_obj.id_etablissement
            )
            pays = etab.pays
            media_root = getattr(settings, 'MEDIA_ROOT', '')
            if not media_root:
                media_root = _os.path.join(settings.BASE_DIR, 'media')
            if hasattr(pays, 'armoirePays') and pays.armoirePays:
                wp = _os.path.join(media_root, pays.armoirePays)
                if _os.path.exists(wp):
                    watermark_path = wp
            # Fallback: check project root
            if not watermark_path:
                fallback_wm = _os.path.join(settings.BASE_DIR, 'armoirerdc.png')
                if _os.path.exists(fallback_wm):
                    watermark_path = fallback_wm
        except Exception as e:
            logger.warning(f"[BULLETIN PDF] Could not fetch watermark: {e}")

        def on_all_pages(canvas, doc):
            draw_border(canvas, doc, eleve, margin, watermark_path=watermark_path) 

        doc.build(elements, onFirstPage=on_all_pages, onLaterPages=on_all_pages)

    # ───────────────────────────────────────────────
    # Nom de fichier final + réponse
    # ───────────────────────────────────────────────
    if len(id_eleves) == 1 and filename_parts:
        nom_fichier = slugify(filename_parts[0])
    else:
        try:
            eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
            nom_classe = slugify(eac.classe.classe or "classe")
        except:
            nom_classe = "classe"
        nom_fichier = f"Bulletins_{localisation}_{nom_classe}_{id_annee}"

    filename = f"{nom_fichier}.pdf"

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"; filename*=UTF-8\'\'{filename}'

    buffer.close()
    return response

