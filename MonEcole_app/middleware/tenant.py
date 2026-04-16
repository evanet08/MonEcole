"""
Middleware de résolution multi-tenant par sous-domaine.

Fonctionnement :
1. Extrait le sous-domaine depuis HTTP_HOST (ex: collegealfajiri.monecole.pro → collegealfajiri)
2. Cherche l'établissement correspondant dans countryStructure.etablissements via le champ `url`
3. Stocke id_etablissement + id_pays en session pour un accès rapide
4. Attache id_etablissement, id_pays et nom_etablissement au request pour usage dans les vues

Les requêtes vers monecole.pro (sans sous-domaine) passent sans contexte tenant.
"""

import logging
from django.db import connections
from django.http import HttpResponseNotFound

logger = logging.getLogger(__name__)

# Domaines de base (sans sous-domaine) — pas de résolution tenant
BASE_DOMAINS = {'monecole.pro', 'www.monecole.pro', 'localhost', '127.0.0.1', '87.106.23.108'}


class TenantMiddleware:
    """
    Middleware qui résout l'établissement (tenant) à partir du sous-domaine.
    
    Exemple :
        collegealfajiri.monecole.pro → url='collegealfajiri.monecole.pro'
        → countryStructure.etablissements.url = 'collegealfajiri.monecole.pro'
        → id_etablissement = 9, id_pays = 2
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extraire le host (sans le port)
        host = request.get_host().split(':')[0].lower().strip()

        # Si c'est un domaine de base, pas de résolution tenant
        if host in BASE_DOMAINS:
            request.id_etablissement = None
            request.id_pays = None
            request.nom_etablissement = None
            return self.get_response(request)

        # Vérifier si déjà résolu dans la session (cache)
        session_host = request.session.get('tenant_host')
        if session_host == host:
            request.id_etablissement = request.session.get('id_etablissement')
            request.id_pays = request.session.get('id_pays')
            request.nom_etablissement = request.session.get('nom_etablissement')
            return self.get_response(request)

        # Résoudre le tenant via SQL direct sur countryStructure
        id_etablissement, id_pays, nom = self._resolve_tenant(host)

        if id_etablissement is None:
            logger.warning(f"[TenantMiddleware] Aucun établissement trouvé pour le host: {host}")
            return HttpResponseNotFound(
                f"<h1>Établissement introuvable</h1>"
                f"<p>Aucun établissement n'est associé à <strong>{host}</strong>.</p>"
                f"<p>Vérifiez l'URL ou contactez l'administrateur.</p>"
            )

        # Stocker en session et sur le request
        request.session['id_etablissement'] = id_etablissement
        request.session['id_pays'] = id_pays
        request.session['nom_etablissement'] = nom
        request.session['tenant_host'] = host

        request.id_etablissement = id_etablissement
        request.id_pays = id_pays
        request.nom_etablissement = nom

        logger.info(f"[TenantMiddleware] Tenant résolu: {host} → id_etablissement={id_etablissement}, id_pays={id_pays} ({nom})")

        return self.get_response(request)

    def _resolve_tenant(self, host):
        """
        Cherche l'établissement dans countryStructure.etablissements
        où url = host (ex: 'collegealfajiri.monecole.pro').
        
        Retourne (id_etablissement, id_pays, nom) ou (None, None, None).
        """
        try:
            with connections['countryStructure'].cursor() as cursor:
                cursor.execute(
                    "SELECT id_etablissement, pays_id, nom FROM etablissements WHERE url = %s LIMIT 1",
                    [host]
                )
                row = cursor.fetchone()
                if row:
                    return row[0], row[1], row[2]
        except Exception as e:
            logger.error(f"[TenantMiddleware] Erreur lors de la résolution du tenant: {e}")
        
        return None, None, None
