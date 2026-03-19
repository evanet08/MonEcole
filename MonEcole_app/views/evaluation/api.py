from .__initials import *
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef, Count, Q,Subquery
from MonEcole_app.models.models_import import (Deliberation_trimistrielle_resultat,Eleve_note, Evaluation, Eleve, Eleve_note_type, Campus, Classe_cycle_actif, Classe_active, Cours_par_classe, Annee)
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from django.core.exceptions import ObjectDoesNotExist
from django.views.decorators.csrf import csrf_exempt
from MonEcole_app.models import Deliberation_annuelle_finalite
from django.views.decorators.http import require_POST
from MonEcole_app.views.tools.tenant_utils import (
    get_tenant_campus_ids, deny_cross_tenant_access, validate_campus_access
)
import logging
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────
# Listes de classes RDC par type de structure académique
# ─────────────────────────────────────────────────────────────────────────
CLASSES_PRIMAIRES_RDC = [
    '1ère Année', '1er Langue', '1er SC', '1er Eco',
    '1ère Primaire', '2ème Primaire', '3ème Primaire',
    '4ème Primaire', '5ème Primaire', '6ème Primaire',
]
CLASSES_EDUCATION_BASE_RDC = ['7ème A E.B', '8ème A E.B', '7ème', '8ème']
CLASSES_SUPERIEUR_RDC = [
    '4ème construction', '2ème Niveau Eléctricité Industrielle',
    '2sc MTP', '2ème LANGUE', '2ème Eco', '2ème BCT',
    '3ème MPT', '3ème BCT', '3ème ECO',
]

def get_max_deliberation_periods(id_campus, id_classe):
    """
    Retourne le nombre max de périodes de délibération pour une classe donnée :
      - 3 pour primaire/maternelle (trimestres)
      - 2 pour éducation de base et cycle supérieur (semestres)
      - 3 par défaut (BDI et autres localisations)
    """
    try:
        campus = Campus.objects.get(id_campus=id_campus)
        localisation = campus.localisation.upper()
    except Campus.DoesNotExist:
        return 3  # défaut

    if localisation != "RDC":
        return 3  # BDI = 3 trimestres

    classe_obj = Classe_active.objects.filter(id_classe_active=id_classe).select_related('classe_id').first()
    if not classe_obj or not classe_obj.classe_id:
        return 3

    classe_name = classe_obj.classe_id.classe.strip() if classe_obj.classe_id.classe else ""

    if classe_name in CLASSES_EDUCATION_BASE_RDC or classe_name in CLASSES_SUPERIEUR_RDC:
        return 2  # semestres
    return 3  # trimestres (primaire/maternelle)

# =============================================Loading section

@login_required
def load_all_classes_have_evaluations_by_year(request):
    annee_id = request.GET.get('id_annee')
    data = []
    error_message = None

    if annee_id:
        try:
            annee_id = int(annee_id)
        except (TypeError, ValueError):
            return JsonResponse({'data': data, 'error': 'Paramètre id_annee invalide'})

        try:
            personnel = request.user.personnel
        except AttributeError:
            return JsonResponse({'data': data, 'error': 'Aucun personnel associé'})

        user_modules = UserModule.objects.filter(
            user_id=personnel.id_personnel, is_active=True
        ).values_list('module__module', flat=True)

        full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
        has_full_access = any(module in full_access_modules for module in user_modules)

        classes_avec_evaluations = Evaluation.objects.filter(
            id_annee_id=annee_id
        ).values_list('id_classe_active', flat=True).distinct()

        if not classes_avec_evaluations:
            return JsonResponse({'data': data, 'error': 'Aucune classe avec évaluations trouvée'})

        classes_qs = Classe_active.objects.filter(
            id_annee_id=annee_id,
            id_classe_active__in=classes_avec_evaluations,
            id_campus__in=get_tenant_campus_ids(request)
        ).select_related('id_campus', 'cycle_id__cycle_id', 'classe_id')

        if not has_full_access:
            attribution_classes = Attribution_cours.objects.filter(
                id_personnel=personnel.id_personnel,
                id_annee_id=annee_id
            ).values_list('id_classe', flat=True).distinct()

            common_classes = set(classes_avec_evaluations).intersection(attribution_classes)

            if not common_classes:
                return JsonResponse({
                    'data': data,
                    'error': "Aucune classe attribuée à l'utilisateur avec des évaluations"
                })

            classes_qs = classes_qs.filter(
                id_classe_active__in=common_classes
            )

        for classe in classes_qs.order_by('cycle_id__cycle_id'):
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
    return JsonResponse({'data': data, 'error': error_message})

@login_required
def load_all_classes_with_pupils_registred_by_year(request):
    annee_id = request.GET.get('id_annee')
    data = []

    if annee_id:
        inscriptions_subquery = Eleve_inscription.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee_id=annee_id,
            status = True
        )
        classes = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery)
        ).filter(
            id_annee_id=annee_id,
            has_students=True,
            id_campus__in=get_tenant_campus_ids(request)
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
def displaying_course_by_classe_with_evaluation(request):
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
            print(f"Paramètres invalides: id_campus={id_campus}, id_cycle={id_cycle}, id_classe={id_classe}, id_annee={id_annee}")
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

        cours_avec_evaluations = Evaluation.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle,
            id_classe_active_id=id_classe
        ).values('id_cours_classe').distinct()

        cours_classe_ids = [item['id_cours_classe'] for item in cours_avec_evaluations]

        cours_qs = Cours_par_classe.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe,
            id_cours_classe__in=cours_classe_ids
        ).select_related("id_cours")

        if not has_full_access:
            attribution_cours = Attribution_cours.objects.filter(
                id_personnel=personnel.id_personnel,
                id_annee_id=id_annee,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_classe_id=id_classe
            ).values('id_cours')

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

    return JsonResponse({'cours_list': cours_list})

# =====================================getting informations's section:
@login_required
def get_note_type(request):
    types_exclus = ["Devoir", "travail journalier"]
    note_types = Eleve_note_type.objects.exclude(type__iexact='Devoir')
    data = [
        {
            'id': note_type.id_type_note,
            'label': f'{note_type.type}-{note_type.sigle}',
        }
        for note_type in note_types
    ]
    return JsonResponse({'data': data})

@login_required
def get_note_type_devoir(request):
    
    note_types = Eleve_note_type.objects.filter(type = 'Devoir')
    data = [
        {
            'id': note_type.id_type_note,
            'label': f'{note_type.type}-{note_type.sigle}',
        }
        for note_type in note_types
    ]
    return JsonResponse({'data': data})

@login_required
def get_note_type_pour_repechage(request):
    types_exclus = ["Devoir", "Travail Journalier"]
    exclusion_query = Q()
    for exclu in types_exclus:
        exclusion_query |= Q(type__iexact=exclu)
    note_types = Eleve_note_type.objects.exclude(exclusion_query)
    data = [
        {
            'id': note_type.id_type_note,
            'label': f'{note_type.type} - {note_type.sigle}',
        }
        for note_type in note_types
    ]

    return JsonResponse({'data': data})

@login_required
def get_all_trimestres(request):
    trimestres = RepartitionInstance.objects.filter(is_active=True)
    data = [
        {
            'id': t.id_instance,
            'label': t.nom
        }
        for t in trimestres
    ]
    return JsonResponse({'data': data})

@login_required
def get_all_periodes(request):
    periodes = RepartitionInstance.objects.filter(is_active=True)
    data = [
        {
            'id': p.id_instance,
            'label': p.nom
        }
        for p in periodes
    ]
    return JsonResponse({'data': data})

@login_required
def get_all_trimestres_par_classe(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe')
    trimestres = Annee_trimestre.objects.filter(id_annee = id_annee,
                                                id_campus = id_campus,
                                                id_cycle = id_cycle_actif,
                                                id_classe = id_classe_active,
                                                isOpen=True)
    data = [
        {
            'id': trimestre.id_trimestre,
            'label': trimestre.repartition.nom
        }
        for trimestre in trimestres
    ]
    return JsonResponse({'data': data})

@login_required
def get_all_trimestres_par_classe_avec_notes(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe')

    if not all([id_annee, id_campus, id_cycle_actif, id_classe_active]):
        return JsonResponse({'data': []})
    trimestres_ids = Eleve_note.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_actif_id=id_cycle_actif,
        id_classe_active_id=id_classe_active
    ).values_list('id_trimestre_id', flat=True).distinct()
    trimestres = Annee_trimestre.objects.filter(
        id_trimestre__in=trimestres_ids
    )

    data = [
        {
            'id': trimestre.id_trimestre,
            'label': trimestre.repartition.nom
        }
        for trimestre in trimestres
    ]

    return JsonResponse({'data': data})


@login_required
def get_all_periodes_par_classe(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe')
    id_trimestre = request.GET.get('id_trimestre')
    
    periodes = Annee_periode.objects.filter(id_annee = id_annee,id_campus = id_campus,id_cycle = id_cycle_actif,id_classe = id_classe_active,id_trimestre_annee = id_trimestre)
    data = [
        {
            'id': periode.id_periode,
            'label': periode.repartition.nom
        }
        for periode in periodes
    ]
    return JsonResponse({'data': data})

@login_required
def get_all_periodes_par_classe_avec_notes(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe')
    id_trimestre = request.GET.get('id_trimestre_annee')
   

    if not all([id_annee, id_campus, id_cycle_actif, id_classe_active, id_trimestre]):
        return JsonResponse({'data': []})
    
    periodes_definies = Annee_periode.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle_actif,
        id_classe=id_classe_active,
        id_trimestre_annee=id_trimestre
    )

    periodes_utilisees_ids = Eleve_note.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_actif_id=id_cycle_actif,
        id_classe_active_id=id_classe_active,
        id_trimestre_id=id_trimestre,
        id_periode_id__in=periodes_definies.values_list('id_periode', flat=True)
    ).values_list('id_periode_id', flat=True).distinct()

    periodes = periodes_definies.filter(id_periode__in=periodes_utilisees_ids)

    data = [
        {
            'id': periode.id_periode,
            'label': periode.repartition.nom
        }
        for periode in periodes
    ]

    return JsonResponse({'data': data})


@login_required
def get_last_trimestres_par_classe(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe')

    dernier_trimestre = Annee_trimestre.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle_actif,
        id_classe=id_classe_active,
        isOpen=False
    ).order_by('-id_trimestre').first()  

    if dernier_trimestre:
        data = [{
            'id': dernier_trimestre.id_trimestre,
            'label': dernier_trimestre.repartition.nom
        }]
    else:
        data = []

    return JsonResponse({'data': data})

@login_required
def get_all_periodes_par_classe(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe')
    id_trimestre = request.GET.get('id_trimestre')
    
    periodes = Annee_periode.objects.filter(id_annee = id_annee,id_campus = id_campus,id_cycle = id_cycle_actif,id_classe = id_classe_active,id_trimestre_annee = id_trimestre)
    data = [
        {
            'id': periode.id_periode,
            'label': periode.repartition.nom
        }
        for periode in periodes
    ]
    return JsonResponse({'data': data})

@login_required
def get_periodes_by_trimestre(request):
    id_trimestre = request.GET.get("id_trimestre")
    data = []

    if id_trimestre:
        periodes = RepartitionInstance.objects.filter(type_id=id_trimestre)
        data = [
            {
                "id": p.id_instance,
                "label": p.nom
            }
            for p in periodes
        ]

    return JsonResponse({'data': data})

@login_required
def get_all_sessions_created(request):
    sessions = Session.objects.all()
    data = [
        {
            'id': sess.id_session,
            'label': sess.session
        }
        for sess in sessions
    ]
    return JsonResponse({'data': data})

@login_required
def get_all_sessions_created_excludeOne(request):
    sessions = Session.objects.exclude(session__iexact="repechage")
    data = [
        {
            'id': sess.id_session,
            'label': sess.session
        }
        for sess in sessions
    ]
    return JsonResponse({'data': data})



@login_required
def get_note_type_par_cours_evaluer(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe_active')
    id_cours = request.GET.get('id_cours')

    if not all([id_annee, id_campus, id_cycle, id_classe_active, id_cours]):
        return JsonResponse({'data': []}, status=400)  

    evaluations = Evaluation.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle_actif=id_cycle,
        id_classe_active=id_classe_active,
        id_cours_classe=id_cours 
    ).values('id_type_note').distinct()

    note_type_ids = [eval['id_type_note'] for eval in evaluations]
    note_types = Eleve_note_type.objects.filter(id_type_note__in=note_type_ids)

    data = [
        {
            'id': note_type.id_type_note,
            'label': f'{note_type.type}-{note_type.sigle}',
        }
        for note_type in note_types
    ]
    return JsonResponse({'data': data})

@login_required
def get_trimestres_by_evaluationsCours_soumises(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe_active')
    id_cours = request.GET.get('id_cours')
    id_type_note = request.GET.get('id_type_note')
    if not all([id_annee, id_campus, id_cycle, id_classe_active, id_cours, id_type_note]):
        return JsonResponse({'data': []}, status=400)
    
    evaluations = Evaluation.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle_actif=id_cycle,
        id_classe_active=id_classe_active,
        id_cours_classe=id_cours,
        id_type_note=id_type_note 
    ).values('id_trimestre').distinct()
    trimestre_ids = [eval['id_trimestre'] for eval in evaluations]

    trimestres = Annee_trimestre.objects.filter(id_trimestre__in=trimestre_ids,isOpen=True)
    data = [
        {
            'id': trimestre.id_trimestre,
            'label': trimestre.repartition.nom
        }
        for trimestre in trimestres
    ]
    return JsonResponse({'data': data})

@login_required
def get_periodes_by_trimestre_coursEvaluation(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe_active')
    id_cours = request.GET.get('id_cours')
    id_type_note = request.GET.get('id_type_note')
    id_trimestre = request.GET.get("id_trimestre")
    
    if not all([id_annee, id_campus, id_cycle, id_classe_active, id_cours, id_type_note,id_trimestre]):
        return JsonResponse({'data': []}, status=400)
    
    evaluations = Evaluation.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle_actif=id_cycle,
        id_classe_active=id_classe_active,
        id_cours_classe=id_cours,
        id_type_note=id_type_note,
        id_trimestre =  id_trimestre
    ).values('id_periode').distinct()
    data = []
    periode_ids = [eval['id_periode'] for eval in evaluations]
    
    periodes = Annee_periode.objects.filter(id_periode__in=periode_ids)

    data = [
        {
            "id": p.id_periode,
            "label": p.repartition.nom
        }
        for p in periodes
    ]

    return JsonResponse({'data': data})

@login_required
def get_evalutions_by_select_specific(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe_active')
    id_cours = request.GET.get('id_cours')
    id_type = request.GET.get('id_type_note')
    id_trimestre = request.GET.get('id_trimestre')
    id_periode = request.GET.get('id_periode')
    id_session = request.GET.get('id_session')
   
    if not all([id_annee, id_campus, id_cycle, id_classe, id_trimestre, id_cours, id_type, id_periode, id_session]):
        return JsonResponse({'data': []}, status=400)
    
    existing_evaluation_ids = Eleve_note.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_actif_id=id_cycle,
        id_classe_active_id=id_classe,
        id_session_id=id_session,
        id_trimestre_id=id_trimestre,
        id_periode_id=id_periode,
        id_type_note_id=id_type,
        id_cours_id=id_cours
    ).values_list('id_evaluation_id', flat=True)

    evaluations = Evaluation.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle_actif=id_cycle,
        id_classe_active=id_classe,
        id_trimestre_id=id_trimestre,
        id_periode=id_periode,
        id_session=id_session,
        id_type_note=id_type,
        id_cours_classe=id_cours
    ).exclude(id_evaluation__in=existing_evaluation_ids)

    data = [
        {
            "id": e.id_evaluation,
            "label": e.title
        }
        for e in evaluations
    ]

    return JsonResponse({'data': data})

@login_required
def get_sessions_created_parCours_evaluation(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe_active')
    id_cours = request.GET.get('id_cours')
    id_type_note = request.GET.get('id_type_note')
    id_trimestre = request.GET.get("id_trimestre")
    id_periode = request.GET.get("id_periode")
    if not all([id_annee, id_campus, id_cycle, id_classe_active, id_cours, id_type_note,id_trimestre,id_periode]):
        return JsonResponse({'data': []}, status=400)
    
    evaluations = Evaluation.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle_actif=id_cycle,
        id_classe_active=id_classe_active,
        id_cours_classe=id_cours,
        id_type_note=id_type_note,
        id_trimestre =  id_trimestre,
        id_periode = id_periode
        
    ).values('id_session').distinct()
    session_ids = [eval['id_session'] for eval in evaluations]
    sessions = Session.objects.filter(id_session__in = session_ids)
    data = [
        {
            'id': sess.id_session,
            'label': sess.session
        }
        for sess in sessions
    ]
    return JsonResponse({'data': data})    

@login_required
def get_all_classes_deliberations_alliers(request):
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
            id_annee=annee_id,
            status=True
        )

        deliberation_count = Deliberation_trimistrielle_resultat.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee=annee_id
        ).values('id_classe').annotate(
            trimestre_count=Count('id_trimestre', distinct=True)
        ).values('trimestre_count')

        classes_query = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery),
            trimestre_count=Subquery(deliberation_count)
        ).filter(
            id_annee=annee_id,
            has_students=True,
            trimestre_count__gte=2  # 2 pour semestres (éducation de base/supérieur), 3 pour trimestres (primaire)
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        )

        if not has_full_access:
            attribution_classes = Attribution_cours.objects.filter(
                id_personnel=personnel,
                id_annee=annee_id
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
def get_all_classes_deliberations_parTitulaire(request):
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
            id_annee=annee_id,
            status=True
        )

        deliberation_count = Deliberation_trimistrielle_resultat.objects.filter(
            id_classe=OuterRef('pk'),
            id_annee=annee_id
        ).values('id_classe').annotate(
            trimestre_count=Count('id_trimestre', distinct=True)
        ).values('trimestre_count')

        classes_query = Classe_active.objects.annotate(
            has_students=Exists(inscriptions_subquery),
            trimestre_count=Subquery(deliberation_count)
        ).filter(
            id_annee=annee_id,
            has_students=True,
            trimestre_count__gte=2  # 2 pour semestres (éducation de base/supérieur), 3 pour trimestres (primaire)
        ).select_related(
            'id_campus',
            'cycle_id__cycle_id',
            'classe_id'
        )

        if not has_full_access:
            responsable_classes = Classe_active_responsable.objects.filter(
                id_personnel=personnel,
                id_annee=annee_id
            ).values_list('id_classe', flat=True)

            classes_query = classes_query.filter(
                id_classe_active__in=responsable_classes
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
def get_available_trimestres(request):
   
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')

    if not all([id_annee, id_campus, id_cycle, id_classe]):
        return JsonResponse({'error': 'Paramètres manquants'}, status=400)

    try:
        id_annee = int(id_annee)
        id_campus = int(id_campus)
        id_cycle = int(id_cycle)
        id_classe = int(id_classe)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Paramètres invalides'}, status=400)

    # Déterminer le nombre max de périodes selon le type de classe
    max_periods = get_max_deliberation_periods(id_campus, id_classe)

    # Récupérer les IDs valides (les N premiers par ordre d'id_trimestre)
    valid_trimestre_ids = list(
        Annee_trimestre.objects.filter(
            id_annee=id_annee, id_campus=id_campus, id_cycle=id_cycle, id_classe=id_classe
        ).order_by('id_trimestre').values_list('id_trimestre', flat=True).distinct()[:max_periods]
    )

    deliberated_trimestres = Deliberation_trimistrielle_resultat.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe
    ).values('id_trimestre_id').distinct()

    deliberated_ids = [d['id_trimestre_id'] for d in deliberated_trimestres]

    trimestres = Annee_trimestre.objects.filter(
        id_trimestre__in=valid_trimestre_ids,
        isOpen=True
    ).exclude(
        id_trimestre__in=deliberated_ids
    ).order_by('id_trimestre').values('id_trimestre', 'trimestre__trimestre').distinct()

    # Pour les classes à 2 semestres, renommer si nécessaire
    trimestres_list = []
    for i, t in enumerate(trimestres):
        name = t['trimestre__trimestre']
        if max_periods == 2 and name.startswith('Trimestre'):
            name = f"Semestre {i + 1}"
        trimestres_list.append({'id': t['id_trimestre'], 'name': name})

    return JsonResponse({'trimestres': trimestres_list}, status=200)


@login_required
def get_sessions_disponible(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')

    if not all([id_annee, id_campus, id_cycle, id_classe]):
        return JsonResponse({"error": "Paramètres manquants"}, status=400)

    sessions_utilisees = Deliberation_annuelle_resultat.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe
    ).values_list('id_session', flat=True)

    sessions_repechage = Deliberation_repechage_resultat.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe
    ).values_list('id_session', flat=True)

    sessions_exclues = set(sessions_utilisees).union(set(sessions_repechage))

    sessions_disponibles = Session.objects.exclude(
        id_session__in=sessions_exclues
    ).order_by('session')

    data = [
        {
            "id": session.id_session,
            "name": session.session
        }
        for session in sessions_disponibles
    ]

    return JsonResponse({"data": data})


@login_required
def get_sessions_reclammations(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')

    if not all([id_annee, id_campus, id_cycle, id_classe]):
        return JsonResponse({"error": "Paramètres manquants"}, status=400)

    sessions_utilisees = Evaluation.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle_actif=id_cycle,
        id_classe_active=id_classe
    ).values_list('id_session', flat=True)

    sessions_disponibles = Session.objects.filter(
        id_session__in=sessions_utilisees
    ).order_by('session')

    data = [
        {
            "id": session.id_session,
            "name": session.session
        }
        for session in sessions_disponibles
    ]

    return JsonResponse({"data": data})

@login_required
def get_sessions_non_usable_in_evaluations(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')

    if not all([id_annee, id_campus, id_cycle, id_classe]):
        return JsonResponse({"error": "Paramètres manquants"}, status=400)

    sessions_utilisees = Evaluation.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle_actif=id_cycle,
        id_classe_active=id_classe
    ).values_list('id_session', flat=True)
    sessions_disponibles = Session.objects.exclude(
        id_session__in=sessions_utilisees
    ).order_by('session')

    data = [
        {
            "id": session.id_session,
            "name": session.session
        }
        for session in sessions_disponibles
    ]
    return JsonResponse({"data": data})

@login_required
def get_evaluations(request):

    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')
    id_trimestre = request.GET.get('id_trimestre')
    id_periode = request.GET.get('id_periode')
    id_session = request.GET.get('id_session')
    id_type_note = request.GET.get('id_type_note')
    id_cours = request.GET.get('id_cours')
    id_eleve = request.GET.get('id_eleve')


    if not all([id_annee, id_campus, id_cycle, id_classe, id_trimestre, id_periode, id_session, id_eleve]):
        return JsonResponse({"error": "Paramètres manquants"}, status=400)

    try:
        evaluations = Evaluation.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle,
            id_classe_active_id=id_classe,
            id_trimestre_id=id_trimestre,
            id_periode_id=id_periode,
            id_session_id=id_session,
        )

        if id_type_note:
            evaluations = evaluations.filter(id_type_note_id=id_type_note)
        if id_cours:
            evaluations = evaluations.filter(id_cours_id=id_cours)


        note_subquery = Eleve_note.objects.filter(
            id_evaluation=OuterRef('pk'),
            id_eleve=id_eleve
        ).values('note')[:1]

        evaluations = evaluations.select_related(
            'id_cours_classe__id_cours', 'id_type_note'
        ).annotate(
            note=Subquery(note_subquery)
        ).values(
            'id_evaluation',
            'title',
            'note',
            'ponderer_eval',
            'id_cours_classe__id_cours__cours',
            'id_type_note__type',
            'id_type_note__sigle'
        )


        grouped_data = {}
        for eval in evaluations:
            cours = eval['id_cours_classe__id_cours__cours']
            type_note = eval['id_type_note__type']
            sigle = eval['id_type_note__sigle']

            if cours not in grouped_data:
                grouped_data[cours] = {}
            if type_note not in grouped_data[cours]:
                grouped_data[cours][type_note] = {
                    'sigle': sigle,
                    'evaluations': []
                }

            grouped_data[cours][type_note]['evaluations'].append({
                'id_evaluation': eval['id_evaluation'],
                'title': eval['title'],
                'ponderer_eval': eval['ponderer_eval'],
                'note': str(eval['note']) if eval['note'] is not None else ''
            })
        data = []
        for cours, types in grouped_data.items():
            for type_note, info in types.items():
                for eval in info['evaluations']:
                    data.append({
                        'cours': cours,
                        'type_evaluation': type_note,
                        'sigle': info['sigle'],
                        'nom_evaluation': eval['title'],
                        'note': eval['note'],
                        'ponderation': eval['ponderer_eval'],
                        'id_evaluation': eval['id_evaluation']
                    })
        return JsonResponse({"data": data})

    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "success": False
        }, status=500)

@login_required
def update_note_after_reclammations(request):
    if request.method != 'POST':
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    try:
        data = json.loads(request.body)
        id_evaluation = data.get('id_evaluation')
        title = data.get('title')
        note = data.get('note')
        id_eleve = data.get('id_eleve') 
        
        if not all([id_evaluation, title, id_eleve]):
            return JsonResponse({"error": "Paramètres manquants"}, status=400)

        with transaction.atomic():
            evaluation = Evaluation.objects.get(id_evaluation=id_evaluation)
            evaluation.title = title
            ponderation = evaluation.ponderer_eval
            if float(note) > ponderation:
                return JsonResponse({"error": f"Désolé, la note ne peut pas dépasser {ponderation}."}, status=400)
            evaluation.save()
            eleve_note, created = Eleve_note.objects.update_or_create(
                id_evaluation_id=id_evaluation,
                id_eleve_id=id_eleve,
                defaults={
                    'note': float(note) if note else None,
                    'id_annee': evaluation.id_annee,
                    'id_campus': evaluation.id_campus,
                    'id_cycle_actif': evaluation.id_cycle_actif,
                    'id_classe_active': evaluation.id_classe_active,
                    'id_session': evaluation.id_session,
                    'id_trimestre': evaluation.id_trimestre,
                    'id_periode': evaluation.id_periode,
                    'id_type_note': evaluation.id_type_note,
                    'id_cours_classe': evaluation.id_cours_classe
                }
            )
        return JsonResponse({"success": True})
    except Evaluation.DoesNotExist:
        return JsonResponse({"error": "Évaluation introuvable"}, status=404)
    except ValueError:
        return JsonResponse({"error": "Note invalide"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@login_required
def get_notes_by_selection(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle_actif')
    id_classe_active = request.GET.get('id_classe_active')
    id_trimestre = request.GET.get('id_trimestre')
    id_periode = request.GET.get('id_periode')
    id_session = request.GET.get('id_session')
    id_cours_classe = request.GET.get('id_cours_classe')
    id_type_note = request.GET.get('id_type_note')

    if not all([id_annee, id_campus, id_cycle_actif, id_classe_active, id_trimestre, id_periode, id_session, id_cours_classe, id_type_note]):
        return JsonResponse({'error': 'Paramètres manquants'}, status=400)

    try:
        notes = Eleve_note.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle_actif,
            id_classe_active_id=id_classe_active,
            id_trimestre_id=id_trimestre,
            id_periode_id=id_periode,
            id_session_id=id_session,
            id_cours_id=id_cours_classe,
            id_type_note_id=id_type_note
        ).select_related('id_eleve', 'id_evaluation', 'id_type_note')
        data = []
        for note in notes:
            data.append({
                'id_eleve': note.id_eleve_id,
                'nom': note.id_eleve.nom,
                'prenom': note.id_eleve.prenom,
                'note': str(note.note) if note.note is not None else None,
                'note_repechage': str(note.note_repechage) if note.note_repechage is not None else None,
                'title': note.id_evaluation.title,
                'ponderer_eval': str(note.id_evaluation.ponderer_eval),
                'id_type_note': note.id_type_note_id,
                'type': note.id_type_note.type, 
                'id_cours_classe': note.id_cours_id,
            })

        return JsonResponse({'data': data}, status=200)

    except ObjectDoesNotExist:
        return JsonResponse({'data': []}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
def generate_notes_pdf(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle_actif')
    id_classe_active = request.GET.get('id_classe_active')
    id_trimestre = request.GET.get('id_trimestre')
    id_periode = request.GET.get('id_periode')
    id_session = request.GET.get('id_session')
    id_cours_classe = request.GET.get('id_cours_classe')
    id_type_note = request.GET.get('id_type_note')
    if not all([id_annee, id_campus, id_cycle_actif, id_classe_active, id_trimestre, id_periode, id_session, id_cours_classe, id_type_note]):
        return HttpResponse("Paramètres manquants", status=400)

    try:
        institution = Institution.objects.first()
        annee = Annee.objects.get(id_annee=id_annee).annee
        campus = Campus.objects.get(id_campus=id_campus).campus
        cycle = Classe_cycle_actif.objects.get(id_annee=id_annee, id_campus=id_campus, id_cycle_actif=id_cycle_actif).cycle_id.cycle
        classe = Classe_active.objects.get(id_annee=id_annee, id_campus=id_campus, cycle_id=id_cycle_actif, id_classe_active=id_classe_active).classe_id.classe
        cours = Cours_par_classe.objects.get(id_annee=id_annee, id_campus=id_campus, id_cycle=id_cycle_actif, id_classe=id_classe_active, id_cours_classe=id_cours_classe).id_cours.cours
        type_note = Eleve_note_type.objects.get(id_type_note=id_type_note).sigle
        trimestre = Annee_trimestre.objects.get(id_annee=id_annee, id_campus=id_campus, id_cycle=id_cycle_actif, id_classe=id_classe_active,id_trimestre = id_trimestre)

        pupils = Eleve_inscription.objects.filter(
            id_annee=id_annee,
            id_campus=id_campus,
            id_classe_cycle=id_cycle_actif,
            id_classe=id_classe_active,
            status=1,
            id_trimestre=trimestre.id_trimestre
        )
        pupils_data = [{'id': p.id_eleve.id_eleve, 'nom': p.id_eleve.nom, 'prenom': p.id_eleve.prenom} for p in pupils]

        notes = Eleve_note.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle_actif,
            id_classe_active_id=id_classe_active,
            id_trimestre_id=id_trimestre,
            id_periode_id=id_periode,
            id_session_id=id_session,
            id_cours_id=id_cours_classe,
            id_type_note_id=id_type_note
        ).select_related('id_eleve', 'id_evaluation', 'id_type_note')

        classe_obj = Classe_active.objects.get(
            id_annee=id_annee,
            id_campus=id_campus,
            cycle_id=id_cycle_actif,
            id_classe_active=id_classe_active
        )

        notes_by_type = {}
        for note in notes:
            key = f"{note.id_type_note_id}_{note.id_cours_id}_{note.id_evaluation_id}"
            if key not in notes_by_type:
                notes_by_type[key] = {
                    'type': note.id_type_note.sigle or 'Inconnu',
                    'ponderer_eval': note.id_evaluation.ponderer_eval or 20,
                    'notes': [],
                }
            notes_by_type[key]['notes'].append({
                'id_eleve': note.id_eleve_id,
                'note': float(note.note) if note.note is not None else None,
                'note_repechage': float(note.note_repechage) if note.note_repechage is not None else None,
            })

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="fiche_des_points.pdf"'
        doc = SimpleDocTemplate(response, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(name='TitleStyle', fontSize=14, leading=16, alignment=0)
        center_style = ParagraphStyle(name='CenterStyle', fontSize=14, leading=16, alignment=1)

        elements.append(Paragraph(f"Ecole : <font color='black'><b>{institution}</b></font>", title_style))
        elements.append(Paragraph(f"Année scolaire : <font color='black'><b>{annee}</b></font>", title_style))
        elements.append(Paragraph(f"Campus : <font color='black'><b>{campus}</b></font>", title_style))
        elements.append(Paragraph(f"Cycle : <font color='black'><b>{cycle}</b></font>", title_style))
        classe_label = f"{classe}"
        if classe_obj.groupe:
            classe_label += f" - Groupe : {classe_obj.groupe}"
        elements.append(Paragraph(f"Classe : <font color='black'><b>{classe_label}</b></font>", title_style))
        elements.append(Paragraph(f"Cours : <font color='black'><b>{cours}</b></font>", title_style))
        elements.append(Paragraph(f"Type d'évaluation : <font color='black'><b>{type_note}</b></font>", title_style))
        elements.append(Paragraph(f"Trimestre : <font color='black'><b>{trimestre}</b></font>", title_style))
        # elements.append(Paragraph(f"Période : <font color='black'><b>{trimestre.id}</b></font>", title_style))
        
        ponderation_totale = sum(type_data['ponderer_eval'] for type_data in notes_by_type.values()) or 0
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(f"FICHE DES POINTS : <font color='black'><b>.../{ponderation_totale}</b></font>", center_style))
        elements.append(Spacer(1, 0.5*cm))

        elements.append(Table([[' ']], colWidths=[17*cm], rowHeights=[0.1*cm], style=[
            ('BACKGROUND', (0, 0), (-1, -1), colors.black),
        ]))

        max_eleve_per_page = 27
        type_columns = list(notes_by_type.values())

        table_header = ["N°", "Nom et prénom"]
        for type_data in type_columns:
            table_header.append(f"{type_data['type']}")
        table_header.append("Total")

        table_data = [table_header]
        for index, pupil in enumerate(pupils_data, start=1):
            row = [str(index), f"{pupil['nom']} {pupil['prenom']}"]
            total = 0
            for type_data in type_columns:
                note = next((n for n in type_data['notes'] if n['id_eleve'] == pupil['id']), None)
                if note:
                    note_value = note['note'] if note['note'] is not None else note['note_repechage']
                    row.append(f"{note_value:.2f}" if note_value is not None else "")
                    total += note_value or 0
                else:
                    row.append("")
            row.append(f"{total:.2f}")
            table_data.append(row)


        for i in range(0, len(pupils_data), max_eleve_per_page):
            page_data = [table_header] + table_data[i + 1:i + max_eleve_per_page + 1]
            table = Table(page_data, colWidths=[1.5*cm] + [5*cm] * len(type_columns) + [2.5*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(Spacer(1, 0.5*cm))
            elements.append(table)

        doc.build(elements)
        return response

    except ObjectDoesNotExist as e:
        return HttpResponse(f"Données introuvables : {str(e)}", status=404)
    except Exception as e:
        return HttpResponse(f"Erreur : {str(e)}", status=500)
    
    


@csrf_exempt  
@require_POST
def toggle_droit_avancement(request):
    try:
        data = json.loads(request.body)
        finalite_id = data.get("id")
        new_value = data.get("value", False)

        finalite = Deliberation_annuelle_finalite.objects.get(id_finalite=finalite_id)
        finalite.droit_avancement = new_value
        finalite.save()

        return JsonResponse({"success": True, "new_value": finalite.droit_avancement})
    except Deliberation_annuelle_finalite.DoesNotExist:
        return JsonResponse({"success": False, "error": "Finalité non trouvée"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
