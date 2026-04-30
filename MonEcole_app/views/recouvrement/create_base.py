"""
Recouvrement — Page rendering views (create_base).
Ported from standalone _recouvrement-main with multi-tenant scoping.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.db.models import Sum, Count, Q
import logging
import datetime
import os

from MonEcole_app.models import (
    Annee, Campus, Eleve_inscription, Eleve, Institution,
)
from MonEcole_app.models.recouvrement import (
    VariableCategorie, Variable, VariablePrix, VariableDatebutoire,
    VariableDerogation, Eleve_reduction_prix, Paiement, PenaliteConfig,
    Banque, Compte, CategorieOperation, OperationCaisse,
)
from MonEcole_app.models.country_structure import Cycle
from MonEcole_app.models.classe import Classe
from .helpers import _get_tenant, _require_tenant, _tenant_error, logger


# ============================================================
#  DASHBOARD (page d'accueil Recouvrement)
# ============================================================

@login_required(login_url='login')
def rec_dashboard(request):
    """Données du dashboard recouvrement — rendu via template principal."""
    id_pays, id_etablissement = _require_tenant(request)
    if not id_pays:
        return _tenant_error()
    return JsonResponse({'success': True, 'message': 'Dashboard loaded'})


@login_required(login_url='login')
def rec_dashboard_data(request):
    """API JSON — statistiques globales du dashboard recouvrement."""
    id_pays, id_etablissement = _require_tenant(request)
    if not id_pays:
        return _tenant_error()

    annee_id = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    eleve_id = request.GET.get('eleve')
    variable_id = request.GET.get('variable')

    if not annee_id:
        return JsonResponse({'success': False, 'error': 'Année requise'})

    # Élèves inscrits — scoped
    eleves_qs = Eleve_inscription.objects.filter(
        id_annee_id=annee_id, status=True,
        id_pays=id_pays, id_etablissement=id_etablissement
    )
    if classe_id:
        eleves_qs = eleves_qs.filter(id_classe_id=int(classe_id))
    if eleve_id:
        eleves_qs = eleves_qs.filter(id_eleve_id=int(eleve_id))

    eleves_ids = list(eleves_qs.values_list('id_eleve_id', flat=True).distinct())
    if not eleves_ids:
        return JsonResponse({
            'success': True,
            'stats': {
                'total_transactions': 0, 'total_paye': 0, 'total_attendu': 0,
                'reste_a_payer': 0, 'eleves_en_dette': 0, 'total_rejete': 0
            }
        })

    # Variables prix — scoped
    v_prix_qs = VariablePrix.objects.filter(
        id_annee_id=annee_id,
        id_pays=id_pays, id_etablissement=id_etablissement
    )
    if classe_id:
        v_prix_qs = v_prix_qs.filter(id_classe_id=int(classe_id))
    if variable_id:
        v_prix_qs = v_prix_qs.filter(id_variable_id=int(variable_id))

    variables_prix_list = list(v_prix_qs)
    v_ids = [vp.id_variable_id for vp in variables_prix_list]

    # Paiements aggregates — scoped
    paiements_stats = Paiement.objects.filter(
        id_annee_id=annee_id,
        id_eleve_id__in=eleves_ids,
        id_variable_id__in=v_ids,
        id_pays=id_pays, id_etablissement=id_etablissement
    ).aggregate(
        total_p=Sum('montant', filter=Q(status=True, is_rejected=False)),
        total_t=Count('id_paiement', filter=Q(status=True)),
        total_r=Count('id_paiement', filter=Q(is_rejected=True))
    )

    total_paye = paiements_stats['total_p'] or 0
    total_transactions = paiements_stats['total_t'] or 0
    total_rejete = paiements_stats['total_r'] or 0

    # Réductions
    reductions = Eleve_reduction_prix.objects.filter(
        id_annee_id=annee_id, id_eleve_id__in=eleves_ids, id_variable_id__in=v_ids,
        id_pays=id_pays, id_etablissement=id_etablissement
    ).values('id_eleve_id', 'id_variable_id', 'pourcentage')
    red_map = {(r['id_eleve_id'], r['id_variable_id']): r['pourcentage'] for r in reductions}

    # Total attendu
    total_attendu = 0
    num_eleves = len(eleves_ids)
    for vp in variables_prix_list:
        base_prix = vp.prix
        somme_reduction_variable = sum(
            (base_prix * red_map.get((eid, vp.id_variable_id), 0) / 100) for eid in eleves_ids
        )
        total_attendu += (base_prix * num_eleves) - somme_reduction_variable

    # Élèves en dette
    paid_map = {}
    paid_qs = Paiement.objects.filter(
        id_annee_id=annee_id, id_eleve_id__in=eleves_ids, id_variable_id__in=v_ids,
        status=True, is_rejected=False,
        id_pays=id_pays, id_etablissement=id_etablissement
    ).values('id_eleve_id', 'id_variable_id').annotate(total=Sum('montant'))
    for p in paid_qs:
        paid_map[(p['id_eleve_id'], p['id_variable_id'])] = p['total']

    eleves_en_dette_count = 0
    for eid in eleves_ids:
        for vp in variables_prix_list:
            expected = vp.prix * (1 - red_map.get((eid, vp.id_variable_id), 0) / 100)
            paid = paid_map.get((eid, vp.id_variable_id), 0)
            if paid < expected:
                eleves_en_dette_count += 1
                break

    reste_a_payer = max(total_attendu - total_paye, 0)

    return JsonResponse({
        'success': True,
        'stats': {
            'total_transactions': total_transactions,
            'total_paye': total_paye,
            'total_attendu': total_attendu,
            'reste_a_payer': reste_a_payer,
            'eleves_en_dette': eleves_en_dette_count,
            'total_rejete': total_rejete
        }
    })


@login_required(login_url='login')
def rec_dashboard_details(request):
    """API JSON — détails du dashboard (dette, reste, paiements)."""
    id_pays, id_etablissement = _require_tenant(request)
    if not id_pays:
        return _tenant_error()

    annee = request.GET.get('annee')
    classe_id = request.GET.get('classe')
    variable_id = request.GET.get('variable')
    type_stat = request.GET.get('type')
    eleve_id = request.GET.get('eleve')

    if not annee:
        return JsonResponse({'success': False, 'rows': []})

    rows = []
    title = ""

    # Élèves
    eleves = Eleve_inscription.objects.filter(
        id_annee_id=annee, status=True,
        id_pays=id_pays, id_etablissement=id_etablissement
    )
    if classe_id:
        eleves = eleves.filter(id_classe_id=int(classe_id))
    if eleve_id:
        eleves = eleves.filter(id_eleve_id=int(eleve_id))

    # Variables
    variables_prix = VariablePrix.objects.filter(
        id_annee_id=annee,
        id_pays=id_pays, id_etablissement=id_etablissement
    )
    if classe_id:
        variables_prix = variables_prix.filter(id_classe_id=int(classe_id))
    if variable_id:
        variables_prix = variables_prix.filter(id_variable_id=int(variable_id))

    def get_classe_nom(vp):
        try:
            return f"{vp.idCampus.campus} - {vp.id_classe.classe}"
        except Exception:
            return "-"

    if type_stat == "dette":
        title = "Élèves en dette"
        for vp in variables_prix:
            prix = vp.prix
            for e in eleves:
                reduction = Eleve_reduction_prix.objects.filter(
                    id_variable_id=vp.id_variable_id,
                    id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee,
                    id_pays=id_pays, id_etablissement=id_etablissement
                ).first()
                attendu = prix
                if reduction:
                    attendu -= (prix * reduction.pourcentage) / 100
                total_paye = Paiement.objects.filter(
                    id_variable_id=vp.id_variable_id,
                    id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee,
                    status=True, is_rejected=False,
                    id_pays=id_pays, id_etablissement=id_etablissement
                ).aggregate(total=Sum('montant'))['total'] or 0
                reste = attendu - total_paye
                if reste > 0:
                    rows.append({
                        "classe": get_classe_nom(vp),
                        "nom": f"{e.id_eleve.nom} {e.id_eleve.prenom}",
                        "variable": vp.id_variable.variable,
                        "total": reste
                    })

    elif type_stat == "reste":
        title = "Reste à payer par variable"
        for vp in variables_prix:
            reste_global = 0
            prix = vp.prix
            for e in eleves:
                reduction = Eleve_reduction_prix.objects.filter(
                    id_variable_id=vp.id_variable_id,
                    id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee,
                    id_pays=id_pays, id_etablissement=id_etablissement
                ).first()
                attendu = prix
                if reduction:
                    attendu -= (prix * reduction.pourcentage) / 100
                total_paye = Paiement.objects.filter(
                    id_variable_id=vp.id_variable_id,
                    id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee,
                    status=True, is_rejected=False,
                    id_pays=id_pays, id_etablissement=id_etablissement
                ).aggregate(total=Sum('montant'))['total'] or 0
                reste_global += max(attendu - total_paye, 0)
            rows.append({
                "classe": get_classe_nom(vp),
                "variable": vp.id_variable.variable,
                "total": reste_global
            })

    elif type_stat == "transactions":
        title = "Nombre de paiements par variable"
        for vp in variables_prix:
            qs = Paiement.objects.filter(
                id_variable_id=vp.id_variable_id,
                id_annee_id=annee,
                status=True, is_rejected=False,
                id_pays=id_pays, id_etablissement=id_etablissement
            )
            if classe_id:
                qs = qs.filter(id_classe_id=int(classe_id))
            rows.append({
                "classe": get_classe_nom(vp),
                "variable": vp.id_variable.variable,
                "total": qs.count()
            })

    elif type_stat == "paye":
        title = "Montants payés"
        for vp in variables_prix:
            for e in eleves:
                paiements_qs = Paiement.objects.filter(
                    id_variable_id=vp.id_variable_id,
                    id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee,
                    status=True, is_rejected=False,
                    id_pays=id_pays, id_etablissement=id_etablissement
                )
                total_montant = paiements_qs.aggregate(total=Sum('montant'))['total'] or 0
                if total_montant > 0:
                    rows.append({
                        "classe": get_classe_nom(vp),
                        "nom": f"{e.id_eleve.nom} {e.id_eleve.prenom}",
                        "variable": vp.id_variable.variable,
                        "total": total_montant
                    })

    elif type_stat == "attendu":
        title = "Montant attendu par variable"
        for vp in variables_prix:
            total_att = 0
            prix = vp.prix
            for e in eleves:
                reduction = Eleve_reduction_prix.objects.filter(
                    id_variable_id=vp.id_variable_id,
                    id_eleve_id=e.id_eleve_id,
                    id_annee_id=annee,
                    id_pays=id_pays, id_etablissement=id_etablissement
                ).first()
                att = prix
                if reduction:
                    att -= (prix * reduction.pourcentage) / 100
                total_att += att
            rows.append({
                "classe": get_classe_nom(vp),
                "variable": vp.id_variable.variable,
                "total": total_att
            })

    return JsonResponse({'success': True, 'title': title, 'rows': rows})
