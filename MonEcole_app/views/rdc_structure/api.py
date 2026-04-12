
from collections import defaultdict, OrderedDict
from django.db.models import Prefetch
from MonEcole_app.models import Cours_par_classe
import logging

logger = logging.getLogger(__name__)

def get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe):
    """
    Récupère les cours d'une classe pour le bulletin RDC.
    id_classe = EAC id (EtablissementAnneeClasse)
    
    Supporte la hiérarchie domaine → sous-domaine via parent_id.
    Si un cours est assigné à un sous-domaine (parent_id IS NOT NULL),
    il apparaît sous le domaine parent avec le sous-domaine comme label intermédiaire.
    
    Retourne une liste de:
        {'domaine': str, 'sous_domaines': [{'nom': str, 'cours': [cpc]}]}
    Si pas de sous-domaines, tous les cours du domaine sont dans un seul sous-domaine vide.
    """
    from MonEcole_app.models.country_structure import EtablissementAnneeClasse
    from MonEcole_app.models.enseignmnts.matiere import Cours
    
    try:
        eac = EtablissementAnneeClasse.objects.select_related(
            'etablissement_annee', 'classe'
        ).get(id=id_classe)
        hub_classe_id = eac.classe_id
        etab_id = eac.etablissement_annee.etablissement_id
    except EtablissementAnneeClasse.DoesNotExist:
        logger.error(f"[get_cours_classe_rdc] EAC {id_classe} not found")
        return []

    # Trouver les cours liés à cette classe du catalogue Hub
    cours_ids = list(Cours.objects.filter(classe_id=hub_classe_id).values_list('id_cours', flat=True))
    
    if not cours_ids:
        logger.warning(f"[get_cours_classe_rdc] No cours found for hub_classe_id={hub_classe_id}")
        return []
    
    # Récupérer les configs annuelles (Cours_par_classe) pour ces cours
    cpc_qs = Cours_par_classe.objects.filter(
        id_cours_id__in=cours_ids,
        id_annee_id=id_annee,
        is_obligatory=True
    ).select_related('id_cours').order_by('ordre_cours')

    # Récupérer les domaines depuis le Hub (avec parent_id et ordre)
    from MonEcole_app.models.country_structure import Domaine
    domaines_dict = {}
    try:
        for d in Domaine.objects.all():
            domaines_dict[d.id_domaine] = {
                'nom': d.nom,
                'parent_id': d.parent_id,
                'ordre': d.ordre or 0,
            }
    except Exception:
        pass

    def get_root_domaine(dom_id):
        """Remonte au domaine racine (parent_id IS NULL)."""
        visited = set()
        current = dom_id
        while current and current not in visited:
            visited.add(current)
            info = domaines_dict.get(current)
            if not info or not info['parent_id']:
                return current
            current = info['parent_id']
        return dom_id

    # Grouper: domaine_racine → sous_domaine → cours
    # Structure: {root_dom_id: {sub_dom_id_or_None: [(ordre, cpc)]}}
    hierarchy = defaultdict(lambda: defaultdict(list))
    
    for cpc in cpc_qs:
        # Priority: domaine_id from cours_annee, fallback to cours table
        domaine_id = cpc.domaine_id or cpc.id_cours.domaine_id
        if not domaine_id:
            hierarchy[0][None].append((cpc.ordre_cours, cpc))
            continue
            
        dom_info = domaines_dict.get(domaine_id, {})
        parent_id = dom_info.get('parent_id')
        
        if parent_id:
            # Cours dans un sous-domaine → regrouper sous le parent racine
            root_id = get_root_domaine(domaine_id)
            hierarchy[root_id][domaine_id].append((cpc.ordre_cours, cpc))
        else:
            # Cours directement dans un domaine racine (pas de sous-domaine)
            hierarchy[domaine_id][None].append((cpc.ordre_cours, cpc))

    # Construire la sortie ordonnée
    domaines_ordonnes = []
    for root_dom_id, sous_groupes in hierarchy.items():
        root_info = domaines_dict.get(root_dom_id, {'nom': 'Non classé', 'ordre': 9999})
        root_nom = root_info['nom']
        root_ordre = root_info.get('ordre', 9999)
        
        # Déterminer le min ordre_cours de tous les cours sous ce domaine
        all_ordres = []
        for sub_list in sous_groupes.values():
            for o, _ in sub_list:
                if o is not None:
                    all_ordres.append(o)
        min_ordre = min(all_ordres) if all_ordres else 9999
        
        # Construire la liste de sous-domaines
        sous_domaines_out = []
        for sub_dom_id, cours_list in sous_groupes.items():
            cours_list.sort(key=lambda x: x[0] if x[0] is not None else float('inf'))
            sub_nom = domaines_dict.get(sub_dom_id, {}).get('nom', '') if sub_dom_id else None
            sub_ordre = domaines_dict.get(sub_dom_id, {}).get('ordre', 9999) if sub_dom_id else 0
            sous_domaines_out.append({
                'nom': sub_nom,
                'ordre': sub_ordre,
                'cours': [item[1] for item in cours_list]
            })
        
        sous_domaines_out.sort(key=lambda s: s['ordre'])
        
        domaines_ordonnes.append({
            'domaine': root_nom,
            'sous_domaines': sous_domaines_out,
            # Compat: cours plat = tous les cours (ancien format)
            'cours': [cpc for sd in sous_domaines_out for cpc in sd['cours']],
            '_min_ordre': min_ordre,
            '_root_ordre': root_ordre,
        })

    domaines_ordonnes.sort(key=lambda g: (g['_root_ordre'], g['_min_ordre']))

    total_cours = sum(len(g['cours']) for g in domaines_ordonnes)
    total_doms = len(domaines_ordonnes)
    has_subs = any(
        sd['nom'] is not None 
        for g in domaines_ordonnes 
        for sd in g['sous_domaines']
    )
    logger.warning(
        f"[get_cours_classe_rdc] Found {total_cours} cours in {total_doms} domaines "
        f"(has_sous_domaines={has_subs}) for EAC {id_classe}"
    )
    return domaines_ordonnes
