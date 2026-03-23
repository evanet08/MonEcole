import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from unidecode import unidecode

from ..models.country_structure import (
    Pays, StructurePedagogique, StructureAdministrative, PAYS_AFRIQUE_EST
)
from ..forms.country_structure_forms import (
    PaysForm, StructurePedagogiqueForm, StructureAdministrativeForm
)
from .tools.utils import get_user_info


def generate_code(nom):
    """Génère un code de 3 caractères à partir du nom."""
    if not nom: return ''
    # Convertir en ASCII (enlever accents) et majuscules
    clean_name = unidecode(nom).upper().replace(' ', '')
    # Prendre les 3 premiers caractères ou compléter avec des X
    return clean_name[:3] if len(clean_name) >= 3 else clean_name.ljust(3, 'X')


@login_required
def structuration_pays_view(request):
    """Vue principale pour la page de structuration par pays."""
    user_info = get_user_info(request)
    pays_existants = list(Pays.objects.values_list('sigle', flat=True))
    
    pays_list = []
    for sigle, nom in PAYS_AFRIQUE_EST:
        pays_list.append({
            'sigle': sigle,
            'nom': nom,
            'exists': sigle in pays_existants
        })
    
    context = {
        'pays_list': pays_list,
        'photo_profil': user_info.get('photo_profil'),
        'modules': user_info.get('modules'),
        'last_name': user_info.get('last_name'),
    }
    return render(request, 'parametrage/structuration_pays.html', context)


@login_required
@require_http_methods(["GET"])
def get_pays_data(request):
    """API pour récupérer les données d'un pays."""
    sigle = request.GET.get('sigle', '')
    nom = request.GET.get('nom', '')
    
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"GET_PAYS_DATA: sigle={sigle}, nom={nom}")
    
    if not sigle:
        return JsonResponse({'error': 'Sigle requis'}, status=400)
    
    try:
        pays = Pays.objects.get(sigle=sigle)
        structures_ped = list(pays.structures_pedagogiques.values('id_structure', 'code', 'nom', 'ordre').order_by('ordre'))
        structures_admin = list(pays.structures_administratives.values('id_structure', 'code', 'nom', 'ordre').order_by('ordre'))
        
        return JsonResponse({
            'exists': True,
            'pays': {
                'id_pays': pays.id_pays,
                'nom': pays.nom,
                'sigle': pays.sigle,
                'nLevelsStructuraux': pays.nLevelsStructuraux,
                'nLevelsAdministratifs': pays.nLevelsAdministratifs,
            },
            'structures_pedagogiques': structures_ped,
            'structures_administratives': structures_admin,
        })
    except Pays.DoesNotExist:
        return JsonResponse({
            'exists': False,
            'pays': {'nom': nom, 'sigle': sigle, 'nLevelsStructuraux': 0, 'nLevelsAdministratifs': 0},
            'structures_pedagogiques': [],
            'structures_administratives': [],
        })


@login_required
@require_http_methods(["POST"])
def save_pays(request):
    """API pour créer ou mettre à jour un pays."""
    try:
        data = json.loads(request.body)
        sigle = data.get('sigle')
        nom = data.get('nom')
        
        # Conversion robuste vers entier
        try:
            nLevelsStructuraux = int(data.get('nLevelsStructuraux') or 0)
            nLevelsAdministratifs = int(data.get('nLevelsAdministratifs') or 0)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Les nombres de niveaux doivent être des entiers.'}, status=400)
        
        if not sigle or not nom:
            return JsonResponse({'success': False, 'error': 'Sigle et nom requis'}, status=400)
        
        pays, created = Pays.objects.update_or_create(
            sigle=sigle,
            defaults={
                'nom': nom,
                'nLevelsStructuraux': nLevelsStructuraux,
                'nLevelsAdministratifs': nLevelsAdministratifs,
            }
        )
        return JsonResponse({
            'success': True, 
            'pays': {
                'sigle': pays.sigle, 
                'nLevelsStructuraux': pays.nLevelsStructuraux, 
                'nLevelsAdministratifs': pays.nLevelsAdministratifs
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def add_structure_pedagogique(request):
    try:
        data = json.loads(request.body)
        pays = get_object_or_404(Pays, sigle=data.get('pays_sigle'))
        if pays.structures_pedagogiques.count() >= pays.nLevelsStructuraux:
            return JsonResponse({'error': 'Limite atteinte'}, status=400)
        
        nom = data.get('nom')
        code = generate_code(nom)
        ordre = pays.structures_pedagogiques.count() + 1
        
        StructurePedagogique.objects.create(pays=pays, nom=nom, code=code, ordre=ordre)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def add_structure_administrative(request):
    try:
        data = json.loads(request.body)
        pays = get_object_or_404(Pays, sigle=data.get('pays_sigle'))
        if pays.structures_administratives.count() >= pays.nLevelsAdministratifs:
            return JsonResponse({'error': 'Limite atteinte'}, status=400)
        
        nom = data.get('nom')
        code = generate_code(nom)
        ordre = pays.structures_administratives.count() + 1
        
        StructureAdministrative.objects.create(pays=pays, nom=nom, code=code, ordre=ordre)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def delete_structure_pedagogique(request):
    try:
        data = json.loads(request.body)
        structure = get_object_or_404(StructurePedagogique, id_structure=data.get('id_structure'))
        pays = structure.pays
        structure.delete()
        # Réorganiser l'ordre
        for idx, s in enumerate(pays.structures_pedagogiques.order_by('ordre'), 1):
            s.ordre = idx
            s.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def delete_structure_administrative(request):
    try:
        data = json.loads(request.body)
        structure = get_object_or_404(StructureAdministrative, id_structure=data.get('id_structure'))
        pays = structure.pays
        structure.delete()
        # Réorganiser l'ordre
        for idx, s in enumerate(pays.structures_administratives.order_by('ordre'), 1):
            s.ordre = idx
            s.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def adjust_levels(request):
    try:
        data = json.loads(request.body)
        pays = get_object_or_404(Pays, sigle=data.get('pays_sigle'))
        adj_type = data.get('type')
        
        if adj_type == 'pedagogique' or adj_type == 'all':
            pays.nLevelsStructuraux = pays.structures_pedagogiques.count()
        if adj_type == 'administrative' or adj_type == 'all':
            pays.nLevelsAdministratifs = pays.structures_administratives.count()
            
        pays.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def generate_code_api(request):
    return JsonResponse({'code': generate_code(request.GET.get('nom', ''))})
