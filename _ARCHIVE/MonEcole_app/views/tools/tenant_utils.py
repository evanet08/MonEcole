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


def tenant_etablissement_filter(request, queryset, field='id_etablissement'):
    """
    Filtre un queryset directement par id_etablissement.
    Pour les modèles qui ont une colonne id_etablissement (Eleve, Evaluation,
    Personnel, Eleve_inscription, Eleve_note, Deliberation_*, etc.).
    
    C'est plus efficace que de passer par Campus car on évite un JOIN.
    
    Args:
        request: la requête HTTP
        queryset: le queryset à filtrer
        field: nom du champ id_etablissement (défaut: 'id_etablissement')
    
    Returns:
        queryset filtré
    """
    tenant_id = get_tenant_id(request)
    if tenant_id is None:
        return queryset

    filter_kwargs = {field: tenant_id}
    return queryset.filter(**filter_kwargs)


# ============================================================
# RÉPARTITIONS TEMPORELLES — Fonctions utilitaires
# Bridge entre l'ancien pattern spoke (id_campus, id_annee)
# et le nouveau système Hub (EtablissementAnnee → RepartitionConfigEtabAnnee)
# ============================================================

def get_etab_annee(id_campus, id_annee):
    """
    Résout (id_campus, id_annee) → EtablissementAnnee du Hub.
    
    Le spoke connaît id_campus (local) et id_annee (hub).
    Cette fonction fait le pont vers EtablissementAnnee
    qui est la clé pour accéder aux répartitions.
    
    Returns: EtablissementAnnee instance or None
    """
    from MonEcole_app.models.country_structure import EtablissementAnnee
    try:
        campus = Campus.objects.get(id_campus=id_campus)
        return EtablissementAnnee.objects.filter(
            etablissement_id=campus.id_etablissement,
            annee_id=id_annee
        ).first()
    except (Campus.DoesNotExist, ValueError, TypeError):
        return None


def get_etab_annee_from_request(request, id_annee):
    """
    Résout EtablissementAnnee en utilisant le tenant_id de la requête.
    Plus direct que get_etab_annee car utilise directement id_etablissement.
    
    Returns: EtablissementAnnee instance or None
    """
    from MonEcole_app.models.country_structure import EtablissementAnnee
    tenant_id = get_tenant_id(request)
    if tenant_id is None:
        # Mode base — cherche le premier campus actif
        campus = Campus.objects.filter(is_active=True).first()
        if not campus:
            return None
        tenant_id = campus.id_etablissement
    try:
        return EtablissementAnnee.objects.filter(
            etablissement_id=tenant_id,
            annee_id=id_annee
        ).first()
    except (ValueError, TypeError):
        return None


def get_trimestres_for_etab(id_campus, id_annee):
    """
    Retourne les trimestres/semestres (répartitions RACINE) pour un campus+année.
    
    Remplace: Annee_trimestre.objects.filter(id_annee=X, id_campus=Y, ...)
    Par:      Filtrage via EtablissementAnnee → repartition_configs_etab_annee (has_parent=False)
    
    Le spoke ne sait pas si c'est le calendrier national ou personnalisé.
    Il lit simplement ce qui est configuré pour son établissement.
    
    Returns: QuerySet de Annee_trimestre (= RepartitionConfigEtabAnnee avec has_parent=False)
    """
    from MonEcole_app.models.annee import Annee_trimestre
    ea = get_etab_annee(id_campus, id_annee)
    if not ea:
        return Annee_trimestre.objects.none()
    return Annee_trimestre.objects.filter(
        etablissement_annee=ea,
        has_parent=False
    ).select_related('repartition').order_by('repartition__ordre')


def get_periodes_for_trimestre(id_campus, id_annee, trimestre_id):
    """
    Retourne les périodes (répartitions ENFANTS) pour un trimestre donné.
    
    Remplace: Annee_periode.objects.filter(id_annee=X, id_campus=Y, id_trimestre_annee=Z, ...)
    Par:      Filtrage via EtablissementAnnee → repartition_configs_etab_annee (has_parent=True, parent_id=Z)
    
    Returns: QuerySet de Annee_periode (= RepartitionConfigEtabAnnee avec has_parent=True)
    """
    from MonEcole_app.models.annee import Annee_periode
    ea = get_etab_annee(id_campus, id_annee)
    if not ea:
        return Annee_periode.objects.none()
    return Annee_periode.objects.filter(
        etablissement_annee=ea,
        has_parent=True,
        id_trimestre_annee_id=trimestre_id
    ).select_related('repartition').order_by('repartition__ordre')


def get_all_periodes_for_etab(id_campus, id_annee):
    """
    Retourne TOUTES les périodes (enfants) pour un campus+année.
    Utile quand on n'a pas besoin de filtrer par trimestre parent.
    
    Returns: QuerySet de Annee_periode
    """
    from MonEcole_app.models.annee import Annee_periode
    ea = get_etab_annee(id_campus, id_annee)
    if not ea:
        return Annee_periode.objects.none()
    return Annee_periode.objects.filter(
        etablissement_annee=ea,
        has_parent=True
    ).select_related('repartition').order_by('repartition__ordre')

