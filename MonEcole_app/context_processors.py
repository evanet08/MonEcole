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
