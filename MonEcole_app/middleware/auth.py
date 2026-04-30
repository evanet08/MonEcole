"""
Middleware d'authentification session-based pour MonEcole.
Remplace Django AuthenticationMiddleware — utilise personnel au lieu de auth_user.
"""
import time
import logging
from django.shortcuts import redirect
from django.http import JsonResponse
from MonEcole_app.models.personnel import Personnel

logger = logging.getLogger(__name__)

# Chemins exemptés d'authentification
EXEMPT_PATHS = (
    '/login/',
    '/api/auth/',
    '/api/get-pays-data/',
    '/static/',
    '/favicon.ico',
    '/media/',
    '/admin/',
    '/parent/',
    '/sw.js',
    '/manifest.json',
)

SESSION_INACTIVITY_TIMEOUT = 600  # 10 minutes


def _is_exempt(path):
    return any(path.startswith(p) for p in EXEMPT_PATHS)


class PersonnelAuthMiddleware:
    """
    Middleware qui :
    1. Vérifie que la session contient un personnel_id valide
    2. Attache l'objet personnel au request (request.user)
    3. Gère le timeout d'inactivité
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Chemins exemptés
        if _is_exempt(request.path):
            request.user = _AnonymousUser()
            return self.get_response(request)

        # Bypass pour appels inter-services (eSchool Hub → MonEcole)
        HUB_API_KEY = 'eSchoolRDC-Hub-2025-SecretKey'
        api_key = request.headers.get('X-Hub-Api-Key') or request.GET.get('hub_key') or request.POST.get('hub_key')
        if api_key == HUB_API_KEY:
            request.user = _AnonymousUser()
            request.user.is_authenticated = True  # Mark as authenticated for downstream
            return self.get_response(request)

        personnel_id = request.session.get('personnel_id')

        if not personnel_id:
            request.user = _AnonymousUser()
            # Redirections pour les pages (pas les API)
            if request.path.startswith('/api/'):
                return JsonResponse({'error': 'Non authentifié', 'session_expired': True}, status=401)
            return redirect('/login/')

        # Vérifier timeout d'inactivité
        now = time.time()
        last_activity = request.session.get('_last_activity')
        if last_activity and (now - last_activity > SESSION_INACTIVITY_TIMEOUT):
            request.session.flush()
            request.user = _AnonymousUser()
            if request.path.startswith('/api/'):
                return JsonResponse({'error': 'Session expirée', 'session_expired': True}, status=401)
            return redirect('/login/?expired=1')

        # Mettre à jour le timestamp
        request.session['_last_activity'] = now

        # Charger le personnel (avec cache session pour éviter les requêtes DB)
        try:
            cached_verified = request.session.get('_personnel_cached')
            if cached_verified:
                # Créer un objet léger à partir de la session
                request.user = _SessionPersonnel(request.session)
            else:
                personnel = Personnel.objects.get(id_personnel=personnel_id)
                request.user = personnel
                # Cacher les données essentielles en session
                request.session['_personnel_cached'] = True
                request.session['_personnel_email'] = personnel.email or ''
                request.session['_personnel_nom'] = personnel.nom or ''
                request.session['_personnel_prenom'] = personnel.prenom or ''
                request.session['_personnel_matricule'] = personnel.matricule or ''
        except Personnel.DoesNotExist:
            request.session.flush()
            request.user = _AnonymousUser()
            if request.path.startswith('/api/'):
                return JsonResponse({'error': 'Compte non trouvé'}, status=401)
            return redirect('/login/')

        # Bloquer l'accès au dashboard si le compte n'est pas vérifié
        needs_verification = request.session.get('needs_verification', False)
        if needs_verification:
            # Re-check DB to avoid stale session causing redirect loops
            try:
                from django.db import connections
                pid = request.session.get('personnel_id')
                if pid:
                    with connections['default'].cursor() as cur:
                        cur.execute("SELECT email_verified, phone_verified FROM personnel WHERE id_personnel=%s", [pid])
                        row = cur.fetchone()
                        if row and (row[0] or row[1]):
                            request.session['needs_verification'] = False
                            request.session['email_verified'] = bool(row[0])
                            request.session['phone_verified'] = bool(row[1])
                            needs_verification = False
            except Exception:
                pass

            if needs_verification:
                # Autoriser uniquement les endpoints de vérification et la page login
                verification_paths = ('/login/', '/api/auth/verify-contact/', '/api/auth/request-otp/', '/api/auth/verify-otp/', '/logout/')
                if not any(request.path.startswith(p) for p in verification_paths):
                    if request.path.startswith('/api/'):
                        return JsonResponse({
                            'error': 'Veuillez vérifier votre email ou numéro de téléphone.',
                            'needs_verification': True
                        }, status=403)
                    return redirect('/login/?step=verify')

        return self.get_response(request)


class _AnonymousUser:
    """Objet utilisateur anonyme minimal pour compatibilité."""
    id = None
    id_personnel = None
    pk = None
    username = ''
    email = ''
    is_authenticated = False
    is_anonymous = True
    is_active = False
    first_name = ''
    last_name = ''

    def get_full_name(self):
        return ''

    def has_usable_password(self):
        return False


class _SessionPersonnel:
    """
    Proxy léger pour Personnel, construit à partir des données session.
    Évite une requête DB à chaque request.
    """
    def __init__(self, session):
        self.id_personnel = session.get('personnel_id')
        self.id = self.id_personnel
        self.pk = self.id_personnel
        self.email = session.get('_personnel_email', session.get('user_email', ''))
        self.nom = session.get('_personnel_nom', '')
        self.prenom = session.get('_personnel_prenom', '')
        self.matricule = session.get('_personnel_matricule', '')
        self.is_authenticated = True
        self.is_anonymous = False
        self.is_active = True
        self.username = session.get('user_email', '')

    @property
    def first_name(self):
        return self.prenom

    @property
    def last_name(self):
        return self.nom

    def get_full_name(self):
        parts = [self.prenom or '', self.nom or '']
        return ' '.join(p for p in parts if p).strip()

    def has_usable_password(self):
        return True
