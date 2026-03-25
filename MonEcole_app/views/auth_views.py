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

@csrf_exempt
@require_http_methods(["POST"])
def check_email(request):
    """
    Étape 1: Vérifie si un email existe dans auth_user + personnel.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'success': False, 'error': 'Email requis'}, status=400)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return JsonResponse({
                'success': True,
                'exists': False,
                'validated': False,
                'has_password': False,
            })

        # Vérifier que le personnel existe
        try:
            personnel = Personnel.objects.get(user=user)
        except Personnel.DoesNotExist:
            return JsonResponse({
                'success': True,
                'exists': False,
                'validated': False,
                'has_password': False,
            })

        # Vérifier si c'est le super admin du Hub → bypass les checks
        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
        is_hub_admin = False
        if etab_id:
            try:
                from django.db import connections as db_conns
                with db_conns['countryStructure'].cursor() as hub_cur:
                    hub_cur.execute(
                        "SELECT admin_email FROM etablissements WHERE id_etablissement=%s",
                        [etab_id]
                    )
                    hub_row = hub_cur.fetchone()
                    admin_email_hub = hub_row[0] if hub_row else None
                if admin_email_hub and email == admin_email_hub.strip().lower():
                    is_hub_admin = True
            except Exception:
                pass

        if not is_hub_admin:
            # Vérifier que le personnel est autorisé
            if not personnel.isUser or not personnel.en_fonction:
                return JsonResponse({
                    'success': False,
                    'error': "Ce compte n'est pas autorisé à se connecter."
                }, status=403)

            # Vérifier l'établissement (tenant)
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

        # Trouver le user Django par email
        try:
            django_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Identifiants incorrects'}, status=401)

        # Vérifier le personnel
        try:
            personnel = Personnel.objects.get(user=django_user)
        except Personnel.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Compte non configuré.'}, status=403)

        # ── Auto-provisioning Super Admin (AVANT les checks bloquants) ──
        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
        is_super_admin = False
        try:
            if etab_id:
                from django.db import connections as db_conns
                with db_conns['countryStructure'].cursor() as hub_cur:
                    hub_cur.execute(
                        "SELECT admin_email FROM etablissements WHERE id_etablissement=%s",
                        [etab_id]
                    )
                    hub_row = hub_cur.fetchone()
                    admin_email_hub = hub_row[0] if hub_row else None

                if admin_email_hub and email == admin_email_hub.strip().lower():
                    is_super_admin = True
                    # Activer le personnel si nécessaire
                    if not personnel.isUser or not personnel.is_verified or not personnel.en_fonction:
                        Personnel.objects.filter(id_personnel=personnel.id_personnel).update(
                            isUser=True, is_verified=True, en_fonction=True
                        )
                        personnel.refresh_from_db()

                    # Créer tous les user_module pour cet établissement
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
        except Exception:
            import traceback
            traceback.print_exc()

        # Maintenant les checks normaux (le super admin les passe car auto-provisionné)
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
            return JsonResponse({'success': False, 'error': 'Identifiants incorrects'}, status=401)

        # Vérifier l'établissement (tenant)
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

        # Vérifier qu'il a au moins un module actif
        all_user_modules = UserModule.objects.filter(user=personnel, is_active=True)
        if not all_user_modules.exists():
            return JsonResponse({
                'success': False,
                'error': "Aucun module assigné à votre compte."
            }, status=403)

        # Login Django
        login(request, authenticated_user)

        # Session supplémentaire
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
