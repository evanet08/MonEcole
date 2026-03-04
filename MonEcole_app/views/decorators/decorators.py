
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from MonEcole_app.models.module import UserModule
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from functools import wraps
from urllib.parse import urlparse
from MonEcole_app.models import UserModule



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
                if not UserModule.objects.filter(user=personnel, module__module=module_name).exists():
                    messages.error(request, "Vous n'avez pas accès à ce module. Veuillez contacter l'administrateur !")
                    if referer:
                        parsed_referer = urlparse(referer)
                        parsed_host = urlparse(request.build_absolute_uri()).netloc
                        if parsed_referer.netloc and parsed_referer.netloc != parsed_host:
                            return redirect('log_in') 
                        return redirect(referer)
                    return redirect('log_in')  
            except AttributeError:
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



