"""
Service d'email Brevo pour MonEcole.
Utilise l'API HTTP Brevo (ex-Sendinblue) via urllib (stdlib Python).
Aucune dépendance externe — fonctionne partout.
Plan gratuit: 300 emails/jour.
"""
import json
import logging
import urllib.request
import urllib.error
import ssl

from django.conf import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'


def send_brevo_email(to_emails, subject, html_content=None, text_content=None,
                     from_email=None, from_name=None, fail_silently=True):
    """
    Envoie un email via l'API Brevo.

    Args:
        to_emails: list de dicts [{'email': '...', 'name': '...'}] ou list de str
        subject: sujet du mail
        html_content: contenu HTML (optionnel)
        text_content: contenu texte (optionnel, requis si pas de html)
        from_email: adresse expéditeur (défaut: settings.DEFAULT_FROM_EMAIL)
        from_name: nom expéditeur (défaut: settings.DEFAULT_FROM_NAME)
        fail_silently: si True, ne lève pas d'exception en cas d'erreur

    Returns:
        dict: {'success': bool, 'sent': int, 'failed': int, 'errors': list}
    """
    api_key = getattr(settings, 'BREVO_API_KEY', '')
    if not api_key:
        logger.error("BREVO_API_KEY non configurée!")
        if not fail_silently:
            raise ValueError("BREVO_API_KEY non configurée dans les settings.")
        return {'success': False, 'sent': 0, 'failed': 0, 'errors': ['BREVO_API_KEY non configurée']}

    if not from_email:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@monecole.pro')
    if not from_name:
        from_name = getattr(settings, 'DEFAULT_FROM_NAME', 'MonEcole')

    # Normaliser les destinataires
    recipients = []
    for e in to_emails:
        if isinstance(e, str):
            recipients.append({'email': e})
        elif isinstance(e, dict):
            recipients.append(e)

    if not recipients:
        return {'success': False, 'sent': 0, 'failed': 0, 'errors': ['Aucun destinataire']}

    # Brevo limite à 50 destinataires par appel — on batche
    BATCH_SIZE = 50
    total_sent = 0
    total_failed = 0
    errors = []

    # SSL context (permissif pour éviter les problèmes de certificats serveur)
    ctx = ssl.create_default_context()

    for i in range(0, len(recipients), BATCH_SIZE):
        batch = recipients[i:i + BATCH_SIZE]

        payload = {
            'sender': {'name': from_name, 'email': from_email},
            'to': batch,
            'subject': subject,
        }

        if html_content:
            payload['htmlContent'] = html_content
            if text_content:
                payload['textContent'] = text_content
        elif text_content:
            payload['textContent'] = text_content
        else:
            payload['textContent'] = subject  # fallback

        json_data = json.dumps(payload).encode('utf-8')

        req = urllib.request.Request(
            BREVO_API_URL,
            data=json_data,
            method='POST',
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'api-key': api_key,
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                status_code = resp.getcode()
                body = resp.read().decode('utf-8', errors='replace')

            if 200 <= status_code < 300:
                logger.info(f"Brevo email envoyé à {len(batch)} destinataires: {body}")
                total_sent += len(batch)
            else:
                logger.error(f"Erreur API Brevo ({status_code}): {body}")
                total_failed += len(batch)
                errors.append(f"HTTP {status_code}: {body[:200]}")

        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='replace') if e.fp else str(e)
            logger.error(f"Erreur HTTP Brevo ({e.code}): {body}")
            total_failed += len(batch)
            errors.append(f"HTTP {e.code}: {body[:200]}")
        except urllib.error.URLError as e:
            logger.error(f"Erreur URL Brevo: {e.reason}")
            total_failed += len(batch)
            errors.append(f"URL Error: {e.reason}")
        except Exception as e:
            logger.error(f"Erreur Brevo: {e}")
            total_failed += len(batch)
            errors.append(str(e))

    return {
        'success': total_sent > 0,
        'sent': total_sent,
        'failed': total_failed,
        'errors': errors,
    }


def build_parent_email_html(sender_name, message_text, school_name='MonEcole'):
    """
    Construit un email HTML élégant pour les communications enseignant → parents.
    """
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f4f4;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f4;padding:20px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08)">
    <!-- Header -->
    <tr><td style="background:linear-gradient(135deg,#075e54,#128c7e);padding:24px 30px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700">{school_name}</h1>
        <p style="color:rgba(255,255,255,.8);margin:4px 0 0;font-size:13px">Communication scolaire</p>
    </td></tr>
    <!-- Body -->
    <tr><td style="padding:30px">
        <p style="color:#128c7e;font-size:14px;font-weight:700;margin:0 0 6px">Message de : {sender_name}</p>
        <hr style="border:none;border-top:1px solid #e8e8e8;margin:12px 0">
        <div style="color:#333;font-size:15px;line-height:1.6;white-space:pre-wrap">{message_text}</div>
        <hr style="border:none;border-top:1px solid #e8e8e8;margin:20px 0">
        <p style="color:#999;font-size:11px;margin:0">Ce message a été envoyé depuis la plateforme {school_name}. Veuillez ne pas répondre directement à cet email.</p>
    </td></tr>
    <!-- Footer -->
    <tr><td style="background:#f8f9fa;padding:16px 30px;text-align:center">
        <p style="color:#aaa;font-size:11px;margin:0">&copy; {school_name} &mdash; Plateforme de gestion scolaire</p>
    </td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
