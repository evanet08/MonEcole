from ._initials import *
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
import json
from django.views.decorators.csrf import csrf_exempt

# =========================information personnel edition :

@login_required
@module_required("Administration")
def edit_institution(request, id_ecole):
    institution_infos = Institution.objects.all()
    try:
        institution = Institution.objects.get(id_ecole=id_ecole)
    except Institution.DoesNotExist:
        messages.error(request, "Institution non trouvée.")
        return redirect('create_institution')

    if request.method == 'POST':
        form = InstitutionForm(request.POST, request.FILES, instance=institution)
        if form.is_valid():
            institution = form.save(commit=False)

            if 'logo_ecole' in request.FILES:
                if institution.logo_ecole and default_storage.exists(institution.logo_ecole.path):
                    default_storage.delete(institution.logo_ecole.path)
                logo_ecole_file = request.FILES['logo_ecole']
                nom_logo_ecole = logo_ecole_file.name 
                chemin_complet_ecole = os.path.join('logos/ecole', nom_logo_ecole)
                default_storage.save(chemin_complet_ecole, ContentFile(logo_ecole_file.read()))
                institution.logo_ecole.name = nom_logo_ecole

            if 'logo_ministere' in request.FILES:
                if institution.logo_ministere and default_storage.exists(institution.logo_ministere.path):
                    default_storage.delete(institution.logo_ministere.path)
                logo_ministere_file = request.FILES['logo_ministere']
                nom_logo_ministere = logo_ministere_file.name 
                chemin_complet_ministere = os.path.join('logos/ministere', nom_logo_ministere)
                default_storage.save(chemin_complet_ministere, ContentFile(logo_ministere_file.read()))
                institution.logo_ministere.name = nom_logo_ministere

            institution.save()

            messages.success(request, "Données modifiées avec succès !")
            return redirect('create_institution')
        else:
            messages.error(request, "Erreur lors de la mise à jour. Veuillez vérifier les données.")
            print(form.errors)
            return render(request, 'parametrage/index_parametrage.html', {
                'form': form,
                'institution_infos': institution_infos,
                'institution': institution,
                'form_type': 'institution',
                'show_nav': True,
                'photo_profil': get_user_info(request)['photo_profil'],
                'modules': get_user_info(request)['modules'],
                'last_name': get_user_info(request)['last_name']
            })

    form = InstitutionForm(instance=institution)
    return render(request, 'parametrage/index_parametrage.html', {
        'form': form,
        'institution_infos': institution_infos,
        'institution': institution,
        'form_type': 'institution',
        'show_nav': True,
        'photo_profil': get_user_info(request)['photo_profil'],
        'modules': get_user_info(request)['modules'],
        'last_name': get_user_info(request)['last_name']
    })

@login_required
@module_required("Administration")

def editer_personnel(request, personnel_id):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = 'editer_personnel' in request.path  

    personnel = get_object_or_404(Personnel, id_personnel=personnel_id)
    user = personnel.user  

    valeurs_a_garder_user = {'username': user.username, 'password': user.password,'email':user.email}
    valeurs_a_garder_personnel = {
        'date_naissance': personnel.date_naissance,
        'type_identite': personnel.type_identite,
        'numero_identite': personnel.numero_identite,
        'imageUrl': personnel.imageUrl,
    }

    if request.method == 'POST':
        firstname = request.POST.get('first_name').strip()
        lastname = request.POST.get('last_name').strip()
        form_personnel = PersonnelForm(request.POST, request.FILES, instance=personnel)
        form_personnel_user = PersonnelUserForm(request.POST, instance=user)

        if form_personnel.is_valid() and form_personnel_user.is_valid():
            existing_personnel = Personnel.objects.filter(
                user__first_name__iexact=firstname, user__last_name__iexact=lastname
            ).exclude(id_personnel=personnel.id_personnel)

            if existing_personnel.exists():
                messages.error(request, "Un personnel avec ce nom et prénom existe déjà !")
            else:
                user = form_personnel_user.save(commit=False)

                user.username = valeurs_a_garder_user['username']
                user.password = valeurs_a_garder_user['password']
                user.email = valeurs_a_garder_user['email']

                user.first_name = firstname.upper()
                user.last_name = ' '.join([part.capitalize() for part in user.last_name.split()])
                
                
                user.save() 

                personnel = form_personnel.save(commit=False)

                for champ, valeur in valeurs_a_garder_personnel.items():
                    setattr(personnel, champ, valeur)
                personnel.save()  
                
                messages.success(request, "Personnel mis à jour avec succès !")
                return redirect('ajouter_personnel')  

        else:
            messages.error(request, "Erreur lors de la mise à jour des informations.")
            return redirect('ajouter_personnel')  


    else:
        form_personnel = PersonnelForm(instance=personnel)
        form_personnel_user = PersonnelUserForm(instance=user)
    
    champs_per_masquer = ['addresse','telephone','imageUrl','date_naissance','pays','province','region','commune','etat_civil']
    champ_user_masquer = ['username', 'password','email']

    return render(request, 'parametrage/index_parametrage.html', {
        'form_personnel_edit': form_personnel,
        'form_personnel_edit_user': form_personnel_user,
        'show_nav': show_nav,
        'champ_person_masquer': champs_per_masquer,
        'champ_user_masquer': champ_user_masquer,
        'form_type': 'edition_personnel',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Administration")
def update_personnel_categorie(request, id_personnel_category):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            categorie = data.get('categorie')
            sigle = data.get('sigle')

            if not categorie:
                return JsonResponse({
                    'success': False,
                    'error': "Le champ catégorie est requis."
                }, status=400)

            personnel_categorie = Personnel_categorie.objects.get(id_personnel_category=id_personnel_category)

            if Personnel_categorie.objects.filter(categorie=categorie).exclude(id_personnel_category=id_personnel_category).exists():
                return JsonResponse({
                    'success': False,
                    'error': "Une catégorie avec ce nom existe déjà."
                }, status=400)

            personnel_categorie.categorie = categorie
            personnel_categorie.sigle = sigle if sigle else None
            personnel_categorie.save()
            return JsonResponse({
                'success': True,
                'message': "Catégorie mise à jour avec succès."
            })

        except Personnel_categorie.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Catégorie non trouvée."
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': "Une erreur s'est produite. Contactez l'administrateur."
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)

@login_required
@module_required("Administration")
def update_personnel_diplome(request, id_diplome):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            diplome = data.get('diplome')
            sigle = data.get('sigle')

            if not diplome:
                return JsonResponse({
                    'success': False,
                    'error': "Le champ diplome est requis."
                }, status=400)

            personnel_diplome = Diplome.objects.get(id_diplome=id_diplome)

            if Diplome.objects.filter(diplome=diplome).exclude(id_diplome=id_diplome).exists():
                return JsonResponse({
                    'success': False,
                    'error': "Un diplome avec ce nom existe déjà."
                }, status=400)

            personnel_diplome.diplome = diplome
            personnel_diplome.sigle = sigle if sigle else None
            personnel_diplome.save()
            return JsonResponse({
                'success': True,
                'message': "Diplome mise à jour avec succès."
            })

        except Diplome.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Diplome non trouvée."
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': "Une erreur s'est produite. Contactez l'administrateur."
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)

@login_required
@module_required("Administration")
def update_personnel_speciality(request, id_specialite):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            specialite = data.get('specialite')
            sigle = data.get('sigle')

            if not specialite:
                return JsonResponse({
                    'success': False,
                    'error': "Le champ specialite est requis."
                }, status=400)

            personnel_specialite = Specialite.objects.get(id_specialite=id_specialite)

            if Specialite.objects.filter(specialite=specialite).exclude(id_specialite=id_specialite).exists():
                return JsonResponse({
                    'success': False,
                    'error': "  La spécialité avec ce nom existe déjà."
                }, status=400)

            # Mettre à jour
            personnel_specialite.specialite = specialite
            personnel_specialite.sigle = sigle if sigle else None
            personnel_specialite.save()
            return JsonResponse({
                'success': True,
                'message': "Spécialité mise à jour avec succès."
            })

        except Specialite.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Spécialité non trouvée."
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': "Une erreur s'est produite. Contactez l'administrateur."
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)


@login_required
@module_required("Administration")
def update_personnel_vacation(request, id_vacation):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            vacation = data.get('vacation')
            sigle = data.get('sigle')

            if not vacation:
                return JsonResponse({
                    'success': False,
                    'error': "Le champ vacation est requis."
                }, status=400)

            personnel_vacation = Vacation.objects.get(id_vacation=id_vacation)

            if Vacation.objects.filter(vacation=vacation).exclude(id_vacation=id_vacation).exists():
                return JsonResponse({
                    'success': False,
                    'error': "  La vacation avec ce nom existe déjà."
                }, status=400)

            # Mettre à jour
            personnel_vacation.vacation = vacation
            personnel_vacation.sigle = sigle if sigle else None
            personnel_vacation.save()
            return JsonResponse({
                'success': True,
                'message': "vacation mise à jour avec succès."
            })

        except Vacation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "vacation non trouvée."
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': "Une erreur s'est produite. Contactez l'administrateur."
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)

@login_required
@module_required("Administration")
def update_personnel_type_personnel(request, id_type_personnel):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            type = data.get('type')
            sigle = data.get('sigle')

            if not type:
                return JsonResponse({
                    'success': False,
                    'error': "Le champ type est requis."
                }, status=400)

            personnel_type = PersonnelType.objects.get(id_type_personnel=id_type_personnel)

            if PersonnelType.objects.filter(type=type).exclude(id_type_personnel=id_type_personnel).exists():
                return JsonResponse({
                    'success': False,
                    'error': "  Le type de personnel avec ce nom existe déjà."
                }, status=400)

            # Mettre à jour
            personnel_type.type = type
            personnel_type.sigle = sigle if sigle else None
            personnel_type.save()
            return JsonResponse({
                'success': True,
                'message': "type de personnel mise à jour avec succès."
            })

        except PersonnelType.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Type non trouvée."
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': "Une erreur s'est produite. Contactez l'administrateur."
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)

# @login_required
# @module_required("Administration")
# def update_trimestre(request, id_trimestre):

#     if request.method == "POST":
#         try:
#             import json
#             data = json.loads(request.body)
#             trimestre_value = data.get('trimestre')
#             etat_value = data.get('etat_trimestre')
#             date_ouverture = data.get('date_ouverture')
#             date_cloture = data.get('date_cloture')

#             if not all([trimestre_value, etat_value, date_ouverture, date_cloture]):
#                 return JsonResponse({
#                     'success': False,
#                     'error': "Tous les champs sont requis."
#                 }, status=400)

#             if etat_value not in ['En attente', 'En Cours', 'Cloturée']:
#                 return JsonResponse({
#                     'success': False,
#                     'error': "État du trimestre invalide."
#                 }, status=400)
#             existe = Trimestre.objects.exclude(id_trimestre=id_trimestre).filter(
#                 date_ouverture=date_ouverture,
#                 date_cloture=date_cloture
#             ).exists()
            
#             existe_trim_only = Trimestre.objects.filter(
#                 trimestre=trimestre_value
#             ).exclude(id_trimestre = id_trimestre).exists()


#             if existe or existe_trim_only:
#                 return JsonResponse({
#                     'success': False,
#                     'error': "Un autre trimestre possède déjà ces dates ou le trimestre existe deja."
#                 }, status=400)

#             try:
#                 date_ouverture = datetime.strptime(date_ouverture, '%Y-%m-%d').date()
#                 date_cloture = datetime.strptime(date_cloture, '%Y-%m-%d').date()
#                 if date_ouverture >= date_cloture:
#                     return JsonResponse({
#                         'success': False,
#                         'error': "La date d'ouverture doit être antérieure à la date de clôture."
#                     }, status=400)
#             except ValueError:
#                 return JsonResponse({
#                     'success': False,
#                     'error': "Format de date invalide (AAAA-MM-JJ)."
#                 }, status=400)

#             trimestre = Trimestre.objects.get(id_trimestre=id_trimestre)
#             if Periode.objects.filter(id_trimestre=trimestre).exists():
#                 return JsonResponse({
#                     'success': False,
#                     'error': "Impossible de modifier le trimestre car il est utilisé dans des périodes."
#                 }, status=400)

#             # Mettre à jour
#             trimestre.trimestre = trimestre_value
#             trimestre.etat_trimestre = etat_value
#             trimestre.date_ouverture = date_ouverture
#             trimestre.date_cloture = date_cloture
#             trimestre.save()
#             return JsonResponse({
#                 'success': True,
#                 'message': "Trimestre mis à jour avec succès."
#             })

#         except Trimestre.DoesNotExist:
#             return JsonResponse({
#                 'success': False,
#                 'error': "Trimestre non trouvé."
#             }, status=404)
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'error': "Une erreur s'est produite. Contactez l'administrateur."
#             }, status=500)

#     return JsonResponse({
#         'success': False,
#         'error': "Méthode non autorisée."
#     }, status=405)





@login_required
@module_required("Administration")
@require_POST
def update_trimestre(request, id_trimestre):
    try:
        trimestre = Trimestre.objects.get(id_trimestre=id_trimestre)
        data = json.loads(request.body)
        trimestre_value = data.get('trimestre')

        if not trimestre_value:
            return JsonResponse({"success": False, "error": "Le champ trimestre est requis."})

        if Trimestre.objects.filter(trimestre=trimestre_value).exclude(id_trimestre=id_trimestre).exists():
            return JsonResponse({"success": False, "error": "Ce trimestre existe déjà."})

        ordre = [key for key, _ in trimestres_default]
        try:
            current_index = ordre.index(trimestre_value)
            if current_index > 0:
                trimestre_precedent = ordre[current_index - 1]
                if not Trimestre.objects.filter(trimestre=trimestre_precedent).exists():
                    return JsonResponse({"success": False, "error": f"Vous devez d'abord créer {trimestre_precedent} avant {trimestre_value}."})
        except ValueError:
            return JsonResponse({"success": False, "error": "Trimestre invalide."})

        trimestre.trimestre = trimestre_value
        trimestre.save()
        return JsonResponse({"success": True, "message": "Trimestre mis à jour avec succès."})
    except Trimestre.DoesNotExist:
        return JsonResponse({"success": False, "error": "Trimestre introuvable."})

@login_required
@module_required("Administration")
def update_class(request, class_id):
    
    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            new_name = data.get('classe')

            if not new_name:
                return JsonResponse({
                    'success': False,
                    'error': 'Le nom de la classe est requis.'
                }, status=400)

            classe = Classe.objects.get(id_classe=class_id)
            if Classe_active.objects.filter(classe_id=classe).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Impossible de modifier la classe car elle est utilisée dans des classes actives.'
                }, status=400)

            if Classe.objects.exclude(id_classe=class_id).filter(classe=new_name).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Une classe avec ce nom existe déjà.'
                }, status=400)

            classe.classe = new_name
            classe.save()
            return JsonResponse({
                'success': True,
                'message': 'Classe mise à jour avec succès.'
            })

        except Classe.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Classe non trouvée.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Une erreur s\'est produite. Contactez l\'administrateur.'
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée.'
    }, status=405)

@login_required
@module_required("Administration")
def update_cycle(request, cycle_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            new_name = data.get('cycle')

            if not new_name:
                return JsonResponse({
                    'success': False,
                    'error': 'Le nom du cycle est requis.'
                }, status=400)

            cycle = Classe_cycle.objects.get(id_cycle=cycle_id)
            dependencies = []
            if Classe_cycle_actif.objects.filter(cycle_id=cycle).exists():
                dependencies.append("cycles actifs")
            if Classe_active.objects.filter(cycle_id__cycle_id=cycle).exists():
                dependencies.append("classes actives")

            if dependencies:
                error_msg = f"Impossible de modifier le cycle car il est utilisé dans : {', '.join(dependencies)}."
                return JsonResponse({'success': False, 'error': error_msg}, status=400)

            if Classe_cycle.objects.exclude(id_cycle=cycle_id).filter(cycle=new_name).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Un cycle avec ce nom existe déjà.'
                }, status=400)

            cycle.cycle = new_name
            cycle.save()
            return JsonResponse({
                'success': True,
                'message': 'Cycle mis à jour avec succès.'
            })

        except Classe_cycle.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Cycle non trouvé.'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'Une erreur s\'est produite. Contactez l\'administrateur.'
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée.'
    }, status=405)

# @login_required
# @module_required("Administration")
# def update_periode(request, id_periode):

#     if request.method == "POST":
#         try:
#             import json
#             data = json.loads(request.body)
#             periode_value = data.get('periode')
#             etat_value = data.get('etat_periode')
#             id_trimestre = data.get('id_trimestre')
#             date_debut = data.get('date_debut')
#             date_fin = data.get('date_fin')
#             date_debut_obj = datetime.strptime(date_debut, "%Y-%m-%d").date()
#             date_fin_obj = datetime.strptime(date_fin, "%Y-%m-%d").date()

#             if not all([periode_value, etat_value, id_trimestre,date_debut,date_fin]):
#                 return JsonResponse({
#                     'success': False,
#                     'error': "Tous les champs sont requis."
#                 }, status=400)

#             if etat_value not in ['En attente', 'En Cours', 'Cloturée']:
#                 return JsonResponse({
#                     'success': False,
#                     'error': "État de la période invalide."
#                 }, status=400)

#             periode = Periode.objects.get(id_periode=id_periode)
#             try:
#                 trimestre = Trimestre.objects.get(id_trimestre=id_trimestre,is_active = True)
#                 if not trimestre.is_active:
#                     return JsonResponse({
#                         'success': False,
#                         'error': "Le trimestre sélectionné est supprimé."
#                     }, status=400)
#             except Trimestre.DoesNotExist:
#                 return JsonResponse({
#                     'success': False,
#                     'error': "Trimestre non trouvé."
#                 }, status=404)
                
#             date_debut_obj = datetime.strptime(date_debut, "%Y-%m-%d").date()
#             date_fin_obj = datetime.strptime(date_fin, "%Y-%m-%d").date()

                
                
#             if date_debut_obj < trimestre.date_ouverture or date_fin_obj > trimestre.date_cloture:
#                 return JsonResponse({
#                 'success': False,
#                 'error': f"Les dates doivent être comprises entre {trimestre.date_ouverture} et {trimestre.date_cloture} pour le trimestre sélectionné."
#             }, status=400)



#             if Eleve_note.objects.filter(id_periode=periode).exists():
#                 return JsonResponse({'success': False, 'error': "Période utilisée dans des notes."}, status=400)

#             # Mettre à jour
#             periode.periode = periode_value
#             periode.etat_periode = etat_value
#             periode.id_trimestre = trimestre
#             periode.date_debut = date_debut_obj
#             periode.date_fin = date_fin_obj
#             periode.save()

#             periode.save()
#             return JsonResponse({
#                 'success': True,
#                 'message': "Période mise à jour avec succès."
#             })

#         except Periode.DoesNotExist:
#             return JsonResponse({
#                 'success': False,
#                 'error': "Période non trouvée."
#             }, status=404)
#         except Exception as e:
#             # print(f"Erreur inattendue: {str(e)}")  # Debug
#             return JsonResponse({
#                 'success': False,
#                 'error': "Une erreur s'est produite. Contactez l'administrateur."
#             }, status=500)

#     # print(f"Méthode non autorisée pour id_periode={id_periode}")  # Debug
#     return JsonResponse({
#         'success': False,
#         'error': "Méthode non autorisée."
#     }, status=405) 



@login_required
@require_POST
def update_periode(request, id_periode):
    try:
        data = json.loads(request.body)
        periode_value = data.get('periode')
        id_trimestre = data.get('id_trimestre')

        if not all([periode_value, id_trimestre]):
            return JsonResponse({
                'success': False,
                'error': "Tous les champs sont requis."
            }, status=400)

        periode = Periode.objects.get(id_periode=id_periode)
        try:
            trimestre = Trimestre.objects.get(id_trimestre=id_trimestre, is_active=True)
        except Trimestre.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Trimestre non trouvé ou non actif."
            }, status=404)

        if Periode.objects.filter(periode=periode_value, id_trimestre=trimestre).exclude(id_periode=id_periode).exists():
            return JsonResponse({
                'success': False,
                'error': "Cette période existe déjà pour ce trimestre."
            }, status=400)

        if Annee_periode.objects.filter(periode=periode).exists():
            return JsonResponse({
                'success': False,
                'error': "Période utilisée dans des notes via Annee_periode."
            }, status=400)

        periode_choices = [choice[0] for choice in periodes_default]
        if periode_value not in periode_choices:
            return JsonResponse({
                'success': False,
                'error': "Période invalide."
            }, status=400)

        periode.periode = periode_value
        periode.id_trimestre = trimestre
        periode.save()

        return JsonResponse({
            'success': True,
            'message': "Période mise à jour avec succès."
        })

    except Periode.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': "Période non trouvée."
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': "Format de données invalide."
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': "Une erreur s'est produite. Contactez l'administrateur."
        }, status=500)

@login_required
@module_required("Administration")
def update_checkbox(request):
    if request.method == "POST":
        personnel_id = request.POST.get("personnel_id")
        field_name = request.POST.get("field_name")
        is_checked = request.POST.get("is_checked") == "true"

        if not personnel_id or not field_name:
            return JsonResponse({"success": False, "error": "Paramètres manquants"}, status=400)
        personnel = get_object_or_404(Personnel, id_personnel=personnel_id)
        if hasattr(personnel, field_name):
            setattr(personnel, field_name, is_checked)
            personnel.save()
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Champ invalide"}, status=400)

    return JsonResponse({"success": False, "error": "Méthode non autorisée"}, status=400)

@login_required
@module_required("Administration")
def update_annee(request, id_annee):

    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            annee_value = data.get('annee')
            etat_value = data.get('etat_annee')

            if not annee_value:
                return JsonResponse({
                    'success': False,
                    'error': "Le nom de l'année est requis."
                }, status=400)

            if etat_value not in ['En attente', 'En Cours', 'Cloturée']:
                return JsonResponse({
                    'success': False,
                    'error': "État de l'année invalide."
                }, status=400)

            annee = Annee.objects.get(id_annee=id_annee)
            dependencies = []
            if Classe_active.objects.filter(id_annee=annee).exists():
                dependencies.append("classes actives")
            if Classe_cycle_actif.objects.filter(id_annee=annee).exists():
                dependencies.append("cycles actifs")

            if dependencies:
                error_msg = f"Impossible de modifier l'année car elle est utilisée dans : {', '.join(dependencies)}."
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)

          
            if Annee.objects.exclude(id_annee=id_annee).filter(annee=annee_value).exists():
                return JsonResponse({
                    'success': False,
                    'error': "Une année avec ce nom existe déjà."
                }, status=400)

            annee.annee = annee_value
            annee.etat_annee = etat_value
            annee.save()
            return JsonResponse({
                'success': True,
                'message': "Année mise à jour avec succès."
            })

        except Annee.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Année non trouvée."
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': "Une erreur s'est produite. Contactez l'administrateur."
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)

@login_required
@module_required("Administration")
def update_campus(request, campus_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            campus = Campus.objects.get(id_campus=campus_id)
            campus.campus = data['campus']
            campus.adresse = data['adresse'] 
            campus.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
@module_required("Administration")
def update_classe_cycle_actif(request, id_cycle_actif):

    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            id_annee = data.get('id_annee')
            id_campus = data.get('id_campus')
            cycle_id = data.get('cycle_id')
            role = data.get('role')

            if not all([id_annee, id_campus, cycle_id]):
                return JsonResponse({
                    'success': False,
                    'error': "Les champs année, campus et cycle sont requis."
                }, status=400)

            cycle_actif = Classe_cycle_actif.objects.get(id_cycle_actif=id_cycle_actif)
            dependencies = []
            if Classe_active.objects.filter(cycle_id=cycle_actif).exists():
                dependencies.append("classes actives")
            if Cours_par_cycle.objects.filter(cycle_id=cycle_actif).exists():
                dependencies.append("cours par cycle")
            if Eleve_inscription.objects.filter(id_classe_cycle=cycle_actif).exists():
                dependencies.append("inscriptions d'élèves")

            if dependencies:
                error_msg = f"Impossible de modifier le cycle actif car il est utilisé dans : {', '.join(dependencies)}."
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)

            ordre_inchange = cycle_actif.ordre
          
            try:
                annee = Annee.objects.get(id_annee=id_annee)
                campus = Campus.objects.get(id_campus=id_campus)
                cycle = Classe_cycle.objects.get(id_cycle=cycle_id)
                if not annee.is_active or not campus.is_active:
                    return JsonResponse({
                        'success': False,
                        'error': "L'année ou le campus sélectionné est supprimé."
                    }, status=400)
            except (Annee.DoesNotExist, Campus.DoesNotExist, Classe_cycle.DoesNotExist) as e:
                return JsonResponse({
                    'success': False,
                    'error': "Année, campus ou cycle non trouvé."
                }, status=404)
            cycle_actif_registred = Classe_cycle_actif.objects.filter(id_campus=campus,id_annee=annee,cycle_id = cycle).exclude(id_cycle_actif=id_cycle_actif)
            if not cycle_actif_registred.exists():           
                cycle_actif.id_annee = annee
                cycle_actif.id_campus = campus
                cycle_actif.cycle_id = cycle
                cycle_actif.nbre_classe_par_cycle_actif = role if role else None
                cycle_actif.ordre = ordre_inchange
                cycle_actif.save()
                return JsonResponse({
                    'success': True,
                    'message': "Cycle actif mis à jour avec succès."
                })
            else:
                return JsonResponse({
                    'success': True,
                    'message': "Ce Cycle  n'est pas mis à jour car il existe deja.Verifiez bien "
                })
                

        except Classe_cycle_actif.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Cycle actif non trouvé."
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': "Une erreur s'est produite. Contactez l'administrateur."
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)

@login_required
@module_required("Administration")
def update_classe_active(request, id_classe_active):
    if request.method == "POST":
        try:
            if request.content_type != 'application/json':
                return JsonResponse({
                    'success': False,
                    'error': "Requête invalide, JSON attendu."
                }, status=400)

            data = json.loads(request.body)
            id_campus = data.get('id_campus')
            id_annee = data.get('id_annee')
            cycle_id = data.get('cycle_id')
            classe_id = data.get('classe_id')
            groupe = data.get('groupe')
            isTerminale = data.get('isTerminale') == 'true'

            if not all([id_campus, id_annee, cycle_id, classe_id]):
                return JsonResponse({
                    'success': False,
                    'error': "Les champs campus, année, cycle et classe sont requis."
                }, status=400)

            try:
                classe_active = get_object_or_404(Classe_active, id_classe_active=id_classe_active)
                ordre_initial = classe_active.ordre
            except:
                return JsonResponse({
                    'success': False,
                    'error': "Ordre invalide."
                }, status=400)
                
            dependencies = []
            if Cours_par_classe.objects.filter(id_classe=classe_active).exists():
                dependencies.append("cours par classe")
            if Eleve_inscription.objects.filter(id_classe=classe_active).exists():
                dependencies.append("inscriptions d'élèves")

            if dependencies:
                error_msg = f"Impossible de modifier la classe active car elle est utilisée dans : {', '.join(dependencies)}."
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)

            try:
                campus = Campus.objects.get(id_campus=id_campus)
                annee = Annee.objects.get(id_annee=id_annee)
                cycle = Classe_cycle_actif.objects.get(id_cycle_actif=cycle_id)
                classe = Classe.objects.get(id_classe=classe_id)
                if not all([annee.is_active, campus.is_active, cycle.is_active]):
                    return JsonResponse({
                        'success': False,
                        'error': "L'année, le campus ou le cycle sélectionné est désactivé."
                    }, status=400)
            except (Campus.DoesNotExist, Annee.DoesNotExist, Classe_cycle_actif.DoesNotExist, Classe.DoesNotExist) as e:
                return JsonResponse({
                    'success': False,
                    'error': "Campus, année, cycle ou classe non trouvé."
                }, status=404)

            valid_groups = [g[0] for g in Classe_active._meta.get_field('groupe').choices]
            if groupe and groupe not in valid_groups:
                return JsonResponse({
                    'success': False,
                    'error': "Groupe invalide."
                }, status=400)

            existing = Classe_active.objects.filter(
                id_campus=campus,
                id_annee=annee,
                cycle_id=cycle,
                classe_id=classe,
                groupe=groupe,
                is_active=True
            ).exclude(id_classe_active=id_classe_active).exists()
            if existing:
                return JsonResponse({
                    'success': False,
                    'error': "Une classe active avec cette combinaison existe déjà."
                }, status=400)

           
            classe_active.id_campus = campus
            classe_active.id_annee = annee
            classe_active.cycle_id = cycle
            classe_active.classe_id = classe
            classe_active.groupe = groupe if groupe else None
            classe_active.isTerminale = isTerminale
            classe_active.ordre = ordre_initial  
            classe_active.save()

            return JsonResponse({
                'success': True,
                'message': f"Classe active mise à jour avec succès. Ordre conservé : {ordre_initial}"
            })

        except Classe_active.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Classe active non trouvée."
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': "Format JSON invalide."
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"Une erreur s'est produite : {str(e)}"
            }, status=500)

    return JsonResponse({
        'success': False,
        'error': "Méthode non autorisée."
    }, status=405)


@require_POST
@module_required("Administration")
def update_annee_periode(request):
    try:
        data = json.loads(request.body)
        periode_id = data.get('id_periode')
        periode = data.get('periode')
        debut = data.get('debut')
        fin = data.get('fin')
        isOpen_value = data.get('isOpen', True)
        id_annee = data.get('id_annee')
        id_campus = data.get('id_campus')
        id_cycle = data.get('id_cycle')
        id_classe = data.get('id_classe')
        id_trimestre_annee = data.get('id_trimestre_annee')

        if not all([periode_id, periode, id_annee, id_campus, id_cycle, id_classe, id_trimestre_annee]):
            return JsonResponse({'success': False, 'errors': 'Tous les champs requis doivent être fournis'}, status=400)

        debut = debut if debut and debut != "null" else None
        fin = fin if fin and fin != "null" else None
        
        # Update via raw SQL since annee_periode is a VIEW
        from django.db import connection
        is_open_int = 1 if isOpen_value in [True, 'true', 'True', 1, '1'] else 0
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE countryStructure.etablissements_annees_periodes SET isOpen=%s, debut=%s, fin=%s WHERE id=%s",
                [is_open_int, debut, fin, periode_id]
            )

        # Fetch periode_instance to get the label for the response
        periode_instance = Periode.objects.get(id_periode=periode)
        periode_label = periode_instance.periode

        return JsonResponse({
            'success': True,
            'message': 'Période mise à jour avec succès',
            'periode__periode': periode_label
        }, status=200)
    except Periode.DoesNotExist:
        return JsonResponse({'success': False, 'errors': 'Période non trouvée'}, status=404)
    except ValidationError as e:
        return JsonResponse({'success': False, 'errors': f'Erreur de validation : {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'errors': f'Erreur serveur : {str(e)}'}, status=500)
    
    
@require_POST
@module_required("Administration")
def update_annee_trimestre(request):
    try:
        data = json.loads(request.body)

        trimestre_id = data.get('id_trimestre')
        trimestre = data.get('trimestre')
        debut = data.get('debut')
        fin = data.get('fin')
        isOpen_value = data.get('isOpen', True)
        id_annee = data.get('id_annee')
        id_campus = data.get('id_campus')
        id_cycle = data.get('id_cycle')
        id_classe = data.get('id_classe')

        if not all([trimestre_id, trimestre, id_annee, id_campus, id_cycle, id_classe]):
            return JsonResponse({'success': False, 'errors': 'Tous les champs requis doivent être fournis'}, status=400)

        # Update via raw SQL since annee_trimestre is a VIEW
        from django.db import connection
        is_open_int = 1 if isOpen_value in [True, 'true', 'True', 1, '1'] else 0
        debut_val = debut if debut and debut != "null" else None
        fin_val = fin if fin and fin != "null" else None
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE countryStructure.etablissements_annees_trimestres SET isOpen=%s, debut=%s, fin=%s WHERE id=%s",
                [is_open_int, debut_val, fin_val, trimestre_id]
            )
        trimestre_label = Trimestre.objects.get(id_trimestre=trimestre).trimestre
        return JsonResponse({
            'success': True,
            'message': 'Trimestre mis à jour avec succès',
            'trimestre__trimestre': trimestre_label
        }, status=200)
    except Annee_trimestre.DoesNotExist:
        return JsonResponse({'success': False, 'errors': 'Trimestre non trouvé'}, status=400)
    except ValidationError as e:
        return JsonResponse({'success': False, 'errors': f'Erreur de validation : {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'errors': f'Erreur serveur : {str(e)}'}, status=500)
    
    
    
@csrf_exempt
@require_POST
def update_user_module_access(request):
    import json
    try:
        body = json.loads(request.body)
        id_user_module = body.get("id_user_module")
        is_active = body.get("is_active")
        
        um = UserModule.objects.get(pk=id_user_module)
        um.is_active = is_active
        um.save()

        return JsonResponse({"success": True, "message": "Mise à jour réussie"})
    except UserModule.DoesNotExist:
        return JsonResponse({"error": "UserModule introuvable"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
