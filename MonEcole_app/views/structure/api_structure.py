from ._initials import *
from django.views.decorators.csrf import csrf_exempt
from MonEcole_app.views.tools.tenant_utils import (
    get_tenant_campus_qs, get_tenant_campus_ids, validate_campus_access,
    deny_cross_tenant_access, tenant_campus_filter
)

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
    annee_list = list(Annee.objects.all())
    return JsonResponse({'annees': annee_list})

@login_required
def get_active_annees(request):
    annees = Annee.objects.filter(is_active=True).values('id_annee', 'annee')
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
        .filter(user=personnel, id_annee=id_annee, is_active=True)
        .values_list('module__module', flat=True)
    )

    has_full_access = any(module in full_access_modules for module in user_modules)

    if has_full_access:
        cycles = (
            Classe_cycle_actif.objects
            .filter(id_annee=id_annee, id_campus=id_campus)
            .select_related('cycle_id')
            .values('id_cycle_actif', 'cycle_id__cycle')
            .distinct()
        )
    else:
        cycles = (
            Classe_cycle_actif.objects
            .filter(
                id_cycle_actif__in=Classe_active_responsable.objects.filter(
                    id_personnel=personnel,
                    id_annee=id_annee,
                    id_campus=id_campus
                ).values_list('id_cycle', flat=True)
            )
            .select_related('cycle_id')
            .values('id_cycle_actif', 'cycle_id__cycle')
            .distinct()
        )

    results = [{'id_cycle_actif': c['id_cycle_actif'], 'cycle': c['cycle_id__cycle']} for c in cycles]
    return JsonResponse(results, safe=False)


@login_required
def get_active_cycles_actifs(request):
    campus_ids = get_tenant_campus_ids(request)
    cycles_actifs = Classe_cycle_actif.objects.filter(
        is_active=True,
        id_campus__in=campus_ids
    ).values('id_cycle_actif', 'cycle_id__cycle')
    return JsonResponse({'cycles_actifs': list(cycles_actifs)})

@login_required
def get_cycle_for_edit(request, cycle_id):
    try:
        cycle = Classe_cycle.objects.get(id_cycle=cycle_id)
        dependencies = []
        if Classe_cycle_actif.objects.filter(cycle_id=cycle).exists():
            dependencies.append("cycles actifs")
        if Classe_active.objects.filter(cycle_id__cycle_id=cycle).exists():
            dependencies.append("classes actives")

        if dependencies:
            error_msg = f"Impossible de modifier le cycle car il est utilisé dans : {', '.join(dependencies)}."
            return JsonResponse({'error': error_msg}, status=400)

        data = {
            'cycle_name': cycle.cycle
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
        user_modules = (
            UserModule.objects
            .filter(user=personnel, id_annee=id_annee, is_active=True)
            .values_list('module__module', flat=True)
        )
        has_full_access = any(module in full_access_modules for module in user_modules)
        if has_full_access:
            queryset = Classe_active.objects.filter(
                cycle_id=id_cycle_actif,
                id_annee=id_annee,
                id_campus=id_campus
            )
        else:
            queryset = Classe_active.objects.filter(
                id_classe_active__in=Classe_active_responsable.objects.filter(
                    id_personnel=personnel,
                    id_cycle=id_cycle_actif,
                    id_annee=id_annee,
                    id_campus=id_campus
                ).values_list('id_classe', flat=True)
            )

        classes = list(queryset.values('id_classe_active', 'classe_id__classe', 'groupe'))

        result = [
            {
                'id_classe': c['id_classe_active'],
                'classe': f"{c['classe_id__classe']} {c['groupe']}" if c['groupe'] else c['classe_id__classe']
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
        cycles_actifs = Classe_cycle_actif.objects.filter(
            id_campus__id_campus=id_campus,
            id_annee__id_annee=id_annee,
            is_active=True
        ).values('id_cycle_actif', 'cycle_id__cycle')
        return JsonResponse({'cycles_actifs': list(cycles_actifs)})
    except Exception as e:
        return JsonResponse({'cycles_actifs': []}, status=500)

@login_required
def get_all_classes(request):
    try:
        classes = Classe.objects.filter(is_active=True).values('id_classe', 'classe')
        return JsonResponse({'classes': list(classes)})
    except Exception as e:
        return JsonResponse({'classes': []}, status=500)
# ////////////////////**********CLASSES AND TRIMESTRES
@login_required
def get_class_for_edit(request, class_id):
    try:
        classe = Classe.objects.get(id_classe=class_id)
        if Classe_active.objects.filter(classe_id=classe).exists():
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
    trimestres = Trimestre.objects.filter(is_active=True).values('id_trimestre', 'trimestre')
    return JsonResponse({'trimestres': list(trimestres)})

@login_required
def get_active_classes(request):
    classes = Classe.objects.filter(is_active=True).values('id_classe', 'classe')
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
        classes_actives = Classe_active.objects.filter(
            id_campus__id_campus=id_campus,
            id_annee__id_annee=id_annee,
            cycle_id__id_cycle_actif=id_cycle,
            is_active=True
        ).values('classe_id', 'classe_id__classe').distinct()
        return JsonResponse({'classes_actives': list(classes_actives)})
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
        classe_active = Classe_active.objects.filter(
            id_campus__id_campus=id_campus,
            id_annee__id_annee=id_annee,
            cycle_id__id_cycle_actif=id_cycle,
            classe_id__id_classe=id_classe,
            is_active=True
        ).values('groupe').first()
        groupe = classe_active['groupe'] if classe_active and classe_active['groupe'] else None
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

            classe = Classe_active.objects.get(id_classe_active=classe_id)
            # Validation tenant via le campus de la classe
            if not validate_campus_access(request, classe.id_campus_id):
                return JsonResponse({"status": "error", "message": "Accès interdit"}, status=403)
            classe.isTerminale = is_terminale
            classe.save()
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

    # Note: UserModule n'a pas de lien direct avec Campus/établissement.
    # Le filtrage tenant se fait indirectement via le personnel associé.
    # Pour l'instant, on conserve le comportement existant car les modules
    # sont des assignations de rôles, pas des données opérationnelles.
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
