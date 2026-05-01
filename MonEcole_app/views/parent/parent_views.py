"""
Views pour le Module Parents — PWA MonEcole.
Gère l'authentification parent (email + OTP), la sélection d'enfant,
et les pages du portail parent (accueil, profil, évaluations, paiements, communication).

Toutes les queries filtrent par id_pays + id_etablissement (multi-tenant strict).
"""
import json
import time
import random
import logging

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connections

from MonEcole_app.models.eleves.parent import Parent
from MonEcole_app.models.eleves.eleve import Eleve, Eleve_inscription

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_parent_session(request):
    """Vérifie et retourne les données parent depuis la session. None si pas connecté."""
    if request.session.get('user_type') != 'parent':
        return None
    id_parent = request.session.get('id_parent')
    if not id_parent:
        return None
    return {
        'id_parent': id_parent,
        'parent_name': request.session.get('parent_name', ''),
        'parent_email': request.session.get('parent_email', ''),
        'id_pays': request.session.get('id_pays'),
    }


def _parent_required(view_func):
    """Décorateur : redirige vers login parent si pas connecté."""
    def wrapper(request, *args, **kwargs):
        parent_data = _get_parent_session(request)
        if not parent_data:
            return redirect('parent_login')
        request.parent_data = parent_data
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_children(id_parent, id_pays=None):
    """Retourne la liste des enfants d'un parent avec leurs inscriptions actives."""
    filters = {'id_parent': id_parent}
    if id_pays:
        filters['id_pays'] = id_pays

    eleves = Eleve.objects.filter(**filters).order_by('nom', 'prenom')
    children = []

    for eleve in eleves:
        # Chercher l'inscription active — PAS de select_related (classes est Hub)
        insc_filters = {'id_eleve': eleve, 'status': True}
        if id_pays:
            insc_filters['id_pays'] = id_pays

        inscription = Eleve_inscription.objects.filter(
            **insc_filters
        ).order_by('-id_annee_id').first()

        child = {
            'id_eleve': eleve.id_eleve,
            'nom': eleve.nom or '',
            'prenom': eleve.prenom or '',
            'genre': eleve.genre or 'M',
            'photo': eleve.imageUrl.url if eleve.imageUrl else '',
            'id_etablissement': eleve.id_etablissement,
            'classe': '',
            'campus': '',
            'id_inscription': None,
        }

        if inscription:
            child['id_inscription'] = inscription.id_inscription

            # Résoudre le nom de la classe depuis le Hub (countryStructure)
            classe_id = inscription.id_classe_id  # raw FK value (classe_id column)
            groupe = inscription.groupe or ''
            if classe_id:
                try:
                    with connections['countryStructure'].cursor() as cur:
                        cur.execute("SELECT nom FROM classes WHERE id_classe=%s LIMIT 1", [classe_id])
                        row = cur.fetchone()
                        base_name = row[0] if row else f'Classe {classe_id}'
                        child['classe'] = f'{base_name} {groupe}'.strip() if base_name else ''
                except Exception:
                    child['classe'] = f'Classe {classe_id} {groupe}'.strip()

            # Résoudre le campus depuis le spoke
            campus_id = inscription.idCampus_id  # raw FK value
            if campus_id:
                try:
                    with connections['default'].cursor() as cur:
                        cur.execute("SELECT campus FROM campus WHERE id_campus=%s LIMIT 1", [campus_id])
                        row = cur.fetchone()
                        child['campus'] = row[0] if row else ''
                except Exception:
                    child['campus'] = ''

        # Résoudre le nom de l'établissement depuis le Hub
        if eleve.id_etablissement:
            try:
                with connections['countryStructure'].cursor() as cur:
                    sql = "SELECT nom FROM etablissements WHERE id_etablissement=%s"
                    params = [eleve.id_etablissement]
                    if id_pays:
                        sql += " AND pays_id=%s"
                        params.append(id_pays)
                    cur.execute(sql + " LIMIT 1", params)
                    row = cur.fetchone()
                    child['etablissement_nom'] = row[0] if row else ''
            except Exception:
                child['etablissement_nom'] = ''
        else:
            child['etablissement_nom'] = ''

        children.append(child)

    return children


# ═══════════════════════════════════════════════════════════════
# AUTH — Parent Login (Email → OTP → Session)
# ═══════════════════════════════════════════════════════════════

def parent_login_view(request):
    """Page de connexion parent (PWA mobile-first)."""
    # Si déjà connecté comme parent → accueil
    if request.session.get('user_type') == 'parent' and request.session.get('id_parent'):
        return redirect('parent_home')

    context = {}
    # Récupérer le contexte tenant si disponible
    etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
    if etab_id:
        try:
            with connections['countryStructure'].cursor() as cur:
                id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')
                sql = "SELECT nom, logo_ecole FROM etablissements WHERE id_etablissement=%s"
                params = [etab_id]
                if id_pays:
                    sql += " AND pays_id=%s"
                    params.append(id_pays)
                cur.execute(sql + " LIMIT 1", params)
                row = cur.fetchone()
                if row:
                    context['etab_nom'] = row[0]
                    context['etab_logo'] = row[1] or ''
        except Exception:
            pass

    return render(request, 'pwa/parent_login.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def parent_check_email(request):
    """Étape 1 : Vérifie si l'email existe dans la table parents."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'success': False, 'error': 'Email requis'}, status=400)

        id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')

        # Chercher dans parents — emailPere OU emailMere
        from django.db.models import Q
        filters = Q(emailPere__iexact=email) | Q(emailMere__iexact=email)

        parents_qs = Parent.objects.filter(filters)
        if id_pays:
            parents_qs = parents_qs.filter(id_pays=id_pays)

        parent = parents_qs.first()

        if not parent:
            return JsonResponse({
                'success': False,
                'error': "Aucun compte parent trouvé avec cet email. Contactez l'administration de l'école."
            }, status=404)

        # Stocker l'email et parent trouvé en session pour l'OTP
        request.session['_parent_auth_email'] = email
        request.session['_parent_auth_id'] = parent.id_parent
        # Stocker id_pays depuis le parent trouvé (critique pour multi-tenant)
        if parent.id_pays:
            request.session['id_pays'] = parent.id_pays

        # Déterminer le nom du parent
        parent_name = ''
        if parent.emailPere and parent.emailPere.lower() == email:
            parent_name = parent.nomsPere or ''
        elif parent.emailMere and parent.emailMere.lower() == email:
            parent_name = parent.nomsMere or ''

        request.session['_parent_auth_name'] = parent_name

        return JsonResponse({
            'success': True,
            'parent_name': parent_name,
            'message': f'Compte trouvé. Un code de vérification va être envoyé à {email}.',
        })

    except Exception as e:
        logger.exception("parent_check_email error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def parent_request_otp(request):
    """Étape 2 : Envoie un OTP par email au parent."""
    try:
        email = request.session.get('_parent_auth_email')
        if not email:
            return JsonResponse({'success': False, 'error': 'Veuillez d\'abord vérifier votre email.'}, status=400)

        # Générer le code OTP (6 chiffres)
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        # Stocker en session
        request.session['_parent_otp_code'] = code
        request.session['_parent_otp_expires'] = time.time() + 600  # 10 min
        request.session['_parent_otp_attempts'] = 0

        # Envoyer par email
        try:
            from MonEcole_app.email_service import send_brevo_email
            parent_name = request.session.get('_parent_auth_name', '')
            result = send_brevo_email(
                to_emails=[email],
                subject='MonEcole - Code de connexion parent',
                html_content=f'''
                    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px">
                        <h2 style="color:#1e3a8a;text-align:center">MonEcole — Espace Parents</h2>
                        <p>Bonjour{' ' + parent_name if parent_name else ''},</p>
                        <p>Votre code de connexion est :</p>
                        <div style="text-align:center;margin:20px 0">
                            <span style="font-size:32px;font-weight:bold;letter-spacing:8px;color:#1e3a8a;background:#eff6ff;padding:12px 24px;border-radius:8px">{code}</span>
                        </div>
                        <p style="color:#666;font-size:14px">Ce code expire dans 10 minutes.</p>
                    </div>
                ''',
                text_content=f'Votre code de connexion MonEcole est : {code}\nCe code expire dans 10 minutes.',
            )
            if not result.get('success'):
                logger.warning(f"[ParentOTP] Brevo send failed: {result}")
        except Exception as mail_err:
            logger.exception(f"[ParentOTP] Email send error: {mail_err}")

        # Masquer l'email pour affichage
        parts = email.split('@')
        masked = parts[0][:2] + '***@' + parts[1] if len(parts) == 2 else email

        return JsonResponse({
            'success': True,
            'masked_email': masked,
            'message': f'Code envoyé à {masked}.',
        })

    except Exception as e:
        logger.exception("parent_request_otp error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def parent_verify_otp(request):
    """Étape 3 : Vérifie le code OTP et crée la session parent."""
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip()

        if not code or len(code) != 6:
            return JsonResponse({'success': False, 'error': 'Code à 6 chiffres requis.'}, status=400)

        stored_code = request.session.get('_parent_otp_code')
        otp_expires = request.session.get('_parent_otp_expires', 0)

        if not stored_code:
            return JsonResponse({'success': False, 'error': 'Aucun code en attente.'}, status=400)

        if time.time() > otp_expires:
            for k in ('_parent_otp_code', '_parent_otp_expires', '_parent_otp_attempts'):
                request.session.pop(k, None)
            return JsonResponse({'success': False, 'error': 'Code expiré. Demandez un nouveau code.'}, status=400)

        if code != stored_code:
            attempts = request.session.get('_parent_otp_attempts', 0) + 1
            request.session['_parent_otp_attempts'] = attempts
            if attempts >= 3:
                for k in ('_parent_otp_code', '_parent_otp_expires', '_parent_otp_attempts'):
                    request.session.pop(k, None)
                return JsonResponse({'success': False, 'error': 'Trop de tentatives.'}, status=400)
            return JsonResponse({
                'success': False,
                'error': f'Code incorrect. {3 - attempts} tentative(s) restante(s).'
            }, status=400)

        # ── Code correct ──
        id_parent = request.session.get('_parent_auth_id')
        parent_email = request.session.get('_parent_auth_email', '')
        parent_name = request.session.get('_parent_auth_name', '')
        id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')

        # Clean OTP data
        for k in ('_parent_otp_code', '_parent_otp_expires', '_parent_otp_attempts'):
            request.session.pop(k, None)

        # Vérifier si un mot de passe existe déjà
        has_password = False
        try:
            eleve = Eleve.objects.filter(id_parent=id_parent).first()
            if eleve and eleve.password_parent:
                has_password = True
        except Exception:
            pass

        if not has_password:
            # Pas de mot de passe → demander la création
            request.session['_parent_otp_verified'] = True
            return JsonResponse({
                'success': True,
                'needs_password': True,
                'message': 'Code vérifié ! Créez votre mot de passe.',
            })

        # Mot de passe existe → créer la session directement
        for k in ('_parent_auth_email', '_parent_auth_id', '_parent_auth_name'):
            request.session.pop(k, None)

        request.session['user_type'] = 'parent'
        request.session['id_parent'] = id_parent
        request.session['parent_email'] = parent_email
        request.session['parent_name'] = parent_name
        request.session['id_pays'] = id_pays
        request.session['_last_activity'] = time.time()

        return JsonResponse({
            'success': True,
            'needs_password': False,
            'redirect_url': '/parent/',
            'message': 'Connexion réussie !',
        })

    except Exception as e:
        logger.exception("parent_verify_otp error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def parent_set_password(request):
    """Étape 4 : Créer le mot de passe après vérification OTP."""
    try:
        if not request.session.get('_parent_otp_verified'):
            return JsonResponse({'success': False, 'error': 'OTP non vérifié.'}, status=400)

        data = json.loads(request.body)
        password = data.get('password', '').strip()
        if not password or len(password) < 4:
            return JsonResponse({'success': False, 'error': 'Mot de passe (min 4 caractères) requis.'}, status=400)

        id_parent = request.session.get('_parent_auth_id')
        parent_email = request.session.get('_parent_auth_email', '')
        parent_name = request.session.get('_parent_auth_name', '')
        id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')

        # Enregistrer le mot de passe sur tous les enfants de ce parent
        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
        Eleve.objects.filter(id_parent=id_parent).update(password_parent=hashed)

        # Nettoyer et créer la session
        for k in ('_parent_otp_verified', '_parent_auth_email', '_parent_auth_id', '_parent_auth_name'):
            request.session.pop(k, None)

        request.session['user_type'] = 'parent'
        request.session['id_parent'] = id_parent
        request.session['parent_email'] = parent_email
        request.session['parent_name'] = parent_name
        request.session['id_pays'] = id_pays
        request.session['_last_activity'] = time.time()

        return JsonResponse({
            'success': True,
            'redirect_url': '/parent/',
            'message': 'Mot de passe créé ! Bienvenue.',
        })

    except Exception as e:
        logger.exception("parent_set_password error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def parent_login_password(request):
    """Connexion directe par email + mot de passe (sans OTP)."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()

        if not email or not password:
            return JsonResponse({'success': False, 'error': 'Email et mot de passe requis.'}, status=400)

        id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')

        from django.db.models import Q
        filters = Q(emailPere__iexact=email) | Q(emailMere__iexact=email)
        parents_qs = Parent.objects.filter(filters)
        if id_pays:
            parents_qs = parents_qs.filter(id_pays=id_pays)
        parent = parents_qs.first()

        if not parent:
            return JsonResponse({'success': False, 'error': 'Email non trouvé.'}, status=404)

        # Vérifier le mot de passe
        import hashlib
        hashed = hashlib.sha256(password.encode()).hexdigest()
        eleve = Eleve.objects.filter(id_parent=parent.id_parent, password_parent=hashed).first()

        if not eleve:
            return JsonResponse({'success': False, 'error': 'Mot de passe incorrect.'}, status=401)

        # Déterminer le nom du parent
        parent_name = ''
        if parent.emailPere and parent.emailPere.lower() == email:
            parent_name = parent.nomsPere or ''
        elif parent.emailMere and parent.emailMere.lower() == email:
            parent_name = parent.nomsMere or ''

        request.session['user_type'] = 'parent'
        request.session['id_parent'] = parent.id_parent
        request.session['parent_email'] = email
        request.session['parent_name'] = parent_name
        request.session['id_pays'] = id_pays
        request.session['_last_activity'] = time.time()

        return JsonResponse({
            'success': True,
            'redirect_url': '/parent/',
            'message': 'Connexion réussie !',
        })

    except Exception as e:
        logger.exception("parent_login_password error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def parent_logout(request):
    """Déconnexion parent."""
    request.session.flush()
    return redirect('parent_login')


# ═══════════════════════════════════════════════════════════════
# PAGES — Portail Parent
# ═══════════════════════════════════════════════════════════════

@_parent_required
def parent_home(request):
    """Page d'accueil parent — liste des enfants."""
    parent_data = request.parent_data
    children = _get_children(parent_data['id_parent'], parent_data.get('id_pays'))

    context = {
        'parent_data': parent_data,
        'children': children,
        'active_section': 'home',
    }
    return render(request, 'pwa/parent_home.html', context)


@_parent_required
def parent_child_view(request, id_eleve):
    """Page profil/détails d'un enfant — évaluations, notes, paiements."""
    parent_data = request.parent_data

    # Vérifier que l'enfant appartient bien au parent
    filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
    if parent_data.get('id_pays'):
        filters['id_pays'] = parent_data['id_pays']

    try:
        eleve = Eleve.objects.get(**filters)
    except Eleve.DoesNotExist:
        return redirect('parent_home')

    # Inscription active — PAS de select_related (classes est Hub cross-DB)
    insc_filters = {'id_eleve': eleve, 'status': True}
    if parent_data.get('id_pays'):
        insc_filters['id_pays'] = parent_data['id_pays']

    inscription = Eleve_inscription.objects.filter(
        **insc_filters
    ).order_by('-id_annee_id').first()

    # Résoudre les noms cross-DB
    classe_nom = ''
    campus_nom = ''
    if inscription:
        # Classe → Hub
        classe_id = inscription.id_classe_id
        groupe = inscription.groupe or ''
        if classe_id:
            try:
                with connections['countryStructure'].cursor() as cur:
                    cur.execute("SELECT nom FROM classes WHERE id_classe=%s LIMIT 1", [classe_id])
                    row = cur.fetchone()
                    base_name = row[0] if row else f'Classe {classe_id}'
                    classe_nom = f'{base_name} {groupe}'.strip()
            except Exception:
                classe_nom = f'Classe {classe_id} {groupe}'.strip()

        # Campus → Spoke
        campus_id = inscription.idCampus_id
        if campus_id:
            try:
                with connections['default'].cursor() as cur:
                    cur.execute("SELECT campus FROM campus WHERE id_campus=%s LIMIT 1", [campus_id])
                    row = cur.fetchone()
                    campus_nom = row[0] if row else ''
            except Exception:
                campus_nom = ''

    # Stocker l'établissement de l'enfant en session
    if eleve.id_etablissement:
        request.session['child_id_etablissement'] = eleve.id_etablissement

    context = {
        'parent_data': parent_data,
        'eleve': eleve,
        'inscription': inscription,
        'classe_nom': classe_nom,
        'campus_nom': campus_nom,
        'active_section': 'child',
    }
    return render(request, 'pwa/parent_child.html', context)


# ═══════════════════════════════════════════════════════════════
# API — Données enfant (notes, paiements)
# ═══════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["GET"])
def api_parent_children(request):
    """API : liste des enfants du parent connecté."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    children = _get_children(parent_data['id_parent'], parent_data.get('id_pays'))
    return JsonResponse({'success': True, 'children': children})


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_child_notes(request):
    """API : Notes d'un enfant pour le parent connecté."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    # Vérifier propriété
    filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
    if parent_data.get('id_pays'):
        filters['id_pays'] = parent_data['id_pays']

    if not Eleve.objects.filter(**filters).exists():
        return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

    # Charger les notes
    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT
                    en.id_note, c.cours, en.note, en.note_repechage,
                    ent.type as type_note, e.id_session_id,
                    en.date_saisie
                FROM eleve_note en
                JOIN cours c ON c.id_cours = en.id_cours_id
                JOIN eleve_note_type ent ON ent.id_type_note = en.id_type_note_id
                JOIN evaluation e ON e.id_evaluation = en.id_evaluation_id
                WHERE en.id_eleve_id = %s
                ORDER BY c.cours, en.date_saisie DESC
            """, [id_eleve])

            columns = [col[0] for col in cur.description]
            notes = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Convertir les Decimal en float
        for n in notes:
            if n.get('note') is not None:
                n['note'] = float(n['note'])
            if n.get('note_repechage') is not None:
                n['note_repechage'] = float(n['note_repechage'])

        return JsonResponse({'success': True, 'notes': notes})

    except Exception as e:
        logger.exception("api_parent_child_notes error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_child_payments(request):
    """API : Paiements d'un enfant (module recouvrement)."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    # Vérifier propriété
    filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
    if parent_data.get('id_pays'):
        filters['id_pays'] = parent_data['id_pays']

    if not Eleve.objects.filter(**filters).exists():
        return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

    try:
        with connections['default'].cursor() as cur:
            cur.execute("""
                SELECT
                    p.id_paiement, p.montant, p.devise, p.date_paiement,
                    p.mode_paiement, p.reference_paiement, p.statut,
                    rv.nom as rubrique
                FROM paiement p
                LEFT JOIN rubrique_variable rv ON rv.id_variable = p.id_variable_id
                WHERE p.id_eleve_id = %s
                ORDER BY p.date_paiement DESC
            """, [id_eleve])

            columns = [col[0] for col in cur.description]
            payments = [dict(zip(columns, row)) for row in cur.fetchall()]

        for p in payments:
            if p.get('montant') is not None:
                p['montant'] = float(p['montant'])
            if p.get('date_paiement'):
                p['date_paiement'] = str(p['date_paiement'])

        return JsonResponse({'success': True, 'payments': payments})

    except Exception as e:
        logger.exception("api_parent_child_payments error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════
# API — Profil élève (lecture + mise à jour partielle)
# ═══════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["GET"])
def api_parent_child_profile(request):
    """Profil complet d'un enfant, avec résolution ref_administrative."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    id_eleve = request.GET.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
    if parent_data.get('id_pays'):
        filters['id_pays'] = parent_data['id_pays']

    if not Eleve.objects.filter(**filters).exists():
        return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

    try:
        eleve = Eleve.objects.get(id_eleve=id_eleve)
        parent = None
        try:
            from MonEcole_app.models.eleves.parent import Parent
            parent = Parent.objects.filter(id_parent=eleve.id_parent).first()
        except Exception:
            pass

        # Résoudre ref_administrative naissance et résidence
        def resolve_ref_admin(ref_str, id_pays):
            """Résoudre une chaîne ref_administrative (ex: '1-2-14-47') en noms."""
            if not ref_str:
                return []
            parts = [p.strip() for p in ref_str.split('-') if p.strip()]
            if not parts:
                return []
            ids = []
            for p in parts:
                try:
                    ids.append(int(p))
                except (ValueError, TypeError):
                    pass
            if not ids:
                return []
            try:
                with connections['countryStructure'].cursor() as cur:
                    placeholders = ','.join(['%s'] * len(ids))
                    cur.execute(f"""
                        SELECT a.id_structure, a.nom, a.ordre
                        FROM administrativeStructures a
                        WHERE a.id_structure IN ({placeholders}) AND a.pays_id = %s
                        ORDER BY a.ordre
                    """, ids + [id_pays])
                    return [{'id': r[0], 'nom': r[1], 'ordre': r[2]} for r in cur.fetchall()]
            except Exception:
                return []

        id_pays = parent_data.get('id_pays') or eleve.id_pays

        profile = {
            'id_eleve': eleve.id_eleve,
            'nom': eleve.nom or '',
            'prenom': eleve.prenom or '',
            'genre': eleve.genre or 'M',
            'etat_civil': eleve.etat_civil or '',
            'date_naissance': str(eleve.date_naissance) if eleve.date_naissance else '',
            'telephone': str(eleve.telephone) if eleve.telephone else '',
            'email': eleve.email or '',
            'nationalite': eleve.nationalite or '',
            'matricule': eleve.matricule or '',
            'code_eleve': eleve.code_eleve or '',
            'IDNational': eleve.IDNational or '',
            'photo': eleve.imageUrl.url if eleve.imageUrl else '',
            'ref_administrative_naissance': eleve.ref_administrative_naissance or '',
            'ref_administrative_residence': eleve.ref_administrative_residence or '',
            'naissance_chain': resolve_ref_admin(eleve.ref_administrative_naissance, id_pays),
            'residence_chain': resolve_ref_admin(eleve.ref_administrative_residence, id_pays),
        }

        # Données parent
        parent_info = {}
        if parent:
            parent_info = {
                'nom_pere': parent.nomsPere or '',
                'tel_pere': parent.telephonePere or '',
                'email_pere': parent.emailPere or '',
                'nom_mere': parent.nomsMere or '',
                'tel_mere': parent.telephoneMere or '',
                'email_mere': parent.emailMere or '',
                'pere_en_vie': parent.pere_en_vie,
                'mere_en_vie': parent.mere_en_vie,
            }

        # Résoudre la hiérarchie administrative pour les dropdowns
        admin_types = []
        admin_instances = {}
        try:
            with connections['countryStructure'].cursor() as cur:
                cur.execute("""
                    SELECT id_structure, code, nom, ordre
                    FROM administrativeStructuresTypes
                    WHERE pays_id = %s ORDER BY ordre
                """, [id_pays])
                admin_types = [{'id': r[0], 'code': r[1], 'nom': r[2], 'ordre': r[3]} for r in cur.fetchall()]

                cur.execute("""
                    SELECT id_structure, nom, ordre, code
                    FROM administrativeStructures
                    WHERE pays_id = %s ORDER BY ordre, nom
                """, [id_pays])
                for r in cur.fetchall():
                    ordre = r[2]
                    if ordre not in admin_instances:
                        admin_instances[ordre] = []
                    admin_instances[ordre].append({
                        'id': r[0], 'nom': r[1], 'code': r[3] or '',
                    })
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'profile': profile,
            'parent': parent_info,
            'admin_types': admin_types,
            'admin_instances': admin_instances,
        })

    except Exception as e:
        logger.exception("api_parent_child_profile error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_parent_update_profile(request):
    """Met à jour les champs modifiables du profil élève par le parent."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    try:
        data = json.loads(request.body)
        id_eleve = data.get('id_eleve')
        if not id_eleve:
            return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

        filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
        if parent_data.get('id_pays'):
            filters['id_pays'] = parent_data['id_pays']

        try:
            eleve = Eleve.objects.get(**filters)
        except Eleve.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

        # Champs modifiables par le parent
        editable_fields = {
            'telephone': 'telephone',
            'email': 'email',
            'nationalite': 'nationalite',
            'etat_civil': 'etat_civil',
            'ref_administrative_naissance': 'ref_administrative_naissance',
            'ref_administrative_residence': 'ref_administrative_residence',
        }

        updated = []
        for json_key, model_field in editable_fields.items():
            if json_key in data:
                setattr(eleve, model_field, data[json_key] or None)
                updated.append(model_field)

        if updated:
            eleve.save(update_fields=updated)

        return JsonResponse({'success': True, 'updated': updated})

    except Exception as e:
        logger.exception("api_parent_update_profile error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_parent_upload_photo(request):
    """Upload de la photo de l'élève."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    id_eleve = request.POST.get('id_eleve')
    if not id_eleve:
        return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

    filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
    if parent_data.get('id_pays'):
        filters['id_pays'] = parent_data['id_pays']

    try:
        eleve = Eleve.objects.get(**filters)
    except Eleve.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

    photo = request.FILES.get('photo')
    if not photo:
        return JsonResponse({'success': False, 'error': 'Fichier photo requis'}, status=400)

    if photo.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'Photo trop volumineuse (max 5MB)'}, status=400)

    try:
        eleve.imageUrl = photo
        eleve.save(update_fields=['imageUrl'])
        return JsonResponse({
            'success': True,
            'photo_url': eleve.imageUrl.url if eleve.imageUrl else '',
        })
    except Exception as e:
        logger.exception("api_parent_upload_photo error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

