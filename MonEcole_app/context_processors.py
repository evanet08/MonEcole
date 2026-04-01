"""
Context processors pour injecter les données session dans tous les templates.
"""


def verification_status(request):
    """Injecte le statut de vérification email/téléphone dans le contexte template."""
    return {
        'email_verified': request.session.get('email_verified', False),
        'phone_verified': request.session.get('phone_verified', False),
        'user_phone': request.session.get('_personnel_phone', ''),
    }
