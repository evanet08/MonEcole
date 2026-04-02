
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Line
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import os
from MonEcole_app.models import Eleve,Annee_periode
from django.conf import settings
from MonEcole_app.models import Institution
from reportlab.pdfgen import canvas
from .api import get_cours_classe_rdc
from django.contrib import messages
from reportlab.lib.styles import getSampleStyleSheet
from collections import defaultdict
import logging
from MonEcole_app.models import (Eleve_note,
                                 EtablissementAnneeClasse,Annee,
                                Campus,Annee_trimestre,Deliberation_annuelle_resultat,
                                Deliberation_periodique_resultat,
                                Deliberation_trimistrielle_resultat,
                                Deliberation_examen_resultat)

logger = logging.getLogger(__name__)




styles = getSampleStyleSheet()
style_center = styles['Normal']
style_center.alignment = 1 
style_normal = styles['Normal']
style_normal.alignment = 0  


def get_trimestres(id_annee, id_campus, id_cycle, id_classe):
    
    try:
        campus = Campus.objects.get(id_campus=id_campus)
        localisation = campus.localisation.upper() 
    except Campus.DoesNotExist:
        return None

    try:
        eac = EtablissementAnneeClasse.objects.select_related('etablissement_annee').get(id=id_classe)
        etab_annee_id = eac.etablissement_annee_id
    except EtablissementAnneeClasse.DoesNotExist:
        return None

    trimestres_qs = Annee_trimestre.objects.filter(
        etablissement_annee_id=etab_annee_id,
        has_parent=False
    ).select_related('repartition').order_by('id_trimestre')[:3]


    if len(trimestres_qs) != 3:
        return None

    result = []
    for trimestre in trimestres_qs:
        nom_original = trimestre.repartition.nom  

     
        if localisation == 'RDC':
            mapping = {
                "Trimestre 1": "PREMIER TRIMESTRE",
                "Trimestre 2": "SECOND TRIMESTRE",
                "Trimestre 3": "TROISIEME TRIMESTRE",
                
            }
            nom_affiche = mapping.get(nom_original, nom_original.upper())  
        else:  
            nom_affiche = nom_original

        result.append((trimestre.id_trimestre, nom_original, nom_affiche))

    return result




def get_styles():
    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle(name='NormalSmall', fontSize=4.5, leading=6, alignment=0)  
    style_center = ParagraphStyle(name='CenterSmall', fontSize=4.5, leading=6, alignment=1)  
    style_title = ParagraphStyle(name='TitleSmall', fontSize=8, leading=9, alignment=1)
    style_right = ParagraphStyle(name='RightSmall', fontSize=7, leading=8, alignment=2, fontName='Helvetica-Oblique') 
    return styles, style_normal, style_center, style_title, style_right

def check_image_paths(logo_path, emblem_path):
    if logo_path and not os.path.exists(logo_path):
        raise ValueError(f"Fichier logo introuvable : {logo_path}")
    if emblem_path and not os.path.exists(emblem_path):
        raise ValueError(f"Fichier emblème introuvable : {emblem_path}")

def create_header(elements, logo_path, emblem_path, style_title, style_center):
    logo = Image(logo_path, width=12*mm, height=12*mm) if logo_path and os.path.exists(logo_path) else Paragraph("", style_center)
    emblem = Image(emblem_path, width=12*mm, height=12*mm) if emblem_path and os.path.exists(emblem_path) else Paragraph("", style_center)
    photo_square = Paragraph("Photo", style_center) 
    header_data = [
        [logo, Paragraph("<font color='black'><b>REPUBLIQUE DEMOCRATIQUE DU CONGO<br/>MINISTERE DE L'EDUCATION NATIONALE ET NOUVELLE CITOYENNETE</b></font>", style_title), emblem, photo_square]
    ]
    header_table = Table(header_data, colWidths=[20*mm, 140*mm, 20*mm, 10*mm], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, 0), 0), 
        ('RIGHTPADDING', (-1, -1), (-1, -1), 0),  
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('BOX', (3, 0), (3, 0), 0.5, colors.black),
        ('ALIGN', (3, 0), (3, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*mm))


def create_line2_left(elements, style_normal, id_campus=None):
    
    # Récupérer la matricule de l'établissement via campus → countryStructure
    matricule = ""
    if id_campus:
        try:
            campus = Campus.objects.get(id_campus=id_campus)
            if campus.id_etablissement:
                from django.db import connections
                with connections['countryStructure'].cursor() as cursor:
                    cursor.execute(
                        "SELECT matricule FROM etablissements WHERE id_etablissement = %s",
                        [campus.id_etablissement]
                    )
                    row = cursor.fetchone()
                    if row and row[0]:
                        matricule = str(row[0]).strip()
        except Exception:
            pass

    # Créer les cases dynamiquement selon la taille de la matricule
    nb_cases = len(matricule) if matricule else 10
    matricule_cells = [list(matricule)] if matricule else [[''] * nb_cases]
    
    code_squares_table = Table(matricule_cells, colWidths=[3*mm]*nb_cases, rowHeights=4*mm)
    code_squares_table.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('LEADING', (0,0), (-1,-1), 11),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    left_data = [
        [Paragraph(f"<font color='black'><b>PROVINCE :</b></font>", style_normal), Paragraph("SUD-KIVU", style_normal)],
        [Paragraph(f"<font color='black'><b>VILLE :</b></font>", style_normal), Paragraph("BUKAVU", style_normal)],
        [Paragraph(f"<font color='black'><b>COMMUNE :</b></font>", style_normal), Paragraph("D'IBANDA", style_normal)],
        [Paragraph(f"<font color='black'><b>EP :</b></font>", style_normal), Paragraph("1 College Alfajiri Bukavu", style_normal)],
        [Paragraph(f"<font color='black'><b>Matricule :</b></font>", style_normal), code_squares_table]
    ]
    left_table_vertical = Table(left_data, colWidths=[30*mm, 80*mm], rowHeights=[4*mm]*5)
    left_table_vertical.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ]))
    return left_table_vertical  

def create_nid_section(elements, style_normal):
    nid_squares = [[None] * 27]
    nid_squares_table = Table(nid_squares, colWidths=[3*mm]*27, rowHeights=4*mm)
    nid_squares_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
    nid_data = [[Paragraph("<font color='black'><b>N.ID :</b></font>", style_normal), nid_squares_table]]
    nid_table = Table(nid_data, colWidths=[15*mm, 81*mm], hAlign='CENTER')
    nid_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(nid_table)
    elements.append(Spacer(1, 1*mm))


def create_line2_right(elements, eleve, style_normal,id_classe):
    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
        classe_name = eac.classe.classe.strip()
        
    except:
        return HttpResponse('<script>history.back();</script>', status=404)
    
    nperm_squares = [[None] * 13]
    nperm_squares_table = Table(nperm_squares, colWidths=[3*mm]*13, rowHeights=4*mm)
    nperm_squares_table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black)]))
    right_data = [
        [Paragraph(f"<font color='black'><b>ELEVE  : {eleve.nom} {eleve.prenom}</b></font>", style_normal), Paragraph(f"<font color='black'><b>SEXE : {eleve.genre}</b></font>", style_normal)],
        [Paragraph(f"<font color='black'><b>Ne(e) A : {getattr(eleve, 'Lieu_naissance', '..........')}</b></font>", style_normal), Paragraph(f"<font color='black'><b>DATE NAISSANCE: {eleve.date_naissance}</b></font>", style_normal)],
        [Paragraph(f"<font color='black'><b>CLASSE : {classe_name}</b></font>", style_normal), None],
        [Paragraph(f"<font color='black'><b>N.PERM :</b></font>", style_normal), nperm_squares_table]
    ]
    right_table = Table(right_data, colWidths=[50*mm, 50*mm])
    right_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ]))
    return right_table  

def create_line2_section(elements, left_table, right_table):
    line2_data = [[left_table, right_table]]
    line2_table = Table(line2_data, colWidths=[100*mm, 100*mm])
    line2_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(line2_table)
    elements.append(Spacer(1, 0.5*mm))

def create_bulletin_title(elements, style_title,id_annee,id_classe):
    try:
        annee_obj = Annee.objects.filter(id_annee=id_annee).first()
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
        classe_name = eac.classe.classe.strip()
        
    except:
        # messages.error(request, "Classe ou année introuvable.")
        return HttpResponse('<script>history.back();</script>', status=404)
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(f"<font color='black'><b>BULLETIN DE L'ELEVE DE DEGRE ({classe_name}) | Année Scolaire: {annee_obj.annee}</b></font>", style_title))
    elements.append(Spacer(1, 2*mm))

def get_periodes_par_trimestre(trimestres_data, id_annee, id_campus, id_cycle, id_classe):
    periodes_labels = []

    for trimestre_tuple in trimestres_data:
        id_trimestre_annee = trimestre_tuple[0] 

        periodes_qs = Annee_periode.objects.filter(
            id_trimestre_annee_id=id_trimestre_annee,
            has_parent=True
        ).select_related('repartition').order_by('id_periode')[:2]  


        labels_trimestre = []
        for periode in periodes_qs:
           
            nom_reel = periode.repartition.nom if hasattr(periode, 'repartition') and periode.repartition else f"Période {len(labels_trimestre) + 1}"
            labels_trimestre.append(nom_reel)

        while len(labels_trimestre) < 2:
            labels_trimestre.append("-")

        periodes_labels.append(labels_trimestre)

    while len(periodes_labels) < 3:
        periodes_labels.append(["-", "-"])

    return periodes_labels


def calculer_pts_obt_trimestriels_et_annuel(table_data, style_center):

    protected_rows = {0, 1}

    def safe_float(value):
        if value is None:
            return 0.0
        try:
            text = str(value.text if hasattr(value, 'text') else value).strip()
            if text in ("", "-", " ", None):
                return 0.0
            return float(text)
        except (ValueError, AttributeError, TypeError):
            return 0.0

    def format_note(val):
       
        if val <= 0:
            return "-"
        
        # On arrondit à 2 décimales pour nettoyer les erreurs flottantes
        rounded = round(val, 2)
        
        if rounded.is_integer():
            return str(int(rounded))
        return f"{rounded:.2f}"

    for row_idx, row in enumerate(table_data):
        if row_idx in protected_rows:
            continue

        if len(row) < 24:
            continue

        texte = str(row[0]) if row[0] else ""
        texte_upper = texte.upper()

        # Ignorer les lignes de titres, sous-totaux et sections spéciales
        if "<b>" in texte and "SOUS TOTAL" not in texte_upper:
            continue
        if any(mot in texte_upper for mot in [
            "APPLICATION", "MAXIMA GENEREAUX", "POURCENTAGE",
            "PLACE", "CONDUITE", "SIGNATURE"
        ]):
            continue

        # Calcul des points par trimestre
        pts_t1 = safe_float(row[2]) + safe_float(row[3]) + safe_float(row[5])
        pts_t2 = safe_float(row[9]) + safe_float(row[10]) + safe_float(row[12])
        pts_t3 = safe_float(row[16]) + safe_float(row[17]) + safe_float(row[19])

        # Somme annuelle (selon ton code actuel — pas de /2)
        pts_annuel = pts_t1 + pts_t2 + pts_t3

        # Assurer que la ligne a assez de colonnes
        while len(row) < 24:
            row.append(None)

        # Mise à jour avec formatage propre
        row[7]  = Paragraph(format_note(pts_t1),  style_center)
        row[14] = Paragraph(format_note(pts_t2),  style_center)
        row[21] = Paragraph(format_note(pts_t3),  style_center)
        row[23] = Paragraph(format_note(pts_annuel), style_center)

def calculer_sous_totaux_et_maxima(table_data, style_center):
   
    def safe_float(value):
        if value is None:
            return 0.0
        try:
            text = str(value.text if hasattr(value, 'text') else value).strip()
            if text in ("", "-", " ", None):
                return 0.0
            return float(text)
        except (ValueError, AttributeError, TypeError):
            return 0.0

    def format_note(val, force_decimal=False):
        """Formatage propre et lisible"""
        if val <= 0:
            return "-"
        
        rounded = round(val, 2)
        
        if rounded.is_integer():
            return str(int(rounded))
        if force_decimal or rounded * 10 != int(rounded * 10):
            return f"{rounded:.2f}"
        return f"{rounded:.1f}"

    sous_total_indices = []
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            text = row[0].text or ""
            if "<b>Sous Total</b>" in text:
                sous_total_indices.append(idx)

    for st_idx in sous_total_indices:
        domaine_idx = st_idx - 1
        while domaine_idx >= 0:
            if len(table_data[domaine_idx]) == 0 or table_data[domaine_idx][0] is None:
                domaine_idx -= 1
                continue
            texte = str(table_data[domaine_idx][0])
            if "<b>" in texte and "Sous Total" not in texte:
                break
            domaine_idx -= 1

        if domaine_idx < 0:
            continue

        sommes = [0.0] * 24
        for cours_idx in range(domaine_idx + 1, st_idx):
            row = table_data[cours_idx]
            for col in range(1, 24):
                if col >= len(row) or row[col] is None:
                    continue
                sommes[col] += safe_float(row[col])

        st_row = table_data[st_idx]
        while len(st_row) < 24:
            st_row.append(None)

        for col in range(1, 24):
            if col >= len(st_row):
                continue
            val = sommes[col]
            st_row[col] = Paragraph(format_note(val), style_center)

        max_trim_somme = sommes[6] + sommes[13] + sommes[20]
        if len(st_row) > 22:
            st_row[22] = Paragraph(format_note(max_trim_somme), style_center)

    max_gen_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            text = row[0].text or ""
            if "MAXIMA GENEREAUX" in text:
                max_gen_idx = idx
                break

    if max_gen_idx is None:
        return

    max_sommes = [0.0] * 24
    colonnes_a_diviser_par_2 = {1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23}

    for row_idx in range(2, max_gen_idx):
        row = table_data[row_idx]
        for col in range(1, 24):
            if col >= len(row) or row[col] is None:
                continue
            max_sommes[col] += safe_float(row[col])

    mg_row = table_data[max_gen_idx]
    while len(mg_row) < 24:
        mg_row.append(None)

    for col in range(1, 24):
        if col >= len(mg_row):
            continue
        
        val = max_sommes[col]
        if col in colonnes_a_diviser_par_2:
            val = val / 2

        display_text = format_note(val, force_decimal=True) if val > 0 else "0"
        mg_row[col] = Paragraph(display_text, style_center)
   
def calculer_somme_pts_obt_maxima(table_data, style_center):
    max_gen_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph) and "MAXIMA GENEREAUX" in row[0].text:
            max_gen_idx = idx
            break

    if max_gen_idx is None:
        return

    somme_col_7  = 0.0
    somme_col_14 = 0.0
    somme_col_21 = 0.0
    somme_col_23 = 0.0

    lignes_a_ignorer = {"APPLICATION", "POURCENTAGE", "PLACE", "CONDUITE", "SIGNATURE"}

    for row_idx in range(2, max_gen_idx):
        row = table_data[row_idx]
        if len(row) == 0 or row[0] is None:
            continue

        texte = str(row[0]).strip()
        if "<b>" in texte and "Sous Total" not in texte:
            continue
        if any(mot in texte.upper() for mot in lignes_a_ignorer):
            continue

        def get_val(col):
            if col >= len(row) or row[col] is None:
                return 0.0
            try:
                text = str(row[col].text).strip()
                if text in ("", "-", " "):
                    return 0.0
                return float(text)
            except (ValueError, AttributeError, TypeError):
                return 0.0

        somme_col_7  += get_val(7)
        somme_col_14 += get_val(14)
        somme_col_21 += get_val(21)
        somme_col_23 += get_val(23)

    mg_row = table_data[max_gen_idx]
    while len(mg_row) < 24:
        mg_row.append(None)

    def format_note(valeur):
        if valeur <= 0:
            return "-"
        
        val_ar = round(valeur, 2)
        
        if val_ar.is_integer():
            return str(int(val_ar))
    
        return f"{val_ar:.2f}"

    mg_row[7]  = Paragraph(format_note(somme_col_7),  style_center)
    mg_row[14] = Paragraph(format_note(somme_col_14), style_center)
    mg_row[21] = Paragraph(format_note(somme_col_21), style_center)
    mg_row[23] = Paragraph(format_note(somme_col_23), style_center)

def get_student_notes_rdc(id_eleve, id_annee, id_campus, id_cycle, id_classe):
    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
    except EtablissementAnneeClasse.DoesNotExist:
        return defaultdict(dict)

    nom_classe = eac.classe.classe.strip()

    if nom_classe in ['1ère Année', '1er Langue', '1er SC', '1er Eco', '1ère Primaire', '2ème Primaire', '3ème Primaire', '4ème Primaire', '5ème Primaire', '6ème Primaire']:
        periode_to_col = {
            "P1": 2, "P2": 3,
            "P3": 9, "P4": 10,
            "P5": 16, "P6": 17
        }
    elif nom_classe in ['7ème A E.B', '8ème A E.B', '7ème', '8ème']:
        periode_to_col = {
            "P1": 2, "P2": 3,
            "P3": 9, "P4": 10
        }
    else:
        
        return defaultdict(dict)

    notes_qs = Eleve_note.objects.filter(
        id_eleve_id=id_eleve,
        id_annee_id=id_annee,
        idCampus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe,
        id_type_note__sigle="T.J",
    )

    # Prefetch RepartitionInstance names (Hub) to avoid cross-DB JOIN
    from MonEcole_app.models.country_structure import RepartitionInstance
    rep_ids = set(notes_qs.values_list('id_repartition_instance', flat=True))
    rep_ids.discard(None)
    rep_map = {}
    if rep_ids:
        rep_map = dict(RepartitionInstance.objects.filter(id_instance__in=rep_ids).values_list('id_instance', 'code'))

    regroupement = defaultdict(lambda: defaultdict(list)) 

    for note in notes_qs:
        cours_id  = note.id_cours_id
        try:
            periode_nom = rep_map.get(note.id_repartition_instance_id, None)
            if not periode_nom:
                continue
        except (AttributeError, Exception):
            continue

        if periode_nom not in periode_to_col:
            continue 

        valeur = note.note
        if valeur is not None:
            regroupement[cours_id][periode_nom].append(valeur)

    notes_par_cours = defaultdict(dict)

    for cours_id, periodes in regroupement.items():
        for periode_nom, liste_notes in periodes.items():
            if not liste_notes:
                continue

      
            moyenne = sum(liste_notes) / len(liste_notes)

      
            moyenne_arrondie = round(moyenne, 1)

            if moyenne_arrondie.is_integer():
                valeur_affichee = str(int(moyenne_arrondie))
            else:
                valeur_affichee = f"{moyenne_arrondie:.1f}"

            col = periode_to_col[periode_nom]
            notes_par_cours[cours_id][periode_nom] = {
                'valeur': valeur_affichee,
                'colonne': col
            }

    return notes_par_cours


def get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe):
    """
    Retourne les notes d'examen par cours, indexées par config_id (repartition_configs_etab_annee.id).
    Le template accède aux notes via trimestres_data[i][0] qui est le config_id.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
    except EtablissementAnneeClasse.DoesNotExist:
        return defaultdict(dict)

    notes_qs = Eleve_note.objects.filter(
        id_eleve_id=id_eleve,
        id_annee_id=id_annee,
        idCampus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe,
        id_type_note__sigle="EX"
    )

    # Build mapping: repartition_instance_id -> config_id
    # repartition_configs_etab_annee maps repartition_id to its config ID
    from MonEcole_app.models.annee import Annee_trimestre
    etab_annee_id = eac.etablissement_annee_id
    
    # Get all configs for this etab_annee: {repartition_id: config_id}
    rep_to_config = dict(
        Annee_trimestre.objects.filter(
            etablissement_annee_id=etab_annee_id
        ).values_list('repartition_id', 'id_trimestre')
    )

    logger.warning(f"[get_student_exam_notes] rep_to_config={rep_to_config}, notes_count={notes_qs.count()}")

    notes_par_cours = defaultdict(dict)

    for note in notes_qs:
        cours_id = note.id_cours_id
        rep_instance_id = note.id_repartition_instance_id
        
        # Map the repartition instance to the config ID
        config_id = rep_to_config.get(rep_instance_id)
        
        if config_id is not None:
            notes_par_cours[cours_id][config_id] = (
                note.note if note.note is not None else "-"
            )

    logger.warning(f"[get_student_exam_notes] Found exam notes for {len(notes_par_cours)} cours")
    return notes_par_cours




def calculer_pts_obt_et_somme_finale(table_data, style_center):
    
    protected_rows = {0, 1}

    def safe_float(value):
        """Convertit proprement en float, retourne 0.0 en cas d'erreur"""
        if value is None:
            return 0.0
        try:
            text = str(value.text).strip() if hasattr(value, 'text') else str(value).strip()
            if text in ("", "-", " "):
                return 0.0
            return float(text)
        except (ValueError, AttributeError, TypeError):
            return 0.0

    def format_note(val, decimals=2):
        """Formatage propre : entier si possible, sinon X décimales"""
        if val <= 0:
            return "-"
        rounded = round(val, decimals)
        if rounded.is_integer():
            return str(int(rounded))
        return f"{rounded:.{decimals}f}"

    # 1. Traitement ligne par ligne (sauf protégées)
    for row_idx, row in enumerate(table_data):
        if row_idx in protected_rows:
            continue

        if len(row) < 24:
            continue

        texte = str(row[0]) if row[0] else ""
        texte_upper = texte.upper()

        # Ignorer les lignes de titre / sous-total / spéciales
        if "<b>" in texte and "SOUS TOTAL" not in texte_upper:
            continue
        if any(mot in texte_upper for mot in [
            "APPLICATION", "MAXIMA GENEREAUX", "POURCENTAGE",
            "PLACE", "CONDUITE", "SIGNATURE"
        ]):
            continue

        # Calcul des points par trimestre
        pts_t1 = safe_float(row[2]) + safe_float(row[3]) + safe_float(row[5])
        pts_t2 = safe_float(row[9]) + safe_float(row[10]) + safe_float(row[12])
        pts_t3 = safe_float(row[16]) + safe_float(row[17]) + safe_float(row[19])

        pts_annuel = (pts_t1 + pts_t2 + pts_t3) / 2

        # Assurer que la ligne a assez de colonnes
        while len(row) < 24:
            row.append(None)

        # Mise à jour des cellules (division par 2 pour trimestres)
        row[7]  = Paragraph(format_note(pts_t1 / 2), style_center)
        row[14] = Paragraph(format_note(pts_t2 / 2), style_center)
        row[21] = Paragraph(format_note(pts_t3 / 2), style_center)
        row[23] = Paragraph(format_note(pts_annuel), style_center)

    # 2. Calcul de la somme totale en colonne 23 (sauf lignes protégées et spéciales)
    somme_col_23 = 0.0
    for row_idx, row in enumerate(table_data):
        if row_idx in protected_rows:
            continue
        if len(row) <= 23 or row[23] is None:
            continue

        texte = str(row[0]) if row[0] else ""
        texte_upper = texte.upper()

        # Ignorer les mêmes lignes que plus haut
        if any(mot in texte_upper for mot in [
            "APPLICATION", "MAXIMA GENEREAUX", "POURCENTAGE",
            "PLACE", "CONDUITE", "SIGNATURE", "SOUS TOTAL"
        ]):
            continue

        somme_col_23 += safe_float(row[23])

    # 3. Mise à jour de la ligne 41 (index 40), colonne 23
    ligne_somme_index = 40
    if ligne_somme_index < len(table_data):
        while len(table_data[ligne_somme_index]) <= 23:
            table_data[ligne_somme_index].append(None)

        # Formatage final de la somme
        display_val = format_note(somme_col_23, decimals=2)
        table_data[ligne_somme_index][23] = Paragraph(display_val, style_center)


def calculer_pourcentages(table_data, style_center):
    ligne_pourcentage_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph) and "POURCENTAGE" in row[0].text:
            ligne_pourcentage_idx = idx
            break

    if ligne_pourcentage_idx is None:
        return

    max_gen_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph) and "MAXIMA GENEREAUX" in row[0].text:
            max_gen_idx = idx
            break

    if max_gen_idx is None:
       
        return

    def get_val(row_idx, col):
        if row_idx < len(table_data) and col < len(table_data[row_idx]):
            try:
                text = table_data[row_idx][col].text.strip()
                return float(text) if text not in ["", "-", "0"] else 0.0
            except:
                return 0.0
        return 0.0
    max_per_t1 = get_val(max_gen_idx, 1)
    max_per_t2 = get_val(max_gen_idx, 8)
    max_per_t3 = get_val(max_gen_idx, 15)
    max_exam_t1 = get_val(max_gen_idx, 4)
    max_exam_t2 = get_val(max_gen_idx, 11)
    max_exam_t3 = get_val(max_gen_idx, 18)
    max_trim_t1 = get_val(max_gen_idx, 6)
    max_trim_t2 = get_val(max_gen_idx, 13)
    max_trim_t3 = get_val(max_gen_idx, 20)
    max_annuel = get_val(max_gen_idx, 22)
    pts_t1 = get_val(max_gen_idx, 7)
    pts_t2 = get_val(max_gen_idx, 14)
    pts_t3 = get_val(max_gen_idx, 21)
    pts_annuel = get_val(max_gen_idx, 23)
    pourcentage_row = table_data[ligne_pourcentage_idx]
    while len(pourcentage_row) < 24:
        pourcentage_row.append(None)
    pourcentage_row[2] = Paragraph(f"{(get_val(max_gen_idx, 2) / max_per_t1 * 100):.2f}%", style_center) if max_per_t1 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[3] = Paragraph(f"{(get_val(max_gen_idx, 3) / max_per_t1 * 100):.2f}%", style_center) if max_per_t1 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[9] = Paragraph(f"{(get_val(max_gen_idx, 9) / max_per_t2 * 100):.2f}%", style_center) if max_per_t2 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[10] = Paragraph(f"{(get_val(max_gen_idx, 10) / max_per_t2 * 100):.2f}%", style_center) if max_per_t2 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[16] = Paragraph(f"{(get_val(max_gen_idx, 16) / max_per_t3 * 100):.2f}%", style_center) if max_per_t3 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[17] = Paragraph(f"{(get_val(max_gen_idx, 17) / max_per_t3 * 100):.2f}%", style_center) if max_per_t3 > 0 else Paragraph("0.00%", style_center)

    pourcentage_row[5] = Paragraph(f"{(get_val(max_gen_idx, 5) / max_exam_t1 * 100):.2f}%", style_center) if max_exam_t1 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[12] = Paragraph(f"{(get_val(max_gen_idx, 12) / max_exam_t2 * 100):.2f}%", style_center) if max_exam_t2 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[19] = Paragraph(f"{(get_val(max_gen_idx, 19) / max_exam_t3 * 100):.2f}%", style_center) if max_exam_t3 > 0 else Paragraph("0.00%", style_center)

    pourcentage_row[7] = Paragraph(f"{(pts_t1 / max_trim_t1 * 100):.2f}%", style_center) if max_trim_t1 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[14] = Paragraph(f"{(pts_t2 / max_trim_t2 * 100):.2f}%", style_center) if max_trim_t2 > 0 else Paragraph("0.00%", style_center)
    pourcentage_row[21] = Paragraph(f"{(pts_t3 / max_trim_t3 * 100):.2f}%", style_center) if max_trim_t3 > 0 else Paragraph("0.00%", style_center)

    pourcentage_row[23] = Paragraph(f"{(pts_annuel / max_annuel * 100):.2f}%", style_center) if max_annuel > 0 else Paragraph("0.00%", style_center)

 
def get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe):
    """
    Retourne les notes TJ par cours, indexées par code de période (P1, P2, P3, P4).
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
    except EtablissementAnneeClasse.DoesNotExist:
        return defaultdict(dict)

    # Codes de période valides selon le type de classe
    nom_classe = eac.classe.classe.strip()
    if nom_classe in ['1ère Année', '1er Langue', '1er SC', '1er Eco', '1ère Primaire', '2ème Primaire', '3ème Primaire', '4ème Primaire', '5ème Primaire', '6ème Primaire']:
        valid_codes = {"P1", "P2", "P3", "P4", "P5", "P6"}
    elif nom_classe in ['7ème A E.B', '8ème A E.B', '7ème', '8ème', '4ème construction', '2ème Niveau Eléctricité Industrielle', '2sc MTP', '2ème LANGUE', '2ème Eco', '2ème BCT', '3ème MPT', '3ème BCT', '3ème ECO']:
        valid_codes = {"P1", "P2", "P3", "P4"}
    else:
        return defaultdict(dict)

    notes_qs = Eleve_note.objects.filter(
        id_eleve_id=id_eleve,
        id_annee_id=id_annee,
        idCampus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe,
        id_type_note__sigle="T.J"
    )

    # Prefetch RepartitionInstance codes (Hub) to avoid cross-DB JOIN
    from MonEcole_app.models.country_structure import RepartitionInstance
    rep_ids = set(notes_qs.values_list('id_repartition_instance', flat=True))
    rep_ids.discard(None)
    rep_map = {}
    if rep_ids:
        rep_map = dict(RepartitionInstance.objects.filter(id_instance__in=rep_ids).values_list('id_instance', 'code'))

    logger.warning(f"[get_student_period_notes] classe={nom_classe}, notes_count={notes_qs.count()}, rep_ids={rep_ids}, rep_map={rep_map}")

    notes_par_cours = defaultdict(dict)

    for note in notes_qs:
        cours_id = note.id_cours_id
        code = rep_map.get(note.id_repartition_instance_id)
        if not code or code not in valid_codes:
            continue
            
        valeur = note.note if note.note is not None else "-"
        notes_par_cours[cours_id][code] = valeur

    logger.warning(f"[get_student_period_notes] Found notes for {len(notes_par_cours)} cours")
    return notes_par_cours




def get_place_for_column(id_annee, id_campus, id_cycle, id_classe, id_eleve, col):

    trimestres_data = get_trimestres(id_annee, id_campus, id_cycle, id_classe)

    if len(trimestres_data) < 3:
        return "-"

    T1 = trimestres_data[0][0]
    T2 = trimestres_data[1][0]
    T3 = trimestres_data[2][0]

    mapping = {

        # PERIODES
        2:  ("periode", Deliberation_periodique_resultat, T1, "1e P"),
        3:  ("periode", Deliberation_periodique_resultat, T1, "2e P"),

        9:  ("periode", Deliberation_periodique_resultat, T2, "3e P"),
        10: ("periode", Deliberation_periodique_resultat, T2, "4e P"),

        16: ("periode", Deliberation_periodique_resultat, T3, "5e P"),
        17: ("periode", Deliberation_periodique_resultat, T3, "6e P"),

        # EXAMENS
        5:  ("examen", Deliberation_examen_resultat, T1, None),
        12: ("examen", Deliberation_examen_resultat, T2, None),
        19: ("examen", Deliberation_examen_resultat, T3, None),

        # TRIMESTRES
        7:  ("trimestre", Deliberation_trimistrielle_resultat, T1, None),
        14: ("trimestre", Deliberation_trimistrielle_resultat, T2, None),
        21: ("trimestre", Deliberation_trimistrielle_resultat, T3, None),
    }

    if col not in mapping:
        return "-"

    type_case, model, trimestre_id, periode_label = mapping[col]

    # filtre commun
    filtre = {
        "id_annee_id": id_annee,
        "idCampus_id": id_campus,
        "id_cycle_id": id_cycle,
        "id_classe_id": id_classe,
        "id_eleve_id": id_eleve,
        "id_trimestre_id": trimestre_id,
    }

    # filtre supplémentaire seulement pour les périodes
    if type_case == "periode":
        filtre["id_periode__repartition__nom"] = periode_label

    res = model.objects.filter(**filtre).first()

    if res and res.place and res.place.strip():
        return res.place.strip()

    return "-"


def injecter_places_dans_tableau(table_data, id_annee, id_campus, id_cycle, id_classe, id_eleve, id_trimestre):
    LIGNE_CIBLE_INDEX = 42  

    if len(table_data) <= LIGNE_CIBLE_INDEX:
        return False

    ligne_43 = table_data[LIGNE_CIBLE_INDEX]
    while len(ligne_43) < 24:
        ligne_43.append(None)

    place_style = ParagraphStyle(
    name='PlaceStyle',
    parent=style_normal,
    fontName='Helvetica-Bold',  
    fontSize=6,
    leading=8,
    alignment=1,
    textColor=colors.red,
    spaceBefore=0,
    spaceAfter=0
)

    colonnes_avec_places = [2, 3, 5, 7, 9, 10, 12, 14, 16, 17, 19, 21]

    for col in colonnes_avec_places:
        place = get_place_for_column(
            id_annee, id_campus, id_cycle, id_classe,
            id_eleve, col
        )
        

        ligne_43[col] = Paragraph(place, place_style)


def create_notes_table(elements, style_center, style_normal, id_annee, id_campus, id_cycle, id_classe, id_eleve):
    table_data = []
    trimestres_data = get_trimestres(id_annee, id_campus, id_cycle, id_classe)
    if trimestres_data and len(trimestres_data) == 3:
        nom_trim1 = trimestres_data[0][2]
        nom_trim2 = trimestres_data[1][2]
        nom_trim3 = trimestres_data[2][2]
    else:
        nom_trim1 = "PREMIER TRIMESTRE"
        nom_trim2 = "SECOND TRIMESTRE"
        nom_trim3 = "TROISIEME TRIMESTRE"
    table_data.append([
        Paragraph("<font color='black'><b>BRANCHES</b></font>", style_center),
        Paragraph(f"<font color='black'><b>{nom_trim1}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph(f"<font color='black'><b>{nom_trim2}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph(f"<font color='black'><b>{nom_trim3}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph("<font color='black'><b>TOTAL</b></font>", style_center), None
    ])
    id_trimestre_actif = None
    for t in trimestres_data:
        try:
            trim_obj = Annee_trimestre.objects.get(id_trimestre=t[0])
            if not trim_obj.isOpen:
                id_trimestre_actif = t[0]
                break
        except:
            pass
    if not id_trimestre_actif and trimestres_data:
        id_trimestre_actif = trimestres_data[0][0]  
        
    periodes_par_trim = get_periodes_par_trimestre(trimestres_data, id_annee, id_campus, id_cycle, id_classe)
    sous_header = [Paragraph("BRANCHES", style_center)]
    for i in range(3):
        p1 = periodes_par_trim[i][0] if len(periodes_par_trim[i]) > 0 else "-"
        p2 = periodes_par_trim[i][1] if len(periodes_par_trim[i]) > 1 else "-"
        sous_header.extend([
            Paragraph("Max per", style_center), Paragraph(p1, style_center), Paragraph(p2, style_center),
            Paragraph("Max<br/>Exam", style_center), Paragraph("PTS.OBT", style_center),
            Paragraph("MAX TRIM", style_center), Paragraph("PTS.OBT", style_center),
        ])
    sous_header.extend([Paragraph("MAX", style_center), Paragraph("PTS.OBT", style_center)])
    table_data.append(sous_header)
    domaines_cours = get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe)
    notes_periodes = get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    notes_exam = get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    for groupe in domaines_cours:
        domaine_nom = groupe['domaine']
        row_domaine = [Paragraph(f"<font color='black'><b>{domaine_nom}</b></font>", style_center)]
        table_data.append(row_domaine + [None] * 22)

        for cpc in groupe['cours']:
            nom_cours = cpc.id_cours.cours
            ponderation = cpc.TPE if cpc.TPE is not None else "-"
            max_exam = float(ponderation) * 2 if isinstance(ponderation, (int, float)) else "-"
            max_trim_val = max_exam * 2 if max_exam != "-" else "-"
            max_annee = max_trim_val * 3 if max_trim_val != "-" else "-"

            row = [Paragraph(nom_cours, style_normal)]
            id_cpc = cpc.id_cours_id
            notes_cours_periodes = notes_periodes.get(id_cpc, {})
            notes_cours_exam = notes_exam.get(id_cpc, {})

            exam_notes = {
                5: notes_cours_exam.get(trimestres_data[0][0], "-"),   
                12: notes_cours_exam.get(trimestres_data[1][0], "-"),  
                19: notes_cours_exam.get(trimestres_data[2][0], "-"),  
            }
            for col in range(1, 24):
                if col in [1, 8, 15]:          
                    row.append(Paragraph(str(ponderation), style_center))
                elif col in [4, 11, 18]:       
                    row.append(Paragraph(str(max_exam), style_center))
                elif col in [5, 12, 19]:      
                    note_ex = exam_notes.get(col, "-")
                    row.append(Paragraph(str(note_ex), style_center))
                elif col in [6, 13, 20]:    
                    row.append(Paragraph(str(max_trim_val), style_center)) 
                elif col == 22:                
                    row.append(Paragraph(str(float(max_annee) if max_trim_val != "-" else "-"), style_center))
                elif col == 23:               
                    row.append(Paragraph("-", style_center))
                elif col in [2, 3, 9, 10, 16, 17]: 
                    col_to_sigle = {
                        2: "1e P", 3: "2e P",
                        9: "3e P", 10: "4e P",
                        16: "5e P", 17: "6e P"
                    }
                    sigle = col_to_sigle[col]
                    note_val = notes_cours_periodes.get(sigle, "-")
                    row.append(Paragraph(str(note_val), style_center))
                else:
                    row.append(Paragraph("-", style_center))
            table_data.append(row)
        row_sous_total = [Paragraph("<b>Sous Total</b>", style_normal)] + [None] * 22
        table_data.append(row_sous_total)
    table_data.append([None] * 23)
    lignes_finales = [
        "MAXIMA GENEREAUX",
        "POURCENTAGE",
        "PLACE/NBRE D'ELEVES",
        "CONDUITE",
        "APPLICATION",
        "SIGNATURE DE L'INSTITEUR",
        "SIGNATURE DU RESPONSABLE"
    ]
    for texte in lignes_finales:
        if texte == "APPLICATION":
            table_data.append([Paragraph(f"<b>{texte}</b>", style_normal)] + [None] * 22)
        else:
            table_data.append([Paragraph(f"<b>{texte}</b>", style_normal)] + [None] * 22)
    calculer_sous_totaux_et_maxima(table_data, style_center)
    calculer_pts_obt_et_somme_finale(table_data, style_center)
    calculer_somme_pts_obt_maxima(table_data, style_center)
    calculer_pourcentages(table_data, style_center)
    calculer_pts_obt_trimestriels_et_annuel(table_data, style_center)
    injecter_places_dans_tableau(
        table_data,
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe,
        id_eleve=id_eleve,
        id_trimestre=id_trimestre_actif
    )

    
    
    col_widths = [30*mm] + [7.4*mm] * 22
    table = Table(table_data, colWidths=col_widths, rowHeights=[4*mm] * len(table_data))
    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.3, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.5),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (7, 0)),
        ('SPAN', (8, 0), (14, 0)),
        ('SPAN', (15, 0), (21, 0)),
        ('SPAN', (22, 0), (23, 0)),
    ])
    gris_fonce = colors.Color(red=0.2, green=0.2, blue=0.2)  
    cases_a_hachurer = [
        # Ligne 42
        (42, 2),
        (42, 5),
        (42, 7),
        (42, 9),
        (42, 12),
        (42, 14),
        (42, 16),
        (42, 19),
        (42, 21),
        (42, 23),

        # Ligne 43
        (43, 2),
        (43, 5),
        (43, 7),
        (43, 9),
        (43, 12),
        (43, 14),
        (43, 16),
        (43, 19),
        (43, 21),
        (43, 23),

        # Ligne 44
        (44, 2),
        (44, 5),
        (44, 6),
        (44, 7),
        (44, 8),
        (44, 9),
        (44, 12),
        (44, 13),
        (44, 14),
        (44, 15),
        (44, 16),
        (44, 19),
        (44, 20),
        (44, 21),
        (44, 22),
        (44, 23),

        # Ligne 45
        (45, 2),
        (45, 5),
        (45, 6),
        (45, 7),
        (45, 8),
        (45, 9),
        (45, 12),
        (45, 13),
        (45, 14),
        (45, 15),
        (45, 16),
        (45, 19),
        (45, 20),
        (45, 21),
        (45, 22),
        (45, 23),
        (45, 24)
    ]
    for ligne_num, col_num in cases_a_hachurer:
        ligne_index = ligne_num - 1  
        col_index = col_num - 1      
        if 0 <= ligne_index < len(table_data) and 0 <= col_index < len(table_data[ligne_index]):
            table_style.add('BACKGROUND', (col_index, ligne_index), (col_index, ligne_index), gris_fonce)
    lignes_a_fusionner = [3, 8, 12, 19, 22, 25, 29, 33, 37, 40]
    for ligne_num in lignes_a_fusionner:
        index_ligne = ligne_num - 1
        if 0 <= index_ligne < len(table_data):
            table_style.add('SPAN', (0, index_ligne), (-1, index_ligne))
            table_style.add('BACKGROUND', (0, index_ligne), (-1, index_ligne), colors.lightblue)    
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 0.5*mm))



def create_footer(elements, style_normal, style_center):
    footer_data = [
        [
            Paragraph("L'élève passe dans la classe supérieure<br/>L'élève double la classe<br/>(1) : Biffer la mention inutile<br/>Note importante : Le bulletin est sans valeur s'il est raturé ou surchargé", style_normal),
            Paragraph("Sceau de l'école<br/><br/>Interdiction formelle de reproduire ce bulletin sous peine des sanctions prévues par la loi", style_center),
            None
        ],
        [
            None,
            None,
            Paragraph("<font color='black'><b>Le chef de l'établissement<br/>Nom et signature : Ndayiragije Alain Fabrice</b></font>", style_normal)
        ]
    ]
    footer_table = Table(footer_data, colWidths=[70*mm, 70*mm, 50*mm])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 1), (2, 1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.5),
    ]))
    elements.append(footer_table)
    elements.append(Spacer(1, 0.5*mm))


def draw_border(canvas, doc, eleve, margin):
    canvas.setLineWidth(0.5)
    canvas.rect(margin, margin, A4[0] - 2 * margin, A4[1] - 2 * margin)
    qr_value = f"Généré par  MonEkole App,ce Bulletin est de : {eleve.nom}{eleve.prenom} Conçue par entreprise ICT Group"
    qr_code = qr.QrCodeWidget(qr_value)
    bounds = qr_code.getBounds()
    qr_width = bounds[2] - bounds[0]
    qr_height = bounds[3] - bounds[1]
    qr_size = 20*mm
    d = Drawing(qr_size, qr_size, transform=[qr_size/qr_width, 0, 0, qr_size/qr_height, 0, 0])
    d.add(qr_code)
    canvas.saveState()
    canvas.translate(180*mm, 5*mm)  
    d.drawOn(canvas, 0, 0)
    canvas.restoreState()





