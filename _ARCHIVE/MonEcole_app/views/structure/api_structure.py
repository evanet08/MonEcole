from ._initials import *
from django.views.decorators.csrf import csrf_exempt
from MonEcole_app.views.tools.tenant_utils import (
    get_tenant_campus_qs, get_tenant_campus_ids, validate_campus_access,
    deny_cross_tenant_access, tenant_campus_filter
)
from MonEcole_app.models.country_structure import (
    EtablissementAnnee, EtablissementAnneeClasse
)


def _get_etab_annee(id_campus, id_annee):
    """Helper: retrouve EtablissementAnnee à partir d'un campus local + année."""
    try:
        campus = Campus.objects.get(id_campus=id_campus)
        return EtablissementAnnee.objects.filter(
            etablissement_id=campus.id_etablissement,
            annee_id=id_annee
        ).first()
    except Campus.DoesNotExist:
        return None


# ===========================================API POUR LA FILTRAGE DES DONNEES 
# ////////////////////////USERS:
@login_required
def get_all_users(request):
    user_info = get_user_info(request)
    user_modules = user_info
    personnel_list = Personnel.objects.all()
    return render(request,'parametrage/index_parametrage.html',
                  {'personnel_acces': personnel_list,
                    "photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']})

# /////////////////////*****CAMPUS:
@login_required
def get_campus(request):
    campus_list = list(get_tenant_campus_qs(request).values('id_campus', 'campus'))
    return JsonResponse({'campus': campus_list})

@login_required
def get_active_campus(request):
    campus = get_tenant_campus_qs(request).filter(is_active=True).values('id_campus', 'campus')
    return JsonResponse({'campus': list(campus)})


# ////////////////////******ANNEE:
@login_required
def get_annees(request):
    annee_list = list(Annee.objects.all().values('id_annee', 'annee'))
    return JsonResponse({'annees': annee_list})

@login_required
def get_active_annees(request):
    annees = Annee.objects.all().values('id_annee', 'annee')
    return JsonResponse({'annees': list(annees)})


# //////////////////******CYCLES:

@login_required
def get_cycles_parFiltration(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]

    # Validation tenant : le campus doit appartenir à l'établissement
    if id_campus:
        denied = deny_cross_tenant_access(request, id_campus)
        if denied:
            return denied

    try:
        personnel = request.user.personnel
    except AttributeError:
        return JsonResponse([], safe=False) 

    user_modules = (
        UserModule.objects
        .filter(user=personnel, id_annee_id=id_annee, is_active=True)
        .values_list('module__module', flat=True)
    )

    has_full_access = any(module in full_access_modules for module in user_modules)

    # Récupérer les cycles via EtablissementAnneeClasse
    ea = _get_etab_annee(id_campus, id_annee)
    if not ea:
        return JsonResponse([], safe=False)

    if has_full_access:
        cycle_ids = EtablissementAnneeClasse.objects.filter(
            etablissement_annee=ea
        ).values_list('classe__cycle_id', flat=True).distinct()
    else:
        # Filtre par les classes dont le personnel est responsable
        resp_classe_ids = Classe_active_responsable.objects.filter(
            id_personnel=personnel,
            id_annee_id=id_annee,
            id_campus_id=id_campus
        ).values_list('id_classe_id', flat=True)
        cycle_ids = EtablissementAnneeClasse.objects.filter(
            etablissement_annee=ea,
            id__in=resp_classe_ids
        ).values_list('classe__cycle_id', flat=True).distinct()

    cycles = Classe_cycle_actif.objects.filter(
        id_cycle_actif__in=cycle_ids
    ).values('id_cycle_actif', 'cycle')

    results = [{'id_cycle_actif': c['id_cycle_actif'], 'cycle': c['cycle']} for c in cycles]
    return JsonResponse(results, safe=False)


@login_required
def get_active_cycles_actifs(request):
    """Liste tous les cycles (catalogue national)."""
    cycles = Classe_cycle_actif.objects.all().values('id_cycle_actif', 'cycle')
    return JsonResponse({'cycles_actifs': [
        {'id_cycle_actif': c['id_cycle_actif'], 'cycle': c['cycle']}
        for c in cycles
    ]})

@login_required
def get_cycle_for_edit(request, cycle_id):
    try:
        cycle = Classe_cycle.objects.get(id_cycle=cycle_id)
        # Vérifier si le cycle a des classes dans le Hub
        has_classes = Classe.objects.filter(cycle_id=cycle_id).exists()
        if has_classes:
            return JsonResponse({
                'error': 'Impossible de modifier le cycle car il a des classes liées.'
            }, status=400)

        data = {
            'cycle': cycle.cycle,
        }
        return JsonResponse(data)
    except Classe_cycle.DoesNotExist:
        return JsonResponse({'error': 'Cycle non trouvé'}, status=404)


@login_required
def get_classes_actives_by_cycle_annee(request):
    id_cycle_actif = request.GET.get('id_classe_cycle')
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    
    full_access_modules = ["Administration", "Inscription", "Archive", "Recouvrement"]
    if not id_cycle_actif or not id_annee or not id_campus or id_cycle_actif == 'undefined':
        return JsonResponse({'error': 'Paramètres manquants ou invalides'}, status=400)

    # Validation tenant
    denied = deny_cross_tenant_access(request, id_campus)
    if denied:
        return denied

    try:
        personnel = request.user.personnel
    except AttributeError:
        return JsonResponse([], safe=False) 

    try:
        ea = _get_etab_annee(id_campus, id_annee)
        if not ea:
            return JsonResponse([], safe=False)

        user_modules = (
            UserModule.objects
            .filter(user=personnel, id_annee_id=id_annee, is_active=True)
            .values_list('module__module', flat=True)
        )
        has_full_access = any(module in full_access_modules for module in user_modules)

        # Filtrer EtablissementAnneeClasse par cycle
        eac_qs = EtablissementAnneeClasse.objects.filter(
            etablissement_annee=ea,
            classe__cycle_id=id_cycle_actif
        )

        if not has_full_access:
            resp_classe_ids = Classe_active_responsable.objects.filter(
                id_personnel=personnel,
                id_annee_id=id_annee,
                id_campus_id=id_campus
            ).values_list('id_classe_id', flat=True)
            eac_qs = eac_qs.filter(id__in=resp_classe_ids)

        classes = list(eac_qs.select_related('classe').values(
            'id', 'classe__nom', 'groupe'
        ))

        result = [
            {
                'id_classe': c['id'],
                'classe': f"{c['classe__nom']} {c['groupe']}" if c['groupe'] else c['classe__nom']
            }
            for c in classes
        ]
        return JsonResponse(result, safe=False)

    except Exception:
        return JsonResponse({'error': 'Erreur interne du serveur'}, status=500)

 
@login_required
def get_active_cycles(request):
    cycles = Classe_cycle.objects.all().values('id_cycle', 'cycle')
    return JsonResponse({'cycles': list(cycles)})

@login_required
def get_active_cycles_by_campus_annee(request):
    id_campus = request.GET.get('id_campus')
    id_annee = request.GET.get('id_annee')
    if not (id_campus and id_annee):
        return JsonResponse({'cycles_actifs': []}, status=400)

    # Validation tenant
    denied = deny_cross_tenant_access(request, id_campus)
    if denied:
        return denied

    try:
        ea = _get_etab_annee(id_campus, id_annee)
        if not ea:
            return JsonResponse({'cycles_actifs': []})

        cycle_ids = EtablissementAnneeClasse.objects.filter(
            etablissement_annee=ea
        ).values_list('classe__cycle_id', flat=True).distinct()

        cycles = Classe_cycle_actif.objects.filter(
            id_cycle_actif__in=cycle_ids
        ).values('id_cycle_actif', 'cycle')

        return JsonResponse({'cycles_actifs': [
            {'id_cycle_actif': c['id_cycle_actif'], 'cycle': c['cycle']}
            for c in cycles
        ]})
    except Exception as e:
        return JsonResponse({'cycles_actifs': []}, status=500)

@login_required
def get_all_classes(request):
    try:
        classes = Classe.objects.all().values('id_classe', 'classe')
        return JsonResponse({'classes': list(classes)})
    except Exception as e:
        return JsonResponse({'classes': []}, status=500)

# ////////////////////**********CLASSES AND TRIMESTRES
@login_required
def get_class_for_edit(request, class_id):
    try:
        classe = Classe.objects.get(id_classe=class_id)
        # Vérifier si la classe est utilisée dans des EAC
        if EtablissementAnneeClasse.objects.filter(classe_id=class_id).exists():
            return JsonResponse({
                'error': 'Impossible de modifier la classe car elle est utilisée dans des classes actives.'
            }, status=400)

        data = {
            'classe_name': classe.classe
        }
        return JsonResponse(data)
    except Classe.DoesNotExist:
        return JsonResponse({'error': 'Classe non trouvée'}, status=404)

@login_required
def get_active_trimestres(request):
    trimestres = RepartitionInstance.objects.filter(is_active=True).values('id_instance', 'nom')
    return JsonResponse({'trimestres': [{'id_trimestre': t['id_instance'], 'trimestre': t['nom']} for t in trimestres]})

@login_required
def get_active_classes(request):
    classes = Classe.objects.all().values('id_classe', 'classe')
    return JsonResponse({'classes': list(classes)})

@login_required
def get_active_classes_by_campus_annee_cycle(request):
    id_campus = request.GET.get('id_campus')
    id_annee = request.GET.get('id_annee')
    id_cycle = request.GET.get('id_cycle')
    if not (id_campus and id_annee and id_cycle):
        return JsonResponse({'classes_actives': []}, status=400)

    # Validation tenant
    denied = deny_cross_tenant_access(request, id_campus)
    if denied:
        return denied

    try:
        ea = _get_etab_annee(id_campus, id_annee)
        if not ea:
            return JsonResponse({'classes_actives': []})

        eac_qs = EtablissementAnneeClasse.objects.filter(
            etablissement_annee=ea,
            classe__cycle_id=id_cycle
        ).select_related('classe').values('classe_id', 'classe__nom').distinct()

        return JsonResponse({'classes_actives': [
            {'classe_id': c['classe_id'], 'classe_id__classe': c['classe__nom']}
            for c in eac_qs
        ]})
    except Exception as e:
        return JsonResponse({'classes_actives': []}, status=500)

@login_required
def get_groupe_by_campus_annee_cycle_classe(request):
    id_campus = request.GET.get('id_campus')
    id_annee = request.GET.get('id_annee')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')
    if not (id_campus and id_annee and id_cycle and id_classe):
        return JsonResponse({'groupe':None}, status=400)

    # Validation tenant
    denied = deny_cross_tenant_access(request, id_campus)
    if denied:
        return denied

    try:
        ea = _get_etab_annee(id_campus, id_annee)
        if not ea:
            return JsonResponse({'groupe': None})

        eac = EtablissementAnneeClasse.objects.filter(
            etablissement_annee=ea,
            classe__cycle_id=id_cycle,
            classe_id=id_classe
        ).values('groupe').first()

        groupe = eac['groupe'] if eac and eac['groupe'] else None
        return JsonResponse({'groupe': groupe})
    except Exception as e:
        return JsonResponse({'groupe': None}, status=500)

@csrf_exempt 
def toggle_terminale_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            classe_id = data.get("id_classe_active")
            is_terminale = data.get("isTerminale", False)

            # EtablissementAnneeClasse n'a plus isTerminale — on renvoie OK
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request"})



from django.views.decorators.http import require_GET


@require_GET
def get_user_modules(request):
    id_annee = request.GET.get("id_annee")
    if not id_annee:
        return JsonResponse({"error": "id_annee manquant"}, status=400)

    user_modules = UserModule.objects.filter(id_annee_id=id_annee).select_related("user", "module")

    data = []
    for um in user_modules:
        data.append({
            "id_user_module": um.id_user_module,
            "nom_complet": f"{um.user.user.first_name} {um.user.user.last_name}",
            "module": um.module.module,
            "is_active": um.is_active,
        })
    return JsonResponse({"results": data})
