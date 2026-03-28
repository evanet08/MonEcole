
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, PageBreak
from io import BytesIO
from MonEcole_app.views.rdc_structure import *

# module_required decorator
try:
    from MonEcole_app.views.decorators.decorators import module_required
except ImportError:
    def module_required(module_name):
        def decorator(view_func):
            return view_func
        return decorator

@csrf_exempt
@login_required
@module_required("Evaluation")
def generer_bulletin_pdf(request):
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        id_annee  = request.POST.get('id_annee')
        id_campus = request.POST.get('id_campus')
        id_cycle  = request.POST.get('id_cycle')
        id_classe = request.POST.get('id_classe')
        id_eleves = request.POST.getlist('id_eleve')
    else:
        id_annee  = request.GET.get('id_annee')
        id_campus = request.GET.get('id_campus')
        id_cycle  = request.GET.get('id_cycle')
        id_classe = request.GET.get('id_classe')
        # Support comma-separated IDs: ?id_eleve=2,3,5
        raw_eleves = request.GET.get('id_eleve', '')
        id_eleves = [e.strip() for e in raw_eleves.split(',') if e.strip()]

    logger.warning(f"[BULLETIN PDF] Initial params: annee={id_annee}, campus={id_campus}, cycle={id_cycle}, classe={id_classe}, eleves={id_eleves[:3]}...")

    # Auto-résolution des paramètres manquants via EAC
    if id_classe and (not id_annee or not id_campus or not id_cycle):
        try:
            from MonEcole_app.models.country_structure import (
                EtablissementAnneeClasse, EtablissementAnnee, Annee
            )
            from MonEcole_app.models.campus import Campus
            eac = EtablissementAnneeClasse.objects.select_related(
                'etablissement_annee', 'etablissement_annee__annee', 'classe', 'classe__cycle'
            ).get(id=int(id_classe))
            logger.warning(f"[BULLETIN PDF] EAC found: {eac}, etab_annee={eac.etablissement_annee}, classe={eac.classe}")
            if not id_annee:
                id_annee = str(eac.etablissement_annee.annee_id)
            if not id_cycle and eac.classe and eac.classe.cycle:
                id_cycle = str(eac.classe.cycle_id)
            if not id_campus:
                etab_id = eac.etablissement_annee.etablissement_id
                campus = Campus.objects.filter(id_etablissement=etab_id).first()
                id_campus = str(campus.id_campus) if campus else '1'
            logger.warning(f"[BULLETIN PDF] After auto-resolve: annee={id_annee}, campus={id_campus}, cycle={id_cycle}")
        except Exception as e:
            logger.error(f"[BULLETIN PDF] Auto-resolve FAILED: {e}")

    if not all([id_annee, id_campus, id_cycle, id_classe]) or not id_eleves or not id_eleves[0]:
        logger.error(f"[BULLETIN PDF] MISSING PARAMS: annee={id_annee}, campus={id_campus}, cycle={id_cycle}, classe={id_classe}, eleves={id_eleves}")
        messages.error(request, "Paramètres manquants ou invalides.")
        return HttpResponse('<script>window.location.href="/dashboard/evaluations/?section=bulletins";</script>')

    try:
        id_annee  = int(id_annee)
        id_campus = int(id_campus)
        id_cycle  = int(id_cycle)
        id_classe = int(id_classe)
        id_eleves = [int(e) for e in id_eleves if e and str(e).isdigit()]
    except ValueError:
        messages.error(request, "Paramètres numériques invalides.")
        return HttpResponse('<script>history.back();</script>', status=400)

    if not id_eleves:
        messages.error(request, "Aucun élève sélectionné.")
        return HttpResponse('<script>history.back();</script>', status=400)

    logger.warning(f"[BULLETIN PDF] Resolved params OK: annee={id_annee}, campus={id_campus}, cycle={id_cycle}, classe={id_classe}, eleves_count={len(id_eleves)}")

    # ───────────────────────────────────────────────
    # Déterminer la localisation
    # ───────────────────────────────────────────────
    try:
        campus = Campus.objects.get(id_campus=id_campus)
        localisation = campus.localisation.strip().upper()
    except Campus.DoesNotExist:
        logger.error(f"[BULLETIN PDF] Campus NOT FOUND: id_campus={id_campus}")
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
                    id_campus=id_campus,
                    id_classe_cycle=id_cycle,
                    id_classe=id_classe,
                    status=1
                ).first()

                if not inscription:
                    continue

                if idx > 0:
                    elements.append(PageBreak())
                elements.extend(create_header_elements())
                student_info, nom_eleve = create_student_info_tables(
                    id_eleve, id_annee, id_campus, id_cycle, id_classe
                )
                elements.extend(student_info)

                results_table, total_pct = create_results_table(
                    id_eleve, id_annee, id_campus, id_cycle, id_classe
                )
                elements.extend(results_table)

                elements.extend(create_signature_table())
                elements.append(PageBreak())

                elements.extend(create_back_page(
                    id_annee, id_campus, id_cycle, id_eleve, id_classe, total_pct
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
        margin = 5 * mm

        # Déterminer le cycle par mots-clés dans le model_name
        cycle_model = ''

        if not cycle_model:
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

                    elements.append(Spacer(1, 5*mm))
                    institution = Institution.objects.get(id_ecole=id_campus)
                    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                    check_image_paths(logo_path, emblem_path)

                    create_header(elements, logo_path, emblem_path, style_title, style_center)
                    create_nid_section(elements, style_normal)
                    left_table = create_line2_left(elements, style_normal)
                    right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
                    create_line2_section__secondaire_rdc(elements, left_table, right_table)
                    create_bulletin_title__secondaire_superieur(elements, style_title, style_right, id_classe=id_classe, id_annee=id_annee)
                    create_bulletin_maternelle(
                        elements, style_normal, style_center, style_title,
                        id_annee, id_campus, id_cycle, id_classe, id_eleve
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

                    elements.append(Spacer(1, 5*mm))
                    institution = Institution.objects.get(id_ecole=id_campus)
                    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                    check_image_paths(logo_path, emblem_path)

                    create_header(elements, logo_path, emblem_path, style_title, style_center)
                    create_nid_section(elements, style_normal)
                    left_table = create_line2_left(elements, style_normal)
                    right_table = create_line2_right(elements, eleve, style_normal, id_classe)
                    create_line2_section(elements, left_table, right_table)
                    create_bulletin_title(elements, style_title, id_annee, id_classe)
                    create_notes_table(
                        elements, style_center, style_normal,
                        id_annee, id_campus, id_cycle, id_classe, id_eleve
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

            for idx, id_eleve in enumerate(id_eleves):
                try:
                    eleve = Eleve.objects.get(id_eleve=id_eleve)
                    if idx > 0:
                        elements.append(PageBreak())

                    elements.append(Spacer(1, 5*mm))
                    institution = Institution.objects.get(id_ecole=id_campus)
                    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                    check_image_paths(logo_path, emblem_path)

                    create_header(elements, logo_path, emblem_path, style_title, style_center)
                    create_nid_section(elements, style_normal)
                    left_table = create_line2_left(elements, style_normal)
                    right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
                    create_line2_section__secondaire_rdc(elements, left_table, right_table)
                    create_bulletin_title__secondaire_rdc(elements, style_title, style_right, id_annee, id_classe)
                    create_notes_table__secondaire_rdc(
                        elements, style_center, style_normal,
                        id_annee, id_campus, id_cycle, id_classe, id_eleve
                    )
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

                        elements.append(Spacer(1, 5*mm))
                        institution = Institution.objects.get(id_ecole=id_campus)
                        logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                        emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                        check_image_paths(logo_path, emblem_path)

                        create_header(elements, logo_path, emblem_path, style_title, style_center)
                        create_nid_section(elements, style_normal)
                        left_table = create_line2_left(elements, style_normal)
                        right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
                        create_line2_section__secondaire_rdc(elements, left_table, right_table)
                        create_bulletin_title__secondaire_superieur(elements, style_title, style_right, id_classe=id_classe, id_annee=id_annee)
                        create_notes_table_superieur(
                            elements, style_center, style_normal,
                            id_annee, id_campus, id_cycle, id_classe, id_eleve
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

                        institution = Institution.objects.get(id_ecole=id_campus)
                        logo_path = institution.logo_ecole.path if institution.logo_ecole else None
                        emblem_path = institution.logo_ministere.path if institution.logo_ministere else None
                        check_image_paths(logo_path, emblem_path)

                        create_header(elements, logo_path, emblem_path, style_title, style_center)
                        create_nid_section(elements, style_normal)
                        left_table = create_line2_left(elements, style_normal)
                        right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
                        create_line2_section__secondaire_rdc(elements, left_table, right_table)
                        create_bulletin_title__secondaire_superieur(elements, style_title, style_right, id_classe=id_classe, id_annee=id_annee)
                        create_bulletin_content_cycle_superieur(
                            elements, style_normal, style_center,
                            id_annee, id_campus, id_cycle, id_classe, id_eleve,
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

        def on_all_pages(canvas, doc):
            draw_border(canvas, doc, eleve, margin) 

        doc.build(elements, onFirstPage=on_all_pages, onLaterPages=on_all_pages)

    # ───────────────────────────────────────────────
    # Nom de fichier final + réponse
    # ───────────────────────────────────────────────
    if len(id_eleves) == 1 and filename_parts:
        nom_fichier = slugify(filename_parts[0])
    else:
        try:
            classe = Classe.objects.get(id_classe=id_classe)
            nom_classe = slugify(classe.nom or "classe")
        except:
            nom_classe = "classe"
        nom_fichier = f"Bulletins_{localisation}_{nom_classe}_{id_annee}"

    filename = f"{nom_fichier}.pdf"

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"; filename*=UTF-8\'\'{filename}'

    buffer.close()
    return response

