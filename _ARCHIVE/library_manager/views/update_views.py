
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError
from library_manager.models import Armoire,Compartiment,Categorie,Livre,Exemplaire,Emprunt
import json
from django.contrib.auth.decorators import login_required
from MonEcole_app.models import Eleve, Annee, Campus, Classe_cycle_actif, Classe_active, Personnel,Eleve_inscription
from datetime import datetime
import json
from django.utils.timezone import now
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime


@login_required
@csrf_protect
def update_compartiment(request, id):
    if request.method == 'POST':
        try:
            compartiment = Compartiment.objects.get(id=id)
            data = json.loads(request.body.decode('utf-8'))
            armoire_id = data.get('armoire_id')
            numero = data.get('numero')
            capacite = data.get('capacite')

            if not armoire_id:
                return JsonResponse({'success': False, 'error': 'L\'armoire doit être sélectionnée.'}, status=400)
            if not numero:
                return JsonResponse({'success': False, 'error': 'Le numéro ne peut pas être vide.'}, status=400)
            if not capacite or int(capacite) <= 0:
                return JsonResponse({'success': False, 'error': 'La capacité doit être un nombre positif.'}, status=400)

            try:
                armoire = Armoire.objects.get(id=armoire_id)
            except Armoire.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Armoire non trouvée.'}, status=400)

            if (compartiment.armoire_id != int(armoire_id) or 
                compartiment.numero != numero or 
                compartiment.capacite != int(capacite)):
                compartiment.armoire = armoire
                compartiment.numero = numero
                compartiment.capacite = int(capacite)
                try:
                    compartiment.full_clean() 
                    compartiment.save()
                    return JsonResponse({'success': True})
                except ValidationError as e:
                    error_msg = 'Erreur de validation : ' + str(e)
                    if 'unique_armoire_numero' in str(e):
                        error_msg = 'Ce numéro existe déjà pour cette armoire.'
                    return JsonResponse({'success': False, 'error': error_msg}, status=400)
            else:
                return JsonResponse({'success': True})  
        except Compartiment.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Compartiment non trouvé.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Requête JSON invalide.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erreur serveur : {str(e)}'}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

@login_required
@csrf_protect
def update_armoire(request, id):
    if request.method == 'POST':
        try:
            armoire = Armoire.objects.get(id=id)
            data = json.loads(request.body) if request.body else {}
            new_nom = data.get('nom')

            if not new_nom:
                return JsonResponse({'success': False, 'error': 'Le nom ne peut pas être vide.'}, status=400)

            if armoire.nom != new_nom:
                armoire.nom = new_nom
                try:
                    armoire.full_clean() 
                    armoire.save()
                    return JsonResponse({'success': True})
                except ValidationError as e:
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
            else:
                return JsonResponse({'success': True})  

        except Armoire.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Armoire non trouvée.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

@login_required
@csrf_protect
def update_categorie(request, id):
    if request.method == 'POST':
        try:
            categorie = Categorie.objects.get(id=id)
            data = json.loads(request.body.decode('utf-8'))
            new_nom = data.get('nom')
            if not new_nom:
                return JsonResponse({'success': False, 'error': 'Le nom ne peut pas être vide.'}, status=400)
            if categorie.nom != new_nom:
                categorie.nom = new_nom
                try:
                    categorie.full_clean()  
                    categorie.save()
                    return JsonResponse({'success': True})
                except ValidationError as e:
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
            else:
                return JsonResponse({'success': True}) 

        except Categorie.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Catégorie non trouvée.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Requête JSON invalide.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

@login_required
@csrf_protect
def update_livre(request, id):
    if request.method == 'POST':
        try:
            livre = Livre.objects.get(id=id)
            data = json.loads(request.body.decode('utf-8'))
            new_titre = data.get('titre')
            new_auteur = data.get('auteur')
            new_isbn = data.get('isbn')
            new_categorie_id = data.get('categorie_id')
            new_compartiment_id = data.get('compartiment_id')
            new_etat = data.get('etat')
            new_exemplaires = data.get('nombre_exemplaires')

            if not new_titre:
                return JsonResponse({'success': False, 'error': 'Le titre ne peut pas être vide.'}, status=400)
            if not new_auteur:
                return JsonResponse({'success': False, 'error': 'L\'auteur ne peut pas être vide.'}, status=400)
            if not new_categorie_id:
                return JsonResponse({'success': False, 'error': 'La catégorie doit être sélectionnée.'}, status=400)
            if not new_compartiment_id:
                return JsonResponse({'success': False, 'error': 'Le compartiment doit être sélectionné.'}, status=400)
            if not new_etat or new_etat not in ['NEUF', 'BON', 'USÉ', 'ENDOMMAGÉ']:
                return JsonResponse({'success': False, 'error': 'L\'état doit être valide.'}, status=400)
            if not new_exemplaires or int(new_exemplaires) < 1:
                return JsonResponse({'success': False, 'error': 'Le nombre d\'exemplaires doit être un entier positif.'}, status=400)

            try:
                new_categorie = Categorie.objects.get(id=new_categorie_id)
            except Categorie.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Catégorie non trouvée.'}, status=400)
            try:
                new_compartiment = Compartiment.objects.get(id=new_compartiment_id)
            except Compartiment.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Compartiment non trouvé.'}, status=400)

            if new_isbn and (livre.isbn != new_isbn) and Livre.objects.filter(isbn=new_isbn).exclude(id=id).exists():
                return JsonResponse({'success': False, 'error': 'Cet ISBN existe déjà.'}, status=400)

            livre.titre = new_titre
            livre.auteur = new_auteur
            livre.isbn = new_isbn if new_isbn else None
            livre.categorie = new_categorie
            livre.compartiment = new_compartiment
            livre.etat = new_etat
            livre.nombre_exemplaires = int(new_exemplaires)
            try:
                livre.full_clean()  
                livre.save()
                return JsonResponse({'success': True})
            except ValidationError as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)

        except Livre.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Livre non trouvé.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Requête JSON invalide.'}, status=400)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Le nombre d\'exemplaires doit être un nombre valide.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

@login_required
@csrf_protect
def update_livre_exemplaire(request, id):
    if request.method == 'POST':
        try:
            livre_exemplaire = Exemplaire.objects.get(id=id)
            data = json.loads(request.body.decode('utf-8'))
            new_livre_id = data.get('livre_id')
            new_numero = data.get('numero_inventaire')
            new_etat = data.get('etat')

            if not new_livre_id:
                return JsonResponse({'success': False, 'error': 'Le livre doit être sélectionné.'}, status=400)
            if not new_numero:
                return JsonResponse({'success': False, 'error': 'Le numéro d\'inventaire ne peut pas être vide.'}, status=400)
            if not new_etat or new_etat not in ['NEUF', 'BON', 'USÉ', 'ENDOMMAGÉ']:
                return JsonResponse({'success': False, 'error': 'L\'état doit être valide.'}, status=400)

            try:
                new_livre = Livre.objects.get(id=new_livre_id)
            except Livre.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Livre non trouvé.'}, status=400)

            if livre_exemplaire.numero_inventaire != new_numero and \
               Exemplaire.objects.filter(numero_inventaire=new_numero).exclude(id=id).exists():
                return JsonResponse({'success': False, 'error': 'Ce numéro d\'inventaire existe déjà.'}, status=400)

            livre_exemplaire.livre = new_livre
            livre_exemplaire.numero_inventaire = new_numero
            livre_exemplaire.etat = new_etat
            try:
                livre_exemplaire.full_clean() 
                livre_exemplaire.save()
                return JsonResponse({'success': True})
            except ValidationError as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)

        except Exemplaire.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Exemplaire de livre non trouvé.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Requête JSON invalide.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)


@login_required
@csrf_protect
def update_emprunt(request, id):
    if request.method == 'POST':
        try:
            emprunt = Emprunt.objects.get(id=id)
            data = json.loads(request.body.decode('utf-8'))
            new_annee_id = data.get('id_annee')
            new_campus_id = data.get('id_campus')
            new_cycle_id = data.get('id_cycle_actif')
            new_classe_id = data.get('id_classe_active')
            new_eleve_id = data.get('id_eleve')
            new_livre_id = data.get('id_livre')
            new_date_emprunt = data.get('date_emprunt')
            new_date_retour = data.get('date_retour_prevue')

            if not new_annee_id:
                return JsonResponse({'success': False, 'error': 'L\'année doit être sélectionnée.'}, status=400)
            if not new_campus_id:
                return JsonResponse({'success': False, 'error': 'Le campus doit être sélectionné.'}, status=400)
            if not new_cycle_id:
                return JsonResponse({'success': False, 'error': 'Le cycle doit être sélectionné.'}, status=400)
            if not new_classe_id:
                return JsonResponse({'success': False, 'error': 'La classe doit être sélectionnée.'}, status=400)
            if not new_eleve_id:
                return JsonResponse({'success': False, 'error': 'L\'élève doit être sélectionné.'}, status=400)
            if not new_livre_id:
                return JsonResponse({'success': False, 'error': 'Le livre doit être sélectionné.'}, status=400)
            if not new_date_emprunt:
                return JsonResponse({'success': False, 'error': 'La date d\'emprunt ne peut pas être vide.'}, status=400)
            if not new_date_retour:
                return JsonResponse({'success': False, 'error': 'La date de retour prévue ne peut pas être vide.'}, status=400)

            try:
                new_annee = Annee.objects.get(id_annee=new_annee_id)
            except Annee.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Année non trouvée.'}, status=400)
            try:
                new_campus = Campus.objects.get(id_campus=new_campus_id)
            except Campus.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Campus non trouvé.'}, status=400)
            try:
                new_cycle = Classe_cycle_actif.objects.get(id_cycle_actif=new_cycle_id)
            except Classe_cycle_actif.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Cycle non trouvé.'}, status=400)
            try:
                new_classe = Classe_active.objects.get(id_classe_active=new_classe_id)
            except Classe_active.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Classe non trouvée.'}, status=400)
            try:
                new_eleve = Eleve.objects.get(id_eleve=new_eleve_id)
            except Eleve.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Élève non trouvé.'}, status=400)
            try:
                new_livre = Livre.objects.get(id=new_livre_id)
            except Livre.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Livre non trouvé.'}, status=400)

            if not Classe_cycle_actif.objects.filter(id_cycle_actif=new_cycle_id, id_annee__id_annee=new_annee_id, id_campus__id_campus=new_campus_id).exists():
                return JsonResponse({'success': False, 'error': 'Ce cycle n\'est pas valide pour l\'année et le campus sélectionnés.'}, status=400)
            if not Classe_active.objects.filter(id_classe_active=new_classe_id, id_annee__id_annee=new_annee_id, id_campus__id_campus=new_campus_id, cycle_id__id_cycle_actif=new_cycle_id).exists():
                return JsonResponse({'success': False, 'error': 'Cette classe n\'est pas valide pour l\'année, le campus et le cycle sélectionnés.'}, status=400)
            if not Eleve_inscription.objects.filter(
                id_annee__id_annee=new_annee_id,
                id_campus__id_campus=new_campus_id,
                id_classe_cycle__id_cycle_actif=new_cycle_id,
                id_classe__id_classe_active=new_classe_id,
                id_eleve__id_eleve=new_eleve_id,
                status=1
            ).exists():
                return JsonResponse({'success': False, 'error': 'Cet élève n\'est pas inscrit dans cette classe pour l\'année, le campus et le cycle sélectionnés.'}, status=400)

            try:
                date_emprunt = datetime.strptime(new_date_emprunt, '%Y-%m-%d').date()
                date_retour = datetime.strptime(new_date_retour, '%Y-%m-%d').date()
                if date_retour < date_emprunt:
                    return JsonResponse({'success': False, 'error': 'La date de retour ne peut pas être antérieure à la date d\'emprunt.'}, status=400)
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Format de date invalide.'}, status=400)

            emprunt.id_annee = new_annee
            emprunt.id_campus = new_campus
            emprunt.id_cycle_actif = new_cycle
            emprunt.id_classe_active = new_classe
            emprunt.id_eleve = new_eleve
            emprunt.id_livre = new_livre
            emprunt.date_emprunt = date_emprunt
            emprunt.date_retour_prevue = date_retour
            try:
                emprunt.full_clean()  
                emprunt.save()
                return JsonResponse({'success': True})
            except ValidationError as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)

        except Emprunt.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Emprunt non trouvé.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Requête JSON invalide.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

@login_required
@require_POST
def update_rendu(request):
    emprunt_id = request.POST.get("id")
    date_retour_effective = request.POST.get("date_retour_effective")
    try:
        emprunt = Emprunt.objects.get(id=emprunt_id)
        emprunt.rendu = True
        if date_retour_effective:
            try:
                emprunt.date_retour_effective = datetime.strptime(date_retour_effective, "%Y-%m-%d").date()
                if emprunt.date_retour_effective > timezone.now().date():
                    return JsonResponse({"success": False, "error": "La date de retour ne peut pas être dans le futur."})
            except ValueError:
                return JsonResponse({"success": False, "error": "Format de date invalide."})
        else:
            return JsonResponse({"success": False, "error": "Aucune date de retour fournie."})

        emprunt.save()
        livre = emprunt.id_livre
        livre.disponible = True
        livre.save()
        return JsonResponse({
            "success": True,
            "date_retour_effective": emprunt.date_retour_effective.strftime("%Y-%m-%d")
        })
    except Emprunt.DoesNotExist:
        return JsonResponse({"success": False, "error": "Emprunt introuvable"})