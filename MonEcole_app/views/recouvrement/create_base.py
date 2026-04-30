"""
Recouvrement — Dashboard stats views.
Uses HUB for years/classes, SPOKE for financial data.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Count, Q

from MonEcole_app.models.eleves.eleve import Eleve_inscription
from MonEcole_app.models.recouvrement import (
    VariablePrix, Eleve_reduction_prix, Paiement,
)
from .helpers import (
    _require_tenant, _tenant_error, logger,
    get_hub_classe_name,
)


@login_required(login_url='login')
def rec_dashboard_data(request):
    """API JSON — statistiques globales du dashboard recouvrement."""
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('annee')
    if not annee_id:
        return JsonResponse({'success': False, 'error': 'Année requise'})
    empty = {'success': True, 'stats': {
        'total_transactions': 0, 'total_paye': 0, 'total_attendu': 0,
        'reste_a_payer': 0, 'eleves_en_dette': 0, 'total_rejete': 0
    }}

    # Élèves inscrits (spoke)
    eleves_ids = list(Eleve_inscription.objects.filter(
        id_annee_id=annee_id, status=True,
        id_pays=id_pays, id_etablissement=id_etab
    ).values_list('id_eleve_id', flat=True).distinct())
    if not eleves_ids:
        return JsonResponse(empty)

    # Variables prix (spoke)
    v_prix_qs = VariablePrix.objects.filter(
        id_annee_id=annee_id, id_pays=id_pays, id_etablissement=id_etab
    )
    variables_prix_list = list(v_prix_qs)
    v_ids = [vp.id_variable_id for vp in variables_prix_list]
    if not v_ids:
        return JsonResponse(empty)

    # Paiements (spoke)
    paiements_stats = Paiement.objects.filter(
        id_annee_id=annee_id, id_eleve_id__in=eleves_ids, id_variable_id__in=v_ids,
        id_pays=id_pays, id_etablissement=id_etab
    ).aggregate(
        total_p=Sum('montant', filter=Q(status=True, is_rejected=False)),
        total_t=Count('id_paiement', filter=Q(status=True)),
        total_r=Count('id_paiement', filter=Q(is_rejected=True))
    )
    total_paye = paiements_stats['total_p'] or 0
    total_transactions = paiements_stats['total_t'] or 0
    total_rejete = paiements_stats['total_r'] or 0

    # Réductions
    red_map = {}
    for r in Eleve_reduction_prix.objects.filter(
        id_annee_id=annee_id, id_eleve_id__in=eleves_ids, id_variable_id__in=v_ids,
        id_pays=id_pays, id_etablissement=id_etab
    ).values('id_eleve_id', 'id_variable_id', 'pourcentage'):
        red_map[(r['id_eleve_id'], r['id_variable_id'])] = r['pourcentage']

    # Total attendu
    total_attendu = 0
    num_eleves = len(eleves_ids)
    for vp in variables_prix_list:
        base = vp.prix
        red_sum = sum((base * red_map.get((eid, vp.id_variable_id), 0) / 100) for eid in eleves_ids)
        total_attendu += (base * num_eleves) - red_sum

    # Élèves en dette
    paid_map = {}
    for p in Paiement.objects.filter(
        id_annee_id=annee_id, id_eleve_id__in=eleves_ids, id_variable_id__in=v_ids,
        status=True, is_rejected=False, id_pays=id_pays, id_etablissement=id_etab
    ).values('id_eleve_id', 'id_variable_id').annotate(total=Sum('montant')):
        paid_map[(p['id_eleve_id'], p['id_variable_id'])] = p['total']

    eleves_en_dette = 0
    for eid in eleves_ids:
        for vp in variables_prix_list:
            expected = vp.prix * (1 - red_map.get((eid, vp.id_variable_id), 0) / 100)
            if paid_map.get((eid, vp.id_variable_id), 0) < expected:
                eleves_en_dette += 1
                break

    return JsonResponse({'success': True, 'stats': {
        'total_transactions': total_transactions, 'total_paye': total_paye,
        'total_attendu': total_attendu, 'reste_a_payer': max(total_attendu - total_paye, 0),
        'eleves_en_dette': eleves_en_dette, 'total_rejete': total_rejete,
    }})


@login_required(login_url='login')
def rec_dashboard_details(request):
    """API JSON — detail rows for dashboard drill-down."""
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee = request.GET.get('annee')
    type_stat = request.GET.get('type')
    if not annee:
        return JsonResponse({'success': False, 'rows': []})

    eleves = Eleve_inscription.objects.filter(
        id_annee_id=annee, status=True, id_pays=id_pays, id_etablissement=id_etab
    )
    variables_prix = VariablePrix.objects.filter(
        id_annee_id=annee, id_pays=id_pays, id_etablissement=id_etab
    ).select_related('id_variable')

    # Resolve class names from HUB
    classe_names = {}
    for vp in variables_prix:
        cid = vp.id_classe_id
        if cid and cid not in classe_names:
            classe_names[cid] = get_hub_classe_name(cid, id_pays)

    rows = []
    title = ""

    if type_stat == "dette":
        title = "Élèves en dette"
        for vp in variables_prix:
            for e in eleves:
                red = Eleve_reduction_prix.objects.filter(
                    id_variable_id=vp.id_variable_id, id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee, id_pays=id_pays, id_etablissement=id_etab
                ).first()
                attendu = vp.prix - (vp.prix * red.pourcentage / 100 if red else 0)
                paye = Paiement.objects.filter(
                    id_variable_id=vp.id_variable_id, id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee, status=True, is_rejected=False,
                    id_pays=id_pays, id_etablissement=id_etab
                ).aggregate(t=Sum('montant'))['t'] or 0
                reste = attendu - paye
                if reste > 0:
                    rows.append({
                        "classe": classe_names.get(vp.id_classe_id, '-'),
                        "nom": f"{e.id_eleve.nom} {e.id_eleve.prenom}",
                        "variable": vp.id_variable.variable, "total": reste
                    })

    elif type_stat == "transactions":
        title = "Transactions par variable"
        for vp in variables_prix:
            cnt = Paiement.objects.filter(
                id_variable_id=vp.id_variable_id, id_annee_id=annee,
                status=True, is_rejected=False, id_pays=id_pays, id_etablissement=id_etab
            ).count()
            rows.append({
                "classe": classe_names.get(vp.id_classe_id, '-'),
                "variable": vp.id_variable.variable, "total": cnt
            })

    elif type_stat == "paye":
        title = "Montants payés"
        for vp in variables_prix:
            for e in eleves:
                t = Paiement.objects.filter(
                    id_variable_id=vp.id_variable_id, id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee, status=True, is_rejected=False,
                    id_pays=id_pays, id_etablissement=id_etab
                ).aggregate(t=Sum('montant'))['t'] or 0
                if t > 0:
                    rows.append({
                        "classe": classe_names.get(vp.id_classe_id, '-'),
                        "nom": f"{e.id_eleve.nom} {e.id_eleve.prenom}",
                        "variable": vp.id_variable.variable, "total": t
                    })

    elif type_stat == "attendu":
        title = "Montant attendu par variable"
        for vp in variables_prix:
            att = 0
            for e in eleves:
                red = Eleve_reduction_prix.objects.filter(
                    id_variable_id=vp.id_variable_id, id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee, id_pays=id_pays, id_etablissement=id_etab
                ).first()
                att += vp.prix - (vp.prix * red.pourcentage / 100 if red else 0)
            rows.append({
                "classe": classe_names.get(vp.id_classe_id, '-'),
                "variable": vp.id_variable.variable, "total": att
            })

    return JsonResponse({'success': True, 'title': title, 'rows': rows})
