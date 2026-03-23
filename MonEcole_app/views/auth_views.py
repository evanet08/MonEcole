"""
Views d'authentification pour MonEcole.
Flow multi-étapes identique à eSchool : Email → Password / OTP → Dashboard

Utilise AdminUser + OTPCode du hub (countryStructure), exactement comme eSchool.
"""
import json
import random
import string
import hashlib
import secrets
import time
from datetime import timedelta

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import connections

from MonEcole_app.variables import MODULE_ID_TO_PAGE


# ── Import des modèles Hub (countryStructure) ──
# AdminUser et OTPCode sont dans countryStructure, accessibles via le db_router

def _get_admin_user_model():
    """Import lazy pour éviter les imports circulaires."""
    from MonEcole_app.models.hub_auth import AdminUser
    return AdminUser

def _get_otp_model():
    from MonEcole_app.models.hub_auth import OTPCode
    return OTPCode


# ── Helpers ──

def hash_password(password):
    """Hash un mot de passe avec SHA256 + salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hashed.hex()}"


def verify_password(stored_hash, password):
    """Vérifie un mot de passe contre son hash."""
    if not stored_hash or '$' not in stored_hash:
        return False
    salt, hash_value = stored_hash.split('$', 1)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return hashed.hex() == hash_value


def generate_otp_code():
    return ''.join(random.choices(string.digits, k=6))


def generate_token():
    return secrets.token_urlsafe(32)


def _load_user_modules(request, user):
    """
    Charge les modules accessibles pour l'utilisateur depuis user_module.
    
    Chaîne de liaison : AdminUser.email → auth_user.email → personnel.user_id
                        → user_module.user_id (FK vers personnel.id_personnel)
    
    Stocke la liste en session pour éviter de refaire la query.
    """
    try:
        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
        user_email = user.email

        with connections['default'].cursor() as cur:
            # Trouver les modules via la chaîne: email → auth_user → personnel → user_module
            if etab_id:
                cur.execute("""
                    SELECT DISTINCT um.module_id, m.module, m.url_name
                    FROM user_module um
                    JOIN module m ON m.id_module = um.module_id
                    JOIN personnel p ON p.id_personnel = um.user_id
                    JOIN auth_user au ON au.id = p.user_id
                    WHERE au.email = %s AND um.is_active = 1
                      AND um.id_etablissement = %s
                    ORDER BY um.module_id
                """, [user_email, etab_id])
            else:
                cur.execute("""
                    SELECT DISTINCT um.module_id, m.module, m.url_name
                    FROM user_module um
                    JOIN module m ON m.id_module = um.module_id
                    JOIN personnel p ON p.id_personnel = um.user_id
                    JOIN auth_user au ON au.id = p.user_id
                    WHERE au.email = %s AND um.is_active = 1
                    ORDER BY um.module_id
                """, [user_email])
            rows = cur.fetchall()
    except Exception as e:
        import traceback
        traceback.print_exc()
        rows = []

    modules = []
    for row in rows:
        mod_id = row[0]
        mod_info = MODULE_ID_TO_PAGE.get(mod_id)
        if mod_info:
            modules.append({
                'id': mod_id,
                'name': row[1],
                'page': mod_info['page'],
                'url': mod_info['url'],
                'icon': mod_info['icon'],
                'label': mod_info['label'],
            })

    # Dédupliquer par page (plusieurs modules peuvent mapper vers la même page)
    seen_pages = set()
    unique_modules = []
    for m in modules:
        if m['page'] not in seen_pages:
            seen_pages.add(m['page'])
            unique_modules.append(m)

    request.session['user_modules'] = unique_modules
    return unique_modules


def get_redirect_url_for_user(user, modules=None):
    """Retourne l'URL de redirection post-login (premier module accessible)."""
    if modules and len(modules) > 0:
        return modules[0]['url']
    return '/dashboard/'


# ── Page Views ──

def login_view(request):
    """Vue de la page de connexion."""
    user_id = request.session.get('user_id')
    if user_id:
        AdminUser = _get_admin_user_model()
        try:
            user = AdminUser.objects.get(id_admin=user_id)
            if user.is_active and user.email_verified:
                return redirect(get_redirect_url_for_user(user))
        except AdminUser.DoesNotExist:
            request.session.flush()

    return render(request, 'auth/login.html')


def logout_view(request):
    """Déconnexion."""
    request.session.flush()
    return redirect('login')


# ── API Views ──

@csrf_exempt
@require_http_methods(["POST"])
def check_email(request):
    """
    Étape 1: Vérifie si un email existe et son état.
    Identique à eSchool.
    """
    try:
        AdminUser = _get_admin_user_model()
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'success': False, 'error': 'Email requis'}, status=400)

        users = AdminUser.objects.filter(email__iexact=email, is_active=True)

        if not users.exists():
            return JsonResponse({
                'success': True,
                'exists': False,
                'validated': False,
                'has_password': False,
            })

        # Le premier avec mot de passe, sinon le premier
        primary = users.filter(password_hash__gt='').first() or users.first()

        accounts = []
        for u in users:
            accounts.append({
                'id': u.id_admin,
                'niveau_nom': u.niveau_nom,
                'scope_name': u.scope_name,
            })

        return JsonResponse({
            'success': True,
            'exists': True,
            'validated': primary.is_validated,
            'has_password': primary.has_password,
            'multiple_accounts': len(accounts) > 1,
            'accounts': accounts,
            'user': {
                'id': primary.id_admin,
                'email': primary.email,
                'telephone': primary.telephone,
                'niveau_nom': primary.niveau_nom,
                'niveau_ordre': primary.niveau_ordre,
                'scope_name': primary.scope_name,
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def request_otp(request):
    """Envoie un code OTP par email ou SMS."""
    try:
        AdminUser = _get_admin_user_model()
        OTPCode = _get_otp_model()

        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        method = data.get('method', 'EMAIL')

        if method not in ['EMAIL', 'SMS']:
            return JsonResponse({'success': False, 'error': 'Méthode invalide'}, status=400)

        users = AdminUser.objects.filter(email__iexact=email, is_active=True)
        user = users.filter(password_hash__gt='').first() or users.first()
        if not user:
            return JsonResponse({'success': False, 'error': 'Utilisateur non trouvé'}, status=404)

        # Invalider les anciens codes
        OTPCode.objects.filter(user=user, used=False).update(used=True)

        # Générer nouveau code
        code = generate_otp_code()
        expires_at = timezone.now() + timedelta(minutes=10)

        otp = OTPCode.objects.create(
            user=user,
            code=code,
            type=method,
            expires_at=expires_at
        )

        # Envoyer le code
        send_success = False
        send_error = None
        if method == 'EMAIL':
            try:
                send_mail(
                    subject='Code de vérification MonEcole',
                    message=f'Votre code de vérification est: {code}\n\nCe code expire dans 10 minutes.',
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@monecole.pro'),
                    recipient_list=[email],
                    fail_silently=False,
                )
                send_success = True
            except Exception as e:
                send_error = str(e)
                print(f"[ERROR] Envoi email OTP échoué pour {email}: {e}")

        # Token de session
        token = generate_token()
        request.session['otp_token'] = token
        request.session['otp_user_id'] = user.id_admin
        request.session['otp_code_id'] = otp.id_otp

        response_data = {
            'success': True,
            'token': token,
            'message': f'Code envoyé par {method}'
        }
        if not send_success:
            response_data['warning'] = f"Erreur lors de l'envoi: {send_error}"

        return JsonResponse(response_data)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    """Vérifie le code OTP saisi."""
    try:
        AdminUser = _get_admin_user_model()
        OTPCode = _get_otp_model()

        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()
        token = data.get('token', '')

        if request.session.get('otp_token') != token:
            return JsonResponse({'success': False, 'error': 'Session invalide'}, status=400)

        users = AdminUser.objects.filter(email__iexact=email, is_active=True)
        user = users.filter(id_admin=request.session.get('otp_user_id')).first()
        if not user:
            user = users.filter(password_hash__gt='').first() or users.first()
        if not user:
            return JsonResponse({'success': False, 'error': 'Utilisateur non trouvé'}, status=404)

        otp = OTPCode.objects.filter(user=user, used=False).order_by('-created_at').first()
        if not otp:
            return JsonResponse({'success': False, 'error': 'Aucun code en attente'}, status=400)

        if otp.attempts >= 3:
            return JsonResponse({'success': False, 'error': 'Trop de tentatives.'}, status=400)

        if otp.is_expired:
            return JsonResponse({'success': False, 'error': 'Code expiré.'}, status=400)

        if otp.code != code:
            otp.increment_attempts()
            remaining = 3 - otp.attempts
            return JsonResponse({
                'success': False,
                'error': f'Code incorrect. {remaining} tentative(s) restante(s).'
            }, status=400)

        # Code valide
        otp.mark_used()

        if otp.type == 'EMAIL':
            user.email_verified = True
            AdminUser.objects.filter(email__iexact=email).update(email_verified=True)
        else:
            user.phone_verified = True
            AdminUser.objects.filter(email__iexact=email).update(phone_verified=True)
        user.save()

        new_token = generate_token()
        request.session['password_token'] = new_token
        request.session['password_user_id'] = user.id_admin

        return JsonResponse({
            'success': True,
            'token': new_token,
            'message': 'Code vérifié avec succès'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def set_password(request):
    """Définit le mot de passe après validation OTP."""
    try:
        AdminUser = _get_admin_user_model()

        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        token = data.get('token', '')

        if request.session.get('password_token') != token:
            return JsonResponse({'success': False, 'error': 'Session invalide'}, status=400)

        if len(password) < 6:
            return JsonResponse({'success': False, 'error': 'Mot de passe trop court (min 6)'}, status=400)

        users = AdminUser.objects.filter(email__iexact=email, is_active=True)
        user = users.filter(id_admin=request.session.get('password_user_id')).first()
        if not user:
            user = users.first()
        if not user:
            return JsonResponse({'success': False, 'error': 'Utilisateur non trouvé'}, status=404)

        # Hash et sauvegarde
        hashed = hash_password(password)
        user.password_hash = hashed
        user.last_login = timezone.now()
        user.save()

        # Synchroniser pour tous les comptes avec ce même email
        AdminUser.objects.filter(email__iexact=email).exclude(id_admin=user.id_admin).update(password_hash=hashed)

        # Session
        request.session['user_id'] = user.id_admin
        request.session['user_email'] = user.email
        request.session['user_niveau'] = user.niveau_ordre
        request.session['user_scope'] = user.scope_code
        request.session['_last_activity'] = time.time()

        all_accounts = list(AdminUser.objects.filter(
            email__iexact=user.email, is_active=True, email_verified=True
        ).values_list('id_admin', flat=True))
        request.session['user_account_ids'] = all_accounts

        # Charger les modules
        user_modules = _load_user_modules(request, user)

        # Nettoyer
        request.session.pop('password_token', None)
        request.session.pop('password_user_id', None)

        return JsonResponse({
            'success': True,
            'redirect_url': get_redirect_url_for_user(user, user_modules),
            'message': 'Compte activé avec succès'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """Connexion email + mot de passe."""
    try:
        AdminUser = _get_admin_user_model()

        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        user_id_choice = data.get('user_id')

        users = AdminUser.objects.filter(email__iexact=email, is_active=True)
        if not users.exists():
            return JsonResponse({'success': False, 'error': 'Identifiants incorrects'}, status=401)

        valid_user = None
        for u in users:
            if verify_password(u.password_hash, password):
                valid_user = u
                break

        if not valid_user:
            return JsonResponse({'success': False, 'error': 'Identifiants incorrects'}, status=401)

        if not valid_user.email_verified:
            return JsonResponse({
                'success': False,
                'error': "Email non vérifié. Activez votre compte via le code OTP.",
                'email_not_verified': True,
            }, status=403)

        # Si un choix de structure spécifique
        if user_id_choice:
            target = users.filter(id_admin=user_id_choice).first()
            if target and verify_password(target.password_hash, password):
                if not target.email_verified:
                    return JsonResponse({
                        'success': False,
                        'error': 'Email non vérifié pour cette structure.',
                        'email_not_verified': True,
                    }, status=403)
                valid_user = target

        user = valid_user

        if not user.is_active:
            return JsonResponse({'success': False, 'error': 'Compte désactivé.'}, status=403)

        # Vérifier que l'utilisateur appartient à CET établissement (résolu par le sous-domaine)
        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
        if etab_id:
            try:
                with connections['default'].cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM user_module um
                        JOIN personnel p ON p.id_personnel = um.user_id
                        JOIN auth_user au ON au.id = p.user_id
                        WHERE au.email = %s AND um.is_active = 1
                          AND um.id_etablissement = %s
                    """, [user.email, etab_id])
                    count = cur.fetchone()[0]
                if count == 0:
                    return JsonResponse({
                        'success': False,
                        'error': "Vous n'avez pas accès à cet établissement."
                    }, status=403)
            except Exception:
                pass  # En cas d'erreur SQL, on laisse passer (graceful degradation)

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Tous les comptes accessibles
        all_account_ids = []
        for u in users:
            if u.password_hash and u.email_verified and verify_password(u.password_hash, password):
                all_account_ids.append(u.id_admin)
        if user.id_admin not in all_account_ids:
            all_account_ids.append(user.id_admin)

        # Session
        request.session['user_id'] = user.id_admin
        request.session['user_email'] = user.email
        request.session['user_niveau'] = user.niveau_ordre
        request.session['user_scope'] = user.scope_code
        request.session['user_account_ids'] = all_account_ids
        request.session['_last_activity'] = time.time()

        # Charger les modules (filtrés par établissement via etab_id)
        user_modules = _load_user_modules(request, user)

        return JsonResponse({
            'success': True,
            'redirect_url': get_redirect_url_for_user(user, user_modules),
            'modules': user_modules,
            'user': {
                'email': user.email,
                'niveau_nom': user.niveau_nom,
                'scope_name': user.scope_name,
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
    request.session.flush()
    return JsonResponse({'success': True, 'redirect_url': '/login/'})


@require_http_methods(["GET"])
def get_current_user(request):
    """Retourne les informations de l'utilisateur connecté."""
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'authenticated': False}, status=401)

    try:
        AdminUser = _get_admin_user_model()
        user = AdminUser.objects.get(id_admin=user_id)
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': user.id_admin,
                'email': user.email,
                'telephone': user.telephone,
                'niveau_nom': user.niveau_nom,
                'niveau_ordre': user.niveau_ordre,
                'scope_name': user.scope_name,
                'scope_code': user.scope_code,
            }
        })
    except AdminUser.DoesNotExist:
        request.session.flush()
        return JsonResponse({'authenticated': False}, status=401)


def require_auth(view_func):
    """Décorateur pour exiger une authentification."""
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'Non authentifié'}, status=401)
        try:
            AdminUser = _get_admin_user_model()
            request.admin_user = AdminUser.objects.get(id_admin=user_id)
        except AdminUser.DoesNotExist:
            request.session.flush()
            return JsonResponse({'error': 'Session invalide'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper
