from django.contrib.auth.decorators import login_required
from MonEcole_app.views.decorators.decorators import module_required
from MonEcole_app.views import get_user_info
from django.shortcuts import render,redirect
from django.contrib import messages
from MonEcole_app.forms import (VariableCategorieForm,VariableCategorie,Variable,
                                VariableForm,BanqueForm,CompteForm,Compte,Banque,
                                VariablePrixForm,VariablePrix,VariableDerogationForm,
                                VariableDerogation,VariableReductionForm,Eleve_reduction_prix,
                                VariableDatebutoire,VariableDateButoireForm,PaiementForm,Paiement)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect,csrf_exempt
from django.shortcuts import get_object_or_404
from MonEcole_app.models import Classe_active,Annee
from MonEcole_app.views.tools.tenant_utils import (
    tenant_etablissement_filter, get_tenant_campus_ids, validate_campus_access
)

import logging

logger = logging.getLogger(__name__)
import os


@login_required
@module_required("Recouvrement")
def ajouter_categorie_variable(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        form = VariableCategorieForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"La categorie créee avec succès")
            return redirect('categorie_variable')
    else:
        form = VariableCategorieForm()
    variablesCategories = VariableCategorie.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'variable_categorie': variablesCategories,
        'form_variable_categorie': form,
        'form_type': 'variablecategorie_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']

    })
    
    
@login_required
@module_required("Recouvrement")
def ajouter_variable(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        form = VariableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"La variable  créee avec succès")
            return redirect('create_variable_frais')
    else:
        form = VariableForm()
    variablesList = Variable.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'variableList': variablesList,
        'form_variable': form,
        'form_type': 'variable_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']

    })
    
    
    
@login_required
@module_required("Recouvrement")
def ajouter_banque_epargne(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        form = BanqueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"La Banque a été créee avec succès")
            return redirect('create_banque')
    else:
        form = BanqueForm()
    banqueList = Banque.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'banque_list': banqueList,
        'form_banque': form,
        'form_type': 'banque_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']

    })

@login_required
@module_required("Recouvrement")
def ajouter_compte_epargne(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        compte = request.POST.get('compte')
        form = CompteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Le compte a été créee avec succès")
            return redirect('create_compte')
    else:
        form = CompteForm()
    compteList = Compte.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'compte_list': compteList,
        'form_compte': form,
        'form_type': 'compte_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']

    })
    



@login_required
@module_required("Recouvrement")
def ajouter_variable_prix(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        form = VariablePrixForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Le prix pour la variable choisi a été créee avec succès")
            return redirect('create_compte')
    else:
        form = VariablePrixForm()
    variableprixList = VariablePrix.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'variable_prix_list': variableprixList,
        'form_variable_prix': form,
        'form_type': 'variable_prix_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']

    })

@login_required
@module_required("Recouvrement")
def add_paiement_for_anyclass(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        form = PaiementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Le paiement a été enregistré avec succès")
            return redirect('create_compte')
    else:
        form = PaiementForm()
    paiementList = Paiement.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'paiement_list': paiementList,
        'form_paiement': form,
        'form_type': 'paiement_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })
    


@login_required
@module_required("Recouvrement")
def ajouter_variable_derogation(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form = VariableDerogationForm()
    is_derog = True
    derogationList = VariableDerogation.objects.all()
    variables_list = Variable.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'derogation_list': derogationList,
        'variable_list': variables_list,
        'form_derogation': form,
        'derogationField':is_derog,
        'form_type': 'derogation_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']

    })
    
    
@login_required
@module_required("Recouvrement")
def ajouter_reduction_for_pupil(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form = VariableReductionForm()
    is_reduct = True
    variables_list = Variable.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'variable_list': variables_list,
        'form_reduction': form,
        'reductionField':is_reduct,
        'form_type': 'reduction_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']

    })

@login_required
@module_required("Recouvrement")
def ajouter_date_butoire_for_anyclass(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form = VariableDateButoireForm()
    is_butoire = True
    variables_list = Variable.objects.all()
    return render(request, 'recouvrement/index_recouvrement.html', {
        'variable_list': variables_list,
        'form_butoire': form,
        'butoireField':is_butoire,
        'form_type': 'butoire_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']

    })

@csrf_protect
def save_paiement(request):
    if request.method == 'POST':
        try:
            logger.info(f"Données reçues : {request.POST}, Fichiers : {request.FILES}")
            form = PaiementForm(request.POST, request.FILES)
            if form.is_valid():
                logger.info(f"Données validées : {form.cleaned_data}")
                id_annee = form.cleaned_data['id_annee'].id_annee
                id_classe_active = form.cleaned_data['id_classe_active'].id_classe_active
                id_eleve = form.cleaned_data['id_eleve'].id_eleve
                id_variable = form.cleaned_data['id_variable'].id_variable
                id_banque = form.cleaned_data['id_banque'].id_banque
                id_compte = form.cleaned_data['id_compte'].id_compte
                montant = form.cleaned_data['montant']
                date_paie = form.cleaned_data['date_paie']
                bordereau = form.cleaned_data['bordereau']

                if Paiement.objects.filter(
                    id_eleve_id=id_eleve,
                    id_variable_id=id_variable,
                    date_paie=date_paie
                ).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ce paiement existe déjà.'
                    }, status=400)

                try:
                    classe_active = Classe_active.objects.get(id_classe_active=id_classe_active)
                    id_campus = classe_active.id_campus_id
                    id_cycle_actif = classe_active.cycle_id_id
                except Classe_active.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'error': 'Classe active non trouvée.'
                    }, status=404)

                paiement = Paiement(
                    id_variable_id=id_variable,
                    montant=montant,
                    id_banque_id=id_banque,
                    id_compte_id=id_compte,
                    date_paie=date_paie,
                    id_eleve_id=id_eleve,
                    id_campus_id=id_campus,
                    id_annee_id=id_annee,
                    id_cycle_actif_id=id_cycle_actif,
                    id_classe_active_id=id_classe_active
                )

                if bordereau:
                    paiement.save()
                    file_extension = os.path.splitext(bordereau.name)[1]  
                    new_filename = f"{bordereau.name}_{paiement.id_paiement}"
                    paiement.bordereau.save(new_filename, bordereau, save=False)
                    paiement.bordereau.name = new_filename
                    paiement.save()
                else:
                    paiement.save()

                logger.info(f"Paiement enregistré: id={paiement.id_paiement}, eleve={id_eleve}, annee={id_annee}, campus={id_campus}, cycle={id_cycle_actif}, classe={id_classe_active}, variable={id_variable}, montant={montant}, banque={id_banque}, compte={id_compte}, date={date_paie}, bordereau={paiement.bordereau.name if paiement.bordereau else None}")

                return JsonResponse({'success': True})
            else:
                errors = form.errors.as_json()
                logger.warning(f"Erreurs de validation du formulaire Paiement: {errors}")
                return JsonResponse({
                    'success': False,
                    'error': 'Erreurs de validation du formulaire.',
                    'details': errors
                }, status=400)
        except Exception as e:
            logger.error(f"Erreur dans save_paiement: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Une erreur est survenue lors de l\'enregistrement : {str(e)}'
            }, status=500)
    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée.'
    }, status=405)

