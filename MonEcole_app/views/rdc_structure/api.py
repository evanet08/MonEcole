
from collections import defaultdict
from django.db.models import Prefetch
from MonEcole_app.models import Cours_par_classe

def get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe):
   
    cpc_qs = Cours_par_classe.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe,
        is_obligatory=True 
    ).select_related('id_cours').order_by('ordre_cours')

    groupes = defaultdict(list)
    for cpc in cpc_qs:
        domaine = cpc.id_cours.domaine or "Non classe"
        groupes[domaine].append((cpc.ordre_cours, cpc)) 

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

    return domaines_ordonnes
