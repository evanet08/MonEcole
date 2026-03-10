"""
Utilitaires d'isolation multi-tenant.

Toutes les requêtes sur les données opérationnelles (Campus, Elèves, Notes, etc.)
doivent passer par ces fonctions pour garantir l'isolation entre établissements.

Chaîne de confiance :
  TenantMiddleware → request.id_etablissement → Campus.id_etablissement → données filtrées
"""

import logging
from django.http import JsonResponse
from MonEcole_app.models.campus import Campus

logger = logging.getLogger(__name__)


def get_tenant_id(request):
    """
    Récupère l'id_etablissement du tenant courant.
    Retourne None si pas de contexte tenant (domaine de base).
    """
    return getattr(request, 'id_etablissement', None)


def get_tenant_campus_ids(request):
    """
    Retourne la liste des id_campus appartenant à l'établissement du tenant courant.
    Si pas de contexte tenant, retourne TOUS les campus (compatibilité mode base).
    """
    tenant_id = get_tenant_id(request)
    if tenant_id is None:
        # Pas de sous-domaine → mode base, retourne tout
        return list(Campus.objects.values_list('id_campus', flat=True))

    return list(
        Campus.objects.filter(id_etablissement=tenant_id)
        .values_list('id_campus', flat=True)
    )


def get_tenant_campus_qs(request):
    """
    Retourne un queryset de Campus filtré par le tenant courant.
    Utilise le manager par défaut (is_active=True) sauf si pas de tenant.
    """
    tenant_id = get_tenant_id(request)
    if tenant_id is None:
        return Campus.objects.all()

    return Campus.objects.filter(id_etablissement=tenant_id)


def validate_campus_access(request, campus_id):
    """
    Vérifie qu'un campus donné appartient bien au tenant courant.
    Retourne True si l'accès est autorisé, False sinon.
    """
    tenant_id = get_tenant_id(request)
    if tenant_id is None:
        # Pas de contexte tenant → accès libre
        return True

    try:
        campus_id = int(campus_id)
    except (TypeError, ValueError):
        return False

    return Campus.objects.filter(
        id_campus=campus_id,
        id_etablissement=tenant_id
    ).exists()


def tenant_campus_filter(request, queryset, campus_field='id_campus'):
    """
    Filtre un queryset générique pour n'inclure que les enregistrements
    liés à un campus du tenant courant.

    Args:
        request: la requête HTTP
        queryset: le queryset à filtrer
        campus_field: nom du champ FK vers Campus (défaut: 'id_campus')

    Returns:
        queryset filtré
    """
    tenant_id = get_tenant_id(request)
    if tenant_id is None:
        return queryset

    campus_ids = get_tenant_campus_ids(request)
    filter_kwargs = {f'{campus_field}__in': campus_ids}
    return queryset.filter(**filter_kwargs)


def tenant_campus_filter_by_id(request, queryset, campus_field='id_campus__id_campus'):
    """
    Variante de tenant_campus_filter pour les champs avec lookup FK.
    Exemple: pour filtrer Classe_active par id_campus__id_campus.
    """
    tenant_id = get_tenant_id(request)
    if tenant_id is None:
        return queryset

    campus_ids = get_tenant_campus_ids(request)
    filter_kwargs = {f'{campus_field}__in': campus_ids}
    return queryset.filter(**filter_kwargs)


def deny_cross_tenant_access(request, campus_id):
    """
    Retourne une JsonResponse 403 si le campus n'appartient pas au tenant.
    Retourne None si l'accès est autorisé.
    """
    if not validate_campus_access(request, campus_id):
        logger.warning(
            f"[TENANT] Accès refusé: user={request.user}, "
            f"campus={campus_id}, tenant={get_tenant_id(request)}"
        )
        return JsonResponse(
            {'error': "Accès interdit : ce campus ne fait pas partie de votre établissement."},
            status=403
        )
    return None
