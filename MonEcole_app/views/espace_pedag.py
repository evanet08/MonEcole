from django.shortcuts import render,redirect
from MonEcole_app.models.models_import import Attribution_cours
from django.contrib.auth.models import User




def visualizer_cours_enseignant (request):
    mycourse_select = Attribution_cours.objects.all()
    return render(request,'enseignement/zone_pedag/espace_enseignant.html',
                  {'my_cours':mycourse_select})