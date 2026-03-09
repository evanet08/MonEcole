
from django.contrib.auth.models import User
from MonEcole_app.models import Personnel
from MonEcole_app.models.module import UserModule
from django.contrib import messages
from django.shortcuts import redirect
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

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
            
            # Tier 1: Modules for the year with etat_annee = "En Cours"
            user_modules = UserModule.objects.filter(
                user=personnel,
                is_active=True,
                id_annee__etat_annee="En Cours"
            ).select_related('module', 'id_annee')

            # Tier 2: Fallback — any active year (is_active=True)
            if not user_modules.exists():
                logger.warning(
                    f"[get_user_info] No modules with etat_annee='En Cours' for {user.username}. "
                    "Falling back to is_active=True."
                )
                user_modules = UserModule.objects.filter(
                    user=personnel,
                    is_active=True,
                    id_annee__is_active=True
                ).select_related('module', 'id_annee')

            # Tier 3: Last resort — any assigned active module
            if not user_modules.exists():
                logger.warning(
                    f"[get_user_info] No modules with active year for {user.username}. "
                    "Falling back to any active module assignment."
                )
                user_modules = UserModule.objects.filter(
                    user=personnel,
                    is_active=True
                ).select_related('module', 'id_annee')

            user_info['modules'] = [
                mod.module for mod in user_modules if mod.module.url_name
            ]

            # Store the resolved year in session for decorator use
            if user_modules.exists():
                first_mod = user_modules.first()
                if first_mod and first_mod.id_annee:
                    request.session['id_annee'] = first_mod.id_annee.id_annee
        
        except Personnel.DoesNotExist:
           messages.error(request, "Votre compte n'est pas correctement configuré. Contactez l'administrateur.")
           return redirect("log_out") 
    return user_info


