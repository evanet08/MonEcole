"""
API Évaluations & Notes — Module Parents PWA.
Fournit les données d'évaluations planifiées, notes par éval, notes bulletin, résultats.
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connections

from MonEcole_app.models.eleves.eleve import Eleve
from MonEcole_app.views.parent.parent_views import _get_parent_session

logger = logging.getLogger(__name__)


def _verify_parent_child(request, id_eleve):
    """Vérifie que l'enfant appartient au parent connecté. Retourne (parent_data, error_resp)."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return None, JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
    if parent_data.get('id_pays'):
        filters['id_pays'] = parent_data['id_pays']

    if not Eleve.objects.filter(**filters).exists():
        return None, JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

    return parent_data, None


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_evaluations(request):
    """Évaluations planifiées pour la classe de l'enfant."""
    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    parent_data, err = _verify_parent_child(request, id_eleve)
    if err:
        return err

    try:
        with connections['default'].cursor() as cur:
            # Trouver l'inscription active
            cur.execute("""
                SELECT ei.classe_id, ei.groupe, ei.section_id, ei.id_annee_id,
                       ei.id_etablissement, ei.idCampus_id
                FROM eleve_inscription ei
                WHERE ei.id_eleve_id = %s AND ei.status = 1
                ORDER BY ei.id_annee_id DESC LIMIT 1
            """, [id_eleve])
            insc = cur.fetchone()
            if not insc:
                return JsonResponse({'success': True, 'evaluations': []})

            classe_id, groupe, section_id, annee_id, etab_id, campus_id = insc

            # Évaluations de cette classe
            cur.execute("""
                SELECT e.id_evaluation, e.title, e.date_eval, e.ponderer_eval,
                       cpc.id_cours_id,
                       (SELECT en.note FROM eleve_note en
                        WHERE en.id_evaluation_id = e.id_evaluation AND en.id_eleve_id = %s
                        LIMIT 1) as note_eleve
                FROM evaluation e
                JOIN cours_par_classe cpc ON cpc.id_cours_classe = e.id_cours_classe_id
                WHERE e.classe_id = %s AND e.id_annee_id = %s
                  AND e.id_etablissement = %s
                ORDER BY e.date_eval DESC
            """, [id_eleve, classe_id, annee_id, etab_id])

            columns = [col[0] for col in cur.description]
            evals_raw = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Résoudre les noms de cours depuis le Hub
        cours_ids = list(set(e['id_cours_id'] for e in evals_raw if e.get('id_cours_id')))
        cours_names = {}
        if cours_ids:
            try:
                with connections['countryStructure'].cursor() as cur:
                    placeholders = ','.join(['%s'] * len(cours_ids))
                    cur.execute(f"SELECT id_cours, cours FROM cours WHERE id_cours IN ({placeholders})", cours_ids)
                    cours_names = {row[0]: row[1] for row in cur.fetchall()}
            except Exception:
                pass

        evaluations = []
        for ev in evals_raw:
            evaluations.append({
                'id_evaluation': ev['id_evaluation'],
                'title': ev['title'],
                'date_eval': str(ev['date_eval']) if ev['date_eval'] else '',
                'ponderation': ev['ponderer_eval'] or 0,
                'cours': cours_names.get(ev['id_cours_id'], f"Cours #{ev['id_cours_id']}"),
                'note_eleve': float(ev['note_eleve']) if ev['note_eleve'] is not None else None,
            })

        return JsonResponse({'success': True, 'evaluations': evaluations})

    except Exception as e:
        logger.exception("api_parent_evaluations error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_notes(request):
    """Notes de l'élève regroupées par cours et par période."""
    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    parent_data, err = _verify_parent_child(request, id_eleve)
    if err:
        return err

    try:
        with connections['default'].cursor() as cur:
            # Notes détaillées par évaluation
            cur.execute("""
                SELECT en.id_note, en.note, en.note_repechage, en.id_cours_id,
                       ev.title as eval_title, ev.ponderer_eval, ev.date_eval,
                       ent.type as type_note, ent.sigle as sigle_note
                FROM eleve_note en
                JOIN evaluation ev ON ev.id_evaluation = en.id_evaluation_id
                LEFT JOIN eleve_note_type ent ON ent.id_type_note = en.id_type_note_id
                WHERE en.id_eleve_id = %s AND en.id_etablissement = %s
                ORDER BY en.id_cours_id, ev.date_eval DESC
            """, [id_eleve, parent_data.get('id_pays') and
                  Eleve.objects.filter(id_eleve=id_eleve).values_list('id_etablissement', flat=True).first()])

            columns = [col[0] for col in cur.description]
            notes_raw = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Résoudre cours
        cours_ids = list(set(n['id_cours_id'] for n in notes_raw if n.get('id_cours_id')))
        cours_names = {}
        if cours_ids:
            try:
                with connections['countryStructure'].cursor() as cur:
                    placeholders = ','.join(['%s'] * len(cours_ids))
                    cur.execute(f"SELECT id_cours, cours FROM cours WHERE id_cours IN ({placeholders})", cours_ids)
                    cours_names = {row[0]: row[1] for row in cur.fetchall()}
            except Exception:
                pass

        # Grouper par cours
        notes_by_cours = {}
        for n in notes_raw:
            cours_id = n['id_cours_id']
            cours_nom = cours_names.get(cours_id, f"Cours #{cours_id}")
            if cours_nom not in notes_by_cours:
                notes_by_cours[cours_nom] = []
            notes_by_cours[cours_nom].append({
                'id_note': n['id_note'],
                'note': float(n['note']) if n['note'] is not None else None,
                'note_repechage': float(n['note_repechage']) if n['note_repechage'] is not None else None,
                'eval_title': n['eval_title'],
                'ponderation': n['ponderer_eval'] or 0,
                'date_eval': str(n['date_eval']) if n['date_eval'] else '',
                'type_note': n['type_note'] or '',
                'sigle_note': n['sigle_note'] or '',
            })

        return JsonResponse({'success': True, 'notes_par_cours': notes_by_cours})

    except Exception as e:
        logger.exception("api_parent_notes error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_bulletin(request):
    """Notes du bulletin de l'élève (note_bulletin)."""
    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    parent_data, err = _verify_parent_child(request, id_eleve)
    if err:
        return err

    try:
        eleve = Eleve.objects.get(id_eleve=id_eleve)
        etab_id = eleve.id_etablissement

        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT nb.id_note_bulletin, nb.note, nb.maxima, nb.source_type,
                       nb.id_note_type, nb.id_cours_annee, nb.id_repartition_config
                FROM note_bulletin nb
                WHERE nb.id_eleve_id = %s AND nb.id_etablissement = %s
                ORDER BY nb.id_cours_annee, nb.id_repartition_config
            """, [id_eleve, etab_id])
            columns = [col[0] for col in cur.description]
            bulletin_raw = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Résoudre cours_annee et repartition depuis Hub
        ca_ids = list(set(b['id_cours_annee'] for b in bulletin_raw if b.get('id_cours_annee')))
        rep_ids = list(set(b['id_repartition_config'] for b in bulletin_raw if b.get('id_repartition_config')))

        cours_map = {}
        rep_map = {}

        if ca_ids:
            try:
                with connections['countryStructure'].cursor() as cur:
                    placeholders = ','.join(['%s'] * len(ca_ids))
                    cur.execute(f"""
                        SELECT ca.id_cours_annee, c.cours
                        FROM cours_annee ca
                        JOIN cours c ON c.id_cours = ca.cours_id
                        WHERE ca.id_cours_annee IN ({placeholders})
                    """, ca_ids)
                    cours_map = {row[0]: row[1] for row in cur.fetchall()}
            except Exception:
                pass

        if rep_ids:
            try:
                with connections['countryStructure'].cursor() as cur:
                    placeholders = ','.join(['%s'] * len(rep_ids))
                    cur.execute(f"""
                        SELECT rcea.id, ri.nom, ri.code
                        FROM repartition_configs_etab_annee rcea
                        JOIN repartition_instances ri ON ri.id = rcea.repartition_id
                        WHERE rcea.id IN ({placeholders})
                    """, rep_ids)
                    rep_map = {row[0]: {'nom': row[1], 'code': row[2]} for row in cur.fetchall()}
            except Exception:
                pass

        bulletin = []
        for b in bulletin_raw:
            bulletin.append({
                'id': b['id_note_bulletin'],
                'note': float(b['note']) if b['note'] is not None else None,
                'maxima': b['maxima'],
                'source_type': b['source_type'],
                'type_note_id': b['id_note_type'],
                'cours': cours_map.get(b['id_cours_annee'], f"Cours #{b['id_cours_annee']}"),
                'periode': rep_map.get(b['id_repartition_config'], {}).get('nom', ''),
                'periode_code': rep_map.get(b['id_repartition_config'], {}).get('code', ''),
            })

        return JsonResponse({'success': True, 'bulletin': bulletin})

    except Exception as e:
        logger.exception("api_parent_bulletin error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_resultats(request):
    """Résultats de délibération (périodique, trimestrielle, annuelle)."""
    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    parent_data, err = _verify_parent_child(request, id_eleve)
    if err:
        return err

    try:
        eleve = Eleve.objects.get(id_eleve=id_eleve)
        etab_id = eleve.id_etablissement

        resultats = {'periodique': [], 'trimestriel': [], 'annuel': []}

        with connections['default'].cursor() as cur:
            # Périodique
            cur.execute("""
                SELECT dpr.pourcentage, dpr.place, dpr.id_trimestre_id, dpr.id_periode_id
                FROM deliberation_periodique_resultats dpr
                WHERE dpr.id_eleve_id = %s AND dpr.id_etablissement = %s
                ORDER BY dpr.id_trimestre_id, dpr.id_periode_id
            """, [id_eleve, etab_id])
            for row in cur.fetchall():
                resultats['periodique'].append({
                    'pourcentage': round(row[0], 2) if row[0] else 0,
                    'place': row[1] or '',
                    'trimestre_id': row[2],
                    'periode_id': row[3],
                })

            # Trimestriel
            cur.execute("""
                SELECT dtr.pourcentage, dtr.place, dtr.id_trimestre_id
                FROM deliberation_trimistrielle_resultats dtr
                WHERE dtr.id_eleve_id = %s AND dtr.id_etablissement = %s
                ORDER BY dtr.id_trimestre_id
            """, [id_eleve, etab_id])
            for row in cur.fetchall():
                resultats['trimestriel'].append({
                    'pourcentage': round(row[0], 2) if row[0] else 0,
                    'place': row[1] or '',
                    'trimestre_id': row[2],
                })

            # Annuel
            cur.execute("""
                SELECT dar.pourcentage, dar.place, m.mention, m.abbreviation,
                       daf.finalite, daf.sigle as finalite_sigle
                FROM deliberation_annuelle_resultats dar
                LEFT JOIN countryStructure.mentions m ON m.id_mention = dar.id_mention_id
                LEFT JOIN deliberation_annuelle_conditions dac ON dac.id_decision = dar.id_decision_id
                LEFT JOIN countryStructure.deliberation_annuelle_finalites daf ON daf.id_finalite = dac.id_finalite_id
                WHERE dar.id_eleve_id = %s AND dar.id_etablissement = %s
            """, [id_eleve, etab_id])
            for row in cur.fetchall():
                resultats['annuel'].append({
                    'pourcentage': round(row[0], 2) if row[0] else 0,
                    'place': row[1] or '',
                    'mention': row[2] or '',
                    'mention_sigle': row[3] or '',
                    'finalite': row[4] or '',
                    'finalite_sigle': row[5] or '',
                })

        return JsonResponse({'success': True, 'resultats': resultats})

    except Exception as e:
        logger.exception("api_parent_resultats error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
