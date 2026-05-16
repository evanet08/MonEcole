"""
Context processors pour injecter les données session dans tous les templates.
"""
from django.db import connections


def verification_status(request):
    """Injecte le statut de vérification email/téléphone dans le contexte template."""
    phone = request.session.get('_personnel_phone', '')
    email_verified = request.session.get('email_verified', False)
    phone_verified = request.session.get('phone_verified', False)

    # Si pas de téléphone en session, le charger depuis la DB
    personnel_id = request.session.get('personnel_id')
    if not phone and personnel_id:
        try:
            with connections['default'].cursor() as cur:
                cur.execute(
                    "SELECT telephone, email_verified, phone_verified FROM personnel WHERE id_personnel = %s",
                    [personnel_id]
                )
                row = cur.fetchone()
                if row:
                    phone = row[0] or ''
                    email_verified = bool(row[1])
                    phone_verified = bool(row[2])
                    # Cache en session
                    request.session['_personnel_phone'] = phone
                    request.session['email_verified'] = email_verified
                    request.session['phone_verified'] = phone_verified
        except Exception:
            pass

    return {
        'email_verified': email_verified,
        'phone_verified': phone_verified,
        'user_phone': phone,
    }


def activation_status(request):
    """
    Injecte le statut d'activation progressive dans tous les templates.
    Permet au frontend de :
    - Griser/bloquer les modules non autorisés dans la sidebar
    - Verrouiller les onglets Configuration si pas de campus
    - Afficher des messages explicatifs
    """
    # Essayer d'abord le statut attaché par le middleware
    status = getattr(request, 'activation_status', None)

    if status is None:
        # Fallback : calculer depuis le service
        try:
            from MonEcole_app.services.activation_service import get_cached_activation_status
            etab_id = getattr(request, 'id_etablissement', None) or request.session.get('id_etablissement')
            if etab_id:
                status = get_cached_activation_status(request)
        except Exception:
            pass

    if status is None:
        status = {
            'geo_complete': False,
            'campus_exists': False,
            'config_unlocked': False,
            'config_tabs_unlocked': False,
            'modules_allowed': ['administration'],
            'sections_allowed': ['dashboard', 'structure'],
            'blocking_reason': '',
        }

    return {
        'activation': status,
        'geo_complete': status.get('geo_complete', False),
        'campus_exists': status.get('campus_exists', False),
        'config_unlocked': status.get('config_unlocked', False),
        'config_tabs_unlocked': status.get('config_tabs_unlocked', False),
        'modules_allowed': status.get('modules_allowed', []),
        'sections_allowed': status.get('sections_allowed', []),
        'activation_blocking_reason': status.get('blocking_reason', ''),
    }
