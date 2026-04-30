"""
Recouvrement — Save/write API views.
Ported from standalone with id_pays + id_etablissement scoping.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.db.models import Sum
from datetime import datetime, date
import os, logging

from MonEcole_app.models import Annee, Campus, Eleve_inscription
from MonEcole_app.models.recouvrement import (
    VariableCategorie, Variable, VariablePrix, VariableDatebutoire,
    VariableDerogation, Eleve_reduction_prix, Paiement, PenaliteConfig,
    Banque, Compte, CategorieOperation, OperationCaisse,
)
from .helpers import _require_tenant, _tenant_error, logger


# ============================================================
#  CATÉGORIE VARIABLE
# ============================================================

@csrf_protect
@login_required(login_url='login')
def rec_save_categorie_variable(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    nom = request.POST.get('nom', '').strip()
    if not nom:
        return JsonResponse({'success': False, 'error': 'Nom requis'}, status=400)
    cat = VariableCategorie(nom=nom, id_pays=id_pays, id_etablissement=id_etab)
    cat.save()
    return JsonResponse({'success': True, 'id': cat.id_variable_categorie, 'nom': cat.nom})


@csrf_protect
@login_required(login_url='login')
def rec_save_variable(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    variable_name = request.POST.get('variable', '').strip()
    categorie_id = request.POST.get('id_variable_categorie')
    if not all([variable_name, categorie_id]):
        return JsonResponse({'success': False, 'error': 'Champs requis'}, status=400)
    v = Variable(variable=variable_name, id_variable_categorie_id=categorie_id,
                 id_pays=id_pays, id_etablissement=id_etab)
    v.save()
    return JsonResponse({'success': True, 'id': v.id_variable})


# ============================================================
#  BANQUE / COMPTE
# ============================================================

@csrf_protect
@login_required(login_url='login')
def rec_save_banque(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    banque_nom = request.POST.get('banque', '').strip()
    sigle = request.POST.get('sigle', '').strip()
    if not banque_nom:
        return JsonResponse({'success': False, 'error': 'Nom banque requis'}, status=400)
    b = Banque(banque=banque_nom, sigle=sigle, id_pays=id_pays, id_etablissement=id_etab)
    b.save()
    return JsonResponse({'success': True, 'id': b.id_banque})


@csrf_protect
@login_required(login_url='login')
def rec_save_compte(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    compte_nom = request.POST.get('compte', '').strip()
    banque_id = request.POST.get('id_banque')
    if not all([compte_nom, banque_id]):
        return JsonResponse({'success': False, 'error': 'Champs requis'}, status=400)
    c = Compte(compte=compte_nom, id_banque_id=banque_id, id_pays=id_pays, id_etablissement=id_etab)
    c.save()
    return JsonResponse({'success': True, 'id': c.id_compte})


# ============================================================
#  VARIABLE PRIX
# ============================================================

@csrf_protect
@login_required(login_url='login')
def rec_save_variable_prix(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        annee_id = request.POST.get('id_annee')
        classe_id = request.POST.get('id_classe')
        variable_id = request.POST.get('id_variable')
        campus_id = request.POST.get('idCampus')
        cycle_id = request.POST.get('id_cycle')
        prix = request.POST.get('prix')
        groupe = request.POST.get('groupe', '')
        if not all([annee_id, classe_id, variable_id, prix]):
            return JsonResponse({'success': False, 'error': 'Champs obligatoires manquants'}, status=400)
        vp, created = VariablePrix.objects.update_or_create(
            id_annee_id=annee_id, id_classe_id=classe_id, id_variable_id=variable_id,
            id_pays=id_pays, id_etablissement=id_etab,
            defaults={
                'idCampus_id': campus_id if campus_id else None,
                'id_cycle_id': cycle_id if cycle_id else None,
                'prix': int(prix),
                'groupe': groupe or None,
            }
        )
        return JsonResponse({'success': True, 'created': created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================
#  PAIEMENT
# ============================================================

@csrf_protect
@login_required(login_url='login')
def rec_save_paiement(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        annee_id = request.POST.get('id_annee')
        classe_id = request.POST.get('id_classe')
        eleve_id = request.POST.get('id_eleve')
        variable_id = request.POST.get('id_variable')
        compte_id = request.POST.get('id_compte')
        montant = request.POST.get('montant')
        date_paie = request.POST.get('date_paie')
        campus_id = request.POST.get('idCampus')
        cycle_id = request.POST.get('id_cycle')
        groupe = request.POST.get('groupe', '')
        bordereau = request.FILES.get('bordereau')

        if not all([annee_id, classe_id, eleve_id, variable_id, compte_id, montant, date_paie]):
            return JsonResponse({'success': False, 'error': 'Champs obligatoires manquants'}, status=400)

        montant = int(montant)
        date_paie_obj = datetime.strptime(date_paie, '%Y-%m-%d').date()
        if date_paie_obj > date.today():
            return JsonResponse({'success': False, 'error': 'Date future non autorisée'})

        # Déterminer banque depuis le compte
        try:
            compte = Compte.objects.get(id_compte=compte_id, id_pays=id_pays, id_etablissement=id_etab)
        except Compte.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Compte non trouvé'}, status=404)
        banque_id = compte.id_banque_id

        # Vérifier prix variable
        vp = VariablePrix.objects.filter(
            id_variable_id=variable_id, id_annee_id=annee_id, id_classe_id=classe_id,
            id_pays=id_pays, id_etablissement=id_etab
        ).first()
        if not vp:
            return JsonResponse({'success': False, 'error': 'Aucun prix défini pour cette variable'}, status=400)
        prix_max = vp.prix

        # Réduction
        reduction = Eleve_reduction_prix.objects.filter(
            id_eleve_id=eleve_id, id_variable_id=variable_id, id_annee_id=annee_id,
            id_pays=id_pays, id_etablissement=id_etab
        ).first()
        montant_autorise = prix_max
        if reduction:
            montant_autorise -= (prix_max * reduction.pourcentage) / 100

        # Cumul
        total_deja = Paiement.objects.filter(
            id_eleve_id=eleve_id, id_variable_id=variable_id,
            id_pays=id_pays, id_etablissement=id_etab
        ).aggregate(total=Sum('montant'))['total'] or 0

        if total_deja + montant > montant_autorise:
            restant = montant_autorise - total_deja
            return JsonResponse({'success': False, 'error': f'Dépassement. Reste à payer: {restant}'})

        paiement = Paiement(
            id_variable_id=variable_id, montant=montant,
            id_banque_id=banque_id, id_compte_id=compte_id,
            date_paie=date_paie_obj, id_eleve_id=eleve_id,
            idCampus_id=campus_id, id_annee_id=annee_id,
            id_cycle_id=cycle_id, id_classe_id=classe_id,
            groupe=groupe or None, status=True,
            id_pays=id_pays, id_etablissement=id_etab
        )
        paiement.save()
        if bordereau:
            ext = os.path.splitext(bordereau.name)[1]
            new_name = f"{bordereau.name}_{paiement.id_paiement}"
            paiement.bordereau.save(new_name, bordereau, save=True)
        return JsonResponse({'success': True, 'id': paiement.id_paiement})
    except Exception as e:
        logger.error(f"rec_save_paiement: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================
#  DÉROGATION / RÉDUCTION / DATE BUTOIRE
# ============================================================

@csrf_protect
@login_required(login_url='login')
def rec_save_derogation(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        annee_id = request.POST.get('id_annee')
        classe_id = request.POST.get('id_classe')
        eleve_id = request.POST.get('id_eleve')
        variable_id = request.POST.get('id_variable')
        date_derog = request.POST.get('date_butoire')
        campus_id = request.POST.get('idCampus')
        cycle_id = request.POST.get('id_cycle')
        if not all([annee_id, classe_id, eleve_id, date_derog]):
            return JsonResponse({'success': False, 'error': 'Champs requis'}, status=400)
        date_obj = datetime.strptime(date_derog, '%Y-%m-%d').date()
        if date_obj < date.today():
            return JsonResponse({'success': False, 'error': 'Date passée non autorisée'}, status=400)
        obj, created = VariableDerogation.objects.update_or_create(
            id_eleve_id=eleve_id, id_annee_id=annee_id,
            id_classe_id=classe_id, id_variable_id=variable_id,
            id_pays=id_pays, id_etablissement=id_etab,
            defaults={
                'idCampus_id': campus_id, 'id_cycle_id': cycle_id,
                'date_derogation': date_obj,
            }
        )
        return JsonResponse({'success': True, 'updated': not created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_protect
@login_required(login_url='login')
def rec_save_reduction(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        annee_id = request.POST.get('id_annee')
        classe_id = request.POST.get('id_classe')
        eleve_id = request.POST.get('id_eleve')
        variable_id = request.POST.get('id_variable')
        pourcentage = request.POST.get('pourcentage')
        campus_id = request.POST.get('idCampus')
        cycle_id = request.POST.get('id_cycle')
        if not all([annee_id, classe_id, eleve_id, pourcentage]):
            return JsonResponse({'success': False, 'error': 'Champs requis'}, status=400)
        obj, created = Eleve_reduction_prix.objects.update_or_create(
            id_eleve_id=eleve_id, id_annee_id=annee_id,
            id_classe_id=classe_id, id_variable_id=variable_id,
            id_pays=id_pays, id_etablissement=id_etab,
            defaults={
                'idCampus_id': campus_id, 'id_cycle_id': cycle_id,
                'pourcentage': int(pourcentage),
            }
        )
        return JsonResponse({'success': True, 'updated': not created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_protect
@login_required(login_url='login')
def rec_save_date_butoire(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        annee_id = request.POST.get('id_annee')
        classe_id = request.POST.get('id_classe')
        variable_id = request.POST.get('id_variable')
        date_but = request.POST.get('date_butoire')
        campus_id = request.POST.get('idCampus')
        cycle_id = request.POST.get('id_cycle')
        if not all([annee_id, classe_id, date_but]):
            return JsonResponse({'success': False, 'error': 'Champs requis'}, status=400)
        date_obj = datetime.strptime(date_but, '%Y-%m-%d').date()
        obj, created = VariableDatebutoire.objects.update_or_create(
            id_annee_id=annee_id, id_classe_id=classe_id,
            id_variable_id=variable_id,
            id_pays=id_pays, id_etablissement=id_etab,
            defaults={
                'idCampus_id': campus_id, 'id_cycle_id': cycle_id,
                'date_butoire': date_obj,
            }
        )
        return JsonResponse({'success': True, 'updated': not created})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================
#  PÉNALITÉ
# ============================================================

@csrf_protect
@login_required(login_url='login')
def rec_save_penalite(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        annee_id = request.POST.get('id_annee')
        type_pen = request.POST.get('type_penalite')
        valeur = request.POST.get('valeur')
        plafond = request.POST.get('plafond')
        variable_id = request.POST.get('id_variable')
        campus_id = request.POST.get('idCampus')
        cycle_id = request.POST.get('id_cycle')
        classe_id = request.POST.get('id_classe')
        if not all([annee_id, type_pen, valeur]):
            return JsonResponse({'success': False, 'error': 'Champs requis'}, status=400)
        pen = PenaliteConfig(
            id_annee_id=annee_id, type_penalite=type_pen,
            valeur=float(valeur), plafond=int(plafond) if plafond else None,
            id_variable_id=variable_id if variable_id else None,
            idCampus_id=campus_id if campus_id else None,
            id_cycle_id=cycle_id if cycle_id else None,
            id_classe_id=classe_id if classe_id else None,
            id_pays=id_pays, id_etablissement=id_etab
        )
        pen.save()
        return JsonResponse({'success': True}, status=201)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ============================================================
#  CATÉGORIE OPÉRATION / OPÉRATION CAISSE
# ============================================================

@csrf_protect
@login_required(login_url='login')
def rec_save_categorie_operation(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        annee_id = request.POST.get('id_annee')
        campus_id = request.POST.get('idCampus')
        type_op = request.POST.get('type_operation')
        nom = request.POST.get('nom', '').strip()
        description = request.POST.get('description', '')
        if not all([annee_id, campus_id, type_op, nom]):
            return JsonResponse({'success': False, 'error': 'Champs obligatoires manquants'}, status=400)
        if type_op not in ('ENTREE', 'SORTIE'):
            return JsonResponse({'success': False, 'error': 'Type invalide'}, status=400)
        if CategorieOperation.objects.filter(
            id_annee_id=annee_id, idCampus_id=campus_id,
            type_operation=type_op, nom__iexact=nom,
            id_pays=id_pays, id_etablissement=id_etab
        ).exists():
            return JsonResponse({'success': False, 'error': 'Catégorie déjà existante'}, status=400)
        cat = CategorieOperation(
            id_annee_id=annee_id, idCampus_id=campus_id,
            type_operation=type_op, nom=nom, description=description,
            est_active=True, id_pays=id_pays, id_etablissement=id_etab
        )
        cat.save()
        return JsonResponse({'success': True, 'id': cat.id_categorie, 'nom': cat.nom}, status=201)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_protect
@login_required(login_url='login')
def rec_save_operation_caisse(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        annee_id = request.POST.get('id_annee')
        campus_id = request.POST.get('idCampus')
        categorie_id = request.POST.get('categorie')
        montant = request.POST.get('montant')
        date_op = request.POST.get('date_operation')
        description = request.POST.get('description', '')
        source = request.POST.get('source_beneficiaire', '')
        mode = request.POST.get('mode_paiement')
        reference = request.POST.get('reference', '')
        justificatif = request.FILES.get('justificatif')
        if not all([annee_id, campus_id, categorie_id, montant, date_op, mode]):
            return JsonResponse({'success': False, 'error': 'Champs obligatoires manquants'}, status=400)
        montant_f = float(montant)
        if montant_f <= 0:
            return JsonResponse({'success': False, 'error': 'Montant positif requis'}, status=400)
        date_obj = datetime.strptime(date_op, '%Y-%m-%d').date()
        op = OperationCaisse(
            id_annee_id=annee_id, idCampus_id=campus_id,
            categorie_id=categorie_id, montant=int(montant_f),
            date_operation=date_obj, description=description,
            source_beneficiaire=source, mode_paiement=mode,
            reference=reference, justificatif=justificatif,
            id_pays=id_pays, id_etablissement=id_etab
        )
        op.save()
        return JsonResponse({'success': True, 'id': op.id_operation}, status=201)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_protect
@login_required(login_url='login')
def rec_delete_paiement(request, id_paiement):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        p = Paiement.objects.get(id_paiement=id_paiement, id_pays=id_pays, id_etablissement=id_etab)
        p.status = False
        p.save()
        return JsonResponse({'success': True})
    except Paiement.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Paiement non trouvé'}, status=404)


@csrf_protect
@login_required(login_url='login')
def rec_delete_operation(request, id_operation):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST requis'}, status=405)
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    try:
        op = OperationCaisse.objects.get(id_operation=id_operation, id_pays=id_pays, id_etablissement=id_etab)
        op.delete()
        return JsonResponse({'success': True})
    except OperationCaisse.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Opération non trouvée'}, status=404)
