"""
Recouvrement — Update views.
Ported from standalone with id_pays + id_etablissement scoping.
"""
import json
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from datetime import datetime, date
import os

from MonEcole_app.models.recouvrement import (
    VariableCategorie, Variable, VariablePrix, VariableDatebutoire,
    VariableDerogation, Eleve_reduction_prix, Paiement,
    Banque, Compte,
)
from .helpers import _require_tenant, _tenant_error, logger


@csrf_protect
@login_required(login_url='login')
def rec_update_paiement_field(request):
    """Valider ou rejeter un paiement."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        id_paiement = request.POST.get('id_paiement')
        field = request.POST.get('field')
        value = request.POST.get('value') == 'true'
        if field not in ('status', 'is_rejected'):
            return JsonResponse({'success': False, 'error': 'Champ non valide'}, status=400)
        p = Paiement.objects.get(id_paiement=id_paiement, id_pays=id_pays, id_etablissement=id_etab)
        setattr(p, field, value)
        p.save()
        return JsonResponse({'success': True})
    except Paiement.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Paiement non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_protect
@login_required(login_url='login')
def rec_update_categorie(request, categorie_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        cat = VariableCategorie.objects.get(
            id_variable_categorie=categorie_id, id_pays=id_pays, id_etablissement=id_etab
        )
        new_name = request.POST.get('nom', '').strip()
        if not new_name:
            return JsonResponse({'success': False, 'error': 'Nom requis'})
        cat.nom = new_name
        cat.save()
        return JsonResponse({'success': True})
    except VariableCategorie.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Catégorie non trouvée'}, status=404)


@csrf_protect
@login_required(login_url='login')
def rec_update_variable(request, variable_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        v = Variable.objects.get(id_variable=variable_id, id_pays=id_pays, id_etablissement=id_etab)
        new_name = request.POST.get('variable', '').strip()
        categorie_id = request.POST.get('categorie_id')
        if not all([new_name, categorie_id]):
            return JsonResponse({'success': False, 'error': 'Champs requis'})
        v.variable = new_name
        v.id_variable_categorie_id = categorie_id
        v.save()
        return JsonResponse({'success': True})
    except Variable.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Variable non trouvée'}, status=404)


@csrf_protect
@login_required(login_url='login')
def rec_update_banque(request, banque_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        b = Banque.objects.get(id_banque=banque_id, id_pays=id_pays, id_etablissement=id_etab)
        b.banque = request.POST.get('banque', b.banque)
        b.sigle = request.POST.get('sigle', b.sigle)
        b.save()
        return JsonResponse({'success': True})
    except Banque.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Banque non trouvée'}, status=404)


@csrf_protect
@login_required(login_url='login')
def rec_update_compte(request, compte_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        c = Compte.objects.get(id_compte=compte_id, id_pays=id_pays, id_etablissement=id_etab)
        c.compte = request.POST.get('compte', c.compte)
        banque_id = request.POST.get('banque_id')
        if banque_id:
            c.id_banque_id = banque_id
        c.save()
        return JsonResponse({'success': True})
    except Compte.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Compte non trouvé'}, status=404)


@csrf_protect
@login_required(login_url='login')
def rec_update_paiement(request, id_paiement):
    """Modifier montant/date/bordereau d'un paiement existant."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        p = Paiement.objects.get(id_paiement=id_paiement, id_pays=id_pays, id_etablissement=id_etab)
        montant = request.POST.get('montant')
        date_paie = request.POST.get('date_paie')
        bordereau = request.FILES.get('bordereau')
        if not montant:
            return JsonResponse({'success': False, 'error': 'Montant requis'})
        montant = int(montant)
        if date_paie:
            date_paie = datetime.strptime(date_paie, '%Y-%m-%d').date()
            if date_paie > date.today():
                return JsonResponse({'success': False, 'error': 'Date future non autorisée'})
        else:
            date_paie = p.date_paie

        # Vérification cumul
        vp = VariablePrix.objects.filter(
            id_variable_id=p.id_variable_id, id_annee_id=p.id_annee_id,
            id_classe_id=p.id_classe_id,
            id_pays=id_pays, id_etablissement=id_etab
        ).first()
        if vp:
            prix_max = vp.prix
            reduction = Eleve_reduction_prix.objects.filter(
                id_eleve_id=p.id_eleve_id, id_variable_id=p.id_variable_id,
                id_annee_id=p.id_annee_id,
                id_pays=id_pays, id_etablissement=id_etab
            ).first()
            montant_autorise = prix_max
            if reduction:
                montant_autorise -= (prix_max * reduction.pourcentage) / 100
            total_deja = Paiement.objects.filter(
                id_eleve_id=p.id_eleve_id, id_variable_id=p.id_variable_id,
                status=True, id_pays=id_pays, id_etablissement=id_etab
            ).exclude(id_paiement=id_paiement).aggregate(total=Sum('montant'))['total'] or 0
            if total_deja + montant > montant_autorise:
                return JsonResponse({'success': False, 'error': f'Dépassement. Max: {montant_autorise - total_deja}'})

        p.montant = montant
        p.date_paie = date_paie
        if bordereau:
            new_name = f"{bordereau.name}_{p.id_paiement}"
            p.bordereau.save(new_name, bordereau, save=False)
        p.save()
        return JsonResponse({'success': True})
    except Paiement.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Paiement non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
@login_required(login_url='login')
def rec_suivi_reduction_update(request, pk):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        r = Eleve_reduction_prix.objects.get(id_reduction_prix=pk, id_pays=id_pays, id_etablissement=id_etab)
        r.pourcentage = request.POST.get('statut', r.pourcentage)
        r.save()
        return JsonResponse({'success': True})
    except Eleve_reduction_prix.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Réduction introuvable'}, status=404)


@require_POST
@login_required(login_url='login')
def rec_suivi_derogation_update(request, pk):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        d = VariableDerogation.objects.get(id_derogation=pk, id_pays=id_pays, id_etablissement=id_etab)
        d.date_derogation = request.POST.get('statut', d.date_derogation)
        d.save()
        return JsonResponse({'success': True})
    except VariableDerogation.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Dérogation introuvable'}, status=404)


@require_POST
@login_required(login_url='login')
def rec_update_date_butoire(request, pk):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        obj = VariableDatebutoire.objects.get(id_datebutoire=pk, id_pays=id_pays, id_etablissement=id_etab)
        obj.date_butoire = request.POST.get('date_butoire', obj.date_butoire)
        obj.save()
        return JsonResponse({'success': True})
    except VariableDatebutoire.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Date butoire introuvable'}, status=404)


@csrf_exempt
@login_required(login_url='login')
def rec_update_variable_obligatoire(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        # Support both JSON body and form data
        if request.content_type and 'json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST
        var_id = data.get('id_variable')
        val = data.get('estObligatoire')
        if isinstance(val, str):
            val = val.lower() in ('true', '1', 'yes')
        v = Variable.objects.get(id_variable=var_id, id_pays=id_pays, id_etablissement=id_etab)
        v.estObligatoire = bool(val)
        v.save()
        return JsonResponse({'success': True})
    except Variable.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Variable non trouvée'}, status=404)
