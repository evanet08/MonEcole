"""
Views d'authentification pour MonEcole.
Utilise Django auth_user + Personnel + UserModule + Module (tout dans db_monecole).
Flow : Email → Password → Dashboard (avec chargement des modules).
"""
import json
import time

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import connections

from MonEcole_app.variables import MODULE_ID_TO_PAGE
from MonEcole_app.models.personnel import Personnel
from MonEcole_app.models.module import Module, UserModule
from MonEcole_app.models.annee import Annee


# ── Helpers ──

def _load_user_modules(request, personnel):
    """
    Charge les modules accessibles pour le Personnel depuis user_module.
    Stocke la liste en session.
    """
    try:
        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')

        if etab_id:
            user_modules_qs = UserModule.objects.filter(
                user=personnel,
                is_active=True,
                id_etablissement=etab_id
            ).select_related('module').order_by('module__id_module')
        else:
            user_modules_qs = UserModule.objects.filter(
                user=personnel,
                is_active=True
            ).select_related('module').order_by('module__id_module')

        modules = []
        for um in user_modules_qs:
            if um.module:
                mod_id = um.module.id_module
                mod_info = MODULE_ID_TO_PAGE.get(mod_id)
                if mod_info:
                    modules.append({
                        'id': mod_id,
                        'name': um.module.module,
                        'page': mod_info['page'],
                        'url': mod_info['url'],
                        'icon': mod_info['icon'],
                        'label': mod_info['label'],
                    })

        # Dédupliquer par page
        seen_pages = set()
        unique_modules = []
        for m in modules:
            if m['page'] not in seen_pages:
                seen_pages.add(m['page'])
                unique_modules.append(m)

        request.session['user_modules'] = unique_modules
        return unique_modules

    except Exception as e:
        import traceback
        traceback.print_exc()
        request.session['user_modules'] = []
        return []


def get_redirect_url_for_user(modules=None):
    """Retourne l'URL de redirection post-login (premier module accessible)."""
    if modules and len(modules) > 0:
        return modules[0]['url']
    return '/dashboard/'


# ── Page Views ──

def login_view(request):
    """Vue de la page de connexion."""
    if request.user.is_authenticated:
        try:
            personnel = Personnel.objects.get(user=request.user)
            if personnel.isUser and personnel.en_fonction:
                return redirect('/dashboard/')
        except Personnel.DoesNotExist:
            pass

    # Contexte établissement pour afficher le logo
    context = {}
    etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
    if etab_id:
        try:
            from MonEcole_app.models.country_structure import Etablissement
            etab = Etablissement.objects.get(id_etablissement=etab_id)
            context['etab_nom'] = etab.nom
            logo = etab.logo_ecole or ''
            # Fallback: try spoke DB logo
            if not logo:
                try:
                    from MonEcole_app.models.ecole import Institution
                    inst = Institution.objects.get(id_ecole=etab_id)
                    if inst.logo_ecole:
                        logo = str(inst.logo_ecole)
                except Exception:
                    pass
            context['etab_logo'] = logo
        except Exception:
            pass

    return render(request, 'auth/login.html', context)


def logout_view(request):
    """Déconnexion."""
    logout(request)
    request.session.flush()
    return redirect('login')


# ── API Views ──

# ── Helpers pour Super Admin Hub ──

def _check_hub_admin(email, etab_id):
    """
    Vérifie si l'email correspond au admin_email du Hub pour cet établissement.
    Retourne (is_admin, admin_email, admin_info_dict) ou (False, None, None).
    """
    if not etab_id or not email:
        return False, None, None
    try:
        with connections['countryStructure'].cursor() as cur:
            cur.execute(
                "SELECT admin_email, admin_telephone, nom FROM etablissements WHERE id_etablissement=%s",
                [etab_id]
            )
            row = cur.fetchone()
            if not row:
                return False, None, None
            admin_email_hub = row[0]
            if admin_email_hub and email.strip().lower() == admin_email_hub.strip().lower():
                return True, admin_email_hub, {
                    'telephone': row[1] or '',
                    'nom_etab': row[2] or '',
                }
    except Exception:
        import traceback
        traceback.print_exc()
    return False, None, None


def _auto_provision_super_admin(email, etab_id, password=None):
    """
    Auto-crée auth_user + personnel + user_module pour le super admin Hub
    s'ils n'existent pas encore dans le spoke. Retourne (django_user, personnel).
    """
    from django.contrib.auth.hashers import make_password

    # 1. Chercher ou créer auth_user
    try:
        django_user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        username = email.split('@')[0].lower().replace('.', '_')
        # Garantir unicité du username
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        django_user = User.objects.create(
            username=username,
            email=email.lower(),
            first_name='Admin',
            last_name='',
            is_active=True,
        )
        if password:
            django_user.set_password(password)
            django_user.save()

    # 2. Chercher ou créer personnel
    try:
        personnel = Personnel.objects.get(user=django_user)
    except Personnel.DoesNotExist:
        # Générer un matricule unique
        last_pers = Personnel.objects.filter(
            id_etablissement=etab_id
        ).order_by('-id_personnel').first()
        next_num = (last_pers.id_personnel + 1) if last_pers else 1
        matricule = f"M_{etab_id}_{next_num}"

        personnel = Personnel.objects.create(
            user=django_user,
            matricule=matricule,
            id_etablissement=etab_id,
            isUser=True,
            is_verified=True,
            en_fonction=True,
            telephone='',
        )

    # 3. Garantir isUser, is_verified, en_fonction
    if not personnel.isUser or not personnel.is_verified or not personnel.en_fonction:
        Personnel.objects.filter(id_personnel=personnel.id_personnel).update(
            isUser=True, is_verified=True, en_fonction=True
        )
        personnel.refresh_from_db()

    # 4. Créer user_module pour TOUS les modules
    all_modules = Module.objects.all()
    annee = Annee.objects.order_by('-annee').first()
    annee_id = annee.id_annee if annee else 1

    for mod in all_modules:
        um, created = UserModule.objects.get_or_create(
            user=personnel,
            module=mod,
            id_etablissement=etab_id,
            defaults={
                'id_annee_id': annee_id,
                'is_active': True,
            }
        )
        if not created and not um.is_active:
            um.is_active = True
            um.save()

    return django_user, personnel


@csrf_exempt
@require_http_methods(["POST"])
def check_email(request):
    """
    Étape 1: Vérifie si un email existe dans auth_user + personnel.
    Si introuvable → cherche dans le Hub (admin_email) et auto-crée si match.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'success': False, 'error': 'Email requis'}, status=400)

        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')

        # Chercher dans le spoke
        user = None
        personnel = None
        try:
            user = User.objects.get(email__iexact=email)
            try:
                personnel = Personnel.objects.get(user=user)
            except Personnel.DoesNotExist:
                pass
        except User.DoesNotExist:
            pass

        # Si introuvable dans le spoke → chercher dans le Hub
        is_hub_admin = False
        if user is None or personnel is None:
            is_hub_admin_check, _, _ = _check_hub_admin(email, etab_id)
            if is_hub_admin_check:
                is_hub_admin = True
                # Auto-créer dans le spoke
                user, personnel = _auto_provision_super_admin(email, etab_id)
            else:
                # Ni dans le spoke, ni admin Hub → n'existe pas
                return JsonResponse({
                    'success': True,
                    'exists': False,
                    'validated': False,
                    'has_password': False,
                })
        else:
            # L'utilisateur existe dans le spoke — vérifier s'il est aussi admin Hub
            is_hub_admin, _, _ = _check_hub_admin(email, etab_id)
            if is_hub_admin:
                # Auto-provisionner (activer flags + modules)
                _auto_provision_super_admin(email, etab_id)
                personnel.refresh_from_db()

        # Si pas admin Hub → checks normaux
        if not is_hub_admin:
            if not personnel.isUser or not personnel.en_fonction:
                return JsonResponse({
                    'success': False,
                    'error': "Ce compte n'est pas autorisé à se connecter."
                }, status=403)

            if etab_id:
                has_modules = UserModule.objects.filter(
                    user=personnel,
                    is_active=True,
                    id_etablissement=etab_id
                ).exists()
                if not has_modules:
                    return JsonResponse({
                        'success': False,
                        'error': "Vous n'avez pas accès à cet établissement."
                    }, status=403)

        has_password = user.has_usable_password()

        return JsonResponse({
            'success': True,
            'exists': True,
            'validated': personnel.is_verified or is_hub_admin,
            'has_password': has_password,
            'multiple_accounts': False,
            'accounts': [],
            'user': {
                'id': user.id,
                'email': user.email,
                'telephone': str(personnel.telephone) if personnel.telephone else '',
                'niveau_nom': '',
                'niveau_ordre': 0,
                'scope_name': '',
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def request_otp(request):
    """OTP non utilisé dans cette version. Retourne un message indicatif."""
    return JsonResponse({
        'success': False,
        'error': "Contactez l'administrateur pour activer votre compte."
    }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    """OTP non utilisé dans cette version."""
    return JsonResponse({
        'success': False,
        'error': "Contactez l'administrateur pour activer votre compte."
    }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def set_password(request):
    """OTP non utilisé dans cette version."""
    return JsonResponse({
        'success': False,
        'error': "Contactez l'administrateur pour configurer votre mot de passe."
    }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """Connexion email + mot de passe via Django auth."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')

        # Chercher dans le spoke
        django_user = None
        personnel = None
        try:
            django_user = User.objects.get(email__iexact=email)
            try:
                personnel = Personnel.objects.get(user=django_user)
            except Personnel.DoesNotExist:
                pass
        except User.DoesNotExist:
            pass

        # Si introuvable → chercher dans le Hub
        is_super_admin = False
        if django_user is None or personnel is None:
            is_hub_admin, _, _ = _check_hub_admin(email, etab_id)
            if is_hub_admin:
                is_super_admin = True
                django_user, personnel = _auto_provision_super_admin(email, etab_id, password=password)
            else:
                return JsonResponse({'success': False, 'error': 'Identifiants incorrects'}, status=401)
        else:
            # L'utilisateur existe — vérifier s'il est admin Hub
            is_super_admin, _, _ = _check_hub_admin(email, etab_id)
            if is_super_admin:
                _auto_provision_super_admin(email, etab_id)
                personnel.refresh_from_db()

        # Checks normaux (super admin déjà auto-provisionné, donc passe)
        if not personnel.isUser or not personnel.en_fonction:
            return JsonResponse({'success': False, 'error': 'Compte non autorisé.'}, status=403)

        if not personnel.is_verified:
            return JsonResponse({
                'success': False,
                'error': "Compte non vérifié. Contactez l'administrateur.",
                'email_not_verified': True,
            }, status=403)

        # Authentifier via Django
        authenticated_user = authenticate(request, username=django_user.username, password=password)
        if authenticated_user is None:
            # Si le user vient d'être créé, le mot de passe n'est peut-être pas encore défini
            if is_super_admin and not django_user.has_usable_password():
                django_user.set_password(password)
                django_user.save()
                authenticated_user = authenticate(request, username=django_user.username, password=password)
            if authenticated_user is None:
                return JsonResponse({'success': False, 'error': 'Identifiants incorrects'}, status=401)

        # Vérifier les modules pour l'établissement
        if etab_id:
            has_modules = UserModule.objects.filter(
                user=personnel,
                is_active=True,
                id_etablissement=etab_id
            ).exists()
            if not has_modules:
                return JsonResponse({
                    'success': False,
                    'error': "Vous n'avez pas accès à cet établissement."
                }, status=403)

        all_user_modules = UserModule.objects.filter(user=personnel, is_active=True)
        if not all_user_modules.exists():
            return JsonResponse({
                'success': False,
                'error': "Aucun module assigné à votre compte."
            }, status=403)

        # Login Django
        login(request, authenticated_user)

        # Session
        request.session['user_id'] = django_user.id
        request.session['user_email'] = django_user.email
        request.session['personnel_id'] = personnel.id_personnel
        request.session['_last_activity'] = time.time()
        if is_super_admin:
            request.session['is_super_admin'] = True

        # Charger les modules
        user_modules = _load_user_modules(request, personnel)

        return JsonResponse({
            'success': True,
            'redirect_url': get_redirect_url_for_user(user_modules),
            'modules': user_modules,
            'user': {
                'email': django_user.email,
                'last_name': django_user.last_name,
                'first_name': django_user.first_name,
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_logout(request):
    """API Déconnexion."""
    logout(request)
    request.session.flush()
    return JsonResponse({'success': True, 'redirect_url': '/login/'})


@require_http_methods(["GET"])
def get_current_user(request):
    """Retourne les informations de l'utilisateur connecté."""
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False}, status=401)

    try:
        personnel = Personnel.objects.get(user=request.user)
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': request.user.id,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'matricule': personnel.matricule,
            }
        })
    except Personnel.DoesNotExist:
        return JsonResponse({'authenticated': False}, status=401)


def require_auth(view_func):
    """Décorateur pour exiger une authentification."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Non authentifié'}, status=401)
        try:
            request.personnel = Personnel.objects.get(user=request.user)
        except Personnel.DoesNotExist:
            return JsonResponse({'error': 'Compte non configuré'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper
