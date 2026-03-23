

# import uuid
# from django.core.mail import send_mail
# from django.conf import settings
# from MonEcole_app.models .models_import import Eleve

# from django.shortcuts import get_object_or_404, redirect
# from django.http import HttpResponse

# def confirm_email(request, token):
#     eleve = get_object_or_404(Eleve, email_token=token)
#     eleve.email_verifie = True
#     eleve.email_token = None
#     eleve.save()
#     return HttpResponse("Votre adresse e-mail est confirmée. Merci !")


# def creer_eleve_et_envoyer_confirmation(nom, email):
#     token = str(uuid.uuid4())
#     eleve = Eleve.objects.create(nom=nom, email_parent=email, email_token=token)
    
#     lien = f"http://tonsite.com/confirm-email/{token}"
    
#     message = f"Bonjour {nom}, veuillez confirmer votre adresse e-mail en cliquant ici : {lien}"
    
#     send_mail(
#         subject="Confirmation d'email",
#         message=message,
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         recipient_list=[email],
#         fail_silently=False,
    # )
# path('confirm-email/<str:token>/', views.confirm_email, name='confirm_email'),
