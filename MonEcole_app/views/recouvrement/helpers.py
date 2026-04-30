"""
Recouvrement helpers — tenant scoping & shared utilities.
"""
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _get_tenant(request):
    """
    Extract id_pays and id_etablissement from request/session.
    Returns (id_pays, id_etablissement) or (None, None).
    """
    id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')
    id_etablissement = (
        getattr(request, 'id_etablissement', None)
        or request.session.get('id_etablissement')
    )
    if id_pays is not None:
        try:
            id_pays = int(id_pays)
        except (ValueError, TypeError):
            id_pays = None
    if id_etablissement is not None:
        try:
            id_etablissement = int(id_etablissement)
        except (ValueError, TypeError):
            id_etablissement = None
    return id_pays, id_etablissement


def _require_tenant(request):
    """
    Returns (id_pays, id_etablissement) or raises a JsonResponse-ready error.
    """
    id_pays, id_etablissement = _get_tenant(request)
    if not id_pays or not id_etablissement:
        return None, None
    return id_pays, id_etablissement


def _tenant_filter(qs, id_pays, id_etablissement, pays_field='id_pays', etab_field='id_etablissement'):
    """Apply standard tenant filtering to a QuerySet."""
    return qs.filter(**{pays_field: id_pays, etab_field: id_etablissement})


def _tenant_error():
    """Return standard tenant-missing error."""
    return JsonResponse({
        'success': False,
        'error': 'Établissement non identifié. Reconnectez-vous.'
    }, status=403)
