"""
Views d'authentification pour MonEcole.
Utilise Personnel directement (sans auth_user).
Flow : Email → Password → Dashboard (avec chargement des modules).
"""
import json
import time
import hashlib
import secrets

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connections

from MonEcole_app.variables import MODULE_ID_TO_PAGE
from MonEcole_app.models.personnel import Personnel
from MonEcole_app.models.module import Module, UserModule
from MonEcole_app.models.annee import Annee


# ── Helpers ──

def _load_user_modules(request, personnel):
    """
    Charge les modules accessibles pour le Personnel depuis user_module.
    Auto-injecte le module Espace_Enseignant (id=5) si le personnel
    a au moins un cours attribué dans attribution_cours.
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
        seen_ids = set()
        for um in user_modules_qs:
            if um.module:
                mod_id = um.module.id_module
                mod_info = MODULE_ID_TO_PAGE.get(mod_id)
                if mod_info:
                    seen_ids.add(mod_id)
                    modules.append({
                        'id': mod_id,
                        'name': um.module.module,
                        'page': mod_info['page'],
                        'url': mod_info['url'],
                        'icon': mod_info['icon'],
                        'label': mod_info['label'],
                    })

        # ── Auto-inject Espace Enseignant (module 5) ──
        ESPACE_ENSEIGNANT_ID = 5
        if ESPACE_ENSEIGNANT_ID not in seen_ids and etab_id:
            try:
                with connections['default'].cursor() as cur:
                    cur.execute("""
                        SELECT COUNT(*) FROM attribution_cours
                        WHERE id_personnel_id = %s AND id_etablissement = %s
                    """, [personnel.id_personnel, etab_id])
                    has_courses = cur.fetchone()[0] > 0
                if has_courses:
                    mod_info = MODULE_ID_TO_PAGE.get(ESPACE_ENSEIGNANT_ID)
                    if mod_info:
                        modules.append({
                            'id': ESPACE_ENSEIGNANT_ID,
                            'name': 'Espace_Enseignant',
                            'page': mod_info['page'],
                            'url': mod_info['url'],
                            'icon': mod_info['icon'],
                            'label': mod_info['label'],
                        })
            except Exception:
                import traceback
                traceback.print_exc()

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
    # Vérifier si déjà connecté via la session
    personnel_id = request.session.get('personnel_id')
    if personnel_id:
        try:
            personnel = Personnel.objects.get(id_personnel=personnel_id)
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
    request.session.flush()
    return redirect('login')


# ── API Views ──

# ── Helpers pour authentification Hub ──

def _verify_hub_password(stored_hash, password):
    """
    Vérifie un mot de passe contre le hash du Hub (PBKDF2-SHA256, format: salt$hex).
    Même algorithme que dans eSchoolStructure/structure_app/auth_views.py.
    """
    if not stored_hash or '$' not in stored_hash:
        return False
    try:
        salt, hash_value = stored_hash.split('$', 1)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return hashed.hex() == hash_value
    except Exception:
        return False


def _check_hub_user(email, etab_id):
    """
    Vérifie si l'email existe dans le Hub pour cet établissement.
    Cherche dans 2 endroits:
      1) etablissements.admin_email — le super admin désigné
      2) admin_users — tout utilisateur Hub assigné à cet établissement

    Retourne (found, is_super_admin, hub_info_dict) ou (False, False, None).
    """
    if not etab_id or not email:
        return False, False, None
    email_lower = email.strip().lower()
    try:
        with connections['countryStructure'].cursor() as cur:
            # 1) Vérifier si c'est le super admin de l'établissement
            is_super = False
            cur.execute(
                "SELECT admin_email, admin_telephone, nom FROM etablissements WHERE id_etablissement=%s",
                [etab_id]
            )
            etab_row = cur.fetchone()
            if etab_row:
                admin_email_hub = etab_row[0]
                if admin_email_hub and email_lower == admin_email_hub.strip().lower():
                    is_super = True

            # 2) Vérifier dans admin_users du Hub
            cur.execute(
                """SELECT id_admin, email, telephone, password_hash,
                          email_verified, is_active
                   FROM admin_users
                   WHERE LOWER(email) = %s
                     AND etablissement_id = %s
                     AND is_active = 1
                   LIMIT 1""",
                [email_lower, etab_id]
            )
            hub_user = cur.fetchone()

            if hub_user:
                return True, is_super, {
                    'hub_id': hub_user[0],
                    'email': hub_user[1],
                    'telephone': hub_user[2] or '',
                    'password_hash': hub_user[3] or '',
                    'email_verified': bool(hub_user[4]),
                    'nom_etab': etab_row[2] if etab_row else '',
                }

            # Si c'est le super admin mais pas dans admin_users → encore valide
            if is_super:
                return True, True, {
                    'hub_id': None,
                    'email': email_lower,
                    'telephone': etab_row[1] or '',
                    'password_hash': '',
                    'email_verified': False,
                    'nom_etab': etab_row[2] if etab_row else '',
                }

    except Exception:
        import traceback
        traceback.print_exc()
    return False, False, None


# Rétro-compatibilité
def _check_hub_admin(email, etab_id):
    """Wrapper rétro-compatible."""
    found, is_super, info = _check_hub_user(email, etab_id)
    if found:
        return True, email, info
    return False, None, None


def _auto_provision_hub_user(email, etab_id, hub_info=None, is_super=False, password=None):
    """
    Auto-crée un personnel + user_module pour un utilisateur Hub
    s'ils n'existent pas encore dans le spoke.

    - is_super=True  → provisionne TOUS les modules
    - is_super=False → provisionne le module Administration par défaut

    Retourne personnel.
    """
    hub_password_hash = (hub_info or {}).get('password_hash', '') if hub_info else ''
    hub_telephone = (hub_info or {}).get('telephone', '') if hub_info else ''

    # 1. Chercher le personnel existant par email
    try:
        personnel = Personnel.objects.get(email__iexact=email, id_etablissement=etab_id)
    except Personnel.DoesNotExist:
        # Chercher sans filtre etab
        try:
            personnel = Personnel.objects.get(email__iexact=email)
        except (Personnel.DoesNotExist, Personnel.MultipleObjectsReturned):
            personnel = None

    if personnel is None:
        # Créer le personnel directement
        from MonEcole_app.models.personnel import (
            Diplome, Specialite, Personnel_categorie, Vacation, PersonnelType
        )
        def_diplome, _ = Diplome.objects.get_or_create(
            diplome='N/A', defaults={'sigle': 'NA'}
        )
        def_spec, _ = Specialite.objects.get_or_create(
            specialite='N/A', defaults={'sigle': 'NA'}
        )
        def_cat, _ = Personnel_categorie.objects.get_or_create(
            categorie='Administratif', defaults={'sigle': 'ADM'}
        )
        def_vac, _ = Vacation.objects.get_or_create(
            vacation='N/A', defaults={'sigle': 'NA'}
        )
        def_type, _ = PersonnelType.objects.get_or_create(
            type='Administrateur', defaults={'sigle': 'Admin'}
        )

        # Générer un username unique
        username = email.split('@')[0].lower().replace('.', '_')
        base_username = username
        counter = 1
        while Personnel.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        # Créer via SQL direct (managed=False)
        with connections['default'].cursor() as cur:
            ts = int(time.time())
            matricule = f"M_{etab_id}_{ts}"

            cur.execute("""
                INSERT INTO personnel (
                    username, email, password_hash, nom, prenom, matricule,
                    genre, id_etablissement, id_diplome_id, id_specialite_id,
                    id_categorie_id, id_vacation_id, id_personnel_type_id,
                    isUser, is_verified, en_fonction, email_verified, phone_verified,
                    telephone, date_creation
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    1, 1, 1, 0, 0,
                    %s, CURDATE()
                )
            """, [
                username, email.lower(), '', 'Admin' if is_super else '', '',
                matricule, 'M', etab_id,
                def_diplome.id_diplome, def_spec.id_specialite,
                def_cat.id_personnel_category, def_vac.id_vacation,
                def_type.id_type_personnel,
                hub_telephone or '',
            ])
            new_id = cur.lastrowid
            # Fix matricule
            final_matricule = f"M_{etab_id}_{new_id}"
            cur.execute("UPDATE personnel SET matricule=%s WHERE id_personnel=%s", [final_matricule, new_id])

        personnel = Personnel.objects.get(id_personnel=new_id)

    # 2. Set password if provided
    if password and not personnel.has_usable_password():
        personnel.set_password(password)
        with connections['default'].cursor() as cur:
            cur.execute(
                "UPDATE personnel SET password_hash=%s WHERE id_personnel=%s",
                [personnel.password_hash, personnel.id_personnel]
            )

    # 3. Garantir isUser, is_verified, en_fonction
    if not personnel.isUser or not personnel.is_verified or not personnel.en_fonction:
        with connections['default'].cursor() as cur:
            cur.execute(
                "UPDATE personnel SET isUser=1, is_verified=1, en_fonction=1 WHERE id_personnel=%s",
                [personnel.id_personnel]
            )
        personnel.isUser = True
        personnel.is_verified = True
        personnel.en_fonction = True

    # 4. Créer user_module
    annee = Annee.objects.order_by('-annee').first()
    annee_id = annee.id_annee if annee else 1

    if is_super:
        all_modules = Module.objects.all()
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
    else:
        admin_mod = Module.objects.filter(id_module=1).first()
        if admin_mod:
            um, created = UserModule.objects.get_or_create(
                user=personnel,
                module=admin_mod,
                id_etablissement=etab_id,
                defaults={
                    'id_annee_id': annee_id,
                    'is_active': True,
                }
            )
            if not created and not um.is_active:
                um.is_active = True
                um.save()

    return personnel


# Rétro-compatibilité
def _auto_provision_super_admin(email, etab_id, password=None):
    """Wrapper rétro-compatible."""
    return _auto_provision_hub_user(email, etab_id, hub_info=None, is_super=True, password=password)


@csrf_exempt
@require_http_methods(["POST"])
def check_email(request):
    """
    Étape 1: Vérifie si un email existe dans personnel.
    Si introuvable → cherche dans le Hub (admin_users + admin_email) et auto-crée si match.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'success': False, 'error': 'Email requis'}, status=400)

        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')

        # Chercher dans le spoke (personnel)
        personnel = None
        try:
            personnel = Personnel.objects.get(email__iexact=email)
        except Personnel.DoesNotExist:
            pass
        except Personnel.MultipleObjectsReturned:
            # Prendre celui de l'établissement courant
            if etab_id:
                personnel = Personnel.objects.filter(email__iexact=email, id_etablissement=etab_id).first()
            if not personnel:
                personnel = Personnel.objects.filter(email__iexact=email).first()

        # Si introuvable dans le spoke → chercher dans le Hub
        is_hub_user = False
        is_super = False
        if personnel is None:
            found, is_super, hub_info = _check_hub_user(email, etab_id)
            if found:
                is_hub_user = True
                personnel = _auto_provision_hub_user(
                    email, etab_id, hub_info=hub_info, is_super=is_super
                )
            else:
                return JsonResponse({
                    'success': True,
                    'exists': False,
                    'validated': False,
                    'has_password': False,
                })
        else:
            # L'utilisateur existe dans le spoke — vérifier s'il est aussi dans le Hub
            found, is_super, hub_info = _check_hub_user(email, etab_id)
            if found:
                is_hub_user = True
                _auto_provision_hub_user(
                    email, etab_id, hub_info=hub_info, is_super=is_super
                )
                personnel.refresh_from_db()

        # Si pas utilisateur Hub → checks normaux
        if not is_hub_user:
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

        has_password = personnel.has_usable_password()

        return JsonResponse({
            'success': True,
            'exists': True,
            'validated': personnel.is_verified or is_hub_user,
            'has_password': has_password,
            'multiple_accounts': False,
            'accounts': [],
            'user': {
                'id': personnel.id_personnel,
                'email': personnel.email or '',
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
    """Envoie un code OTP par email ou SMS au personnel."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        method = data.get('method', 'EMAIL').upper()

        if not email:
            return JsonResponse({'success': False, 'error': 'Email requis'}, status=400)

        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')

        # Vérifier que le personnel existe
        personnel = None
        if etab_id:
            personnel = Personnel.objects.filter(email__iexact=email, id_etablissement=etab_id).first()
        if not personnel:
            personnel = Personnel.objects.filter(email__iexact=email).first()
        if not personnel:
            return JsonResponse({'success': False, 'error': 'Aucun compte trouvé avec cet email.'}, status=404)

        # Générer le code OTP (6 chiffres)
        import random
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Stocker en session
        import time as _time
        request.session['_otp_code'] = code
        request.session['_otp_type'] = method
        request.session['_otp_expires'] = _time.time() + 600  # 10 min
        request.session['_otp_attempts'] = 0
        request.session['_otp_email'] = email

        # Envoyer le code
        if method == 'EMAIL':
            try:
                from MonEcole_app.email_service import send_brevo_email
                result = send_brevo_email(
                    to_emails=[email],
                    subject='MonEcole - Code de vérification',
                    html_content=f'''
                        <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px">
                            <h2 style="color:#667eea;text-align:center">MonEcole</h2>
                            <p>Votre code de vérification est :</p>
                            <div style="text-align:center;margin:20px 0">
                                <span style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#667eea;background:#f0f0ff;padding:12px 24px;border-radius:8px">{code}</span>
                            </div>
                            <p style="color:#666;font-size:14px">Ce code expire dans 10 minutes. Si vous n'avez pas demandé ce code, ignorez cet email.</p>
                        </div>
                    ''',
                    text_content=f'Votre code de vérification MonEcole est : {code}\n\nCe code expire dans 10 minutes.',
                )
                if not result.get('success'):
                    import sys
                    print(f"[OTP] Brevo send failed: {result}", file=sys.stderr, flush=True)
            except Exception as mail_err:
                import traceback, sys
                traceback.print_exc()
                print(f"[OTP] Email send error: {mail_err}", file=sys.stderr, flush=True)

        elif method == 'SMS':
            # Envoi par SMS via Twilio Messaging Service
            phone = str(personnel.telephone).strip() if personnel.telephone else ''
            if not phone:
                return JsonResponse({'success': False, 'error': 'Aucun numéro de téléphone enregistré.'}, status=400)

            # Normaliser le numéro (ajouter + si absent)
            if not phone.startswith('+'):
                phone = '+' + phone

            # Masquer pour affichage
            masked_phone = phone[:4] + '****' + phone[-2:] if len(phone) > 6 else phone

            try:
                import urllib.request
                import urllib.parse
                import urllib.error
                import base64
                import sys

                from django.conf import settings as _settings
                sid = getattr(_settings, 'TWILIO_ACCOUNT_SID', '')
                token = getattr(_settings, 'TWILIO_AUTH_TOKEN', '')
                from_number = getattr(_settings, 'TWILIO_PHONE_NUMBER', '')

                if not sid or not token or not from_number:
                    return JsonResponse({'success': False, 'error': 'Service SMS non configuré.'}, status=500)

                url = f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
                msg_body = f'MonEcole - Votre code de vérification est : {code} (expire dans 10 min)'
                post_data = urllib.parse.urlencode({
                    'From': from_number,
                    'To': phone,
                    'Body': msg_body,
                }).encode('utf-8')

                # Auth Basic
                credentials = base64.b64encode(f'{sid}:{token}'.encode()).decode()
                req = urllib.request.Request(url, data=post_data, method='POST')
                req.add_header('Authorization', f'Basic {credentials}')
                req.add_header('Content-Type', 'application/x-www-form-urlencoded')

                try:
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        resp_body = resp.read().decode('utf-8', errors='replace')
                        print(f"[OTP-SMS] Twilio OK ({resp.getcode()}): {resp_body[:300]}", file=sys.stderr, flush=True)
                except urllib.error.HTTPError as http_err:
                    err_body = http_err.read().decode('utf-8', errors='replace')
                    print(f"[OTP-SMS] Twilio HTTP Error {http_err.code}: {err_body[:500]}", file=sys.stderr, flush=True)
                except urllib.error.URLError as url_err:
                    print(f"[OTP-SMS] Twilio URL Error: {url_err.reason}", file=sys.stderr, flush=True)

            except Exception as sms_err:
                import traceback, sys
                traceback.print_exc()
                print(f"[OTP-SMS] Send error: {sms_err}", file=sys.stderr, flush=True)

            return JsonResponse({
                'success': True,
                'token': 'session',
                'phone': masked_phone,
                'message': f'Un code de vérification a été envoyé par SMS au {masked_phone}.',
            })

        return JsonResponse({
            'success': True,
            'token': 'session',
            'message': f'Un code de vérification a été envoyé à votre email.',
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_otp(request):
    """Vérifie le code OTP saisi par l'utilisateur."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()

        if not code or len(code) != 6:
            return JsonResponse({'success': False, 'error': 'Code à 6 chiffres requis.'}, status=400)

        # Vérifier le code en session
        stored_code = request.session.get('_otp_code')
        otp_expires = request.session.get('_otp_expires', 0)

        if not stored_code:
            return JsonResponse({'success': False, 'error': 'Aucun code en attente. Demandez un nouveau code.'}, status=400)

        import time as _time
        if _time.time() > otp_expires:
            for k in ('_otp_code', '_otp_type', '_otp_expires', '_otp_attempts'):
                request.session.pop(k, None)
            return JsonResponse({'success': False, 'error': 'Code expiré. Demandez un nouveau code.'}, status=400)

        if code != stored_code:
            attempts = request.session.get('_otp_attempts', 0) + 1
            request.session['_otp_attempts'] = attempts
            if attempts >= 3:
                for k in ('_otp_code', '_otp_type', '_otp_expires', '_otp_attempts'):
                    request.session.pop(k, None)
                return JsonResponse({'success': False, 'error': 'Trop de tentatives. Demandez un nouveau code.'}, status=400)
            return JsonResponse({'success': False, 'error': f'Code incorrect. {3 - attempts} tentative(s) restante(s).'}, status=400)

        # Code correct — marquer comme vérifié
        request.session['_otp_verified'] = True
        request.session['_otp_verified_email'] = email

        return JsonResponse({
            'success': True,
            'token': 'session',
            'message': 'Code vérifié avec succès. Définissez votre mot de passe.',
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def set_password(request):
    """Définit le mot de passe après vérification OTP réussie."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not password or len(password) < 6:
            return JsonResponse({'success': False, 'error': 'Mot de passe minimum 6 caractères.'}, status=400)

        # Vérifier que l'OTP a été validé
        if not request.session.get('_otp_verified'):
            return JsonResponse({'success': False, 'error': 'Veuillez d\'abord vérifier votre code OTP.'}, status=403)

        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')

        # Trouver le personnel
        personnel = None
        if etab_id:
            personnel = Personnel.objects.filter(email__iexact=email, id_etablissement=etab_id).first()
        if not personnel:
            personnel = Personnel.objects.filter(email__iexact=email).first()
        if not personnel:
            return JsonResponse({'success': False, 'error': 'Personnel introuvable.'}, status=404)

        # Définir le mot de passe + marquer comme vérifié
        personnel.set_password(password)
        with connections['default'].cursor() as cur:
            cur.execute(
                "UPDATE personnel SET password_hash=%s, is_verified=1, email_verified=1, isUser=1 WHERE id_personnel=%s",
                [personnel.password_hash, personnel.id_personnel]
            )

        # Nettoyer la session OTP
        for k in ('_otp_code', '_otp_type', '_otp_expires', '_otp_attempts', '_otp_verified', '_otp_verified_email'):
            request.session.pop(k, None)

        # Créer la session de login
        request.session['personnel_id'] = personnel.id_personnel
        request.session['user_id'] = personnel.id_personnel
        request.session['user_email'] = personnel.email or ''
        request.session['_last_activity'] = time.time()
        request.session['_personnel_cached'] = True
        request.session['_personnel_email'] = personnel.email or ''
        request.session['_personnel_nom'] = personnel.nom or ''
        request.session['_personnel_prenom'] = personnel.prenom or ''
        request.session['_personnel_matricule'] = personnel.matricule or ''
        request.session['needs_verification'] = False
        request.session['email_verified'] = True

        # Charger les modules
        user_modules = _load_user_modules(request, personnel)

        return JsonResponse({
            'success': True,
            'redirect_url': get_redirect_url_for_user(user_modules) if user_modules else '/dashboard/',
            'message': 'Mot de passe défini avec succès.',
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """Connexion email + mot de passe via Personnel.
    Vérifie d'abord le Spoke, puis le Hub si nécessaire."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')

        # Chercher dans le spoke (personnel)
        personnel = None
        try:
            if etab_id:
                personnel = Personnel.objects.filter(email__iexact=email, id_etablissement=etab_id).first()
            if not personnel:
                personnel = Personnel.objects.filter(email__iexact=email).first()
        except Exception:
            pass

        # Si introuvable → chercher dans le Hub
        is_hub_user = False
        is_super = False
        hub_info = None
        if personnel is None:
            found, is_super, hub_info = _check_hub_user(email, etab_id)
            if found:
                is_hub_user = True
                personnel = _auto_provision_hub_user(
                    email, etab_id, hub_info=hub_info, is_super=is_super, password=password
                )
            else:
                return JsonResponse({'success': False, 'error': 'Identifiants incorrects'}, status=401)
        else:
            found, is_super, hub_info = _check_hub_user(email, etab_id)
            if found:
                is_hub_user = True
                _auto_provision_hub_user(
                    email, etab_id, hub_info=hub_info, is_super=is_super
                )
                personnel.refresh_from_db()

        # Checks normaux
        if not personnel.isUser or not personnel.en_fonction:
            return JsonResponse({'success': False, 'error': 'Compte non autorisé.'}, status=403)

        if not personnel.is_verified:
            masked = email[:2] + '***' + email[email.index('@')-1:] if '@' in email else email
            return JsonResponse({
                'success': False,
                'error': f"Votre email ({masked}) n'est pas encore vérifié. Veuillez vérifier votre boîte de réception pour récupérer le code de vérification.",
                'email_not_verified': True,
                'needs_otp': True,
            }, status=403)

        # Vérifier le mot de passe
        authenticated = personnel.check_password(password)

        # Si échec, essayer le mot de passe Hub
        if not authenticated and is_hub_user:
            hub_pw_hash = (hub_info or {}).get('password_hash', '')
            if hub_pw_hash and _verify_hub_password(hub_pw_hash, password):
                # Le mot de passe Hub est correct → sync dans personnel
                personnel.set_password(password)
                with connections['default'].cursor() as cur:
                    cur.execute(
                        "UPDATE personnel SET password_hash=%s WHERE id_personnel=%s",
                        [personnel.password_hash, personnel.id_personnel]
                    )
                authenticated = True
            elif not personnel.has_usable_password():
                # Premier login — définir le mot de passe
                personnel.set_password(password)
                with connections['default'].cursor() as cur:
                    cur.execute(
                        "UPDATE personnel SET password_hash=%s WHERE id_personnel=%s",
                        [personnel.password_hash, personnel.id_personnel]
                    )
                authenticated = True

        if not authenticated:
            return JsonResponse({'success': False, 'error': 'Identifiants incorrects'}, status=401)

        # Vérifier email_verified / phone_verified AVANT la session complète
        email_verified = bool(getattr(personnel, 'email_verified', 0))
        phone_verified = bool(getattr(personnel, 'phone_verified', 0))
        needs_verification = not email_verified and not phone_verified

        if needs_verification:
            # Créer une session limitée — accès uniquement à la page de vérification
            request.session.flush()
            request.session['personnel_id'] = personnel.id_personnel
            request.session['user_email'] = personnel.email or ''
            request.session['_personnel_phone'] = str(personnel.telephone) if personnel.telephone else ''
            request.session['needs_verification'] = True
            request.session['_last_activity'] = time.time()

            return JsonResponse({
                'success': True,
                'needs_contact_verification': True,
                'redirect_url': '/login/?step=verify',
                'email': personnel.email or '',
                'phone': str(personnel.telephone)[:4] + '****' if personnel.telephone else '',
                'email_verified': False,
                'phone_verified': False,
            })

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

        # ── Créer la session COMPLÈTE (compte vérifié) ──
        request.session.flush()  # Clean start
        request.session['personnel_id'] = personnel.id_personnel
        request.session['user_id'] = personnel.id_personnel  # Rétro-compat
        request.session['user_email'] = personnel.email or ''
        request.session['_last_activity'] = time.time()
        request.session['_personnel_cached'] = True
        request.session['_personnel_email'] = personnel.email or ''
        request.session['_personnel_nom'] = personnel.nom or ''
        request.session['_personnel_prenom'] = personnel.prenom or ''
        request.session['_personnel_matricule'] = personnel.matricule or ''
        request.session['needs_verification'] = False
        if is_super:
            request.session['is_super_admin'] = True

        # Mettre à jour last_login
        personnel.update_last_login()

        # Charger les modules
        user_modules = _load_user_modules(request, personnel)

        request.session['email_verified'] = email_verified
        request.session['phone_verified'] = phone_verified

        response_data = {
            'success': True,
            'redirect_url': get_redirect_url_for_user(user_modules),
            'modules': user_modules,
            'user': {
                'email': personnel.email or '',
                'last_name': personnel.nom or '',
                'first_name': personnel.prenom or '',
            },
            'needs_contact_verification': False,
            'email_verified': email_verified,
            'phone_verified': phone_verified,
        }

        return JsonResponse(response_data)

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
    personnel_id = request.session.get('personnel_id')
    if not personnel_id:
        return JsonResponse({'authenticated': False}, status=401)

    try:
        personnel = Personnel.objects.get(id_personnel=personnel_id)
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': personnel.id_personnel,
                'email': personnel.email or '',
                'first_name': personnel.prenom or '',
                'last_name': personnel.nom or '',
                'matricule': personnel.matricule,
            }
        })
    except Personnel.DoesNotExist:
        return JsonResponse({'authenticated': False}, status=401)


def require_auth(view_func):
    """Décorateur pour exiger une authentification."""
    def wrapper(request, *args, **kwargs):
        personnel_id = request.session.get('personnel_id')
        if not personnel_id:
            return JsonResponse({'error': 'Non authentifié'}, status=401)
        try:
            request.personnel = Personnel.objects.get(id_personnel=personnel_id)
        except Personnel.DoesNotExist:
            return JsonResponse({'error': 'Compte non configuré'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


@csrf_exempt
@require_http_methods(["POST"])
def verify_contact(request):
    """
    API pour vérifier/confirmer les contacts (email ou téléphone) via code OTP.
    
    Flow :
    1. Frontend envoie {type: 'email'|'phone', code: '123456'}
    2. On vérifie le code OTP stocké en session
    3. Si valide → on marque email_verified=1 ou phone_verified=1 dans personnel
    4. On déverrouille la session (needs_verification = False)
    """
    personnel_id = request.session.get('personnel_id')
    if not personnel_id:
        return JsonResponse({'success': False, 'error': 'Non authentifié'}, status=401)

    try:
        data = json.loads(request.body)
        verify_type = data.get('type', 'email')  # 'email' ou 'phone'
        code = data.get('code', '').strip()
        
        # Aussi accepter la vérification directe (sans OTP) pour la mise à jour initiale
        email = data.get('email', '').strip()
        telephone = data.get('telephone', '').strip()
        direct_update = data.get('direct_update', False)

        if direct_update:
            # Mode mise à jour directe (premier setup — pas de code OTP requis)
            if not email:
                return JsonResponse({'success': False, 'error': 'Email requis'}, status=400)
            
            with connections['default'].cursor() as cur:
                cur.execute("""
                    UPDATE personnel
                    SET email = %s,
                        telephone = %s,
                        email_verified = 1,
                        phone_verified = CASE WHEN %s != '' THEN 1 ELSE 0 END
                    WHERE id_personnel = %s
                """, [email, telephone or None, telephone, personnel_id])
            
            # Débloquer la session
            request.session['email_verified'] = True
            request.session['phone_verified'] = bool(telephone)
            request.session['user_email'] = email
            request.session['_personnel_email'] = email
            request.session['_personnel_cached'] = True
            request.session['needs_verification'] = False
            
            return JsonResponse({
                'success': True,
                'message': 'Contacts vérifiés avec succès.',
                'email_verified': True,
                'phone_verified': bool(telephone),
            })

        # Mode vérification par OTP
        if not code or len(code) != 6:
            return JsonResponse({'success': False, 'error': 'Code de vérification requis (6 chiffres)'}, status=400)

        # Vérifier le code OTP en session
        stored_code = request.session.get('_otp_code')
        stored_type = request.session.get('_otp_type')
        otp_expires = request.session.get('_otp_expires', 0)

        if not stored_code:
            return JsonResponse({'success': False, 'error': 'Aucun code de vérification en attente. Veuillez en demander un nouveau.'}, status=400)

        import time as _time
        if _time.time() > otp_expires:
            # Nettoyer
            for k in ('_otp_code', '_otp_type', '_otp_expires'):
                request.session.pop(k, None)
            return JsonResponse({'success': False, 'error': 'Code expiré. Veuillez en demander un nouveau.'}, status=400)

        if code != stored_code:
            # Incrémenter les tentatives
            attempts = request.session.get('_otp_attempts', 0) + 1
            request.session['_otp_attempts'] = attempts
            if attempts >= 3:
                for k in ('_otp_code', '_otp_type', '_otp_expires', '_otp_attempts'):
                    request.session.pop(k, None)
                return JsonResponse({'success': False, 'error': 'Trop de tentatives. Veuillez demander un nouveau code.'}, status=400)
            return JsonResponse({'success': False, 'error': f'Code incorrect. {3 - attempts} tentative(s) restante(s).'}, status=400)

        # Code correct → marquer comme vérifié
        with connections['default'].cursor() as cur:
            if verify_type == 'phone':
                cur.execute("UPDATE personnel SET phone_verified = 1 WHERE id_personnel = %s", [personnel_id])
                request.session['phone_verified'] = True
            else:
                cur.execute("UPDATE personnel SET email_verified = 1 WHERE id_personnel = %s", [personnel_id])
                request.session['email_verified'] = True

        # Nettoyer les données OTP de session
        for k in ('_otp_code', '_otp_type', '_otp_expires', '_otp_attempts'):
            request.session.pop(k, None)

        # Débloquer la session
        request.session['needs_verification'] = False
        request.session['_personnel_cached'] = True

        return JsonResponse({
            'success': True,
            'message': f"{'Téléphone' if verify_type == 'phone' else 'Email'} vérifié avec succès.",
            'email_verified': request.session.get('email_verified', False),
            'phone_verified': request.session.get('phone_verified', False),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
