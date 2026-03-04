
from django.contrib.auth.models import User
from MonEcole_app.models import Personnel
from MonEcole_app.models.module import UserModule
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings

def get_user_info(request):
    user_info = {
        'photo_profil': None,
        'modules': [],
        'last_name': None,
    }
    if request.user.is_authenticated:
        user = request.user
        try:
            personnel = Personnel.objects.get(user=user)
            if personnel.imageUrl:
                photo_filename = str(personnel.imageUrl)  
                photo_url = f"/media/logos/personnel/{photo_filename}"
                user_info['photo_profil'] = photo_url
            else:
                user_info['photo_profil'] = None

            user_info['last_name'] = user.last_name 
            
            user_modules = UserModule.objects.filter(user=personnel,is_active = True,id_annee__etat_annee = "En Cours").select_related('module')
            user_info['modules'] = [
                mod.module for mod in user_modules if mod.module.url_name
            ]  
        
        except Personnel.DoesNotExist:
           messages.error(request, "Votre compte n'est pas correctement configuré. Contactez l'administrateur.")
           return redirect("log_out") 
    return user_info


