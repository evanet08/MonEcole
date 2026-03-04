
from django.shortcuts import get_object_or_404, render,redirect
from MonEcole_app.forms.form_imports import (CoursForm,Cours_F,
                                             Cours_cyleForm,
                                             AttributionType_coursF,
                                             Attribution_coursForm,
                                             HoraireTypeForm,
                                             HoraireForm)
from MonEcole_app.models.models_import import *

from django.http import JsonResponse
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..tools.utils import get_user_info
# =========================================Generer l'horaire 
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
import json
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db import transaction
from MonEcole_app.models import Classe_active_responsable
from django.db.models import Exists, OuterRef
from MonEcole_app.views.decorators.decorators import module_required
from django.views.decorators.csrf import csrf_protect



@login_required
@module_required("Enseignement")
def create_cours(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if 'create_cours' in request.path:  
        show_nav = True
    if request.method == "POST":
        cours_name = request.POST.get('cours')
        cours_domaine = request.POST.get('domaine')
        cours_code = request.POST.get('code_cours')
        form = Cours_F(request.POST)
        if form.is_valid():
            cours_existant = Cours.objects.filter(cours = cours_name,code_cours=cours_code,domaine = cours_domaine)
            if cours_existant.exists():
                messages.error(request,'Désolé!cours existe déjà!')
                return redirect("create_cours")  
                
            else:
                form.save()
                messages.success(request, "Cours ajouté avec succès !")
                return redirect("create_cours")  
        else:
            messages.error(request, "Erreur lors de l'ajout du cours. Vérifiez les informations.")
    else:
        form = Cours_F()
    cours = Cours.objects.all()
    return render(request, 'enseignement/index_enseignement.html', {
        'cours': cours,
        'form_crs': form,
        'show_nav': show_nav,
        'form_type': 'cours_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })




@login_required
@module_required("Enseignement")
def create_cours_par_classe(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_cours = CoursForm()
    show_nav = 'organiser_cours_classes' in request.path
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Format JSON invalide"}, status=400)

        try:
            cours_id = int(data.get('cours'))
            class_id = int(data.get('id_classe'))
            id_classe_cycle = int(data.get('id_classe_cycle'))
            id_annee = int(data.get('id_annee'))
            id_campus = int(data.get('id_campus'))
            
            ponderation = data.get('ponderation')  
            TP = data.get("TP") 
            TPE = data.get("TPE")
        
            credits = data.get("credits")
            ordre = data.get("ordre_cours")
            heure_semaine = data.get("heure_semaine")
            compte_au_nombre_echec = data.get("compte_au_nombre_echec", False)
            total_considerable_trimestre = data.get("total_considerable_trimestre", False)
            est_considerer_echec_lorsque_pourcentage_est = data.get("est_considerer_echec_lorsque_pourcentage_est")

            if ponderation is not None: ponderation = int(ponderation)
            if TP is not None: TP = int(TP)
            if TPE is not None: TPE = int(TPE)
            if credits is not None: credits = int(credits)
            if ordre is not None: ordre = int(ordre)
            if heure_semaine is not None: heure_semaine = int(heure_semaine)
            if est_considerer_echec_lorsque_pourcentage_est is not None: 
                est_considerer_echec_lorsque_pourcentage_est = int(est_considerer_echec_lorsque_pourcentage_est)

        except (TypeError, ValueError):
            return JsonResponse({"success": False, "message": "Données invalides (types incorrects)"}, status=400)

        try:
            cours_obj = get_object_or_404(Cours, id_cours=cours_id)
            classe_obj = get_object_or_404(Classe_active, id_classe_active=class_id)
            cycle_obj = get_object_or_404(Classe_cycle_actif, id_cycle_actif=id_classe_cycle)
            annee_obj = get_object_or_404(Annee, id_annee=id_annee)
            campus_obj = get_object_or_404(Campus, id_campus=id_campus)
        except:
            return JsonResponse({"success": False, "message": "ID invalide (Objet non trouvé)"}, status=404)

        if campus_obj.localisation == "BDI" and ponderation is not None and TP is not None and TPE is not None:
            if TP + TPE != ponderation:
                return JsonResponse({
                    "success": False,
                    "message": "Erreur : La somme de TP et TPE doit être égale à la pondération !"
                }, status=400)

        if Cours_par_classe.objects.filter(id_annee=annee_obj, id_campus=campus_obj, id_cycle=cycle_obj, id_cours=cours_obj, id_classe=classe_obj).exists():
            return JsonResponse({"success": False, "message": "Cours déjà existant"}, status=409)

        new_cours = Cours_par_classe.objects.create(
            id_cours=cours_obj,
            id_classe=classe_obj,
            id_cycle=cycle_obj,
            id_annee=annee_obj,
            id_campus=campus_obj,
            ponderation=ponderation,
            TP=TP,
            TPE=TPE,
            credits=credits,
            ordre_cours=ordre,
            heure_semaine=heure_semaine,
            compte_au_nombre_echec=compte_au_nombre_echec,
            total_considerable_trimestre=total_considerable_trimestre,
            est_considerer_echec_lorsque_pourcentage_est=est_considerer_echec_lorsque_pourcentage_est
        )

        response_data = {
            "success": True,
            "message": "Cours ajouté avec succès !",
            "id_cours_classe": new_cours.id_cours_classe,
            "cours": new_cours.id_cours.cours,
            "ponderation": new_cours.ponderation,
            "TP": new_cours.TP,
            "TPE": new_cours.TPE,
            "credits": new_cours.credits,
            "ordre_cours": new_cours.ordre_cours,
            "is_second_semester":new_cours.is_second_semester,
            "heure_semaine": new_cours.heure_semaine,
        }
        return JsonResponse(response_data)
    cours_classes = Cours_par_classe.objects.all()
    return render(request, 'enseignement/index_enseignement.html', {
        'cours_classes': cours_classes,
        'show_nav': show_nav,
        'cours_cl_form': form_cours,
        'form_type': 'cours_classes',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })



@login_required
def create_cours_par_cycle(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = False  
    if 'create_cours_cycle' in request.path:  
        show_nav = True
    full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
    try:
        personnel = request.user.personnel
    except AttributeError:
        messages.error(request, "Utilisateur non lié à un personnel.")
        return redirect("error_page") 

    modules_user = UserModule.objects.filter(
        user=personnel, 
        is_active=True
    ).values_list('module__module', flat=True)

    has_full_access = any(module in full_access_modules for module in modules_user)

    if request.method == "POST":        
        form_cours_cycle = Cours_cyleForm(request.POST)
        if form_cours_cycle.is_valid():
            form_cours_cycle.save()
            messages.success(request, "Cours ajouté avec succès !")
            return redirect("create_cours_cycle")
        else:
            messages.error(request, "Erreur lors de l'ajout du cours. Vérifiez que ce cours n'existe pas déjà.")
    else:
        form_cours_cycle = Cours_cyleForm()

    if has_full_access:
        cours_cycle = Cours_par_cycle.objects.all()
    else:
        cycle_ids = Classe_active_responsable.objects.filter(
            id_personnel=personnel
        ).values_list('id_cycle', flat=True)

        cours_cycle = Cours_par_cycle.objects.filter(
          cycle_id__in=cycle_ids
        )
    return render(request, 'enseignement/index_enseignement.html', {
        'cours_cycles': cours_cycle,
        'form_crs_cycle': form_cours_cycle,
        'show_nav': show_nav,
        'form_type': 'cours_form_cycle',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })



# @login_required
# @require_POST
# def save_cours(request, cours_id):
#     try:
#         data = json.loads(request.body)
#         cours_par_classe = get_object_or_404(Cours_par_classe, pk=int(cours_id))

#         localisation = cours_par_classe.id_campus.localisation  

#         new_data = {
#             'id_cours': int(data.get('cours', cours_par_classe.id_cours_classe_id)),
#             'id_classe': int(data.get('id_classe', cours_par_classe.id_classe_id)),
#             'id_annee': int(data.get('id_annee', cours_par_classe.id_annee_id)),
#             'id_cycle': int(data.get('id_classe_cycle', cours_par_classe.id_cycle_id)),
#             'id_campus': int(data.get('id_campus', cours_par_classe.id_campus_id)),
#         }

#         # Vérification unicité
#         duplicate = Cours_par_classe.objects.filter(
#             id_annee=new_data['id_annee'],
#             id_campus=new_data['id_campus'],
#             id_cycle=new_data['id_cycle'],
#             id_classe=new_data['id_classe'],
#             id_cours=new_data['id_cours']
#         ).exclude(pk=cours_par_classe.pk).exists()

#         if duplicate:
#             return JsonResponse({'status': 'error', 'message': 'Ce cours est déjà assigné à cette classe !'}, status=400)

#         with transaction.atomic():
#             # Champs communs
#             cours_par_classe.id_cours_classe_id = new_data['id_cours']
#             cours_par_classe.id_classe_id = new_data['id_classe']
#             cours_par_classe.id_annee_id = new_data['id_annee']
#             cours_par_classe.id_cycle_id = new_data['id_cycle']
#             cours_par_classe.id_campus_id = new_data['id_campus']

#             if localisation == "BDI":
#                 ponderation = int(data.get('ponderation', cours_par_classe.ponderation or 0))
#                 TP = int(data.get('TP', cours_par_classe.TP or 0))
#                 TPE = int(data.get('TPE', cours_par_classe.TPE or 0))

#                 if TP + TPE != ponderation:
#                     return JsonResponse({'status': 'error', 'message': 'La somme de TP et TPE doit être égale à la pondération !'}, status=400)

#                 cours_par_classe.ponderation = ponderation
#                 cours_par_classe.TP = TP
#                 cours_par_classe.TPE = TPE

#             elif localisation == "RDC":
#                 cours_par_classe.TP = int(data.get('TP', cours_par_classe.TP or 0))               
#                 cours_par_classe.TPE = int(data.get('TPE', cours_par_classe.TPE or 0))           
#                 cours_par_classe.ponderation = int(data.get('ponderation', cours_par_classe.ponderation or 0)) 
#                 cours_par_classe.heure_semaine = int(data.get('heure_semaine', cours_par_classe.heure_semaine or 0))
#                 cours_par_classe.credits = int(data.get('credits', cours_par_classe.credits or 0))
#                 cours_par_classe.ordre_cours = int(data.get('ordre_cours', cours_par_classe.ordre_cours or 0))

#             cours_par_classe.save()

#         return JsonResponse({'status': 'success', 'message': 'Cours mis à jour avec succès'})

#     except ValueError as ve:
#         return JsonResponse({'status': 'error', 'message': f'Erreur de conversion : {str(ve)}'}, status=400)
#     except Exception as e:
#         return JsonResponse({'status': 'error', 'message': f'Erreur interne : {str(e)}'}, status=500)




def update_cours(request, cours_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cours = data.get('cours')
            code_cours = data.get('code_cours')
            domaine = data.get('domaine')

            if not cours:
                return JsonResponse({
                    'success': False,
                    'error': "Le champ cours est requis."
                }, status=400)

            cours_instance = Cours.objects.get(id_cours=cours_id)
            dependencies = []
            if Cours_par_cycle.objects.filter(cours_id=cours_id).exists():
                dependencies.append("cours par cycle")

            if dependencies:
                error_msg = f"Impossible de modifier le cours, car il est utilisée dans : {', '.join(dependencies)}."
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
            if Cours.objects.filter(cours=cours).exclude(id_cours=cours_id).exists():
                return JsonResponse({
                    'success': False,
                    'error': "Un cours avec ce nom existe déjà."
                }, status=400)

            cours_instance.cours = cours
            cours_instance.code_cours = code_cours if code_cours else None
            cours_instance.domaine = domaine if domaine else None
            cours_instance.save()
            return JsonResponse({
                'success': True,
                'message': "Cours mis à jour avec succès."
            })

        except Cours.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Cours non trouvé."
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
@module_required("Enseignement")
def create_attribution_type(request):
    attrib_type = Attribution_type.objects.all()
    user_info = get_user_info(request)
    user_modules = user_info
    if 'attribution_type_cours' in request.path:  
        show_nav = True
    if request.method == "POST":
        attrib_name = request.POST.get('attribution_type')
        form_attrib = AttributionType_coursF(request.POST)
        if form_attrib.is_valid():
            attrib_existant = Attribution_type.objects.filter(attribution_type = attrib_name)
            if attrib_existant.exists():
                messages.error(request,"Désolé!ce type d'attribution existe déjà!")
                return redirect("attribution_type_cours")  
            else:
                form_attrib.save()
                messages.success(request, "Attribution ajouté avec succès !")
                return redirect("attribution_type_cours") 
        else:
            messages.error(request, "Erreur lors de l'ajout du type d'attribution. Vérifiez les informations.")
    else:
        form_attrib= AttributionType_coursF()
    return render(request, 'enseignement/index_enseignement.html', {
        'attrib_type': attrib_type,
        'form_attrib': form_attrib,
        'show_nav': show_nav,
        'form_type': 'cours_attribuer_type',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Enseignement")
def attribution_create(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == 'POST':
        form = Attribution_coursForm(request.POST)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            id_cours_classe_id = int(request.POST.get('id_cours'))
            id_classe = form.cleaned_data['id_classe']
            id_annee = form.cleaned_data['id_annee']
            id_campus = form.cleaned_data['id_campus']
            id_cycle = form.cleaned_data['id_cycle']
            try:
                cours_par_classe = Cours_par_classe.objects.get(
                    id_annee=id_annee,
                    id_campus=id_campus,
                    id_cycle=id_cycle,
                    id_classe=id_classe,
                    id_cours_classe=id_cours_classe_id  
                )
            except Cours_par_classe.DoesNotExist:
                
                if is_ajax:
                    messages.error(request, 'Cours non trouvé pour cette classe, année et cycle.')
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Cours non trouvé pour cette classe, année et cycle.',
                        'redirect': '/attribution_cours'
                    })
                return render(request, 'enseignement/index_enseignement.html', {'form_attrib': form})

            if Attribution_cours.objects.filter(
                id_annee=id_annee,
                id_cycle=id_cycle,
                id_classe=id_classe,
                id_cours=cours_par_classe  
            ).exists():
               
                if is_ajax:
                    messages.error(request, 'Ce cours est déjà attribué à cette classe.')
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Ce cours est déjà attribué à cette classe.',
                        'redirect': '/attribution_cours'
                    })
                return render(request, 'enseignement/index_enseignement.html', {'form_attrib': form})

            try:
                attribution = form.save(commit=False)
                attribution.id_cours_classe = cours_par_classe
                attribution.save()
                if is_ajax:
                    messages.success(request, 'Attribution enregistrée avec succès.')
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Attribution enregistrée avec succès.',
                        'redirect': '/list_cours_attribution'
                    })
            except Exception as e:
                if is_ajax:
                    messages.error(request, f'Erreur lors de l’enregistrement : {str(e)}')
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Erreur lors de l’enregistrement : {str(e)}',
                        'redirect': '/attribution_cours'
                    })
                return render(request, 'enseignement/index_enseignement.html', {'form_attrib': form})
        else:
            if is_ajax:
                messages.error(request, f'Formulaire invalide : {form.errors.as_text()}')
                return JsonResponse({
                    'status': 'error',
                    'message': f'Formulaire invalide : {form.errors.as_text()}',
                    'redirect': '/attribution_cours'
                })
            return render(request, 'enseignement/index_enseignement.html', {'form_attrib': form})

    form = Attribution_coursForm()
    return render(request, 'enseignement/index_enseignement.html', {'form_attrib': form,
                                                                     "photo_profil":user_modules['photo_profil'],
                                                                     "modules": user_modules['modules'],
                                                                     "last_name": user_modules['last_name']})

@login_required
def update_attribution_cours(request, id_attribution):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            attribution_type_id = data.get('attribution_type')
            id_personnel = data.get('id_personnel')

            if not all([attribution_type_id, id_personnel]):
                return JsonResponse({
                    'success': False,
                    'error': "Tous les champs modifiables sont requis."
                }, status=400)

            attribution = Attribution_cours.objects.get(id_attribution=id_attribution)
            try:
                attribution_type = Attribution_type.objects.get(id_attribution_type=attribution_type_id)
                personnel = Personnel.objects.get(id_personnel=id_personnel)
                if not all([attribution_type, personnel.is_verified]):
                    return JsonResponse({
                        'success': False,
                        'error': "Le type ou le personnel sélectionné est désactivé."
                    }, status=400)
            except (Attribution_type.DoesNotExist, Personnel.DoesNotExist) as e:
                return JsonResponse({
                    'success': False,
                    'error': "Type ou personnel non trouvé."
                }, status=404)

            if Attribution_cours.objects.filter(
                id_cours=attribution.id_cours,
                id_personnel=personnel,
                id_classe=attribution.id_classe
            ).exclude(id_attribution=id_attribution).exists():
                return JsonResponse({
                    'success': False,
                    'error': "Ce cours est déjà attribué à ce personnel pour cette classe."
                }, status=400)
            attribution.attribution_type = attribution_type
            attribution.id_personnel = personnel
            attribution.save()
            return JsonResponse({
                'success': True,
                'message': "Attribution mise à jour avec succès."
            })

        except Attribution_cours.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Attribution non trouvée."
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
def get_active_attribution_types(request):
    try:
        types = Attribution_type.objects.all().values('id_attribution_type', 'attribution_type')
        return JsonResponse({'types': list(types)})
    except Exception as e:
        return JsonResponse({'types': []}, status=500)

@login_required
def get_active_personnel(request):
    try:
        personnel = Personnel.objects.filter(isUser = True,en_fonction = True,is_verified=True).values('id_personnel', 'user__first_name', 'user__last_name')
        return JsonResponse({'personnel': list(personnel)})
    except Exception as e:
        return JsonResponse({'personnel': []}, status=500)

@login_required
def get_attributions_html(request):
    annee_id = request.GET.get("id_annee")
    campus_id = request.GET.get("id_campus")
    cycle_id = request.GET.get("id_cycle")
    classe_id = request.GET.get("id_classe")

    attributions = Attribution_cours.objects.filter(
        id_annee_id=annee_id,
        id_campus=campus_id,
        id_cycle=cycle_id,
        id_classe_id=classe_id
    )
    return render(request, "enseignement/partials/attributions_table_rows.html", {"cours_attribution": attributions})

@login_required
def get_all_course_attribute(request):
    user_info = get_user_info(request)
    full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]

    try:
        personnel = request.user.personnel
    except AttributeError:
        return render(request, "enseignement/index_enseignement.html", {
            'cours_attribution': [],
            "photo_profil": user_info['photo_profil'],
            "modules": user_info['modules'],
            "last_name": user_info['last_name']
        })

    current_year = Attribution_cours.objects.filter(id_annee__etat_annee="En Cours").values_list('id_annee', flat=True).distinct()

    if not current_year:
        return render(request, "enseignement/index_enseignement.html", {
            'cours_attribution': [],
            "photo_profil": user_info['photo_profil'],
            "modules": user_info['modules'],
            "last_name": user_info['last_name']
        })

    user_modules = UserModule.objects.filter(user=personnel, id_annee__in=current_year, is_active=True).values_list('module__module', flat=True)
    has_full_access = any(module in full_access_modules for module in user_modules)

    if has_full_access:
        cours_attrib = Attribution_cours.objects.filter(id_annee__etat_annee="En Cours")
    else:
        cycles_ids = Classe_active_responsable.objects.filter(
            id_personnel=personnel,
            id_annee__in=current_year
        ).values_list('id_cycle', flat=True)

        cours_attrib = Attribution_cours.objects.filter(
            id_annee__etat_annee="En Cours",
            id_cycle__in=cycles_ids
        )

    return render(request, "enseignement/index_enseignement.html", {
        'cours_attribution': cours_attrib,
        "photo_profil": user_info['photo_profil'],
        "modules": user_info['modules'],
        "last_name": user_info['last_name']
    })

@login_required
@module_required("Enseignement")
def attribute_cours_display(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form = Attribution_coursForm(request.POST or None)  
    return render(request, 'enseignement/index_enseignement.html', {
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name'],
        'form_attrib': form, 
        'form_type': 'cours_attribuer',
        
    })
# ===========================Api getting course in select to add new course

@login_required
def get_all_coursPar_cycle_annee(request):
    cycle_id = request.GET.get('id_cycle')
    annee_id = request.GET.get('id_annee')
    campus_id = request.GET.get('id_campus')
    classe_id = request.GET.get('id_classe') 

    try:
        cours_par_cycle = Cours_par_cycle.objects.filter(
            id_campus=campus_id,
            id_annee=annee_id,
            cycle_id=cycle_id
        )
        if not cours_par_cycle.exists():
            return JsonResponse([], safe=False)

        cours_deja_enregistres_ids = Cours_par_classe.objects.filter(
            id_campus=campus_id,
            id_annee=annee_id,
            id_cycle=cycle_id,
            id_classe=classe_id
        ).values_list('id_cours_id', flat=True)

        cours_list = [
            {
                'id_cours': c.cours_id.id_cours,
                'cours': c.cours_id.cours
            }
            for c in cours_par_cycle
            if c.cours_id.id_cours 
            #  not in cours_deja_enregistres_ids
        ]
        return JsonResponse(cours_list, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_cours_by_classe(request):
    id_campus = request.GET.get("id_campus")
    id_cycle = request.GET.get("id_cycle")
    id_classe = request.GET.get("id_classe")
    id_annee = request.GET.get("id_annee")

    cours_list = []

    if id_campus and id_cycle and id_classe and id_annee:
        try:
            id_campus = int(id_campus)
            id_cycle = int(id_cycle)
            id_classe = int(id_classe)
            id_annee = int(id_annee)
        except (TypeError, ValueError):
            return JsonResponse({'cours_list': cours_list})

        try:
            personnel = request.user.personnel
        except AttributeError:
            return JsonResponse({'cours_list': cours_list})

        user_modules = UserModule.objects.filter(
            user_id=personnel.id_personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        cours_qs = Cours_par_classe.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe,
        ).select_related("id_cours")

        if not has_full_access:
            attribution_cours = Attribution_cours.objects.filter(
                id_personnel=personnel.id_personnel,
                id_annee_id=id_annee,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_classe_id=id_classe
            ).select_related('id_cycle', 'id_classe', 'id_cours__id_cours').values('id_cours')
            cours_qs = cours_qs.filter(
                id_cours_classe__in=[ac['id_cours'] for ac in attribution_cours]
            )
        cours_list = [
            {
                "id": cours.id_cours_classe,
                "label": cours.id_cours.cours,
                "code": cours.id_cours.code_cours
            }
            for cours in cours_qs
        ]
    return JsonResponse({'data': cours_list})

@login_required
def get_cours_by_classe_par_type_notes(request):
    id_campus = request.GET.get("id_campus")
    id_cycle = request.GET.get("id_cycle")
    id_classe = request.GET.get("id_classe")
    id_annee = request.GET.get("id_annee")
    id_type_note = request.GET.get("id_type_note")

    cours_list = []

    if id_campus and id_cycle and id_classe and id_annee and id_type_note:
        try:
            id_campus = int(id_campus)
            id_cycle = int(id_cycle)
            id_classe = int(id_classe)
            id_annee = int(id_annee)
            id_type_note = int(id_type_note)
        except (TypeError, ValueError):
            return JsonResponse({'data': cours_list})

        try:
            personnel = request.user.personnel
        except AttributeError:
            return JsonResponse({'data': cours_list})

        user_modules = UserModule.objects.filter(
            user_id=personnel.id_personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        cours_ids_with_notes = Eleve_note.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle,
            id_classe_active_id=id_classe,
            id_type_note_id=id_type_note
        ).values_list('id_cours_id', flat=True).distinct()

        cours_qs = Cours_par_classe.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe,
            id_cours_classe__in=cours_ids_with_notes  
        ).select_related("id_cours")

        if not has_full_access:
            attribution_cours = Attribution_cours.objects.filter(
                id_personnel=personnel.id_personnel,
                id_annee_id=id_annee,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_classe_id=id_classe
            ).values_list('id_cours', flat=True)

            cours_qs = cours_qs.filter(
                id_cours_id__in=attribution_cours
            )

        cours_list = [
            {
                "id": cours.id_cours_classe,
                "label": cours.id_cours.cours,
                "code": cours.id_cours.code_cours
            }
            for cours in cours_qs
        ]

    return JsonResponse({'data': cours_list})



@login_required
def get_cours_by_classe_titulaire(request):
    id_campus = request.GET.get("id_campus")
    id_cycle = request.GET.get("id_cycle")
    id_classe = request.GET.get("id_classe")
    id_annee = request.GET.get("id_annee")

    cours_list = []

    if id_campus and id_cycle and id_classe and id_annee:
        try:
            id_campus = int(id_campus)
            id_cycle = int(id_cycle)
            id_classe = int(id_classe)
            id_annee = int(id_annee)
        except (TypeError, ValueError):
            return JsonResponse({'cours_list': cours_list})

        try:
            personnel = request.user.personnel
        except AttributeError:
            return JsonResponse({'cours_list': cours_list})

        user_modules = UserModule.objects.filter(
            user_id=personnel.id_personnel,
            id_annee=id_annee,
            is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        cours_qs = Cours_par_classe.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe
        ).select_related("id_cours")

        if not has_full_access:
            is_responsable = Classe_active_responsable.objects.filter(
                personnel=personnel,
                id_annee_id=id_annee,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_classe_id=id_classe
            ).exists()

            if not is_responsable:
                return JsonResponse({'data': []})

        cours_list = [
            {
                "id": cours.id_cours_classe,
                "label": cours.id_cours.cours,
                "code": cours.id_cours.code_cours,
                "tp": cours.TP  
            }
            for cours in cours_qs
        ]

    return JsonResponse({'data': cours_list})

@login_required
def get_non_attributed_cours_by_classe(request):
    id_campus = request.GET.get("id_campus")
    id_cycle = request.GET.get("id_cycle")
    id_classe = request.GET.get("id_classe")
    id_annee = request.GET.get("id_annee")

    cours_list = []

    if id_campus and id_cycle and id_classe and id_annee:
        cours_qs = Cours_par_classe.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe,
        ).select_related("id_cours")

        cours_attribues_ids = Attribution_cours.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe,
        ).values_list("id_cours_id", flat=True)

        cours_non_attribues = cours_qs.exclude(id_cours_classe__in=cours_attribues_ids)

        cours_list = [
            {
                "id": cours.id_cours_classe,
                "label": cours.id_cours.cours,
                "code": cours.id_cours.code_cours
            }
            for cours in cours_non_attribues
        ]

    return JsonResponse({'cours_list': cours_list})


@login_required
def get_cours_table(request):
    classe_id = request.GET.get("id_classe")
    annee_id = request.GET.get("id_annee")
    cycle_id = request.GET.get("id_cycle")
    campus_id = request.GET.get("id_campus")

    try:
        classe_active = Classe_active.objects.get(id_classe_active=classe_id)
        cours_qs = Cours_par_classe.objects.filter(
            id_annee=annee_id,
            id_campus=campus_id,
            id_cycle=cycle_id,
            id_classe=classe_active.id_classe_active
        ).select_related("id_cours")

        # Récupérer la localisation du campus
        campus = Campus.objects.get(id_campus=campus_id)  
        localisation = campus.localisation  

        cours = list(cours_qs.values(
            "id_cours_classe", 
            "id_cours__cours", 
            "id_cours__code_cours", 
            "ponderation", 
            "CM", 
            "TD", 
            "TP", 
            "TPE",
            "TPE",
            "compte_au_nombre_echec",
            "total_considerable_trimestre",
            "est_considerer_echec_lorsque_pourcentage_est",
            "credits",
            "ordre_cours",
            "is_second_semester",
            "heure_semaine"
        ))

        return JsonResponse({
            'localisation': localisation,
            'cours': cours
        }, safe=False)

    except (Classe_active.DoesNotExist, Campus.DoesNotExist):
        return JsonResponse({'error': 'Classe_active ou Campus non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)




@login_required
def check_cours_parClasse_pop(request):
    id_classe = request.GET.get('id_classe') 
    cours_id = request.GET.get('cours_id') 
    Annee_id = request.GET.get('id_annee')  
    cycle_id = request.GET.get('cycle_id')  
    if not id_classe:
        return JsonResponse({'error': 'Aucun id de classe spécifié.'}, status=400)
    if not cours_id:
        return JsonResponse({'error': 'Aucun ID de cours spécifié.'}, status=400)
    if not cycle_id:
        return JsonResponse({'error': 'Aucun ID de cycle spécifié.'}, status=400)
    if not Annee_id:
        return JsonResponse({'error': 'Aucun ID de cours spécifié.'}, status=400)
    course_in_classe = Cours_par_classe.objects.filter(id_annee = Annee_id,id_cours=cours_id,id_cycle =cycle_id,id_classe=id_classe)
    if course_in_classe.exists():
        return JsonResponse({'exists': True}, safe=False)
    else:
        return JsonResponse({'exists': False}, safe=False)

@login_required
def check_cours_parCycle_pop(request):
    id_cycle = request.GET.get('id_cycle') 
    cours_id = request.GET.get('cours_id') 
    annee_id = request.GET.get('id_annee')  

    if not id_cycle:
        return JsonResponse({'error': 'Aucun cycle spécifié.'}, status=400)

    if not cours_id:
        return JsonResponse({'error': 'Aucun ID de cours spécifié.'}, status=400)
    course_in_cycle = Cours_par_cycle.objects.filter(id_annee=annee_id, cycle_id=id_cycle,cours_id=cours_id)
    if not course_in_cycle.exists():
        return JsonResponse({'error': 'Le cours sélectionné n\'est pas disponible pour ce cycle.'}, status=400)
    return JsonResponse({'message': 'Le cours est disponible dans ce cycle.'}, safe=False)

@login_required
def get_cycles_parCours(request):
    id_cours = request.GET.get('id_cours')
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')


    if not id_cours or not id_annee or not id_campus or id_cours == 'undefined' or id_annee == 'undefined' or id_campus == 'undefined':
        return JsonResponse({'error': 'Paramètres manquants ou invalides'}, status=400)

    try:
        unique_cycles = set()
        cycles = []

        cycles_qs = Cours_par_cycle.objects.filter(
            id_annee=id_annee,
            id_campus=id_campus,
            cours_id=id_cours
        ).select_related('cycle_id__cycle_id')

        for c in cycles_qs:
            cycle_obj = c.cycle_id 
            cycle_key = cycle_obj.id_cycle_actif 
            if cycle_key not in unique_cycles:
                unique_cycles.add(cycle_key)
                cycles.append({
                    'id_cycle': cycle_obj.id_cycle_actif, 
                    'cycle': cycle_obj.cycle_id.cycle  
                })

        return JsonResponse({'cycles': cycles}, safe=False)

    except Exception as e:
        return JsonResponse({'error': 'Erreur interne du serveur'}, status=500)

@login_required
def get_cycles_parAnnee_pop(request):
    id_annee = request.GET.get('id_annee')
    if id_annee:
        cycles = list(Classe_cycle_actif.objects.filter(id_annee=id_annee).values('id_cycle', 'cycle'))
    else:
        cycles = []

    return JsonResponse({'cycles': cycles}, safe=False)

@login_required
def get_classes_pop(request):
    id_cours = request.GET.get('id_cours')
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')

    classes = []

    if id_cours and id_annee and id_cycle:
        classes_qs = Cours_par_classe.objects.filter(
            id_cours=id_cours,
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle=id_cycle
        ).select_related('id_classe__classe_id')

        classes = [
            {
                'id_classe': item.id_classe.id_classe_active,
                'classe': f"{item.id_classe.classe_id.classe}{'_' + item.id_classe.groupe if item.id_classe.groupe else ''}"
            }
            for item in classes_qs
        ]

        
    return JsonResponse({'classes': classes}, safe=False)
# ===================================Gestion d'horaires
@login_required
@module_required("Enseignement")
def etablir_type_horaire(request):
    from MonEcole_app.models.horaire import Horaire_type
    horaire_type_list = Horaire_type.objects.all()
    user_info = get_user_info(request)
    user_modules = user_info
    if 'type_horaire' in request.path:  
        show_nav = True
    if request.method == "POST":
        horaire_type = request.POST.get('horaire_type')
        form_horaire_type = HoraireTypeForm(request.POST)
        if form_horaire_type.is_valid():
            horaire_type_existant = Horaire_type.objects.filter(horaire_type = horaire_type)
            if horaire_type_existant.exists():
                messages.error(request,"Désolé!ce type d'horaire existe déjà!")
                return redirect("type_horaire")  
            else:
                form_horaire_type.save()
                messages.success(request, "Opération effectuée avec succès !")
                return redirect("type_horaire")  
        else:
            messages.error(request, "Erreur lors de l'ajout du type d'horaire. Vérifiez les informations fournies puis reessayer!.")
    else:
        form_horaire_type= HoraireTypeForm()
    return render(request,  'enseignement/horaire.html', {
        'horaire_type_list': horaire_type_list,
        'form_horaire_type': form_horaire_type,
        'show_nav': show_nav,
        'form_type': 'horaire_type',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
        })
    

@login_required
def save_session_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            for key, value in data.items():
                request.session[key] = value
            request.session.modified = True
            return JsonResponse({'status': 'success'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@login_required
@module_required("Enseignement")
def etablir_horaire_annuelle(request):
    from MonEcole_app.models.horaire import Horaire_type,Horaire
    selected_classe_data = request.session.get("selected_classe_data")
    show_nav = 'create_horaire' in request.path
    user_info = get_user_info(request)
    user_modules = user_info
    form_horaire = HoraireForm()

    campus_id = cycle_id = classe_id = None

    if selected_classe_data:
        try:
            parsed_data = json.loads(selected_classe_data)
            campus_id = parsed_data.get("id_campus")
            cycle_id = parsed_data.get("id_cycle")
            classe_id = parsed_data.get("id_classe")
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Erreur de décodage des données de session.")

    if request.method == "POST":
        id_annee = request.POST.get('id_annee') or request.session.get("id_annee")
        id_horaire_type = request.POST.get('id_horaire_type') or request.session.get("id_horaire_type")
        campus_id = request.POST.get('id_campus') or campus_id
        cycle_id = request.POST.get('id_cycle') or cycle_id
        classe_id = request.POST.get('id_classe') or classe_id

        if not (campus_id and cycle_id and classe_id):
            messages.error(request, "Veuillez sélectionner une classe avant de créer un horaire.")
            return redirect("create_horaire")

        try:
            campus = Campus.objects.get(id_campus=campus_id)
            cycle = Classe_cycle_actif.objects.get(id_campus = campus,id_annee = id_annee, id_cycle_actif=cycle_id)
            classe = Classe_active.objects.get(id_campus = campus,id_annee = id_annee, cycle_id=cycle_id,id_classe_active=classe_id)
            annee = Annee.objects.get(id_annee=id_annee)
            horaire_type = Horaire_type.objects.get(id_horaire_type=id_horaire_type)
            
        except Exception as e:
            messages.error(request, f"Données invalides (campus, cycle, classe, année ou type d'horaire) : {str(e)}")
            return redirect("create_horaire")

        jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        errors = False
        

        horaires_crees = 0  

        for i in range(1, 9):  
            debut = request.POST.get(f'horaire[{i}][debut]')
            fin = request.POST.get(f'horaire[{i}][fin]')

            if not debut or not fin:
                continue

            for jour in jours:
                cours_id = request.POST.get(f'horaire[{i}][{jour}][cours]')
                if cours_id and cours_id.strip():
                    if not cours_id.isdigit():
                        messages.error(request, f"Cours invalide pour {jour}, ligne {i}.")
                        errors = True
                        break

                    try:
                        cours = Cours_par_classe.objects.get(
                            id_cours_classe = cours_id,
                            id_annee=annee,
                            id_cycle=cycle,
                            id_classe=classe
                        )
                    except Cours_par_classe.DoesNotExist:
                        messages.error(request, f"Cours introuvable pour {jour}, ligne {i}. ID : {cours_id}")
                        errors = True
                        break
                    except Cours_par_classe.MultipleObjectsReturned:
                        messages.error(request, f"Plusieurs cours trouvés pour l'ID {cours_id} à la ligne {i}.")
                        errors = True
                        break

                    horaire = Horaire(
                        id_campus=campus,
                        id_annee=annee,
                        id_cycle=cycle,
                        id_classe=classe,
                        id_horaire_type=horaire_type,
                        id_cours=cours,
                        debut=debut,
                        fin=fin,
                        jour=jour
                    )
                    try:
                        horaire.full_clean()
                        horaire.save()
                        horaires_crees += 1  
                    except Exception as e:
                        messages.error(request, f"Erreur en sauvegardant l'horaire pour {jour}, ligne {i} : {str(e)}")
                        errors = True
                        break
            if errors:
                break

        if not errors and horaires_crees > 0:
            messages.success(request, "L'horaire a été enregistré avec succès.")
            return redirect("create_horaire")
        elif not errors and horaires_crees == 0:
            messages.error(request, "Aucun horaire n'a été saisi. Veuillez remplir au moins une ligne.")


    return render(request, 'enseignement/horaire.html', {
        'form_horaire': form_horaire,
        'show_nav': show_nav,
        'form_type': 'horaire',
        'horaire_tab': 'horaire_tab',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],        
    })

@login_required
@module_required("Enseignement")
def view_horaire(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_horaire = HoraireForm(request.POST or None)
    return render(request, 'enseignement/horaire.html', {
        'affich_horaire': form_horaire,
        'form_type': 'horaire_affich',
        'view_only': True,
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
    })


@login_required
def afficher_horaire(request):
    from MonEcole_app.models.horaire import Horaire
    from MonEcole_app.models import Attribution_cours 
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')
    id_annee = request.GET.get('id_annee')
    
    if not all([id_campus, id_cycle, id_classe, id_annee]):
        return JsonResponse({'success': False, 'message': 'Paramètres manquants'})

    try:
        id_campus = int(id_campus)
        id_cycle = int(id_cycle)
        id_classe = int(id_classe)
        id_annee = int(id_annee)

        horaires = Horaire.objects.filter(
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe=id_classe,
            id_annee_id=id_annee
        )

        horaires_par_heures = {}
        jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

        for horaire in horaires:
            heure_debut = horaire.debut
            heure_fin = horaire.fin
            jour = horaire.jour
            heure_label = f"{heure_debut} - {heure_fin}"

            matiere = horaire.id_cours.id_cours.code_cours
            idcours_attribuer = horaire.id_cours

            enseignant = Attribution_cours.objects.filter(
                id_annee=id_annee,
                id_campus=id_campus,
                id_cycle=id_cycle,
                id_cours=idcours_attribuer
            ).first()

            if enseignant:
                nom_enseignant = enseignant.id_personnel.user.last_name
            else:
                nom_enseignant = "Non attribué"

            if heure_label not in horaires_par_heures:
                horaires_par_heures[heure_label] = {
                    jour: {'matiere': matiere, 'enseignant': nom_enseignant}
                }
            else:
                horaires_par_heures[heure_label][jour] = {
                    'matiere': matiere, 'enseignant': nom_enseignant
                }

        return JsonResponse({'success': True, 'horaires': horaires_par_heures, 'jours': jours})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def generate_horaire_pdf(request):
    from MonEcole_app.models.horaire import Horaire
    campus_id = request.GET.get("id_campus")
    cycle_id = request.GET.get("id_cycle")
    classe_id = request.GET.get("id_classe")
    annee_id = request.GET.get("id_annee")
    if not (campus_id and cycle_id and classe_id and annee_id):
        messages.error(request, "Veuillez sélectionner une classe et une année avant de générer l'horaire.")
        return redirect("afficher_horaire")

    try:
        campus = Campus.objects.get(id_campus=campus_id)
        cycle = Classe_cycle_actif.objects.get(id_cycle_actif=cycle_id)
        classe = Classe_active.objects.get(id_classe_active=classe_id)
        annee = Annee.objects.get(id_annee=annee_id)
    except Exception as e:
        messages.error(request, f"Données invalides : {str(e)}")
        return redirect("afficher_horaire")

    horaires_queryset = Horaire.objects.filter(
        id_classe=classe,
        id_annee=annee,
        id_cycle=cycle,
        id_campus=campus
    ).order_by('debut', 'fin').distinct()

    tous_les_jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    jours = [jour for jour in tous_les_jours if jour in set(h.jour for h in horaires_queryset)]

    creaneaux_attendus = [
        ('07:20', '08:05'), ('08:05', '08:50'), ('08:50', '09:35'), ('09:35', '10:20'),
        ('10:50', '11:35'), ('11:35', '12:20'), ('12:20', '13:05'), ('13:05', '13:50')
    ]

    horaires = creaneaux_attendus[:8]
    response = HttpResponse(content_type='application/pdf')
    groupe = f"_{classe.groupe}" if classe.groupe else ""
    response['Content-Disposition'] = f'attachment; filename="Horaire_cours_{classe.classe_id.classe}_{groupe}_{annee.annee}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=2*cm, leftMargin=2*cm, 
                            topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='Title', parent=styles['Heading1'], alignment=1, spaceAfter=12)
    header_style = ParagraphStyle(name='Header', parent=styles['Normal'], fontSize=12, spaceAfter=6)
    normal_style = styles['Normal']
    try:
        inst = Institution.objects.order_by('id_ecole').first()
    except Institution.DoesNotExist:
        inst = "institution non pris en charge"

    elements = []

    elements.extend([
        Paragraph(f"{inst or 'École Non Spécifiée'}", header_style),
        Paragraph(f"Année scolaire : {annee.annee}", header_style),
        Paragraph(f"Campus : {campus.campus}", header_style),
        Paragraph(f"Cycle : {cycle.cycle_id.cycle}", header_style),
        Paragraph(f"Classe : {classe.classe_id.classe}{'_' + classe.groupe if classe.groupe else ''}", header_style),
        Spacer(1, 0.2*cm),
        Paragraph("HORAIRE ANNUELLE DES COURS", title_style),
        Spacer(1, 0.3*cm)
    ])
    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm
    )
    doc.title = "Horaire annuel"
   
    table_data = [['Heure'] + jours]
    for index, (debut, fin) in enumerate(horaires):
        row = [f"{debut} - {fin}"]
        for jour in jours:
            try:
                horaire = Horaire.objects.get(
                    id_classe=classe,
                    id_annee=annee,
                    id_cycle=cycle,
                    id_campus=campus,
                    jour=jour,
                    debut=debut,
                    fin=fin
                )
                code_cours = horaire.id_cours.id_cours.code_cours if horaire.id_cours else ''
                row.append(code_cours)
            except Horaire.DoesNotExist:
                row.append('')
        table_data.append(row)

        if index == 3:
            table_data.append(['PAUSE'] + [''] * len(jours))

        if index == 5:
            table_data.append(['APRÈS-MIDI'] + [''] * len(jours))

    table = Table(table_data, colWidths=[4*cm] + [3*cm]*len(jours), rowHeights=[1*cm]*len(table_data))
    table.setStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    for i, row in enumerate(table_data):
        if row[0] == "PAUSE" or row[0] == "APRÈS-MIDI":
            table.setStyle([
                ('SPAN', (0, i), (-1, i)),
                ('FONTSIZE', (0, i), (-1, i), 12),
                ('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'),
                ('BACKGROUND', (0, i), (-1, i), colors.lightgrey),
            ])

    elements.append(table)
    elements.append(Spacer(1, 0.5*cm))
    doc.build(elements)
    return response

@login_required
def get_horaire_parclasse_annee(request):
    from MonEcole_app.models.horaire import Horaire
    classe_id = request.GET.get("id_classe")
    cycle_id = request.GET.get("id_cycle")
    campus_id = request.GET.get("id_campus")
    annee_id = request.GET.get("id_annee")

    if not (classe_id and cycle_id and campus_id and annee_id):
        return JsonResponse({'success': False, 'message': 'Paramètres manquants'})

    horaires = Horaire.objects.filter(
        id_classe_id=classe_id,
        id_cycle_id=cycle_id,
        id_campus_id=campus_id,
        id_annee_id=annee_id
    ).select_related('id_cours')

    if not horaires.exists():
        return JsonResponse({'success': False, 'data': {}})

    horaire_dict = {}

    for h in horaires:
        key = f"{h.debut} - {h.fin}"
        if key not in horaire_dict:
            horaire_dict[key] = {}

        horaire_dict[key][h.jour] = h.id_cours.cours  

    return JsonResponse({'success': True, 'data': horaire_dict})

@login_required
def get_classes_with_horaire(request):
    from MonEcole_app.models import Horaire
    annee_id = request.GET.get("id_annee")
    if not annee_id:
        return JsonResponse({'success': False, 'message': 'Année scolaire manquante'})

    try:
       
        personnel = request.user.personnel  
        user_modules = UserModule.objects.filter(
            user=personnel,
            id_annee_id=annee_id,
            is_active=True
        ).values_list('module__module', flat=True)
        if user_modules:
            horaires_qs = Horaire.objects.filter(id_annee_id=annee_id).values(
                'id_classe_id', 'id_cycle_id', 'id_campus_id'
            ).distinct()
        else:
            classes_id = Classe_active_responsable.objects.filter(
                id_personnel=personnel,
                id_annee_id=annee_id
            ).values_list('id_classe', flat=True)

            if not classes_id.exists():
                return JsonResponse({'success': False, 'message': "Aucune classe liée à cet utilisateur."})

            horaires_qs = Horaire.objects.filter(
                id_annee_id=annee_id,
                id_classe_id__in=classes_id
            ).values('id_classe_id', 'id_cycle_id', 'id_campus_id').distinct()

        if not horaires_qs.exists():
            return JsonResponse({'success': False, 'message': 'Aucune classe avec horaire trouvée.'})

        classes = []
        for h in horaires_qs:
            try:
                campus = Campus.objects.get(id_campus=h['id_campus_id'])
                classe_active = Classe_active.objects.get(
                    id_annee_id=annee_id,
                    id_campus=campus,
                    cycle_id=h['id_cycle_id'],
                    id_classe_active=h['id_classe_id']
                )
                cycle_actif = Classe_cycle_actif.objects.get(
                    id_annee_id=annee_id,
                    id_campus=campus,
                    id_cycle_actif=h['id_cycle_id']
                )
                classe = classe_active.classe_id
                cycle = cycle_actif.cycle_id
                groupe = classe_active.groupe or ""

                label_parts = [campus.campus, cycle.cycle, classe.classe]
                if groupe:
                    label_parts.append(groupe)
                label = "_".join(label_parts)

                classes.append({
                    'id': classe_active.id_classe_active,
                    'label': label,
                    'id_campus': campus.id_campus,
                    'id_cycle': cycle_actif.id_cycle_actif,
                    'id_classe': classe.id_classe,
                    'groupe': groupe
                })
            except (Classe_active.DoesNotExist, Classe_cycle_actif.DoesNotExist, Campus.DoesNotExist):
                continue  

        return JsonResponse({'success': True, 'data': classes})

    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Erreur serveur : {str(e)}"})


@login_required
def load_classes_by_year_exclude_classes_schedule(request):
    from MonEcole_app.models.horaire import Horaire
    from django.db.models import Exists, OuterRef

    annee_id = request.GET.get('id_annee')
    user = request.user
    data = []

    if not annee_id or annee_id == 'undefined':
        return JsonResponse({'error': 'id_annee manquant ou invalide'}, status=400)

    try:
        personnel = user.personnel
    except AttributeError:
        return JsonResponse({"data": data})

    try:
        user_modules = UserModule.objects.filter(
            user=personnel,
            id_annee_id=annee_id,
            is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]

        classes_avec_horaires = Horaire.objects.filter(
            id_annee_id=annee_id
        ).values_list('id_classe_id', flat=True)

        cours_exists = Cours_par_classe.objects.filter(
            id_annee_id=annee_id,
            id_classe_id=OuterRef('pk')
        )

        if any(module in full_access_modules for module in user_modules):
            classes = Classe_active.objects.annotate(
                has_cours=Exists(cours_exists)
            ).filter(
                id_annee_id=annee_id,
                has_cours=True
            ).exclude(
                id_classe_active__in=classes_avec_horaires
            )
        else:
            classes_id = Classe_active_responsable.objects.filter(
                id_personnel=personnel,
                id_annee_id=annee_id
            ).values_list('id_classe', flat=True)

            classes = Classe_active.objects.annotate(
                has_cours=Exists(cours_exists)
            ).filter(
                id_annee_id=annee_id,
                id_classe_active__in=classes_id,
                has_cours=True
            ).exclude(
                id_classe_active__in=classes_avec_horaires
            )

        classes = classes.select_related('id_campus', 'cycle_id__cycle_id', 'classe_id').order_by('cycle_id__cycle_id')

        for classe in classes:
            nom_campus = classe.id_campus.campus
            nom_cycle = classe.cycle_id.cycle_id.cycle
            nom_classe = classe.classe_id.classe
            groupe = classe.groupe or ""
            label = f"{nom_campus} - {nom_cycle} - {nom_classe} {groupe}".strip()

            data.append({
                "id": classe.id_classe_active,
                "label": label,
                "id_campus": classe.id_campus.id_campus,
                "id_cycle": classe.cycle_id.id_cycle_actif,
                "id_classe": classe.classe_id.id_classe
            })

        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({'error': 'Erreur interne du serveur'}, status=500)


@login_required
def get_horaire_type(request):
    from MonEcole_app.models.horaire import Horaire_type
    horaire_types = Horaire_type.objects.all()  
    data = [{"id": h.id_horaire_type, "label": h.horaire_type} for h in horaire_types]
    return JsonResponse(data, safe=False)


@login_required
def update_cours_classe(request, id_cours_classe):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            cours_classe = Cours_par_classe.objects.get(id_cours_classe=id_cours_classe)

            if data.get('cours'):
                cours_classe.cours_id = int(data['cours'])

            if data.get('ponderation') is not None:
                cours_classe.ponderation = int(data['ponderation']) if data['ponderation'] else None

            if data.get('TP') is not None:
                cours_classe.TP = int(data['TP']) if data['TP'] else None

            if data.get('TPE') is not None:
                cours_classe.TPE = int(data['TPE']) if data['TPE'] else None

            if data.get('heure_semaine') is not None:
                cours_classe.heure_semaine = int(data['heure_semaine']) if data['heure_semaine'] else None

            if data.get('credits') is not None:
                cours_classe.credits = int(data['credits']) if data['credits'] else None

            if data.get('ordre_cours') is not None:
                cours_classe.ordre_cours = int(data['ordre_cours']) if data['ordre_cours'] else None

            cours_classe.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Mise à jour réussie !'
            })

        except Cours_par_classe.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Cours par classe non trouvé.'
            }, status=404)

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': 'Méthode non autorisée.'
    }, status=405)




@login_required
def update_cours_par_cycle(request, id_cours_cycle):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            id_campus = data.get('id_campus')
            id_annee = data.get('id_annee')
            cours_id = data.get('cours_id')
            cycle_id = data.get('cycle_id')

            if not all([id_campus, id_annee, cours_id, cycle_id]):
                return JsonResponse({
                    'success': False,
                    'error': "Tous les champs sont requis."
                }, status=400)
            dependencies = []
            cours_cycle = Cours_par_cycle.objects.get(id_cours_cycle=id_cours_cycle)
            if Cours_par_classe.objects.filter(id_cours=id_cours_cycle).exists():
                dependencies.append("cours par classes")

            if dependencies:
                error_msg = f"Impossible de modifier le cours, car il est utilisée dans : {', '.join(dependencies)}."
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                }, status=400)
            try:
                campus = Campus.objects.get(id_campus=id_campus)
                annee = Annee.objects.get(id_annee=id_annee)
                cours = Cours.objects.get(id_cours=cours_id)
                cycle = Classe_cycle_actif.objects.get(id_cycle_actif=cycle_id)
                if not all([campus.is_active, annee.is_active, cycle.is_active]):
                    return JsonResponse({
                        'success': False,
                        'error': "Le campus, l'année ou le cycle sélectionné est désactivé."
                    }, status=400)
            except (Campus.DoesNotExist, Annee.DoesNotExist, Cours.DoesNotExist, Classe_cycle_actif.DoesNotExist) as e:
                return JsonResponse({
                    'success': False,
                    'error': "Campus, année, cours ou cycle non trouvé."
                }, status=404)

            if Cours_par_cycle.objects.filter(
                cours_id=cours,
                cycle_id=cycle,
                id_annee=annee
            ).exclude(id_cours_cycle=id_cours_cycle).exists():
                return JsonResponse({
                    'success': False,
                    'error': "Une combinaison cours, cycle, année existe déjà."
                }, status=400)
            
            cours_cycle.id_campus = campus
            cours_cycle.id_annee = annee
            cours_cycle.cours_id = cours
            cours_cycle.cycle_id = cycle
            cours_cycle.save()
            return JsonResponse({
                'success': True,
                'message': "Cours par cycle mis à jour avec succès."
            })

        except Cours_par_cycle.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Cours par cycle non trouvé."
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
def get_active_cours(request):
    try:
        cours = Cours.objects.all().values('id_cours', 'cours')
        return JsonResponse({'cours': list(cours)})
    except Exception as e:
        return JsonResponse({'cours': []}, status=500)

@login_required
def load_classes_by_year_exclude_responsible(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if not annee_id or annee_id == 'undefined':
        return JsonResponse({'error': 'id_annee manquant ou invalide'}, status=400)

    try:
        classes_avec_responsable = Classe_active_responsable.objects.filter(
            id_annee_id=annee_id
        ).values_list('id_classe_id', flat=True)

        classes = Classe_active.objects.filter(id_annee_id=annee_id).select_related('id_campus', 'cycle_id__cycle_id', 'classe_id').order_by('cycle_id__cycle_id')
        for classe in classes:
            nom_campus = classe.id_campus.campus
            nom_cycle = classe.cycle_id.cycle_id.cycle
            nom_classe = classe.classe_id.classe
            groupe = classe.groupe or ""
            label = f"{nom_campus} - {nom_cycle} - {nom_classe} {groupe}".strip()

            data.append({
                "id": classe.id_classe_active,
                "label": label,
                "id_campus": classe.id_campus.id_campus,
                "id_cycle": classe.cycle_id.id_cycle_actif,
                "id_classe": classe.classe_id.id_classe
            })
        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({'error': 'Erreur interne du serveur'}, status=500)

@login_required
def load_all_classes_deliberates_by_yea_byTutilaire(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if annee_id:
        try:
            annee_id = int(annee_id)
        except (TypeError, ValueError) as e:
            return JsonResponse({"data": data})

        try:
            personnel = request.user.personnel
        except AttributeError as e:
            return JsonResponse({"data": data})

        user_modules = UserModule.objects.filter(
            user=personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        deliberation_classes = Deliberation_trimistrielle_resultat.objects.filter(
            id_annee_id=annee_id
        ).values('id_campus_id', 'id_cycle_id', 'id_classe_id').distinct()

        inscriptions_subquery = Eleve_inscription.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee_id=annee_id,
            status=True
        )

        classes_query = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery)
        ).filter(
            id_annee_id=annee_id,
            has_students=True,
            id_classe_active__in=[classe['id_classe_id'] for classe in deliberation_classes]
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        )

        if not has_full_access:
            cycles_ids = Classe_active_responsable.objects.filter(
                id_personnel=personnel,
                id_annee_id=annee_id
            ).values_list('id_cycle', flat=True)
            classes_query = classes_query.filter(
                cycle_id_id__in=cycles_ids
            )
            
        classes = classes_query.order_by('cycle_id__cycle_id')

        for classe in classes:
            nom_campus = classe.id_campus.campus
            nom_cycle = classe.cycle_id.cycle_id.cycle
            nom_classe = classe.classe_id
            groupe = classe.groupe or ""
            label = f"{nom_campus} - {nom_cycle} - {nom_classe} {groupe}".strip()

            data.append({
                "id": classe.id_classe_active,
                "label": label,
                "id_campus": classe.id_campus.id_campus,
                "id_cycle": classe.cycle_id.id_cycle_actif,
                "id_classe": classe.classe_id.id_classe
            })

    return JsonResponse({"data": data})




@csrf_protect
def update_is_second_semester(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        id_cours_classe = data.get('id_cours_classe')
        is_second_semester = data.get('is_second_semester')

        try:
            cours_classe = Cours_par_classe.objects.get(id_cours_classe=id_cours_classe)
            cours_classe.is_second_semester = is_second_semester
            cours_classe.save()
            return JsonResponse({'success': True, 'message': 'Mis à jour avec succès'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})