
from django.shortcuts import render
from MonEcole_app.views.tools.utils import get_user_info
from MonEcole_app.views.decorators.decorators import  module_required
from django.contrib.auth.decorators import login_required
from MonEcole_app.models.models_import import Personnel,Annee,Attribution_cours
from library_manager.models import Armoire
from django.shortcuts import redirect
from django.contrib import messages

@login_required
@module_required("Administration")
def redirect_to_parametrage(request):
    user_info = get_user_info(request)
    user_modules = user_info
    return render(request,
                  'parametrage/index_parametrage.html',
                  {
                    "photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name'],
                    "active_page": "parametrage",
                     
                  })

@login_required
@module_required("Evaluation")
def redirect_to_evaluation(request):
    user_info = get_user_info(request)
    user_modules = user_info
    return render(request,'evaluation/index_evaluation.html',
                    {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                     "last_name": user_modules['last_name'],
                     "active_page": "evaluation"})

@login_required
@module_required("Inscription")
def redirect_to_inscription(request):
    user_info = get_user_info(request)
    user_modules = user_info
    return render(request,'inscription/index_inscription.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name'],
                    "active_page": "inscription"}
                    )

@login_required
@module_required("Enseignement")
def redirect_to_enseignement(request):
    user_info = get_user_info(request)
    user_modules = user_info
    return render(request,'enseignement/index_enseignement.html',
                  {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                     "last_name": user_modules['last_name'],
                     "active_page": "enseignement"})
@login_required

@module_required("Recouvrement")
def redirect_to_recouvrement(request):
    user_info = get_user_info(request)
    user_modules = user_info
    return render(request,'recouvrement/index_recouvrement.html',
                  {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name'],
                    "active_page": "recouvrement"})

@login_required
@module_required("archives")
def redirect_to_achive(request):
    user_info = get_user_info(request)
    user_modules = user_info
    return render(request,'archives/index_archives.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                     "last_name": user_modules['last_name'],
                     "active_page": "archives"})
    

@login_required
@module_required("Bibliotheque")
def redirect_to_library(request):
    user_info = get_user_info(request)
    user_modules = user_info
    return render(request,'library/index_library.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                     "last_name": user_modules['last_name'],
                     "active_page": "library",
                    
                     })
    

@login_required
@module_required("Institeur et son Espace")
def redirect_to_espace_enseignat(request):
    user_info = get_user_info(request)
    user_modules = user_info

    # Récupérer les cours directement depuis la base
    try:
        personnel = Personnel.objects.get(user=request.user)
        annee_en_cours = Annee.objects.get(etat_annee="En Cours")

        cours = Attribution_cours.objects.filter(
            id_personnel=personnel,
            id_annee=annee_en_cours.id_annee
        ).select_related('id_cycle__cycle_id', 'id_classe__classe_id', 'id_cours')
        
        # Regrouper les cours par cycle (dynamique)
        cours_by_cycle = {}
        for c in cours:
            cycle_nom = getattr(c.id_cycle.cycle_id, 'cycle', '-')  
            if cycle_nom not in cours_by_cycle:
                cours_by_cycle[cycle_nom] = []
            cours_by_cycle[cycle_nom].append({
                'cours': getattr(c.id_cours.id_cours, 'cours', '-'), 
                'classe': f"{c.id_classe.classe_id.classe} {c.id_classe.groupe}" if c.id_classe.groupe else c.id_classe.classe_id.classe,
                'cycle': cycle_nom,
                'heures_par_semaine': getattr(c.id_cours, 'heures_par_semaine', 0), 
                'etat': getattr(c, 'etat', '-') 
            })

        # print('Cours par cycle:', cours_by_cycle)
    except Personnel.DoesNotExist:
        messages.error(request, "Votre compte n'est pas correctement configuré.")
        return redirect("log_out")
    except Annee.DoesNotExist:
        messages.error(request, "Aucune année scolaire en cours n'est définie.")
        return redirect("log_in")

    return render(request, 'enseignement/zone_pedag/espace_enseignant.html', {
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
        'cours_by_cycle': cours_by_cycle,
        'active_page': 'enseignement',
    })

@login_required
@module_required("Suivi des élèves")
def redirect_to_suivi_eleve(request):
    user_info = get_user_info(request)
    user_modules = user_info
    return render(request,'suivi/index_suivi.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name'],
                    "active_page": "suivi"})

def signup_page(request):
    return render (request,'auth_page/signup.html')
