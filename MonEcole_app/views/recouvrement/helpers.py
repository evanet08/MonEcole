"""
Recouvrement helpers — tenant scoping & HUB data access utilities.
Follows the same hub-and-spoke pattern as dashboard_views.py.
"""
import logging
from django.http import JsonResponse
from django.db import connections

# Hub models
from MonEcole_app.models.country_structure import (
    Pays, Etablissement, Cycle,
    EtablissementAnnee, EtablissementAnneeClasse,
)
from MonEcole_app.models.annee import Annee
from MonEcole_app.models.classe import Classe as ClasseHub
from MonEcole_app.models.campus import Campus

logger = logging.getLogger(__name__)


def _get_etab_id(request):
    """Resolve id_etablissement robustly: request attr → session → host SQL."""
    etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
    if etab_id:
        return etab_id
    try:
        host = request.get_host().split(':')[0].lower().strip()
        with connections['countryStructure'].cursor() as cursor:
            cursor.execute("SELECT id_etablissement FROM etablissements WHERE url = %s LIMIT 1", [host])
            row = cursor.fetchone()
            if row:
                etab_id = row[0]
                request.session['id_etablissement'] = etab_id
                return etab_id
    except Exception:
        pass
    return None


def _get_tenant(request):
    """
    Extract id_pays and id_etablissement from request/session.
    Returns (id_pays, id_etablissement) or (None, None).
    """
    id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')
    id_etablissement = _get_etab_id(request)
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


# ============================================================
#  HUB DATA ACCESS — Same pattern as _get_dashboard_context
# ============================================================

def get_hub_annees(id_pays):
    """Get all academic years from HUB for this pays."""
    return Annee.objects.filter(pays_id=id_pays).order_by('-annee')


def get_hub_annee_active(id_pays):
    """Get the currently open academic year from HUB."""
    a = Annee.objects.filter(pays_id=id_pays, isOpen=True).order_by('-annee').first()
    if not a:
        a = Annee.objects.filter(pays_id=id_pays).order_by('-annee').first()
    return a


def get_hub_etab(id_pays, id_etablissement):
    """Get the Etablissement object from HUB."""
    try:
        return Etablissement.objects.filter(
            id_etablissement=id_etablissement, pays_id=id_pays
        ).first()
    except Exception:
        return None


def get_hub_classes_for_annee(id_pays, id_etablissement, annee_id):
    """
    Get active classes for an establishment + year using HUB pattern:
    EtablissementAnnee → EtablissementAnneeClasse → ClasseHub lookup.

    Returns list of dicts with class info including campus from spoke.
    """
    try:
        # Step 1: Find the EtablissementAnnee record
        etab = get_hub_etab(id_pays, id_etablissement)
        if not etab:
            return []

        annee = Annee.objects.filter(id_annee=annee_id, pays_id=id_pays).first()
        if not annee:
            return []

        etab_annee = EtablissementAnnee.objects.filter(
            etablissement=etab, annee=annee, id_pays=id_pays
        ).first()
        if not etab_annee:
            return []

        # Step 2: Get configured classes (EtablissementAnneeClasse)
        eac_list = EtablissementAnneeClasse.objects.filter(
            etablissement_annee=etab_annee
        ).select_related('section')

        # Step 3: Resolve class business keys → ClasseHub objects
        eac_classe_bk_set = set(cc.classe_id for cc in eac_list)
        classes_by_bk = {}
        if eac_classe_bk_set:
            for cls in ClasseHub.objects.filter(
                id_classe__in=eac_classe_bk_set, id_pays=id_pays
            ).select_related('cycle'):
                classes_by_bk[cls.id_classe] = cls

        # Step 4: Get campus info from spoke
        campuses = {}
        try:
            for c in Campus.objects.filter(id_pays=id_pays, id_etablissement=id_etablissement):
                campuses[c.id_campus] = c.campus
        except Exception:
            pass

        # Step 5: Build result
        result = []
        for cc in eac_list:
            cls = classes_by_bk.get(cc.classe_id)
            if not cls:
                continue
            # Get campus from spoke (first available if not mapped)
            campus_name = list(campuses.values())[0] if campuses else '-'
            campus_id = list(campuses.keys())[0] if campuses else None

            result.append({
                'id_classe': cls.id_classe,
                'classe_nom': cls.classe,
                'campus_nom': campus_name,
                'id_campus': campus_id,
                'id_cycle': cls.cycle.id_cycle if cls.cycle else None,
                'cycle_nom': cls.cycle.cycle if cls.cycle else '-',
                'groupe': cc.groupe or '',
                'section_id': cc.section_id,
                'section_nom': cc.section.nom if cc.section else '',
            })

        return sorted(result, key=lambda x: (x.get('cycle_nom', ''), x.get('classe_nom', '')))
    except Exception as e:
        logger.error(f"get_hub_classes_for_annee error: {e}")
        return []


def get_hub_classe_name(id_classe, id_pays):
    """Resolve a class business key to its name from HUB."""
    try:
        cls = ClasseHub.objects.filter(id_classe=id_classe, id_pays=id_pays).first()
        return cls.classe if cls else f"Classe {id_classe}"
    except Exception:
        return f"Classe {id_classe}"
