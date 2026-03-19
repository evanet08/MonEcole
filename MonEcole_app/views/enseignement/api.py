from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from MonEcole_app.models.models_import import Session,Campus, Eleve_note_type, Annee_periode,Annee_trimestre,Eleve_note,UserModule,Cours_par_classe,Attribution_cours
from django.core.mail import send_mail
import logging
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from MonEcole_app.views.tools.tenant_utils import deny_cross_tenant_access
logger = logging.getLogger(__name__)



from django.http import JsonResponse
from django.shortcuts import get_object_or_404

def get_campus_localisation(request):
    id_campus = request.GET.get('id_campus')
    if not id_campus:
        return JsonResponse({"error": "ID campus manquant"}, status=400)
    # Validation tenant
    denied = deny_cross_tenant_access(request, id_campus)
    if denied:
        return denied
    campus = get_object_or_404(Campus, id_campus=id_campus)
    return JsonResponse({"localisation": campus.localisation})



def get_trimestres_table(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')

    # Validation tenant
    if id_campus:
        denied = deny_cross_tenant_access(request, id_campus)
        if denied:
            return denied

    trimestres = Annee_trimestre.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe
    ).values(
        'id_trimestre',
        'trimestre__trimestre', 
        'debut',
        'fin',
        'isOpen'
    )

    return JsonResponse(list(trimestres), safe=False)

def get_periodes_table(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')
    id_trimestre= request.GET.get('id_trimestre_annee')

    # Validation tenant
    if id_campus:
        denied = deny_cross_tenant_access(request, id_campus)
        if denied:
            return denied
    
    periodes = Annee_periode.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe,
        id_trimestre_annee = id_trimestre
        
    ).values(
        'id_periode',
        'periode__periode', 
        'debut',
        'fin',
        'isOpen'
    )

    return JsonResponse(list(periodes), safe=False)

@require_GET
def get_trimestre_par_classe(request):
    try:
        id_annee = request.GET.get('id_annee')
        id_campus = request.GET.get('id_campus')
        id_cycle = request.GET.get('id_cycle')
        id_classe = request.GET.get('id_classe')

        if not all([id_annee, id_campus, id_cycle, id_classe]):
            return JsonResponse({'error': 'Tous les paramètres (id_annee, id_campus, id_cycle, id_classe) sont requis'}, status=400)

        # Validation tenant
        denied = deny_cross_tenant_access(request, id_campus)
        if denied:
            return denied

        trimestres = Annee_trimestre.objects.filter(
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle=id_cycle,
            id_classe=id_classe,
            
        ).select_related('repartition')

        data = [
            {
                'id_trimestre_annee': trimestre.id_trimestre,
                'trimestre': trimestre.repartition.nom, 
            }
            for trimestre in trimestres
        ]

        return JsonResponse({'data': data}, status=200)

    except ValidationError as e:
        return JsonResponse({'error': f'Erreur de validation : {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Erreur serveur : {str(e)}'}, status=500)
    
def envoyer_mail_simplifie(sujet, message, destinataires,html_message):
    try:
        result = send_mail(
            subject=sujet,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinataires,
            fail_silently=False,
            html_message=html_message
        )
        if result >= 1:  
            logger.info(f"Email envoyé avec succès à {destinataires}")
            return True
        else:
            return False
    except Exception as e:
        return False
    
    
@login_required
def get_cours_with_notes_by_classe(request):
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

        notes_subquery = Eleve_note.objects.filter(
            id_cours_classe=OuterRef('pk'),
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle,
            id_classe_active_id=id_classe
        )

        cours_qs = Cours_par_classe.objects.annotate(
            has_notes=Exists(notes_subquery)
        ).filter(
            has_notes=True,
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe
        ).select_related("id_cours")

        if not has_full_access:
            cours_autorises = Attribution_cours.objects.filter(
                id_personnel=personnel.id_personnel,
                id_annee_id=id_annee,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_classe_id=id_classe
            ).values_list("id_cours", flat=True)

            cours_qs = cours_qs.filter(id_cours_id__in=cours_autorises)

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
def get_note_type_by_cours_with_notes(request):
    id_annee = request.GET.get("id_annee")
    id_campus = request.GET.get("id_campus")
    id_cycle = request.GET.get("id_cycle")
    id_classe_active = request.GET.get("id_classe_active")
    id_cours_classe = request.GET.get("id_cours_classe")

    data = []

    if all([id_annee, id_campus, id_cycle, id_classe_active, id_cours_classe]):
        try:
            id_annee = int(id_annee)
            id_campus = int(id_campus)
            id_cycle = int(id_cycle)
            id_classe_active = int(id_classe_active)
            id_cours_classe = int(id_cours_classe)
        except (TypeError, ValueError):
            return JsonResponse({'data': data})

        notes_qs = Eleve_note.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle,
            id_classe_active_id=id_classe_active,
            id_cours_id=id_cours_classe
        )

        type_ids = notes_qs.values_list("id_type_note", flat=True).distinct()

        note_types = Eleve_note_type.objects.filter(id_type_note__in=type_ids)

        data = [
            {
                'id': note_type.id_type_note,
                'label': f'{note_type.type} - {note_type.sigle}'
            }
            for note_type in note_types
        ]

    return JsonResponse({'data': data})


@login_required
def get_trimestres_with_notes(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle_actif = request.GET.get('id_cycle')  
    id_classe_active = request.GET.get('id_classe')
    id_cours = request.GET.get('id_cours')
    id_type_note = request.GET.get('id_type_note')

    data = []

    if all([id_annee, id_campus, id_cycle_actif, id_classe_active, id_cours, id_type_note]):
        try:
            id_annee = int(id_annee)
            id_campus = int(id_campus)
            id_cycle_actif = int(id_cycle_actif)
            id_classe_active = int(id_classe_active)
            id_cours = int(id_cours)
            id_type_note = int(id_type_note)
        except (TypeError, ValueError):
            return JsonResponse({'data': data})

        trimestre_ids = Eleve_note.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle_actif,
            id_classe_active_id=id_classe_active,
            id_cours_id=id_cours,
            id_type_note_id=id_type_note
        ).values_list('id_trimestre', flat=True).distinct()

        trimestres = Annee_trimestre.objects.filter(
            id_trimestre__in=trimestre_ids,
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle_actif,
            id_classe_id=id_classe_active
        ).select_related('repartition')

        data = [
            {
                'id': trimestre.id_trimestre,
                'label': trimestre.repartition.nom
            }
            for trimestre in trimestres
        ]

    return JsonResponse({'data': data})


@login_required
def get_periodes_notes_par_classe(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')  
    id_classe = request.GET.get('id_classe')
    id_cours = request.GET.get('id_cours')
    id_type_note = request.GET.get('id_type_note')
    id_trimestre = request.GET.get('id_trimestre')

    periodes = Annee_periode.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe,
        id_trimestre_annee=id_trimestre,
        id_periode__in=Eleve_note.objects.filter(
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle_actif=id_cycle,
            id_classe_active=id_classe,
            id_cours_classe=id_cours,
            id_type_note=id_type_note,
            id_trimestre=id_trimestre
        ).values_list('id_periode', flat=True).distinct()
    )

    data = [
        {
            'id': periode.id_periode,
            'label': periode.repartition.nom
        }
        for periode in periodes
    ]
    
    return JsonResponse({'data': data})


@login_required
def get_notes_sessions_created(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe_active = request.GET.get('id_classe_active')
    id_cours = request.GET.get('id_cours')
    id_type_note = request.GET.get('id_type_note')
    id_trimestre = request.GET.get('id_trimestre')
    id_periode = request.GET.get('id_periode')

    sessions = Session.objects.filter(
        id_session__in=Eleve_note.objects.filter(
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle_actif=id_cycle,
            id_classe_active=id_classe_active,
            id_cours_classe=id_cours,
            id_type_note=id_type_note,
            id_trimestre=id_trimestre,
            id_periode=id_periode
        ).values_list('id_session', flat=True).distinct()
    )

    data = [
        {
            'id': sess.id_session,
            'label': sess.session
        }
        for sess in sessions
    ]
    return JsonResponse({'data': data})
