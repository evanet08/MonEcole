from .create_base import *
from MonEcole_app.views.tools.tenant_utils import deny_cross_tenant_access

@login_required
@csrf_protect
def save_variable_prix(request):
    if request.method == 'POST':
        try:

            id_campus = request.POST.get('id_campus')
            id_cycle_actif = request.POST.get('id_cycle_actif')  #
            if not id_campus or not id_cycle_actif:
                return JsonResponse({
                    'success': False,
                    'error': "Champs obligatoires manquants : id_campus ou id_cycle_actif."
                }, status=400)

            try:
                id_campus = int(id_campus)
                id_cycle_actif = int(id_cycle_actif)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'error': "id_campus et id_cycle_actif doivent être des entiers."
                }, status=400)

            # Validation tenant
            denied = deny_cross_tenant_access(request, id_campus)
            if denied:
                return denied

            form = VariablePrixForm(request.POST)
            if not form.is_valid():
                errors = form.errors.as_json()
                return JsonResponse({
                    'success': False,
                    'error': 'Erreurs de validation du formulaire.',
                    'details': errors
                }, status=400)

            id_annee = form.cleaned_data['id_annee']
            id_classe_active = form.cleaned_data['id_classe_active']
            id_variable = form.cleaned_data['id_variable']
            prix = form.cleaned_data['prix']

            if VariablePrix.objects.filter(
                id_annee=id_annee,
                id_classe_active=id_classe_active,
                id_variable=id_variable
            ).exists():
                return JsonResponse({
                    'success': False,
                    'error': "Cette combinaison d'année, classe et variable existe déjà."
                }, status=400)

            try:
                classe_active = Classe_active.objects.get(pk=id_classe_active.pk)
                if classe_active.id_campus_id != id_campus or classe_active.cycle_id_id != id_cycle_actif:
                    return JsonResponse({
                        'success': False,
                        'error': "Les valeurs de campus ou cycle ne correspondent pas à la classe sélectionnée."
                    }, status=400)
            except Classe_active.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': "Classe active introuvable."
                }, status=400)

            # Enregistrer
            variable_prix = form.save(commit=False)
            variable_prix.id_campus_id = id_campus
            variable_prix.id_cycle_actif_id = id_cycle_actif
            variable_prix.save()
            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"Une erreur est survenue lors de l'enregistrement : {str(e)}"
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)

@login_required
@csrf_protect
def save_variable_derogation(request):
    if request.method == 'POST':
        try:
            id_annee = request.POST.get('id_annee')
            id_campus = request.POST.get('id_campus')
            id_cycle_actif = request.POST.get('id_cycle_actif')
            id_classe_active = request.POST.get('id_classe_active')
            id_eleve = request.POST.get('id_eleve')
            id_variable = request.POST.get('id_variable')
            date_butoire = request.POST.get('date_butoire')
    

            if not all([id_annee, id_campus, id_cycle_actif, id_classe_active, id_eleve, date_butoire]):
                return JsonResponse({
                    'success': False,
                    'error': 'Tous les champs sont requis.'
                }, status=400)

            # Validation tenant
            denied = deny_cross_tenant_access(request, id_campus)
            if denied:
                return denied

            if VariableDerogation.objects.filter(
                id_eleve=id_eleve,
                id_annee = id_annee,
                id_classe_active=id_classe_active,
            ).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Cette derogation existe déjà.'
                }, status=400)

            derogation = VariableDerogation(
                id_eleve_id=id_eleve,
                id_campus_id=id_campus,
                id_annee_id=id_annee,
                id_cycle_actif_id=id_cycle_actif,
                id_classe_active_id=id_classe_active,
                date_derogation=date_butoire,
                id_variable_id= id_variable
            )
            derogation.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Une erreur est survenue lors de l\'enregistrement : {str(e)}'
            }, status=500)
    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée.'
    }, status=405)

@login_required
@csrf_protect
def save_variable_date_butoire(request):
    if request.method == 'POST':
        try:
            id_annee = request.POST.get('id_annee')
            id_campus = request.POST.get('id_campus')
            id_cycle_actif = request.POST.get('id_cycle_actif')
            id_classe_active = request.POST.get('id_classe_active')
            id_variable = request.POST.get('id_variable')
            date_butoire = request.POST.get('date_butoire')
        
            if not all([id_annee, id_campus, id_cycle_actif, id_classe_active, date_butoire]):
                return JsonResponse({
                    'success': False,
                    'error': 'Tous les champs sont requis.'
                }, status=400)

            # Validation tenant
            denied = deny_cross_tenant_access(request, id_campus)
            if denied:
                return denied

            if VariableDatebutoire.objects.filter(
                id_annee = id_annee,
                id_classe_active=id_classe_active,
            ).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Cette date butoire  existe déjà.'
                }, status=400)

            derogation = VariableDatebutoire(
                id_campus_id=id_campus,
                id_annee_id=id_annee,
                id_cycle_actif_id=id_cycle_actif,
                id_classe_active_id=id_classe_active,
                date_butoire=date_butoire,
                id_variable_id=id_variable
                
            )
            derogation.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Une erreur est survenue lors de l\'enregistrement : {str(e)}'
            }, status=500)
    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée.'
    }, status=405)



@login_required
@csrf_protect
def save_variable_reduction(request):
    if request.method == 'POST':
        try:
            id_annee = request.POST.get('id_annee')
            id_campus = request.POST.get('id_campus')
            id_cycle_actif = request.POST.get('id_cycle_actif')
            id_classe_active = request.POST.get('id_classe_active')
            id_eleve = request.POST.get('id_eleve')
            id_variable = request.POST.get('id_variable')
            pourcentage = request.POST.get('pourcentage')
    

            if not all([id_annee, id_campus, id_cycle_actif, id_classe_active, id_eleve,pourcentage]):
                return JsonResponse({
                    'success': False,
                    'error': 'Tous les champs sont requis.'
                }, status=400)

            # Validation tenant
            denied = deny_cross_tenant_access(request, id_campus)
            if denied:
                return denied

            if Eleve_reduction_prix.objects.filter(
                id_eleve=id_eleve,
                id_annee = id_annee,
                id_classe_active=id_classe_active,
            ).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Cette reduction existe déjà pour le même élève.'
                }, status=400)

            reduction = Eleve_reduction_prix(
                id_eleve_id=id_eleve,
                id_campus_id=id_campus,
                id_annee_id=id_annee,
                id_cycle_actif_id=id_cycle_actif,
                id_classe_active_id=id_classe_active,
                pourcentage=pourcentage,
                id_variable_id= id_variable
            )
            reduction.save()

            return JsonResponse({'success': True})
        except Exception as e:
            logger.error(f"Erreur dans save_variable_reduction: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Une erreur est survenue lors de l\'enregistrement : {str(e)}'
            }, status=500)
    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée.'
    }, status=405)


