"""
API Paiements — Module Parents PWA.
Visualisation des paiements effectués, soldes et soumission "en attente".
"""
import json
import logging
from datetime import date

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connections

from MonEcole_app.models.eleves.eleve import Eleve, Eleve_inscription
from MonEcole_app.views.parent.parent_views import _get_parent_session

logger = logging.getLogger(__name__)


def _verify_parent_child(request, id_eleve):
    """Vérifie propriété parent→enfant."""
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
def api_parent_payments_summary(request):
    """Résumé des paiements : variables attendues, montants payés, soldes."""
    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    parent_data, err = _verify_parent_child(request, id_eleve)
    if err:
        return err

    try:
        eleve = Eleve.objects.get(id_eleve=id_eleve)
        etab_id = eleve.id_etablissement

        # Trouver l'inscription active
        insc = Eleve_inscription.objects.filter(
            id_eleve=eleve, status=True
        ).order_by('-id_annee_id').first()

        if not insc:
            return JsonResponse({'success': True, 'summary': [], 'payments': []})

        with connections['default'].cursor() as cur:
            # Prix attendus pour cette classe
            cur.execute("""
                SELECT vp.id_prix, vp.prix, v.id_variable, v.variable, vc.nom as categorie
                FROM recouvrment_variable_prix vp
                JOIN recouvrment_variable v ON v.id_variable = vp.id_variable_id
                LEFT JOIN recouvrment_variable_categorie vc ON vc.id_variable_categorie = v.id_variable_categorie_id
                WHERE vp.id_classe_id = %s AND vp.id_annee_id = %s
                  AND vp.idCampus_id = %s AND vp.id_etablissement = %s
                ORDER BY vc.nom, v.variable
            """, [insc.id_classe_id, insc.id_annee_id, insc.idCampus_id, etab_id])

            columns = [col[0] for col in cur.description]
            prix_raw = [dict(zip(columns, row)) for row in cur.fetchall()]

            # Réductions pour cet élève
            cur.execute("""
                SELECT rp.id_variable_id, rp.pourcentage
                FROM recouvrment_reduction_prix rp
                WHERE rp.id_eleve_id = %s AND rp.id_etablissement = %s
            """, [id_eleve, etab_id])
            reductions = {row[0]: row[1] for row in cur.fetchall()}

            # Paiements validés (status=1) et en attente (status=0)
            cur.execute("""
                SELECT p.id_paiement, p.montant, p.date_paie, p.status,
                       p.is_rejected, p.id_variable_id,
                       v.variable as variable_nom,
                       b.banque as banque_nom, c.compte as compte_nom
                FROM recouvrment_paiement p
                JOIN recouvrment_variable v ON v.id_variable = p.id_variable_id
                LEFT JOIN recouvrment_banque b ON b.id_banque = p.id_banque_id
                LEFT JOIN recouvrment_compte c ON c.id_compte = p.id_compte_id
                WHERE p.id_eleve_id = %s AND p.id_etablissement = %s
                ORDER BY p.date_paie DESC
            """, [id_eleve, etab_id])
            columns_p = [col[0] for col in cur.description]
            payments_raw = [dict(zip(columns_p, row)) for row in cur.fetchall()]

        # Construire le résumé par variable
        summary = []
        payments_by_var = {}
        for p in payments_raw:
            vid = p['id_variable_id']
            if vid not in payments_by_var:
                payments_by_var[vid] = {'valide': 0, 'en_attente': 0}
            if p['status']:
                payments_by_var[vid]['valide'] += p['montant'] or 0
            elif not p['is_rejected']:
                payments_by_var[vid]['en_attente'] += p['montant'] or 0

        for prix in prix_raw:
            vid = prix['id_variable']
            montant_attendu = prix['prix']
            reduction_pct = reductions.get(vid, 0)
            if reduction_pct:
                montant_attendu = int(montant_attendu * (100 - reduction_pct) / 100)

            payed = payments_by_var.get(vid, {})
            summary.append({
                'id_variable': vid,
                'variable': prix['variable'],
                'categorie': prix['categorie'] or 'Autre',
                'montant_attendu': montant_attendu,
                'reduction_pct': reduction_pct,
                'montant_paye': payed.get('valide', 0),
                'montant_en_attente': payed.get('en_attente', 0),
                'solde': montant_attendu - payed.get('valide', 0),
            })

        # Historique des paiements
        payments = []
        for p in payments_raw:
            statut = 'validé' if p['status'] else ('rejeté' if p['is_rejected'] else 'en attente')
            payments.append({
                'id_paiement': p['id_paiement'],
                'montant': p['montant'] or 0,
                'date_paie': str(p['date_paie']) if p['date_paie'] else '',
                'statut': statut,
                'variable': p['variable_nom'] or '',
                'banque': p['banque_nom'] or '',
                'compte': p['compte_nom'] or '',
            })

        return JsonResponse({
            'success': True,
            'summary': summary,
            'payments': payments,
        })

    except Exception as e:
        logger.exception("api_parent_payments_summary error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_payment_options(request):
    """Options pour soumettre un paiement (banques, comptes, variables)."""
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
            # Banques
            cur.execute("""
                SELECT id_banque, banque, sigle FROM recouvrment_banque
                WHERE id_etablissement = %s ORDER BY banque
            """, [etab_id])
            banques = [{'id': r[0], 'nom': r[1], 'sigle': r[2] or ''} for r in cur.fetchall()]

            # Comptes
            cur.execute("""
                SELECT c.id_compte, c.compte, b.banque
                FROM recouvrment_compte c
                JOIN recouvrment_banque b ON b.id_banque = c.id_banque_id
                WHERE c.id_etablissement = %s ORDER BY c.compte
            """, [etab_id])
            comptes = [{'id': r[0], 'nom': r[1], 'banque': r[2]} for r in cur.fetchall()]

            # Variables avec soldes > 0
            cur.execute("""
                SELECT v.id_variable, v.variable
                FROM recouvrment_variable v
                WHERE v.id_etablissement = %s AND v.estObligatoire = 1
                ORDER BY v.variable
            """, [etab_id])
            variables = [{'id': r[0], 'nom': r[1]} for r in cur.fetchall()]

        return JsonResponse({
            'success': True,
            'banques': banques,
            'comptes': comptes,
            'variables': variables,
        })

    except Exception as e:
        logger.exception("api_parent_payment_options error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_parent_payment_submit(request):
    """Soumettre un paiement en attente (status=False). Validé par l'école."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    try:
        data = json.loads(request.body)
        id_eleve = data.get('id_eleve')
        id_variable = data.get('id_variable')
        montant = data.get('montant')
        id_banque = data.get('id_banque')
        id_compte = data.get('id_compte')
        date_paie = data.get('date_paie')

        if not all([id_eleve, id_variable, montant, id_banque, id_compte]):
            return JsonResponse({'success': False, 'error': 'Données manquantes'}, status=400)

        # Vérifier propriété
        _, err = _verify_parent_child(request, id_eleve)
        if err:
            return err

        eleve = Eleve.objects.get(id_eleve=id_eleve)
        insc = Eleve_inscription.objects.filter(
            id_eleve=eleve, status=True
        ).order_by('-id_annee_id').first()

        if not insc:
            return JsonResponse({'success': False, 'error': 'Aucune inscription active'}, status=400)

        # Insérer via raw SQL (respect stricte du schéma existant)
        with connections['default'].cursor() as cur:
            cur.execute("""
                INSERT INTO recouvrment_paiement
                    (id_variable_id, montant, id_banque_id, id_compte_id,
                     date_paie, id_eleve_id, idCampus_id, id_annee_id,
                     id_cycle_id, id_classe_id, groupe, section_id,
                     status, is_rejected, id_pays, id_etablissement)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0, %s, %s)
            """, [
                id_variable, int(montant), id_banque, id_compte,
                date_paie or date.today().isoformat(),
                id_eleve, insc.idCampus_id, insc.id_annee_id,
                insc.id_cycle_id, insc.id_classe_id,
                insc.groupe or None, insc.section_id,
                eleve.id_pays, eleve.id_etablissement,
            ])
            new_id = cur.lastrowid

        return JsonResponse({
            'success': True,
            'id_paiement': new_id,
            'message': 'Paiement soumis en attente de validation par l\'établissement.',
        })

    except Exception as e:
        logger.exception("api_parent_payment_submit error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
