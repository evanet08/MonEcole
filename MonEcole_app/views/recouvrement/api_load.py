"""
Recouvrement — API data-loading views.
Uses HUB for years/classes, SPOKE for recouvrement data.
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Sum, Q
from MonEcole_app.models.eleves.eleve import Eleve_inscription
from MonEcole_app.models.eleves.eleve import Eleve
from MonEcole_app.models.recouvrement import (
    VariableCategorie, Variable, VariablePrix, VariableDatebutoire,
    VariableDerogation, Eleve_reduction_prix, Paiement, PenaliteConfig,
    Banque, Compte, CategorieOperation, OperationCaisse,
)
from .helpers import (
    _require_tenant, _tenant_error, logger,
    get_hub_classes_for_annee, get_hub_classe_name,
)


@login_required(login_url='login')
def rec_get_banques(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    banques = Banque.objects.filter(id_pays=id_pays, id_etablissement=id_etab).values('id_banque', 'banque', 'sigle')
    return JsonResponse({'banques': list(banques)})


@login_required(login_url='login')
def rec_get_categories(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    cats = VariableCategorie.objects.filter(id_pays=id_pays, id_etablissement=id_etab).values('id_variable_categorie', 'nom')
    return JsonResponse({'categories': list(cats)})


@login_required(login_url='login')
def rec_get_comptes_banque(request, id_banque):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    comptes = Compte.objects.filter(id_banque_id=id_banque, id_pays=id_pays, id_etablissement=id_etab).values('id_compte', 'compte')
    return JsonResponse({'success': True, 'comptes': list(comptes)})


@login_required(login_url='login')
def rec_get_classes_actives(request):
    """Get active classes from HUB via EtablissementAnnee → EtablissementAnneeClasse → ClasseHub."""
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('annee_id')
    if not annee_id:
        return JsonResponse({'success': False, 'error': 'annee_id requis'}, status=400)
    classes = get_hub_classes_for_annee(id_pays, id_etab, annee_id)
    return JsonResponse({'success': True, 'classes': classes})


@login_required(login_url='login')
def rec_get_eleves_classe(request):
    """Élèves inscrits dans une classe (spoke data, class identified by hub business key)."""
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('id_annee')
    classe_id = request.GET.get('id_classe')
    if not all([annee_id, classe_id]):
        return JsonResponse({'success': False, 'error': 'Paramètres manquants'}, status=400)
    try:
        inscriptions = Eleve_inscription.objects.filter(
            id_annee_id=annee_id, id_classe_id=classe_id, status=True,
            id_pays=id_pays, id_etablissement=id_etab
        ).select_related('id_eleve').distinct()
        data = []
        seen = set()
        for ins in inscriptions:
            if ins.id_eleve_id not in seen:
                seen.add(ins.id_eleve_id)
                e = ins.id_eleve
                data.append({
                    'id_eleve': e.id_eleve,
                    'nom_complet': f"{e.nom} {e.prenom}",
                })
        data.sort(key=lambda x: x['nom_complet'])
        return JsonResponse({'success': True, 'data': data, 'count': len(data)})
    except Exception as e:
        logger.error(f"rec_get_eleves_classe: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required(login_url='login')
def rec_get_variables_restant(request):
    """Variables avec reste à payer pour un élève."""
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    eleve_id = request.GET.get('id_eleve')
    annee_id = request.GET.get('id_annee')
    classe_id = request.GET.get('id_classe')
    if not all([eleve_id, annee_id, classe_id]):
        return JsonResponse({'success': False, 'error': 'Paramètres manquants'}, status=400)
    try:
        variables_prix = VariablePrix.objects.filter(
            id_annee_id=annee_id, id_classe_id=classe_id,
            id_pays=id_pays, id_etablissement=id_etab
        ).select_related('id_variable', 'id_variable__id_variable_categorie')
        result = []
        for vp in variables_prix:
            variable = vp.id_variable
            montant_max = vp.prix
            reduction = Eleve_reduction_prix.objects.filter(
                id_eleve_id=eleve_id, id_variable_id=variable.id_variable,
                id_annee_id=annee_id, id_classe_id=classe_id,
                id_pays=id_pays, id_etablissement=id_etab
            ).first()
            if reduction:
                montant_max -= montant_max * reduction.pourcentage / 100
            total_paye = Paiement.objects.filter(
                id_eleve_id=eleve_id, id_variable_id=variable.id_variable,
                id_annee_id=annee_id,
                id_pays=id_pays, id_etablissement=id_etab
            ).aggregate(total=Sum('montant'))['total'] or 0
            reste = max(0, montant_max - total_paye)
            result.append({
                'id_variable': variable.id_variable,
                'nom_variable': variable.variable,
                'categorie': variable.id_variable_categorie.nom if variable.id_variable_categorie else '',
                'montant_total': montant_max,
                'total_deja_paye': total_paye,
                'reste_a_payer': reste,
                'reduction': reduction.pourcentage if reduction else 0,
            })
        return JsonResponse({'success': True, 'variables': result})
    except Exception as e:
        logger.error(f"rec_get_variables_restant: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required(login_url='login')
def rec_get_paiements_submitted(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('id_annee')
    classe_id = request.GET.get('id_classe')
    if not all([annee_id, classe_id]):
        return JsonResponse({'success': False, 'error': 'Paramètres manquants'}, status=400)
    paiements = Paiement.objects.filter(
        id_annee_id=annee_id, id_classe_id=classe_id,
        status=False, is_rejected=False,
        id_pays=id_pays, id_etablissement=id_etab
    ).select_related('id_eleve', 'id_variable').order_by('-date_paie')
    data = [{'id_paiement': p.id_paiement, 'variable': p.id_variable.variable,
             'montant': p.montant, 'bordereau': p.bordereau.url if p.bordereau else '',
             'status': p.status, 'eleve_nom': p.id_eleve.nom, 'eleve_prenom': p.id_eleve.prenom,
             'date_paie': p.date_paie.strftime('%d/%m/%Y') if p.date_paie else '',
             } for p in paiements]
    return JsonResponse({'success': True, 'data': data})


@login_required(login_url='login')
def rec_get_paiements_validated(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('id_annee')
    classe_id = request.GET.get('id_classe')
    if not all([annee_id, classe_id]):
        return JsonResponse({'success': False, 'error': 'Paramètres manquants'}, status=400)
    paiements = Paiement.objects.filter(
        id_annee_id=annee_id, id_classe_id=classe_id, status=True,
        id_pays=id_pays, id_etablissement=id_etab
    ).select_related('id_eleve', 'id_variable')
    data = [{'id_paiement': p.id_paiement, 'id_eleve': p.id_eleve.id_eleve,
             'variable': p.id_variable.variable, 'montant': p.montant,
             'bordereau': p.bordereau.url if p.bordereau else '',
             'status': p.status,
             'eleve_nom': p.id_eleve.nom, 'eleve_prenom': p.id_eleve.prenom,
             'is_rejected': p.is_rejected,
             'date_paie': p.date_paie.strftime('%d/%m/%Y') if p.date_paie else '',
             'date_saisie': p.date_saisie.strftime('%d/%m/%Y') if p.date_saisie else '',
             } for p in paiements.order_by('-date_paie')]
    return JsonResponse({'success': True, 'data': data})


@login_required(login_url='login')
def rec_get_paiements_eleve(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    eleve_id = request.GET.get('id_eleve')
    annee_id = request.GET.get('id_annee')
    classe_id = request.GET.get('id_classe')
    if not all([eleve_id, annee_id]):
        return JsonResponse({'success': False, 'error': 'Paramètres manquants'}, status=400)
    qs = Paiement.objects.filter(
        id_eleve_id=eleve_id, id_annee_id=annee_id, status=True,
        id_pays=id_pays, id_etablissement=id_etab
    ).select_related('id_variable')
    if classe_id:
        qs = qs.filter(id_classe_id=classe_id)
    data = [{'id_paiement': p.id_paiement, 'variable': p.id_variable.variable,
             'montant': p.montant,
             'date_paie': p.date_paie.strftime('%d/%m/%Y') if p.date_paie else '',
             'is_rejected': p.is_rejected,
             } for p in qs]
    return JsonResponse({'success': True, 'data': data})


@login_required(login_url='login')
def rec_get_existing_derogation_reduction(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('id_annee')
    classe_id = request.GET.get('id_classe')
    eleve_id = request.GET.get('id_eleve')
    if not all([annee_id, classe_id]):
        return JsonResponse({'success': False, 'error': 'Paramètres manquants'}, status=400)
    result = {}
    dates_butoire = VariableDatebutoire.objects.filter(
        id_annee_id=annee_id, id_classe_id=classe_id,
        id_pays=id_pays, id_etablissement=id_etab
    )
    for db in dates_butoire:
        var_id = str(db.id_variable_id)
        result.setdefault(var_id, {})['date_butoire'] = db.date_butoire.strftime('%Y-%m-%d') if db.date_butoire else None
    if eleve_id:
        for d in VariableDerogation.objects.filter(id_annee_id=annee_id, id_classe_id=classe_id, id_eleve_id=eleve_id, id_pays=id_pays, id_etablissement=id_etab):
            result.setdefault(str(d.id_variable_id), {})['date_derogation'] = d.date_derogation.strftime('%Y-%m-%d') if d.date_derogation else None
        for r in Eleve_reduction_prix.objects.filter(id_annee_id=annee_id, id_classe_id=classe_id, id_eleve_id=eleve_id, id_pays=id_pays, id_etablissement=id_etab):
            result.setdefault(str(r.id_variable_id), {})['pourcentage'] = float(r.pourcentage)
    return JsonResponse({'success': True, 'data': result})


@login_required(login_url='login')
def rec_get_penalites(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('id_annee')
    qs = PenaliteConfig.objects.filter(id_pays=id_pays, id_etablissement=id_etab)
    if annee_id:
        qs = qs.filter(id_annee_id=annee_id)
    data = [{'id': p.id_penalite_regle,
             'variable': p.id_variable.variable if p.id_variable else 'Toutes',
             'type': p.type_penalite, 'valeur': p.valeur, 'plafond': p.plafond,
             'actif': p.actif,
             'annee': str(p.id_annee.annee) if p.id_annee else '',
             } for p in qs.select_related('id_variable', 'id_annee')]
    return JsonResponse({'success': True, 'data': data})


@login_required(login_url='login')
def rec_get_categories_operations(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('annee')
    type_op = request.GET.get('type')
    qs = CategorieOperation.objects.filter(est_active=True, id_pays=id_pays, id_etablissement=id_etab)
    if annee_id: qs = qs.filter(id_annee_id=annee_id)
    if type_op: qs = qs.filter(type_operation=type_op)
    data = [{'id': c.id_categorie, 'nom': c.nom, 'type_operation': c.type_operation,
             'description': c.description or '',
             } for c in qs.order_by('-date_creation')]
    return JsonResponse({'success': True, 'categories': data})


@login_required(login_url='login')
def rec_get_operations_caisse(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('annee')
    type_op = request.GET.get('type')
    categorie_id = request.GET.get('categorie')
    qs = OperationCaisse.objects.filter(id_pays=id_pays, id_etablissement=id_etab)
    if annee_id: qs = qs.filter(id_annee_id=annee_id)
    if type_op: qs = qs.filter(categorie__type_operation=type_op)
    if categorie_id: qs = qs.filter(categorie_id=categorie_id)
    qs = qs.select_related('categorie').order_by('-date_operation')
    total_entrees = 0
    total_sorties = 0
    data = []
    for op in qs:
        m = float(op.montant)
        if op.categorie and op.categorie.type_operation == 'ENTREE':
            total_entrees += m
        else:
            total_sorties += m
        data.append({
            'id': op.id_operation,
            'date': op.date_operation.strftime('%d/%m/%Y'),
            'categorie': op.categorie.nom if op.categorie else '',
            'type_operation': op.categorie.type_operation if op.categorie else '',
            'montant': m,
            'montant_formatted': f"{m:,.0f}".replace(',', ' '),
            'source_beneficiaire': op.source_beneficiaire or '-',
            'mode_paiement': op.mode_paiement or '-',
            'description': op.description or '-',
            'reference': op.reference or '-',
        })
    return JsonResponse({
        'success': True, 'operations': data,
        'stats': {'total': len(data), 'entrees': total_entrees, 'sorties': total_sorties}
    })


@login_required(login_url='login')
def rec_get_date_butoires(request):
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('id_annee')
    classe_id = request.GET.get('id_classe')
    qs = VariableDatebutoire.objects.filter(id_pays=id_pays, id_etablissement=id_etab)
    if annee_id: qs = qs.filter(id_annee_id=annee_id)
    if classe_id: qs = qs.filter(id_classe_id=classe_id)
    data = [{'id': d.id_datebutoire,
             'variable': d.id_variable.variable if d.id_variable else '',
             'date_butoire': d.date_butoire.strftime('%Y-%m-%d') if d.date_butoire else '',
             } for d in qs.select_related('id_variable')]
    return JsonResponse({'success': True, 'data': data})


@login_required(login_url='login')
def rec_get_all_variables(request):
    """All variables for this establishment (for prix assignment)."""
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    qs = Variable.objects.filter(
        id_pays=id_pays, id_etablissement=id_etab
    ).select_related('id_variable_categorie').order_by('id_variable_categorie__nom', 'variable')
    data = [{
        'id_variable': v.id_variable,
        'variable': v.variable,
        'categorie': v.id_variable_categorie.nom if v.id_variable_categorie else '',
        'id_categorie': v.id_variable_categorie_id,
        'estObligatoire': v.estObligatoire,
    } for v in qs]
    return JsonResponse({'success': True, 'variables': data})


@login_required(login_url='login')
def rec_get_prix_classe(request):
    """
    Prix configuration for a year + class.
    Returns all variables with their current price (if set) for the given class.
    This is the core business logic: variables drive the pricing, class is context.
    """
    id_pays, id_etab = _require_tenant(request)
    if not id_pays: return _tenant_error()
    annee_id = request.GET.get('id_annee')
    classe_id = request.GET.get('id_classe')
    if not all([annee_id, classe_id]):
        return JsonResponse({'success': False, 'error': 'Paramètres manquants'}, status=400)

    # All variables for this establishment
    all_vars = Variable.objects.filter(
        id_pays=id_pays, id_etablissement=id_etab
    ).select_related('id_variable_categorie').order_by('id_variable_categorie__nom', 'variable')

    # Existing prix for this year + class
    existing_prix = {
        vp.id_variable_id: vp
        for vp in VariablePrix.objects.filter(
            id_annee_id=annee_id, id_classe_id=classe_id,
            id_pays=id_pays, id_etablissement=id_etab
        )
    }

    result = []
    for v in all_vars:
        vp = existing_prix.get(v.id_variable)
        result.append({
            'id_variable': v.id_variable,
            'variable': v.variable,
            'categorie': v.id_variable_categorie.nom if v.id_variable_categorie else '',
            'prix': vp.prix if vp else None,
            'id_prix': vp.id_prix if vp else None,
        })

    return JsonResponse({'success': True, 'variables': result})
