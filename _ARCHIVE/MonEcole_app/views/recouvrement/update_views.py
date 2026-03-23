
from .create_base import *
from MonEcole_app.views.tools.tenant_utils import validate_campus_access



@login_required
@csrf_protect
def update_paiement_field(request):
    if request.method == 'POST':
        try:
            id_paiement = request.POST.get('id_paiement')
            field = request.POST.get('field')
            value = request.POST.get('value') == 'true'  

            if not id_paiement or not field:
                return JsonResponse({
                    'success': False,
                    'error': 'ID de paiement ou champ manquant.'
                }, status=400)

            if field not in ['status', 'is_rejected']:
                return JsonResponse({
                    'success': False,
                    'error': 'Champ non valide.'
                }, status=400)

            try:
                paiement = Paiement.objects.get(id_paiement=id_paiement)
            except Paiement.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Paiement non trouvé.'
                }, status=404)

            # Validation tenant
            if not validate_campus_access(request, paiement.id_campus_id):
                return JsonResponse({
                    'success': False,
                    'error': 'Accès interdit à ce paiement.'
                }, status=403)

            if field == 'status':
                paiement.status = value
            elif field == 'is_rejected':
                paiement.is_rejected = value

            paiement.save()

            logger.info(f"Paiement mis à jour: id={id_paiement}, {field}={value}")

            return JsonResponse({'success': True})

        except Exception as e:
            logger.error(f"Erreur dans update_paiement_field pour id_paiement={id_paiement}, field={field}: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Une erreur est survenue : {str(e)}'
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée.'
    }, status=405)


@login_required
@csrf_protect
def update_categorie(request, categorie_id):
    if request.method == 'POST':
        try:
            categorie = get_object_or_404(VariableCategorie, id_variable_categorie=categorie_id)
            new_name = request.POST.get('nom')
            if not new_name:
                return JsonResponse({'success': False, 'error': 'Le nom ne peut pas être vide.'})
            categorie.nom = new_name
            categorie.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'})


@login_required
@csrf_protect
def update_compte(request, compte_id):
    if request.method == 'POST':
        try:
            compte = get_object_or_404(Compte, id_compte=compte_id)
            new_compte = request.POST.get('compte')
            banque_id = request.POST.get('banque_id')

            if not new_compte or not banque_id:
                return JsonResponse({'success': False, 'error': 'Les champs ne peuvent pas être vides.'})

            banque = get_object_or_404(Banque, id_banque=banque_id)

            if Compte.objects.filter(
                id_banque=banque,
                compte=new_compte
            ).exclude(id_compte=compte_id).exists():
                return JsonResponse({'success': False, 'error': 'Un compte avec ce numéro existe déjà pour cette banque.'})

            compte.compte = new_compte
            compte.id_banque = banque
            compte.save()

            return JsonResponse({
                'success': True,
                'banque_nom': banque.banque
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'})

@login_required
@csrf_protect
def update_banque(request, banque_id):
    if request.method == 'POST':
        try:
            banque = get_object_or_404(Banque, id_banque=banque_id)
            new_banque = request.POST.get('banque')
            new_sigle = request.POST.get('sigle')

            if not new_banque or not new_sigle:
                return JsonResponse({'success': False, 'error': 'Les champs ne peuvent pas être vides.'})

            if Banque.objects.filter(banque=new_banque).exclude(id_banque=banque_id).exists():
                return JsonResponse({'success': False, 'error': 'Une banque avec ce nom existe déjà.'})
            if Banque.objects.filter(sigle=new_sigle).exclude(id_banque=banque_id).exists():
                return JsonResponse({'success': False, 'error': 'Un sigle identique existe déjà.'})

            banque.banque = new_banque
            banque.sigle = new_sigle
            banque.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'})

@login_required
@csrf_protect
def update_variable(request, variable_id):
    if request.method == 'POST':
        try:
            variable = get_object_or_404(Variable, id_variable=variable_id)
            categorie_id = request.POST.get('categorie_id')
            new_variable = request.POST.get('variable')

            if not categorie_id or not new_variable:
                return JsonResponse({'success': False, 'error': 'Les champs ne peuvent pas être vides.'})

            categorie = get_object_or_404(VariableCategorie, id_variable_categorie=categorie_id)

            if Variable.objects.filter(
                id_variable_categorie=categorie,
                variable=new_variable
            ).exclude(id_variable=variable_id).exists():
                return JsonResponse({'success': False, 'error': 'Une variable avec ce nom existe déjà dans cette catégorie.'})

            variable.id_variable_categorie = categorie
            variable.variable = new_variable
            variable.save()

            return JsonResponse({
                'success': True,
                'categorie_nom': categorie.nom
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'})
