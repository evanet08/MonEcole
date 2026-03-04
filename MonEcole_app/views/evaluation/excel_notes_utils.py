from .__initials import (login_required,
                         messages,Evaluation,
                         redirect,
                         Eleve_note_type,
                         Eleve_note,
                         Cours_par_classe,
                         Eleve_inscription,
                         Workbook,
                         Sum,get_column_letter,
                         Font,Protection,HttpResponse,
                         get_user_info,re,openpyxl,os,Eleve,BytesIO,render,io
)
from MonEcole_app.views.decorators.decorators import module_required


@login_required
@module_required("Institeur et son Espace")
def generate_excel_file_notes(request):
    id_annee = request.GET.get('id_annee')
    id_campus = request.GET.get('id_campus')
    id_cycle = request.GET.get('id_cycle')
    id_classe = request.GET.get('id_classe')
    id_trimestre = request.GET.get('id_trimestre')
    id_periode = request.GET.get('id_periode')
    id_cours = request.GET.get('id_cours')
    id_type_note = request.GET.get('id_type_note')
    id_session = request.GET.get('id_session')
    id_evaluation = request.GET.get('id_evaluation')

    if not all([id_annee, id_campus, id_cycle, id_classe, id_trimestre, id_periode, id_cours, id_type_note, id_session, id_evaluation]):
        messages.error(request, 'Désolé, il manque une donnée !')
        return redirect('generer_excel_file')

    # 1 : Vérifier l'existence de l'évaluation
    try:
        evaluation = Evaluation.objects.get(
            id_evaluation=id_evaluation,
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle_actif=id_cycle,
            id_classe_active=id_classe,
            id_trimestre=id_trimestre,
            id_periode=id_periode,
            id_cours_classe=id_cours,
            id_type_note=id_type_note,
            id_session=id_session
        )
    except Evaluation.DoesNotExist:
        messages.error(request, "Désolé, l'évaluation spécifiée n'existe pas.")
        return redirect("generer_excel_file")

    # 2 : Récupérer le type de note
    try:
        type_note = Eleve_note_type.objects.get(id_type_note=id_type_note)
        sigle_note = type_note.sigle
        valid_sigles = [note_type.sigle for note_type in Eleve_note_type.objects.all()]
        if sigle_note not in valid_sigles:
            messages.error(request, f"Type de note non reconnu : {sigle_note}. Les types valides sont : {', '.join(valid_sigles)}.")
            return redirect("generer_excel_file")
    except Eleve_note_type.DoesNotExist:
        messages.error(request, "Désolé, type de note non trouvé.")
        return redirect("generer_excel_file")

    # 3 : Récupérer les évaluations existantes (exclure l'évaluation cible)
    evaluations = Evaluation.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle_actif=id_cycle,
        id_classe_active=id_classe,
        id_trimestre=id_trimestre,
        id_periode=id_periode,
        id_cours_classe=id_cours,
        id_type_note=id_type_note,
        id_session=id_session
    ).exclude(id_evaluation=id_evaluation).order_by('id_evaluation')

    eval_to_column = {eval.id_evaluation: idx + 1 for idx, eval in enumerate(evaluations)}

    max_notes_count = len(evaluations)
    new_column_index = max_notes_count + 1 

    #4 : Récupérer les notes existantes
    notes = Eleve_note.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_actif_id=id_cycle,
        id_classe_active_id=id_classe,
        id_trimestre_id=id_trimestre,
        id_periode_id=id_periode,
        id_cours_id=id_cours,
        id_type_note_id=id_type_note,
        id_session_id=id_session
    ).select_related('id_eleve')

    notes_by_eleve = {}
    for note in notes:
        eleve_key = (note.id_eleve.id_eleve, note.id_eleve.nom, note.id_eleve.prenom)
        if eleve_key not in notes_by_eleve:
            notes_by_eleve[eleve_key] = {}
        notes_by_eleve[eleve_key][note.id_evaluation_id] = note.note

    #5 : Vérifier la pondération
    try:
        cours = Cours_par_classe.objects.get(
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle=id_cycle,
            id_classe=id_classe,
            id_cours_classe=id_cours
        )
        max_ponderation = cours.TP if sigle_note == "T.J" else cours.TPE
    except Cours_par_classe.DoesNotExist:
        messages.error(request, "Cours non trouvé.")
        return redirect("generer_excel_file")

    # Somme des pondérations des évaluations existantes
    total_ponderer_eval = evaluations.aggregate(total_ponderation=Sum('ponderer_eval'))['total_ponderation'] or 0

    # Vérification si la somme des pondérations est inférieure à la limite
    if total_ponderer_eval >= int(max_ponderation):
        messages.error(request, f"La somme des pondérations ({total_ponderer_eval}) dépasse ou atteint la limite ({max_ponderation}) pour {sigle_note}.")
        return redirect("generer_excel_file")

    # Récupérer les élèves inscrits
    inscriptions = Eleve_inscription.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_classe_cycle=id_cycle,
        id_classe=id_classe,
        id_trimestre=id_trimestre,
        status=1
    ).select_related('id_eleve')

    # Création du fichier Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Notes"

    # Génération des en-têtes
    headers = ["Nom", "Prénom"]
    if max_notes_count > 0:
        headers += [f"{sigle_note}{i+1}" for i in range(max_notes_count)]
    headers += [f"{sigle_note}{new_column_index}"]

    for col_num, header in enumerate(headers, 1):
        col_letter = get_column_letter(col_num)
        ws[f"{col_letter}1"] = header
        ws[f"{col_letter}1"].font = Font(bold=True)

    # Ajustement de la largeur des colonnes
    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 30

    # Remplissage des données élèves
    for row_num, inscription in enumerate(inscriptions, start=2):
        eleve = inscription.id_eleve
        ws[f"A{row_num}"] = eleve.nom
        ws[f"A{row_num}"].protection = Protection(locked=True)

        ws[f"B{row_num}"] = eleve.prenom
        ws[f"B{row_num}"].protection = Protection(locked=True)

        # Remplir les colonnes des notes existantes
        eleve_key = (eleve.id_eleve, eleve.nom, eleve.prenom)
        eleve_notes = notes_by_eleve.get(eleve_key, {})
        for eval_id, column_index in eval_to_column.items():
            col_letter = get_column_letter(3 + column_index - 1)  
            cell = ws[f"{col_letter}{row_num}"]
            note = eleve_notes.get(eval_id)
            cell.value = note if note is not None else ""
            cell.protection = Protection(locked=True)

        # Colonne pour la nouvelle note (déverrouillée)
        new_col_letter = get_column_letter(3 + max_notes_count)
        ws[f"{new_col_letter}{row_num}"] = ""
        ws[f"{new_col_letter}{row_num}"].protection = Protection(locked=False)

    # Protection de la feuille
    ws.protection.enable()
    ws.protection.enable_select_locked_cells = False
    ws.protection.enable_select_unlocked_cells = True

    # Ajustement automatique de la largeur des colonnes
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value and len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = max_length + 2
    get_cours_id = Cours_par_classe.objects.get(id_annee = id_annee,id_campus = id_campus,id_cycle = id_cycle,id_classe = id_classe,id_cours_classe = id_cours)
    cours_nom = get_cours_id.id_cours.cours
    # Génération du fichier
    filename = f"FicheNotes{cours_nom}({sigle_note})_-{id_type_note}_{id_annee}_{id_campus}_{id_cycle}_{id_classe}_{id_cours}_{id_trimestre}_{id_periode}_{id_session}_{id_evaluation}-.xlsx"
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    response = HttpResponse(
        content=buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@module_required("Evaluation")
def importation_notes(request):
    note_form = True
    user_info = get_user_info(request)

    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            messages.error(request, "Aucun fichier sélectionné.")
            return redirect("import_file_note")

        filename_info = validate_filename(request, uploaded_file.name)
        if not filename_info:
            return redirect("import_file_note")

        validation_result = validate_identifiers(id_parts=filename_info['id_parts'])
        if not validation_result['success']:
            messages.error(request, validation_result['error'])
            return redirect("import_file_note")
        
        evaluation, cours, type_note, max_ponderation = validation_result['data']

        imported_data = read_excel_file(request, uploaded_file)
        if not imported_data:
            return redirect("import_file_note")

        validated_data = validate_notes(request, imported_data, max_ponderation)
        if not validated_data:
            return redirect("import_file_note")

        save_notes(request, validated_data, filename_info['id_parts'], evaluation)

    return render(request, 'evaluation/index_evaluation.html', {
        'notes_form': note_form,
        'form_type': 'import_note',
        'photo_profil': user_info['photo_profil'],
        'modules': user_info['modules'],
        'last_name': user_info['last_name']
    })


def validate_filename(request, filename):
    """Valide le nom du fichier et extrait les identifiants."""
    base_name = os.path.splitext(filename)[0]
    base_name_cleaned = re.sub(r'\(\d+\)$', '', base_name)

    if not base_name_cleaned.startswith("FicheNotes"):
        messages.error(request, "Le nom du fichier doit commencer par 'FicheNotes'.")
        return None

    match = re.match(r'.*?-(\d+_\d+_\d+_\d+_\d+_\d+_\d+_\d+_\d+_\d+)-$', base_name_cleaned)
    if not match:
        messages.error(request, "Le format du fichier est incorrect. Les identifiants doivent être de la forme X_X_X_X_X_X_X_X_X_X entre le premier et le dernier '-'.")
        return None

    id_part_str = match.group(1)
    id_parts = id_part_str.split("_")

    if len(id_parts) != 10:
        messages.error(request, f"Le fichier doit contenir 10 identifiants, mais {len(id_parts)} ont été trouvés : {id_parts}")
        return None

    try:
        id_parts = tuple(map(int, id_parts))
    except ValueError as e:
        messages.error(request, f"Un ou plusieurs identifiants ne sont pas des entiers : {e}")
        return None

    return {'base_name': base_name_cleaned, 'id_parts': id_parts}

def validate_identifiers(id_parts):
    """Valide les identifiants et récupère les objets associés."""
    try:
        (
            id_type_note, id_annee, id_campus, id_cycle, id_classe, id_cours,
            id_trimestre, id_periode, id_session, id_evaluation
        ) = id_parts
    except ValueError:
        return {'success': False, 'error': "Erreur lors de la décomposition des identifiants."}

    evaluations = Evaluation.objects.filter(
        id_annee=id_annee, id_campus=id_campus, id_cycle_actif=id_cycle,
        id_classe_active=id_classe, id_trimestre=id_trimestre, id_periode=id_periode,
        id_cours_classe=id_cours, id_type_note=id_type_note, id_session=id_session,
        id_evaluation=id_evaluation
    )
    if not evaluations.exists():
        return {'success': False, 'error': "Aucune évaluation trouvée pour ces critères."}
    
    notes_enregistres = Eleve_note.objects.filter(
        id_annee=id_annee, id_campus=id_campus, id_cycle_actif=id_cycle,
        id_classe_active=id_classe, id_trimestre=id_trimestre, id_periode=id_periode,
        id_cours_classe=id_cours, id_type_note=id_type_note, id_session=id_session,
        id_evaluation=id_evaluation
    )
    if  notes_enregistres.exists():
        return {'success': False, 'error': "La note pour cette évaluation a ete déjà soumise.Merci de vérifier"}
    
    try:
        cours = Cours_par_classe.objects.get(
            id_annee=id_annee, id_campus=id_campus, id_cycle=id_cycle,
            id_classe=id_classe, id_cours_classe=id_cours
        )
    except Cours_par_classe.DoesNotExist:
        return {'success': False, 'error': "Cours non trouvé."}

    try:
        type_note = Eleve_note_type.objects.get(id_type_note=id_type_note)
    except Eleve_note_type.DoesNotExist:
        return {'success': False, 'error': "Type de note non trouvé."}

    try:
        evaluation = evaluations.get()
        max_ponderation = evaluation.ponderer_eval
    except Evaluation.DoesNotExist:
        return {'success': False, 'error': "Pondération de l'évaluation non trouvée !"}

    return {
        'success': True,
        'data': (evaluation, cours, type_note, max_ponderation)
    }

def read_excel_file(request, uploaded_file):
    """Lit le fichier Excel et extrait les données."""
    try:
        wb = openpyxl.load_workbook(BytesIO(uploaded_file.read()))
        sheet = wb.active
    except Exception as e:
        messages.error(request, f"Erreur lors de la lecture du fichier Excel : {str(e)}")
        return None

    imported_data = []
    for row in sheet.iter_rows(min_row=2, values_only=True):
        nom = row[0]
        prenom = row[1]
        note_val = row[-1]

        if nom and prenom:
            nom_clean = str(nom).strip().upper()
            prenom_clean = str(prenom).strip().capitalize()
            full_name = f"{nom_clean} {prenom_clean}"
            imported_data.append({
                "nom_complet": full_name,
                "nom": nom_clean,
                "prenom": prenom_clean,
                "note": note_val
            })

    if not imported_data or all(row["note"] is None or str(row["note"]).strip() == "" for row in imported_data):
        messages.error(request, "Importation annulée : La colonne des notes est entièrement vide.")
        return None

    return imported_data

def validate_notes(request, imported_data, max_ponderation):
    """Valide les notes, y compris les décimales et les chaînes représentant des nombres."""
    validated_data = []

    for row in imported_data:
        full_name = row["nom_complet"]
        note_val = row["note"]

        if note_val is None or str(note_val).strip() == "":
            row["note"] = None 
        else:
            try:
                note = float(note_val)
                if note < 0:
                    messages.error(request, f"Importation annulée : Note négative ({note}) pour {full_name}.")
                    return None
                if note > max_ponderation:
                    messages.error(request, f"Importation annulée : Note ({note}) pour {full_name} dépasse la pondération maximale ({max_ponderation}).")
                    return None
                row["note"] = note
            except (TypeError, ValueError):
                messages.error(request, f"Importation annulée : Note invalide pour {full_name} (doit être un nombre positif ou vide, reçu : '{note_val}').")
                return None

        validated_data.append(row)

    return validated_data


        
def save_notes(request, validated_data, id_parts, evaluation):
    """Enregistre les notes dans la base de données."""
    (
        id_type_note, id_annee, id_campus, id_cycle, id_classe, id_cours,
        id_trimestre, id_periode, id_session, id_evaluation
    ) = id_parts

    notes_importees = 0
    eleves_non_trouves = []

    for row in validated_data:
        nom = row["nom"]
        prenom = row["prenom"]
        full_name = row["nom_complet"]
        note = row["note"]

        eleves_possibles = Eleve.objects.filter(nom__iexact=nom, prenom__iexact=prenom)
        eleve_trouve = None
        for candidat in eleves_possibles:
            inscription = Eleve_inscription.objects.filter(
                id_annee_id=id_annee,
                id_campus_id=id_campus,
                id_classe_cycle_id=id_cycle,
                id_classe_id=id_classe,
                id_eleve=candidat,
                status=True 
            ).first()

            if inscription:
                eleve_trouve = candidat
                break

        if not eleve_trouve:
            eleves_non_trouves.append(full_name)
            continue

        Eleve_note.objects.create(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle,
            id_classe_active_id=id_classe,
            id_session_id=id_session,
            id_trimestre_id=id_trimestre,
            id_periode_id=id_periode,
            id_type_note_id=id_type_note,
            id_cours_id=id_cours,
            id_evaluation_id=id_evaluation,
            id_eleve=eleve_trouve,
            note=note
        )
        notes_importees += 1
    if notes_importees > 0:
        messages.success(request, f"{notes_importees} note(s) ont été importées avec succès.")
    if eleves_non_trouves:
        messages.warning(request, f"Élèves introuvables ou mal inscrits : {', '.join(eleves_non_trouves)}")
    if notes_importees == 0 and not eleves_non_trouves:
        messages.warning(request, "Aucune note n'a été traitée. Vérifiez le fichier importé.")
