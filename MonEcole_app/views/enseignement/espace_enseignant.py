
from MonEcole_app.models.models_import import *
from django.contrib.auth.decorators import login_required
from MonEcole_app.forms.form_imports import *
from django.contrib import messages
from MonEcole_app.views.home.home import get_user_info
from django.http import HttpResponse
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.db.models import Exists, OuterRef,Sum
import os
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import logging
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from MonEcole_app.views.enseignement.api import envoyer_mail_simplifie
from django.core.mail import send_mail
from django.conf import settings
from decouple import config
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@login_required
def soumettre_evaluation_prevu(request):
    evaluation_list = Evaluation.objects.all()
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == 'POST':
        id_annee = request.POST.get('id_annee')
        id_campus = request.POST.get('id_campus')
        id_cycle_actif = request.POST.get('id_cycle_actif')
        id_classe_active = request.POST.get('id_classe_active')
        id_cours = request.POST.get('id_cours_classe')
        form = EvaluationForm(request.POST, request.FILES)
        if form.is_valid():
            fichier = request.FILES['contenu_evaluation']
            nom_original = fichier.name
            nom_sans_ext, ext = os.path.splitext(nom_original)
            evaluation = form.save(commit=False)

            type_note = evaluation.id_type_note.type.lower()
            is_travail_journalier = 'travail journalier' in type_note
            is_examen = 'examen' in type_note
            is_devoir = 'devoir' in type_note  

           
            if is_travail_journalier or is_examen:
                try:
                    cours_classe = Cours_par_classe.objects.get(
                        id_annee=id_annee,
                        id_campus=id_campus,
                        id_cycle=id_cycle_actif,
                        id_classe=id_classe_active,
                        id_cours_classe=id_cours
                    )

                    campus_code = cours_classe.id_campus.localisation if hasattr(cours_classe.id_campus, 'localisation') else str(cours_classe.id_campus)

                    if campus_code.upper() in ("RDC", "CONGO", "DRC"): 
                        if 'examen' in type_note:
                            ponderation_max = cours_classe.ponderation
                        else:
                            ponderation_max = cours_classe.TP 
                    else:
                        ponderation_max = cours_classe.TPE if is_examen else cours_classe.TP

                    if ponderation_max is None or ponderation_max <= 0:
                        type_eval = 'Examen' if is_examen else 'Travail Journalier'
                        messages.error(
                            request,
                            f"La pondération maximale pour {type_eval} du cours numero {id_cours} n'est pas définie ou est invalide "
                            f"pour le campus {campus_code}."
                        )
                        return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
                            'evaluation_form': form,
                            'form_type': 'form_evaluation',
                            'evaluation_list': evaluation_list,
                            'photo_profil': user_modules['photo_profil'],
                            'modules': user_modules['modules'],
                            'last_name': user_modules['last_name']
                        })
                    evaluations_existantes = Evaluation.objects.filter(
                        id_annee=id_annee,
                        id_campus=id_campus,
                        id_cycle_actif=id_cycle_actif,
                        id_classe_active=id_classe_active,
                        id_cours_classe=evaluation.id_cours_classe,
                        id_type_note=evaluation.id_type_note,
                        id_trimestre=evaluation.id_trimestre,
                        id_periode=evaluation.id_periode
                    )

                    if evaluations_existantes:
                        messages.error(request, "Désolé, l'évaluation pour ce meme type est déjà soumise !")
                        return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
                            'evaluation_form': form,
                            'form_type': 'form_evaluation',
                            'evaluation_list': evaluation_list,
                            'photo_profil': user_modules['photo_profil'],
                            'modules': user_modules['modules'],
                            'last_name': user_modules['last_name']
                        })

                    somme_ponderations = sum(eval.ponderer_eval for eval in evaluations_existantes)
                    ponderation_restante = ponderation_max - somme_ponderations

                    if evaluation.ponderer_eval > ponderation_restante:
                        messages.error(
                            request,
                            f"La pondération de l'évaluation ({evaluation.ponderer_eval}) dépasse "
                            f"la pondération restante ({ponderation_restante}) pour ce type."
                        )
                        return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
                            'evaluation_form': form,
                            'form_type': 'form_evaluation',
                            'evaluation_list': evaluation_list,
                            'photo_profil': user_modules['photo_profil'],
                            'modules': user_modules['modules'],
                            'last_name': user_modules['last_name']
                        })
                except Cours_par_classe.DoesNotExist:
                    messages.error(request, "Cours par classe non trouvé dans la base de données.")
                    return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
                        'evaluation_form': form,
                        'form_type': 'form_evaluation',
                        'evaluation_list': evaluation_list,
                        'photo_profil': user_modules['photo_profil'],
                        'modules': user_modules['modules'],
                        'last_name': user_modules['last_name']
                    })

            evaluation.contenu_evaluation = None
            evaluation.save()

            nom_fichier_final = f"{nom_sans_ext}_{evaluation.id_evaluation}{ext}"
            chemin_complet = os.path.join('evaluations', nom_fichier_final)

            default_storage.save(chemin_complet, ContentFile(fichier.read()))
            evaluation.contenu_evaluation = nom_fichier_final
            evaluation.save()
            if is_devoir:
                
                try:
                    logger.info("Début du traitement des devoirs.")
                    
                    cours_classe = Cours_par_classe.objects.get(id_cours_classe=id_cours)
                    nom_cours = cours_classe.id_cours.cours
                    
                    classe_active = Classe_active.objects.get(id_classe_active=id_classe_active)
                    nom_classe = classe_active.classe_id.classe
                    groupe = getattr(classe_active, 'groupe', '')
                    
                    institution = Institution.objects.first()
                    nom_institution = institution.nom_ecole
                    telephone = institution.telephone
                    
                    eleve_inscriptions = Eleve_inscription.objects.filter(
                        id_annee=id_annee,
                        id_campus=id_campus,
                        id_classe_cycle=id_cycle_actif,
                        id_classe=id_classe_active,
                        status=True
                    ).first()
                    logger.info(f"{eleve_inscriptions.count()} élèves trouvés pour l'envoi de devoirs.")
                    
                    emails_envoyes = 0
                    emails_echoues = 0

                    
                    messages.info(request, f"{emails_envoyes} email(s) envoyé(s) avec succès.")
                    logger.info(f"{emails_envoyes} email(s) envoyé(s).")

                except Exception as e:
                    logger.exception("Erreur générale lors de la préparation ou de l'envoi des emails.")
                    messages.warning(
                        request,
                        f"Évaluation enregistrée, mais erreur lors de la préparation des emails : {str(e)}"
                    )
            messages.success(request, 'Évaluation soumise avec succès !')
            return HttpResponse('<script>sessionStorage.clear(); window.location.href="/add_evaluation";</script>')
        else:
            messages.error(request, 'Erreur dans le formulaire. Veuillez vérifier les données.')
    else:
        form = EvaluationForm()
    return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
        'evaluation_form': form,
        'form_type': 'form_evaluation',
        'evaluation_list': evaluation_list,
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name']
    })

@login_required
def load_all_classes_by_attribution_cours_year(request):
    annee_id = request.GET.get('id_annee')
    data = []
    if annee_id:
        try:
            annee_id = int(annee_id)
        except (TypeError, ValueError):
            return JsonResponse({"data": data})

        try:
            personnel = request.user.personnel 
        except AttributeError:
            return JsonResponse({"data": data})  

        user_modules = UserModule.objects.filter(
            user=personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        inscriptions_subquery = Eleve_inscription.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee_id=annee_id,
            status=True
        )
        classes_query = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery)
        ).filter(
            id_annee_id=annee_id,
            has_students=True
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        )

        if not has_full_access:
            attribution_classes = Attribution_cours.objects.filter(
                id_personnel=personnel,
                id_annee_id=annee_id
            ).select_related('id_cycle__cycle_id', 'id_classe__classe_id', 'id_cours').values('id_classe')

            classes_query = classes_query.filter(
                id_classe_active__in=[ac['id_classe'] for ac in attribution_classes]
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

@login_required
def load_all_classes_by_attribution_cours_year_without_classes_deliberateAnnually(request):
    annee_id = request.GET.get('id_annee')
    data = []
    
    if annee_id:
        try:
            annee_id = int(annee_id)
        except (TypeError, ValueError):
            return JsonResponse({"data": data})

        try:
            personnel = request.user.personnel 
        except AttributeError:
            return JsonResponse({"data": data})  

        user_modules = UserModule.objects.filter(
            user=personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        deliberated_class_ids = Deliberation_annuelle_resultat.objects.filter(
            id_annee_id=annee_id
        ).values_list('id_classe_id', flat=True).distinct()

        inscriptions_subquery = Eleve_inscription.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee_id=annee_id,
            status=True
        )

        classes_query = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery)
        ).filter(
            id_annee_id=annee_id,
            has_students=True
        ).exclude(
            id_classe_active__in=deliberated_class_ids 
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        )

        if not has_full_access:
            attribution_classes = Attribution_cours.objects.filter(
                id_personnel=personnel,
                id_annee_id=annee_id
            ).values('id_classe')

            classes_query = classes_query.filter(
                id_classe_active__in=[ac['id_classe'] for ac in attribution_classes]
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



@login_required
def load_all_classes_by_tutilaire_classe_year(request):
    annee_id = request.GET.get('id_annee')
    data = []

    try:
        annee_id = int(annee_id)
    except (TypeError, ValueError):
        return JsonResponse({"data": data})

    try:
        personnel = request.user.personnel
    except AttributeError:
        return JsonResponse({"data": data})

    user_modules = UserModule.objects.filter(
        user=personnel,
        is_active=True
    ).values_list('module__module', flat=True)

    full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
    has_full_access = any(module in full_access_modules for module in user_modules)

    inscriptions_subquery = Eleve_inscription.objects.filter(
        id_classe=OuterRef('pk'),
        id_annee_id=annee_id,
        status=True
    )

    classes_query = Classe_active.objects.annotate(
        has_students=Exists(inscriptions_subquery)
    ).filter(
        id_annee_id=annee_id,
        has_students=True
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

    classes = classes_query.order_by('cycle_id__cycle_id__cycle')

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
def load_all_repechage_classes_byTutilaire_year(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if not annee_id:
        return JsonResponse({"data": data})

    try:
        annee_id = int(annee_id)
    except (TypeError, ValueError):
        return JsonResponse({"data": data})

    try:
        personnel = request.user.personnel
    except AttributeError as e:
        logger.error(f"Aucun personnel associé à l'utilisateur : {str(e)}")
        return JsonResponse({"data": data})

    user_modules = UserModule.objects.filter(
        user=personnel, is_active=True
    ).values_list('module__module', flat=True)

    full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
    has_full_access = any(module in full_access_modules for module in user_modules)

    classe_ids = Deliberation_repechage_resultat.objects.filter(
        id_annee_id=annee_id
    ).values_list('id_classe_id', flat=True).distinct()

    classes_query = Classe_active.objects.filter(
        id_annee_id=annee_id,
        id_classe_active__in=classe_ids
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
    classes = classes_query.order_by('cycle_id__cycle_id__cycle', 'classe_id__classe')

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

    return JsonResponse({"data": data})



@login_required
def load_all_classes_deliberates_by_year(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if annee_id:
        try:
            annee_id = int(annee_id)
        except (TypeError, ValueError):
            return JsonResponse({"data": data})

        try:
            personnel = request.user.personnel
        except AttributeError as e:
            logger.error(f"Erreur : Aucun personnel associé à l'utilisateur - {str(e)}")
            return JsonResponse({"data": data})

        user_modules = UserModule.objects.filter(
            user=personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)
        logger.info(f"Accès complet : {has_full_access}")

        note_classes = Eleve_note.objects.filter(
            id_annee_id=annee_id
        ).values_list('id_classe_active', flat=True).distinct()

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
            id_classe_active__in=note_classes
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        )

        if not has_full_access:
            attribution_classes = Attribution_cours.objects.filter(
                id_personnel=personnel,
                id_annee_id=annee_id
            ).values_list('id_classe', flat=True)

            classes_query = classes_query.filter(
                id_classe_active__in=attribution_classes
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


@login_required
def load_all_classes_by_year_without_classes_deliberated(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if annee_id:
        try:
            annee_id = int(annee_id)
        except (TypeError, ValueError):
            return JsonResponse({"data": data})

        try:
            personnel = request.user.personnel 
        except AttributeError:
            return JsonResponse({"data": data})  

        user_modules = UserModule.objects.filter(
            user=personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        inscriptions_subquery = Eleve_inscription.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee_id=annee_id,
            status=True
        )

        annuelle_exists = Deliberation_annuelle_resultat.objects.filter(
            id_annee_id=annee_id,
            id_classe=OuterRef('pk')
        )
        periodique_exists = Deliberation_periodique_resultat.objects.filter(
            id_annee_id=annee_id,
            id_classe=OuterRef('pk')
        )
        trimistrielle_exists = Deliberation_trimistrielle_resultat.objects.filter(
            id_annee_id=annee_id,
            id_classe=OuterRef('pk')
        )
        note_exists = Eleve_note.objects.filter(
            id_annee_id=annee_id,
            id_classe_active=OuterRef('pk')
        )

        classes_query = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery),
            has_annuelle=Exists(annuelle_exists),
            has_periodique=Exists(periodique_exists),
            has_trimistrielle=Exists(trimistrielle_exists),
            has_note=Exists(note_exists),
        ).filter(
            id_annee_id=annee_id,
            has_students=True,
            has_annuelle=False,
            has_periodique=False,
            has_trimistrielle=False,
            has_note=False
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        )

        if not has_full_access:
            attribution_classes = Attribution_cours.objects.filter(
                id_personnel=personnel,
                id_annee_id=annee_id
            ).values_list('id_classe', flat=True)

            classes_query = classes_query.filter(
                id_classe_active__in=attribution_classes
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


def test_sendgrid_email(request):
    try:
        logger.debug("Début de l'envoi de l'email...")
        send_mail(
            subject='Test Email avec SendGrid',
            message='Ceci est un email de test envoyé via SendGrid depuis ton application Django !',
            from_email=config('DEFAULT_FROM_EMAIL'),
            recipient_list=['alainfabricendayiragije98@gmail.com'],
            fail_silently=False,
        )
        logger.debug("Email envoyé avec succès.")
        return HttpResponse("Email envoyé avec succès via SendGrid !")
    except Exception as e:
        logger.error(f"Erreur détaillée : {str(e)}", exc_info=True)
        return HttpResponse(f"Erreur lors de l'envoi : {str(e)}")

@login_required
def load_all_repechage_classes_by_year(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if not annee_id:
        return JsonResponse({"data": data})

    try:
        annee_id = int(annee_id)
    except (TypeError, ValueError):
        return JsonResponse({"data": data})

    try:
        personnel = request.user.personnel
    except AttributeError as e:
        logger.error(f"Aucun personnel associé à l'utilisateur : {str(e)}")
        return JsonResponse({"data": data})

    user_modules = UserModule.objects.filter(
        user=personnel, is_active=True
    ).values_list('module__module', flat=True)

    full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
    has_full_access = any(module in full_access_modules for module in user_modules)

    classe_ids = Deliberation_repechage_resultat.objects.filter(
        id_annee_id=annee_id
    ).values_list('id_classe_id', flat=True).distinct()

    classes_query = Classe_active.objects.filter(
        id_annee_id=annee_id,
        id_classe_active__in=classe_ids
    ).select_related(
        'id_campus',
        'cycle_id__cycle_id',
        'classe_id'
    )

    if not has_full_access:
        attribution_classes = Attribution_cours.objects.filter(
            id_personnel=personnel,
            id_annee_id=annee_id
        ).values_list('id_classe', flat=True)

        classes_query = classes_query.filter(
            id_classe_active__in=attribution_classes
        )

    classes = classes_query.order_by('cycle_id__cycle_id__cycle', 'classe_id__classe')

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

    return JsonResponse({"data": data})



@login_required
def load_all_classes_with_notes_by_year(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if annee_id:
        try:
            annee_id = int(annee_id)
        except (TypeError, ValueError):
            return JsonResponse({"data": data})

        try:
            personnel = request.user.personnel
        except AttributeError:
            return JsonResponse({"data": data})

        user_modules = UserModule.objects.filter(
            user=personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        notes_subquery = Eleve_note.objects.filter(
            id_classe_active=OuterRef('pk'),
            id_annee_id=annee_id
        )

        classes_query = Classe_active.objects.annotate(
            has_notes=Exists(notes_subquery)
        ).filter(
            id_annee_id=annee_id,
            has_notes=True
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        )

        if not has_full_access:
            attribution_classes = Attribution_cours.objects.filter(
                id_personnel=personnel,
                id_annee_id=annee_id
            ).values('id_classe')

            classes_query = classes_query.filter(
                id_classe_active__in=[ac['id_classe'] for ac in attribution_classes]
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



@login_required
def get_notes_by_type_displaying(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form =EvaluationForm(request.POST or None)
    return render(request,'enseignement/zone_pedag/espace_enseignant.html',{'evaluation_form': form,
        'form_type': 'form_evaluation',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],

        'last_name': user_modules['last_name']})







# for eleve_inscription in eleve_inscriptions:
                    #     parent_email = eleve_inscription.id_eleve.email_parent
                    #     if parent_email:
                    #         try:
                    #             sujet = f"Nouveau devoir pour {eleve_inscription.id_eleve.nom} {eleve_inscription.id_eleve.prenom}"
                    #             message = (
                    #                 f"Bonjour,\n\n"
                    #                 f"Un nouveau devoir a été attribué à votre enfant {eleve_inscription.id_eleve.nom} {eleve_inscription.id_eleve.prenom} "
                    #                 f"dans le cours de {nom_cours}. Ce devoir est noté sur {evaluation.ponderer_eval} et doit être remis avant le {evaluation.date_soumission}.\n\n"
                    #                 f"Merci de suivre régulièrement les activités scolaires via notre plateforme.\n\n"
                    #                 f"{nom_institution}\nTéléphone : {institution.telephone}\nAdresse : {institution.emplacement}"
                    #             )

                    #             groupe_str = f"{groupe}" if groupe else ""
                    #             html_content = f"""<html>
                    #                 <body style="font-family: Arial, sans-serif; color: #333;">
                    #                     <h2 style="color: #db717e; text-align: center;">Bienvenue à {nom_institution} !</h2>
                    #                     <p><strong>Bonjour,</strong></p>
                    #                     <p>
                    #                     Nous sommes ravis de vous informer que notre élève et votre enfant 
                    #                     <strong>{eleve_inscription.id_eleve.nom} {eleve_inscription.id_eleve.prenom}</strong> 
                    #                     a reçu un nouveau devoir.
                    #                     </p>
                    #                     <p>
                    #                     Élève de la classe <strong>{nom_classe}</strong> {groupe_str}, il/elle a un devoir dans le cours de 
                    #                     <strong>{nom_cours}</strong> qui est noté sur <strong>{evaluation.ponderer_eval}</strong>. 
                    #                     Ce devoir doit impérativement être remis avant le <strong>{evaluation.date_soumission}</strong>.
                    #                     </p>
                    #                     <p>
                    #                     Vous pouvez dès maintenant suivre son travail via notre plateforme pour vous assurer de sa réussite.
                    #                     </p>
                    #                     <p>
                    #                     Merci d’avoir choisi <strong>{nom_institution}</strong>. Nous sommes honorés de vous accompagner 
                    #                     dans l’éducation de votre enfant.
                    #                     </p>
                    #                     <br>
                    #                     <p>Cordialement,</p>
                    #                     <p style="font-weight: bold;">{nom_institution}</p>
                    #                     <p>Téléphone : {institution.telephone}</p>
                    #                     <p>Adresse : {institution.emplacement}</p>
                    #                 </body>
                    #                 </html>""" 

                    #             destinataires = [parent_email]
                    #             logger.info(f"Envoi d'email à {parent_email} pour l'élève {eleve_inscription.id_eleve.nom} {eleve_inscription.id_eleve.prenom}")

                    #             if send_mail(
                    #                 subject=sujet,
                    #                 message=message,
                    #                 from_email=settings.DEFAULT_FROM_EMAIL,
                    #                 recipient_list=destinataires,
                    #                 fail_silently=False,
                    #                 html_message=html_content
                    #             ):
                    #                 emails_envoyes += 1
                    #                 logger.info(f"Email envoyé à {parent_email}")
                    #             else:
                    #                 emails_echoues += 1
                    #                 logger.warning(f"Échec d'envoi à {parent_email}")
                    #         except Exception as e:
                    #             emails_echoues += 1
                    #             logger.error(f"Erreur lors de l'envoi à {parent_email} : {str(e)}")

                    # if emails_echoues > 0:
                    #     messages.warning(
                    #         request,
                    #         f"Évaluation enregistrée, mais {emails_echoues} email(s) n'ont pas pu être envoyé(s). Vérifiez les logs pour plus de détails."
                    #     )
                    #     logger.warning(f"{emails_echoues} email(s) échoué(s).")
                       
                    # if emails_envoyes > 0:


















# @login_required
# def soumettre_evaluation_prevu(request):
#     evaluation_list = Evaluation.objects.all()
#     user_info = get_user_info(request)
#     user_modules = user_info
#     if request.method == 'POST':
#         id_annee = request.POST.get('id_annee')
#         id_campus = request.POST.get('id_campus')
#         id_cycle_actif = request.POST.get('id_cycle_actif')
#         id_classe_active = request.POST.get('id_classe_active')
#         id_cours = request.POST.get('id_cours_classe')
       
#         form = EvaluationForm(request.POST, request.FILES)
#         if form.is_valid():
#             fichier = request.FILES['contenu_evaluation']
#             nom_original = fichier.name
#             nom_sans_ext, ext = os.path.splitext(nom_original)
#             evaluation = form.save(commit=False)

#             # Récupérer le type d'évaluation et normaliser
#             type_note = evaluation.id_type_note.type.lower()
#             is_travail_journalier = 'travail journalier' in type_note
#             is_examen = 'examen' in type_note

#             # Vérifications spécifiques pour 'Travail Journalier' ou 'Examen'
#             if is_travail_journalier or is_examen:
#                 try:
#                     # Récupérer le cours par classe associé : a ameliorer 
#                     cours_classe = Cours_par_classe.objects.get(id_annee = id_annee,id_campus = id_campus,id_cycle = id_cycle_actif,id_classe = id_classe_active,id_cours_classe=id_cours)
#                     # Utiliser TPE pour Examen et TP pour Travail Journalier
#                     ponderation_max = cours_classe.TPE if is_examen else cours_classe.TP

#                     # Vérifier que la pondération maximale est valide
#                     if ponderation_max is None or ponderation_max <= 0:
#                         messages.error(
#                             request,
#                             f"La pondération maximale pour ce type d'évaluation ({'Examen' if is_examen else 'Travail Journalier'}) "
#                             "n'est pas définie ou est invalide."
#                         )
#                         return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
#                             'evaluation_form': form,
#                             'form_type': 'form_evaluation',
#                             'evaluation_list': evaluation_list,
#                             'photo_profil': user_modules['photo_profil'],
#                             'modules': user_modules['modules'],
#                             'last_name': user_modules['last_name']
#                         })

#                     # Récupérer les évaluations existantes du même type pour ce cours et classe
#                     evaluations_existantes = Evaluation.objects.filter(
#                         id_annee = id_annee,
#                         id_campus = id_campus,
#                         id_cycle_actif = id_cycle_actif,
#                         id_classe_active = id_classe_active,
#                         id_cours_classe=evaluation.id_cours_classe,
#                         id_type_note=evaluation.id_type_note,
#                         id_trimestre = evaluation.id_trimestre
#                     )

#                     # Calculer la somme des pondérations des évaluations existantes
#                     somme_ponderations = sum(eval.ponderer_eval for eval in evaluations_existantes)

#                     # Vérifier si la nouvelle pondération dépasse la limite
#                     ponderation_restante = ponderation_max - somme_ponderations
#                     if evaluation.ponderer_eval > ponderation_restante:
#                         messages.error(
#                             request,
#                             f"La pondération de l'évaluation ({evaluation.ponderer_eval}) dépasse "
#                             f"la pondération restante ({ponderation_restante}) pour ce type."
#                         )
#                         return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
#                             'evaluation_form': form,
#                             'form_type': 'form_evaluation',
#                             'evaluation_list': evaluation_list,
#                             'photo_profil': user_modules['photo_profil'],
#                             'modules': user_modules['modules'],
#                             'last_name': user_modules['last_name']
#                         })

#                 except Cours_par_classe.DoesNotExist:
#                     messages.error(request, "Cours par classe non trouvé dans la base de données.")
#                     return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
#                         'evaluation_form': form,
#                         'form_type': 'form_evaluation',
#                         'evaluation_list': evaluation_list,
#                         'photo_profil': user_modules['photo_profil'],
#                         'modules': user_modules['modules'],
#                         'last_name': user_modules['last_name']
#                     })

#             # Si toutes les vérifications passent, procéder à l'enregistrement
#             evaluation.contenu_evaluation = None
#             evaluation.save()

#             # Renommer le fichier avec l'ID
#             nom_fichier_final = f"{nom_sans_ext}_{evaluation.id_evaluation}{ext}"
#             chemin_complet = os.path.join('evaluations', nom_fichier_final)

#             # Enregistrer le fichier
#             default_storage.save(chemin_complet, ContentFile(fichier.read()))

#             # Sauvegarder le nom du fichier dans la base
#             evaluation.contenu_evaluation = nom_fichier_final
#             evaluation.save()

#             messages.success(request, 'Évaluation soumise avec succès !')
#             return HttpResponse('<script>sessionStorage.clear(); window.location.href="/add_evaluation";</script>')
#         else:
#             messages.error(request, 'Erreur dans le formulaire. Veuillez vérifier les données.')
#     else:
#         form = EvaluationForm()

#     return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
#         'evaluation_form': form,
#         'form_type': 'form_evaluation',
#         'evaluation_list': evaluation_list,
#         'photo_profil': user_modules['photo_profil'],
#         'modules': user_modules['modules'],
#         'last_name': user_modules['last_name']
#     })