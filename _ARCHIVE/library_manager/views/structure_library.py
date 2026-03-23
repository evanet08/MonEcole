from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect
from MonEcole_app.views.decorators.decorators import module_required
from MonEcole_app.views.tools.utils import get_user_info
from django.contrib import messages 
from django.urls import reverse
from MonEcole_app.models import Eleve, Annee, Campus, Classe_cycle_actif, Classe_active, Personnel
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
import json
from library_manager.models import Emprunt
from library_manager.forms import (ArmoireForm,
                                   Armoire,Compartiment,
                                   CompartimentForm,Categorie,
                                   CategorieForm,Livre,LivreForm,
                                   Exemplaire,ExemplaireForm)



@login_required
@module_required("Bibliotheque")
def redirect_ajout_emprunt(request):
    user_info = get_user_info(request)
    user_modules = user_info
    biblio_home = True
    list_armoire = Armoire.objects.all()
    annee_list = Annee.objects.all()
    return render(request,'library/index_library.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                     "last_name": user_modules['last_name'],
                    "list_armoire":list_armoire,
                    "annees":annee_list,
                    "biblio_home":biblio_home
                     })
    
    
@login_required
@module_required("Bibliotheque")
def displaying_emprunt(request):
    user_info = get_user_info(request)
    user_modules = user_info
    emprunt_list = Emprunt.objects.filter(rendu = False)
    return render(request,'library/index_library.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                     "last_name": user_modules['last_name'],
                    "emprunt_list":emprunt_list,
                    
                     })
    
@login_required
@module_required("Bibliotheque")
def displaying_retour_emprunt(request):
    user_info = get_user_info(request)
    user_modules = user_info
    emprunt_list = Emprunt.objects.filter(rendu = False)
    return render(request,'library/index_library.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name'],
                    "emprunt_list_retour":emprunt_list,
                    
                     })      
    
@login_required
@module_required("Bibliotheque")
def add_armoire_library(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        nom = request.POST.get('nom')
        form = ArmoireForm(request.POST)
        if form.is_valid():
            library_list = Armoire.objects.filter(nom = nom)
            if library_list:
               messages.success(request,"Désolé!L'armoire a été déjà créee;Veuillew changer et utiliser un autre!")
               return reverse(redirect('library:create_armory_library'))
            form.save()
            messages.success(request,"L'armoire a été créee avec succès")
            return redirect('library:create_armory_library')
    else:
        form = ArmoireForm()
        armoire_list = Armoire.objects.all()
    return render(request, 'library/index_library.html', {
        'armoire_list': armoire_list,
        'form_armoire': form,
        'form_type': 'armoire_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })
    
    
@login_required
@module_required("Bibliotheque")
def add_compartiment_library(request):
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        numero = request.POST.get('numero')
        form = CompartimentForm(request.POST)
        if form.is_valid():
            library_list = Compartiment.objects.filter(numero = numero)
            if library_list:
               messages.success(request,"Le compartement a été déjà créé;Choisir un autre nommenclature")
               return reverse(redirect('library:create_compartiment_library'))
            form.save()
            messages.success(request,"L'armoire a été créee avec succès")
            return redirect('library:create_compartiment_library')
    else:
        form = CompartimentForm()
        compartement_list = Compartiment.objects.all()
    return render(request, 'library/index_library.html', {
        'compartement_list': compartement_list,
        'form_compartement': form,
        'form_type': 'compartement_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })
    
@login_required
@module_required("Bibliotheque")
def add_category_livre_library(request):
    categorie_list = Categorie.objects.all()
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        nom = request.POST.get('nom')
        form = CategorieForm(request.POST)
        if form.is_valid():
            library_list = Categorie.objects.filter(nom = nom)
            if library_list:
               messages.success(request,"Le categorie d'un livre a été déjà créé;Choisir un autre nommenclature")
               return reverse(redirect('library:create_category_livre_library'))
            form.save()
            messages.success(request,"Le categorie pour un livre a été créee avec succès")
            return redirect('library:create_category_livre_library')
    else:
        form = CategorieForm()
    return render(request, 'library/index_library.html', {
        'categorie_list': categorie_list,
        'form_category': form,
        'form_type': 'category_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })
    
    
@login_required
@module_required("Bibliotheque")
def add_livre_library(request):
    livre_list = Livre.objects.all()
    user_info = get_user_info(request)
    user_modules = user_info
    if request.method == "POST":
        titre = request.POST.get('titre')
        form = LivreForm(request.POST)
        if form.is_valid():
            library_list = Livre.objects.filter(titre = titre)
            if library_list:
               messages.success(request,"Le livre a été déjà créé;Choisir un autre livre")
               return reverse(redirect('library:create_livre_library'))
            form.save()
            messages.success(request,"Le livre a été enregistré avec succès")
            return redirect('library:create_livre_library')
    else:
        form = LivreForm()
    return render(request, 'library/index_library.html', {
        'livre_list': livre_list,
        'form_livre': form,
        'form_type': 'livre_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })
    
@login_required
@module_required("Bibliotheque")
def add_livre_exemplaire_library(request):
    livre_list = Exemplaire.objects.all()
    user_info = get_user_info(request)
    # id_eleve = request.POST.get('id_eleve')
    user_modules = user_info
    # get_all_exemplaire = Exemplaire.objects.filter(id_eleve = id_eleve)
    if request.method == "POST":
        form = ExemplaireForm(request.POST)
        if form.is_valid():            
            form.save()
            messages.success(request,"L'exemplaire d'un livre a été enregistré avec succès")
            return redirect('library:create_livre_exemplaire_library')
    else:
        form = ExemplaireForm()
    return render(request, 'library/index_library.html', {
        'livre_exempl_list': livre_list,
        'form_livre_exemplaire': form,
        'form_type': 'livre_exemplaire_form',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })
    

@csrf_protect
@login_required
def save_emprunt(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

    try:
        data = json.loads(request.body)
        id_livre = data.get('id_livre')
        id_annee = data.get('id_annee')
        id_campus = data.get('id_campus')
        id_cycle_actif = data.get('id_cycle_actif')
        id_classe_active = data.get('id_classe_active')
        id_eleve = data.get('id_eleve')
        date_retour_prevue = data.get('date_retour_prevue')

        if not all([id_livre, id_annee, id_campus, id_eleve, date_retour_prevue]):
            return JsonResponse({'error': 'Tous les champs requis ne sont pas remplis'}, status=400)

        # Vérifier les objets
        try:
            livre = Livre.objects.get(id=id_livre)
            annee = Annee.objects.get(id_annee=id_annee)
            campus = Campus.objects.get(id_campus=id_campus)
            eleve = Eleve.objects.get(id_eleve=id_eleve)
            classe_active = Classe_active.objects.get(id_classe_active=id_classe_active) if id_classe_active else None
            cycle_actif = Classe_cycle_actif.objects.get(id_cycle_actif=id_cycle_actif) if id_cycle_actif else None
            personnel = Personnel.objects.get(user=request.user)
        except (Livre.DoesNotExist, Annee.DoesNotExist, Campus.DoesNotExist, Eleve.DoesNotExist, 
                Classe_active.DoesNotExist, Classe_cycle_actif.DoesNotExist, Personnel.DoesNotExist) as e:
            return JsonResponse({'error': f'Erreur de données : {str(e)}'}, status=404)

        # Créer l'emprunt
        Emprunt.objects.create(
            id_livre=livre,
            id_personnel=personnel,
            id_eleve=eleve,
            date_retour_prevue=date_retour_prevue,
            id_annee=annee,
            id_campus=campus,
            id_cycle_actif=cycle_actif,
            id_classe_active=classe_active
            
        )
        livre.disponible = False
        livre.save()
        return JsonResponse({'success': True, 'message': 'Emprunt enregistré avec succès'})
    except Exception as e:
        return JsonResponse({'error': f'Erreur serveur : {str(e)}'}, status=500)