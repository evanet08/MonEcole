
from MonEcole_app.views.decorators.decorators import module_required
from MonEcole_app.views.home import get_user_info
from django.shortcuts import render,redirect
from django.urls import reverse
from MonEcole_app.models import (Eleve_inscription,
                                 Eleve,Annee, Campus, Classe_cycle_actif, Classe_active
                                 )
from django.http import JsonResponse
import logging
logger = logging.getLogger(__name__)
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from MonEcole_app.views.tools.tenant_utils import tenant_etablissement_filter




def get_inscription_stats(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')

    filters = {}
    if id_annee:
        filters['id_annee__id_annee'] = id_annee
    if id_campus:
        filters['id_campus__id_campus'] = id_campus
    if id_cycle:
        filters['id_classe_cycle__id_cycle_actif'] = id_cycle
    if id_classe:
        filters['id_classe__id_classe_active'] = id_classe

    base_qs = tenant_etablissement_filter(request, Eleve_inscription.objects.all())
    inscriptions = base_qs.filter(**filters).values('id_eleve_id').distinct()
    total_inscriptions = inscriptions.count()
    garcons = base_qs.filter(
        **filters, id_eleve__genre='M'
    ).values('id_eleve').distinct().count()
    filles = base_qs.filter(
        **filters, id_eleve__genre='F'
    ).values('id_eleve').distinct().count()

    garcons_percent = (garcons / total_inscriptions * 100) if total_inscriptions > 0 else 0
    filles_percent = (filles / total_inscriptions * 100) if total_inscriptions > 0 else 0

    previous_year = int(id_annee) - 1 if id_annee else None
    trend = 0
    if previous_year:
        prev_filters = {**filters, 'id_annee__debut': previous_year}
        prev_total = base_qs.filter(
            **prev_filters
        ).values('id_eleve').distinct().count()
        trend = ((total_inscriptions - prev_total) / prev_total * 100) if prev_total > 0 else 0

    if id_annee:
        current_inscriptions = base_qs.filter(
            id_annee__id_annee=id_annee,
            **{k: v for k, v in filters.items() if k != 'id_annee__id_annee'}
        ).values('id_eleve').distinct()

        annee_counts = base_qs.filter(
            id_eleve__in=current_inscriptions
        ).values('id_eleve').annotate(
            annee_count=Count('id_annee', distinct=True)
        )

        nouveaux = sum(1 for item in annee_counts if item['annee_count'] == 1)

        reinscriptions = sum(1 for item in annee_counts if item['annee_count'] > 1)
    else:
        nouveaux = 0
        reinscriptions = 0

    total_nouveaux_reinscriptions = nouveaux + reinscriptions
    nouveaux_percent = (nouveaux / total_nouveaux_reinscriptions * 100) if total_nouveaux_reinscriptions > 0 else 0
    reinscriptions_percent = (reinscriptions / total_nouveaux_reinscriptions * 100) if total_nouveaux_reinscriptions > 0 else 0

    cycle_count = 0
    cycle_info = "Sélectionnez un cycle"
    if id_cycle:
        cycle_count = base_qs.filter(
            **filters
        ).values('id_eleve').distinct().count()
        cycle_info = f"Cycle {Classe_cycle_actif.objects.get(id_cycle_actif=id_cycle).cycle_id}"

    return JsonResponse({
        'total_inscriptions': total_inscriptions,
        'garcons_count': garcons,
        'garcons_percent': f"{garcons_percent:.1f}%",
        'filles_count': filles,
        'filles_percent': f"{filles_percent:.1f}%",
        'cycle_count': cycle_count,
        'cycle_info': cycle_info,
        'trend': f"{trend:+.1f}% vs {previous_year}" if previous_year else "N/A",
        'nouveaux': nouveaux,
        'reinscriptions': reinscriptions,
        'nouveaux_percent': f"{nouveaux_percent:.1f}",
        'reinscriptions_percent': f"{reinscriptions_percent:.1f}"
    })

@login_required
def redirect_to_direction(request):
    user_info = get_user_info(request)
    user_modules = user_info
    annees = Annee.objects.all()
    return render(request, 'direction_page/index_direction.html', {
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name'],
        "annees": annees,
        "active_page": "direction",
    })