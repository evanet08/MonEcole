"""
Service central de vérification des conditions d'activation progressive.

RÈGLES FONDAMENTALES :
1. Un établissement est VALIDE uniquement s'il est géolocalisé ET possède un
   ref_administrative COMPLET correspondant exactement à la profondeur nLevelsAdministratifs.
2. Tant que la géolocalisation est incomplète → seuls Dashboard et MonEcole sont actifs.
3. Dès que la géolocalisation est complète → Configuration devient accessible.
4. Dans Configuration, seul l'onglet "Campus / Emplacement" est actif tant qu'aucun campus n'existe.
5. TOUT est filtré par id_pays + id_etablissement — aucune donnée hors scope.
"""
import logging
from django.db import connections

logger = logging.getLogger(__name__)


def check_geolocation_complete(etab_id, id_pays):
    """
    Vérifie que l'établissement est géolocalisé ET possède un ref_administrative complet.

    Conditions :
    - latitude ET longitude non NULL et non 0
    - ref_administrative non NULL et non vide
    - nombre de segments dans ref_administrative == nLevelsAdministratifs du pays

    Retourne (is_complete: bool, details: dict)
    """
    details = {
        'has_coordinates': False,
        'has_ref_admin': False,
        'ref_admin_depth': 0,
        'required_depth': 0,
        'latitude': None,
        'longitude': None,
        'ref_administrative': '',
    }

    if not etab_id or not id_pays:
        return False, details

    try:
        with connections['countryStructure'].cursor() as cur:
            # Récupérer les données de l'établissement ET la profondeur du pays
            cur.execute("""
                SELECT e.latitude, e.longitude, e.ref_administrative,
                       p.nLevelsAdministratifs
                FROM etablissements e
                JOIN pays p ON p.id_pays = e.pays_id
                WHERE e.id_etablissement = %s AND e.pays_id = %s
                LIMIT 1
            """, [etab_id, id_pays])
            row = cur.fetchone()

            if not row:
                return False, details

            lat, lng, ref_admin, n_levels = row

            # Vérifier les coordonnées GPS
            details['latitude'] = lat
            details['longitude'] = lng
            if lat is not None and lng is not None:
                try:
                    lat_f = float(lat)
                    lng_f = float(lng)
                    details['has_coordinates'] = (lat_f != 0.0 or lng_f != 0.0)
                except (ValueError, TypeError):
                    details['has_coordinates'] = False

            # Vérifier le ref_administrative
            details['ref_administrative'] = ref_admin or ''
            details['required_depth'] = n_levels or 0

            if ref_admin and ref_admin.strip():
                # Compter les segments (format: "1-4-22-51-54")
                segments = [s.strip() for s in ref_admin.strip().split('-') if s.strip().isdigit()]
                details['ref_admin_depth'] = len(segments)
                # COMPLET si le nombre de segments correspond exactement à nLevels
                details['has_ref_admin'] = (len(segments) == (n_levels or 0)) if n_levels else len(segments) > 0

    except Exception as e:
        logger.error(f"[ActivationService] Erreur check_geolocation: {e}")
        import traceback
        traceback.print_exc()

    is_complete = details['has_coordinates'] and details['has_ref_admin']
    return is_complete, details


def check_campus_exists(etab_id, id_pays):
    """
    Vérifie qu'au moins un campus actif existe pour cet établissement.
    Filtrage STRICT par id_etablissement ET id_pays.

    Retourne (has_campus: bool, campus_count: int)
    """
    if not etab_id:
        return False, 0

    try:
        with connections['default'].cursor() as cur:
            sql = "SELECT COUNT(*) FROM campus WHERE id_etablissement = %s AND is_active = 1"
            params = [etab_id]

            if id_pays:
                sql += " AND id_pays = %s"
                params.append(id_pays)

            cur.execute(sql, params)
            row = cur.fetchone()
            count = int(row[0]) if row else 0
            return count > 0, count

    except Exception as e:
        logger.error(f"[ActivationService] Erreur check_campus: {e}")
        return False, 0


def get_activation_status(request):
    """
    Construit le statut d'activation complet pour le request courant.

    Retourne un dict avec :
    - geo_complete: bool (géolocalisation + ref_admin complet)
    - geo_details: dict (détails de la vérification géolocalisation)
    - campus_exists: bool (au moins un campus actif)
    - campus_count: int
    - config_unlocked: bool (Configuration accessible = geo_complete)
    - config_tabs_unlocked: bool (tous les onglets Configuration = campus_exists)
    - modules_allowed: list[str] (pages autorisées : 'administration' toujours, les autres selon statut)
    - sections_allowed: list[str] (sections admin autorisées)
    - blocking_reason: str (raison du blocage, vide si aucun)
    """
    etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
    id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')

    # État par défaut (tout bloqué)
    status = {
        'geo_complete': False,
        'geo_details': {},
        'campus_exists': False,
        'campus_count': 0,
        'config_unlocked': False,
        'config_tabs_unlocked': False,
        'modules_allowed': ['administration'],  # Dashboard + MonEcole toujours accessibles (dans administration)
        'sections_allowed': ['dashboard', 'structure'],  # Dashboard et MonEcole toujours dans admin
        'blocking_reason': '',
        'etab_id': etab_id,
        'id_pays': id_pays,
    }

    if not etab_id:
        status['blocking_reason'] = 'Aucun établissement résolu.'
        return status

    # 1. Vérifier la géolocalisation
    geo_complete, geo_details = check_geolocation_complete(etab_id, id_pays)
    status['geo_complete'] = geo_complete
    status['geo_details'] = geo_details

    if not geo_complete:
        reasons = []
        if not geo_details.get('has_coordinates'):
            reasons.append('Géolocalisation GPS manquante')
        if not geo_details.get('has_ref_admin'):
            depth = geo_details.get('ref_admin_depth', 0)
            required = geo_details.get('required_depth', 0)
            if depth == 0:
                reasons.append('Référence administrative non définie')
            else:
                reasons.append(f'Référence administrative incomplète ({depth}/{required} niveaux)')
        status['blocking_reason'] = ' • '.join(reasons)
        return status

    # 2. Géolocalisation OK → Configuration accessible
    status['config_unlocked'] = True
    status['sections_allowed'].extend(['structuration', 'calendrier', 'personnel', 'utilisateurs'])

    # 3. Vérifier la présence d'un campus
    campus_exists, campus_count = check_campus_exists(etab_id, id_pays)
    status['campus_exists'] = campus_exists
    status['campus_count'] = campus_count

    if campus_exists:
        # Tout est débloqué dans Configuration
        status['config_tabs_unlocked'] = True
        # Tous les modules deviennent accessibles
        status['modules_allowed'] = [
            'administration', 'scolarite', 'evaluations', 'enseignements',
            'espace_enseignant', 'communication', 'recouvrement',
        ]
    else:
        status['blocking_reason'] = 'Créez au moins un campus pour débloquer les autres onglets et modules.'

    return status


def invalidate_activation_cache(request):
    """
    Invalide le cache d'activation en session.
    À appeler après toute modification qui pourrait changer le statut :
    - Géolocalisation de l'établissement
    - Création/suppression d'un campus
    - Modification du ref_administrative
    """
    request.session.pop('_activation_status', None)
    request.session.pop('_activation_ts', None)


def get_cached_activation_status(request, max_age=60):
    """
    Retourne le statut d'activation depuis le cache session si encore valide,
    sinon le recalcule et le met en cache.

    max_age : durée de validité du cache en secondes (défaut: 60s)
    """
    import time

    cached = request.session.get('_activation_status')
    cached_ts = request.session.get('_activation_ts', 0)

    if cached and (time.time() - cached_ts) < max_age:
        return cached

    # Recalculer
    status = get_activation_status(request)

    # Stocker en session (sans les objets non-sérialisables)
    cache_data = {
        'geo_complete': status['geo_complete'],
        'campus_exists': status['campus_exists'],
        'campus_count': status['campus_count'],
        'config_unlocked': status['config_unlocked'],
        'config_tabs_unlocked': status['config_tabs_unlocked'],
        'modules_allowed': status['modules_allowed'],
        'sections_allowed': status['sections_allowed'],
        'blocking_reason': status['blocking_reason'],
    }
    request.session['_activation_status'] = cache_data
    request.session['_activation_ts'] = time.time()

    return status
