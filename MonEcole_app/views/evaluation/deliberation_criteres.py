
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from MonEcole_app.models.mention import Mention
from MonEcole_app.models.models_import import *
from MonEcole_app.forms.form_imports import (MentionForm,
                                             DeliberationTypeForm,
                                             DeliberationFinaliteForm,
                                             DeliberationConditionForm
                                             )
from django.contrib.auth.decorators import login_required
from MonEcole_app.views.tools.utils import get_user_info
from django.http import JsonResponse
from django.db.models import OuterRef, Exists, Count, Subquery,IntegerField
from django.db.models.functions import Coalesce
import json
from MonEcole_app.views.decorators.decorators import module_required
from django.views.decorators.http import require_http_methods
import logging
logger = logging.getLogger(__name__)



@login_required
@module_required("Evaluation")
def create_mention(request):
    user_info = get_user_info(request)
    user_modules = user_info
    mentions = Mention.objects.all().order_by('id_mention') 

    if request.method == 'POST':
        form_mention = MentionForm(request.POST)
        if form_mention.is_valid():
            try:
                form_mention.save()
                messages.success(request, "Mention ajoutée avec succès.")
                return redirect('create_mention') 
            except:
                messages.error(request, "Erreur lors de l'enregistrement. Veuillez réessayer.")
        else:
            if '__all__' in form_mention.errors:
                for error in form_mention.errors['__all__']:
                    messages.warning(request, error)
            else:
                messages.warning(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form_mention = MentionForm()

    return render(request, 'evaluation/index_evaluation.html', {
        'form_mention': form_mention,
        'mentions': mentions,
        'form_type': 'form_mention',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Evaluation")
def create_deliberation_type(request):
    user_info = get_user_info(request)
    user_modules = user_info
    type_deliberat_list = Deliberation_type.objects.all().order_by('id_deliberation_type') 
    if request.method == 'POST':
        form_type_delib = DeliberationTypeForm(request.POST)
        if form_type_delib.is_valid():
            try:
                form_type_delib.save()
                messages.success(request, "Type de délibération ajoutée avec succès.")
                return redirect('create_deliberation_type') 
            except:
                messages.error(request, "Erreur lors de l'enregistrement.Formulaire invalide")
        else:
            messages.warning(request, "Veuillez saisir les nouveaux éléments.car ceux que vous venez de saisir existe déjà!")
    else:
        form_type_delib = DeliberationTypeForm()
    return render(request, 'evaluation/index_evaluation.html',
                  {'form_type_delib': form_type_delib,
                   'type_deliberat_list': type_deliberat_list,
                   'form_type': 'form_type_delib', 
                    "photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']})

@login_required
@module_required("Evaluation")
def create_deliberation_finalite(request):
    user_info = get_user_info(request)
    user_modules = user_info
    finalit_deliberat_list = Deliberation_annuelle_finalite.objects.all().order_by('id_finalite') 
    if request.method == 'POST':
        form_finalit_delib = DeliberationFinaliteForm(request.POST)
        if form_finalit_delib.is_valid():
            try:
                finalite_obj = form_finalit_delib.save(commit=False)
                finalite_obj.save() 
                messages.success(request, "Type de finalité pour la délibération ajouté avec succès.")
                return redirect('create_deliberation_finalite') 
            except Exception as e:
                messages.error(request, f"Erreur lors de l'enregistrement : {str(e)}")
        else:
            messages.warning(request, "Veuillez saisir les nouveaux éléments. Car ceux que vous venez de saisir existent déjà !")
    else:
        form_finalit_delib = DeliberationFinaliteForm()

    return render(request, 'evaluation/index_evaluation.html', {
        'form_finalit_delib': form_finalit_delib,
        'finalit_deliberat_list': finalit_deliberat_list,
        'form_type': 'form_finalit_delib', 
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })


@login_required
@module_required("Evaluation")
def create_deliberation_condition(request):
    user_info = get_user_info(request)
    personnel = request.user.personnel  
    current_year = Annee.objects.filter(etat_annee="En Cours").values_list('id_annee', flat=True)
    user_modules = UserModule.objects.filter(
        user=personnel,
        id_annee__in=current_year,
        is_active=True
    ).values_list('module__module', flat=True)

    full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]

    has_full_access = any(module in full_access_modules for module in user_modules)

    if has_full_access:
        condit_deliberat_list = Deliberation_annuelle_condition.objects.all().order_by('id_decision')
    else:
        cycles_ids = Classe_active_responsable.objects.filter(
            id_personnel=personnel,
            id_annee__in=current_year
        ).values_list('id_cycle', flat=True)

        cours_attrib = Attribution_cours.objects.filter(
            id_annee__in=current_year,
            id_cycle__in=cycles_ids
        ).values_list('id_classe_id', flat=True)

        condit_deliberat_list = Deliberation_annuelle_condition.objects.filter(
            id_annee__in=current_year,
            id_classe_id__in=cours_attrib
        ).order_by('id_decision')

    if request.method == 'POST':
        form_condit_delib = DeliberationConditionForm(request.POST)
        if form_condit_delib.is_valid():
            try:
                form_condit_delib.save()
                messages.success(request, "Condition annuelle pour la délibération ajoutée avec succès.")
                return render(request, 'evaluation/index_evaluation.html', {
                    'form_condit_delib': DeliberationConditionForm(),
                    'condit_deliberat_list': condit_deliberat_list,
                    'form_type': 'form_condit_delib',
                    'photo_profil': user_info['photo_profil'],
                    'modules': user_info['modules'],
                    'last_name': user_info['last_name'],
                    'reset_session': True 
                })
            except Exception as e:
                messages.error(request, f"Erreur lors de l'enregistrement : {str(e)}")
        else:
            messages.error(request, f"Formulaire invalide. Erreurs : {form_condit_delib.errors}")
    else:
        form_condit_delib = DeliberationConditionForm()

    return render(request, 'evaluation/index_evaluation.html', {
        'form_condit_delib': form_condit_delib,
        'condit_deliberat_list': condit_deliberat_list,
        'form_type': 'form_condit_delib',
        'photo_profil': user_info['photo_profil'],
        'modules': user_info['modules'],
        'last_name': user_info['last_name']
    })


@login_required
def load_all_classes_by_year_with(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if annee_id:
        inscriptions_subquery = Eleve_inscription.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee_id=annee_id,
            status=True
        )
        classes = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery)
        ).filter(
            id_annee_id=annee_id,
            has_students=True
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        ).order_by('cycle_id__cycle_id')

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


@login_required
def load_all_classes_without_decision_deliberat_by_year(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if annee_id:
        personnel = request.user.personnel

        user_modules = (
            UserModule.objects
            .filter(user=personnel, id_annee=annee_id, is_active=True)
            .values_list('module__module', flat=True)
        )

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        inscriptions_subquery = Eleve_inscription.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee_id=annee_id,
            status=True
        )

        deliberation_count_subquery = Deliberation_annuelle_condition.objects.filter(
            id_annee_id=annee_id,
            id_campus_id=OuterRef('id_campus_id'),
            id_cycle_id=OuterRef('cycle_id_id'),
            id_classe_id=OuterRef('pk')
        ).values('id_classe_id').annotate(
            finalite_count=Count('id_finalite', distinct=True)
        ).values('finalite_count')[:1]

        total_finalites = Deliberation_annuelle_finalite.objects.count()

        classes = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery),
            finalite_count=Coalesce(Subquery(deliberation_count_subquery, output_field=IntegerField()), 0)
        ).filter(
            id_annee_id=annee_id,
            has_students=True,
            finalite_count__lt=total_finalites
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        ).order_by('cycle_id__cycle_id__cycle')

        if not has_full_access:
            classes = classes.filter(
                id_classe_active__in=Classe_active_responsable.objects.filter(
                    id_personnel=personnel,
                    id_annee_id=annee_id
                ).values_list('id_classe', flat=True)
            )

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


@login_required
def load_available_finalites(request):
    annee_id = request.GET.get('id_annee')
    campus_id = request.GET.get('id_campus')
    cycle_id = request.GET.get('id_cycle')
    classe_id = request.GET.get('id_classe')
    data = []

    if annee_id and campus_id and cycle_id and classe_id:
        used_finalites = Deliberation_annuelle_condition.objects.filter(
            id_annee_id=annee_id,
            id_campus_id=campus_id,
            id_cycle_id=cycle_id,
            id_classe_id=classe_id
        ).values_list('id_finalite_id', flat=True)

        available_finalites = Deliberation_annuelle_finalite.objects.exclude(
            id_finalite__in=used_finalites
        ).values('id_finalite', 'finalite')

        for finalite in available_finalites:
            data.append({
                'id': finalite['id_finalite'],
                'label': finalite['finalite']
            })

    return JsonResponse({"data": data})

@login_required
def load_all_finalites(request):
    finalites = Deliberation_annuelle_finalite.objects.values('id_finalite', 'finalite')
    data = [{"id": f['id_finalite'], "label": f['finalite']} for f in finalites]
    return JsonResponse({"data": data})

@login_required
def get_cycles_by_classe(request):
    classe_id = request.GET.get('id_classe')
    data = []

    if classe_id:
        try:
            classe_id = int(classe_id)
            cycles = Classe_active.objects.filter(
                id_classe_active=classe_id
            ).select_related('cycle_id').values(
                'cycle_id__id_cycle_actif',
                'cycle_id__cycle_id__cycle'
            ).distinct()

            for cycle in cycles:
                data.append({
                    'id_cycle': cycle['cycle_id__id_cycle_actif'],
                    'label': cycle['cycle_id__cycle_id__cycle']
                })

        except (ValueError, TypeError) as e:
            return JsonResponse({"data": []}, status=400)

    return JsonResponse({"data": data})

@login_required
def update_deliberation_condition(request, id_decision):
    condition = get_object_or_404(Deliberation_annuelle_condition, id_decision=id_decision)
    
    if request.method == 'POST':
        form = DeliberationConditionForm(request.POST, instance=condition)
        if form.is_valid():
            form.save()
            messages.success(request, "Condition de délibération mise à jour avec succès.")
            return redirect('list_deliberation_conditions')  
        else:
            messages.error(request, "Erreur lors de la mise à jour. Veuillez vérifier les données.")
    else:
        form = DeliberationConditionForm(instance=condition)
        condition_data = {
            'id_annee': condition.id_annee.annee,
            'id_campus': condition.id_campus.campus,
            'id_cycle': condition.id_cycle,
            'id_classe': condition.id_classe,
            'id_finalite': condition.id_finalite,
            'pourcentage_requis_reussite': condition.pourcentage_requis_reussite,
            'max_echecs_acceptable': condition.max_echecs_acceptable,
            'seuil_profondeur_echec': condition.seuil_profondeur_echec,
            'decision': condition.decision,
            'sigle': condition.sigle,
            'sanction_disciplinaire': condition.sanction_disciplinaire
        }

    return render(request, 'evalution/editer_cond.html', {
        'form_condit_delib': form,
        'is_edit_mode': True,
        'id_decision': id_decision,
        'condition_data': json.dumps(condition_data)
    })

@login_required
@module_required("Evaluation")
def mention_edit(request):
    if request.method == 'POST':
        id_mention = request.POST.get('id_mention')
        mention = get_object_or_404(Mention, id_mention=id_mention)
        form = MentionForm(request.POST, instance=mention)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            try:
                form.save()
                if is_ajax:
                    messages.success(request, 'Mention modifiée avec succès.')
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Mention modifiée avec succès.',
                        'redirect': '/create_mention'
                    })
            except Exception as e:
                if is_ajax:
                    messages.error(request, f'Erreur lors de l’enregistrement : {str(e)}')
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Erreur lors de l’enregistrement : {str(e)}',
                        'redirect': '/create_mention'
                    })
        else:
            if is_ajax:
                messages.error(request, f'Formulaire invalide : {form.errors.as_text()}')
                return JsonResponse({
                    'status': 'error',
                    'message': f'Formulaire invalide : {form.errors.as_text()}',
                    'redirect': '/create_mention'
                })
        return render(request, 'enseignement/index_evaluation.html', {'form': form})
    return render(request, 'enseignement/index_evaluation.html')

@login_required
@module_required("Evaluation")
def deliberation_type_edit(request):
    if request.method == 'POST':
        id_deliberation_type = request.POST.get('id_deliberation_type')
        deliberation_type = get_object_or_404(Deliberation_type, id_deliberation_type=id_deliberation_type)
        form = DeliberationTypeForm(request.POST, instance=deliberation_type)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            try:
                form.save()
                if is_ajax:
                    messages.success(request, 'Type de délibération modifié avec succès.')
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Type de délibération modifié avec succès.',
                        'redirect': '/create_deliberation_type'
                    })
            except Exception as e:
                if is_ajax:
                    messages.error(request, f'Erreur lors de l’enregistrement : {str(e)}')
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Erreur lors de l’enregistrement : {str(e)}',
                        'redirect': '/create_deliberation_type'
                    })
        else:
            if is_ajax:
                messages.error(request, f'Formulaire invalide : {form.errors.as_text()}')
                return JsonResponse({
                    'status': 'error',
                    'message': f'Formulaire invalide : {form.errors.as_text()}',
                    'redirect': '/create_deliberation_type'
                })
        return render(request, 'enseignement/index_evaluation.html', {'form': form})
    return render(request, 'enseignement/index_evaluation.html')

@login_required
@module_required("Evaluation")
def deliberation_finalite_edit(request):
    if request.method == 'POST':
        id_finalite = request.POST.get('id_finalite')
        finalite = get_object_or_404(Deliberation_annuelle_finalite, id_finalite=id_finalite)
        form = DeliberationFinaliteForm(request.POST, instance=finalite)
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if form.is_valid():
            try:
                form.save()
                if is_ajax:
                    messages.success(request, 'Finalité modifiée avec succès.')
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Finalité modifiée avec succès.',
                        'redirect': '/create_deliberation_finalite'
                    })
            except Exception as e:
                if is_ajax:
                    messages.error(request, f'Erreur lors de l’enregistrement : {str(e)}')
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Erreur lors de l’enregistrement : {str(e)}',
                        'redirect': '/create_deliberation_finalite'
                    })
        else:
            if is_ajax:
                messages.error(request, f'Formulaire invalide : {form.errors.as_text()}')
                return JsonResponse({
                    'status': 'error',
                    'message': f'Formulaire invalide : {form.errors.as_text()}',
                    'redirect': '/create_deliberation_finalite'
                })
        return render(request, 'enseignement/index_evaluation.html', {'form': form})
    return render(request, 'enseignement/index_evaluation.html')

@login_required
@module_required("Evaluation")
@require_http_methods(["PUT"])
def update_deliberation_condition(request, id_decision):
    try:
        condition = get_object_or_404(Deliberation_annuelle_condition, id_decision=id_decision)
        
        data = json.loads(request.body)
        
        max_echecs = data.get('max_echecs_acceptable')
        seuil_profondeur = data.get('seuil_profondeur_echec')
        
        if max_echecs is None or seuil_profondeur is None:
            return JsonResponse({'error': 'Les champs max_echecs_acceptable et seuil_profondeur_echec sont requis.'}, status=400)
        
        try:
            condition.max_echecs_acceptable = int(max_echecs)
            condition.seuil_profondeur_echec = int(seuil_profondeur)
        except (ValueError, TypeError) as e:
            return JsonResponse({'error': 'Les valeurs doivent être des nombres valides.'}, status=400)
        
        if condition.max_echecs_acceptable < 0:
            return JsonResponse({'error': 'Le nombre maximum d\'échecs doit être positif.'}, status=400)
        if condition.seuil_profondeur_echec < 0:
            return JsonResponse({'error': 'Le seuil de profondeur d\'échec doit être positif.'}, status=400)
        
        condition.save()
        logger.info(f"Condition mise à jour avec succès pour id_decision={id_decision}")
        
        return JsonResponse({
            'message': 'Condition de délibération mise à jour avec succès.',
            'id_decision': condition.id_decision,
            'max_echecs_acceptable': condition.max_echecs_acceptable,
            'seuil_profondeur_echec': condition.seuil_profondeur_echec
        }, status=200)
    
    except json.JSONDecodeError as e:
        return JsonResponse({'error': 'Données JSON invalides.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erreur serveur : {str(e)}'}, status=500)