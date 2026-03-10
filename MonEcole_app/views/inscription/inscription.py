from django.shortcuts import render,redirect,get_object_or_404
from django.http import HttpResponse
from MonEcole_app.forms.form_imports import EleveInscriptionForm,EleveForm
from MonEcole_app.models.models_import import *
from django.contrib import messages
import pandas as pd
from openpyxl import load_workbook
from io import BytesIO
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.shortcuts import render, redirect
from datetime import datetime
from MonEcole_app.views.home.home import get_user_info
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
import re 
from validate_email_address import validate_email
from django.views.decorators.csrf import csrf_protect,csrf_exempt
from django.views.decorators.http import require_GET
from MonEcole_app.forms.evaluation_form import Eleve_NoteForm
import json
import logging
logger = logging.getLogger(__name__)
from django.core.exceptions import ObjectDoesNotExist
from MonEcole_app.views.decorators.decorators import  module_required
from MonEcole_app.views.tools.tenant_utils import (
    get_tenant_campus_ids, validate_campus_access, deny_cross_tenant_access
)



@login_required
@module_required("Inscription")
def select_by_field_to_reaffect_inscription(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_select = Eleve_NoteForm(request.POST or None)
    return render(request, 'inscription/index_inscription.html', {
        'form_select_bulletin':form_select,
        'form_type': 'select_form_bull',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
    })

def is_valid_email_address(email):
    return validate_email(email, verify=True) 

def normalize_student_key(nom, prenom):
    return (
        nom.strip().lower(),
        ' '.join([part.capitalize() for part in prenom.strip().split()])
    )

@login_required
@module_required("Inscription")
def create_inscription_eleve(request):
    user_info = get_user_info(request)
    user_modules = user_info
    inscriptions = Eleve.objects.filter(
        eleve_inscription__id_campus__in=get_tenant_campus_ids(request)
    ).distinct()
    show_nav = 'create_inscription' in request.path  

    if request.method == 'POST':
        form_eleve = EleveForm(request.POST)
        form_inscription = EleveInscriptionForm(request.POST)
        
        if form_eleve.is_valid() and form_inscription.is_valid():
            eleve = form_eleve.save(commit=False)  
            inscription = form_inscription.save(commit=False)

            id_annee = form_inscription.cleaned_data['id_annee']  
            id_campus = form_inscription.cleaned_data['id_campus']
            id_classe_cycle = form_inscription.cleaned_data['id_classe_cycle']
            id_classe = form_inscription.cleaned_data['id_classe']
            email_parent = form_eleve.cleaned_data['email_parent']
            

            id_classe_active = id_classe.id_classe_active if id_classe else None
            ecole = Institution.objects.first()
            id_trimestre = Annee_trimestre.objects.filter(
                id_annee=id_annee,
                id_campus=id_campus,
                id_cycle=id_classe_cycle,
                id_classe=id_classe
            ).first()

            if id_trimestre is None:
                messages.error(request, "Impossible de faire cette inscription car les trimestres ne sont pas configurés !")
                return redirect('create_inscription')

                            
            if not ecole:
                messages.error(request, "Aucune institution trouvée pour générer le matricule.")
                return redirect('create_inscription')

            if not id_classe_active:
                messages.error(request, "Impossible de générer le matricule : classe non spécifiée.")
                return redirect('create_inscription')

            eleve_existant = Eleve.objects.filter(
                nom=eleve.nom.upper(),
                prenom=' '.join([part.capitalize() for part in eleve.prenom.split()])
            ).first()

            if eleve_existant:
                inscription_existante = Eleve_inscription.objects.filter(
                    id_eleve=eleve_existant,
                    id_annee=id_annee,  
                    id_campus=id_campus,
                    id_classe_cycle=id_classe_cycle,
                    id_classe=id_classe
                ).exists()

                if inscription_existante:
                    messages.error(request, "Cet élève est déjà inscrit dans cette classe pour cette année et ce campus !")
                    return redirect('create_inscription')
            try:
                code_annee = id_annee.annee.split('-')[0][-2:] 
            except AttributeError:
                messages.error(request, "Année sélectionnée invalide.")
                return redirect('create_inscription')

            sigle = ecole.sigle.lower()
            compteur = Eleve.objects.count() + 1  
            matricule = f"{sigle}-0{id_classe_active}-{code_annee}-{str(compteur).zfill(5)}"
            email = f"{matricule}@{sigle}.bi"
            password_hashed = make_password("12345")
            eleve.nom = eleve.nom.upper()
            eleve.prenom = ' '.join([part.capitalize() for part in eleve.prenom.split()])
            eleve.matricule = matricule
            eleve.email = email
            eleve.password = password_hashed
            eleve.code_annee = code_annee
            eleve.email_parent = email_parent 
            eleve.save()

            inscription.id_eleve = eleve
            inscription.id_annee = id_annee 
            inscription.id_campus = id_campus
            inscription.id_classe_cycle = id_classe_cycle
            inscription.id_classe = id_classe
            inscription.id_trimestre = id_trimestre
            inscription.save()

            messages.success(request, "L'élève et son inscription ont été ajoutés avec succès !")
            return redirect('create_inscription')
        else:
            messages.error(request, "Erreur dans le formulaire. Veuillez vérifier les informations saisies.")
            return redirect('create_inscription')
            
    else:
        form_eleve = EleveForm()
        form_inscription = EleveInscriptionForm()

    champs_a_masquer = ['telephone']
    return render(request, 'inscription/index_inscription.html', {
        'form_eleve': form_eleve,
        'form_inscription': form_inscription,
        'show_nav': show_nav,
        'inscriptions': inscriptions,
        'form_type': 'inscriptions',
        'champs_a_masquer': champs_a_masquer,
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name']
    })


@login_required
@module_required("Inscription")
def import_eleves(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = 'import_inscription' in request.path

    if request.method == "POST" and request.FILES.get('excel_file'):
        file = request.FILES['excel_file']

        try:
            df = pd.read_excel(file)
            required_columns = ["Nom", "Prénom", "Genre", "Date de Naissance"]

            if not all(col in df.columns for col in required_columns):
                messages.error(request, "Les colonnes attendues ne sont pas présentes dans le fichier.")
                return render(request, "inscription/index_inscription.html", {
                    'show_nav': show_nav,
                    'form_type': 'import_file',
                    "photo_profil": user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']
                })

            if df[required_columns].dropna(how='all').empty:
                messages.error(request, "Le fichier ne contient aucune donnée dans les colonnes importantes.")
                return render(request, "inscription/index_inscription.html", {
                    'show_nav': show_nav,
                    'form_type': 'import_file',
                    "photo_profil": user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name']
                })

        except Exception as e:
            messages.error(request, f"Erreur lors de la lecture du fichier : {str(e)}")
            return render(request, "inscription/index_inscription.html", {
                'show_nav': show_nav,
                'form_type': 'import_file',
                "photo_profil": user_modules['photo_profil'],
                "modules": user_modules['modules'],
                "last_name": user_modules['last_name']
            })
        

        try:
            file_name = file.name
            id_campus = int(file_name.split("Campus_")[1].split("_")[0])
            id_annee = int(file_name.split("Annee_")[1].split("_")[0])
            id_classe_cycle = int(file_name.split("Cycle_")[1].split("_")[0])
            classe_part = file_name.split("Class_")[1].split(".xlsx")[0]
            id_classe = int(re.search(r'\d+', classe_part).group())
            campus = Campus.objects.get(id_campus=id_campus)
            annee = Annee.objects.get(id_annee=id_annee)
            classe_cycle = Classe_cycle_actif.objects.filter(id_campus=id_campus, id_cycle_actif=id_classe_cycle, id_annee=id_annee).first()
            classe = Classe_active.objects.filter(id_campus=id_campus, id_annee=id_annee, id_classe_active=id_classe, cycle_id=id_classe_cycle).first()

            if not (campus and annee and classe_cycle and classe):
                raise ValueError("Certaines données (campus, année, cycle ou classe) sont introuvables.")

        except (ValueError, IndexError, Campus.DoesNotExist, Annee.DoesNotExist, Classe_cycle_actif.DoesNotExist, Classe_active.DoesNotExist) as e:
            messages.error(request, "Erreur : Vérifiez le nom du fichier. Il doit respecter le format attendu (ex. FormInscription_Campus_X_Annee_Y_Cycle_Z_Class_W.xlsx).")
            return render(request, "inscription/index_inscription.html", {
                'show_nav': show_nav,
                'form_type': 'import_file',
                "photo_profil": user_modules['photo_profil'],
                "modules": user_modules['modules'],
                "last_name": user_modules['last_name']
            })
        surch_trimestr = Annee_trimestre.objects.filter(id_annee=id_annee,id_campus=id_campus,id_classe=id_classe,id_cycle=id_classe_cycle)
        if not surch_trimestr.exists():
            messages.error(request, "Désolé !! Vous devez d'abord configurer les données de base !comme les  trimestres par exemple")
            return render(request, "inscription/index_inscription.html", {
                'show_nav': show_nav,
                'form_type': 'import_file',
                "photo_profil": user_modules['photo_profil'],
                "modules": user_modules['modules'],
                "last_name": user_modules['last_name']
            })

        required_columns = ["Nom", "Prénom", "Genre", "Date de Naissance"]
        if not all(col in df.columns for col in required_columns):
            messages.error(request, "Le fichier doit contenir les colonnes : Nom, Prénom, Genre, Date de Naissance.")
            return render(request, "inscription/index_inscription.html", {
                'show_nav': show_nav,
                'form_type': 'import_file',
                "photo_profil": user_modules['photo_profil'],
                "modules": user_modules['modules'],
                "last_name": user_modules['last_name']
            })
        inserted_count = 0
        duplicate_count = 0
        seen_students = set()
        annee_actuelle = datetime.now().year
        code_annee = str(annee_actuelle)[-2:]
        ecole = Institution.objects.first()
        sigle = ecole.sigle.upper()
        trimestre = surch_trimestr.first() if surch_trimestr.exists() else None
        if not trimestre:
            messages.error(request, "Il n'y a pas de trimestre défini. Veuillez d'abord ajouter un trimestre.")
            return render(request, "inscription/index_inscription.html", {
                'show_nav': show_nav,
                'form_type': 'import_file',
                "photo_profil": user_modules['photo_profil'],
                "modules": user_modules['modules'],
                "last_name": user_modules['last_name']
            })

        for _, row in df.iterrows():
            nom = str(row["Nom"]).strip().upper() if pd.notna(row["Nom"]) else ""
            prenom = str(row["Prénom"]).strip().capitalize() if pd.notna(row["Prénom"]) else ""
            genre = str(row["Genre"]).strip().capitalize() if pd.notna(row["Genre"]) else ""
            prenom = ' '.join([part.capitalize() for part in prenom.split()])

            if not nom and not prenom:
                continue

            try:
                if pd.notna(row["Date de Naissance"]):
                    date_naissance = pd.to_datetime(row["Date de Naissance"]).date()
                else:
                    date_naissance = None
            except Exception:
                date_naissance = None

            student_key = normalize_student_key(nom, prenom)
            existing_eleve = Eleve.objects.filter(nom=nom, prenom=prenom).first()
            is_duplicate = False
            if existing_eleve:
                is_duplicate = Eleve_inscription.objects.filter(
                    id_eleve=existing_eleve,
                    id_classe=classe,
                    id_classe_cycle=classe_cycle,
                    id_annee=annee,
                    id_campus = id_campus
                ).exists()

            if student_key in seen_students or is_duplicate:
                duplicate_count += 1
                continue
            seen_students.add(student_key)

            compteur = Eleve.objects.count() + 1
            matricule = f"{sigle.lower()}-0{id_classe}-{code_annee}-{str(compteur).zfill(5)}"
            email = f"{matricule}@{sigle.lower()}.bi"
            password_hashed = make_password("12345")
            eleve = Eleve.objects.create(
                nom=nom,
                prenom=prenom,
                date_naissance=date_naissance,
                matricule=matricule,
                email=email,
                genre=genre,
                password=password_hashed,
                code_annee=code_annee
            )

            Eleve_inscription.objects.create(
                id_eleve=eleve,
                id_classe=classe,
                id_campus=campus,
                id_annee=annee,
                id_classe_cycle=classe_cycle,
                redoublement=False,
                status=True,
                isDelegue=False,
                id_trimestre=trimestre  
            )
            inserted_count += 1

        messages.success(request, f"{inserted_count} élèves insérés, {duplicate_count} doublons ignorés.")
        return render(request, "inscription/index_inscription.html", {
            'show_nav': show_nav,
            'form_type': 'import_file',
            "photo_profil": user_modules['photo_profil'],
            "modules": user_modules['modules'],
            "last_name": user_modules['last_name']
        })

    return render(request, "inscription/index_inscription.html", {
        'show_nav': show_nav,
        'form_type': 'import_file',
        "photo_profil": user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })

@login_required
@module_required("Inscription")
def generate_excel_template(request):
    user_info = get_user_info(request)
    user_modules = user_info
    show_nav = False  
    if 'inscription_excel_file' in request.path:  
        show_nav = True
    if request.method == "POST":
        
        id_campus = request.POST.get("id_campus")
        id_annee = request.POST.get("id_annee")
        id_classe_cycle = request.POST.get("id_classe_cycle")
        id_classe = request.POST.get("id_classe")
        
        if not all([id_campus, id_annee, id_classe_cycle, id_classe]):
            messages.error(request, "Erreur lors de la générations du fichier Excel.")
            return render(request, "inscription/index_inscription.html", {'show_nav_generer': show_nav, 'form_type': 'excel_file'})
        columns = [ "Nom", "Prénom", "Genre", "Date de Naissance"]
        data = [["", "", "", ""]]

        df = pd.DataFrame(data, columns=columns)

        file_name = f"FormInscription_Campus_{id_campus}_Annee_{id_annee}_Cycle_{id_classe_cycle}_Class_{id_classe}.xlsx"

        buffer = BytesIO()

       
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Inscription")
            
            worksheet = writer.sheets["Inscription"]  
            worksheet.set_column("A:A", 25)  
            worksheet.set_column("B:B", 25) 
            worksheet.set_column("C:C", 10)  
            worksheet.set_column("D:D", 20) 


        buffer.seek(0)

        workbook = load_workbook(buffer)
        new_buffer = BytesIO()
        workbook.save(new_buffer)

        response = HttpResponse(new_buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'

        return response

    form_inscription = EleveInscriptionForm()
    return render(request, 'inscription/index_inscription.html', {
        'form_inscription': form_inscription,
        'show_nav_generer': show_nav, 
        'form_type': 'excel_file',
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']  
    })

@login_required
@module_required("Inscription")
def edit_eleve(request, id_eleve):
    user_info = get_user_info(request)
    user_modules = user_info
    eleve = get_object_or_404(Eleve, id_eleve=id_eleve)
    form_eleve = EleveForm(request.POST or None, instance=eleve)
    show_nav = 'edit_eleve' in request.path

    if request.method == 'POST':
        if form_eleve.is_valid():
            eleve = form_eleve.save(commit=False)
            if not form_eleve.cleaned_data.get('telephone'):
                eleve.telephone = eleve.telephone
            eleve.nom = eleve.nom.upper()
            eleve.prenom = ' '.join([part.capitalize() for part in eleve.prenom.split()])
            
            eleve_existants = Eleve.objects.filter(nom=eleve.nom, prenom=eleve.prenom).exclude(id_eleve=eleve.id_eleve)
            if eleve_existants.exists():
                messages.error(request, f"Le nom {eleve.nom} et le prénom {eleve.prenom} existent déjà!")
                return redirect('create_inscription')
            eleve.save()
            messages.success(request, "Les informations de l'élève ont été mises à jour avec succès!")
            return redirect('create_inscription')
        else:
            messages.error(request, "Erreur lors de la mise à jour de l'élève.")

    champs_a_masquer = ['date_naissance','telephone']

    return render(request, 'inscription/index_inscription.html', {
        'form_eleve': form_eleve,
        'form_type': 'edition_eleve',
        'eleve': eleve,
        'show_nav': show_nav,
        'champs_a_masquer': champs_a_masquer,
        "photo_profil":user_modules['photo_profil'],
        "modules": user_modules['modules'],
        "last_name": user_modules['last_name']
    })


@login_required
def get_pupils_registred_classe(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe_active')

    if not all([id_annee, id_campus, id_cycle, id_classe]):
        return JsonResponse({'error': 'Paramètres manquants'}, status=400)
    

    try:
        # Validation tenant pour le campus
        if id_campus and not validate_campus_access(request, id_campus):
            return JsonResponse({'error': 'Accès interdit à ce campus', 'success': False}, status=403)

        inscriptions = Eleve_inscription.objects.filter(
            Q(id_annee=id_annee) &
            Q(id_campus=id_campus) &
            Q(id_classe_cycle=id_cycle) &
            Q(id_classe=id_classe), 
            Q(status=1)
        ).select_related('id_eleve').order_by('id_eleve')

        seen_eleve_ids = set()
        pupils_data = []
        for inscription in inscriptions:
            eleve = inscription.id_eleve
            if eleve.id_eleve not in seen_eleve_ids:
                seen_eleve_ids.add(eleve.id_eleve)
                pupils_data.append({
                    'id_eleve': eleve.id_eleve,
                    'status': inscription.status, 
                    'redoublement': inscription.redoublement,
                    'nom_complet': f"{eleve.nom} {eleve.prenom}"
                })

        return JsonResponse({
            'success': True,
            'data': pupils_data,
            'count': len(pupils_data)
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'success': False
        }, status=500)



@csrf_protect
def reaffectation_pupil_inscription(request):
    if request.method == "POST":
        try:
            id_eleve = request.POST.get("id_eleve")
            id_annee = request.POST.get("id_annee")
            id_campus = request.POST.get("id_campus")
            id_cycle = request.POST.get("id_cycle")
            id_classe = request.POST.get("id_classe")

            if not all([id_eleve, id_annee, id_campus, id_cycle, id_classe]):
                messages.error(request, "Tous les champs requis doivent être remplis.")
                return redirect("changer_inscription")

            trimestre = Annee_trimestre.objects.filter(
                id_annee=id_annee,
                id_campus=id_campus,
                id_cycle=id_cycle,
                id_classe=id_classe
            ).first()

            if not trimestre:
                messages.error(request, "Aucun trimestre actif trouvé pour cette année.")
                return redirect("changer_inscription")

            try:
                inscription = Eleve_inscription.objects.get(id_eleve_id=id_eleve)

                inscription.id_annee_id = id_annee
                inscription.id_campus_id = id_campus
                inscription.id_classe_cycle_id = id_cycle
                inscription.id_classe_id = id_classe
                inscription.id_trimestre = trimestre
                inscription.date_inscription = timezone.now()
                inscription.save()

                messages.success(request, "Inscription mise à jour avec succès.")

            except Eleve_inscription.DoesNotExist:
                messages.warning(request, "Aucune inscription existante trouvée pour cet élève.")

        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour : {str(e)}")

        return redirect("changer_inscription")
    else:
        return HttpResponse(status=405)

@require_GET
def get_all_years(request):
    try:
        years = Annee.objects.filter(is_active = True).values("id_annee", "annee")
        years_list = list(years)
        return JsonResponse(years_list, safe=False)
    except Exception as e:
        return JsonResponse({"error": f"Erreur lors de la récupération des années : {str(e)}"}, status=500)
    
 