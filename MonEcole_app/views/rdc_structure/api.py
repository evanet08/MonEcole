
from collections import defaultdict
from django.db.models import Prefetch
from MonEcole_app.models import Cours_par_classe
import logging

logger = logging.getLogger(__name__)

def get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe):
    """
    Récupère les cours d'une classe pour le bulletin RDC.
    id_classe = EAC id (EtablissementAnneeClasse)
    
    La table cours_annee (Cours_par_classe) n'a PAS de colonne id_classe.
    Les cours sont liés à la classe via: Cours.classe_id = Classe.id_classe
    Cours_par_classe (cours_annee) lie: cours_id + annee_id + etablissement_id
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

    # Récupérer les noms de domaines depuis le Hub
    from MonEcole_app.models.country_structure import Domaine
    domaines_dict = {}
    try:
        domaines_dict = {d.id_domaine: d.nom for d in Domaine.objects.all()}
    except Exception:
        pass

    groupes = defaultdict(list)
    for cpc in cpc_qs:
        domaine_id = cpc.id_cours.domaine_id
        domaine_nom = domaines_dict.get(domaine_id, "Non classé") if domaine_id else "Non classé"
        groupes[domaine_nom].append((cpc.ordre_cours, cpc)) 

    domaines_ordonnes = []
    for domaine, liste in groupes.items():
        liste.sort(key=lambda x: x[0] if x[0] is not None else float('inf'))
        domaines_ordonnes.append({
            'domaine': domaine,
            'cours': [item[1] for item in liste]  
        })

    domaines_ordonnes.sort(key=lambda g: min(
        (item.ordre_cours for item in g['cours'] if item.ordre_cours is not None),
        default=9999
    ))

    logger.warning(f"[get_cours_classe_rdc] Found {sum(len(g['cours']) for g in domaines_ordonnes)} cours in {len(domaines_ordonnes)} domaines for EAC {id_classe}")
    return domaines_ordonnes
