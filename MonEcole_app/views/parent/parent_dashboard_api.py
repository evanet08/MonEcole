"""
API Dashboard — Module Parents PWA.
Vue synthétique : résumé notes, présence, conduite.
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connections

from MonEcole_app.models.eleves.eleve import Eleve, Eleve_inscription
from MonEcole_app.views.parent.parent_views import _get_parent_session

logger = logging.getLogger(__name__)


def _verify_parent_child(request, id_eleve):
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
def api_parent_dashboard(request):
    """Dashboard complet : synthèse notes + présence + conduite."""
    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    parent_data, err = _verify_parent_child(request, id_eleve)
    if err:
        return err

    try:
        eleve = Eleve.objects.get(id_eleve=id_eleve)
        etab_id = eleve.id_etablissement

        dashboard = {
            'notes_summary': {},
            'presence': {},
            'conduite': [],
            'resultats_evolution': [],
        }

        with connections['default'].cursor() as cur:
            # ── 1. Résumé notes par cours (moyenne des notes) ──
            cur.execute("""
                SELECT en.id_cours_id,
                       COUNT(*) as nb_notes,
                       AVG(en.note) as moyenne,
                       MAX(ev.ponderer_eval) as max_ponderation
                FROM eleve_note en
                JOIN evaluation ev ON ev.id_evaluation = en.id_evaluation_id
                WHERE en.id_eleve_id = %s AND en.id_etablissement = %s
                  AND en.note IS NOT NULL
                GROUP BY en.id_cours_id
                ORDER BY en.id_cours_id
            """, [id_eleve, etab_id])

            columns = [col[0] for col in cur.description]
            notes_summary_raw = [dict(zip(columns, row)) for row in cur.fetchall()]

            # Résoudre cours
            cours_ids = [n['id_cours_id'] for n in notes_summary_raw]
            cours_names = {}
            if cours_ids:
                try:
                    with connections['countryStructure'].cursor() as cur_hub:
                        placeholders = ','.join(['%s'] * len(cours_ids))
                        cur_hub.execute(f"SELECT id_cours, cours FROM cours WHERE id_cours IN ({placeholders})", cours_ids)
                        cours_names = {row[0]: row[1] for row in cur_hub.fetchall()}
                except Exception:
                    pass

            notes_par_cours = []
            for n in notes_summary_raw:
                notes_par_cours.append({
                    'cours': cours_names.get(n['id_cours_id'], f"#{n['id_cours_id']}"),
                    'nb_notes': n['nb_notes'],
                    'moyenne': round(float(n['moyenne']), 2) if n['moyenne'] else 0,
                    'max_ponderation': n['max_ponderation'] or 20,
                })
            dashboard['notes_summary'] = notes_par_cours

            # ── 2. Présence ──
            cur.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN hp.present_ou_absent = 1 THEN 1 ELSE 0 END) as presents,
                    SUM(CASE WHEN hp.present_ou_absent = 0 THEN 1 ELSE 0 END) as absents
                FROM horaire_presence hp
                WHERE hp.id_eleve_id = %s AND hp.id_etablissement = %s
            """, [id_eleve, etab_id])
            row = cur.fetchone()
            if row:
                total = row[0] or 0
                presents = row[1] or 0
                absents = row[2] or 0
                dashboard['presence'] = {
                    'total': total,
                    'presents': presents,
                    'absents': absents,
                    'taux_presence': round((presents / total * 100), 1) if total > 0 else 100,
                }

            # Dernières absences
            cur.execute("""
                SELECT hp.date_presence, hp.si_absent_motif,
                       h.debut, h.fin
                FROM horaire_presence hp
                JOIN horaire h ON h.id_horaire = hp.id_horaire_id
                WHERE hp.id_eleve_id = %s AND hp.id_etablissement = %s
                  AND hp.present_ou_absent = 0
                ORDER BY hp.date_presence DESC
                LIMIT 10
            """, [id_eleve, etab_id])
            absences = []
            for r in cur.fetchall():
                absences.append({
                    'date': str(r[0]) if r[0] else '',
                    'motif': r[1] or 'Non justifié',
                    'creneau': f"{r[2]}-{r[3]}" if r[2] and r[3] else '',
                })
            dashboard['presence']['absences_recentes'] = absences

            # ── 3. Conduite ──
            cur.execute("""
                SELECT ec.motif, ec.quote, ec.date_enregistrement
                FROM eleve_conduite ec
                WHERE ec.id_eleve_id = %s AND ec.id_etablissement = %s
                ORDER BY ec.date_enregistrement DESC
                LIMIT 20
            """, [id_eleve, etab_id])
            for r in cur.fetchall():
                dashboard['conduite'].append({
                    'motif': r[0] or '',
                    'quote': r[1] or 0,
                    'date': str(r[2]) if r[2] else '',
                })

            # ── 4. Évolution des résultats par période ──
            cur.execute("""
                SELECT dpr.pourcentage, dpr.place, dpr.id_periode_id
                FROM deliberation_periodique_resultats dpr
                WHERE dpr.id_eleve_id = %s AND dpr.id_etablissement = %s
                ORDER BY dpr.id_periode_id
            """, [id_eleve, etab_id])
            for r in cur.fetchall():
                dashboard['resultats_evolution'].append({
                    'pourcentage': round(float(r[0]), 2) if r[0] else 0,
                    'place': r[1] or '',
                    'periode_id': r[2],
                })

        return JsonResponse({'success': True, 'dashboard': dashboard})

    except Exception as e:
        logger.exception("api_parent_dashboard error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
