"""
Vue Dashboard principal MonEcole.
Point d'entrée après login — affiche les stats de l'établissement.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import connections


@login_required(login_url='login')
def dashboard_view(request):
    """Dashboard principal de l'établissement."""
    etab_id = getattr(request, 'id_etablissement', None)
    etab_nom = getattr(request, 'nom_etablissement', None)

    if not etab_id:
        return render(request, 'dashboard/no_tenant.html')

    # Récupérer les stats de base
    stats = _get_dashboard_stats(etab_id)

    context = {
        'etab_id': etab_id,
        'etab_nom': etab_nom,
        'stats': stats,
        'active_section': 'dashboard',
    }
    return render(request, 'dashboard/index.html', context)


def _get_dashboard_stats(etab_id):
    """Récupère les statistiques de base pour le dashboard."""
    stats = {
        'cycles_actifs': 0,
        'classes': 0,
        'enseignants': 0,
        'eleves_inscrits': 0,
    }

    try:
        # Stats depuis le Hub (countryStructure)
        with connections['countryStructure'].cursor() as cur:
            # Classes actives
            cur.execute("""
                SELECT COUNT(DISTINCT eac.id) AS total_classes,
                       COUNT(DISTINCT eac.classe_id) AS nb_classes
                FROM etablissements_annees_classes eac
                JOIN etablissements_annees ea ON ea.id = eac.etablissement_annee_id
                JOIN annees a ON a.id_annee = ea.annee_id
                WHERE ea.etablissement_id = %s AND a.etat_annee = 'En Cours'
            """, [etab_id])
            row = cur.fetchone()
            if row:
                stats['classes'] = row[0] or 0

            # Cycles actifs
            cur.execute("""
                SELECT COUNT(DISTINCT c.id_cycle) AS cycles
                FROM etablissements_annees_classes eac
                JOIN etablissements_annees ea ON ea.id = eac.etablissement_annee_id
                JOIN annees a ON a.id_annee = ea.annee_id
                JOIN classes cl ON cl.id_classe = eac.classe_id
                JOIN cycles c ON c.id_cycle = cl.cycle_id
                WHERE ea.etablissement_id = %s AND a.etat_annee = 'En Cours'
            """, [etab_id])
            row = cur.fetchone()
            if row:
                stats['cycles_actifs'] = row[0] or 0

        # Stats depuis le Spoke (db_monecole)
        with connections['default'].cursor() as cur:
            # Enseignants
            cur.execute("""
                SELECT COUNT(*) FROM personnel
                WHERE en_fonction = 1
            """)
            row = cur.fetchone()
            if row:
                stats['enseignants'] = row[0] or 0

            # Élèves inscrits
            cur.execute("""
                SELECT COUNT(DISTINCT ei.id_eleve_id) FROM eleve_inscription ei
                JOIN eleve e ON e.id_eleve = ei.id_eleve_id
                WHERE ei.status = 1
            """)
            row = cur.fetchone()
            if row:
                stats['eleves_inscrits'] = row[0] or 0

    except Exception as e:
        import traceback
        traceback.print_exc()

    return stats
