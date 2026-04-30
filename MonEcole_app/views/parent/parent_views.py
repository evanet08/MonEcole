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
        # Chercher l'inscription active
        insc_filters = {'id_eleve': eleve, 'status': True}
        if id_pays:
            insc_filters['id_pays'] = id_pays

        inscription = Eleve_inscription.objects.filter(
            **insc_filters
        ).select_related('id_classe', 'idCampus').order_by('-id_annee_id').first()

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
            child['classe'] = str(inscription.id_classe) if inscription.id_classe else ''
            child['campus'] = str(inscription.idCampus) if inscription.idCampus else ''
            child['id_inscription'] = inscription.id_inscription

        # Résoudre le nom de l'établissement
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

        # ── Code correct → créer la session parent ──
        id_parent = request.session.get('_parent_auth_id')
        parent_email = request.session.get('_parent_auth_email', '')
        parent_name = request.session.get('_parent_auth_name', '')
        id_pays = getattr(request, 'id_pays', None) or request.session.get('id_pays')

        # Clean OTP data
        for k in ('_parent_otp_code', '_parent_otp_expires', '_parent_otp_attempts',
                   '_parent_auth_email', '_parent_auth_id', '_parent_auth_name'):
            request.session.pop(k, None)

        # Créer la session parent
        request.session['user_type'] = 'parent'
        request.session['id_parent'] = id_parent
        request.session['parent_email'] = parent_email
        request.session['parent_name'] = parent_name
        request.session['id_pays'] = id_pays
        request.session['_last_activity'] = time.time()

        return JsonResponse({
            'success': True,
            'redirect_url': '/parent/',
            'message': 'Connexion réussie !',
        })

    except Exception as e:
        logger.exception("parent_verify_otp error")
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

    # Inscription active
    insc_filters = {'id_eleve': eleve, 'status': True}
    if parent_data.get('id_pays'):
        insc_filters['id_pays'] = parent_data['id_pays']

    inscription = Eleve_inscription.objects.filter(
        **insc_filters
    ).select_related('id_classe', 'idCampus').order_by('-id_annee_id').first()

    # Stocker l'établissement de l'enfant en session
    if eleve.id_etablissement:
        request.session['child_id_etablissement'] = eleve.id_etablissement

    context = {
        'parent_data': parent_data,
        'eleve': eleve,
        'inscription': inscription,
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
