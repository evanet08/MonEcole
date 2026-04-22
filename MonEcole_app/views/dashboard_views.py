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

    # Récupérer l'établissement depuis le Hub (filtré par pays)
    id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')
    try:
        etab_qs = Etablissement.objects.select_related(
            'pays', 'structure_pedagogique', 'gestionnaire'
        )
        if id_pays:
            etab = etab_qs.filter(id_etablissement=etab_id, pays_id=id_pays).first()
        else:
            etab = etab_qs.filter(id_etablissement=etab_id).first()
        if not etab:
            return None
    except Exception:
        return None

    pays = etab.pays

    active_section = request.GET.get('section', 'dashboard')

    # --- Année scolaire active ---
    # isOpen = True (1) si l'année est en cours, False (0) sinon
    annee_active = Annee.objects.filter(
        pays_id=pays.id_pays, isOpen=True
    ).order_by('-annee').first()
    if not annee_active:
        annee_active = Annee.objects.filter(
            pays_id=pays.id_pays
        ).order_by('-annee').first()

    annees_raw = Annee.objects.filter(
        pays_id=pays.id_pays
    ).order_by('-annee').values('id_annee', 'annee', 'isOpen')
    annees_list = [{'id_annee': a['id_annee'], 'annee': a['annee'], 'isOpen': a['isOpen']} for a in annees_raw]

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
            etablissement=etab, annee=annee_active, id_pays=pays.id_pays
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
                    cycle_id__in=active_cycle_ids, is_active=True, id_pays=pays.id_pays
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
            for h in RepartitionHierarchie.objects.filter(is_active=True, id_pays=pays.id_pays).select_related('type_parent', 'type_enfant'):
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

                # Build parent mapping: child instance → parent instance
                # Using type hierarchy + instance ordering
                parent_instances_by_type = {}  # parent_type_id → [instances ordered]
                child_to_parent_type = {}      # child_type_id → (parent_type_id, nb_enfants)
                for ptid, info in hierarchies_for_types.items():
                    child_to_parent_type[info['child_type_id']] = (ptid, info['nb_enfants'])

                all_instances = list(ri_qs)

                # Group instances by type
                instances_by_type = {}
                for ri in all_instances:
                    instances_by_type.setdefault(ri.type_id, []).append(ri)

                # Build child→parent instance mapping
                child_parent_map = {}  # child_instance_id → parent_instance
                for child_type_id, (parent_type_id, nb_enfants) in child_to_parent_type.items():
                    parent_insts = instances_by_type.get(parent_type_id, [])
                    child_insts = instances_by_type.get(child_type_id, [])
                    if parent_insts and child_insts:
                        # Distribute children evenly across parents
                        for ci, child in enumerate(child_insts):
                            parent_idx = ci // nb_enfants if nb_enfants > 0 else 0
                            if parent_idx < len(parent_insts):
                                child_parent_map[child.id_instance] = parent_insts[parent_idx]

                # Grouper par type et limiter par le nombre calculé
                type_count_tracker = {}  # type_id → nombre ajouté
                for ri in all_instances:
                    tid = ri.type_id
                    current_count = type_count_tracker.get(tid, 0)
                    max_allowed = type_instance_limits.get(tid)
                    # Si pas de limite (type non configuré), skip
                    if max_allowed is not None and current_count >= max_allowed:
                        continue
                    type_count_tracker[tid] = current_count + 1
                    parent_inst = child_parent_map.get(ri.id_instance)
                    repartitions_notes.append({
                        'id': ri.id_instance, 'id_instance': ri.id_instance,
                        'nom': ri.nom, 'code': ri.code,
                        'type': ri.type.nom if ri.type else '',
                        'type_code': ri.type.code if ri.type else '',
                        'ordre': ri.ordre, 'is_open': ri.is_active,
                        'is_leaf': ri.type_id not in parent_type_ids,
                        'parent_instance_id': parent_inst.id_instance if parent_inst else None,
                        'parent_nom': parent_inst.nom if parent_inst else None,
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
                    'repartition__type_id',
                    'repartition__ordre', 'debut', 'fin', 'is_open'
                )
                stats['n_trimestres_ouverts'] = sum(1 for r in repartitions_raw if r.get('is_open'))

                # Build parent mapping for non-synched path too
                reps_list = list(repartitions_raw)
                child_to_parent_type_ns = {}
                for ptid, info in hierarchies_for_types.items():
                    child_to_parent_type_ns[info['child_type_id']] = (ptid, info['nb_enfants'])

                instances_by_type_ns = {}
                for rc in reps_list:
                    tid = rc.get('repartition__type_id')
                    instances_by_type_ns.setdefault(tid, []).append(rc)

                child_parent_map_ns = {}
                for child_tid, (parent_tid, nb_enf) in child_to_parent_type_ns.items():
                    p_insts = instances_by_type_ns.get(parent_tid, [])
                    c_insts = instances_by_type_ns.get(child_tid, [])
                    if p_insts and c_insts:
                        for ci, child_rc in enumerate(c_insts):
                            pi = ci // nb_enf if nb_enf > 0 else 0
                            if pi < len(p_insts):
                                child_parent_map_ns[child_rc.get('repartition__id_instance')] = p_insts[pi]

                for rc in reps_list:
                    type_code = rc.get('repartition__type__code', '')
                    type_id = rc.get('repartition__type_id')
                    parent_rc = child_parent_map_ns.get(rc.get('repartition__id_instance'))
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
                        'parent_instance_id': parent_rc.get('repartition__id_instance') if parent_rc else None,
                        'parent_nom': parent_rc.get('repartition__nom') if parent_rc else None,
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
            # Elèves — filtrer par établissement (DISTINCT pour éviter doublons)
            cur.execute("""
                SELECT COUNT(DISTINCT ei.id_eleve_id) as total,
                       COUNT(DISTINCT CASE WHEN e.genre='M' THEN ei.id_eleve_id END) as garcons,
                       COUNT(DISTINCT CASE WHEN e.genre='F' THEN ei.id_eleve_id END) as filles
                FROM eleve_inscription ei
                JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                WHERE ei.status = 1 AND ei.id_etablissement = %s AND ei.id_pays = %s
            """, [etab_id, pays.id_pays])
            row = cur.fetchone()
            if row:
                eleves_stats['total'] = int(row[0] or 0)
                eleves_stats['garcons'] = int(row[1] or 0)
                eleves_stats['filles'] = int(row[2] or 0)

            # Age distribution
            cur.execute("""
                SELECT TIMESTAMPDIFF(YEAR, e.date_naissance, CURDATE()) as age, COUNT(DISTINCT ei.id_eleve_id) as nb
                FROM eleve_inscription ei
                JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                WHERE ei.status = 1 AND ei.id_etablissement = %s AND ei.id_pays = %s AND e.date_naissance IS NOT NULL AND e.date_naissance != '0000-00-00'
                GROUP BY age ORDER BY age
            """, [etab_id, pays.id_pays])
            eleves_stats['age_distribution'] = [
                {'tranche': f"{int(r[0])} ans", 'nb': int(r[1])} for r in cur.fetchall()
            ]

            # Elèves par classe (cross-DB via clés métier + COLLATE)
            cur.execute("""
                SELECT eac.id as eac_id, COUNT(DISTINCT ei.id_eleve_id) as total,
                       COUNT(DISTINCT CASE WHEN e.genre='M' THEN ei.id_eleve_id END) as garcons,
                       COUNT(DISTINCT CASE WHEN e.genre='F' THEN ei.id_eleve_id END) as filles
                FROM eleve_inscription ei
                JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                JOIN countryStructure.etablissements_annees_classes eac
                  ON eac.classe_id = ei.classe_id
                  AND (eac.groupe COLLATE utf8mb4_general_ci <=> ei.groupe COLLATE utf8mb4_general_ci)
                  AND eac.section_id <=> ei.section_id
                  AND eac.etablissement_annee_id = %s
                WHERE ei.status = 1 AND ei.id_etablissement = %s AND ei.id_pays = %s
                GROUP BY eac.id
            """, [etab_annee.id if etab_annee else 0, etab_id, pays.id_pays])
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
                JOIN campus c ON c.idCampus = ei.idCampus_id
                WHERE ei.status = 1 AND ei.id_etablissement = %s AND ei.id_pays = %s
                GROUP BY c.idCampus, c.campus ORDER BY total DESC
            """, [etab_id, pays.id_pays])
            eleves_par_campus = [
                {'campus_nom': r[0], 'total': int(r[1])} for r in cur.fetchall()
            ]

            # Enseignants — filtrer par établissement
            cur.execute("SELECT COUNT(*) FROM personnel WHERE en_fonction = 1 AND id_etablissement = %s AND id_pays = %s", [etab_id, pays.id_pays])
            row = cur.fetchone()
            stats['n_enseignants'] = int(row[0]) if row else 0

    except Exception:
        import traceback
        traceback.print_exc()

    stats['n_eleves'] = eleves_stats.get('total', 0)
    stats['n_garcons'] = eleves_stats.get('garcons', 0)
    stats['n_filles'] = eleves_stats.get('filles', 0)

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
            'isOpen': annee_active.isOpen,
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
                        JOIN classes cl ON cl.id = eac.classe_id
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


# ============================================================
# COMMUNICATION — Module standalone (accessible à tous)
# ============================================================

@login_required(login_url='login')
def communication_view(request):
    """Page Communication — Module standalone accessible à tout utilisateur connecté."""
    context = _get_dashboard_context(request)
    if context is None:
        return render(request, 'dashboard/no_tenant.html')

    context['active_page'] = 'communication'
    _add_module_context(context, request, 'communication')

    # Identifier le personnel connecté (même logique que espace_enseignant)
    etab_id = context['etab']['id_etablissement']
    personnel_id = None
    personnel_info = {}

    try:
        from MonEcole_app.models.personnel import Personnel
        pers_id = request.session.get('personnel_id')
        pers = None
        if pers_id:
            pers = Personnel.objects.filter(
                id_personnel=pers_id, id_etablissement=etab_id
            ).first()

        if not pers and request.user.email:
            try:
                pers = Personnel.objects.filter(
                    email__iexact=request.user.email, id_etablissement=etab_id
                ).first()
            except Exception:
                pass

        if pers:
            personnel_id = pers.id_personnel
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

    return render(request, 'dashboard/communication.html', context)

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

            # etab_annee_id will be resolved after hub connection is established
            etab_annee_id = None

            cur.execute("""
                SELECT ac.id_attribution, ac.id_cours_id, ac.classe_id,
                       ac.groupe, ac.section_id,
                       ac.id_cycle_id, ac.idCampus_id, ac.date_attribution
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

            # Resolve etab_annee_id via direct SQL on Hub
            if hub_cur:
                try:
                    hub_cur.execute("""
                        SELECT ea.id FROM etablissements_annees ea
                        JOIN annees a ON a.id = ea.annee_id
                        WHERE ea.etablissement_id = %s
                          AND a.isOpen = 1
                        ORDER BY a.annee DESC LIMIT 1
                    """, [etab_id])
                    ea_row = hub_cur.fetchone()
                    if ea_row:
                        etab_annee_id = ea_row['id']
                    print(f"[api_enseignant_dashboard] etab_annee_id resolved via SQL: {etab_annee_id}", file=sys.stderr, flush=True)
                except Exception as e:
                    print(f"[api_enseignant_dashboard] etab_annee_id resolution error: {e}", file=sys.stderr, flush=True)

            for att in attributions:
                cours_annee_id = att['id_cours_id']
                classe_id = att['classe_id']

                cours_nom = f"Cours #{cours_annee_id}"
                code_cours = ''
                maxima_exam = 0
                heure_semaine = 0
                classe_nom = f"Classe #{classe_id}"
                cycle_nom = '-'
                real_eac_id = None  # Will be resolved from Hub

                # Course info from Hub
                if hub_cur:
                    try:
                        hub_cur.execute("""
                            SELECT c.cours, c.code_cours, ca.maxima_exam, ca.heure_semaine
                            FROM cours_annee ca
                            JOIN cours c ON c.id = ca.cours_id
                            WHERE ca.id_cours_annee = %s
                        """, [cours_annee_id])
                        cr = hub_cur.fetchone()
                        if cr:
                            cours_nom = cr['cours']
                            code_cours = cr['code_cours'] or ''
                            maxima_exam = cr['maxima_exam'] or 0
                            heure_semaine = cr['heure_semaine'] or 0
                    except Exception:
                        pass

                    # Class & cycle info from Hub (classe_id is now Hub Classe.id_classe)
                    try:
                        hub_cur.execute("""
                            SELECT cl.nom AS classe_nom, cy.nom AS cycle_nom
                            FROM classes cl
                            LEFT JOIN cycles cy ON cy.id = cl.cycle_id
                            WHERE cl.id_classe = %s
                        """, [classe_id])
                        cl = hub_cur.fetchone()
                        if cl:
                            grp = att.get('groupe') or ''
                            classe_nom = cl['classe_nom'] + (f' ({grp})' if grp else '')
                            cycle_nom = cl['cycle_nom'] or '-'
                    except Exception:
                        pass

                    # Resolve real eac_id (etablissements_annees_classes.id) from business keys
                    if etab_annee_id:
                        try:
                            hub_cur.execute("""
                                SELECT eac.id FROM etablissements_annees_classes eac
                                WHERE eac.classe_id = %s
                                  AND eac.groupe <=> %s
                                  AND eac.section_id <=> %s
                                  AND eac.etablissement_annee_id = %s
                                LIMIT 1
                            """, [classe_id, att.get('groupe'), att.get('section_id'), etab_annee_id])
                            eac_row = hub_cur.fetchone()
                            if eac_row:
                                real_eac_id = eac_row['id']
                        except Exception:
                            pass

                # Count students in this class (Spoke via business keys, already in att)
                n_eleves = 0
                try:
                    cur.execute("""
                        SELECT COUNT(*) as n FROM eleve_inscription
                        WHERE classe_id = %s AND groupe <=> %s AND section_id <=> %s
                          AND status = 1 AND id_etablissement = %s
                    """, [classe_id, att.get('groupe'), att.get('section_id'), etab_id])
                    r = cur.fetchone()
                    n_eleves = r['n'] if r else 0
                except Exception:
                    pass

                courses.append({
                    'id_attribution': att['id_attribution'],
                    'id_cours_annee': cours_annee_id,
                    'cours': cours_nom,
                    'code_cours': code_cours,
                    'maxima_exam': maxima_exam,
                    'heure_semaine': heure_semaine,
                    'classe_nom': classe_nom,
                    'cycle_nom': cycle_nom,
                    'eac_id': real_eac_id or classe_id,
                    'n_eleves': n_eleves,
                })
                print(f"[api_enseignant_dashboard] course: classe_id={classe_id}, groupe={att.get('groupe')}, section_id={att.get('section_id')}, etab_annee_id={etab_annee_id}, real_eac_id={real_eac_id}, final_eac_id={real_eac_id or classe_id}", file=sys.stderr, flush=True)

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
                           h.id_cours_id, h.classe_id, h.groupe
                    FROM horaire h
                    JOIN attribution_cours ac ON ac.id_cours_id = h.id_cours_id
                        AND ac.classe_id = h.classe_id
                        AND ac.groupe <=> h.groupe AND ac.section_id <=> h.section_id
                    WHERE ac.id_personnel_id = %s AND ac.id_etablissement = %s
                    ORDER BY h.date DESC, h.debut
                    LIMIT 50
                """, [personnel_id, etab_id])
                for row in cur.fetchall():
                    lookup_key = f"{row['id_cours_id']}_{row['classe_id']}"
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
                        'id_classe_id': row['classe_id'],
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
                        AND ac.classe_id = h.classe_id
                        AND ac.groupe <=> h.groupe AND ac.section_id <=> h.section_id
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
            'n_classes': len(set(f"{c['eac_id']}_{c.get('groupe','')}" for c in courses)),
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
                cur.execute("SELECT id_horaire, date, debut, fin, id_cours_id, classe_id FROM horaire WHERE id_horaire=%s", [horaire_id])
                horaire = cur.fetchone()
                if not horaire:
                    conn.close()
                    return JsonResponse({'success': False, 'error': 'Horaire non trouvé'}, status=404)
                # Resolve EAC.id → business keys
                cur.execute("""
                    SELECT eac.classe_id, eac.groupe, eac.section_id
                    FROM countryStructure.etablissements_annees_classes eac WHERE eac.id = %s
                """, [horaire['classe_id']])
                bk = cur.fetchone()
                if bk:
                    cur.execute("""
                        SELECT DISTINCT e.id_eleve, e.nom, e.prenom, e.genre
                        FROM eleve_inscription ei JOIN eleve e ON e.id_eleve=ei.id_eleve_id
                        WHERE ei.classe_id=%s AND ei.groupe <=> %s AND ei.section_id <=> %s
                          AND ei.status=1 AND ei.id_etablissement=%s
                        ORDER BY e.nom, e.prenom
                    """, [bk['classe_id'], bk['groupe'], bk['section_id'], etab_id])
                    eleves = cur.fetchall()
                else:
                    eleves = []
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
                cur.execute("SELECT id_horaire, date, debut, fin, id_cours_id, classe_id, groupe, section_id FROM horaire WHERE id_horaire=%s", [horaire_id])
                horaire = cur.fetchone()
                if not horaire:
                    conn.close()
                    return JsonResponse({'success': False, 'error': 'Horaire non trouve'}, status=404)
                # Business keys are now directly in the horaire table
                cur.execute("""
                    SELECT DISTINCT e.id_eleve, e.nom, e.prenom, e.genre
                    FROM eleve_inscription ei JOIN eleve e ON e.id_eleve=ei.id_eleve_id
                    WHERE ei.classe_id=%s AND ei.groupe <=> %s AND ei.section_id <=> %s
                      AND ei.status=1 AND ei.id_etablissement=%s
                    ORDER BY e.nom, e.prenom
                """, [horaire['classe_id'], horaire['groupe'], horaire['section_id'], etab_id])
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
# COMMUNICATION API — Module standalone
# ============================================================

def _get_personnel_id(request):
    """Helper : renvoie (personnel_id, etab_id) depuis la session."""
    etab_id = _get_etab_id(request)
    pers_id = request.session.get('personnel_id')
    return pers_id, etab_id


def _get_sender_info(pers_id, etab_id):
    """Retourne (sender_id, sender_name) par SQL direct."""
    try:
        with connections['default'].cursor() as cur:
            cur.execute(
                "SELECT id_personnel, COALESCE(nom,''), COALESCE(postnom,''), COALESCE(prenom,'') "
                "FROM personnel WHERE id_personnel = %s AND id_etablissement = %s LIMIT 1",
                [pers_id, etab_id]
            )
            row = cur.fetchone()
            if row:
                name = f"{row[1]} {row[3]}".strip()
                return row[0], name or f"Personnel #{row[0]}"
    except Exception:
        pass
    return pers_id, ''


def _get_annee_id(etab_id):
    """Retourne l'id de l'année active."""
    try:
        from MonEcole_app.models.country_structure import Etablissement as Etab
        from MonEcole_app.models.annee import Annee as AnneeModel
        etab_obj = Etab.objects.select_related('pays').filter(id_etablissement=etab_id).first()
        if etab_obj:
            annee = AnneeModel.objects.filter(pays_id=etab_obj.pays_id, isOpen=True).order_by('-annee').first()
            return annee.id_annee if annee else None
    except Exception:
        pass
    return None


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_contacts(request):
    """
    GET /api/communication/contacts/
    Retourne TOUS les contacts organisés par catégorie en un seul appel.
    Catégories : direction, colleagues, classes (avec élèves), custom_groups.
    """
    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    result = {
        'colleagues': [],
        'classes': [],
        'custom_groups': [],
    }

    current_pers = int(pers_id) if pers_id else 0

    # ── 1. Tout le personnel en fonction, classé par type ──
    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT p.id_personnel, p.nom, p.postnom, p.prenom, p.email,
                       p.imageUrl, p.genre,
                       COALESCE(pt.type, 'Autre') as type_nom,
                       COALESCE(pt.sigle, '?') as type_sigle,
                       p.isDirecteur, p.isDAF, p.isMaitresse,
                       CASE WHEN ac_sub.cnt > 0 THEN 1 ELSE 0 END as is_teacher
                FROM personnel p
                LEFT JOIN personnel_type pt ON pt.id_type_personnel = p.id_personnel_type_id
                LEFT JOIN (
                    SELECT id_personnel_id, COUNT(*) as cnt
                    FROM attribution_cours
                    WHERE id_etablissement = %s
                    GROUP BY id_personnel_id
                ) ac_sub ON ac_sub.id_personnel_id = p.id_personnel
                WHERE p.id_etablissement = %s
                  AND p.en_fonction = 1
                  AND p.id_personnel != %s
                ORDER BY pt.type, p.nom, p.prenom
            """, [etab_id, etab_id, current_pers])
            types_seen = set()
            for row in cur.fetchall():
                nm = f"{row[1] or ''} {row[3] or ''}".strip()
                if nm:
                    type_nom = row[7] or 'Autre'
                    types_seen.add(type_nom)
                    result['colleagues'].append({
                        'id_personnel': row[0],
                        'nom': row[1] or '',
                        'postnom': row[2] or '',
                        'prenom': row[3] or '',
                        'email': row[4] or '',
                        'imageUrl': row[5] or '',
                        'genre': row[6] or 'M',
                        'type_nom': type_nom,
                        'type_sigle': row[8] or '?',
                        'isDirecteur': bool(row[9]),
                        'isDAF': bool(row[10]),
                        'isMaitresse': bool(row[11]),
                        'is_teacher': bool(row[12]),
                    })
            result['personnel_types'] = sorted(list(types_seen))
    except Exception as e:
        import traceback; traceback.print_exc()

    # ── 2. Classes de l'enseignant (via attribution_cours) + élèves ──
    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ac.classe_id, ac.groupe, ac.section_id,
                       eac.id as eac_id
                FROM attribution_cours ac
                JOIN countryStructure.etablissements_annees ea
                    ON ea.etablissement_id = ac.id_etablissement
                JOIN countryStructure.etablissements_annees_classes eac
                    ON eac.etablissement_annee_id = ea.id
                    AND eac.classe_id = ac.classe_id
                    AND (COALESCE(eac.groupe COLLATE utf8mb4_general_ci,'') = COALESCE(ac.groupe,''))
                    AND (COALESCE(eac.section_id,0) = COALESCE(ac.section_id,0))
                WHERE ac.id_personnel_id = %s AND ac.id_etablissement = %s
            """, [current_pers, etab_id])
            class_rows = cur.fetchall()

            for cr in class_rows:
                classe_id, groupe, section_id, eac_id = cr

                # Nom de la classe
                cur.execute("""
                    SELECT c.nom as classe_nom, cy.nom as cycle_nom
                    FROM countryStructure.classes c
                    LEFT JOIN countryStructure.cycles cy ON cy.id = c.cycle_id
                    WHERE c.id_classe = %s
                """, [classe_id])
                cls_row = cur.fetchone()
                classe_nom = cls_row[0] if cls_row else f"Classe #{classe_id}"
                cycle_nom = cls_row[1] if cls_row else ''
                full_name = f"{cycle_nom} — {classe_nom}" if cycle_nom else classe_nom
                if groupe:
                    full_name += f" ({groupe})"

                # Élèves inscrits dans cette classe
                cur.execute("""
                    SELECT e.id_eleve, e.nom, e.prenom, e.genre,
                           e.id_parent, e.telephone
                    FROM eleve_inscription ei
                    JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                    WHERE ei.classe_id = %s
                      AND (COALESCE(ei.groupe,'') = COALESCE(%s,''))
                      AND (COALESCE(ei.section_id,0) = COALESCE(%s,0))
                      AND ei.status = 1 AND ei.id_etablissement = %s
                    ORDER BY e.nom, e.prenom
                """, [classe_id, groupe, section_id, etab_id])
                students = []
                student_rows = cur.fetchall()
                for s in student_rows:
                    # Résoudre parent via id_parent -> table parents
                    parent_info = {}
                    if s[4]:  # id_parent
                        cur.execute("""
                            SELECT nomPere, prenomPere, telephonePere, emailPere,
                                   nomMere, prenomMere, telephoneMere, emailMere
                            FROM parents WHERE id_parent = %s
                        """, [s[4]])
                        prow = cur.fetchone()
                        if prow:
                            parent_info = {
                                'pere': {'nom': prow[0] or '', 'prenom': prow[1] or '',
                                         'tel': prow[2] or '', 'email': prow[3] or ''},
                                'mere': {'nom': prow[4] or '', 'prenom': prow[5] or '',
                                         'tel': prow[6] or '', 'email': prow[7] or ''},
                            }
                    students.append({
                        'id_eleve': s[0],
                        'nom': s[1] or '',
                        'prenom': s[2] or '',
                        'genre': s[3] or 'M',
                        'id_parent': s[4],
                        'telephone': s[5] or '',
                        'parent': parent_info,
                    })

                result['classes'].append({
                    'eac_id': eac_id,
                    'classe_nom': classe_nom,
                    'cycle_nom': cycle_nom,
                    'full_name': full_name,
                    'n_eleves': len(students),
                    'students': students,
                })
    except Exception as e:
        import traceback; traceback.print_exc()

    # ── 3. Groupes personnalisés ──
    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT g.id_group, g.name, g.description, g.avatar_color, g.created_by,
                       (SELECT COUNT(*) FROM communication_group_member WHERE id_group = g.id_group) as n_members
                FROM communication_group g
                WHERE g.id_etablissement = %s
                  AND (g.created_by = %s
                       OR EXISTS (SELECT 1 FROM communication_group_member gm
                                  WHERE gm.id_group = g.id_group AND gm.id_personnel = %s))
                ORDER BY g.name
            """, [etab_id, current_pers, current_pers])
            for gr in cur.fetchall():
                # Charger les membres
                cur.execute("""
                    SELECT gm.id_personnel, p.nom, p.prenom, p.email
                    FROM communication_group_member gm
                    JOIN personnel p ON p.id_personnel = gm.id_personnel
                    WHERE gm.id_group = %s
                    ORDER BY p.nom
                """, [gr[0]])
                members = [{'id_personnel': m[0], 'nom': f"{m[1] or ''} {m[2] or ''}".strip(), 'email': m[3] or ''} for m in cur.fetchall()]

                result['custom_groups'].append({
                    'id_group': gr[0],
                    'name': gr[1],
                    'description': gr[2] or '',
                    'avatar_color': gr[3] or '#128c7e',
                    'created_by': gr[4],
                    'is_owner': gr[4] == current_pers,
                    'n_members': gr[5],
                    'members': members,
                })
    except Exception as e:
        import traceback; traceback.print_exc()

    return JsonResponse({'success': True, 'personnel_id': pers_id, **result})


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_messages(request):
    """
    GET /api/communication/?thread_id=...
    Renvoie les messages d'un thread, avec direction relative à l'utilisateur courant.
    """
    from MonEcole_app.models.communication import Communication
    pers_id, etab_id = _get_personnel_id(request)
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
        'sender_parent_id', 'scope', 'direction', 'message', 'subject',
        'attachment_url', 'attachment_name', 'attachment_type',
        'status', 'is_read', 'created_at'
    )

    current_pers = int(pers_id) if pers_id else 0
    msgs_list = []
    for m in messages:
        # Direction relative : si c'est moi qui ai envoyé → 'out', sinon → 'in'
        relative_dir = 'out' if m['sender_personnel_id'] == current_pers else 'in'
        msg_data = {
            'id': m['id_communication'],
            'sender_name': m['sender_name'],
            'sender_personnel_id': m['sender_personnel_id'],
            'sender_eleve_id': m['sender_eleve_id'],
            'scope': m['scope'],
            'direction': relative_dir,
            'message': m['message'],
            'subject': m['subject'],
            'status': m['status'],
            'is_read': m['is_read'],
            'created_at': m['created_at'].strftime('%Y-%m-%d %H:%M:%S') if m['created_at'] else '',
            'time': m['created_at'].strftime('%H:%M') if m['created_at'] else '',
        }
        if m['attachment_url']:
            msg_data['attachment'] = {
                'url': m['attachment_url'],
                'name': m['attachment_name'] or '',
                'type': m['attachment_type'] or 'file',
            }
        msgs_list.append(msg_data)

    # Mark messages as read (ceux envoyés par d'autres)
    Communication.objects.filter(
        id_etablissement=etab_id,
        thread_id=thread_id,
        is_read=False
    ).exclude(
        sender_personnel_id=current_pers
    ).update(is_read=True, read_at=__import__('django.utils.timezone', fromlist=['now']).now())

    return JsonResponse({'success': True, 'messages': msgs_list})


@require_http_methods(["POST"])
@login_required(login_url='login')
def api_communication_send(request):
    """
    POST /api/communication/send/
    Envoie un message avec pièce jointe optionnelle.
    Accepte JSON ou FormData (multipart) pour les fichiers.
    """
    from MonEcole_app.models.communication import Communication
    import os

    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    # Accepter JSON ou FormData
    content_type = request.content_type or ''
    if 'multipart' in content_type:
        data = request.POST.dict()
        uploaded_file = request.FILES.get('attachment')
    else:
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)
        uploaded_file = None

    message_text = (data.get('message') or '').strip()
    if not message_text and not uploaded_file:
        return JsonResponse({'success': False, 'error': 'Message vide'}, status=400)
    if not message_text:
        message_text = '📎 Pièce jointe'

    thread_id = data.get('thread_id', '')
    scope = data.get('scope', 'individual')
    target_eleve_id = data.get('target_eleve_id') or None
    target_classe_id = data.get('target_classe_id') or None
    target_personnel_id = data.get('target_personnel_id') or None
    target_group_id = data.get('target_group_id') or None
    subject = data.get('subject', '')

    # Convertir les IDs string "null" en None
    def _clean_id(val):
        if val in ('null', 'None', '', '0', 0):
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None
    target_eleve_id = _clean_id(target_eleve_id)
    target_classe_id = _clean_id(target_classe_id)
    target_personnel_id = _clean_id(target_personnel_id)
    target_group_id = _clean_id(target_group_id)

    sender_id, sender_name = _get_sender_info(pers_id, etab_id)
    annee_id = _get_annee_id(etab_id)

    # Gérer l'upload du fichier
    attachment_url = None
    attachment_name = None
    attachment_type = None
    if uploaded_file:
        # Limiter la taille (10MB max)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'Fichier trop volumineux (max 10MB)'}, status=400)

        # Déterminer le type
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'):
            attachment_type = 'image'
        elif ext in ('.pdf',):
            attachment_type = 'pdf'
        elif ext in ('.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods'):
            attachment_type = 'document'
        else:
            attachment_type = 'file'

        # Sauvegarder dans media/communication/
        import time
        upload_dir = os.path.join('media', 'communication', str(etab_id))
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"{int(time.time())}_{uploaded_file.name.replace(' ', '_')}"
        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)
        attachment_url = f'/{file_path}'
        attachment_name = uploaded_file.name

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
        target_group_id=target_group_id if target_group_id else None,
        subject=subject,
        message=message_text,
        attachment_url=attachment_url,
        attachment_name=attachment_name,
        attachment_type=attachment_type,
        thread_id=thread_id,
        status='sent',
    )

    # ── Envoi d'email aux parents via Brevo ──
    email_result = {'sent': 0, 'failed': 0, 'errors': []}
    parent_emails = []
    try:
        from MonEcole_app.email_service import send_brevo_email, build_parent_email_html
        from MonEcole_app.models.country_structure import Etablissement as Etab

        school_name = 'MonEcole'
        try:
            etab_obj = Etab.objects.filter(id_etablissement=etab_id).first()
            if etab_obj:
                school_name = etab_obj.nom or school_name
        except Exception:
            pass

        # Résoudre les emails parents via id_parent (table parents)
        with connections['default'].cursor() as cur:
            if scope == 'individual' and target_eleve_id:
                cur.execute("""
                    SELECT e.nom, e.prenom,
                           p.emailPere, p.emailMere, p.nomPere, p.nomMere
                    FROM eleve e
                    LEFT JOIN parents p ON p.id_parent = e.id_parent
                    WHERE e.id_eleve = %s
                """, [target_eleve_id])
                row = cur.fetchone()
                if row:
                    eleve_name = f"{row[0] or ''} {row[1] or ''}".strip()
                    if row[2]:  # emailPere
                        parent_emails.append({'email': row[2], 'name': f"Père de {eleve_name}"})
                    if row[3]:  # emailMere
                        parent_emails.append({'email': row[3], 'name': f"Mère de {eleve_name}"})

            elif scope == 'class' and target_classe_id:
                # Résoudre classe EAC → business keys
                cur.execute("""
                    SELECT eac.classe_id, eac.groupe, eac.section_id
                    FROM countryStructure.etablissements_annees_classes eac WHERE eac.id = %s
                """, [target_classe_id])
                bk = cur.fetchone()
                if bk:
                    cur.execute("""
                        SELECT DISTINCT e.nom, e.prenom,
                               p.emailPere, p.emailMere
                        FROM eleve_inscription ei
                        JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                        LEFT JOIN parents p ON p.id_parent = e.id_parent
                        WHERE ei.classe_id = %s
                          AND (COALESCE(ei.groupe,'') = COALESCE(%s,''))
                          AND (COALESCE(ei.section_id,0) = COALESCE(%s,0))
                          AND ei.status = 1 AND ei.id_etablissement = %s
                    """, [bk[0], bk[1], bk[2], etab_id])
                    for row in cur.fetchall():
                        eleve_name = f"{row[0] or ''} {row[1] or ''}".strip()
                        if row[2]:
                            parent_emails.append({'email': row[2], 'name': f"Père de {eleve_name}"})
                        if row[3]:
                            parent_emails.append({'email': row[3], 'name': f"Mère de {eleve_name}"})

        # Dédupliquer
        seen_emails = set()
        unique_parent_emails = []
        for pe in parent_emails:
            if pe['email'] and pe['email'].lower() not in seen_emails:
                seen_emails.add(pe['email'].lower())
                unique_parent_emails.append(pe)
        parent_emails = unique_parent_emails

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
            if email_result.get('sent', 0) > 0:
                comm.status = 'delivered'
                comm.save(update_fields=['status'])

    except Exception as e:
        import traceback
        traceback.print_exc()
        email_result['errors'].append(str(e))

    msg_resp = {
        'id': comm.id_communication,
        'sender_name': comm.sender_name,
        'direction': 'out',
        'message': comm.message,
        'time': comm.created_at.strftime('%H:%M') if comm.created_at else '',
        'created_at': comm.created_at.strftime('%Y-%m-%d %H:%M:%S') if comm.created_at else '',
    }
    if comm.attachment_url:
        msg_resp['attachment'] = {
            'url': comm.attachment_url,
            'name': comm.attachment_name or '',
            'type': comm.attachment_type or 'file',
        }

    return JsonResponse({
        'success': True,
        'message': msg_resp,
        'email': {
            'sent': email_result.get('sent', 0),
            'failed': email_result.get('failed', 0),
            'total_parents': len(parent_emails),
            'errors': email_result.get('errors', []),
        }
    })


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_threads(request):
    """
    GET /api/communication/threads/
    Renvoie la liste des threads avec dernier message, relatif au personnel courant.
    """
    from MonEcole_app.models.communication import Communication
    from django.db.models import Max, Count, Q

    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    current_pers = int(pers_id) if pers_id else 0

    threads = Communication.objects.filter(
        id_etablissement=etab_id
    ).values('thread_id').annotate(
        last_msg=Max('created_at'),
        msg_count=Count('id_communication'),
        unread=Count('id_communication', filter=Q(is_read=False) & ~Q(sender_personnel_id=current_pers))
    ).order_by('-last_msg')

    thread_list = []
    for t in threads:
        last_comm = Communication.objects.filter(
            id_etablissement=etab_id,
            thread_id=t['thread_id']
        ).order_by('-created_at').first()

        first_comm = Communication.objects.filter(
            id_etablissement=etab_id,
            thread_id=t['thread_id']
        ).order_by('created_at').first()

        thread_list.append({
            'thread_id': t['thread_id'],
            'last_message': last_comm.message[:60] if last_comm else '',
            'last_sender': last_comm.sender_name if last_comm else '',
            'last_time': last_comm.created_at.strftime('%H:%M') if last_comm and last_comm.created_at else '',
            'last_date': last_comm.created_at.strftime('%d/%m') if last_comm and last_comm.created_at else '',
            'scope': first_comm.scope if first_comm else 'individual',
            'subject': first_comm.subject if first_comm else '',
            'msg_count': t['msg_count'],
            'unread': t['unread'],
        })

    return JsonResponse({'success': True, 'threads': thread_list})


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_teachers(request):
    """
    GET /api/communication/teachers/
    Renvoie la liste des collègues (rétro-compatibilité).
    """
    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    current_pers = int(pers_id) if pers_id else 0
    teachers = []
    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT p.id_personnel, p.nom, p.postnom, p.prenom, p.email
                FROM personnel p
                WHERE p.id_etablissement = %s AND p.en_fonction = 1 AND p.id_personnel != %s
                ORDER BY p.nom, p.prenom
            """, [etab_id, current_pers])
            for row in cur.fetchall():
                nm = f"{row[1] or ''} {row[3] or ''}".strip()
                if nm:
                    teachers.append({
                        'id_personnel': row[0],
                        'nom': row[1] or '',
                        'postnom': row[2] or '',
                        'prenom': row[3] or '',
                        'email': row[4] or '',
                    })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'teachers': teachers})


# ── Custom Groups API ──

@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='login')
def api_communication_group_create(request):
    """POST /api/communication/groups/create/ — Créer un groupe personnalisé."""
    from MonEcole_app.models.communication import CommunicationGroup, CommunicationGroupMember

    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id or not pers_id:
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)

    name = (data.get('name') or '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Nom du groupe requis'}, status=400)

    description = (data.get('description') or '').strip()
    member_ids = data.get('members', [])
    avatar_color = data.get('avatar_color', '#128c7e')

    group = CommunicationGroup.objects.create(
        id_etablissement=etab_id,
        name=name,
        description=description,
        created_by=pers_id,
        avatar_color=avatar_color,
    )

    # Ajouter le créateur comme membre
    CommunicationGroupMember.objects.create(id_group=group.id_group, id_personnel=pers_id)

    # Ajouter les autres membres
    for mid in member_ids:
        try:
            mid = int(mid)
            if mid != pers_id:
                CommunicationGroupMember.objects.get_or_create(id_group=group.id_group, id_personnel=mid)
        except (ValueError, Exception):
            pass

    return JsonResponse({
        'success': True,
        'group': {
            'id_group': group.id_group,
            'name': group.name,
            'description': group.description,
            'avatar_color': group.avatar_color,
            'n_members': CommunicationGroupMember.objects.filter(id_group=group.id_group).count(),
        }
    })


@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='login')
def api_communication_group_update(request):
    """POST /api/communication/groups/update/ — Modifier un groupe (ajouter/retirer membres, renommer)."""
    from MonEcole_app.models.communication import CommunicationGroup, CommunicationGroupMember

    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id or not pers_id:
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)

    group_id = data.get('id_group')
    if not group_id:
        return JsonResponse({'success': False, 'error': 'id_group requis'}, status=400)

    group = CommunicationGroup.objects.filter(id_group=group_id, id_etablissement=etab_id).first()
    if not group:
        return JsonResponse({'success': False, 'error': 'Groupe non trouvé'}, status=404)

    # Seul le créateur peut modifier (ou un membre)
    is_member = CommunicationGroupMember.objects.filter(id_group=group_id, id_personnel=pers_id).exists()
    if group.created_by != pers_id and not is_member:
        return JsonResponse({'success': False, 'error': 'Vous n\'êtes pas membre de ce groupe'}, status=403)

    action = data.get('action', 'update')

    if action == 'rename':
        new_name = (data.get('name') or '').strip()
        if new_name:
            group.name = new_name
            group.save(update_fields=['name'])

    elif action == 'add_members':
        for mid in data.get('members', []):
            try:
                CommunicationGroupMember.objects.get_or_create(id_group=group_id, id_personnel=int(mid))
            except Exception:
                pass

    elif action == 'remove_member':
        mid = data.get('member_id')
        if mid and int(mid) != group.created_by:
            CommunicationGroupMember.objects.filter(id_group=group_id, id_personnel=int(mid)).delete()

    elif action == 'delete':
        if group.created_by == pers_id:
            CommunicationGroupMember.objects.filter(id_group=group_id).delete()
            group.delete()
            return JsonResponse({'success': True, 'deleted': True})
        else:
            return JsonResponse({'success': False, 'error': 'Seul le créateur peut supprimer'}, status=403)

    elif action == 'leave':
        CommunicationGroupMember.objects.filter(id_group=group_id, id_personnel=pers_id).delete()
        return JsonResponse({'success': True, 'left': True})

    return JsonResponse({'success': True})


# ── Presence & Video Conference API ──

@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='login')
def api_communication_heartbeat(request):
    """
    POST /api/communication/heartbeat/
    Met à jour la présence de l'utilisateur et retourne la liste des collègues en ligne.
    Un personnel est considéré "en ligne" s'il a envoyé un heartbeat dans les 2 dernières minutes.
    """
    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id or not pers_id:
        return JsonResponse({'success': False}, status=400)

    try:
        with connections['default'].cursor() as cur:
            # Upsert : mettre à jour ma présence
            cur.execute("""
                INSERT INTO personnel_presence (id_personnel, id_etablissement, last_activity, is_online)
                VALUES (%s, %s, NOW(), 1)
                ON DUPLICATE KEY UPDATE last_activity = NOW(), is_online = 1, id_etablissement = %s
            """, [pers_id, etab_id, etab_id])

            # Marquer offline ceux inactifs > 2 minutes
            cur.execute("""
                UPDATE personnel_presence
                SET is_online = 0
                WHERE id_etablissement = %s AND last_activity < DATE_SUB(NOW(), INTERVAL 2 MINUTE)
            """, [etab_id])

            # Retourner la liste des collègues en ligne
            cur.execute("""
                SELECT pp.id_personnel,
                       CONCAT(COALESCE(p.nom,''), ' ', COALESCE(p.prenom,'')) as nom,
                       pp.last_activity
                FROM personnel_presence pp
                JOIN personnel p ON p.id_personnel = pp.id_personnel
                WHERE pp.id_etablissement = %s AND pp.is_online = 1 AND pp.id_personnel != %s
                ORDER BY p.nom
            """, [etab_id, pers_id])
            online = []
            for row in cur.fetchall():
                nm = (row[1] or '').strip()
                if nm:
                    online.append({
                        'id_personnel': row[0],
                        'nom': nm,
                        'last_activity': row[2].strftime('%H:%M') if row[2] else '',
                    })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'online': online, 'count': len(online)})


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_visio(request):
    """
    GET /api/communication/visio/?thread_id=...&contact_name=...
    Génère une URL Jitsi Meet sécurisée pour un appel vidéo.
    Utilise le serveur public meet.jit.si (gratuit, pas d'inscription).
    """
    import hashlib

    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    thread_id = request.GET.get('thread_id', '')
    contact_name = request.GET.get('contact_name', 'Réunion')

    if not thread_id:
        return JsonResponse({'success': False, 'error': 'thread_id requis'}, status=400)

    # Générer un nom de salle unique et déterministe
    raw = f"monecole_{etab_id}_{thread_id}"
    room_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
    room_name = f"MonEcole_{room_hash}"

    # Info du personnel courant
    _, sender_name = _get_sender_info(pers_id, etab_id)

    # Construire le lien de partage avec le vrai sous-domaine
    scheme = 'https' if request.is_secure() else 'http'
    host = request.get_host()  # ex: collegealfajiri.monecole.pro
    share_link = f"{scheme}://{host}/dashboard/communication/"

    return JsonResponse({
        'success': True,
        'room_name': room_name,
        'display_name': sender_name,
        'subject': f"Appel — {contact_name}",
        'jitsi_domain': 'meet.jit.si',
        'jitsi_url': f"https://meet.jit.si/{room_name}",
        'share_link': share_link,
    })


# ── Scheduled Meetings API ──

@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='login')
def api_communication_meeting_create(request):
    """POST /api/communication/meetings/create/ — Planifier une réunion."""
    import hashlib, secrets

    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id or not pers_id:
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)

    title = (data.get('title') or '').strip()
    if not title:
        return JsonResponse({'success': False, 'error': 'Titre requis'}, status=400)

    description = (data.get('description') or '').strip()
    scheduled_at = data.get('scheduled_at', '')
    duration = int(data.get('duration_minutes', 60) or 60)
    invitee_ids = data.get('invitees', [])

    if not scheduled_at:
        return JsonResponse({'success': False, 'error': 'Date et heure requises'}, status=400)

    # Générer un nom de salle unique + token de partage
    share_token = secrets.token_urlsafe(16)[:24]
    raw = f"monecole_meeting_{etab_id}_{share_token}"
    room_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
    room_name = f"MonEcole_Meet_{room_hash}"

    _, sender_name = _get_sender_info(pers_id, etab_id)

    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                INSERT INTO communication_meeting
                    (id_etablissement, title, description, room_name, created_by,
                     scheduled_at, duration_minutes, status, share_token)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'scheduled', %s)
            """, [etab_id, title, description, room_name, pers_id,
                  scheduled_at, duration, share_token])
            meeting_id = cur.lastrowid

            # Ajouter le créateur comme invité (accepté)
            cur.execute("""
                INSERT INTO communication_meeting_invitee (id_meeting, id_personnel, rsvp)
                VALUES (%s, %s, 'accepted')
            """, [meeting_id, pers_id])

            # Ajouter les invités
            for inv_id in invitee_ids:
                try:
                    inv_id = int(inv_id)
                    if inv_id != pers_id:
                        cur.execute("""
                            INSERT IGNORE INTO communication_meeting_invitee
                                (id_meeting, id_personnel, rsvp)
                            VALUES (%s, %s, 'pending')
                        """, [meeting_id, inv_id])
                except (ValueError, Exception):
                    pass

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    # Construire le lien de partage avec le vrai sous-domaine
    scheme = 'https' if request.is_secure() else 'http'
    host = request.get_host()  # ex: collegealfajiri.monecole.pro
    share_url = f"{scheme}://{host}/dashboard/communication/?join={share_token}"

    return JsonResponse({
        'success': True,
        'meeting': {
            'id_meeting': meeting_id,
            'title': title,
            'room_name': room_name,
            'scheduled_at': scheduled_at,
            'duration_minutes': duration,
            'share_token': share_token,
            'share_url': share_url,
            'jitsi_url': f"https://meet.jit.si/{room_name}",
            'created_by_name': sender_name,
        }
    })


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_meetings_list(request):
    """GET /api/communication/meetings/ — Mes réunions (planifiées + passées)."""
    pers_id, etab_id = _get_personnel_id(request)
    if not etab_id:
        return JsonResponse({'success': False, 'error': 'Établissement non trouvé'}, status=400)

    current_pers = int(pers_id) if pers_id else 0
    meetings = []

    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT m.id_meeting, m.title, m.description, m.room_name,
                       m.created_by, m.scheduled_at, m.duration_minutes,
                       m.status, m.share_token,
                       CONCAT(COALESCE(p.nom,''), ' ', COALESCE(p.prenom,'')) as creator_name,
                       (SELECT COUNT(*) FROM communication_meeting_invitee WHERE id_meeting = m.id_meeting) as n_invitees,
                       (SELECT rsvp FROM communication_meeting_invitee WHERE id_meeting = m.id_meeting AND id_personnel = %s) as my_rsvp
                FROM communication_meeting m
                JOIN personnel p ON p.id_personnel = m.created_by
                WHERE m.id_etablissement = %s
                  AND (m.created_by = %s
                       OR EXISTS (SELECT 1 FROM communication_meeting_invitee mi
                                  WHERE mi.id_meeting = m.id_meeting AND mi.id_personnel = %s))
                ORDER BY m.scheduled_at DESC
                LIMIT 50
            """, [current_pers, etab_id, current_pers, current_pers])

            for row in cur.fetchall():
                scheme = 'https' if request.is_secure() else 'http'
                host = request.get_host()
                meetings.append({
                    'id_meeting': row[0],
                    'title': row[1],
                    'description': row[2] or '',
                    'room_name': row[3],
                    'created_by': row[4],
                    'scheduled_at': row[5].strftime('%Y-%m-%dT%H:%M') if row[5] else '',
                    'scheduled_display': row[5].strftime('%d/%m/%Y à %H:%M') if row[5] else '',
                    'duration_minutes': row[6],
                    'status': row[7],
                    'share_token': row[8],
                    'creator_name': (row[9] or '').strip(),
                    'n_invitees': row[10],
                    'my_rsvp': row[11] or 'pending',
                    'is_owner': row[4] == current_pers,
                    'share_url': f"{scheme}://{host}/dashboard/communication/?join={row[8]}",
                    'jitsi_url': f"https://meet.jit.si/{row[3]}",
                })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True, 'meetings': meetings})


@require_http_methods(["GET"])
@login_required(login_url='login')
def api_communication_meeting_join(request):
    """GET /api/communication/meetings/join/?token=... — Rejoindre via token."""
    import hashlib

    pers_id, etab_id = _get_personnel_id(request)
    token = request.GET.get('token', '')
    if not token:
        return JsonResponse({'success': False, 'error': 'Token requis'}, status=400)

    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT m.id_meeting, m.title, m.room_name, m.scheduled_at,
                       m.duration_minutes, m.status,
                       CONCAT(COALESCE(p.nom,''), ' ', COALESCE(p.prenom,'')) as creator_name
                FROM communication_meeting m
                JOIN personnel p ON p.id_personnel = m.created_by
                WHERE m.share_token = %s
                LIMIT 1
            """, [token])
            row = cur.fetchone()
            if not row:
                return JsonResponse({'success': False, 'error': 'Réunion non trouvée'}, status=404)

            _, display_name = _get_sender_info(pers_id, etab_id) if pers_id else (None, 'Participant')

            return JsonResponse({
                'success': True,
                'meeting': {
                    'id_meeting': row[0],
                    'title': row[1],
                    'room_name': row[2],
                    'scheduled_at': row[3].strftime('%d/%m/%Y à %H:%M') if row[3] else '',
                    'duration_minutes': row[4],
                    'status': row[5],
                    'creator_name': (row[6] or '').strip(),
                },
                'display_name': display_name or 'Participant',
                'jitsi_domain': 'meet.jit.si',
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@login_required(login_url='login')
def api_communication_meeting_cancel(request):
    """POST /api/communication/meetings/cancel/ — Annuler une réunion."""
    pers_id, etab_id = _get_personnel_id(request)
    if not pers_id:
        return JsonResponse({'success': False, 'error': 'Non autorisé'}, status=403)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON invalide'}, status=400)

    meeting_id = data.get('id_meeting')
    if not meeting_id:
        return JsonResponse({'success': False, 'error': 'id_meeting requis'}, status=400)

    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                UPDATE communication_meeting
                SET status = 'cancelled'
                WHERE id_meeting = %s AND created_by = %s AND id_etablissement = %s
            """, [meeting_id, pers_id, etab_id])
            if cur.rowcount == 0:
                return JsonResponse({'success': False, 'error': 'Réunion non trouvée ou non autorisé'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': True})
