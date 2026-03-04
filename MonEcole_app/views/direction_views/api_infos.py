

from django.http import JsonResponse
from MonEcole_app.models import Campus, Classe_cycle_actif, Classe_active
from django.contrib.auth.decorators import login_required

@login_required
def get_campus_options(request):
    id_annee = request.GET.get('id_annee')
    if not id_annee:
        return JsonResponse({'campus': []})
    campus = Campus.objects.filter(
        is_active=True,
        eleve_inscription__id_annee__id_annee=id_annee
    ).distinct().values('id_campus', 'campus')
    return JsonResponse({'campus': list(campus)})

@login_required
def get_cycle_options(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    if not (id_annee and id_campus):
        return JsonResponse({'cycles': []})

    cycles = Classe_cycle_actif.objects.filter(
        is_active=True,
        id_annee__id_annee=id_annee,
        id_campus__id_campus=id_campus
    ).distinct().values('id_cycle_actif', 'cycle_id__cycle')
    
    return JsonResponse({'cycles': list(cycles)})

@login_required
def get_classe_options(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')

    if not (id_annee and id_campus and id_cycle):
        return JsonResponse({'classes': []})

    classes = Classe_active.objects.filter(
        is_active=True,
        id_annee__id_annee=id_annee,
        id_campus__id_campus=id_campus,
        cycle_id__id_cycle_actif=id_cycle
    ).distinct().values(
        'id_classe_active',
        'classe_id__classe',
        'groupe' 
    )

    return JsonResponse({'classes': list(classes)})

