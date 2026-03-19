from ._initials import *
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from dateutil.relativedelta import relativedelta
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import re
from unidecode import unidecode
import re
import logging
from MonEcole_app.variables import CYCLES_ORDER
from MonEcole_app.forms import ClasseActiveResponsableForm
from MonEcole_app.models import UserModule
from MonEcole_app.views.tools.tenant_utils import (
    get_tenant_id, get_tenant_campus_qs, get_tenant_campus_ids,
    validate_campus_access, deny_cross_tenant_access, tenant_campus_filter
)



# Configurer le logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def calculer_ordre_cycle_actif(id_annee, id_campus):
    dernier_cycle = Classe_cycle_actif.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        is_active=True
    ).order_by('-ordre').first()

    if not dernier_cycle:
        return 1
    return dernier_cycle.ordre + 1

def get_classe_base_name(classe_name):
    cleaned_name = classe_name.strip().lower()
    cleaned_name = unidecode(cleaned_name)
    cleaned_name = re.sub(r'première', '1ere', cleaned_name)
    cleaned_name = re.sub(r'deuxieme', '2eme', cleaned_name)
    cleaned_name = re.sub(r'troisième', '3eme', cleaned_name)
    cleaned_name = re.sub(r'quatrième', '4eme', cleaned_name)
    cleaned_name = re.sub(r'cinquième', '5eme', cleaned_name)
    cleaned_name = re.sub(r'sixième', '6eme', cleaned_name)
    cleaned_name = re.sub(r'septième', '7eme', cleaned_name)
    cleaned_name = re.sub(r'huitième', '8eme', cleaned_name)
    cleaned_name = re.sub(r'neuvième', '9eme', cleaned_name)

    cleaned_name = re.sub(r'\s*[a-z]$', '', cleaned_name)
 
    return cleaned_name

def calculer_ordre_classe_active(classe_id, cycle_id, id_annee, id_campus):
    classe = get_object_or_404(Classe, id_classe=classe_id)
    cycle_actif = get_object_or_404(Classe_cycle_actif, id_cycle_actif=cycle_id)
    cycle = cycle_actif.cycle_id

    is_post_cycle = 'post' in cycle.cycle.lower()
    is_fondamentale = 'fondamentale' in cycle.cycle.lower()
    is_maternelle = 'maternelle' in cycle.cycle.lower()
    
    # is_maternelle = 'maternelle' in cycle.cycle.lower()
    # logger.debug(f"Cycle contient 'Post': {is_post_cycle}, 'Fondamentale': {is_fondamentale}, 'Maternelle': {is_maternelle}")

    if is_post_cycle or is_fondamentale or is_maternelle:
        classe_name = classe.classe
        # logger.debug(f"Nom de la classe: {classe_name}")

        # Regex pour capturer différents formats
        patterns = [
            r'^(\d+)',       # 2sc MTP, 3sc -> 2, 3
            r'(\d+)[èe]me',  # 4ème, 4eme
            r'(\d+)e',       # 4e
            r'(\d+)\s',      # 4 Année
            r'premi[eè]re',  # Première -> 1
            r'deuxi[eè]me',  # Deuxième -> 2
            r'troisi[eè]me', # Troisième -> 3
            r'quatri[eè]me', # Quatrième -> 4
            r'cinqui[eè]me', # Cinquième -> 5
            r'sixi[eè]me',   # Sixième -> 6
            r'septi[eè]me',  # Septième -> 7
            r'huiti[eè]me',  # Huitième -> 8
            r'neuvi[eè]me',  # Neuvième -> 9
        ]
        chiffre = None
        for pattern in patterns:
            match = re.search(pattern, classe_name, re.IGNORECASE)
            if match:
                if pattern in [r'premi[eè]re', r'deuxi[eè]me', r'troisi[eè]me', r'quatri[eè]me', r'cinqui[eè]me', r'sixi[eè]me', r'septi[eè]me', r'huiti[eè]me', r'neuvi[eè]me']:
                    mapping = {
                        'premiere': 1, 'première': 1,
                        'deuxieme': 2, 'deuxième': 2,
                        'troisieme': 3, 'troisième': 3,
                        'quatrieme': 4, 'quatrième': 4,
                        'cinquieme': 5, 'cinquième': 5,
                        'sixieme': 6, 'sixième': 6,
                        'septieme': 7, 'septième': 7,
                        'huitieme': 8, 'huitième': 8,
                        'neuvieme': 9, 'neuvième': 9
                    }
                    chiffre = mapping.get(match.group(0).lower())
                else:
                    chiffre = int(match.group(1))
                # logger.debug(f"Chiffre trouvé avec pattern {pattern}: {chiffre}")
                break

        if chiffre:
            # logger.debug(f"Ordre attribué (cycle Post/Fondamentale/Maternelle): {chiffre}")
            return chiffre
        else:
            # logger.warning(f"Aucun chiffre trouvé dans le nom de la classe: {classe_name}. Retour à l'ordre par défaut (1).")
            return 1

    # Logique par défaut pour les autres cycles
    # logger.debug("Application de la logique par défaut (cycle sans 'Post', 'Fondamentale', ou 'Maternelle')")
    classe_similaire = Classe_active.objects.filter(
        classe_id=classe_id,
        cycle_id=cycle_id,
        id_annee=id_annee,
        id_campus=id_campus,
        is_active=True
    ).first()

    if classe_similaire:
        ordre = classe_similaire.ordre if classe_similaire.ordre is not None else 1
        # logger.debug(f"Classe similaire trouvée: {classe_similaire.classe_id.classe}, Ordre réutilisé: {ordre}")
        return ordre

    # Trouver la dernière classe dans le même cycle et année
    # derniere_classe = Classe_active.objects.filter(
    #     cycle_id=cycle_id,
    #     id_annee=id_annee,
    #     id_campus=id_campus
    # ).order_by('-ordre').first()

    # if not derniere_classe:
    #     logger.debug("Aucune classe existante dans ce cycle/année/campus. Ordre: 1")
    #     return 1

    # ordre = derniere_classe.ordre + 1
    # logger.debug(f"Dernière classe trouvée: {derniere_classe.classe_id.classe}, Ordre incrémenté: {ordre}")
    return ordre

@login_required
@module_required("Administration")
def assigner_module_user(request):
    user_info = get_user_info(request)
    user_modules = user_info
    modules_assign_list = UserModule.objects.all()
    show_nav = False
    if 'assigner_module' in request.path:
        show_nav = True

    if request.method == 'POST':
        # print('information user:',request.POST)
        get_module_assigner = request.POST.get('module')  
        get_user_assigner = request.POST.get('user') 
        get_id_annee = request.POST.get('id_annee') 
        form_module_assigner = ModuleUserForm(request.POST)

        if form_module_assigner.is_valid():
            module_exist = UserModule.objects.filter(
                user=get_user_assigner,
                module=get_module_assigner,
                id_annee=get_id_annee
            )
            if module_exist.exists():
                messages.error(request, "Ce module est déjà assigné à cet utilisateur.")
                return redirect('assigner_module')
            try:
                module = Module.objects.get(id_module=get_module_assigner)  
                if module.module == "Institeur et son Espace":  
                    try:
                        annee_en_cours = Annee.objects.get(etat_annee="En Cours")
                        id_annee = annee_en_cours.id_annee
                    except Annee.DoesNotExist:
                        messages.error(
                            request,
                            "Aucune année scolaire en cours n'est définie. Contactez l'administrateur."
                        )
                        return redirect('assigner_module')

                    has_cours = Attribution_cours.objects.filter(
                        id_personnel=get_user_assigner,
                        id_annee=id_annee
                    ).exists()

                    if not has_cours:
                        messages.error(
                            request,
                            f"Cet utilisateur n'a pas de cours attribué pour l'année. Impossible d'assigner le module Pédagogique.vous devez lui attribuer au moins un cours"
                        )
                        return redirect('assigner_module')
            except Module.DoesNotExist:
                messages.error(request, "Module non trouvé.")
                return redirect('assigner_module')

            form_module_assigner.save()
            messages.success(request, "Module assigné à l'utilisateur avec succès !")
            return redirect('assigner_module')
    else:
        form_module_assigner = ModuleUserForm()

    return render(request, 'parametrage/index_parametrage.html', {
        'form_module_assigner': form_module_assigner,
        'modules_assign_list': modules_assign_list,
        'show_nav': show_nav,
        'form_type': 'modules_assigner',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name']
    })

@login_required
@module_required("Administration")
def create_module(request):
    user_info = get_user_info(request)
    user_modules = user_info
    modules_list = Module.objects.all()
    show_nav = request.resolver_match.url_name == 'create_module'

    if request.method == 'POST':
        # print("POST data:", request.POST)  
        form_module = ModuleForm(request.POST)
        if form_module.is_valid():
            form_module.save()
            messages.success(request, "Module ajouté avec succès !")
            return redirect('create_module')
        else:
            if 'module' in form_module.errors and any("already exists" in error for error in form_module.errors['module']):
                messages.error(request, "Ce module existe déjà.")
            else:
                messages.error(request, "Erreur dans le formulaire. Vérifiez les champs.")
            # print("Form errors:", form_module.errors) 
    else:
        form_module = ModuleForm()

    return render(request, 'parametrage/index_parametrage.html', {
        'form_module': form_module,
        'modules_list': modules_list,
        'show_nav': show_nav,
        'form_type': 'modules',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name']
    })
    
    


@login_required
@module_required("Administration")
def displaying_module_attribute_users(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form = ModuleUserForm()
    masq_field_unused = ['user','module']
    return render(request, 'parametrage/index_parametrage.html', {
        'form_type': 'modules_access',
        'form_module_access': form,
        "masq_field_unused":masq_field_unused,
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })






@login_required
@module_required("Administration")
def create_campus(request):
    campus_list = get_tenant_campus_qs(request)
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = False 
    if 'create_campus' in request.path: 
        show_nav = True  

    if request.method == 'POST':
        campus_form = CampusForm(request.POST)
        if campus_form.is_valid():
            new_campus = campus_form.save(commit=False)
            # Assigner automatiquement l'id_etablissement du tenant
            tenant_id = get_tenant_id(request)
            if tenant_id:
                new_campus.id_etablissement = tenant_id
            new_campus.save()
            messages.success(request,'campus crée avec succès!')
            return redirect('create_campus')
        else:
            if 'campus' in campus_form.errors and any("already exists" in error for error in campus_form.errors['campus']):
                    messages.error(request, "Ce campus existe déjà.")
            else:
                messages.error(request, "Erreur dans le formulaire. Vérifiez les champs.")
        
    else:
        campus_form = CampusForm()

    return render(request, 'parametrage/index_parametrage.html', {
        'campus_form': campus_form,
        'campus': campus_list,
        'show_nav': show_nav, 
        'form_type': 'campus', 
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Administration")
def create_institution(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = False
    if 'create_institution' in request.path:
        show_nav = True

    if request.method == 'POST':
        institution_form = InstitutionForm(request.POST, request.FILES)
        if institution_form.is_valid():
            institution = institution_form.save(commit=False)

            if 'logo_ecole' in request.FILES:
                logo_ecole_file = request.FILES['logo_ecole']
                nom_logo_ecole = logo_ecole_file.name 
                chemin_complet_ecole = os.path.join('logos/ecole', nom_logo_ecole)
                default_storage.save(chemin_complet_ecole, ContentFile(logo_ecole_file.read()))
                institution.logo_ecole.name = nom_logo_ecole

            if 'logo_ministere' in request.FILES:
                logo_ministere_file = request.FILES['logo_ministere']
                nom_logo_ministere = logo_ministere_file.name  
                chemin_complet_ministere = os.path.join('logos/ministere', nom_logo_ministere)
                default_storage.save(chemin_complet_ministere, ContentFile(logo_ministere_file.read()))
                institution.logo_ministere.name = nom_logo_ministere

            institution.save()

            messages.success(request, "Une institution a été créée avec succès !")
            return redirect('create_institution')
        else:
            messages.error(request, "Erreur dans le formulaire. Veuillez vérifier les données.")
    else:
        institution_form = InstitutionForm()
        institution_infos = Institution.objects.all()

    return render(request, 'parametrage/index_parametrage.html', {
        'institution_form': institution_form,
        'institution_infos': institution_infos,
        'show_nav': show_nav,
        'form_type': 'institution',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name']
    })   

@login_required
@module_required("Administration")
def create_annee_scolaire(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = False  

    if 'create_annees' in request.path:  
        show_nav = True 

    if request.method == 'POST':
        annee = request.POST.get('annee')
        anne_form = AnneeForm(request.POST)
        if anne_form.is_valid():
            annee_existant = Annee.objects.filter(annee=annee)
            if annee_existant.exists():
                messages.error(request, "Désolé ! L'année que vous essayez de créer existe déjà !")
                return redirect('create_annees')
            else:
                new_annee = anne_form.save(commit=False)

                annee_en_cours = Annee.objects.filter(etat_annee='En Cours').exists()

                if not annee_en_cours:
                    new_annee.etat_annee = 'En Cours'  
                else:
                    new_annee.etat_annee = 'En attente' 

                new_annee.save()
                return redirect('create_annees') 
    else:
        annee_form = AnneeForm()
        anne_list = Annee.objects.all()

    return render(request, 'parametrage/index_parametrage.html', {
        'annee_form': annee_form,
        'annees': anne_list,
        'show_nav': show_nav, 
        'form_type': 'annees',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name'] 
    })

@login_required
@module_required("Administration")
def create_classe_cycle(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = False  

    if 'create_classes_cycle' in request.path:  
        show_nav = True  

    if request.method == 'POST':
        cycle = request.POST.get('cycle')
        classe_cycle_form = ClasseCycleForm(request.POST)

        if classe_cycle_form.is_valid():
            classes_existant = Classe_cycle.objects.filter(cycle=cycle)
            if classes_existant.exists():
                messages.error(request, 'Désolé, la classe que vous souhaitez insérer existe déjà')
                return redirect('create_classes_cycle')
            else:
                classe_cycle_form.save()
                messages.success(request, f"L'enregistrement de {cycle} a été effectué avec succès!")
                return redirect('create_classes_cycle')
    else:
        classe_cycle_form = ClasseCycleForm()
      
    classe_cycle_list = Classe_cycle.objects.all()
    return render(request, 'parametrage/index_parametrage.html', {
        'class_cycle_form': classe_cycle_form,  
        'classes_cycle': classe_cycle_list,
        'show_nav': show_nav, 
        'form_type': 'classes_cycles',  
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Administration")
def create_classe_cycle_active(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = 'create_classes_cycle_active' in request.path

    if request.method == 'POST':
        cycle = request.POST.get('cycle_id')
        id_annee = request.POST.get('id_annee')
        id_campus = request.POST.get('id_campus')
        nbre_classe = request.POST.get('nbre_classe_par_cycle_actif')
        classe_cycle_actif_form = ClasseCycle_actifForm(request.POST)

        if classe_cycle_actif_form.is_valid():
            if not nbre_classe or int(nbre_classe) <= 0:
                messages.error(request, "Le nombre de classes par cycle actif doit être supérieur à 0.")
                return redirect('create_classes_cycle_active')

            if Classe_cycle_actif.objects.filter(
                id_annee=id_annee,
                id_campus=id_campus,
                cycle_id=cycle
            ).exists():
                messages.error(request, 'Désolé, le cycle que vous souhaitez insérer existe déjà.')
                return redirect('create_classes_cycle_active')
            
            current_cycle_name = Classe_cycle.objects.get(id_cycle=cycle).cycle  
            current_index = CYCLES_ORDER.index(current_cycle_name)

            missing_cycles = []
            for i in range(current_index):
                expected = CYCLES_ORDER[i]
                if not Classe_cycle_actif.objects.filter(
                    id_annee=id_annee,
                    id_campus=id_campus,
                    cycle_id__cycle=expected  
                ).exists():
                    missing_cycles.append(expected)

            if missing_cycles:
                messages.error(
                    request,
                    f"Veuillez d'abord créer le(s) cycle(s) précédent(s) avant celui-ci : {', '.join(missing_cycles)}"
                )
                return redirect('create_classes_cycle_active')

            ordre = calculer_ordre_cycle_actif(id_annee, id_campus)
            classe_cycle_actif = classe_cycle_actif_form.save(commit=False)
            classe_cycle_actif.ordre = ordre
            classe_cycle_actif.save()
            messages.success(request, f"L'enregistrement a été effectué avec succès !")
            return redirect('create_classes_cycle_active')

    else:
        classe_cycle_actif_form = ClasseCycle_actifForm()
    campus_ids = get_tenant_campus_ids(request)
    classe_cycle_list = Classe_cycle_actif.objects.filter(
        is_active=True,
        id_campus__in=campus_ids
    )

    return render(request, 'parametrage/index_parametrage.html', {
        'class_cycle_act_form': classe_cycle_actif_form,
        'classes_cycle_actif': classe_cycle_list,
        'show_nav': show_nav,
        'form_type': 'classes_cycles_actif',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Administration")
def create_classe(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = False  

    if 'create_classes' in request.path:  
        show_nav = True  

    if request.method == 'POST':
        classe = request.POST.get('classe')
        class_form = ClasseForm(request.POST)
        if class_form.is_valid():
            classes_existant  = Classe.objects.filter(classe = classe)
            if classes_existant.exists():
                messages.error(request,'Désolé;La classe que vous souhaitez insérer existe déjà')
                return redirect('create_classes')
            else:
                class_form.save()
                messages.success(request,"l'enregistrement de "+classe+" effectué avec succès!")
                return redirect('create_classes') 
    else:
        class_form = ClasseForm()
        classe_list = Classe.objects.all()
    return render(request, 'parametrage/index_parametrage.html', {
        'class_form': class_form,
        'classes': classe_list,
        'show_nav': show_nav,  
        'form_type': 'classes',  
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Administration")
def create_classe_active(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = 'create_classes_active' in request.path

    if request.method == 'POST':
        classe = request.POST.get('classe_id')
        campus = request.POST.get('id_campus')
        cycle_id = request.POST.get('cycle_id')
        id_annee = request.POST.get('id_annee')
        groupe = request.POST.get('groupe') or None
        class_active_form = Classe_active_Form(request.POST)

        if class_active_form.is_valid():
            cycle_obj = get_object_or_404(Classe_cycle_actif, id_cycle_actif=cycle_id)
            if cycle_obj.nbre_classe_par_cycle_actif:
                classes_count = Classe_active.objects.filter(
                    cycle_id=cycle_id,
                    id_annee=id_annee,
                    id_campus=campus
                ).count()
                if classes_count >= cycle_obj.nbre_classe_par_cycle_actif:
                    messages.error(
                        request,
                        f"Le nombre maximum de classes ({cycle_obj.nbre_classe_par_cycle_actif}) pour ce cycle est atteint."
                    )
                    return redirect('create_classes_active')

            classe_avec_groupe = Classe_active.objects.filter(
                id_annee=id_annee,
                id_campus=campus,
                cycle_id=cycle_id,
                classe_id=classe,
                groupe=groupe
            )
            if classe_avec_groupe.exists():
                messages.error(request, 'Désolé, cette classe avec ce groupe existe déjà.')
                return redirect('create_classes_active')

            if not groupe:
                groupes_existants = Classe_active.objects.filter(
                    id_annee=id_annee,
                    cycle_id=cycle_id,
                    classe_id=classe
                ).exclude(groupe__isnull=True)
                if groupes_existants.exists():
                    messages.error(
                        request,
                        "Impossible de créer cette classe sans groupe : des groupes existent déjà pour cette classe."
                    )
                    return redirect('create_classes_active')

            classe_sans_groupe = Classe_active.objects.filter(
                id_annee=id_annee,
                cycle_id=cycle_id,
                classe_id=classe,
                groupe__isnull=True
            ).first()

            if classe_sans_groupe and groupe:
                classe_sans_groupe.groupe = groupe
                classe_sans_groupe.save()
                messages.success(request, "L'enregistrement a été mis à jour avec succès (groupe ajouté).")
                return redirect('create_classes_active')

            ordre = calculer_ordre_classe_active(classe, cycle_id, id_annee, campus)

            classe_active = class_active_form.save(commit=False)
            classe_active.ordre = ordre
            classe_active.save()
            messages.success(request, f"L'enregistrement a été effectué avec succès !")
            return redirect('create_classes_active')

    else:
        class_active_form = Classe_active_Form()

    campus_ids = get_tenant_campus_ids(request)
    classe_active_list = Classe_active.objects.filter(
        is_active=True,
        id_campus__in=campus_ids
    )

    return render(request, 'parametrage/index_parametrage.html', {
        'class_active_form': class_active_form,
        'classe_active_list': classe_active_list,
        'show_nav': show_nav,
        'form_type': 'classes_active',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@csrf_exempt
@module_required("Administration")
def create_annee_trimestre(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_trimestre = AnneeTrimestreForm()
    show_nav = 'create_annee_trimestre' in request.path

    if request.method == 'POST':
        try:
            if request.content_type != 'application/json':
                return JsonResponse({"success": False, "message": "Requête invalide, JSON attendu"}, status=400)

            data = json.loads(request.body)
            trimestre_id = int(data.get('trimestre'))
            classe_id = int(data.get('id_classe'))
            cycle_id = int(data.get('id_cycle'))
            annee_id = int(data.get('id_annee'))
            campus_id = int(data.get('id_campus'))
            date_ouverture_str = data.get('debut')

            try:
                date_ouverture = datetime.strptime(date_ouverture_str, '%Y-%m-%d').date()
                date_cloture = date_ouverture + relativedelta(months=3)
            except Exception:
                return JsonResponse({"success": False, "message": "Date invalide. Format attendu : YYYY-MM-DD"}, status=400)

            trimestre_obj = get_object_or_404(RepartitionInstance, id_instance=trimestre_id)
            classe_obj = get_object_or_404(Classe_active, id_classe_active=classe_id)
            cycle_obj = get_object_or_404(Classe_cycle_actif, id_cycle_actif=cycle_id)
            annee_obj = get_object_or_404(Annee, id_annee=annee_id)
            campus_obj = get_object_or_404(Campus, id_campus=campus_id)

            if not classe_obj.ordre:
                classe_obj.ordre = calculer_ordre_classe_active(classe_id, cycle_id, annee_id, campus_id)
                classe_obj.save()

            if cycle_obj.nbre_classe_par_cycle_actif:
                classes_count = Classe_active.objects.filter(
                    cycle_id=cycle_id,
                    id_annee=annee_id,
                    id_campus=campus_id
                ).count()
                if classes_count >= cycle_obj.nbre_classe_par_cycle_actif:
                    return JsonResponse({
                        "success": False,
                        "message": f"Le nombre maximum de classes ({cycle_obj.nbre_classe_par_cycle_actif}) pour ce cycle est atteint."
                    }, status=400)

            match = re.search(r'Trimestre\s*(\d)', trimestre_obj.trimestre)
            if not match:
                return JsonResponse({"success": False, "message": "Le nom du trimestre doit contenir un numéro."}, status=400)
            numero_actuel = int(match.group(1))

            trimestres_existant = Annee_trimestre.objects.filter(
                id_classe=classe_obj,
                id_cycle=cycle_obj,
                id_annee=annee_obj,
                id_campus=campus_obj
            ).select_related('repartition')

            numeros_existants = []
            for t in trimestres_existant:
                m = re.search(r'Trimestre\s*(\d)', t.repartition.nom)
                if m:
                    numeros_existants.append(int(m.group(1)))

            if numero_actuel != len(numeros_existants) + 1:
                return JsonResponse({
                    "success": False,
                    "message": f"Veuillez d'abord créer le Trimestre {len(numeros_existants) + 1}."
                }, status=409)

            if any(numero_actuel == n for n in numeros_existants):
                return JsonResponse({"success": False, "message": "Ce trimestre est déjà enregistré pour cette classe."}, status=409)

            etat = 'En attente'
            if not Annee_trimestre.objects.filter(
                id_annee=annee_obj,
                id_campus=campus_obj,
                id_cycle=cycle_obj,
                id_classe=classe_obj,
                isOpen=True
            ).exists():
                etat = 'En cours'

            Annee_trimestre.objects.create(
                trimestre=trimestre_obj,
                debut=date_ouverture,
                fin=date_cloture,
                id_classe=classe_obj,
                id_cycle=cycle_obj,
                id_annee=annee_obj,
                id_campus=campus_obj,
                isOpen=(etat == 'En cours')
            )

            return JsonResponse({
                "success": True,
                "message": f"Trimestre {numero_actuel} ajouté avec succès !"
            })

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Format JSON invalide."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Erreur interne : {str(e)}"}, status=500)

    campus_ids = get_tenant_campus_ids(request)
    trimestres = Annee_trimestre.objects.filter(id_campus__in=campus_ids)
    return render(request, 'parametrage/index_parametrage.html', {
        'trimestres_classes': trimestres,
        'form_trimestre_class': form_trimestre,
        'show_nav': show_nav,
        'form_type': 'trimestres_class',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

# @login_required
# @module_required("Administration")
# def create_trimestre(request):
#     user_info = get_user_info(request)
#     user_modules = user_info
#     show_nav = 'create_trimestre' in request.path

#     if request.method == 'POST':
#         trimestre = request.POST.get('trimestre')
#         date_ouverture_str = request.POST.get('date_ouverture')
#         trimestr_form = TrimesterForm(request.POST)
#         try:
#             date_ouverture = datetime.strptime(date_ouverture_str, '%Y-%m-%d').date()
#             date_cloture = date_ouverture + relativedelta(months=3)
#         except:
#             messages.error(request, "Date invalide.")
#             return redirect('create_trimestre')

#         if trimestr_form.is_valid():
#             if Trimestre.objects.filter(trimestre=trimestre).exists():
#                 messages.error(request, "Désolé; Le trimestre que vous souhaitez insérer existe déjà")
#                 return redirect('create_trimestre')
            
#             if Trimestre.objects.filter(date_ouverture=date_ouverture, date_cloture=date_cloture).exists():
#                 messages.error(request, "Un trimestre existe déjà pour cette période.")
#                 return redirect('create_trimestre')

#             index_trimestre = dict(trimestres_default).keys()
#             ordre = list(dict(trimestres_default).keys())
#             try:
#                 current_index = ordre.index(trimestre)
#                 if current_index > 0:
#                     trimestre_precedent = ordre[current_index - 1]
#                     if not Trimestre.objects.filter(trimestre=trimestre_precedent).exists():
#                         messages.error(request, f"Vous devez d'abord créer {trimestre_precedent} avant {trimestre}.")
#                         return redirect('create_trimestre')
#             except ValueError:
#                 messages.error(request, "Trimestre invalide.")
#                 return redirect('create_trimestre')

#             etat = 'En attente'
#             if not Trimestre.objects.filter(etat_trimestre='En cours').exists():
#                 etat = 'En cours'

#             new_trim = trimestr_form.save(commit=False)
#             new_trim.etat_trimestre = etat
#             new_trim.save()

#             messages.success(request, f"L'enregistrement de {trimestre} a été effectué avec succès!")
#             return redirect('create_trimestre')
#     else:
#         trimestr_form = TrimesterForm()

#     trimestre_list = Trimestre.objects.filter(is_active=True)
#     return render(request, 'parametrage/index_parametrage.html', {
#         'trimestre_form': trimestr_form,
#         'trimestres': trimestre_list,
#         'show_nav': show_nav,
#         'form_type': 'trimestres',
#         "photo_profil": user_modules['photo_profil'],
#         "modules": user_modules['modules'],
#         "last_name": user_modules['last_name']
#     })


@login_required
@module_required("Administration")
def create_trimestre(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = 'create_trimestre' in request.path

    if request.method == 'POST':
        trimestr_form = TrimesterForm(request.POST)
        trimestre = request.POST.get('trimestre')

        if trimestr_form.is_valid():
            if RepartitionInstance.objects.filter(nom=trimestre).exists():
                messages.error(request, "Désolé; Le trimestre que vous souhaitez insérer existe déjà")
                return redirect('create_trimestre')

            # Vérification de l'ordre des trimestres
            ordre = [key for key, _ in trimestres_default]
            try:
                current_index = ordre.index(trimestre)
                if current_index > 0:
                    trimestre_precedent = ordre[current_index - 1]
                    if not RepartitionInstance.objects.filter(nom=trimestre_precedent).exists():
                        messages.error(request, f"Vous devez d'abord créer {trimestre_precedent} avant {trimestre}.")
                        return redirect('create_trimestre')
            except ValueError:
                messages.error(request, "Trimestre invalide.")
                return redirect('create_trimestre')

            new_trim = trimestr_form.save()
            messages.success(request, f"L'enregistrement de {trimestre} a été effectué avec succès!")
            return redirect('create_trimestre')
    else:
        trimestr_form = TrimesterForm()

    trimestre_list = RepartitionInstance.objects.filter(is_active=True)
    return render(request, 'parametrage/index_parametrage.html', {
        'trimestre_form': trimestr_form,
        'trimestres': trimestre_list,
        'show_nav': show_nav,
        'form_type': 'trimestres',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name']
    })


# @login_required 
# @module_required("Administration")
# def create_periode(request):
#     user_info = get_user_info(request)
#     user_modules = user_info
#     show_nav = 'create_periode' in request.path

#     if request.method == 'POST':
#         periode_form = PeriodForm(request.POST)

#         if periode_form.is_valid():
#             periode = periode_form.cleaned_data['periode']
#             trimestre = periode_form.cleaned_data['id_trimestre']
#             date_debut = periode_form.cleaned_data['date_debut']
#             date_fin = periode_form.cleaned_data['date_fin']

#             if Periode.objects.filter(periode=periode).exists():
#                 messages.error(request, f'Désolé, la période "{periode}" existe déjà.')
#                 return redirect('create_periode')

#             if date_debut < trimestre.date_ouverture or date_fin > trimestre.date_cloture:
#                 messages.error(
#                     request,
#                     f"Les dates doivent être comprises entre {trimestre.date_ouverture} et {trimestre.date_cloture} pour le trimestre sélectionné."
#                 )
#                 return redirect('create_periode')

#             etat_periode = "En cours" if trimestre.etat_trimestre == "En Cours" else "En attente"

#             new_periode = periode_form.save(commit=False)
#             new_periode.etat_periode = etat_periode
#             new_periode.save()

#             messages.success(request, f"L'enregistrement de la période '{periode}' a été effectué avec succès.")
#             return redirect('create_periode')
#     else:
#         periode_form = PeriodForm()

#     periode_list = Periode.objects.filter(is_active=True)

#     return render(request, 'parametrage/index_parametrage.html', {
#         'periode_form': periode_form,
#         'periodes': periode_list,
#         'show_nav': show_nav,
#         'form_type': 'periodes',
#         "photo_profil": user_modules['photo_profil'],
#         "modules": user_modules['modules'],
#         "last_name": user_modules['last_name']
#     })


@login_required
@module_required("Administration")
def create_periode(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = 'create_periode' in request.path

    if request.method == 'POST':
        periode_form = PeriodForm(request.POST)

        if periode_form.is_valid():
            periode = periode_form.cleaned_data['periode']
            trimestre = periode_form.cleaned_data['id_trimestre']

            if RepartitionInstance.objects.filter(nom=periode, type_id=trimestre.id_instance if hasattr(trimestre, 'id_instance') else trimestre).exists():
                messages.error(request, f'Désolé, la période "{periode}" existe déjà pour ce trimestre.')
                return redirect('create_periode')

            new_periode = periode_form.save()
            messages.success(request, f"L'enregistrement de la période '{periode}' a été effectué avec succès.")
            return redirect('create_periode')
    else:
        periode_form = PeriodForm()

    periode_list = RepartitionInstance.objects.filter(is_active=True)

    return render(request, 'parametrage/index_parametrage.html', {
        'periode_form': periode_form,
        'periodes': periode_list,
        'show_nav': show_nav,
        'form_type': 'periodes',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

# =============================================CREATION DE LA STRUCTURE D'UNE INSTITUTION : no used

@login_required
@csrf_exempt
@module_required("Administration")
def create_annee_trimestre(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_trimestre = AnneeTrimestreForm()
    show_nav = 'create_annee_trimestre' in request.path

    if request.method == 'POST':
        try:
            if request.content_type != 'application/json':
                return JsonResponse({"success": False, "message": "Requête invalide, JSON attendu"}, status=400)

            data = json.loads(request.body)
            trimestre_id = int(data.get('trimestre'))
            classe_id = int(data.get('id_classe'))
            cycle_id = int(data.get('id_cycle'))
            annee_id = int(data.get('id_annee'))
            campus_id = int(data.get('id_campus'))
            date_ouverture_str = data.get('debut')

            try:
                date_ouverture = datetime.strptime(date_ouverture_str, '%Y-%m-%d').date()
                date_cloture = date_ouverture + relativedelta(months=3)
            except Exception:
                return JsonResponse({"success": False, "message": "Date invalide. Format attendu : YYYY-MM-DD"}, status=400)

            trimestre_obj = get_object_or_404(RepartitionInstance, id_instance=trimestre_id)
            classe_obj = get_object_or_404(Classe_active, id_classe_active=classe_id)
            cycle_obj = get_object_or_404(Classe_cycle_actif, id_cycle_actif=cycle_id)
            annee_obj = get_object_or_404(Annee, id_annee=annee_id)
            campus_obj = get_object_or_404(Campus, id_campus=campus_id)

            match = re.search(r'Trimestre\s*(\d)', trimestre_obj.nom)
            match_semestre = re.search(r'Semestre\s*(\d)', trimestre_obj.nom)
            if not match or match_semestre:
                return JsonResponse({"success": False, "message": "Le nom du trimestre/semstre doit contenir un numéro."}, status=400)
            numero_actuel = int(match.group(1))

            trimestres_existant = Annee_trimestre.objects.filter(
                id_classe=classe_obj,
                id_cycle=cycle_obj,
                id_annee=annee_obj,
                id_campus=campus_obj
            ).select_related('repartition')

            numeros_existants = []
            for t in trimestres_existant:
                m = re.search(r'Trimestre\s*(\d)', t.repartition.nom)
                if m:
                    numeros_existants.append(int(m.group(1)))

            if numero_actuel != len(numeros_existants) + 1:
                return JsonResponse({
                    "success": False,
                    "message": f"Veuillez d'abord créer le Trimestre {len(numeros_existants) + 1}."
                }, status=409)

            if any(numero_actuel == n for n in numeros_existants):
                return JsonResponse({"success": False, "message": "Ce trimestre est déjà enregistré pour cette classe."}, status=409)
          
            etat = 'En attente'
            if not Annee_trimestre.objects.filter(id_annee = annee_obj,id_campus=campus_obj,id_cycle=cycle_obj,id_classe=classe_obj,isOpen=True).exists():
                etat = 'En cours'

            Annee_trimestre.objects.create(
                trimestre=trimestre_obj,
                debut=date_ouverture,
                fin=date_cloture,
                id_classe=classe_obj,
                id_cycle=cycle_obj,
                id_annee=annee_obj,
                id_campus=campus_obj,
                isOpen=(etat == 'En cours')
            )

            return JsonResponse({
                "success": True,
                "message": f"Trimestre {numero_actuel} ajouté avec succès !"
            })

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "Format JSON invalide."}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Erreur interne : {str(e)}"}, status=500)

    trimestres = Annee_trimestre.objects.all()
    return render(request, 'parametrage/index_parametrage.html', {
        'trimestres_classes': trimestres,
        'form_trimestre_class': form_trimestre,
        'show_nav': show_nav,
        'form_type': 'trimestres_class',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Administration")
def create_annee_periode(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = False  
    form_periode = AnneePeriodeForm()
    
    if 'create_annee_periode' in request.path:  
        if request.method == 'POST':
            try:
                if request.content_type != 'application/json':
                    return JsonResponse({"success": False, "message": "Requête invalide, JSON attendu"}, status=400)

                data = json.loads(request.body)
                periode_id = int(data.get('periode'))
                classe_id = int(data.get('id_classe'))
                cycle_id = int(data.get('id_cycle'))
                annee_id = int(data.get('id_annee'))
                campus_id = int(data.get('id_campus'))
                trimestre_annee_id = int(data.get('id_trimestre_annee'))
                debut = data.get('debut') or None
                fin = data.get('fin') or None
                
                try:
                    periode_obj = get_object_or_404(RepartitionInstance, id_instance=periode_id)
                    classe_obj = get_object_or_404(Classe_active, id_classe_active=classe_id)
                    cycle_obj = get_object_or_404(Classe_cycle_actif, id_cycle_actif=cycle_id)
                    annee_obj = get_object_or_404(Annee, id_annee=annee_id)
                    campus_obj = get_object_or_404(Campus, id_campus=campus_id)
                    trimestre_annee_obj = get_object_or_404(Annee_trimestre, id_trimestre=trimestre_annee_id)
                except Exception:
                    return JsonResponse({"success": False, "message": "ID invalide (Objet non trouvé)"}, status=404)

                if not all([periode_obj, classe_obj, cycle_obj, annee_obj, campus_obj, trimestre_annee_obj]):
                    return JsonResponse({"success": False, "message": "Données incomplètes"}, status=400)
            
                if Annee_periode.objects.filter(
                    periode_id=periode_obj,
                    id_campus_id=campus_obj,
                    id_cycle_id=cycle_obj,
                    id_classe_id=classe_obj,
                    id_annee_id=annee_obj,
                    id_trimestre_annee_id=trimestre_annee_obj,
                ).exists():
                    return JsonResponse({"success": False, "message": "Période déjà existante pour cette classe"}, status=409)

                if debut and fin:
                    try:
                        debut_date = datetime.strptime(debut, '%Y-%m-%d').date()
                        fin_date = datetime.strptime(fin, '%Y-%m-%d').date()
                        if debut_date > fin_date:
                            return JsonResponse({"success": False, "message": "La date de début doit être antérieure à la date de fin"}, status=400)
                    except ValueError:
                        return JsonResponse({"success": False, "message": "Format de date invalide"}, status=400)
                elif (debut and not fin) or (not debut and fin):
                    return JsonResponse({"success": False, "message": "Veuillez fournir à la fois la date de début et la date de fin, ou aucune des deux"}, status=400)

                new_periode = Annee_periode.objects.create(
                    periode=periode_obj,
                    debut=debut,
                    fin=fin,
                    id_classe=classe_obj,
                    id_cycle=cycle_obj,
                    id_annee=annee_obj,
                    id_campus=campus_obj,
                    id_trimestre_annee=trimestre_annee_obj
                )

                return JsonResponse({
                    "success": True,
                    "message": "Période ajoutée avec succès !",
                })

            except json.JSONDecodeError as e:
                return JsonResponse({"success": False, "message": "Format JSON invalide"}, status=400)
            except ValueError as e:
                return JsonResponse({"success": False, "message": f"Erreur de validation : {str(e)}"}, status=400)
            except Exception as e:
                return JsonResponse({"success": False, "message": f"Erreur interne : {str(e)}"}, status=500)
        
    periodes_classes = Annee_periode.objects.all()
    
    return render(request, 'parametrage/index_parametrage.html', {
        'form_periode': form_periode,
        'periodes_classes': periodes_classes,
        'show_nav': show_nav, 
        'form_type': 'periodes_class',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

# ========================================== CREATION DU PERSONNEL ET LES ELEMENTS QUI VONT AVEC

@login_required
@module_required("Administration")
def ajouter_personnel(request):
    personnel_list = Personnel.objects.all()
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = 'ajouter_personnel' in request.path
    annee_actuelle = datetime.now().year  
    code_annee = str(annee_actuelle)[-2:]  
    ecole = Institution.objects.first()  
    sigle = ecole.sigle.lower() if ecole and ecole.sigle else "eco"  
    if request.method == 'POST':
        firstname = request.POST.get('first_name')
        lastname = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password', '').strip()
        if not password:  
            password = "12345"  
        compteur = Personnel.objects.count() + 1
        matricule = f"{sigle}-{code_annee}-{str(compteur).zfill(5)}"
        username = f"{matricule}@{sigle}.bi"

        form_personnel_user = PersonnelUserForm(request.POST)
        form_personnel = PersonnelForm(request.POST, request.FILES)

        if form_personnel_user.is_valid() and form_personnel.is_valid():
            existing_user = User.objects.filter(email=email)
            existing_personnel = Personnel.objects.filter(user__first_name = firstname,user__last_name = lastname)
            
            if existing_user.exists() or existing_personnel.exists():
                messages.error(request, "Un utilisateur avec ces informations, existe déjà !")
            else:
                user = form_personnel_user.save(commit=False)
                user.first_name = user.first_name.upper()
                user.last_name = ' '.join([part.capitalize() for part in user.last_name.split()])
                user.username = username  
                user.set_password(password) 
                user.save()   
                personnel = form_personnel.save(commit=False)
                personnel.user = user  
                personnel.matricule = matricule  
                personnel.codeAnnee = code_annee  
                personnel.save()  
                messages.success(request, f"Personnel enregistré avec succès ! Matricule : {matricule}")
            
            return redirect('ajouter_personnel')  
        else:
            messages.error(request, "Formulaire non validé !")
            return redirect('ajouter_personnel')  

    else:
        form_personnel = PersonnelForm()
        form_personnel_user = PersonnelUserForm()
    masq_field_p = ['addresse','telephone','imageUrl','date_naissance','pays','province','region','commune','etat_civil']
    masq_field_u = ['email','password','username']
    return render(request, 'parametrage/index_parametrage.html', {
        'form_personnel': form_personnel,
        'form_personnel_user': form_personnel_user,
        'personnel_list': personnel_list,
        'masq_field_u': masq_field_u,  
        'masq_field_p': masq_field_p,  
        'show_nav': show_nav,  
        'form_type': 'personnels',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })
  

@login_required
@module_required("Administration")
def ajouter_personnel_categorie(request):
    user_info = get_user_info(request)
    user_modules = user_info
    categorie_list = Personnel_categorie.objects.all()
    show_nav = False  #
    if 'ajouter_personnel_categorie' in request.path:  
        show_nav = True
    if request.method == 'POST':
        get_categorie = request.POST.get('categorie')
        form_pers_categorie = PersonnelCategorieForm(request.POST)
        categor_exist = Personnel_categorie.objects.filter(categorie = get_categorie)
        if form_pers_categorie.is_valid():
            if categor_exist.exists():
                messages.error(request,"Catégorie déjà enregistré")
                return redirect('ajouter_personnel_categorie')
            else:
                form_pers_categorie.save()
                messages.success(request,"Catégorie ajouté avec succès!!")
                return redirect('ajouter_personnel_categorie')  #
    else:
        form_pers_categorie = PersonnelCategorieForm()
    return render(request, 'parametrage/index_parametrage.html',
                  {'form_pers_categorie': form_pers_categorie,
                   'categorie_list' :categorie_list,
                    'show_nav': show_nav,  
                    'form_type': 'categories',
                    "photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']
                   })

@login_required
@module_required("Administration")
def ajouter_diplome(request):
    user_info = get_user_info(request)
    user_modules = user_info
    diplome_list = Diplome.objects.all()
    show_nav = False  
    if 'ajouter_diplome' in request.path: 
        show_nav = True
    if request.method == 'POST':
        diplome = request.POST.get('diplome')
        diplome_get = Diplome.objects.filter(diplome = diplome)
        form_pers_diplome = DiplomeForm(request.POST)
        if form_pers_diplome.is_valid():
            if diplome_get.exists():
                messages.error(request,'Diplome déjà ajouté!')
                return redirect('ajouter_diplome')
            else:
                form_pers_diplome.save()
                messages.success(request,'Diplome ajouté avec succès!')
                return redirect('ajouter_diplome')
    else:
        form_pers_diplome = DiplomeForm()
    return render(request, 'parametrage/index_parametrage.html',
                  {'form_pers_diplome': form_pers_diplome,
                   'diplome_list' :diplome_list,
                    'show_nav': show_nav,  
                    'form_type': 'diplomes',
                    "photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']})

@login_required
@module_required("Administration")
def ajouter_specialite(request):
    user_info = get_user_info(request)
    user_modules = user_info
    specialite_list = Specialite.objects.all()
    show_nav = False  
    if 'ajouter_specialite' in request.path: 
        show_nav = True
    if request.method == 'POST':
        specialite = request.POST.get('specialite')
        spcilite_list = Specialite.objects.filter(specialite = specialite)
        form_pers_specialite = SpecialiteForm(request.POST)
        if form_pers_specialite.is_valid():
            if spcilite_list.exists():
                messages.error(request,'Spécialité déjà enregistrée!')
                return redirect('ajouter_specialite')
            else:
                form_pers_specialite.save()
                messages.success(request,'Spécialité ajoutée avec succès')
                return redirect('ajouter_specialite')
    else:
        form_pers_specialite = SpecialiteForm()
    return render(request,'parametrage/index_parametrage.html', 
                  {'form_pers_specialite':form_pers_specialite,
                   'specialite_list' :specialite_list,
                    'show_nav': show_nav,  
                    'form_type': 'specialites',
                    "photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']})

@login_required
@module_required("Administration")
def ajouter_vacation(request):
    user_info = get_user_info(request)
    user_modules = user_info
    vacation_list = Vacation.objects.all()
    show_nav = False  #
    if 'ajouter_vacation' in request.path:  
        show_nav = True
    if request.method == 'POST':
    
        vacation = request.POST.get('vacation')
        form_pers_vacation = VacationForm(request.POST)
        vacation_filters = Vacation.objects.filter(vacation=vacation)
        
        if form_pers_vacation.is_valid():
            if vacation_filters.exists():
                messages.error(request,'La vacation du personnel que vous avez ajouté existe déjà!')
                return redirect('ajouter_vacation')
            else:
                form_pers_vacation.save()
                messages.success(request,"Vacation créée avec succès!")
                return redirect('ajouter_vacation')
    else:
        form_pers_vacation = VacationForm()
    return render(request, 'parametrage/index_parametrage.html',
                  {'form_pers_vacation': form_pers_vacation,
                   'vacation_list' : vacation_list,
                    'show_nav': show_nav,  
                    'form_type': 'vacations',
                    "photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']})

@login_required
@module_required("Administration")
def ajouter_type_personnels(request):
    user_info = get_user_info(request)
    user_modules = user_info
    typerso_list = PersonnelType.objects.all()
    show_nav = False  
    if 'ajouter_type_personnel' in request.path:  
        show_nav = True
    if request.method == 'POST':
    
        type = request.POST.get('type')
        form_pers_type =PersonnalTypeForm(request.POST)
        type_filters = PersonnelType.objects.filter(type=type)
        
        if form_pers_type.is_valid():
            if type_filters.exists():
                messages.error(request,'Le type du personnel que vous avez ajouté existe déjà!')
                return redirect('ajouter_type_personnel')
            else:
                form_pers_type.save()
                messages.success(request,"Type du personnel créé avec succès!")
                return redirect('ajouter_type_personnel')
    else:
        form_pers_type = PersonnalTypeForm()
    return render(request, 'parametrage/index_parametrage.html',
                  {'form_pers_type': form_pers_type,
                   'typerso_list' : typerso_list,
                    'show_nav': show_nav,  
                    'form_type': 'typersonnels',
                    "photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']})

@login_required
@module_required("Administration")
def create_responsabl_class_form(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form = ClasseActiveResponsableForm()
    if request.method == 'POST':
        form = ClasseActiveResponsableForm(request.POST)
        if form.is_valid():
            id_annee = form.cleaned_data['id_annee'].id_annee
            id_classe = form.cleaned_data['id_classe'].id_classe_active
            id_campus = request.POST.get('id_campus')
            id_cycle = request.POST.get('id_cycle')
            personnel_ids = request.POST.get('personnel_ids', '').split(',')

            if not personnel_ids or personnel_ids == ['']:
                return JsonResponse({'success': False, 'error': 'Aucun personnel sélectionné'}, status=400)

            try:
                for personnel_id in personnel_ids:
                    if personnel_id:
                        obj, created = Classe_active_responsable.objects.update_or_create(
                            id_personnel_id=personnel_id,
                            id_annee_id=id_annee,
                            id_classe_id=id_classe,
                            id_campus_id=id_campus,
                            id_cycle_id=id_cycle
                        )
                        # if created:
                        #     logger.debug(f"Nouveau responsable ajouté : {personnel_id}")
                        # else:
                        #     logger.debug(f"Responsable déjà existant mis à jour : {personnel_id}")

                return JsonResponse({'success': True})

            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=400)
        else:
            return JsonResponse({'success': False, 'error': form.errors.as_json()}, status=400)
    return render(request, 'parametrage/index_parametrage.html', {
        'form_type': 'vacations_user',
        'form_user_vacation': form,
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })



@login_required
@module_required("Administration")
def get_personnel(request):
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')
    id_annee = request.GET.get('id_annee')

    personnels = Personnel.objects.filter(
        isUser=True,
        en_fonction=True,
        is_verified=True
    ).select_related('user')

    data = []
    for p in personnels:
        is_selected = Classe_active_responsable.objects.filter(
            id_personnel=p,
            id_campus=id_campus,
            id_cycle=id_cycle,
            id_classe=id_classe,
            id_annee=id_annee
        ).exists()

        data.append({
            'id': p.id_personnel,
            'nom': p.user.last_name,
            'prenom': p.user.first_name,
            'selected': is_selected
        })

    return JsonResponse(data, safe=False)


@require_POST
@login_required
@module_required("Administration")
def delete_responsable(request):
    try:
        data = json.loads(request.body)
        personnel_id = data.get('personnel_id')
        id_campus = data.get('id_campus')
        id_cycle = data.get('id_cycle')
        id_classe = data.get('id_classe')
        id_annee = data.get('id_annee')

        deleted = Classe_active_responsable.objects.filter(
            id_personnel_id=personnel_id,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe,
            id_annee_id=id_annee
        ).delete()

        return JsonResponse({'status': 'success', 'deleted_count': deleted[0]})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

