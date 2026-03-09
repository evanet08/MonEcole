from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from functools import wraps
from urllib.parse import urlparse
from MonEcole_app.models.module import UserModule
import logging

logger = logging.getLogger(__name__)


def module_required(module_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            referer = request.META.get('HTTP_REFERER')

            if not user.is_authenticated:
                messages.error(request, "Veuillez vous connecter pour accéder à ce module.")
                next_url = request.get_full_path()  
                login_url = f"{reverse('log_in')}?next={next_url}"
                return redirect(login_url)

            try:
                personnel = user.personnel

                # Tier 1: Check with etat_annee = "En Cours"
                has_module = UserModule.objects.filter(
                    user=personnel,
                    module__module=module_name,
                    is_active=True,
                    id_annee__etat_annee="En Cours"
                ).exists()

                # Tier 2: Fallback to any active year
                if not has_module:
                    has_module = UserModule.objects.filter(
                        user=personnel,
                        module__module=module_name,
                        is_active=True,
                        id_annee__is_active=True
                    ).exists()

                # Tier 3: Fallback to any active assignment
                if not has_module:
                    has_module = UserModule.objects.filter(
                        user=personnel,
                        module__module=module_name,
                        is_active=True
                    ).exists()

                if not has_module:
                    logger.warning(
                        f"[module_required] User {user.username} denied access to module '{module_name}'. "
                        "No active assignment found."
                    )
                    messages.error(request, "Vous n'avez pas accès à ce module. Veuillez contacter l'administrateur !")
                    if referer:
                        parsed_referer = urlparse(referer)
                        parsed_host = urlparse(request.build_absolute_uri()).netloc
                        if parsed_referer.netloc and parsed_referer.netloc != parsed_host:
                            return redirect('log_in') 
                        return redirect(referer)
                    return redirect('log_in')  

            except AttributeError:
                logger.error(
                    f"[module_required] User {user.username} has no personnel record."
                )
                messages.error(request, "Vous n'avez plus accès à ce module.")
                if referer:
                    parsed_referer = urlparse(referer)
                    parsed_host = urlparse(request.build_absolute_uri()).netloc
                    if parsed_referer.netloc and parsed_referer.netloc != parsed_host:
                        return redirect('log_in')
                    return redirect(referer)
                return redirect('log_in')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
