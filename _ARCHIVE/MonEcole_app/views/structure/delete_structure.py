from ._initials import *

@login_required
@module_required("Administration")
def delete_periode(request, id_periode):


    if request.method == "POST":
        try:
            periode = RepartitionInstance.objects.get(id_instance=id_periode)

            if Eleve_note.objects.filter(id_periode=periode).exists():
                messages.error(request, "Impossible de supprimer la période car elle est utilisée quelque part.")
                return redirect('create_periode')

            periode.delete()
            messages.success(request, "Période supprimée avec succès.")
            return redirect('create_periode')

        except RepartitionInstance.DoesNotExist:
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
            trimestre = RepartitionInstance.objects.get(id_instance=id_trimestre)

            if RepartitionInstance.objects.filter(type_id=trimestre.id_instance).exists():
                messages.error(request, "Impossible de supprimer le trimestre car il est utilisé quelque part.")
                return redirect('create_trimestre')

            trimestre.delete()
            messages.success(request, "Trimestre supprimé avec succès.")
            return redirect('create_trimestre')

        except RepartitionInstance.DoesNotExist:
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

            dependencies = []
            from MonEcole_app.models.country_structure import EtablissementAnnee, EtablissementAnneeClasse
            if EtablissementAnnee.objects.filter(annee=annee).exists():
                dependencies.append("configurations établissement-année")

            if dependencies:
                error_msg = f"Impossible de supprimer l'année car elle est utilisée dans : {', '.join(dependencies)}."
                messages.error(request, error_msg)
                return redirect('create_annees')

            annee.etat_annee = "Clôturée"
            annee.save()
            messages.success(request, "Année clôturée avec succès.")
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
            # Les vérifications de dépendances se font sur les données locales
            if Eleve_inscription.objects.filter(id_campus=campus).exists():
                dependencies.append("inscriptions d'élèves")
            
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
            # Les classes sont gérées via le Hub - pas de suppression locale
            messages.info(request, "La gestion des classes est centralisée via le Hub.")
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
            # Les cycles sont gérés via le Hub - pas de suppression locale
            messages.info(request, "La gestion des cycles est centralisée via le Hub.")
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
            # Les classes actives sont gérées via le Hub
            messages.info(request, "La gestion des classes actives est centralisée via le Hub.")
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

            dependencies = []
            from MonEcole_app.models.country_structure import EtablissementAnneeClasse
            if EtablissementAnneeClasse.objects.filter(classe__cycle_id=cycle_actif.id_cycle_actif).exists():
                dependencies.append("classes actives")
            if Eleve_inscription.objects.filter(id_classe_cycle=cycle_actif).exists():
                dependencies.append("inscriptions d'élèves")

            if dependencies:
                error_msg = f"impossible de supprimer le cycle actif car il est utilisé dans : {', '.join(dependencies)}."
                messages.error(request, error_msg)
                return redirect('create_classes_cycle_active')

            messages.info(request, "La suppression des cycles est gérée via le Hub.")
            return redirect('create_classes_cycle_active')

        except Classe_cycle_actif.DoesNotExist:
            messages.error(request, "Cycle actif non trouvé.")
            return redirect('create_classes_cycle_active')
        except Exception as e:
            messages.error(request, "Une erreur s'est produite. Contactez l'administrateur.")
            return redirect('create_classes_cycle_active')
    messages.error(request, "Méthode non autorisée.")
    return redirect('create_classes_cycle_active')

