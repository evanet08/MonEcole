
from django.shortcuts import render,redirect
from django.contrib import messages
from MonEcole_app.models.personnel import Personnel
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from MonEcole_app.forms.form_imports import PersonnelUserForm,PersonnelForm
from MonEcole_app.models.module import UserModule
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from MonEcole_app.models.models_import import Attribution_cours,Annee
from MonEcole_app.views.home.home import get_user_info
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os


def log_out_view(request):
    logout(request)
    return redirect('log_in')  

def verified_user_test(request):
    if request.method == "POST":
        username = request.POST.get("username").strip()
        user_data = User.objects.filter(username=username).first()

        if user_data:
            try:
                get_user_id = Personnel.objects.get(user=user_data)

                if get_user_id.is_verified:
                    messages.error(request, "Merci de passer, votre nom d'utilisateur a été déjà vérifié !")
                    return redirect("log_in")

                initial_user = {
                    'first_name': user_data.first_name,
                    'last_name': user_data.last_name,
                    'username': user_data.username,
                    'email': user_data.email,
                }
                initial_perso = {
                    'date_naissance': get_user_id.date_naissance,
                    'etat_civil': get_user_id.etat_civil,
                    'telephone': get_user_id.telephone,
                    'region': get_user_id.region,
                    'pays': get_user_id.pays,
                    'province': get_user_id.province,
                    'commune': get_user_id.commune,
                    'imageUrl': get_user_id.imageUrl,
                    'genre': get_user_id.genre,
                    'id_diplome': get_user_id.id_diplome,
                    'id_specialite': get_user_id.id_specialite,
                    'id_categorie': get_user_id.id_categorie,
                    'id_vacation': get_user_id.id_vacation,
                    'id_personnel_type': get_user_id.id_personnel_type,
                }

                formUser = PersonnelUserForm(request.POST or None, instance=user_data)
                formPersonnel = PersonnelForm(request.POST or None, request.FILES or None, instance=get_user_id)

                if formUser.is_valid() and formPersonnel.is_valid():
                    user = formUser.save(commit=False)
                    password = formUser.cleaned_data.get("password")
                    if password:
                        user.set_password(password) 
                    user.username = user_data.username  
                    user.save()

                    personnel = formPersonnel.save(commit=False)
                    personnel.codeAnnee = get_user_id.codeAnnee
                    personnel.matricule = get_user_id.matricule
                    personnel.id_diplome = get_user_id.id_diplome
                    personnel.id_categorie = get_user_id.id_categorie
                    personnel.id_personnel_type = get_user_id.id_personnel_type
                    personnel.id_specialite = get_user_id.id_specialite
                    personnel.id_vacation = get_user_id.id_vacation

                    if 'imageUrl' in request.FILES:
                        image_file = request.FILES['imageUrl']
                        nom_image = image_file.name 
                        chemin_complet = os.path.join('logos/personnel', nom_image)
                        default_storage.save(chemin_complet, ContentFile(image_file.read()))
                        personnel.imageUrl = nom_image

                    personnel.is_verified = True  
                    personnel.save()
                    messages.success(request, "Informations complétées avec succès !")
                    return redirect("log_in") 

            except Personnel.DoesNotExist:
                messages.error(request, "Données personnelles introuvables pour cet utilisateur.")
                return redirect("log_in")

            formUser = PersonnelUserForm(initial=initial_user)
            formPersonnel = PersonnelForm(initial=initial_perso)

            return render(request, "auth_page/signup.html", {
                'user_form': formUser,
                'personnel_form': formPersonnel,
                'username': username, 
            })

        else:
            messages.error(request, "Nom d'utilisateur introuvable. Merci de consulter l'administrateur du système.")
            return redirect("log_in")

    return render(request, "auth_page/signup.html")


def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Email ou mot de passe incorrect.")
            return redirect("log_in")

        try:
            personnel = Personnel.objects.get(user=user)
        except Personnel.DoesNotExist:
            messages.error(request, "Vous n'êtes pas associé à ce compte.")
            return redirect("log_in")

        if not personnel.isUser or not personnel.en_fonction:
            messages.error(request, "Votre compte n'est pas autorisé à se connecter.")
            return redirect("log_in")

        if not personnel.is_verified:
            messages.error(request, "Votre compte n'a pas encore été vérifié. Merci de vérifier votre compte.")
            return redirect("log_in")

        # Check module assignments exist at all
        all_user_modules = UserModule.objects.filter(user=personnel)
        if not all_user_modules.exists():
            messages.error(request, "Aucun module assigné à votre compte.")
            return redirect("log_in")

        # Check if at least one active module exists
        active_modules = all_user_modules.filter(is_active=True)
        if not active_modules.exists():
            messages.error(request, "Tous vos modules ont été désactivés. Contactez l'administrateur.")
            return redirect("log_in")

        # Authentification
        authenticated_user = authenticate(request, username=user.username, password=password)
        if authenticated_user is None:
            messages.error(request, "Email ou mot de passe incorrect.")
            return redirect("log_in")
        login(request, authenticated_user)

        # Retrieve modules (get_user_info now has fallback tiers)
        user_info = get_user_info(request)
        modules = user_info.get('modules', [])

        if modules:
            # Redirect to first available module
            if modules[0].module == "Institeur et son Espace":
                return redirect("home_zone_pedagogique")
            if modules[0].url_name:
                return redirect(modules[0].url_name)

        # If we reach here, modules were assigned but none have valid url_name
        # or get_user_info couldn't resolve any — provide diagnostic message
        has_year_en_cours = Annee.objects.filter(etat_annee="En Cours").exists()
        if not has_year_en_cours:
            messages.error(request, "Aucune année scolaire n'est actuellement 'En Cours'. Contactez l'administrateur pour configurer l'année.")
        else:
            messages.error(request, "Vos modules ne sont pas configurés pour l'année en cours. Contactez l'administrateur.")
        return redirect("log_in")

    return render(request, "auth_page/login.html")


 