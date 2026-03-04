from ._initials import *

@login_required
@module_required("Administration")
def delete_periode(request, id_periode):


    if request.method == "POST":
        try:
            periode = Periode.objects.get(id_periode=id_periode)
            if not periode.is_active:
                messages.error(request, "Cette période est déjà supprimée.")
                return redirect('create_periode')

            if Eleve_note.objects.filter(id_periode=periode).exists():
                messages.error(request, "Impossible de supprimer la période car elle est utilisée quelque part.")
                return redirect('create_periode')

            periode.is_active = False
            periode.save()
            messages.success(request, "Période supprimée avec succès.")
            return redirect('create_periode')

        except Periode.DoesNotExist:
            messages.error(request, "Période non trouvée.")
            return redirect('create_periode')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_periode')

    messages.error(request, "Méthode non autorisée.")
    return redirect('create_periode')

@login_required
@module_required("Administration")
def delete_trimestre(request, id_trimestre):
  
    if request.method == "POST":
        try:
            trimestre = Trimestre.objects.get(id_trimestre=id_trimestre)
            if not trimestre.is_active:
                messages.error(request, "Ce trimestre est déjà supprimé.")
                return redirect('create_trimestre')

            if Periode.objects.filter(id_trimestre=trimestre).exists():
                messages.error(request, "Impossible de supprimer le trimestre car il est utilisé quelque part.")
                return redirect('create_trimestre')

            trimestre.is_active = False
            trimestre.save()
            messages.success(request, "Trimestre supprimé avec succès.")
            return redirect('create_trimestre')

        except Trimestre.DoesNotExist:
            messages.error(request, "Trimestre non trouvé.")
            return redirect('create_trimestre')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_trimestre')

    messages.error(request, "Méthode non autorisée.")
    return redirect('create_trimestre')

@login_required
@module_required("Administration")
def delete_annee(request, id_annee):

    if request.method == "POST":
        try:
            annee = Annee.objects.get(id_annee=id_annee)
            if not annee.is_active:
                messages.error(request, "Cette année est déjà supprimée.")
                return redirect('create_annees')

            dependencies = []
            if Classe_active.objects.filter(id_annee=annee).exists():
                dependencies.append("classes actives")
            if Classe_cycle_actif.objects.filter(id_annee=annee).exists():
                dependencies.append("cycles actifs")

            if dependencies:
                error_msg = f"Impossible de supprimer l'année car elle est utilisée dans : {', '.join(dependencies)}."
                messages.error(request, error_msg)
                return redirect('create_annees')

            annee.is_active = False
            annee.save()
            messages.success(request, "Année supprimée avec succès.")
            return redirect('create_annees')

        except Annee.DoesNotExist:
            messages.error(request, "Année non trouvée.")
            return redirect('create_annees')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_annees')

    messages.error(request, "Méthode non autorisée.")
    return redirect('create_annees')

@login_required
@module_required("Administration")
def delete_campus(request, campus_id):
    
    if request.method == "POST":
        try:
            campus = Campus.objects.get(id_campus=campus_id)            
            if not campus.is_active:
                messages.error(request, "Ce campus est déjà supprimé.")
                return redirect('create_campus')
            dependencies = []
            if Classe_cycle_actif.objects.filter(id_campus=campus).exists():
                dependencies.append("cycles de classes actifs")
            if Classe_active.objects.filter(id_campus=campus).exists():
                dependencies.append("classes actives")
            
            if dependencies:
                error_msg = f"Impossible de supprimer le campus car il est utilisé dans : {', '.join(dependencies)}."
                messages.error(request, error_msg)
                return redirect('create_campus')

            campus.is_active = False
            campus.save()
            messages.success(request, "Campus supprimé avec succès.")
            return redirect('create_campus')

        except Campus.DoesNotExist:
            messages.error(request, "Campus non trouvé.")
            return redirect('create_campus')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_campus')

    messages.error(request, "Méthode non autorisée.")
    return redirect('create_campus')

@login_required
@module_required("Administration")
def delete_classe(request, id_classe):
    if request.method == "POST":
        try:
            classe = Classe.objects.get(id_classe=id_classe)            
            if not classe.is_active:
                messages.error(request, "Cette classe est déjà supprimé.")
                return redirect('create_classes')
            dependencies = []
            
            if Classe_active.objects.filter(classe_id=id_classe).exists():
                dependencies.append("classes actives")
            if dependencies:
                error_msg = f"Impossible de supprimer cette classe car il est utilisé dans : {', '.join(dependencies)}."
                messages.error(request, error_msg)
                return redirect('create_classes')

            classe.is_active = False
            classe.save()
            messages.success(request, "Classe supprimée avec succès.")
            return redirect('create_classes')

        except Classe.DoesNotExist:
            messages.error(request, "Classe non trouvé.")
            return redirect('create_classes')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_classes')

    messages.error(request, "Méthode non autorisée.")
    return redirect('create_classes')


@login_required
@module_required("Administration")
def delete_cycle(request, cycle_id):
  
    if request.method == "POST":
        try:
            cycle = Classe_cycle.objects.get(id_cycle=cycle_id)
            
            if not cycle.is_active:
                messages.error(request, "Ce cycle est déjà supprimé.")
                return redirect('create_classes_cycle')

            dependencies = []
            if Classe_cycle_actif.objects.filter(cycle_id=cycle).exists():
                dependencies.append("cycles actifs")
            if Classe_active.objects.filter(cycle_id__cycle_id=cycle).exists():
                dependencies.append("classes actives")
            if dependencies:
                error_msg = f"impossible de supprimer le cycle car il est utilisé dans : {', '.join(dependencies)}."
                messages.error(request, error_msg)
                return redirect('create_classes_cycle')

            cycle.is_active = False
            cycle.save()
            messages.success(request, "Cycle supprimé avec succès.")
            return redirect('create_classes_cycle')

        except Classe_cycle.DoesNotExist:
            messages.error(request, "Cycle non trouvé.")
            return redirect('create_classes_cycle')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_classes_cycle')

    messages.error(request, "Méthode non autorisée.")
    return redirect('create_classes_cycle')

@login_required
@module_required("Administration")
def delete_classe_active(request, id_classe_active):

    if request.method == "POST":
        try:
            classe_active = Classe_active.objects.get(id_classe_active=id_classe_active)
            if not classe_active.is_active:
                messages.error(request, "Cette classe active est déjà supprimée.")
                return redirect('create_classes_active')

            dependencies = []
            if Cours_par_classe.objects.filter(id_classe=classe_active).exists():
                dependencies.append("cours par classe")
            if Eleve_inscription.objects.filter(id_classe=classe_active).exists():
                dependencies.append("inscriptions d'élèves")

            if dependencies:
                error_msg = f"Impossible de supprimer la classe active car elle est utilisée dans : {', '.join(dependencies)}."
                messages.error(request, error_msg)
                return redirect('create_classes_active')

            classe_active.is_active = False
            classe_active.save()
            messages.success(request, "Classe active supprimée avec succès.")
            return redirect('create_classes_active')

        except Classe_active.DoesNotExist:
            messages.error(request, "Classe active non trouvée.")
            return redirect('create_classes_active')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_classes_active')

    messages.error(request, "Méthode non autorisée.")
    return redirect('create_classes_active')

@login_required
@module_required("Administration")
def delete_classe_cycle_actif(request, id_cycle_actif):

    if request.method == "POST":
        try:
            cycle_actif = Classe_cycle_actif.objects.get(id_cycle_actif=id_cycle_actif)
            if not cycle_actif.is_active:
                messages.error(request, "Ce cycle actif est déjà supprimé.")
                return redirect('create_classes_cycle_active')

            dependencies = []
            if Classe_active.objects.filter(cycle_id=cycle_actif).exists():
                dependencies.append("classes actives")
            if Cours_par_cycle.objects.filter(cycle_id=cycle_actif).exists():
                dependencies.append("cours par cycle")
            if Eleve_inscription.objects.filter(id_classe_cycle=cycle_actif).exists():
                dependencies.append("inscriptions d'élèves")

            if dependencies:
                error_msg = f"impossible de supprimer le cycle actif car il est utilisé dans : {', '.join(dependencies)}."
                messages.error(request, error_msg)
                return redirect('create_classes_cycle_active')

            cycle_actif.is_active = False
            cycle_actif.save()
            messages.success(request, "Cycle actif supprimé avec succès.")
            return redirect('create_classes_cycle_active')

        except Classe_cycle_actif.DoesNotExist:
            messages.error(request, "Cycle actif non trouvé.")
            return redirect('create_classes_cycle_active')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_classes_cycle_active')
    messages.error(request, "Méthode non autorisée.")
    return redirect('create_classes_cycle_active')

