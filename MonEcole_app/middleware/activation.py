"""
Middleware d'activation progressive des modules.

RÈGLES STRICTES :
1. Tant que la géolocalisation est incomplète → seuls Dashboard et MonEcole (section structure)
   sont accessibles dans le module Administration. Tous les autres modules sont BLOQUÉS.
2. Dès que la géolocalisation est complète → module Configuration s'active.
3. Dans Configuration, seul l'onglet Campus est actif tant qu'aucun campus n'existe.
4. Aucun contournement possible.

Ce middleware s'exécute APRÈS TenantMiddleware et PersonnelAuthMiddleware.
"""
import logging
from django.http import JsonResponse
from django.shortcuts import redirect

from MonEcole_app.services.activation_service import (
    get_cached_activation_status,
    invalidate_activation_cache,
)

logger = logging.getLogger(__name__)

# Chemins dashboard exemptés de la vérification d'activation
# (login, static, API d'auth, etc. sont déjà gérés par PersonnelAuthMiddleware)
ACTIVATION_EXEMPT_PATHS = (
    '/login/',
    '/api/auth/',
    '/static/',
    '/favicon.ico',
    '/media/',
    '/admin/',
    '/parent/',
    '/sw.js',
    '/manifest.json',
    '/logout/',
)

# APIs qui doivent TOUJOURS être accessibles (même si modules bloqués)
# car elles concernent la géolocalisation et la création de campus
ALWAYS_ALLOWED_APIS = (
    # MonEcole (fiche établissement + géolocalisation)
    '/api/mon-etablissement/',
    '/api/update-mon-etablissement/',
    '/api/upload-etab-logo/',
    '/api/upload-etab-document/',
    '/api/create-admin-instance/',
    '/api/update-admin-instance/',
    '/api/rue-suggestions/',
    # Campus CRUD (nécessaire pour débloquer Configuration)
    '/api/dashboard/campus-list/',
    '/api/dashboard/campus-create/',
    '/api/dashboard/campus-update/',
    '/api/dashboard/campus-delete/',
    # Dashboard stats
    '/api/dashboard/eleves-stats/',
    # Configuration (structuration) — nécessaire après géolocalisation
    '/api/get-cycles/',
    '/api/get-sections-list/',
    '/api/get-etablissement-config/',
    '/api/save-etablissement-config/',
    # Calendrier
    '/api/toggle-calendar-synch/',
    '/api/update-calendar-config/',
    '/api/repartition/',
    # Personnel & utilisateurs
    '/api/dashboard/personnel-',
    '/api/dashboard/add-personnel/',
    '/api/dashboard/update-personnel/',
    '/api/dashboard/upload-personnel-photo/',
    '/api/dashboard/personnel-ref-crud/',
    '/api/dashboard/personnel-template/',
    '/api/dashboard/import-personnel/',
    '/api/dashboard/users/',
)

# Sections admin toujours accessibles (peu importe l'état)
ALWAYS_ALLOWED_ADMIN_SECTIONS = {'dashboard', 'structure'}

# Mapping URL page → module_page pour le contrôle
DASHBOARD_PAGE_MAP = {
    '/dashboard/administration/': 'administration',
    '/dashboard/': 'administration',
    '/dashboard/scolarite/': 'scolarite',
    '/dashboard/evaluations/': 'evaluations',
    '/dashboard/enseignements/': 'enseignements',
    '/dashboard/enseignant/': 'espace_enseignant',
    '/dashboard/communication/': 'communication',
    '/dashboard/recouvrement/': 'recouvrement',
}


class ActivationMiddleware:
    """
    Middleware qui contrôle l'activation progressive des modules.
    Bloque l'accès aux modules/sections non autorisés selon l'état
    de géolocalisation et de configuration de l'établissement.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Skip pour les chemins exemptés
        if any(path.startswith(p) for p in ACTIVATION_EXEMPT_PATHS):
            return self.get_response(request)

        # Ne s'applique qu'aux requêtes dashboard et API dashboard
        if not path.startswith('/dashboard/') and not path.startswith('/api/'):
            return self.get_response(request)

        # Vérifier que l'utilisateur est authentifié (sinon le auth middleware gère)
        if not request.session.get('personnel_id'):
            return self.get_response(request)

        # Ne pas bloquer les APIs toujours autorisées
        if path.startswith('/api/'):
            if any(path.startswith(p) for p in ALWAYS_ALLOWED_APIS):
                return self.get_response(request)

        # Pas d'établissement résolu → pas de contrôle d'activation
        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
        if not etab_id:
            return self.get_response(request)

        # Récupérer le statut d'activation (avec cache)
        status = get_cached_activation_status(request)

        # Attacher au request pour usage dans les vues et templates
        request.activation_status = status

        # ── Contrôle des pages dashboard ──
        if path.startswith('/dashboard/'):
            module_page = DASHBOARD_PAGE_MAP.get(path)

            if module_page and module_page != 'administration':
                # Vérifier si ce module est autorisé
                if module_page not in status.get('modules_allowed', []):
                    logger.info(
                        f"[ActivationMiddleware] Accès BLOQUÉ à {path} — "
                        f"geo_complete={status.get('geo_complete')}, "
                        f"campus_exists={status.get('campus_exists')}"
                    )
                    # Rediriger vers l'administration avec un message
                    return redirect(
                        f'/dashboard/administration/?section=structure'
                        f'&blocked=1&reason=activation'
                    )

            # Pour l'administration, vérifier les sections
            if module_page == 'administration':
                section = request.GET.get('section', 'dashboard')
                allowed_sections = status.get('sections_allowed', ['dashboard', 'structure'])

                if section not in allowed_sections and section not in ALWAYS_ALLOWED_ADMIN_SECTIONS:
                    logger.info(
                        f"[ActivationMiddleware] Section BLOQUÉE: {section} — "
                        f"geo_complete={status.get('geo_complete')}"
                    )
                    return redirect(
                        f'/dashboard/administration/?section=structure'
                        f'&blocked=1&reason=geo_incomplete'
                    )

        # ── Contrôle des APIs (modules non autorisés) ──
        if path.startswith('/api/') and not status.get('geo_complete', False):
            # Bloquer les APIs qui ne sont pas dans la liste "toujours autorisées"
            blocked_api_prefixes = (
                '/api/evaluations/',
                '/api/notes/',
                '/api/deliberations/',
                '/api/dashboard/search-parents/',
                '/api/dashboard/add-eleve/',
                '/api/dashboard/eleves-list/',
                '/api/dashboard/eleve-template/',
                '/api/dashboard/import-eleves/',
                '/api/dashboard/update-eleve/',
                '/api/dashboard/upload-photo/',
                '/api/dashboard/delete-inscriptions/',
                '/api/dashboard/attribution-cours/',
                '/api/dashboard/horaire/',
                '/api/recouvrement/',
                '/api/enseignant/',
                '/api/communication/',
                '/api/bulletins/',
                '/api/get-cours/',
                '/api/save-cours/',
                '/api/delete-cours/',
                '/api/get-cours-annee/',
                '/api/save-cours-annee/',
                '/api/delete-cours-annee/',
                '/api/bulk-activate-cours-annee/',
                '/api/get-domaines/',
                '/api/save-domaine/',
                '/api/delete-domaine/',
            )
            if any(path.startswith(p) for p in blocked_api_prefixes):
                return JsonResponse({
                    'success': False,
                    'error': 'Module non disponible. Complétez d\'abord la géolocalisation de votre établissement.',
                    'activation_blocked': True,
                    'blocking_reason': status.get('blocking_reason', ''),
                }, status=403)

        return self.get_response(request)
