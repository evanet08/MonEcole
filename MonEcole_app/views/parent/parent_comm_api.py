"""
API Communication — Module Parents PWA.
Inbox (messages reçus), envoi de messages, threads.
Réutilise la table `communication` existante.
"""
import json
import time
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connections
from django.utils import timezone

from MonEcole_app.models.eleves.eleve import Eleve, Eleve_inscription
from MonEcole_app.models.communication import Communication
from MonEcole_app.views.parent.parent_views import _get_parent_session

logger = logging.getLogger(__name__)


def _get_parent_context(request):
    """Retourne (parent_data, id_eleve, eleve, inscription) ou (None, error_resp)."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return None, None, None, None, JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    id_eleve = request.GET.get('id_eleve') or request.session.get('selected_child_id')
    if not id_eleve:
        return parent_data, None, None, None, None

    filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
    if parent_data.get('id_pays'):
        filters['id_pays'] = parent_data['id_pays']

    try:
        eleve = Eleve.objects.get(**filters)
    except Eleve.DoesNotExist:
        return None, None, None, None, JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

    insc = Eleve_inscription.objects.filter(
        id_eleve=eleve, status=True
    ).order_by('-id_annee_id').first()

    return parent_data, id_eleve, eleve, insc, None


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_messages(request):
    """Inbox du parent : messages reçus (individuels, classe, établissement)."""
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
        eleve = Eleve.objects.get(id_eleve=id_eleve)
        etab_id = eleve.id_etablissement

        # Trouver la classe pour le scope 'class'
        insc = Eleve_inscription.objects.filter(
            id_eleve=eleve, status=True, id_etablissement=eleve.id_etablissement
        ).order_by('-id_annee_id').first()
        classe_id = insc.id_classe_id if insc else None

        with connections['default'].cursor() as cur:
            # Messages adressés à cet enfant (individual) ou à sa classe ou à tout l'établissement
            # + messages envoyés par ce parent (pour voir le thread complet)
            params = [etab_id]
            scope_conditions = ["c.scope = 'etab'"]

            if id_eleve:
                scope_conditions.append("(c.scope = 'individual' AND c.target_eleve_id = %s)")
                params.append(int(id_eleve))

            if classe_id:
                # Résoudre l'EAC id pour la classe (Hub)
                try:
                    with connections['countryStructure'].cursor() as cur_hub:
                        cur_hub.execute("""
                            SELECT eac.id FROM etablissements_annees_classes eac
                            JOIN etablissements_annees ea ON ea.id = eac.etablissement_annee_id
                            JOIN etablissements etab ON etab.id = ea.etablissement_id
                            WHERE etab.id_etablissement = %s AND eac.classe_id = %s
                            LIMIT 1
                        """, [etab_id, classe_id])
                        eac_row = cur_hub.fetchone()
                except Exception:
                    eac_row = None
                if eac_row:
                    scope_conditions.append("(c.scope = 'class' AND c.target_classe_id = %s)")
                    params.append(eac_row[0])

            # Messages du parent lui-même
            scope_conditions.append("c.sender_parent_id = %s")
            params.append(parent_data['id_parent'])

            where = ' OR '.join(scope_conditions)
            cur.execute(f"""
                SELECT c.id_communication, c.sender_name, c.sender_personnel_id,
                       c.sender_parent_id, c.scope, c.direction,
                       c.subject, c.message, c.thread_id,
                       c.attachment_url, c.attachment_name, c.attachment_type,
                       c.is_read, c.created_at, c.target_personnel_id
                FROM communication c
                WHERE c.id_etablissement = %s AND ({where})
                ORDER BY c.created_at DESC
                LIMIT 200
            """, params)

            columns = [col[0] for col in cur.description]
            msgs_raw = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Regrouper par thread
        threads = {}
        for m in msgs_raw:
            tid = m['thread_id'] or f"msg-{m['id_communication']}"
            is_mine = (m['sender_parent_id'] == parent_data['id_parent'])

            # Track personnel involved in this thread
            pers_in_msg = m.get('sender_personnel_id') or m.get('target_personnel_id')

            msg_data = {
                'id': m['id_communication'],
                'sender_name': m['sender_name'] or ('Moi' if is_mine else 'École'),
                'sender_personnel_id': m.get('sender_personnel_id'),
                'target_personnel_id': m.get('target_personnel_id'),
                'is_mine': is_mine,
                'scope': m['scope'],
                'subject': m['subject'] or '',
                'message': m['message'] or '',
                'is_read': m['is_read'],
                'created_at': m['created_at'].strftime('%Y-%m-%d %H:%M') if m['created_at'] else '',
                'time': m['created_at'].strftime('%H:%M') if m['created_at'] else '',
                'date': m['created_at'].strftime('%d/%m') if m['created_at'] else '',
            }
            if m['attachment_url']:
                msg_data['attachment'] = {
                    'url': m['attachment_url'],
                    'name': m['attachment_name'] or '',
                    'type': m['attachment_type'] or 'file',
                }

            if tid not in threads:
                threads[tid] = {
                    'thread_id': tid,
                    'subject': m['subject'] or m['message'][:50],
                    'scope': m['scope'],
                    'last_message': m['message'][:80] if m['message'] else '',
                    'last_sender': msg_data['sender_name'],
                    'last_time': msg_data['time'],
                    'last_date': msg_data['date'],
                    'unread': 0,
                    'messages': [],
                    'personnel_ids': [],
                }

            threads[tid]['messages'].append(msg_data)
            if pers_in_msg and pers_in_msg not in threads[tid]['personnel_ids']:
                threads[tid]['personnel_ids'].append(pers_in_msg)
            if not m['is_read'] and not is_mine:
                threads[tid]['unread'] += 1

        thread_list = sorted(threads.values(), key=lambda t: t['messages'][0]['created_at'] if t['messages'] else '', reverse=True)

        return JsonResponse({'success': True, 'threads': thread_list})

    except Exception as e:
        logger.exception("api_parent_messages error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_parent_send_message(request):
    """Envoyer un message (parent → enseignant/direction)."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    try:
        # Support both JSON and FormData (for attachments)
        content_type = request.content_type or ''
        if 'application/json' in content_type:
            data = json.loads(request.body)
        else:
            data = request.POST

        message_text = (data.get('message') or '').strip()
        if not message_text:
            return JsonResponse({'success': False, 'error': 'Message vide'}, status=400)

        id_eleve = data.get('id_eleve')
        thread_id = data.get('thread_id', '')
        scope = data.get('scope', 'teacher')
        target_personnel_id = data.get('target_personnel_id')
        subject = data.get('subject', '')

        # Handle file attachment
        attachment = request.FILES.get('attachment')
        attachment_url = ''
        attachment_name = ''
        attachment_type = ''
        if attachment:
            import os
            from django.conf import settings
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'communication')
            os.makedirs(upload_dir, exist_ok=True)
            fname = f"comm_{int(time.time())}_{attachment.name}"
            fpath = os.path.join(upload_dir, fname)
            with open(fpath, 'wb') as f:
                for chunk in attachment.chunks():
                    f.write(chunk)
            attachment_url = f"{settings.MEDIA_URL}communication/{fname}"
            attachment_name = attachment.name
            attachment_type = attachment.content_type or 'application/octet-stream'

        if not id_eleve:
            return JsonResponse({'success': False, 'error': 'id_eleve requis'}, status=400)

        # Vérifier propriété
        filters = {'id_eleve': id_eleve, 'id_parent': parent_data['id_parent']}
        if parent_data.get('id_pays'):
            filters['id_pays'] = parent_data['id_pays']
        if not Eleve.objects.filter(**filters).exists():
            return JsonResponse({'success': False, 'error': 'Accès refusé'}, status=403)

        eleve = Eleve.objects.get(id_eleve=id_eleve)
        etab_id = eleve.id_etablissement

        # Résoudre l'année active
        annee_id = None
        try:
            from MonEcole_app.models.annee import Annee
            from MonEcole_app.models.country_structure import Etablissement as Etab
            etab_obj = Etab.objects.filter(id_etablissement=etab_id).first()
            if etab_obj:
                annee = Annee.objects.filter(pays_id=etab_obj.pays_id, isOpen=True).order_by('-annee').first()
                annee_id = annee.pk if annee else None
        except Exception:
            pass

        # Générer thread_id si nouveau
        if not thread_id:
            thread_id = f"p{parent_data['id_parent']}-e{id_eleve}-{int(time.time())}"

        # Créer le message
        comm = Communication.objects.create(
            id_etablissement=etab_id,
            id_annee=annee_id,
            id_pays=parent_data.get('id_pays'),
            sender_parent_id=parent_data['id_parent'],
            sender_name=parent_data.get('parent_name', 'Parent'),
            scope=scope,
            direction='in',  # Entrant côté école
            target_eleve_id=int(id_eleve),
            target_personnel_id=int(target_personnel_id) if target_personnel_id else None,
            subject=subject,
            message=message_text,
            thread_id=thread_id,
            status='sent',
            attachment_url=attachment_url or None,
            attachment_name=attachment_name or None,
            attachment_type=attachment_type or None,
        )

        return JsonResponse({
            'success': True,
            'message': {
                'id': comm.id_communication,
                'sender_name': comm.sender_name,
                'is_mine': True,
                'message': comm.message,
                'time': comm.created_at.strftime('%H:%M') if comm.created_at else '',
                'created_at': comm.created_at.strftime('%Y-%m-%d %H:%M') if comm.created_at else '',
            },
            'thread_id': thread_id,
        })

    except Exception as e:
        logger.exception("api_parent_send_message error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_parent_contacts(request):
    """Contacts disponibles pour envoyer un message (enseignants de la classe + direction)."""
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
        etab_id = eleve.id_etablissement

        contacts = {'enseignants': [], 'direction': []}

        with connections['default'].cursor() as cur:
            # Direction
            cur.execute("""
                SELECT p.id_personnel, p.nom, p.postnom, p.prenom
                FROM personnel p
                WHERE p.id_etablissement = %s AND p.en_fonction = 1
                  AND (p.isDirecteur = 1 OR p.isDAF = 1)
                ORDER BY p.nom
            """, [etab_id])
            for r in cur.fetchall():
                contacts['direction'].append({
                    'id_personnel': r[0],
                    'nom': f"{r[1] or ''} {r[3] or ''}".strip(),
                    'role': 'Direction',
                })

            # Enseignants de la classe de l'enfant
            insc = Eleve_inscription.objects.filter(
                id_eleve=eleve, status=True
            ).order_by('-id_annee_id').first()

            if insc:
                cur.execute("""
                    SELECT DISTINCT p.id_personnel, p.nom, p.postnom, p.prenom
                    FROM attribution_cours ac
                    JOIN personnel p ON p.id_personnel = ac.id_personnel_id
                    WHERE ac.classe_id = %s AND ac.id_etablissement = %s
                      AND p.en_fonction = 1
                    ORDER BY p.nom
                """, [insc.id_classe_id, etab_id])
                for r in cur.fetchall():
                    contacts['enseignants'].append({
                        'id_personnel': r[0],
                        'nom': f"{r[1] or ''} {r[3] or ''}".strip(),
                        'role': 'Enseignant',
                    })

        return JsonResponse({'success': True, 'contacts': contacts})

    except Exception as e:
        logger.exception("api_parent_contacts error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_parent_mark_read(request):
    """Marquer les messages d'un thread comme lus."""
    parent_data = _get_parent_session(request)
    if not parent_data:
        return JsonResponse({'success': False, 'error': 'Non connecté'}, status=401)

    try:
        data = json.loads(request.body)
        thread_id = data.get('thread_id')
        if not thread_id:
            return JsonResponse({'success': False, 'error': 'thread_id requis'}, status=400)

        # Marquer comme lus les messages pas envoyés par le parent
        updated = Communication.objects.filter(
            thread_id=thread_id,
            is_read=False,
        ).exclude(
            sender_parent_id=parent_data['id_parent']
        ).update(is_read=True, read_at=timezone.now())

        return JsonResponse({'success': True, 'marked': updated})

    except Exception as e:
        logger.exception("api_parent_mark_read error")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
