"""
Views pour les 4 pages du dashboard MonEcole.
Reproduit exactement le contexte de dashboard_etablissement_view d'eSchool,
adapté pour le multi-tenant par sous-domaine de MonEcole.
"""
import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connections
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# Models Hub (managed=False, routés vers countryStructure)
from MonEcole_app.models.country_structure import (
    Pays, Etablissement, Regime, Cycle, StructurePedagogique,
    AdministrativeStructureType, AdministrativeStructureInstance,
    RepartitionType, RepartitionInstance, RepartitionHierarchie,
    RepartitionConfigEtabAnnee, RepartitionConfigCycle,
)
# Annee model
from MonEcole_app.models.annee import Annee

# Hub models for classes/cours — use country_structure versions
from MonEcole_app.models.country_structure import (
    EtablissementAnnee, EtablissementAnneeClasse, CoursAnnee as CoursAnneeModel,
)


def _get_dashboard_context(request):
    """
    Construit le contexte complet pour le dashboard, identique à eSchool.
    Utilise le tenant middleware (request.id_etablissement) au lieu de la session user_id.
    """
    etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
    if not etab_id:
        return None

    # Récupérer l'établissement depuis le Hub
    try:
        etab = Etablissement.objects.select_related(
            'pays', 'structure_pedagogique', 'gestionnaire'
        ).get(id_etablissement=etab_id)
    except Etablissement.DoesNotExist:
        return None

    pays = etab.pays

    active_section = request.GET.get('section', 'dashboard')

    # --- Année scolaire active ---
    # Annee.pays_id is an IntegerField, not a FK
    # etat_annee can be 'En Cours', 'ouverte', or 'actif' depending on config
    annee_active = Annee.objects.filter(
        pays_id=pays.id_pays, etat_annee__in=['En Cours', 'actif']
    ).order_by('-annee').first()
    if not annee_active:
        annee_active = Annee.objects.filter(
            pays_id=pays.id_pays, etat_annee='ouverte'
        ).order_by('-annee').first()
    if not annee_active:
        annee_active = Annee.objects.filter(
            pays_id=pays.id_pays
        ).order_by('-annee').first()

    annees_raw = Annee.objects.filter(
        pays_id=pays.id_pays
    ).order_by('-annee').values('id_annee', 'annee', 'etat_annee')
    # Template uses {{ a.etat }}, so alias etat_annee → etat
    annees_list = [{'id_annee': a['id_annee'], 'annee': a['annee'], 'etat': a['etat_annee'] or ''} for a in annees_raw]

    # --- Stats ---
    stats = {
        'n_classes': 0, 'n_cycles': 0, 'n_cours': 0,
        'n_trimestres_ouverts': 0, 'n_eleves': 0, 'n_enseignants': 0,
    }
    cycles_detail = []
    classes_detail = []
    trimestres_detail = []
    repartitions_notes = []
    cours_par_domaine = []
    eleves_stats = {}
    eleves_par_classe = []
    eleves_par_campus = []

    if annee_active:
        etab_annee = EtablissementAnnee.objects.filter(
            etablissement=etab, annee=annee_active
        ).first()

        if etab_annee:
            # Classes configurées
            classes_config = EtablissementAnneeClasse.objects.filter(
                etablissement_annee=etab_annee
            ).select_related('classe__cycle', 'section')

            stats['n_classes'] = classes_config.count()

            # Cycles distincts
            cycle_ids = set()
            cycle_counts = {}
            for cc in classes_config:
                cid = cc.classe.cycle_id
                cycle_ids.add(cid)
                cycle_counts[cid] = cycle_counts.get(cid, 0) + 1

            stats['n_cycles'] = len(cycle_ids)

            if cycle_ids:
                cycles_qs = Cycle.objects.filter(
                    id_cycle__in=cycle_ids
                ).order_by('ordre')
                for c in cycles_qs:
                    cycles_detail.append({
                        'nom': c.nom,
                        'n_classes': cycle_counts.get(c.id_cycle, 0),
                        'ordre': c.ordre,
                    })

            # Detail par classe
            for cc in classes_config:
                classe_label = str(cc.classe) if cc.classe else '-'
                if cc.groupe:
                    classe_label += f" {cc.groupe}"
                classes_detail.append({
                    'eac_id': cc.id,
                    'classe_nom': classe_label,
                    'cycle_nom': str(cc.classe.cycle) if cc.classe and cc.classe.cycle else '-',
                    'section_nom': cc.section.nom if cc.section else '-',
                    'groupe': cc.groupe or '',
                })

            # Cours
            classe_ids = [cc.classe_id for cc in classes_config]
            try:
                cours_annee_qs = CoursAnneeModel.objects.filter(
                    annee=annee_active,
                    cours__classe_id__in=classe_ids
                ).select_related('cours')
                stats['n_cours'] = cours_annee_qs.count()

                domaine_counts = {}
                for ca in cours_annee_qs:
                    dom_name = 'Sans domaine'
                    try:
                        if ca.domaine:
                            dom_name = ca.domaine.nom
                        elif hasattr(ca.cours, 'domaine') and ca.cours.domaine:
                            dom_name = ca.cours.domaine.nom
                    except Exception:
                        pass
                    domaine_counts[dom_name] = domaine_counts.get(dom_name, 0) + 1
                cours_par_domaine = sorted(domaine_counts.items(), key=lambda x: x[1], reverse=True)[:8]
            except Exception:
                pass  # Cours table may have schema differences

            # Répartitions temporelles
            active_cycle_ids = set(
                cc.classe.cycle_id for cc in classes_config
                if cc.classe and cc.classe.cycle_id
            )
            allowed_type_ids = set(
                RepartitionConfigCycle.objects.filter(
                    cycle_id__in=active_cycle_ids, is_active=True
                ).values_list('type_racine_id', flat=True)
            ) if active_cycle_ids else set()

            if allowed_type_ids:
                periode_type = RepartitionType.objects.filter(
                    code='P'
                ).values_list('id_type', flat=True).first()
                if periode_type:
                    allowed_type_ids.add(periode_type)

            parent_type_ids = set(
                RepartitionHierarchie.objects.filter(
                    is_active=True
                ).values_list('type_parent_id', flat=True)
            )

            if etab.is_calendar_synched:
                ri_qs = RepartitionInstance.objects.filter(
                    annee=annee_active, pays=pays, is_active=True
                ).select_related('type').order_by('type__nom', 'ordre')
                if allowed_type_ids:
                    ri_qs = ri_qs.filter(type_id__in=allowed_type_ids)
                for ri in ri_qs:
                    repartitions_notes.append({
                        'id': ri.id_instance, 'id_instance': ri.id_instance,
                        'nom': ri.nom, 'code': ri.code,
                        'type': ri.type.nom if ri.type else '',
                        'type_code': ri.type.code if ri.type else '',
                        'ordre': ri.ordre, 'is_open': ri.is_active,
                        'is_leaf': ri.type_id not in parent_type_ids,
                        'debut': str(ri.date_debut or ''), 'fin': str(ri.date_fin or ''),
                    })
                stats['n_trimestres_ouverts'] = sum(1 for r in repartitions_notes if r.get('is_open'))
            else:
                rep_qs = RepartitionConfigEtabAnnee.objects.filter(
                    etablissement_annee=etab_annee
                )
                if allowed_type_ids:
                    rep_qs = rep_qs.filter(repartition__type_id__in=allowed_type_ids)
                repartitions_raw = rep_qs.select_related('repartition__type').order_by(
                    'repartition__type__nom', 'repartition__ordre'
                ).values(
                    'id', 'repartition__id_instance', 'repartition__nom', 'repartition__code',
                    'repartition__type__nom', 'repartition__type__code',
                    'repartition__ordre', 'debut', 'fin', 'is_open'
                )
                stats['n_trimestres_ouverts'] = sum(1 for r in repartitions_raw if r.get('is_open'))
                for rc in repartitions_raw:
                    type_code = rc.get('repartition__type__code', '')
                    type_id = None
                    if type_code:
                        rt = RepartitionType.objects.filter(
                            code=type_code
                        ).values_list('id_type', flat=True).first()
                        type_id = rt
                    repartitions_notes.append({
                        'id': rc.get('id'),
                        'id_instance': rc.get('repartition__id_instance'),
                        'nom': rc.get('repartition__nom', '-'),
                        'code': rc.get('repartition__code', ''),
                        'type': rc.get('repartition__type__nom', ''),
                        'type_code': type_code,
                        'ordre': rc.get('repartition__ordre', 0),
                        'is_open': bool(rc.get('is_open')),
                        'is_leaf': type_id not in parent_type_ids if type_id else True,
                        'debut': str(rc.get('debut', '') or ''),
                        'fin': str(rc.get('fin', '') or ''),
                    })

            # Trimestres dedup
            trim_seen = {}
            for rc in repartitions_notes:
                r_name = rc.get('nom', '-')
                debut_val = rc.get('debut')
                fin_val = rc.get('fin')

                def safe_fmt(v, fmt='%d/%m/%Y'):
                    if v is None or v == '':
                        return '-'
                    if isinstance(v, str):
                        parts = v.split('-')
                        if len(parts) == 3:
                            return f"{parts[2]}/{parts[1]}/{parts[0]}"
                        return v
                    try:
                        return v.strftime(fmt)
                    except Exception:
                        return str(v)

                def safe_iso(v):
                    if v is None or v == '':
                        return None
                    if isinstance(v, str):
                        return v[:10] if len(v) >= 10 else v
                    try:
                        return v.isoformat()
                    except Exception:
                        return str(v)

                if r_name not in trim_seen:
                    trim_seen[r_name] = {
                        'id': rc.get('id'),
                        'trimestre': r_name,
                        'debut': safe_fmt(debut_val),
                        'fin': safe_fmt(fin_val),
                        'debut_iso': safe_iso(debut_val),
                        'fin_iso': safe_iso(fin_val),
                        'isOpen': bool(rc.get('is_open')),
                    }
                else:
                    if rc.get('is_open'):
                        trim_seen[r_name]['isOpen'] = True
            trimestres_detail = list(trim_seen.values())

    # --- Cross-DB stats from spoke (db_monecole = default) ---
    try:
        with connections['default'].cursor() as cur:
            # Elèves — filtrer par établissement
            cur.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN e.genre='M' THEN 1 ELSE 0 END) as garcons,
                       SUM(CASE WHEN e.genre='F' THEN 1 ELSE 0 END) as filles
                FROM eleve_inscription ei
                JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                WHERE ei.status = 1 AND ei.id_etablissement = %s
            """, [etab_id])
            row = cur.fetchone()
            if row:
                eleves_stats['total'] = int(row[0] or 0)
                eleves_stats['garcons'] = int(row[1] or 0)
                eleves_stats['filles'] = int(row[2] or 0)

            # Age distribution
            cur.execute("""
                SELECT TIMESTAMPDIFF(YEAR, e.date_naissance, CURDATE()) as age, COUNT(*) as nb
                FROM eleve_inscription ei
                JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                WHERE ei.status = 1 AND ei.id_etablissement = %s AND e.date_naissance IS NOT NULL AND e.date_naissance != '0000-00-00'
                GROUP BY age ORDER BY age
            """, [etab_id])
            eleves_stats['age_distribution'] = [
                {'tranche': f"{int(r[0])} ans", 'nb': int(r[1])} for r in cur.fetchall()
            ]

            # Elèves par classe (cross-DB)
            cur.execute("""
                SELECT ei.id_classe_id as eac_id, COUNT(*) as total,
                       SUM(CASE WHEN e.genre='M' THEN 1 ELSE 0 END) as garcons,
                       SUM(CASE WHEN e.genre='F' THEN 1 ELSE 0 END) as filles
                FROM eleve_inscription ei
                JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                WHERE ei.status = 1 AND ei.id_etablissement = %s
                GROUP BY ei.id_classe_id
            """, [etab_id])
            epc_raw = {int(r[0]): {'total': int(r[1]), 'garcons': int(r[2] or 0), 'filles': int(r[3] or 0)} for r in cur.fetchall()}

            # Match with classes_detail
            for cd in classes_detail:
                epc = epc_raw.get(cd['eac_id'], {})
                if epc:
                    eleves_par_classe.append({
                        'eac_id': cd['eac_id'],
                        'classe_nom': cd['classe_nom'],
                        'total': epc['total'],
                        'garcons': epc['garcons'],
                        'filles': epc['filles'],
                    })

            # Elèves par campus
            cur.execute("""
                SELECT c.campus as campus_nom, COUNT(*) as total
                FROM eleve_inscription ei
                JOIN campus c ON c.id_campus = ei.id_campus_id
                WHERE ei.status = 1 AND ei.id_etablissement = %s
                GROUP BY c.id_campus, c.campus ORDER BY total DESC
            """, [etab_id])
            eleves_par_campus = [
                {'campus_nom': r[0], 'total': int(r[1])} for r in cur.fetchall()
            ]

            # Enseignants — filtrer par établissement
            cur.execute("SELECT COUNT(*) FROM personnel WHERE en_fonction = 1 AND id_etablissement = %s", [etab_id])
            row = cur.fetchone()
            stats['n_enseignants'] = int(row[0]) if row else 0

    except Exception:
        import traceback
        traceback.print_exc()

    stats['n_eleves'] = eleves_stats.get('total', 0)

    # --- Fiche établissement ---
    regime_nom = '-'
    if etab.id_regime:
        try:
            regime_nom = Regime.objects.get(id_regime=etab.id_regime).regime
        except Regime.DoesNotExist:
            pass

    etab_data = {
        'id_etablissement': etab.id_etablissement,
        'nom': etab.nom,
        'sigle': etab.sigle or '',
        'code_ecole': etab.code_ecole or '',
        'matricule': getattr(etab, 'matricule', '') or '',
        'no_dinacope': getattr(etab, 'no_dinacope', '') or '',
        'reference_agrement': getattr(etab, 'reference_agrement', '') or '',
        'adresse': etab.adresse or '',
        'email': etab.email or '',
        'telephone': etab.telephone or '',
        'fax': getattr(etab, 'fax', '') or '',
        'boite_postale': getattr(etab, 'boite_postale', '') or '',
        'representant': getattr(etab, 'representant', '') or '',
        'emplacement': getattr(etab, 'emplacement', '') or '',
        'url': etab.url or '',
        'logo_ecole': getattr(etab, 'logo_ecole', '') or '',
        'regime_nom': regime_nom,
        'id_regime': etab.id_regime,
        'structure_pedagogique': etab.structure_pedagogique.nom if etab.structure_pedagogique else '-',
        'gestionnaire': str(etab.gestionnaire) if etab.gestionnaire else '-',
        'gestionnaire_email': etab.gestionnaire.email if etab.gestionnaire and hasattr(etab.gestionnaire, 'email') else '',
        'gestionnaire_telephone': etab.gestionnaire.telephone if etab.gestionnaire and hasattr(etab.gestionnaire, 'telephone') else '',
        'code': etab.code,
        'pays_nom': pays.nom,
        'pays_sigle': pays.sigle,
        'pays_id': pays.id_pays,
        'ref_administrative': getattr(etab, 'ref_administrative', '') or '',
        'nom_rue': getattr(etab, 'nom_rue', '') or '',
        'numero_rue': getattr(etab, 'numero_rue', '') or '',
        'annee_creation': getattr(etab, 'annee_creation', '') or '',
        'annee_agrement': getattr(etab, 'annee_agrement', '') or '',
        'document_agrement': getattr(etab, 'document_agrement', '') or '',
        'is_calendar_synched': etab.is_calendar_synched,
    }

    # Régimes
    regimes = list(Regime.objects.filter(pays=pays).values('id_regime', 'regime'))

    # Admin types & instances
    admin_types = list(
        AdministrativeStructureType.objects.filter(
            pays=pays
        ).order_by('ordre').values('id_structure', 'code', 'nom', 'ordre')
    )

    admin_instances_by_ordre = {}
    all_admin_instances = AdministrativeStructureInstance.objects.filter(
        pays=pays
    ).order_by('ordre', 'nom').values('id_structure', 'nom', 'ordre', 'code')
    for inst in all_admin_instances:
        o = inst['ordre']
        if o not in admin_instances_by_ordre:
            admin_instances_by_ordre[o] = []
        admin_instances_by_ordre[o].append({
            'id': inst['id_structure'], 'nom': inst['nom'], 'code': inst['code'],
        })
    # Build admin_chain for the Adresse section in the fiche
    admin_chain = []
    ref_admin = getattr(etab, 'ref_administrative', '') or ''
    if ref_admin:
        ref_ids = [int(x) for x in ref_admin.split('-') if x.strip().isdigit()]
        # Build a lookup: id -> instance dict (with type name)
        id_to_instance = {}
        for inst in all_admin_instances:
            id_to_instance[inst['id_structure']] = inst
        # Map ordre -> type name
        type_by_ordre = {t['ordre']: t['nom'] for t in admin_types}
        for rid in ref_ids:
            inst = id_to_instance.get(rid)
            if inst:
                admin_chain.append({
                    'type_nom': type_by_ordre.get(inst['ordre'], f'Niveau {inst["ordre"]}'),
                    'instance_nom': inst['nom'],
                })

    # JSON data
    cours_domaine_json = json.dumps(
        [{'domaine': d, 'count': c} for d, c in cours_par_domaine] if annee_active else [],
        ensure_ascii=False
    )
    trimestres_json = json.dumps(trimestres_detail, ensure_ascii=False, default=str)

    context = {
        'etab': etab_data,
        'stats': stats,
        'active_section': active_section,
        'annee_active': {
            'id': annee_active.id_annee,
            'annee': annee_active.annee,
            'etat': getattr(annee_active, 'etat_annee', ''),
        } if annee_active else None,
        'annees_list': annees_list,
        'annees_json': json.dumps(annees_list, ensure_ascii=False, default=str),
        'cycles_detail': cycles_detail,
        'trimestres_detail': trimestres_detail,
        'trimestres_json': trimestres_json,
        'cours_domaine_json': cours_domaine_json,
        'eleves_stats_json': json.dumps(eleves_stats, ensure_ascii=False, default=str),
        'eleves_par_classe_json': json.dumps(eleves_par_classe, ensure_ascii=False, default=str),
        'eleves_par_campus_json': json.dumps(eleves_par_campus, ensure_ascii=False, default=str),
        'regimes': json.dumps(regimes, ensure_ascii=False, default=str),
        'classes_detail': classes_detail if annee_active else [],
        'repartitions_notes_json': json.dumps(
            repartitions_notes if annee_active else [], ensure_ascii=False, default=str
        ),
        'admin_types': admin_types,
        'admin_types_json': json.dumps(admin_types, ensure_ascii=False, default=str),
        'admin_instances_json': json.dumps(admin_instances_by_ordre, ensure_ascii=False, default=str),
        'is_calendar_synched': etab.is_calendar_synched,
        'admin_chain': admin_chain,
    }
    return context


# ============================================================
# 4 VIEWS — une par page
# ============================================================

def _add_module_context(context, request, active_module_page):
    """Ajoute les modules de l'utilisateur au contexte (depuis la session)."""
    user_modules = request.session.get('user_modules', [])
    context['user_modules'] = user_modules
    context['active_module'] = active_module_page
    context['user_email'] = request.session.get('user_email', '')
    return context


@login_required(login_url='login')
def administration_view(request):
    """Page Administration : Dashboard + MonEcole + Structuration + Calendrier."""
    context = _get_dashboard_context(request)
    if context is None:
        return render(request, 'dashboard/no_tenant.html')
    context['active_page'] = 'administration'
    _add_module_context(context, request, 'administration')
    return render(request, 'dashboard/administration.html', context)


@login_required(login_url='login')
def enseignements_view(request):
    """Page Enseignements : Enseignants + Cours & Pondérations + Attribution."""
    context = _get_dashboard_context(request)
    if context is None:
        return render(request, 'dashboard/no_tenant.html')
    context['active_page'] = 'enseignements'
    if not context.get('active_section') or context['active_section'] == 'dashboard':
        context['active_section'] = 'enseignants'
    _add_module_context(context, request, 'enseignements')
    return render(request, 'dashboard/enseignements.html', context)


@login_required(login_url='login')
def evaluations_view(request):
    """Page Évaluations : Évaluations + Notes + Résultats."""
    context = _get_dashboard_context(request)
    if context is None:
        return render(request, 'dashboard/no_tenant.html')
    context['active_page'] = 'evaluations'
    if not context.get('active_section') or context['active_section'] == 'dashboard':
        context['active_section'] = 'evaluations'
    _add_module_context(context, request, 'evaluations')
    return render(request, 'dashboard/evaluations_page.html', context)


@login_required(login_url='login')
def scolarite_view(request):
    """Page Scolarité : Élèves."""
    context = _get_dashboard_context(request)
    if context is None:
        return render(request, 'dashboard/no_tenant.html')
    context['active_page'] = 'scolarite'
    if not context.get('active_section') or context['active_section'] == 'dashboard':
        context['active_section'] = 'eleves'
    _add_module_context(context, request, 'scolarite')
    return render(request, 'dashboard/scolarite.html', context)


# ============================================================
# ESPACE ENSEIGNANT
# ============================================================

@login_required(login_url='login')
def espace_enseignant_view(request):
    """Page Espace Enseignant — Dashboard personnel de l'enseignant."""
    context = _get_dashboard_context(request)
    if context is None:
        return render(request, 'dashboard/no_tenant.html')

    active_section = request.GET.get('section', 'dashboard')
    context['active_section'] = active_section
    context['active_page'] = 'espace_enseignant'
    _add_module_context(context, request, 'enseignements')

    # Identifier le personnel connecté
    etab_id = context['etab']['id_etablissement']
    personnel_id = None
    personnel_info = {}

    try:
        from MonEcole_app.models.personnel import Personnel
        pers = Personnel.objects.select_related('user').filter(
            user=request.user, id_etablissement=etab_id
        ).first()
        if pers:
            personnel_id = pers.id_personnel
            personnel_info = {
                'id': pers.id_personnel,
                'nom': pers.user.last_name,
                'prenom': pers.user.first_name,
                'email': pers.user.email,
                'matricule': pers.matricule,
                'telephone': str(pers.telephone) if pers.telephone else '',
                'imageUrl': pers.imageUrl.url if pers.imageUrl else '',
            }
    except Exception:
        pass

    context['personnel_id'] = personnel_id or 0
    context['personnel_info'] = json.dumps(personnel_info, ensure_ascii=False, default=str)

    return render(request, 'dashboard/espace_enseignant.html', context)


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_enseignant_dashboard(request):
    """API : Données dashboard enseignant — cours, horaires, stats."""
    etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    # Find current teacher
    try:
        from MonEcole_app.models.personnel import Personnel
        pers = Personnel.objects.filter(user=request.user, id_etablissement=etab_id).first()
        if not pers:
            return JsonResponse({'success': False, 'error': 'Vous n\'êtes pas enregistré comme personnel'}, status=403)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    personnel_id = pers.id_personnel

    try:
        with connections['default'].cursor() as cur:
            # 1. Mes cours attribués (JOIN Hub via countryStructure)
            courses = []
            try:
                with connections['countryStructure'].cursor() as hub_cur:
                    cur.execute("""
                        SELECT ac.id_attribution, ac.id_cours_id, ac.id_classe_id,
                               ac.id_cycle_id, ac.id_campus_id, ac.date_attribution
                        FROM attribution_cours ac
                        WHERE ac.id_personnel_id = %s AND ac.id_etablissement = %s
                        ORDER BY ac.date_attribution DESC
                    """, [personnel_id, etab_id])
                    attributions = cur.fetchall()

                    for att in attributions:
                        cours_annee_id = att['id_cours_id']
                        classe_id = att['id_classe_id']
                        # Get course name from Hub
                        hub_cur.execute("""
                            SELECT ca.id_cours_annee, c.cours, c.code_cours,
                                   ca.ponderation, ca.heure_semaine
                            FROM cours_annee ca
                            JOIN cours c ON c.id_cours = ca.cours_id
                            WHERE ca.id_cours_annee = %s
                        """, [cours_annee_id])
                        cr = hub_cur.fetchone()
                        if not cr:
                            continue

                        # Get class and cycle info from Hub
                        hub_cur.execute("""
                            SELECT eac.id AS eac_id, cl.nom AS classe_nom,
                                   cy.nom AS cycle_nom
                            FROM etablissement_annee_classes eac
                            JOIN classes cl ON cl.id_classe = eac.classe_id
                            LEFT JOIN cycles cy ON cy.id_cycle = cl.cycle_id
                            WHERE eac.id = %s
                        """, [classe_id])
                        cl = hub_cur.fetchone()

                        # Count students in this class
                        cur.execute("""
                            SELECT COUNT(*) FROM eleve_inscription
                            WHERE id_classe_id = %s AND status = 1 AND id_etablissement = %s
                        """, [classe_id, etab_id])
                        n_eleves = cur.fetchone()[0]

                        courses.append({
                            'id_attribution': att['id_attribution'],
                            'id_cours_annee': cours_annee_id,
                            'cours': cr['cours'] if isinstance(cr, dict) else cr[1],
                            'code_cours': (cr['code_cours'] if isinstance(cr, dict) else cr[2]) or '',
                            'ponderation': (cr['ponderation'] if isinstance(cr, dict) else cr[3]) or 0,
                            'heure_semaine': (cr['heure_semaine'] if isinstance(cr, dict) else cr[4]) or 0,
                            'classe_nom': (cl['classe_nom'] if isinstance(cl, dict) else cl[1]) if cl else '-',
                            'cycle_nom': (cl['cycle_nom'] if isinstance(cl, dict) else cl[2]) if cl else '-',
                            'eac_id': classe_id,
                            'n_eleves': n_eleves,
                        })
            except Exception as e:
                import traceback
                traceback.print_exc()

            # 2. Emploi du temps
            schedule = []
            try:
                cur.execute("""
                    SELECT h.id_horaire, h.date, h.debut, h.fin,
                           h.id_cours_id, h.id_classe_id
                    FROM horaire h
                    JOIN attribution_cours ac ON ac.id_cours_id = h.id_cours_id
                        AND ac.id_classe_id = h.id_classe_id
                    WHERE ac.id_personnel_id = %s AND ac.id_etablissement = %s
                    ORDER BY h.date DESC, h.debut
                    LIMIT 50
                """, [personnel_id, etab_id])
                for row in cur.fetchall():
                    schedule.append({
                        'id': row['id_horaire'] if isinstance(row, dict) else row[0],
                        'date': str(row['date'] if isinstance(row, dict) else row[1]),
                        'debut': row['debut'] if isinstance(row, dict) else row[2],
                        'fin': row['fin'] if isinstance(row, dict) else row[3],
                    })
            except Exception:
                pass

            # 3. Présences stats
            presences_stats = {'total_seances': 0, 'total_presents': 0, 'total_absents': 0}
            try:
                cur.execute("""
                    SELECT COUNT(DISTINCT h.id_horaire) as seances,
                           SUM(CASE WHEN hp.present_ou_absent = 1 THEN 1 ELSE 0 END) as presents,
                           SUM(CASE WHEN hp.present_ou_absent = 0 THEN 1 ELSE 0 END) as absents
                    FROM horaire h
                    JOIN attribution_cours ac ON ac.id_cours_id = h.id_cours_id
                        AND ac.id_classe_id = h.id_classe_id
                    LEFT JOIN horaire_presence hp ON hp.id_horaire_id = h.id_horaire
                    WHERE ac.id_personnel_id = %s AND ac.id_etablissement = %s
                """, [personnel_id, etab_id])
                row = cur.fetchone()
                if row:
                    presences_stats = {
                        'total_seances': int((row['seances'] if isinstance(row, dict) else row[0]) or 0),
                        'total_presents': int((row['presents'] if isinstance(row, dict) else row[1]) or 0),
                        'total_absents': int((row['absents'] if isinstance(row, dict) else row[2]) or 0),
                    }
            except Exception:
                pass

            # 4. Évaluations count
            n_evaluations = 0
            try:
                attr_cours_ids = [c['id_cours_annee'] for c in courses]
                if attr_cours_ids:
                    placeholders = ','.join(['%s'] * len(attr_cours_ids))
                    cur.execute(f"""
                        SELECT COUNT(*) FROM evaluation
                        WHERE id_cours_classe_id IN ({placeholders}) AND id_etablissement = %s
                    """, attr_cours_ids + [etab_id])
                    n_evaluations = cur.fetchone()[0]
            except Exception:
                pass

        return JsonResponse({
            'success': True,
            'courses': courses,
            'schedule': schedule,
            'presences_stats': presences_stats,
            'n_evaluations': n_evaluations,
            'n_courses': len(courses),
            'n_classes': len(set(c['eac_id'] for c in courses)),
            'n_eleves_total': sum(c['n_eleves'] for c in courses),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

