

import logging
from django.shortcuts import get_object_or_404
from MonEcole_app.models import Classe_active,Classe_cycle_actif
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
import logging
from MonEcole_app.models import UserModule,Attribution_cours,Deliberation_annuelle_condition,Mention,Deliberation_annuelle_finalite
from django.views.decorators.http import require_GET
from django.db.models import F  
from django.db import transaction
import logging
from MonEcole_app.models import Deliberation_annuelle_resultat, Deliberation_repechage_resultat, Eleve_inscription, Annee_trimestre, Classe_active, Eleve
from MonEcole_app.views.evaluation import get_all_repechage_courses_on_fields,build_table_data_for_eleve
from django.db import IntegrityError
from django.core.cache import cache
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
logger = logging.getLogger(__name__)


@require_GET
@login_required
def list_ofclasses_next_pour_avancement(request):
    try:
        annee_id_1 = request.GET.get('id_annee_1') 
        annee_id_2 = request.GET.get('id_annee_2') 
        campus_id = request.GET.get('id_campus')
        cycle_id = request.GET.get('cycle_id')
        classe_id = request.GET.get('id_classe')

       
        if not (annee_id_1 and annee_id_2 and campus_id and classe_id):
            return JsonResponse({"data": []})

        try:
            annee_id_1 = int(annee_id_1)
            annee_id_2 = int(annee_id_2)
            campus_id = int(campus_id)
            classe_id = int(classe_id)
            cycle_id = int(cycle_id) if cycle_id else None
        except (TypeError, ValueError) as e:
            return JsonResponse({"data": []})

        try:
            if cycle_id:
                selected_class = Classe_active.objects.get(
                    id_classe_active=classe_id,
                    id_annee_id=annee_id_1,
                    id_campus_id=campus_id,
                    cycle_id_id=cycle_id
                )
            else:
                selected_class = Classe_active.objects.get(
                    id_classe_active=classe_id,
                    id_annee_id=annee_id_1,
                    id_campus_id=campus_id
                )
                cycle_id = selected_class.cycle_id.id_cycle_actif

            nom_classe = selected_class.classe_id.classe
            nom_campus = selected_class.id_campus.campus
            nom_cycle = selected_class.cycle_id.cycle_id.cycle
            is_terminale = selected_class.isTerminale
            ordre_classe = selected_class.ordre
            groupe_classe = selected_class.groupe or ""
        except Classe_active.DoesNotExist:
            return JsonResponse({"data": []})

        data = []

        try:
            matching_class = Classe_active.objects.get(
                id_annee_id=annee_id_2,
                id_campus__campus=nom_campus,
                cycle_id__cycle_id__cycle=nom_cycle,
                classe_id__classe=nom_classe,
                groupe=groupe_classe 
            )
            ordre_classe = matching_class.ordre
            cycle_id = matching_class.cycle_id.id_cycle_actif
            campus_id = matching_class.id_campus.id_campus
        except Classe_active.DoesNotExist:
            return JsonResponse({"data": []})

        if is_terminale:
            try:
                current_cycle = Classe_cycle_actif.objects.get(
                    id_cycle_actif=cycle_id,
                    id_annee_id=annee_id_1
                )
                next_cycle = Classe_cycle_actif.objects.filter(
                    id_annee_id=annee_id_2,
                    ordre__gt=current_cycle.ordre
                ).order_by('ordre').first()

                if next_cycle:
                    classes = Classe_active.objects.filter(
                        id_annee_id=annee_id_2,
                        id_campus_id=campus_id,
                        cycle_id_id=next_cycle.id_cycle_actif,
                        ordre=1,
                        is_active=True
                    ).select_related('classe_id').values(
                        'id_classe_active',
                        'groupe',
                        classe=F('classe_id__classe'),
                        campus_id=F('id_campus_id'), 
                        cycle_id_value=F('cycle_id_id'),  
                        classe_id_value=F('classe_id__id_classe')  
                    )
                    data = [
                        {
                            'id_classe': classe['id_classe_active'],
                            'classe_id__classe': f"{classe['classe']} - Groupe {classe['groupe']}" if classe['groupe'] else classe['classe'],
                            'id_campus': classe['campus_id'],
                            'cycle_id': classe['cycle_id_value'],
                            'id': classe['classe_id_value']
                        } for classe in classes
                    ]
            except Classe_cycle_actif.DoesNotExist:
                return JsonResponse({"data": []})
        else:
            next_ordre = Classe_active.objects.filter(
                id_annee_id=annee_id_2,
                id_campus_id=campus_id,
                cycle_id_id=cycle_id,
                ordre__gt=ordre_classe
            ).order_by('ordre').values('ordre').first()

            if next_ordre:
                next_ordre_value = next_ordre['ordre']
                classes = Classe_active.objects.filter(
                    id_annee_id=annee_id_2,
                    id_campus_id=campus_id,
                    cycle_id_id=cycle_id,
                    ordre=next_ordre_value,
                    is_active=True
                ).select_related('classe_id').values(
                    'id_classe_active',
                    'groupe',
                    classe=F('classe_id__classe'),
                    campus_id=F('id_campus_id'),  
                    cycle_id_value=F('cycle_id_id'), 
                    classe_id_value=F('classe_id__id_classe')  
                )
                data = [
                    {
                        'id_classe': classe['id_classe_active'],
                        'classe_id__classe': f"{classe['classe']}_{classe['groupe']}" if classe['groupe'] else classe['classe'],
                        'id_campus': classe['campus_id'],
                        'id_cycle': classe['cycle_id_value'],
                        'id': classe['classe_id_value']
                    } for classe in classes
                ]
            else:
                return JsonResponse({"data": []})

        return JsonResponse({"data": data})
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de la récupération des classes : {str(e)}"}, status=500)
    
def validate_parameters(request):
    """Valide les paramètres de la requête GET."""
    params = {
        'annee_id_1': request.GET.get('annee1'),
        'classe_id_1': request.GET.get('classeId1'),
        'campus_id_1': request.GET.get('campus1'),
        'cycle_id_1': request.GET.get('cycle1'),
        'annee_id_2': request.GET.get('annee2'),
        'classe_id_2': request.GET.get('classeId2'),
        'campus_id_2': request.GET.get('campus2'),
        'cycle_id_2': request.GET.get('cycle2')
    }
    
    logger.debug(f"Paramètres reçus : {params}")

    if not all(params.values()):
        logger.warning("Paramètres manquants")
        return None, JsonResponse({"error": "Paramètres manquants"}, status=400)

    try:
        return {key: int(value) for key, value in params.items()}, None
    except (TypeError, ValueError) as e:
        logger.error(f"Erreur de conversion des paramètres : {str(e)}")
        return None, JsonResponse({"error": f"Erreur de conversion des paramètres : {str(e)}"}, status=400)

def get_first_trimestre(annee_id, classe_id, campus_id, cycle_id):
    cache_key = f"trimestre_{annee_id}_{classe_id}_{campus_id}_{cycle_id}"
    trimestre = cache.get(cache_key)
    if trimestre:
        return trimestre, None

    trimestre = Annee_trimestre.objects.filter(
        id_annee_id=annee_id,
        id_classe_id=classe_id,
        id_campus_id=campus_id,
        id_cycle_id=cycle_id
    ).order_by('debut').first()
    if trimestre:
        cache.set(cache_key, trimestre, timeout=3600)  
    return trimestre, None if trimestre else JsonResponse({"error": "..."}, status=400)

def get_class_info(classe_id, annee_id, campus_id, cycle_id):
    """Récupère les informations d'une classe."""
    try:
        selected_class = Classe_active.objects.get(
            id_classe_active=classe_id,
            id_annee_id=annee_id,
            id_campus_id=campus_id,
            cycle_id_id=cycle_id
        )
        class_info = {
            'nom_classe': selected_class.classe_id.classe,
            'nom_campus': selected_class.id_campus.campus,
            'nom_cycle': selected_class.cycle_id.cycle_id.cycle,
            'groupe': selected_class.groupe or ""
        }
        logger.debug(f"Classe trouvée : {class_info}")
        return class_info, None
    except Classe_active.DoesNotExist:
        logger.error(f"Classe non trouvée pour id_classe={classe_id}, id_annee={annee_id}")
        return None, JsonResponse({"error": "Classe non trouvée pour l'année donnée"}, status=400)

def get_matching_class_for_redoublement(annee_id, nom_campus, nom_cycle, nom_classe, groupe):
    """Trouve la classe correspondante pour le redoublement dans l'année suivante."""
    try:
        matching_class = Classe_active.objects.get(
            id_annee_id=annee_id,
            id_campus__campus=nom_campus,
            cycle_id__cycle_id__cycle=nom_cycle,
            classe_id__classe=nom_classe,
            groupe=groupe
        )
        logger.debug(f"Classe correspondante pour redoublement trouvée : id_classe={matching_class.id_classe_active}")
        return matching_class, None
    except Classe_active.DoesNotExist:
        logger.info(f"Aucune classe correspondante pour redoublement trouvée pour id_annee={annee_id}")
        return None, None

def get_students(campus_id, cycle_id, classe_id, annee_id):
    """
    Récupère les groupes d'élèves inscrits, avec délibération annuelle et/ou repêchage.
    Retourne un tuple : (groupes d'élèves, erreur éventuelle).
    """
    try:
        trimestre = Annee_trimestre.objects.filter(
            id_annee_id=annee_id,
            id_campus_id=campus_id,
            id_cycle_id=cycle_id,
            id_classe_id=classe_id
        ).first()

        if not trimestre:
            return None, JsonResponse({"error": "Aucun trimestre disponible pour les paramètres donnés"}, status=400)
    except Exception as e:
        return None, JsonResponse({"error": f"Erreur lors de la récupération du trimestre : {str(e)}"}, status=500)

    try:
        inscriptions = Eleve_inscription.objects.filter(
            id_campus_id=campus_id,
            id_classe_cycle_id=cycle_id,
            id_classe_id=classe_id,
            id_annee_id=annee_id,
            id_trimestre_id=trimestre.id_trimestre,
            status=True
        ).select_related('id_eleve')

        if not inscriptions.exists():
            logger.info(f"Aucun élève inscrit trouvé pour id_annee={annee_id}, id_classe={classe_id}")
            return {
                "eleves_inscrits": [],
                "eleves_uniquement_annuelle": [],
                "eleves_dans_les_deux": []
            }, None

        eleves_ids = [inscription.id_eleve_id for inscription in inscriptions]

        deliberation_annuelle = Deliberation_annuelle_resultat.objects.filter(
            id_campus_id=campus_id,
            id_cycle_id=cycle_id,
            id_classe_id=classe_id,
            id_annee_id=annee_id,
            id_eleve_id__in=eleves_ids
        ).values_list('id_eleve_id', flat=True)

        deliberation_repechage = Deliberation_repechage_resultat.objects.filter(
            id_campus_id=campus_id,
            id_cycle_id=cycle_id,
            id_classe_id=classe_id,
            id_annee_id=annee_id,
            id_eleve_id__in=eleves_ids
        ).values_list('id_eleve_id', flat=True)

        set_annuelle = set(deliberation_annuelle)
        set_repechage = set(deliberation_repechage)

        uniquement_annuelle = set_annuelle - set_repechage
        dans_les_deux = set_annuelle & set_repechage

        eleves_uniquement_annuelle = Eleve.objects.filter(id_eleve__in=uniquement_annuelle).values(
            'id_eleve', 'nom', 'prenom',
            pourcentage=F('deliberation_annuelle_resultat__pourcentage')
        )
        eleves_dans_les_deux = Eleve.objects.filter(id_eleve__in=dans_les_deux).values(
            'id_eleve', 'nom', 'prenom',
            pourcentage=F('deliberation_annuelle_resultat__pourcentage')
        )

        return {
            "eleves_inscrits": inscriptions,
            "eleves_uniquement_annuelle": list(eleves_uniquement_annuelle),
            "eleves_dans_les_deux": list(eleves_dans_les_deux)
        }, None

    except Exception as e:
        return None, JsonResponse({"error": f"Erreur lors de la récupération des élèves : {str(e)}"}, status=500)

def determine_target_class(student, is_in_repechage, matching_class, classe_id_2, annee_id_1, campus_id_1, cycle_id_1, classe_id_1):
    """Détermine la classe cible pour l'inscription de l'élève en fonction des règles de délibération."""
    eleve_id = student['id_eleve']
    pourcentage = student.get('pourcentage', 0)

    try:
        deliberation_result = Deliberation_annuelle_resultat.objects.select_related(
            'id_mention', 'id_decision__id_finalite'
        ).get(
            id_eleve_id=eleve_id,
            id_annee_id=annee_id_1,
            id_campus_id=campus_id_1,
            id_cycle_id=cycle_id_1,
            id_classe_id=classe_id_1
        )
    except ObjectDoesNotExist:
        return None, None, 0

    try:
        mention = Mention.objects.get(
            Q(id_mention=deliberation_result.id_mention_id) &
            Q(min__lte=pourcentage) &
            Q(max__gte=pourcentage)
        )
        logger.debug(f"Mention trouvée : {mention.mention} ({mention.min}% - {mention.max}%)")
    except ObjectDoesNotExist:
        return None, None, 0

    try:
        deliberation_condition = Deliberation_annuelle_condition.objects.get(
            id_mention=mention,
            id_annee_id=annee_id_1,
            id_campus_id=campus_id_1,
            id_cycle_id=cycle_id_1,
            id_classe_id=classe_id_1
        )
    except ObjectDoesNotExist:
        return None, None, 0

    try:
        finalite = Deliberation_annuelle_finalite.objects.get(
            id_finalite=deliberation_condition.id_finalite_id
        )
        droit_avancement = finalite.droit_avancement
    except ObjectDoesNotExist:
        return None, None, 0

    has_repechage = Deliberation_repechage_resultat.objects.filter(
        id_eleve_id=eleve_id,
        id_annee_id=annee_id_1,
        id_campus_id=campus_id_1,
        id_cycle_id=cycle_id_1,
        id_classe_id=classe_id_1
    ).exists()

    valid_repechage_count = 0
    if is_in_repechage and has_repechage:
        table_data = build_table_data_for_eleve(
            id_eleve=eleve_id,
            id_annee=annee_id_1,
            id_campus=campus_id_1,
            id_cycle=cycle_id_1,
            id_classe=classe_id_1
        )
        repechage_courses = get_all_repechage_courses_on_fields(table_data)
        total_repechage_courses = len(repechage_courses)

        if total_repechage_courses == 1:
            return classe_id_2, False, valid_repechage_count 

        valid_repechage_count = Deliberation_repechage_resultat.objects.filter(
            id_eleve_id=eleve_id,
            id_annee_id=annee_id_1,
            id_classe_id=classe_id_1,
            id_campus_id=campus_id_1,
            id_cycle_id=cycle_id_1,
            valid_repechage=True,
            id_cours_classe__id_cours__cours__in=repechage_courses
        ).count()

        min_valid_courses = 1 if total_repechage_courses == 2 else 2
        if total_repechage_courses > 1 and valid_repechage_count >= min_valid_courses and droit_avancement:
            return classe_id_2, False, valid_repechage_count 
        else:
            if matching_class is None:
                return None, None, valid_repechage_count
            return matching_class.id_classe_active, True, valid_repechage_count  

    if droit_avancement:
        return classe_id_2, False, valid_repechage_count  
    else:
        if matching_class is None:
            return None, None, valid_repechage_count
        return matching_class.id_classe_active, True, valid_repechage_count 

def create_student_enrollment(eleve_id, trimestre, campus_id_2, annee_id_2, cycle_id_2, inscription_class_id, redoublement):
    if Eleve_inscription.objects.filter(
        id_eleve_id=eleve_id,
        id_trimestre_id=trimestre.id_trimestre,
        id_campus_id=campus_id_2,
        id_annee_id=annee_id_2,
        id_classe_cycle_id=cycle_id_2,
        id_classe_id=inscription_class_id
    ).exists():
        return {'status': 'already_enrolled', 'target_class_id': inscription_class_id}
    
    try:
        enrollment = Eleve_inscription.objects.create(
            id_eleve_id=eleve_id,
            id_trimestre_id=trimestre.id_trimestre,
            id_campus_id=campus_id_2,
            id_annee_id=annee_id_2,
            id_classe_cycle_id=cycle_id_2,
            id_classe_id=inscription_class_id,
            redoublement=redoublement,
            status=True,
        )
        return {
            'status': False if not redoublement else True,
            'target_class_id': inscription_class_id
        }
    except IntegrityError as e:
        return {'status': 'error', 'error': str(e)}

def process_student(student, annee_id_1, campus_id_1, cycle_id_1, classe_id_1,
                   annee_id_2, campus_id_2, cycle_id_2, classe_id_2,
                   matching_class, trimestre, is_in_repechage=False):
    """
    Traite un élève pour son inscription dans la classe suivante ou la même classe.
    """
    
    required_keys = ['id_eleve', 'nom', 'prenom', 'pourcentage']
    if not all(key in student for key in required_keys):
        missing_keys = [key for key in required_keys if key not in student]
        logger.error(f"Données manquantes pour l'élève {student.get('id_eleve', 'inconnu')} : {missing_keys}")
        return {
            'eleve_id': student.get('id_eleve', None),
            'nom': student.get('nom', 'Inconnu'),
            'prenom': student.get('prenom', 'Inconnu'),
            'status': 'error',
            'error': f"Données manquantes : {missing_keys}"
        }
    eleve_id = student['id_eleve']
    nom = student['nom']
    prenom = student['prenom']

    if Eleve_inscription.objects.filter(
        id_eleve_id=eleve_id,
        id_annee_id=annee_id_2,
        id_classe_id=classe_id_2,
        id_campus_id=campus_id_2,
        id_classe_cycle_id=cycle_id_2,
        id_trimestre_id=trimestre.id_trimestre
    ).exists():
        return {
            'eleve_id': eleve_id,
            'nom': nom,
            'prenom': prenom,
            'status': 'already_enrolled',
            'target_class_id': classe_id_2
        }

    inscription_class_id, redoublement, valid_repechage_count = determine_target_class(
        student, is_in_repechage, matching_class, classe_id_2,
        annee_id_1, campus_id_1, cycle_id_1, classe_id_1
    )

    if inscription_class_id is None:
        return {
            'eleve_id': eleve_id,
            'nom': nom,
            'prenom': prenom,
            'status': 'error',
            'error': 'Aucune classe correspondante pour le redoublement'
        }

    result = create_student_enrollment(
        eleve_id, trimestre, campus_id_2, annee_id_2, cycle_id_2,
        inscription_class_id, redoublement
    )

    result.update({
        'eleve_id': eleve_id,
        'nom': nom,
        'prenom': prenom,
        'valid_reerepechage_count': valid_repechage_count,
        'pourcentage': student.get('pourcentage', 0)
    })

    return result

@require_GET
@login_required
def get_students_for_next_or_same_class_year(request):
    """Vue principale pour traiter les élèves pour avancement ou redoublement."""
    
    try:
        params, error_response = validate_parameters(request)
        if error_response:
            return error_response
        
        annee_id_1, classe_id_1, campus_id_1, cycle_id_1 = (
            params['annee_id_1'], params['classe_id_1'], params['campus_id_1'], params['cycle_id_1']
        )
        annee_id_2, classe_id_2, campus_id_2, cycle_id_2 = (
            params['annee_id_2'], params['classe_id_2'], params['campus_id_2'], params['cycle_id_2']
        )
        

        trimestre, error_response = get_first_trimestre(annee_id_2, classe_id_2, campus_id_2, cycle_id_2)
        if error_response:
            return error_response

        class_info, error_response = get_class_info(classe_id_1, annee_id_1, campus_id_1, cycle_id_1)
        if error_response:
            return error_response

        matching_class, _ = get_matching_class_for_redoublement(
            annee_id_2, class_info['nom_campus'], class_info['nom_cycle'], class_info['nom_classe'], class_info['groupe']
        )

        student_groups, error_response = get_students(campus_id_1, cycle_id_1, classe_id_1, annee_id_1)
        if error_response:
            return error_response
        if not student_groups:
            return JsonResponse({"data": [], "message": "Aucun élève trouvé pour cette classe."})


        data = []
        with transaction.atomic():
            for student in student_groups.get("eleves_uniquement_annuelle", []):
                try:
                    result = process_student(
                        student,
                        annee_id_1, campus_id_1, cycle_id_1, classe_id_1,
                        annee_id_2, campus_id_2, cycle_id_2, classe_id_2,
                        matching_class, trimestre,
                        is_in_repechage=False
                    )
                    if result:
                        data.append(result)
                    else:
                        data.append({
                            'eleve_id': student.get('id_eleve', None),
                            'nom': student.get('nom', 'Inconnu'),
                            'prenom': student.get('prenom', 'Inconnu'),
                            'status': 'error',
                            'error': 'Aucun résultat retourné par process_student'
                        })
                except Exception as e:
                    data.append({
                        'eleve_id': student.get('id_eleve', None),
                        'nom': student.get('nom', 'Inconnu'),
                        'prenom': student.get('prenom', 'Inconnu'),
                        'status': 'error',
                        'error': f"Erreur lors du traitement : {str(e)}"
                    })

            for student in student_groups.get("eleves_dans_les_deux", []):
                
                try:
                    result = process_student(
                        student,
                        annee_id_1, campus_id_1, cycle_id_1, classe_id_1,
                        annee_id_2, campus_id_2, cycle_id_2, classe_id_2,
                        matching_class, trimestre,
                        is_in_repechage=True
                    )
                    if result:
                        data.append(result)
                    else:
                        data.append({
                            'eleve_id': student.get('id_eleve', None),
                            'nom': student.get('nom', 'Inconnu'),
                            'prenom': student.get('prenom', 'Inconnu'),
                            'status': 'error',
                            'error': 'Aucun résultat retourné par process_student'
                        })
                except Exception as e:
                    data.append({
                        'eleve_id': student.get('id_eleve', None),
                        'nom': student.get('nom', 'Inconnu'),
                        'prenom': student.get('prenom', 'Inconnu'),
                        'status': 'error',
                        'error': f"Erreur lors du traitement : {str(e)}"
                    })

        return JsonResponse({
            "data": data,
            "message": f"{len(data)} élève(s) traité(s) avec succès pour avancement/redoublement."
        })

    except Exception as e:
        return JsonResponse({
            "error": f"Erreur lors du traitement : {str(e)}",
            "data": []
        }, status=500)