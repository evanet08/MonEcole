"""
Views pour les 4 pages du dashboard MonEcole.
Reproduit exactement le contexte de dashboard_etablissement_view d'eSchool,
adapté pour le multi-tenant par sous-domaine de MonEcole.
"""
import json
from functools import wraps
from django.shortcuts import render, redirect
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


def login_required(login_url='login'):
    """Décorateur session-based qui remplace @login_required de Django."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get('personnel_id'):
                return redirect(login_url)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def _get_etab_id(request):
    """Résout l'id_etablissement de manière robuste : request attr → session → host SQL."""
    etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
    if etab_id:
        return etab_id
    try:
        host = request.get_host().split(':')[0].lower().strip()
        with connections['countryStructure'].cursor() as cursor:
            cursor.execute("SELECT id_etablissement FROM etablissements WHERE url = %s LIMIT 1", [host])
            row = cursor.fetchone()
            if row:
                etab_id = row[0]
                request.session['id_etablissement'] = etab_id
                return etab_id
    except Exception:
        pass
    return None


def _get_dashboard_context(request):
    """
    Construit le contexte complet pour le dashboard, identique à eSchool.
    Utilise le tenant middleware (request.id_etablissement) au lieu de la session user_id.
    """
    etab_id = _get_etab_id(request)
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

            # Répartitions temporelles — filtrer selon les cycles de l'établissement
            active_cycle_ids = set(
                cc.classe.cycle_id for cc in classes_config
                if cc.classe and cc.classe.cycle_id
            )

            # Récupérer les configs cycle pour cet établissement
            etab_cycle_configs = list(
                RepartitionConfigCycle.objects.filter(
                    cycle_id__in=active_cycle_ids, is_active=True
                ).select_related('type_racine')
            ) if active_cycle_ids else []

            # Calculer le nombre max d'instances par type racine
            # Ex: si Ecole de Base = 2 Semestres et Humanités = 2 Semestres → max 2
            type_max_count = {}  # type_id → max nombre d'instances racine
            for cc in etab_cycle_configs:
                tid = cc.type_racine_id
                if tid not in type_max_count or cc.nombre_au_niveau_racine > type_max_count[tid]:
                    type_max_count[tid] = cc.nombre_au_niveau_racine

            allowed_type_ids = set(type_max_count.keys())

            # Charger les hiérarchies pour déterminer les types enfants et leur nombre
            hierarchies_for_types = {}  # parent_type_id → {child_type_id, nb_enfants}
            for h in RepartitionHierarchie.objects.filter(is_active=True).select_related('type_parent', 'type_enfant'):
                hierarchies_for_types[h.type_parent_id] = {
                    'child_type_id': h.type_enfant_id,
                    'nb_enfants': h.nombre_enfants,
                }

            # Calculer le nombre max d'instances enfants par type
            child_type_max_count = {}  # child_type_id → max nombre d'instances enfants
            for root_type_id, max_root in type_max_count.items():
                hier = hierarchies_for_types.get(root_type_id)
                if hier:
                    child_tid = hier['child_type_id']
                    total_children = max_root * hier['nb_enfants']
                    if child_tid not in child_type_max_count or total_children > child_type_max_count[child_tid]:
                        child_type_max_count[child_tid] = total_children
                    allowed_type_ids.add(child_tid)

            # Fusionner pour avoir les limites par type
            # type_id → max instances à afficher
            type_instance_limits = {}
            type_instance_limits.update(type_max_count)
            type_instance_limits.update(child_type_max_count)

            parent_type_ids = set(hierarchies_for_types.keys())

            if etab.is_calendar_synched:
                ri_qs = RepartitionInstance.objects.filter(
                    annee=annee_active, pays=pays, is_active=True
                ).select_related('type').order_by('type__nom', 'ordre')
                if allowed_type_ids:
                    ri_qs = ri_qs.filter(type_id__in=allowed_type_ids)

                # Grouper par type et limiter par le nombre calculé
                type_count_tracker = {}  # type_id → nombre ajouté
                for ri in ri_qs:
                    tid = ri.type_id
                    current_count = type_count_tracker.get(tid, 0)
                    max_allowed = type_instance_limits.get(tid)
                    # Si pas de limite (type non configuré), skip
                    if max_allowed is not None and current_count >= max_allowed:
                        continue
                    type_count_tracker[tid] = current_count + 1
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
    _add_module_context(context, request, 'espace_enseignant')

    # Identifier le personnel connecté
    etab_id = context['etab']['id_etablissement']
    personnel_id = None
    personnel_info = {}

    try:
        from MonEcole_app.models.personnel import Personnel
        # 1. Chercher par personnel_id de la session
        pers_id = request.session.get('personnel_id')
        pers = None
        if pers_id:
            pers = Personnel.objects.filter(
                id_personnel=pers_id, id_etablissement=etab_id
            ).first()

        # 2. Fallback: chercher par email
        if not pers and request.user.email:
            try:
                pers = Personnel.objects.filter(
                    email__iexact=request.user.email, id_etablissement=etab_id
                ).first()
            except Exception:
                pass

        if pers:
            personnel_id = pers.id_personnel
            # Utiliser les champs directs de personnel
            try:
                with connections['default'].cursor() as cur:
                    cur.execute(
                        "SELECT nom, postnom, prenom, email, telephone, imageUrl FROM personnel WHERE id_personnel = %s",
                        [pers.id_personnel]
                    )
                    sql_row = cur.fetchone()
                    if sql_row:
                        personnel_info = {
                            'id': pers.id_personnel,
                            'nom': sql_row[0] or pers.nom or '',
                            'prenom': sql_row[2] or pers.prenom or '',
                            'email': sql_row[3] or pers.email or '',
                            'matricule': pers.matricule,
                            'telephone': sql_row[4] or '',
                            'imageUrl': sql_row[5] or '',
                        }
                    else:
                        personnel_info = {
                            'id': pers.id_personnel,
                            'nom': pers.nom or '',
                            'prenom': pers.prenom or '',
                            'email': pers.email or '',
                            'matricule': pers.matricule,
                            'telephone': str(pers.telephone) if pers.telephone else '',
                            'imageUrl': pers.imageUrl.url if pers.imageUrl else '',
                        }
            except Exception:
                personnel_info = {
                    'id': pers.id_personnel,
                    'nom': pers.nom or '',
                    'prenom': pers.prenom or '',
                    'email': pers.email or '',
                    'matricule': pers.matricule,
                    'telephone': str(pers.telephone) if pers.telephone else '',
                    'imageUrl': pers.imageUrl.url if pers.imageUrl else '',
                }
    except Exception:
        import traceback
        traceback.print_exc()

    context['personnel_id'] = personnel_id or 0
    context['personnel_info'] = json.dumps(personnel_info, ensure_ascii=False, default=str)

    # Charger les répartitions (périodes) pour la section Notes
    # Filtrer selon les cycles actifs de l'établissement
    repartitions = []
    try:
        annee_active = context.get('annee_active')
        if annee_active:
            annee_id = annee_active.get('id') or annee_active.get('id_annee')
            etab_id = context['etab']['id_etablissement']
            from django.conf import settings
            import pymysql
            hub_settings = settings.DATABASES.get('countryStructure', {})
            if hub_settings:
                hconn = pymysql.connect(
                    host=hub_settings.get('HOST','localhost'),
                    user=hub_settings['USER'],
                    password=hub_settings['PASSWORD'],
                    port=int(hub_settings.get('PORT',3306) or 3306),
                    database=hub_settings['NAME'],
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                )
                with hconn.cursor() as hcur:
                    # 1. Trouver les cycles actifs de l'établissement
                    hcur.execute("""
                        SELECT DISTINCT cl.cycle_id
                        FROM etablissements_annees_classes eac
                        JOIN etablissements_annees ea ON ea.id = eac.etablissement_annee_id
                        JOIN classes cl ON cl.id_classe = eac.classe_id
                        WHERE ea.etablissement_id = %s AND ea.annee_id = %s
                    """, [etab_id, annee_id])
                    active_cycle_ids = [r['cycle_id'] for r in hcur.fetchall()]

                    # 2. Configs cycle → type racine + max count
                    type_limits = {}  # type_id → max instances
                    if active_cycle_ids:
                        fmt = ','.join(['%s'] * len(active_cycle_ids))
                        hcur.execute(f"""
                            SELECT type_racine_id, MAX(nombre_au_niveau_racine) as max_nb
                            FROM repartition_configs_cycle
                            WHERE cycle_id IN ({fmt}) AND is_active = 1
                            GROUP BY type_racine_id
                        """, active_cycle_ids)
                        for r in hcur.fetchall():
                            type_limits[r['type_racine_id']] = r['max_nb']

                    # 3. Hiérarchies → types enfants + limites
                    hcur.execute("""
                        SELECT type_parent_id, type_enfant_id, nombre_enfants
                        FROM repartition_hierarchies WHERE is_active = 1
                    """)
                    for h in hcur.fetchall():
                        parent_tid = h['type_parent_id']
                        if parent_tid in type_limits:
                            child_tid = h['type_enfant_id']
                            total = type_limits[parent_tid] * h['nombre_enfants']
                            if child_tid not in type_limits or total > type_limits[child_tid]:
                                type_limits[child_tid] = total

                    # 4. Charger les instances filtrées
                    if type_limits:
                        all_type_ids = list(type_limits.keys())
                        fmt = ','.join(['%s'] * len(all_type_ids))
                        hcur.execute(f"""
                            SELECT ri.id_instance, ri.nom, rt.nom AS type_nom, ri.type_id, ri.ordre
                            FROM repartition_instances ri
                            JOIN repartition_types rt ON rt.id_type = ri.type_id
                            WHERE ri.annee_id = %s AND ri.is_active = 1
                              AND ri.type_id IN ({fmt})
                            ORDER BY ri.type_id, ri.ordre
                        """, [annee_id] + all_type_ids)
                        all_reps = hcur.fetchall()
                        type_count = {}
                        for r in all_reps:
                            tid = r['type_id']
                            cnt = type_count.get(tid, 0)
                            if cnt >= type_limits.get(tid, 999):
                                continue
                            type_count[tid] = cnt + 1
                            repartitions.append({
                                'id_instance': r['id_instance'],
                                'nom': r['nom'],
                                'type_nom': r['type_nom'],
                                'is_leaf': True,
                            })
                hconn.close()
    except Exception:
        import traceback; traceback.print_exc()
    context['repartitions_notes_json'] = json.dumps(repartitions, ensure_ascii=False, default=str)

    return render(request, 'dashboard/espace_enseignant.html', context)


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_enseignant_debug(request):
    """DEBUG TEMPORAIRE — vérifie la chaîne de données enseignant."""
    import pymysql
    etab_id = _get_etab_id(request)
    pers_id = request.session.get('personnel_id')
    debug = {
        'personnel_id': pers_id,
        'user_email': request.user.email,
        'etab_id': etab_id,
        'steps': {}
    }
    try:
        db_settings = connections['default'].settings_dict
        conn = pymysql.connect(
            host=db_settings.get('HOST', 'localhost') or 'localhost',
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            port=int(db_settings.get('PORT', 3306) or 3306),
            database=db_settings['NAME'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
        )
        with conn.cursor() as cur:
            # Step 1: Personnel by id_personnel
            cur.execute("SELECT id_personnel, id_etablissement, matricule, en_fonction, email FROM personnel WHERE id_personnel = %s", [pers_id])
            debug['steps']['1_personnel_by_id'] = cur.fetchall()

            # Step 2: Personnel for this etab
            cur.execute("SELECT id_personnel, id_etablissement, matricule FROM personnel WHERE id_personnel = %s AND id_etablissement = %s", [pers_id, etab_id])
            personnel_rows = cur.fetchall()
            debug['steps']['2_personnel_for_etab'] = personnel_rows

            # Step 3: Table columns
            cur.execute("SHOW COLUMNS FROM attribution_cours")
            debug['steps']['3_attribution_cours_columns'] = [r['Field'] for r in cur.fetchall()]

            # Step 4: All attributions
            if personnel_rows:
                pid = personnel_rows[0]['id_personnel']
                cur.execute("SELECT * FROM attribution_cours WHERE id_personnel_id = %s LIMIT 10", [pid])
                debug['steps']['4_attributions_for_personnel'] = cur.fetchall()

                # Step 5: Try without id_etablissement filter
                cur.execute("SELECT COUNT(*) as n FROM attribution_cours WHERE id_personnel_id = %s", [pid])
                debug['steps']['5_total_attributions'] = cur.fetchone()
            else:
                debug['steps']['4_note'] = 'No personnel found for this user+etab'
                # Try all personnel
                cur.execute("SELECT id_personnel, user_id, id_etablissement, matricule FROM personnel LIMIT 10")
                debug['steps']['4b_all_personnel_sample'] = cur.fetchall()

            # Step 6: Horaire columns
            cur.execute("SHOW COLUMNS FROM horaire")
            debug['steps']['6_horaire_columns'] = [r['Field'] for r in cur.fetchall()]

        conn.close()
    except Exception as e:
        import traceback
        debug['error'] = str(e)
        debug['traceback'] = traceback.format_exc()

    return JsonResponse(debug, json_encoder=json.JSONEncoder, safe=False, default=str)


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_enseignant_dashboard(request):
    """API : Données dashboard enseignant — cours, horaires, stats."""
    import pymysql, sys
    print(f"[api_enseignant_dashboard] CALLED by personnel_id={request.session.get('personnel_id')}, email={request.user.email}", file=sys.stderr, flush=True)
    etab_id = _get_etab_id(request)
    print(f"[api_enseignant_dashboard] etab_id={etab_id}", file=sys.stderr, flush=True)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    # Find current teacher via spoke DB (pymysql DictCursor)
    try:
        db_settings = connections['default'].settings_dict
        conn = pymysql.connect(
            host=db_settings.get('HOST', 'localhost') or 'localhost',
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            port=int(db_settings.get('PORT', 3306) or 3306),
            database=db_settings['NAME'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
            read_timeout=10,
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'DB connection error: {e}'}, status=500)

    try:
        with conn.cursor() as cur:
            # Find personnel for logged-in user (by user_id)
            cur.execute("""
                SELECT p.id_personnel, p.nom, p.postnom, p.prenom, p.matricule,
                       p.telephone, p.prenom as first_name, p.nom as last_name, p.email
                FROM personnel p
                WHERE p.id_personnel = %s AND p.id_etablissement = %s
                LIMIT 1
            """, [request.user.id_personnel, etab_id])
            pers = cur.fetchone()

            # Fallback: chercher par email (personnel ajouté via dashboard avec user_id bidon)
            if not pers:
                user_email = request.user.email
                if user_email:
                    cur.execute("""
                        SELECT p.id_personnel, p.nom, p.postnom, p.prenom, p.matricule,
                               p.telephone, p.email as email
                        FROM personnel p
                        WHERE LOWER(p.email) = LOWER(%s) AND p.id_etablissement = %s
                        LIMIT 1
                    """, [user_email, etab_id])
                    pers = cur.fetchone()
                    if pers:
                        # Remplir les champs manquants pour compatibilité
                        pers['first_name'] = pers.get('prenom') or ''
                        pers['last_name'] = pers.get('nom') or ''
                        # Tenter le re-link silencieusement
                        try:
                            pass  # Plus de re-link nécessaire — auth centrée sur personnel
                            conn.commit()
                        except Exception:
                            try:
                                conn.rollback()
                            except Exception:
                                pass

            if not pers:
                # Debug: print to stderr for journalctl
                import sys
                print(f"[api_enseignant_dashboard] Personnel NOT FOUND: personnel_id={request.user.id_personnel}, email={request.user.email}, etab_id={etab_id}", file=sys.stderr, flush=True)
                cur.execute("SELECT id_personnel, email, nom, prenom FROM personnel WHERE id_etablissement = %s LIMIT 5", [etab_id])
                all_pers = cur.fetchall()
                print(f"[api_enseignant_dashboard] First 5 personnel for etab {etab_id}: {all_pers}", file=sys.stderr, flush=True)
                conn.close()
                return JsonResponse({'success': False, 'error': f'Personnel non trouvé (id={request.user.id_personnel}, email={request.user.email})'}, status=403)

            personnel_id = pers['id_personnel']

            # 1. Mes cours attribués
            courses = []
            cur.execute("""
                SELECT ac.id_attribution, ac.id_cours_id, ac.id_classe_id,
                       ac.id_cycle_id, ac.id_campus_id, ac.date_attribution
                FROM attribution_cours ac
                WHERE ac.id_personnel_id = %s AND ac.id_etablissement = %s
                ORDER BY ac.date_attribution DESC
            """, [personnel_id, etab_id])
            attributions = cur.fetchall()

            # Get Hub data for course & class names
            try:
                hub_settings = connections['countryStructure'].settings_dict
                hub_conn = pymysql.connect(
                    host=hub_settings.get('HOST', 'localhost') or 'localhost',
                    user=hub_settings['USER'],
                    password=hub_settings['PASSWORD'],
                    port=int(hub_settings.get('PORT', 3306) or 3306),
                    database=hub_settings['NAME'],
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=5,
                    read_timeout=10,
                )
                hub_cur = hub_conn.cursor()
            except Exception as e:
                import traceback
                traceback.print_exc()
                hub_cur = None
                hub_conn = None

            for att in attributions:
                cours_annee_id = att['id_cours_id']
                classe_id = att['id_classe_id']

                cours_nom = f"Cours #{cours_annee_id}"
                code_cours = ''
                ponderation = 0
                heure_semaine = 0
                classe_nom = f"Classe #{classe_id}"
                cycle_nom = '-'

                # Course info from Hub
                if hub_cur:
                    try:
                        hub_cur.execute("""
                            SELECT c.cours, c.code_cours, ca.ponderation, ca.heure_semaine
                            FROM cours_annee ca
                            JOIN cours c ON c.id_cours = ca.cours_id
                            WHERE ca.id_cours_annee = %s
                        """, [cours_annee_id])
                        cr = hub_cur.fetchone()
                        if cr:
                            cours_nom = cr['cours']
                            code_cours = cr['code_cours'] or ''
                            ponderation = cr['ponderation'] or 0
                            heure_semaine = cr['heure_semaine'] or 0
                    except Exception:
                        pass

                    # Class & cycle info from Hub
                    try:
                        hub_cur.execute("""
                            SELECT cl.nom AS classe_nom, cy.nom AS cycle_nom, eac.groupe
                            FROM etablissements_annees_classes eac
                            JOIN classes cl ON cl.id_classe = eac.classe_id
                            LEFT JOIN cycles cy ON cy.id_cycle = cl.cycle_id
                            WHERE eac.id = %s
                        """, [classe_id])
                        cl = hub_cur.fetchone()
                        if cl:
                            grp = cl.get('groupe') or ''
                            classe_nom = cl['classe_nom'] + (f' {grp}' if grp else '')
                            cycle_nom = cl['cycle_nom'] or '-'
                    except Exception:
                        pass

                # Count students in this class (Spoke)
                n_eleves = 0
                try:
                    cur.execute("""
                        SELECT COUNT(*) as n FROM eleve_inscription
                        WHERE id_classe_id = %s AND status = 1 AND id_etablissement = %s
                    """, [classe_id, etab_id])
                    r = cur.fetchone()
                    n_eleves = r['n'] if r else 0
                except Exception:
                    pass

                courses.append({
                    'id_attribution': att['id_attribution'],
                    'id_cours_annee': cours_annee_id,
                    'cours': cours_nom,
                    'code_cours': code_cours,
                    'ponderation': ponderation,
                    'heure_semaine': heure_semaine,
                    'classe_nom': classe_nom,
                    'cycle_nom': cycle_nom,
                    'eac_id': classe_id,
                    'n_eleves': n_eleves,
                })

            if hub_cur:
                hub_cur.close()
            if hub_conn:
                hub_conn.close()

            # 2. Horaire (enrichi avec noms de cours/classe)
            schedule = []
            # Build lookup for course/class names
            cours_lookup = {}
            for c in courses:
                key = f"{c['id_cours_annee']}_{c['eac_id']}"
                cours_lookup[key] = {'cours': c['cours'], 'code_cours': c['code_cours'], 'classe_nom': c['classe_nom'], 'cycle_nom': c['cycle_nom']}
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
                    lookup_key = f"{row['id_cours_id']}_{row['id_classe_id']}"
                    info = cours_lookup.get(lookup_key, {})
                    schedule.append({
                        'id': row['id_horaire'],
                        'date': str(row['date']),
                        'debut': row['debut'],
                        'fin': row['fin'],
                        'cours_nom': info.get('cours', ''),
                        'classe_nom': info.get('classe_nom', ''),
                        'code_cours': info.get('code_cours', ''),
                        'id_cours_id': row['id_cours_id'],
                        'id_classe_id': row['id_classe_id'],
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
                        'total_seances': int(row['seances'] or 0),
                        'total_presents': int(row['presents'] or 0),
                        'total_absents': int(row['absents'] or 0),
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
                        SELECT COUNT(*) as n FROM evaluation
                        WHERE id_cours_classe_id IN ({placeholders}) AND id_etablissement = %s
                    """, attr_cours_ids + [etab_id])
                    r = cur.fetchone()
                    n_evaluations = r['n'] if r else 0
            except Exception:
                pass

        conn.close()

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
        conn.close()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@login_required(login_url='login')
def api_enseignant_presences(request):
    """API Présences enseignant: GET = charger élèves+présences, POST = sauvegarder."""
    import pymysql
    etab_id = _get_etab_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)
    db_settings = connections['default'].settings_dict
    conn = pymysql.connect(
        host=db_settings.get('HOST', 'localhost') or 'localhost',
        user=db_settings['USER'], password=db_settings['PASSWORD'],
        port=int(db_settings.get('PORT', 3306) or 3306),
        database=db_settings['NAME'], charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        if request.method == 'GET':
            horaire_id = request.GET.get('horaire_id')
            if not horaire_id:
                conn.close()
                return JsonResponse({'success': False, 'error': 'horaire_id requis'}, status=400)
            with conn.cursor() as cur:
                cur.execute("SELECT id_horaire, date, debut, fin, id_cours_id, id_classe_id FROM horaire WHERE id_horaire=%s", [horaire_id])
                horaire = cur.fetchone()
                if not horaire:
                    conn.close()
                    return JsonResponse({'success': False, 'error': 'Horaire non trouvé'}, status=404)
                cur.execute("""
                    SELECT DISTINCT e.id_eleve, e.nom, e.prenom, e.genre
                    FROM eleve_inscription ei JOIN eleve e ON e.id_eleve=ei.id_eleve_id
                    WHERE ei.id_classe_id=%s AND ei.status=1 AND ei.id_etablissement=%s
                    ORDER BY e.nom, e.prenom
                """, [horaire['id_classe_id'], etab_id])
                eleves = cur.fetchall()
                # Ensure comportement_note column exists
                try:
                    cur.execute("ALTER TABLE horaire_presence ADD COLUMN comportement_note TINYINT DEFAULT NULL")
                    conn.commit()
                except Exception:
                    conn.rollback()
                cur.execute("SELECT id_horaire_presence, id_eleve_id, present_ou_absent, si_absent_motif, comportement_note FROM horaire_presence WHERE id_horaire_id=%s", [horaire_id])
                presences = {}
                for p in cur.fetchall():
                    presences[str(p['id_eleve_id'])] = {
                        'id': p['id_horaire_presence'], 'present': bool(p['present_ou_absent']),
                        'motif': p['si_absent_motif'] or '', 'comportement': p.get('comportement_note') or 5,
                    }
            conn.close()
            return JsonResponse({
                'success': True,
                'horaire': {'id': horaire['id_horaire'], 'date': str(horaire['date']), 'debut': horaire['debut'], 'fin': horaire['fin']},
                'eleves': [{'id': e['id_eleve'], 'nom': e['nom'] or '', 'prenom': e['prenom'] or '', 'genre': e['genre'] or ''} for e in eleves],
                'presences': presences,
            })
        else:
            data = json.loads(request.body)
            horaire_id = data.get('horaire_id')
            records = data.get('records', [])
            if not horaire_id:
                conn.close()
                return JsonResponse({'success': False, 'error': 'horaire_id requis'}, status=400)
            with conn.cursor() as cur:
                try:
                    cur.execute("ALTER TABLE horaire_presence ADD COLUMN comportement_note TINYINT DEFAULT NULL")
                    conn.commit()
                except Exception:
                    conn.rollback()
                cur.execute("SELECT date FROM horaire WHERE id_horaire=%s", [horaire_id])
                h_date = (cur.fetchone() or {}).get('date')
                for rec in records:
                    eid, pres = rec['id_eleve'], (1 if rec.get('present') else 0)
                    motif, comp = rec.get('motif') or None, rec.get('comportement', 0) or 0
                    cur.execute("SELECT id_horaire_presence FROM horaire_presence WHERE id_horaire_id=%s AND id_eleve_id=%s", [horaire_id, eid])
                    ex = cur.fetchone()
                    if ex:
                        cur.execute("UPDATE horaire_presence SET present_ou_absent=%s, si_absent_motif=%s, comportement_note=%s WHERE id_horaire_presence=%s", [pres, motif, comp, ex['id_horaire_presence']])
                    else:
                        cur.execute("INSERT INTO horaire_presence (id_horaire_id,id_eleve_id,present_ou_absent,date_presence,si_absent_motif,id_etablissement,comportement_note) VALUES (%s,%s,%s,%s,%s,%s,%s)", [horaire_id, eid, pres, h_date, motif, etab_id, comp])
                conn.commit()
            conn.close()
            return JsonResponse({'success': True, 'saved': len(records)})
    except Exception as e:
        import traceback; traceback.print_exc()
        conn.close()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
@login_required(login_url='login')
def api_enseignant_presences(request):
    """API Presences enseignant: GET = charger eleves+presences, POST = sauvegarder."""
    import pymysql
    etab_id = _get_etab_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Etablissement non trouve'}, status=400)
    db_settings = connections['default'].settings_dict
    conn = pymysql.connect(
        host=db_settings.get('HOST', 'localhost') or 'localhost',
        user=db_settings['USER'], password=db_settings['PASSWORD'],
        port=int(db_settings.get('PORT', 3306) or 3306),
        database=db_settings['NAME'], charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        if request.method == 'GET':
            horaire_id = request.GET.get('horaire_id')
            if not horaire_id:
                conn.close()
                return JsonResponse({'success': False, 'error': 'horaire_id requis'}, status=400)
            with conn.cursor() as cur:
                cur.execute("SELECT id_horaire, date, debut, fin, id_cours_id, id_classe_id FROM horaire WHERE id_horaire=%s", [horaire_id])
                horaire = cur.fetchone()
                if not horaire:
                    conn.close()
                    return JsonResponse({'success': False, 'error': 'Horaire non trouve'}, status=404)
                cur.execute("""
                    SELECT DISTINCT e.id_eleve, e.nom, e.prenom, e.genre
                    FROM eleve_inscription ei JOIN eleve e ON e.id_eleve=ei.id_eleve_id
                    WHERE ei.id_classe_id=%s AND ei.status=1 AND ei.id_etablissement=%s
                    ORDER BY e.nom, e.prenom
                """, [horaire['id_classe_id'], etab_id])
                eleves = cur.fetchall()
                cur.execute("SELECT id_horaire_presence, id_eleve_id, present_ou_absent, si_absent_motif, comportement_note FROM horaire_presence WHERE id_horaire_id=%s", [horaire_id])
                presences = {}
                for p in cur.fetchall():
                    presences[str(p['id_eleve_id'])] = {
                        'id': p['id_horaire_presence'], 'present': bool(p['present_ou_absent']),
                        'motif': p['si_absent_motif'] or '', 'comportement': p.get('comportement_note') or 0,
                    }
            conn.close()
            return JsonResponse({
                'success': True,
                'horaire': {'id': horaire['id_horaire'], 'date': str(horaire['date']), 'debut': horaire['debut'], 'fin': horaire['fin']},
                'eleves': [{'id': e['id_eleve'], 'nom': e['nom'] or '', 'prenom': e['prenom'] or '', 'genre': e['genre'] or ''} for e in eleves],
                'presences': presences,
            })
        else:
            data = json.loads(request.body)
            horaire_id = data.get('horaire_id')
            records = data.get('records', [])
            if not horaire_id:
                conn.close()
                return JsonResponse({'success': False, 'error': 'horaire_id requis'}, status=400)
            with conn.cursor() as cur:
                try:
                    cur.execute("ALTER TABLE horaire_presence ADD COLUMN comportement_note TINYINT DEFAULT NULL")
                    conn.commit()
                except Exception:
                    conn.rollback()
                cur.execute("SELECT date FROM horaire WHERE id_horaire=%s", [horaire_id])
                h_date = (cur.fetchone() or {}).get('date')
                for rec in records:
                    eid, pres = rec['id_eleve'], (1 if rec.get('present') else 0)
                    motif, comp = rec.get('motif') or None, rec.get('comportement', 0) or 0
                    cur.execute("SELECT id_horaire_presence FROM horaire_presence WHERE id_horaire_id=%s AND id_eleve_id=%s", [horaire_id, eid])
                    ex = cur.fetchone()
                    if ex:
                        cur.execute("UPDATE horaire_presence SET present_ou_absent=%s, si_absent_motif=%s, comportement_note=%s WHERE id_horaire_presence=%s", [pres, motif, comp, ex['id_horaire_presence']])
                    else:
                        cur.execute("INSERT INTO horaire_presence (id_horaire_id,id_eleve_id,present_ou_absent,date_presence,si_absent_motif,id_etablissement,comportement_note) VALUES (%s,%s,%s,%s,%s,%s,%s)", [horaire_id, eid, pres, h_date, motif, etab_id, comp])
                conn.commit()
            conn.close()
            return JsonResponse({'success': True, 'saved': len(records)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        conn.close()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================
# COMMUNICATION API
# ============================================================

@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_messages(request):
    """
    GET /api/enseignant/communication/?thread_id=...
    Renvoie les messages d'un thread de conversation.
    """
    from MonEcole_app.models.communication import Communication
    etab_id = _get_etab_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    thread_id = request.GET.get('thread_id', '')
    if not thread_id:
        return JsonResponse({'success': False, 'error': 'thread_id requis'}, status=400)

    messages = Communication.objects.filter(
        id_etablissement=etab_id,
        thread_id=thread_id
    ).order_by('created_at').values(
        'id_communication', 'sender_name', 'sender_personnel_id', 'sender_eleve_id',
        'scope', 'direction', 'message', 'subject',
        'status', 'is_read', 'created_at'
    )

    msgs_list = []
    for m in messages:
        msgs_list.append({
            'id': m['id_communication'],
            'sender_name': m['sender_name'],
            'sender_personnel_id': m['sender_personnel_id'],
            'sender_eleve_id': m['sender_eleve_id'],
            'scope': m['scope'],
            'direction': m['direction'],
            'message': m['message'],
            'subject': m['subject'],
            'status': m['status'],
            'is_read': m['is_read'],
            'created_at': m['created_at'].strftime('%Y-%m-%d %H:%M:%S') if m['created_at'] else '',
            'time': m['created_at'].strftime('%H:%M') if m['created_at'] else '',
        })

    # Mark incoming messages as read
    Communication.objects.filter(
        id_etablissement=etab_id,
        thread_id=thread_id,
        direction='in',
        is_read=False
    ).update(is_read=True, read_at=__import__('django.utils.timezone', fromlist=['now']).now())

    return JsonResponse({'success': True, 'messages': msgs_list})


@require_http_methods(["POST"])
@login_required(login_url='login')
def api_communication_send(request):
    """
    POST /api/enseignant/communication/send/
    Envoie un message depuis l'enseignant.
    Body JSON: { thread_id, scope, target_eleve_id?, target_classe_id?, message }
    """
    from MonEcole_app.models.communication import Communication
    from MonEcole_app.models.personnel import Personnel

    etab_id = _get_etab_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)

    message_text = (data.get('message') or '').strip()
    if not message_text:
        return JsonResponse({'success': False, 'error': 'Message vide'}, status=400)

    thread_id = data.get('thread_id', '')
    scope = data.get('scope', 'individual')
    target_eleve_id = data.get('target_eleve_id')
    target_classe_id = data.get('target_classe_id')
    target_personnel_id = data.get('target_personnel_id')
    subject = data.get('subject', '')

    # Identifier l'enseignant
    pers_id = request.session.get('personnel_id')
    pers = Personnel.objects.filter(id_personnel=pers_id, id_etablissement=etab_id).first() if pers_id else None
    if not pers:
        # Fallback: chercher par email
        try:
            from django.db import connections
            with connections['default'].cursor() as cur:
                cur.execute(
                    "SELECT id_personnel, CONCAT(COALESCE(nom,''), ' ', COALESCE(prenom,'')) as full_name FROM personnel WHERE id_personnel = %s AND id_etablissement = %s LIMIT 1",
                    [pers_id, etab_id]
                )
                row = cur.fetchone()
                sender_id = row[0] if row else None
                sender_name = (row[1] or '').strip() if row else request.user.get_full_name()
        except Exception:
            sender_id = None
            sender_name = request.user.get_full_name() or ''
    else:
        sender_id = pers.id_personnel
        sender_name = f"{pers.nom or ''} {pers.prenom or ''}".strip() or pers.matricule

    # Année active
    annee_id = None
    try:
        from MonEcole_app.models.country_structure import Etablissement as Etab, Pays as PaysModel
        from MonEcole_app.models.annee import Annee as AnneeModel
        etab_obj = Etab.objects.select_related('pays').filter(id_etablissement=etab_id).first()
        if etab_obj:
            annee_active = AnneeModel.objects.filter(
                pays_id=etab_obj.pays_id, etat_annee__in=['En Cours', 'actif']
            ).order_by('-annee').first()
            annee_id = annee_active.id_annee if annee_active else None
    except Exception:
        pass

    comm = Communication.objects.create(
        id_etablissement=etab_id,
        id_annee=annee_id,
        sender_personnel_id=sender_id,
        sender_name=sender_name,
        scope=scope,
        direction='out',
        target_eleve_id=target_eleve_id if target_eleve_id else None,
        target_classe_id=target_classe_id if target_classe_id else None,
        target_personnel_id=target_personnel_id if target_personnel_id else None,
        subject=subject,
        message=message_text,
        thread_id=thread_id,
        status='sent',
    )

    # ── Envoi d'email aux parents via Brevo ──
    email_result = {'sent': 0, 'failed': 0, 'errors': []}
    try:
        from MonEcole_app.email_service import send_brevo_email, build_parent_email_html
        import pymysql

        # Récupérer le nom de l'école
        school_name = 'MonEcole'
        try:
            etab_obj2 = Etab.objects.filter(id_etablissement=etab_id).first()
            if etab_obj2:
                school_name = etab_obj2.nom or school_name
        except Exception:
            pass

        # Collecter les emails parents
        parent_emails = []
        db_settings = connections['default'].settings_dict
        conn = pymysql.connect(
            host=db_settings.get('HOST', 'localhost') or 'localhost',
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            port=int(db_settings.get('PORT', 3306) or 3306),
            database=db_settings['NAME'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )

        with conn.cursor() as cur:
            if scope == 'individual' and target_eleve_id:
                # Email du parent d'un élève spécifique
                cur.execute(
                    "SELECT email_parent, nom, prenom FROM eleve WHERE id_eleve = %s AND email_parent IS NOT NULL AND email_parent != ''",
                    [target_eleve_id]
                )
                rows = cur.fetchall()
                for r in rows:
                    parent_emails.append({
                        'email': r['email_parent'],
                        'name': f"Parent de {r['nom'] or ''} {r['prenom'] or ''}".strip()
                    })

            elif scope == 'class' and target_classe_id:
                # Emails de tous les parents d'une classe
                cur.execute("""
                    SELECT DISTINCT e.email_parent, e.nom, e.prenom
                    FROM eleve_inscription ei
                    JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                    WHERE ei.id_classe_id = %s
                      AND ei.status = 1
                      AND ei.id_etablissement = %s
                      AND e.email_parent IS NOT NULL
                      AND e.email_parent != ''
                """, [target_classe_id, etab_id])
                rows = cur.fetchall()
                for r in rows:
                    parent_emails.append({
                        'email': r['email_parent'],
                        'name': f"Parent de {r['nom'] or ''} {r['prenom'] or ''}".strip()
                    })

            elif scope == 'etab':
                # Tous les parents de l'établissement
                cur.execute("""
                    SELECT DISTINCT e.email_parent, e.nom, e.prenom
                    FROM eleve_inscription ei
                    JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                    WHERE ei.status = 1
                      AND ei.id_etablissement = %s
                      AND e.email_parent IS NOT NULL
                      AND e.email_parent != ''
                """, [etab_id])
                rows = cur.fetchall()
                for r in rows:
                    parent_emails.append({
                        'email': r['email_parent'],
                        'name': f"Parent de {r['nom'] or ''} {r['prenom'] or ''}".strip()
                    })

        conn.close()

        # Envoyer si des emails trouvés
        if parent_emails:
            email_subject = subject or f"Communication de {sender_name}"
            html_body = build_parent_email_html(sender_name, message_text, school_name)
            email_result = send_brevo_email(
                to_emails=parent_emails,
                subject=email_subject,
                html_content=html_body,
                text_content=message_text,
                from_name=school_name,
                fail_silently=True,
            )
            # Mettre à jour le statut du message
            if email_result.get('sent', 0) > 0:
                comm.status = 'delivered'
                comm.save(update_fields=['status'])
        else:
            email_result['errors'].append('Aucun email parent trouvé')

    except Exception as e:
        import traceback
        traceback.print_exc()
        email_result['errors'].append(str(e))

    return JsonResponse({
        'success': True,
        'message': {
            'id': comm.id_communication,
            'sender_name': comm.sender_name,
            'direction': comm.direction,
            'message': comm.message,
            'time': comm.created_at.strftime('%H:%M') if comm.created_at else '',
            'created_at': comm.created_at.strftime('%Y-%m-%d %H:%M:%S') if comm.created_at else '',
        },
        'email': {
            'sent': email_result.get('sent', 0),
            'failed': email_result.get('failed', 0),
            'total_parents': len(parent_emails) if 'parent_emails' in dir() else 0,
            'errors': email_result.get('errors', []),
        }
    })


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_threads(request):
    """
    GET /api/enseignant/communication/threads/
    Renvoie la liste des threads avec le dernier message de chacun.
    """
    from MonEcole_app.models.communication import Communication
    from django.db.models import Max, Count, Q

    etab_id = _get_etab_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    # Get distinct threads with their latest message timestamp
    threads = Communication.objects.filter(
        id_etablissement=etab_id
    ).values('thread_id').annotate(
        last_msg=Max('created_at'),
        msg_count=Count('id_communication'),
        unread=Count('id_communication', filter=Q(direction='in', is_read=False))
    ).order_by('-last_msg')

    thread_list = []
    for t in threads:
        # Get the last message for preview
        last_comm = Communication.objects.filter(
            id_etablissement=etab_id,
            thread_id=t['thread_id']
        ).order_by('-created_at').first()

        thread_list.append({
            'thread_id': t['thread_id'],
            'last_message': last_comm.message[:60] if last_comm else '',
            'last_sender': last_comm.sender_name if last_comm else '',
            'last_direction': last_comm.direction if last_comm else '',
            'last_time': last_comm.created_at.strftime('%H:%M') if last_comm and last_comm.created_at else '',
            'last_date': last_comm.created_at.strftime('%d/%m') if last_comm and last_comm.created_at else '',
            'msg_count': t['msg_count'],
            'unread': t['unread'],
        })

    return JsonResponse({'success': True, 'threads': thread_list})


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_teachers(request):
    """
    GET /api/enseignant/communication/teachers/
    Renvoie la liste des enseignants collègues du même établissement.
    """
    from django.db import connections

    etab_id = _get_etab_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    teachers = []
    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT p.id_personnel,
                       CONCAT(COALESCE(p.nom,''), ' ', COALESCE(p.prenom,'')) as nom_complet,
                       p.email
                FROM personnel p
                WHERE p.id_etablissement = %s
                  AND p.id_personnel != %s
                ORDER BY p.nom, p.prenom
            """, [etab_id, request.user.id_personnel])
            for row in cur.fetchall():
                nm = (row[1] or '').strip()
                if nm:
                    teachers.append({
                        'id_personnel': row[0],
                        'nom_complet': nm,
                        'email': row[2] or '',
                    })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'teachers': teachers})

