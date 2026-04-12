from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from django.http import HttpResponse
from django.contrib import messages
import os
import logging
from decimal import Decimal, ROUND_HALF_UP
from MonEcole_app.models import Campus,Annee_trimestre,EtablissementAnneeClasse,Annee
from .structure_primaire import (get_styles,check_image_paths,
                                 create_header,create_nid_section,
                                 create_line2_left,get_cours_classe_rdc,
                                 get_student_period_notes,
                                 get_student_exam_notes,Deliberation_examen_resultat,
                                 Deliberation_periodique_resultat,
                                 Deliberation_trimistrielle_resultat,
                                 Deliberation_annuelle_resultat,Eleve)


logger = logging.getLogger(__name__)

styles = getSampleStyleSheet()
style_center = ParagraphStyle(name='CenterSec', parent=styles['Normal'], fontSize=10, leading=11, alignment=1)
style_center_bold = ParagraphStyle(name='CenterSecBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=5, leading=6, alignment=1)
style_normal = ParagraphStyle(name='NormalSec', parent=styles['Normal'], fontSize=10, leading=11, alignment=0)
style_normal_bold = ParagraphStyle(name='NormalSecBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=5, leading=6, alignment=0)


def get_semestres(id_annee, id_campus, id_cycle, id_classe):
    """
    Récupère les 2 semestres racine pour une classe secondaire.
    Utilise repartition_configs_cycle pour déterminer le type de répartition (Semestre/Trimestre)
    puis filtre les configs etab_annee par ce type.
    """
    from MonEcole_app.models.country_structure import RepartitionConfigCycle
    
    try:
        eac = EtablissementAnneeClasse.objects.select_related('etablissement_annee', 'classe').get(id=id_classe)
        etab_annee_id = eac.etablissement_annee_id
    except EtablissementAnneeClasse.DoesNotExist:
        return None
    
    # Déterminer le type de répartition racine pour ce cycle
    try:
        config_cycle = RepartitionConfigCycle.objects.filter(
            cycle_id=id_cycle, is_active=True
        ).first()
        if config_cycle:
            type_racine_id = config_cycle.type_racine_id
        else:
            type_racine_id = None
    except Exception:
        type_racine_id = None
    
    # Filtrer les configs par le type racine du cycle
    qs = Annee_trimestre.objects.filter(
        etablissement_annee_id=etab_annee_id,
    ).select_related('repartition')
    
    if type_racine_id:
        qs = qs.filter(repartition__type_id=type_racine_id)
    
    trimestres_qs = qs.order_by('repartition__ordre')[:2]

    if len(trimestres_qs) != 2:
        return None

    result = []
    for trimestre in trimestres_qs:
        nom_original = trimestre.repartition.nom
        rep_id = trimestre.repartition_id  # repartition_instance id
        result.append((trimestre.id_trimestre, nom_original, rep_id))

    return result



def create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal):
    """Right info section — format officiel: labels gras inline avec pointillés."""
    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
        classe_name = eac.classe.classe.strip().upper()
    except:
        return HttpResponse('<script>history.back();</script>', status=404)

    # N° PERM. boxes
    nperm_str = str(eleve.numero_serie).strip() if eleve.numero_serie else ''
    nb_cases = len(nperm_str) if nperm_str else 13
    nperm_cells = [list(nperm_str)] if nperm_str else [[None] * nb_cases]
    nperm_squares_table = Table(nperm_cells, colWidths=[4*mm]*nb_cases, rowHeights=5*mm)
    nperm_squares_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0, colors.white),
        ('INNERGRID', (0,0), (-1,-1), 0, colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    for i in range(nb_cases):
        nperm_squares_table.setStyle(TableStyle([
            ('BOX', (i,0), (i,0), 0.5, colors.black),
        ]))

    p_style = ParagraphStyle(name='InfoRightP2', fontSize=7, leading=9, alignment=0, fontName='Helvetica-Bold')

    nom_upper = (eleve.nom or '').upper()
    prenom_title = (eleve.prenom or '').title()
    sexe = (eleve.genre or '').upper()

    date_slashes = '...../ ..... /........'
    if eleve.date_naissance:
        try:
            d = eleve.date_naissance
            date_slashes = f"{d.day:02d} / {d.month:02d} / {d.year}"
        except:
            date_slashes = str(eleve.date_naissance)

    # Colonnes: col0 = label+dots, col1 = boxes (N° PERM)
    col1_w = nb_cases * 4 * mm + 1*mm
    col0_w = 116.4*mm - col1_w

    # Calcul dynamique des pointillés
    char_w = 0.88
    dot_w = 0.88
    usable_c0 = col0_w / mm - 4
    usable_full = 116.4 - 4

    # Ligne ELEVE (spanned - full width)
    eleve_label = f"ELEVE : {nom_upper} {prenom_title} "
    sexe_part = f" SEXE : {sexe} "
    eleve_total_chars = len(eleve_label) + len(sexe_part)
    eleve_remaining = usable_full - eleve_total_chars * char_w
    dots_eleve = max(3, int(eleve_remaining * 0.65 / dot_w))
    dots_sexe = max(3, int(eleve_remaining * 0.30 / dot_w))

    # Ligne NE(E) A (col0 only) + LE date (col1 aligned with boxes)
    nea_label = f"NE(E) A : "
    nea_remaining = usable_c0 - len(nea_label) * char_w
    dots_nea = max(3, int(nea_remaining / dot_w))

    # Ligne CLASSE (spanned - full width)
    classe_label = f"CLASSE : {classe_name} "
    classe_remaining = usable_full - len(classe_label) * char_w
    dots_classe = max(5, int(classe_remaining / dot_w))

    final_rows = [
        [Paragraph(f"ELEVE : {nom_upper} {prenom_title} {'.' * dots_eleve}{sexe_part}{'.' * dots_sexe}", p_style), None],
        [Paragraph(f"NE(E) A : {'.' * dots_nea}", p_style),
         Paragraph(f"LE {date_slashes} {'.' * 5}", p_style)],
        [Paragraph(f"CLASSE : {classe_name} {'.' * dots_classe}", p_style), None],
        [Paragraph("N° PERM. :", p_style), nperm_squares_table],
    ]

    right_table = Table(final_rows, colWidths=[col0_w, col1_w], rowHeights=[4.5*mm]*3 + [6*mm])
    right_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('SPAN', (0, 0), (1, 0)),  # ELEVE row spans both columns
        ('SPAN', (0, 2), (1, 2)),  # CLASSE row spans both columns
    ]))

    return right_table



def create_line2_section__secondaire_rdc(elements, left_table, right_table):
    """Combine left (40%) + right (60%) avec séparateur vertical et bordure."""
    if isinstance(right_table, tuple):
        right_table = right_table[0]

    left_w = 80*mm
    right_w = 120*mm
    line2_data = [[left_table, right_table]]
    line2_table = Table(line2_data, colWidths=[left_w, right_w])

    line2_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (0, 0), 'TOP'),
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('LINEBEFORE', (1, 0), (1, -1), 0.3, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line2_table)
    elements.append(Spacer(1, 0.5*mm))

def create_bulletin_title__secondaire_rdc(elements, style_title, style_right,id_annee,id_classe):
    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
        annee_obj = Annee.objects.filter(id_annee=id_annee).first()
        classe_name = eac.classe.classe.strip()
        
    except:
        # messages.error(request, "Classe ou année introuvable.")
        return HttpResponse('<script>history.back();</script>', status=404)
    elements.append(Spacer(1, 1.5*mm))
    # Format annee with dash: "2025-2026" → "2025 - 2026"
    annee_display = annee_obj.annee.strip().replace('-', ' - ') if annee_obj and annee_obj.annee else ''
    title_style_left = ParagraphStyle(name='TitleLeft', fontSize=7.5, leading=9, alignment=0, fontName='Times-Bold')
    title_style_right = ParagraphStyle(name='TitleRight', fontSize=7.5, leading=9, alignment=2, fontName='Times-Bold')
    title_data = [
        [Paragraph(f"<font color='black'><b>BULLETIN D'EDUCATION DE BASE DE : Classe de {classe_name}</b></font>", title_style_left),
         Paragraph(f"<font color='black'><b>ANNEE  SCOLAIRE {annee_display}</b></font>", title_style_right)]
    ]
    title_table = Table(title_data, colWidths=[120*mm, 80*mm])
    title_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(title_table)
    elements.append(Spacer(1, 1.5*mm))


    # Calcul des sous-totaux et MAXIMA (sans doublon)

        
def calculer_sous_totaux_et_maxima_secondaire(table_data, style_center):
    sous_total_indices = []
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            if "<b>Sous Total</b>" in texte:
                sous_total_indices.append(idx)

    for st_idx in sous_total_indices:
        domaine_idx = st_idx - 1
        while domaine_idx >= 0:
            texte = str(table_data[domaine_idx][0]) if table_data[domaine_idx][0] else ""
            if "<b>" in texte and "Sous Total" not in texte:
                break
            domaine_idx -= 1

        if domaine_idx < 0:
            continue

        sommes = [0.0] * 20
        for cours_idx in range(domaine_idx + 1, st_idx):
            row = table_data[cours_idx]
            for col in range(1, 20):
                if col >= len(row) or row[col] is None:
                    continue
                try:
                    val_text = str(row[col].text).strip()
                    if val_text not in ["", "-", " "]:
                        val = float(val_text)
                        sommes[col] += val
                except (ValueError, AttributeError, TypeError):
                    pass  

        st_row = table_data[st_idx]
        while len(st_row) < 20:
            st_row.append(None)

        for col in range(1, 20):
            if col >= len(st_row):
                continue
            val = sommes[col]
            st_row[col] = Paragraph(smart_format(val) if val > 0 else "-", style_center_bold)

    max_gen_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            if "MAXIMA GENEREAUX" in texte:
                max_gen_idx = idx
                break

    if max_gen_idx is None:
        return

    lignes_a_exclure = set()
    for idx, row in enumerate(table_data):
        if len(row) == 0 or row[0] is None:
            continue
        texte = str(row[0])
        if "<b>" in texte or "APPLICATION" in texte.upper() or "Sous Total" in texte or "MAXIMA GENEREAUX" in texte:
            lignes_a_exclure.add(idx)

    max_sommes = [0.0] * 20

    for row_idx in range(3, max_gen_idx):
        if row_idx in lignes_a_exclure:
            continue
        row = table_data[row_idx]
        for col in range(1, 20):
            if col >= len(row) or row[col] is None:
                continue
            try:
                val_text = str(row[col].text).strip()
                if val_text not in ["", "-", " "]:
                    val = float(val_text)
                    max_sommes[col] += val
            except (ValueError, AttributeError, TypeError):
                pass

    mg_row = table_data[max_gen_idx]
    while len(mg_row) < 20:
        mg_row.append(None)

    for col in range(1, 20):
        if col >= len(mg_row):
            continue
        val = max_sommes[col]
        mg_row[col] = Paragraph(smart_format(val) if val > 0 else "0", style_center_bold)

def smart_format(val):
    """Formate un nombre sans zéros inutiles: 54.40→54.4, 200.0→200, 3.50→3.5"""
    if val == 0:
        return "0"
    rounded = round(val, 2)
    if rounded == int(rounded):
        return str(int(rounded))
    # Remove trailing zeros: 54.40 → 54.4
    return f"{rounded:.2f}".rstrip('0').rstrip('.')


def calcul_pourcentage(valeur, maximum):
    try:
        valeur = Decimal(str(valeur))
        maximum = Decimal(str(maximum))
    except:
        return Decimal("0.00")

    if maximum > 0:
        result = (valeur / maximum) * Decimal("100")
        return result.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

    return Decimal("0.00")


def calculer_pourcentages_secondaire(table_data, style_center):
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

    # Max TJ par semestre (colonne 1 et 8)
    max_tj_sem1 = get_val(max_gen_idx, 1)
    max_tj_sem2 = get_val(max_gen_idx, 8)

    # Pondération par période = Max TJ / nombre de périodes (2 par semestre)
    max_per_p1 = max_tj_sem1 / 2 if max_tj_sem1 > 0 else 0
    max_per_p2 = max_tj_sem1 / 2 if max_tj_sem1 > 0 else 0
    max_per_p3 = max_tj_sem2 / 2 if max_tj_sem2 > 0 else 0
    max_per_p4 = max_tj_sem2 / 2 if max_tj_sem2 > 0 else 0

    max_exam_sem1 = get_val(max_gen_idx, 4)
    max_exam_sem2 = get_val(max_gen_idx, 11)
    max_tot_sem1 = get_val(max_gen_idx, 6)
    max_tot_sem2 = get_val(max_gen_idx, 13)

    note_1er_p = get_val(max_gen_idx, 2)
    note_2eme_p = get_val(max_gen_idx, 3)
    note_exam_sem1 = get_val(max_gen_idx, 5)
    tot_sem1 = get_val(max_gen_idx, 7)
    note_3e_p = get_val(max_gen_idx, 9)
    note_4eme_p = get_val(max_gen_idx, 10)
    note_exam_sem2 = get_val(max_gen_idx, 12)
    tot_sem2 = get_val(max_gen_idx, 14)

    pourcentage_row = table_data[ligne_pourcentage_idx]
    while len(pourcentage_row) < 20:
        pourcentage_row.append(None)
        
    # Périodes: pourcentage sur la pondération (max par période)
    pourcentage_row[2] = Paragraph(f"{calcul_pourcentage(note_1er_p, max_per_p1)}%", style_center_bold)
    pourcentage_row[3] = Paragraph(f"{calcul_pourcentage(note_2eme_p, max_per_p2)}%", style_center_bold)
    pourcentage_row[5] = Paragraph(f"{calcul_pourcentage(note_exam_sem1, max_exam_sem1)}%", style_center_bold)
    pourcentage_row[7] = Paragraph(f"{calcul_pourcentage(tot_sem1, max_tot_sem1)}%", style_center_bold)
    pourcentage_row[9] = Paragraph(f"{calcul_pourcentage(note_3e_p, max_per_p3)}%", style_center_bold)
    pourcentage_row[10] = Paragraph(f"{calcul_pourcentage(note_4eme_p, max_per_p4)}%", style_center_bold)
    pourcentage_row[12] = Paragraph(f"{calcul_pourcentage(note_exam_sem2, max_exam_sem2)}%", style_center_bold)
    pourcentage_row[14] = Paragraph(f"{calcul_pourcentage(tot_sem2, max_tot_sem2)}%", style_center_bold)

    # TOTAL GENERAL percentage
    max_total_gen = get_val(max_gen_idx, 15)
    total_gen_obtenu = get_val(max_gen_idx, 16)
    pourcentage_row[16] = Paragraph(f"{calcul_pourcentage(total_gen_obtenu, max_total_gen)}%", style_center_bold)


def create_notes_table__secondaire_rdc(elements, style_center, style_normal, id_annee, id_campus, id_cycle, id_classe,id_eleve):
    table_data = []
    trimestres_data = get_semestres(id_annee, id_campus, id_cycle, id_classe)
    if trimestres_data and len(trimestres_data) == 2:
        nom_trim1 = trimestres_data[0][1] 
        nom_trim2 = trimestres_data[1][1]
    
        
        if nom_trim1 in ("Semestre 1", "1er Semestre", "Trimestre 1", "1er Trimestre"):
            nom_trim1 = "PREMIER SEMESTRE"
            
        if nom_trim2 in ("Semestre 2", "2ème Semestre", "Trimestre 2", "2ème Trimestre"):
           nom_trim2 = "SECOND SEMESTRE"
    else:
        nom_trim1 = "PREMIER SEMESTRE"
        nom_trim2 = "SECOND SEMESTRE"
    table_data.append([
        Paragraph("<b>BRANCHES</b>", style_center_bold),
        Paragraph(f"<b>{nom_trim1}</b>", style_center_bold), None, None, None, None, None, None,
        Paragraph(f"<b>{nom_trim2}</b>", style_center_bold), None, None, None, None, None, None,
        Paragraph("<b>TOTAL GENERAL</b>", style_center_bold), None,
        Paragraph("", style_center_bold), 
        Paragraph("<b>EXAMEN DE REPECHAGE</b>", style_center_bold)  
    ])

    table_data.append([
        None,
        Paragraph("<b>TRAV.JOUR.</b>", style_center_bold), None, None,
        Paragraph("<b>EXAM</b>", style_center_bold), None,
        Paragraph("<b>TOT.SEM</b>", style_center_bold), None,
        Paragraph("<b>TRAV.JOUR.</b>", style_center_bold), None, None,
        Paragraph("<b>EXAM</b>", style_center_bold), None,
        Paragraph("<b>TOT.SEM</b>", style_center_bold), None,
        None, None, 
        None,     
        None      
    ])

    table_data.append([
        Paragraph("BRANCHES", style_center),
        Paragraph("Max", style_center), Paragraph("1e P", style_center), Paragraph("2e P", style_center),
        None, None, None, None,
        Paragraph("Max", style_center), Paragraph("3e P", style_center), Paragraph("4e P", style_center),
        None, None, None, None,
        None, None, 
        Paragraph("", style_center),  
        Paragraph("%", style_center),  
        Paragraph("Sign. prof.", style_center)  
    ])
    

    domaines_cours = get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe)
    notes_periodes = get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    notes_exam = get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    
    
    lignes_domaines = [3, 8, 13, 19, 24, 29, 36]  
    domaine_index = 0 
    ligne_courante = 3  
  
    # Use repartition_id (index 2) for places since deliberation tables store repartition_instance_id
    id_semestre_actif_rep = None
    for s in trimestres_data:
        try:
            sem_obj = Annee_trimestre.objects.get(id=s[0]) 
            if not sem_obj.isOpen:       
                id_semestre_actif_rep = s[2]  # repartition_id
                break
        except:
            pass

    if not id_semestre_actif_rep and trimestres_data:
        id_semestre_actif_rep = trimestres_data[0][2]  # repartition_id
          
    for groupe in domaines_cours:
        domaine_nom = groupe['domaine']

        row_domaine = [Paragraph(f"<b>{domaine_nom}</b>", style_center_bold)]
        table_data.append(row_domaine + [None] * 19) 

        if domaine_index < len(lignes_domaines) and ligne_courante == lignes_domaines[domaine_index]:
            domaine_index += 1
            ligne_courante += 1  

        for cpc in groupe['cours']:
            nom_cours = cpc.id_cours.cours
            ponderation = cpc.maxima_tj if cpc.maxima_tj is not None else "-"
            exam = cpc.maxima_exam if cpc.maxima_exam is not None else "-"
            row = [Paragraph(nom_cours, style_normal)]
            id_cpc = cpc.id_cours_id
            notes_cours_periodes = notes_periodes.get(id_cpc, {})

            row = [Paragraph(nom_cours, style_normal)]
            id_cpc = cpc.id_cours_id
            notes_cours_periodes = notes_periodes.get(id_cpc, {})
            notes_cours_exam = notes_exam.get(id_cpc, {})
           
            exam_notes = {
                5: notes_cours_exam.get(trimestres_data[0][0], "-"),   
                12: notes_cours_exam.get(trimestres_data[1][0], "-"),  
            }
            val_exam_t1 = "0"
            val_exam_t2 = "0"
            val_tot_sem_t1 = "0"
            val_tot_sem_t2 = "0"

            for col in range(1, 20):
                if col in [2, 3, 9, 10]:
                    note_val = notes_cours_periodes.get(col, "-")
                    row.append(Paragraph(str(note_val), style_center))

                elif col in [1, 8]:
                    row.append(Paragraph(str(ponderation), style_center_bold))

                elif col in [4, 11]:
                    exam_val = exam if exam != "-" else "0"
                    row.append(Paragraph(str(exam_val), style_center_bold))
                    if col == 4:
                        val_exam_t1 = exam_val
                    if col == 11:
                        val_exam_t2 = exam_val
                elif col in [5, 12]:      
                    note_ex = exam_notes.get(col, "-")
                    row.append(Paragraph(str(note_ex), style_center))
                elif col == 6: 
                    # Max TOT.SEM = Max TJ (ponderation) + Max Exam
                    pond_val = float(ponderation) if ponderation != "-" else 0.0
                    val_tot_sem_t1 = pond_val + float(val_exam_t1)
                    display_tot_sem = str(int(val_tot_sem_t1)) if val_tot_sem_t1 == int(val_tot_sem_t1) else str(val_tot_sem_t1)
                    row.append(Paragraph(display_tot_sem, style_center_bold))

                elif col == 13: 
                    # Max TOT.SEM = Max TJ (ponderation) + Max Exam
                    pond_val = float(ponderation) if ponderation != "-" else 0.0
                    val_tot_sem_t2 = pond_val + float(val_exam_t2)
                    display_tot_sem = str(int(val_tot_sem_t2)) if val_tot_sem_t2 == int(val_tot_sem_t2) else str(val_tot_sem_t2)
                    row.append(Paragraph(display_tot_sem, style_center_bold))

                elif col == 7:  
                    tot_s1 = 0.0
                    try:
                        tot_s1 += float(row[2].text or 0) if len(row) > 2 and row[2] else 0.0
                        tot_s1 += float(row[3].text or 0) if len(row) > 3 and row[3] else 0.0
                        tot_s1 += float(row[5].text or 0) if len(row) > 5 and row[5] else 0.0
                    except:
                        tot_s1 = 0.0
                    row.append(Paragraph(smart_format(tot_s1), style_center))

                elif col == 14: 
                    tot_s2 = 0.0
                    try:
                        tot_s2 += float(row[9].text or 0) if len(row) > 9 and row[9] else 0.0
                        tot_s2 += float(row[10].text or 0) if len(row) > 10 and row[10] else 0.0
                        tot_s2 += float(row[12].text or 0) if len(row) > 12 and row[12] else 0.0
                    except:
                        tot_s2 = 0.0
                    row.append(Paragraph(smart_format(tot_s2), style_center))

                elif col == 15:
                    # TOTAL GENERAL col 15 = Max Total (TOT.SEM Max S1 + TOT.SEM Max S2)
                    try:
                        tot_max = float(row[6].text or 0) + float(row[13].text or 0)
                    except:
                        tot_max = 0.0
                    row.append(Paragraph(smart_format(tot_max), style_center_bold))

                elif col == 16:
                    # TOTAL GENERAL col 16 = Total Obtenu (TOT S1 + TOT S2)
                    try:
                        tot_gen = float(row[7].text or 0) + float(row[14].text or 0)
                    except:
                        tot_gen = 0.0
                    row.append(Paragraph(smart_format(tot_gen), style_center))

                elif col in [17, 18, 19]:
                    row.append(None)

                else:
                    row.append(Paragraph("-", style_center))

            table_data.append(row)


        row_sous_total = [Paragraph("<b>Sous Total</b>", style_normal_bold)] + [None] * 19
        table_data.append(row_sous_total)
        ligne_courante += 1  
    lignes_finales = [
        "MAXIMA GENEREAUX",
        "POURCENTAGE",
        "PLACE/NBRE D'ELEVES",
        "CONDUITE",
        "APPLICATION",
        "SIGNATURE DU RESPONSABLE"
    ]

    for texte in lignes_finales:
        table_data.append([Paragraph(f"<b>{texte}</b>", style_normal_bold)] + [None] * 19)
    calculer_sous_totaux_et_maxima_secondaire(table_data, style_center_bold)
    calculer_pourcentages_secondaire(table_data, style_center)
    injecter_places_secondaire(
        table_data,
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe,
        id_eleve=id_eleve,
        id_semestre=id_semestre_actif_rep,
        semestres_data=trimestres_data 
    )
    # Post-processing : vider les colonnes non-délibérées
    from .structure_primaire import blank_non_deliberated_columns
    blank_non_deliberated_columns(
        table_data, id_eleve, id_classe, trimestres_data,
        style_center, bulletin_type='secondaire'
    )
    col_widths = [30*mm] + [8.22*mm] * 17 + [10*mm] + [20*mm]

    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('SPAN', (0, 0), (0, 2)),
        ('SPAN', (1, 0), (7, 0)),
        ('SPAN', (1, 1), (3, 1)),
        ('SPAN', (4, 1), (5, 2)),
        ('SPAN', (6, 1), (7, 2)),
        ('SPAN', (8, 0), (14, 0)),
        ('SPAN', (8, 1), (10, 1)),
        ('SPAN', (11, 1), (12, 2)),
        ('SPAN', (13, 1), (14, 2)),
        ('SPAN', (15, 0), (16, 2)),   
        ('SPAN', (17, 0), (17, 2)), 
        ('SPAN', (18, 0), (19, 1)),   
    ])

    num_rows = len(table_data)

    # Appliquer SPAN/BACKGROUND dynamiquement pour les lignes de domaine
    # + bold pour Sous Total et MAXIMA
    for row_idx in range(3, num_rows):
        row = table_data[row_idx]
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            if "<b>" in texte and "Sous Total" not in texte and "MAXIMA" not in texte and "POURCENTAGE" not in texte and "PLACE" not in texte and "CONDUITE" not in texte and "APPLICATION" not in texte and "SIGNATURE" not in texte:
                table_style.add('SPAN', (0, row_idx), (-1, row_idx))
                table_style.add('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightblue)
            elif "Sous Total" in texte:
                pass  # Bold already handled via Paragraph style_normal_bold + style_center_bold
            elif "MAXIMA" in texte:
                pass  # Bold already handled via Paragraph style_normal_bold + style_center_bold

    # Colonne séparatrice (col 17) — fond gris foncé
    col_hachuree = 17
    separator_gray = colors.Color(0.45, 0.45, 0.45)
    for row_idx in range(4, num_rows):
        if col_hachuree < len(table_data[row_idx]):
            table_data[row_idx][col_hachuree] = None
    # Fusionner verticalement + background gris foncé pour la séparatrice
    if num_rows > 4:
        table_style.add('SPAN', (col_hachuree, 4), (col_hachuree, num_rows - 1))
        table_style.add('BACKGROUND', (col_hachuree, 4), (col_hachuree, num_rows - 1), separator_gray)
        table_style.add('LINEAFTER', (col_hachuree - 1, 4), (col_hachuree - 1, num_rows - 1), 0.5, colors.black)
        table_style.add('LINEAFTER', (col_hachuree, 4), (col_hachuree, num_rows - 1), 0.5, colors.black)

    # Même gris foncé pour cols 18-19 sur les lignes domaines + sous-totaux
    for row_idx in range(3, num_rows):
        row = table_data[row_idx]
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            has_bg = False
            if "<b>" in texte and "Sous Total" not in texte and "MAXIMA" not in texte and "POURCENTAGE" not in texte and "PLACE" not in texte and "CONDUITE" not in texte and "APPLICATION" not in texte and "SIGNATURE" not in texte:
                has_bg = True
            elif "Sous Total" in texte:
                has_bg = True
            if has_bg:
                table_style.add('BACKGROUND', (18, row_idx), (19, row_idx), separator_gray)
            
    # Lignes finales (MAXIMA, POURCENTAGE, etc.) — colonnes structurelles avec background gris
    maxima_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph) and "MAXIMA GENEREAUX" in (row[0].text or ""):
            maxima_idx = idx
            break

    if maxima_idx is not None:
        # Colonnes séparatrices: clear data from POURCENTAGE through APPLICATION
        colonnes_struct = [1, 4, 6, 8, 11, 13]
        for row_idx in range(maxima_idx + 1, min(maxima_idx + 5, num_rows)):
            for col_idx in colonnes_struct:
                if col_idx < len(table_data[row_idx]):
                    table_data[row_idx][col_idx] = None

        colonnes_struct_2 = [5, 7, 12, 14]
        for row_idx in range(maxima_idx + 3, min(maxima_idx + 5, num_rows)):
            for col_idx in colonnes_struct_2:
                if row_idx < num_rows and col_idx < len(table_data[row_idx]):
                    table_data[row_idx][col_idx] = None

        # Fusion VERTICALE des colonnes séparatrices (POURCENTAGE → APPLICATION = 4 lignes)
        end_row = min(maxima_idx + 4, num_rows - 1)
        for col_idx in colonnes_struct:
            table_style.add('SPAN', (col_idx, maxima_idx + 1), (col_idx, end_row))
            table_style.add('BACKGROUND', (col_idx, maxima_idx + 1), (col_idx, end_row), separator_gray)

        # Fusion VERTICALE colonnes secondaires (CONDUITE → APPLICATION = 2 lignes)
        if maxima_idx + 4 < num_rows:
            for col_idx in colonnes_struct_2:
                table_style.add('SPAN', (col_idx, maxima_idx + 3), (col_idx, maxima_idx + 4))
                table_style.add('BACKGROUND', (col_idx, maxima_idx + 3), (col_idx, maxima_idx + 4), separator_gray)

        # CONDUITE + APPLICATION: fusionner les cellules vides horizontalement + gray
        for offset in [3, 4]:  # CONDUITE=+3, APPLICATION=+4
            row_idx = maxima_idx + offset
            if row_idx < num_rows:
                # Cols 2-3 (entre séparateurs 1 et 4)
                for c in [2, 3]:
                    if c < len(table_data[row_idx]):
                        table_data[row_idx][c] = None
                table_style.add('SPAN', (2, row_idx), (3, row_idx))
                table_style.add('BACKGROUND', (2, row_idx), (3, row_idx), separator_gray)
                # Cols 9-10 (entre séparateurs 8 et 11)
                for c in [9, 10]:
                    if c < len(table_data[row_idx]):
                        table_data[row_idx][c] = None
                table_style.add('SPAN', (9, row_idx), (10, row_idx))
                table_style.add('BACKGROUND', (9, row_idx), (10, row_idx), separator_gray)
                # Cols 15-16 (Total Général)
                for c in [15, 16]:
                    if c < len(table_data[row_idx]):
                        table_data[row_idx][c] = None
                table_style.add('SPAN', (15, row_idx), (16, row_idx))
                table_style.add('BACKGROUND', (15, row_idx), (16, row_idx), separator_gray)

        # SIGNATURE DU RESPONSABLE (dernière ligne finale): fusion horizontale complète, sans background
        sig_row = maxima_idx + 5
        if sig_row < num_rows:
            for c in range(1, 17):
                if c < len(table_data[sig_row]):
                    table_data[sig_row][c] = None
            table_style.add('SPAN', (0, sig_row), (16, sig_row))

    # Zone signature en bas à droite
    signature_start = num_rows - 5 if num_rows > 5 else num_rows - 1
    signature_end = num_rows - 1
    if signature_start >= 0 and signature_end < num_rows and signature_start < signature_end:
        # Vider toutes les cellules dans la zone du SPAN avant de fusionner
        for r in range(signature_start, signature_end + 1):
            if r < len(table_data):
                for c in [18, 19]:
                    if c < len(table_data[r]):
                        table_data[r][c] = None
        table_style.add('SPAN', (18, signature_start), (19, signature_end))
        table_style.add('BOX', (18, signature_start), (19, signature_end), 0.5, colors.black)

    texte_visible = (
        "Passe(1)<br/>"
        "Double(1)<br/>"
        "A échoué(1)<br/>"
        "<br/>"
        "Le Chef d'Établissement<br/>"
        "Sceau de l'école"
    )

    style_visible = ParagraphStyle(
        name='TexteVisible',
        parent=style_center,
        fontSize=7,
        leading=9,         
        alignment=1,       
        textColor=colors.black,
        spaceBefore=2,
        spaceAfter=2
    )
    if signature_start < len(table_data) and 18 < len(table_data[signature_start]):
        table_data[signature_start][18] = Paragraph(texte_visible, style_visible)
    
    table = Table(table_data, colWidths=col_widths, rowHeights=[4.5*mm] * len(table_data))
    # ── Ligne PLACE : texte bleu foncé + gras ──
    for ridx, row in enumerate(table_data):
        texte = str(row[0]) if row and row[0] else ""
        if "PLACE" in texte.upper():
            table_style.add('TEXTCOLOR', (0, ridx), (-1, ridx), colors.HexColor('#0000CC'))
            table_style.add('FONTNAME', (0, ridx), (-1, ridx), 'Helvetica-Bold')
            break

    # ── Post-traitement : notes < 50% du max ⇒ rouge ──
    import re
    for row_idx in range(2, len(table_data)):
        row = table_data[row_idx]
        if len(row) < 17:
            continue
        texte = str(row[0]) if row[0] else ""
        texte_upper = texte.upper()
        if any(mot in texte_upper for mot in [
            "APPLICATION", "MAXIMA", "POURCENTAGE",
            "PLACE", "CONDUITE", "SIGNATURE", "SOUS TOTAL", "BRANCHES"
        ]):
            continue
        if "<b>" in texte and "Sous Total" not in texte and len(texte) > 20:
            continue

        # PTS.OBT semestriels: col 7 vs max col 6, col 14 vs max col 13
        for pts_col, max_col in [(7, 6), (14, 13)]:
            if pts_col < len(row) and max_col < len(row):
                try:
                    pts_txt = str(row[pts_col]) if row[pts_col] else ""
                    max_txt = str(row[max_col]) if row[max_col] else ""
                    pts_nums = re.findall(r'[\d.]+', pts_txt)
                    max_nums = re.findall(r'[\d.]+', max_txt)
                    if pts_nums and max_nums:
                        pts_val = float(pts_nums[-1])
                        max_val = float(max_nums[-1])
                        if max_val > 0 and pts_val < max_val / 2:
                            row[pts_col] = Paragraph(f"<font color='red'><b>{pts_nums[-1]}</b></font>", style_center)
                except:
                    pass

        # PTS.OBT annuel: col 16 vs max col 15 (secondaire layout)
        if 16 < len(row) and 15 < len(row):
            try:
                pts_txt = str(row[16]) if row[16] else ""
                max_txt = str(row[15]) if row[15] else ""
                pts_nums = re.findall(r'[\d.]+', pts_txt)
                max_nums = re.findall(r'[\d.]+', max_txt)
                if pts_nums and max_nums:
                    pts_val = float(pts_nums[-1])
                    max_val = float(max_nums[-1])
                    if max_val > 0 and pts_val < max_val / 2:
                        row[16] = Paragraph(f"<font color='red'><b>{pts_nums[-1]}</b></font>", style_center)
            except:
                pass

    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 0.5*mm))
   
   
def create_footer__secondaire_rdc(elements, style_normal, style_center, classe_id):
    """Footer matching official RDC bulletin format — used by secondaire and cycle supérieur."""
    elements.append(Spacer(1, 5*mm))  # Detach footer from content
    # Retrieve institution info for dynamic footer
    chef_nom = ""
    ville = ""
    ecole_nom = ""
    if classe_id:
        try:
            _eac = EtablissementAnneeClasse.objects.select_related('etablissement_annee').get(id=classe_id)
            etab_id = _eac.etablissement_annee.etablissement_id
            from django.db import connections
            with connections['countryStructure'].cursor() as cur:
                cur.execute(
                    "SELECT nom, representant, emplacement FROM etablissements WHERE id_etablissement = %s",
                    [etab_id]
                )
                row = cur.fetchone()
                if row:
                    ecole_nom = row[0] or ""
                    chef_nom = row[1] or ""
                    ville = row[2] or ""
        except Exception:
            pass

    style_footer = ParagraphStyle(name='FooterTextSec', fontSize=4, leading=5, alignment=0, fontName='Times-Roman')
    style_footer_center = ParagraphStyle(name='FooterCenterSec', fontSize=4, leading=5, alignment=1, fontName='Times-Roman')
    style_footer_right = ParagraphStyle(name='FooterRightSec', fontSize=4, leading=5, alignment=0, fontName='Times-Roman')

    import datetime
    date_str = datetime.date.today().strftime('%d/%m/%Y')
    fait_a = f"Fait à {ville} le {date_str}" if ville else f"Fait le {date_str}"

    # Row 1: repêchage line (full width)
    repechage_line = Paragraph(
        "L'élève ne pourra pas passer dans la classe supérieure s'il n'a pas subi avec succès "
        "un examen de repêchage en ..............................................................",
        style_footer
    )

    # Row 2: three-column layout
    left_col = Paragraph(
        "L'élève passe dans la classe supérieure (1)<br/>"
        "L'élève double la classe (1)",
        style_footer
    )
    center_col = Paragraph("Sceau de l'école", style_footer_center)
    right_col = Paragraph(
        f"{fait_a}<br/>"
        f"Le chef de l'Établissement<br/>"
        f"Nom et Signature<br/>"
        f"<b>{chef_nom}</b>",
        style_footer_right
    )

    # Row 3: note
    note_line = Paragraph(
        "(1): Biffer la mention inutile<br/>"
        "<b>NOTE IMPORTANTE</b>: Le bulletin est sans importance s'il est raturé ou surchargé",
        style_footer
    )

    # Row 4: branding
    branding = Paragraph(
        "<i>Proclamation générée par MonEkole (https://monecole.pro)</i>",
        style_footer_center
    )

    # Build the footer table
    footer_data = [
        [repechage_line, None, None],
        [left_col, center_col, right_col],
        [note_line, None, None],
        [branding, None, None],
    ]
    footer_table = Table(footer_data, colWidths=[70*mm, 50*mm, 70*mm])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 0), (2, 0)),   # repêchage line full width
        ('SPAN', (0, 2), (2, 2)),   # note line full width
        ('SPAN', (0, 3), (2, 3)),   # branding full width
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(footer_table)
    elements.append(Spacer(1, 4*mm))  
    resultat_table = None

    eac = EtablissementAnneeClasse.objects.select_related('classe').filter(id=classe_id).first()
    if eac:
        classe_name = eac.classe.classe if eac.classe else ""

        if classe_name == "8ème A E.B":
            resultat_data = [
                [
                    Paragraph("<b>RESULTAT FINAL</b>", style_center),
                    Paragraph("<b>POINTS OBTENUS</b>", style_center),
                    Paragraph("<b>MAX</b>", style_center),
                ],
                [
                    Paragraph("MOYENNE ECOLE", style_normal),
                    Paragraph("XX.XX", style_center), 
                    Paragraph("XX.XX", style_center),
                ],
                [
                    Paragraph("ENAFEP", style_normal),
                    Paragraph("XX.XX", style_center),
                    Paragraph("XX.XX", style_center),
                ],
                [
                    Paragraph("TOTAL", style_normal),
                    Paragraph("XX.XX", style_center),
                    Paragraph("XX.XX", style_center),
                ]
            ]

            resultat_table = Table(resultat_data, colWidths=[70*mm, 50*mm, 40*mm])

            resultat_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                ('LEFTPADDING', (0, 0), (-1, -1), 4*mm), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 2*mm),
            ]))

    if resultat_table:
        elements.append(Spacer(5*mm, 0))  
        elements.append(resultat_table)
        elements.append(Spacer(1, 2*mm))

    # Espace final
    elements.append(Spacer(1, 0.5*mm))

def draw_border__secondaire_rdc(canvas, doc, eleve, margin, watermark_path=None):
    canvas.setLineWidth(0.5)
    canvas.rect(margin, margin, A4[0] - 2 * margin, A4[1] - 2 * margin)
    # Watermark: armoirie du pays en filigrane au centre
    if watermark_path and os.path.exists(watermark_path):
        canvas.saveState()
        canvas.setFillAlpha(0.15)
        page_w, page_h = A4
        wm_size = 140 * mm
        x = (page_w - wm_size) / 2
        y = (page_h - wm_size) / 2
        canvas.drawImage(watermark_path, x, y, width=wm_size, height=wm_size,
                         preserveAspectRatio=True, mask='auto')
        canvas.restoreState()
    qr_value = f"Généré par Application MonEkole,ce Bulletin est de : {eleve.nom}{eleve.prenom} Conçue par entreprise ICT Group"
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
    
    
    



def injecter_places_secondaire(table_data, id_annee, id_campus, id_cycle, id_classe, id_eleve, id_semestre, semestres_data=None):
    # Trouver dynamiquement la ligne PLACE/NBRE D'ELEVES
    place_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            if "PLACE" in texte:
                place_idx = idx
                break

    if place_idx is None:
        logger.warning("[injecter_places_secondaire] Ligne PLACE non trouvée")
        return False

    ligne_place = table_data[place_idx]
    while len(ligne_place) < 20:
        ligne_place.append(None)

    colonnes_avec_places = [2, 3, 5, 7, 9, 10, 12, 14, 16]

    place_style = ParagraphStyle(
        name='PlaceStyleSecondaire',
        parent=style_normal,         
        fontName='Helvetica-Bold',
        fontSize=5,                
        leading=6,
        alignment=1,                
        textColor=colors.HexColor('#0000CC'),
        spaceBefore=0,
        spaceAfter=0
    )

    places_injectees = 0

    for col in colonnes_avec_places:
        place = get_place_secondaire(
            id_annee, id_campus, id_cycle, id_classe,
            id_eleve, id_semestre, col, semestres_data=semestres_data
        )

        ligne_place[col] = Paragraph(f"<font color='#0000CC'><b>{place}</b></font>", place_style)

        if place != "-":
            places_injectees += 1

    return places_injectees > 0

def _normalize_place(place_raw, result_model, filtre_key, filtre_base, config_id=None):
    """Convertit '1er'/'1ère'/'40ème' en '1/N' format. Si déjà 'X/Y', retourne tel quel."""
    import re
    if not place_raw or place_raw.strip() == '-':
        return "-"
    place = place_raw.strip()
    # Déjà au format X/Y
    if '/' in place:
        return place
    # Extraire le rang numérique
    match = re.match(r'(\d+)', place)
    if not match:
        return place
    rank = match.group(1)
    # Compter le total d'élèves dans la même délibération
    try:
        count_filtre = {k: v for k, v in filtre_base.items() if k != 'id_eleve_id'}
        if config_id and filtre_key:
            count_filtre[filtre_key] = config_id
        total = result_model.objects.filter(**count_filtre).count()
        return f"{rank}/{total}" if total > 0 else place
    except Exception:
        return place

def get_place_secondaire(id_annee, id_campus, id_cycle, id_classe, id_eleve, id_semestre, col, semestres_data=None):
    """
    Récupère le classement depuis les tables de délibération.
    Utilise config_id (PK de repartition_configs_etab_annee) car c'est ce que 
    execute_deliberation stocke dans id_periode_id / id_trimestre_id.
    """
    from django.db import connections
    
    if not semestres_data:
        semestres_data = get_semestres(id_annee, id_campus, id_cycle, id_classe)
    
    if not semestres_data:
        return "-"
    
    # Resolve EAC → business keys
    from MonEcole_app.models.country_structure import EtablissementAnneeClasse as _EAC
    try:
        _eac = _EAC.objects.get(id=id_classe)
        bk_classe_id = _eac.classe_id
        bk_groupe = _eac.groupe
        bk_section_id = _eac.section_id
        etab_annee_id = _eac.etablissement_annee_id
    except _EAC.DoesNotExist:
        return "-"

    filtre_base = {
        "id_classe_id": bk_classe_id,
        "groupe": bk_groupe,
        "section_id": bk_section_id,
        "id_eleve_id": id_eleve,
    }

    # Build code→config_id mapping from DB
    code_to_config = {}
    try:
        with connections['countryStructure'].cursor() as cur:
            cur.execute("""
                SELECT rc.id, ri.code
                FROM repartition_configs_etab_annee rc
                JOIN repartition_instances ri ON ri.id_instance = rc.repartition_id
                WHERE rc.etablissement_annee_id = %s
            """, [etab_annee_id])
            for row in cur.fetchall():
                code_to_config[row[1]] = row[0]
    except Exception:
        pass

    # Colonnes périodes (TJ)
    if col in [2, 3, 9, 10]:
        col_to_code = {2: "P1", 3: "P2", 9: "P3", 10: "P4"}
        code = col_to_code.get(col)
        config_id = code_to_config.get(code)
        if not config_id:
            return "-"
        filtre = {**filtre_base, "id_periode_id": config_id}
        res = Deliberation_periodique_resultat.objects.filter(**filtre).first()
        raw = res.place.strip() if res and res.place and res.place.strip() else "-"
        return _normalize_place(raw, Deliberation_periodique_resultat, "id_periode_id", filtre_base, config_id)

    # Colonnes examen (sem1=col5, sem2=col12)
    if col in [5, 12]:
        sem_code = "S1" if col == 5 else "S2"
        config_id = code_to_config.get(sem_code)
        if not config_id:
            return "-"
        filtre = {**filtre_base, "id_trimestre_id": config_id}
        res = Deliberation_examen_resultat.objects.filter(**filtre).first()
        raw = res.place.strip() if res and res.place and res.place.strip() else "-"
        return _normalize_place(raw, Deliberation_examen_resultat, "id_trimestre_id", filtre_base, config_id)

    # Colonnes total semestre (sem1=col7, sem2=col14)
    if col in [7, 14]:
        sem_code = "S1" if col == 7 else "S2"
        config_id = code_to_config.get(sem_code)
        if not config_id:
            return "-"
        filtre = {**filtre_base, "id_trimestre_id": config_id}
        res = Deliberation_trimistrielle_resultat.objects.filter(**filtre).first()
        raw = res.place.strip() if res and res.place and res.place.strip() else "-"
        return _normalize_place(raw, Deliberation_trimistrielle_resultat, "id_trimestre_id", filtre_base, config_id)

    # Col 16 = TOTAL GENERAL (deliberation annuelle)
    if col == 16:
        res = Deliberation_annuelle_resultat.objects.filter(**filtre_base).first()
        raw = res.place.strip() if res and res.place and res.place.strip() else "-"
        return _normalize_place(raw, Deliberation_annuelle_resultat, None, filtre_base)

    return "-"


