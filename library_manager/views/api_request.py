

from django.http import JsonResponse
from library_manager.models import Armoire,Categorie,Compartiment,Livre
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from MonEcole_app.models import Annee,Campus

@login_required
@csrf_exempt
def list_livres(request):
    if request.method == 'GET':
        try:
            livres = Livre.objects.all().values('id', 'titre')
            return JsonResponse({'success': True, 'livres': list(livres)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

@login_required
def get_armoires(request):
    if request.method == 'GET':
        try:
            armoires = Armoire.objects.all().values('id', 'nom')
            return JsonResponse({'success': True, 'armoires': list(armoires)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)





@login_required
@csrf_exempt
def list_categories(request):
    if request.method == 'GET':
        try:
            categories = Categorie.objects.all().values('id', 'nom')
            return JsonResponse({'success': True, 'categories': list(categories)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)

@login_required
@csrf_exempt
def list_compartiments(request):
    if request.method == 'GET':
        try:
            compartiments = Compartiment.objects.select_related('armoire').values('id', 'numero', 'armoire__nom')
            compartiments = [{'id': c['id'], 'numero': c['numero'], 'armoire_nom': c['armoire__nom']} for c in compartiments]
            return JsonResponse({'success': True, 'compartiments': compartiments})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée.'}, status=405)



# views.py


def get_categories_and_books(request):
    armoire_id = request.GET.get('armoire_id')
    if not armoire_id:
        return JsonResponse({'categories': []}) 

    # Récupérer les compartiments liés à l'armoire
    compartiments = Compartiment.objects.filter(armoire_id=armoire_id)

    # Récupérer les livres avec leurs catégories, en filtrant par compartiment
    livres = Livre.objects.filter(compartiment__in=compartiments,disponible = True).select_related('categorie')
    
    # Construire la structure de données
    categories_data = []
    categories = Categorie.objects.filter(livre__in=livres).distinct()
    
    for categorie in categories:
        livres_categorie = livres.filter(categorie=categorie)
        categories_data.append({
            'id': categorie.id,
            'name': categorie.nom,
            'books': [
                {
                    'id': livre.id,
                    'title': livre.titre,
                    'author': livre.auteur,
                    'type': 'pdf' if livre.etat == 'BON' else 'doc',  
                } for livre in livres_categorie
            ]
        })

    return JsonResponse({'categories': categories_data})


import logging

logger = logging.getLogger(__name__)

@login_required
def get_annees(request):
    try:
        annee_list = list(Annee.objects.all().values('id_annee', 'annee'))
        return JsonResponse({'annees': annee_list})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    
@login_required
def get_campus_options(request):
    try:
        campus = Campus.objects.filter(is_active=True).distinct().values('id_campus', 'campus')
        return JsonResponse({'campus': list(campus)})
    except Exception as e:
        logger.error(f"Erreur dans get_campus_options : {str(e)}")

