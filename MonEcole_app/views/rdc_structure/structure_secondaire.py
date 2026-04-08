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
style_center = styles['Normal']
style_center.alignment = 1 
style_normal = styles['Normal']
style_normal.alignment = 0  


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
    """Right info section with proper 3-column alignment: Label | : | Value."""
    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
        classe_name = eac.classe.classe.strip()
    except:
        return HttpResponse('<script>history.back();</script>', status=404)

    # N.PERM = numero_serie from eleve table — detached boxes
    nperm_str = str(eleve.numero_serie).strip() if eleve.numero_serie else ''
    nb_cases = len(nperm_str) if nperm_str else 13
    nperm_cells = [list(nperm_str)] if nperm_str else [[None] * nb_cases]
    nperm_squares_table = Table(nperm_cells, colWidths=[3.5*mm]*nb_cases, rowHeights=4.5*mm)
    nperm_squares_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0, colors.white),
        ('INNERGRID', (0,0), (-1,-1), 0, colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Times-Bold'),
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

    # Distinct styles for labels and values
    lbl_style = ParagraphStyle(name='InfoLabelR', fontSize=6, leading=8, alignment=0, fontName='Helvetica-Bold')
    val_style = ParagraphStyle(name='InfoValueR', fontSize=6, leading=8, alignment=0, fontName='Times-Roman')
    colon_style = ParagraphStyle(name='InfoColonR', fontSize=6, leading=8, alignment=1, fontName='Helvetica-Bold')

    # Lieu de naissance
    lieu = getattr(eleve, 'naissance_commune', None) or getattr(eleve, 'Lieu_naissance', None) or '..........'

    right_data = [
        [Paragraph("ELEVE", lbl_style), Paragraph(":", colon_style),
         Paragraph(f"{eleve.nom} {eleve.prenom}", val_style),
         Paragraph("SEXE", lbl_style), Paragraph(":", colon_style),
         Paragraph(f"{eleve.genre}", val_style)],
        [Paragraph("Ne(e) A", lbl_style), Paragraph(":", colon_style),
         Paragraph(f"{lieu}", val_style),
         Paragraph("DATE NAISSANCE", lbl_style), Paragraph(":", colon_style),
         Paragraph(f"{eleve.date_naissance}", val_style)],
        [Paragraph("CLASSE", lbl_style), Paragraph(":", colon_style),
         Paragraph(f"{classe_name}", val_style),
         None, None, None],
        [Paragraph("N.PERM", lbl_style), Paragraph(":", colon_style),
         nperm_squares_table,
         None, None, None],
    ]
    right_table = Table(right_data, colWidths=[20*mm, 3*mm, 30*mm, 22*mm, 3*mm, 22*mm])
    right_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'LEFT'),
        ('ALIGN', (3, 0), (3, -1), 'LEFT'),
        ('ALIGN', (4, 0), (4, -1), 'CENTER'),
        ('ALIGN', (5, 0), (5, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('SPAN', (2, 3), (5, 3)),  # N.PERM value spans remaining columns
    ]))
    return right_table 



def create_line2_section__secondaire_rdc(elements, left_table, right_table):
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

def create_bulletin_title__secondaire_rdc(elements, style_title, style_right,id_annee,id_classe):
    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
        annee_obj = Annee.objects.filter(id_annee=id_annee).first()
        classe_name = eac.classe.classe.strip()
        
    except:
        # messages.error(request, "Classe ou année introuvable.")
        return HttpResponse('<script>history.back();</script>', status=404)
    elements.append(Spacer(1, 2*mm))
    title_data = [
        [Paragraph(f"<font color='black'><b>BULLETIN DE :{classe_name}  EDUCATION DE BASE</b></font>", style_title),
         Paragraph(f"<font color='black'><b>ANNEE SCOLAIRE :{annee_obj.annee} </b></font>", style_right)]
    ]
    title_table = Table(title_data, colWidths=[100*mm, 100*mm])
    title_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(title_table)
    elements.append(Spacer(1, 2*mm))


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
            val_net = round(val, 2)
            if abs(val_net - round(val_net)) < 1e-10:
                display_val = str(int(val_net))
            else:
                display_val = f"{val_net:.2f}"

            st_row[col] = Paragraph(display_val if val > 0 else "-", style_center)

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
        val_net = round(val, 2)
        if abs(val_net - round(val_net)) < 1e-10:
            display_val = str(int(val_net))
        else:
            display_val = f"{val_net:.2f}"

        mg_row[col] = Paragraph(display_val if val > 0 else "0", style_center)

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
    pourcentage_row[2] = Paragraph(f"{calcul_pourcentage(note_1er_p, max_per_p1)}%", style_center)
    pourcentage_row[3] = Paragraph(f"{calcul_pourcentage(note_2eme_p, max_per_p2)}%", style_center)
    pourcentage_row[5] = Paragraph(f"{calcul_pourcentage(note_exam_sem1, max_exam_sem1)}%", style_center)
    pourcentage_row[7] = Paragraph(f"{calcul_pourcentage(tot_sem1, max_tot_sem1)}%", style_center)
    pourcentage_row[9] = Paragraph(f"{calcul_pourcentage(note_3e_p, max_per_p3)}%", style_center)
    pourcentage_row[10] = Paragraph(f"{calcul_pourcentage(note_4eme_p, max_per_p4)}%", style_center)
    pourcentage_row[12] = Paragraph(f"{calcul_pourcentage(note_exam_sem2, max_exam_sem2)}%", style_center)
    pourcentage_row[14] = Paragraph(f"{calcul_pourcentage(tot_sem2, max_tot_sem2)}%", style_center)

    # TOTAL GENERAL percentage
    max_total_gen = get_val(max_gen_idx, 15)
    total_gen_obtenu = get_val(max_gen_idx, 16)
    pourcentage_row[16] = Paragraph(f"{calcul_pourcentage(total_gen_obtenu, max_total_gen)}%", style_center)


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
        Paragraph("<font color='black'><b>BRANCHES</b></font>", style_center),
        Paragraph(f"<font color='black'><b>{nom_trim1}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph(f"<font color='black'><b>{nom_trim2}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph("<font color='black'><b>TOTAL GENERAL</b></font>", style_center), None,
        Paragraph("<font color='black'><b></b></font>", style_center), 
        Paragraph("<font color='black'><b>EXAMEN DE REPECHAGE</b></font>", style_center)  
    ])

    table_data.append([
        None,
        None, Paragraph("<font color='black'><b>TRAV.JOUR.</b></font>", style_center), None,
        Paragraph("<font color='black'><b>EXAM</b></font>", style_center), None,
        Paragraph("<font color='black'><b>TOT.SEM</b></font>", style_center), None,
        None, Paragraph("<font color='black'><b>TRAV.JOUR.</b></font>", style_center), None,
        Paragraph("<font color='black'><b>EXAM</b></font>", style_center), None,
        Paragraph("<font color='black'><b>TOT.SEM</b></font>", style_center), None,
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

        row_domaine = [Paragraph(f"<font color='black'><b>{domaine_nom}</b></font>", style_center)]
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
                    row.append(Paragraph(str(ponderation), style_center))

                elif col in [4, 11]:
                    exam_val = exam if exam != "-" else "0"
                    row.append(Paragraph(str(exam_val), style_center))
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
                    row.append(Paragraph(display_tot_sem, style_center))

                elif col == 13: 
                    # Max TOT.SEM = Max TJ (ponderation) + Max Exam
                    pond_val = float(ponderation) if ponderation != "-" else 0.0
                    val_tot_sem_t2 = pond_val + float(val_exam_t2)
                    display_tot_sem = str(int(val_tot_sem_t2)) if val_tot_sem_t2 == int(val_tot_sem_t2) else str(val_tot_sem_t2)
                    row.append(Paragraph(display_tot_sem, style_center))

                elif col == 7:  
                    tot_s1 = 0.0
                    try:
                        tot_s1 += float(row[2].text or 0) if len(row) > 2 and row[2] else 0.0
                        tot_s1 += float(row[3].text or 0) if len(row) > 3 and row[3] else 0.0
                        tot_s1 += float(row[5].text or 0) if len(row) > 5 and row[5] else 0.0
                    except:
                        tot_s1 = 0.0
                    row.append(Paragraph(str(round(tot_s1, 2)), style_center))

                elif col == 14: 
                    tot_s2 = 0.0
                    try:
                        tot_s2 += float(row[9].text or 0) if len(row) > 9 and row[9] else 0.0
                        tot_s2 += float(row[10].text or 0) if len(row) > 10 and row[10] else 0.0
                        tot_s2 += float(row[12].text or 0) if len(row) > 12 and row[12] else 0.0
                    except:
                        tot_s2 = 0.0
                    row.append(Paragraph(str(round(tot_s2, 2)), style_center))

                elif col == 15:
                    # TOTAL GENERAL col 15 = Max Total (TOT.SEM Max S1 + TOT.SEM Max S2)
                    try:
                        tot_max = float(row[6].text or 0) + float(row[13].text or 0)
                    except:
                        tot_max = 0.0
                    row.append(Paragraph(str(round(tot_max, 2)), style_center))

                elif col == 16:
                    # TOTAL GENERAL col 16 = Total Obtenu (TOT S1 + TOT S2)
                    try:
                        tot_gen = float(row[7].text or 0) + float(row[14].text or 0)
                    except:
                        tot_gen = 0.0
                    row.append(Paragraph(str(round(tot_gen, 2)), style_center))

                elif col in [17, 18, 19]:
                    row.append(None)

                else:
                    row.append(Paragraph("-", style_center))

            table_data.append(row)


        row_sous_total = [Paragraph("<b>Sous Total</b>", style_normal)] + [None] * 19
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
        if texte == "APPLICATION":
            table_data.append([Paragraph(f"<b>{texte}</b>", style_normal)] + [None] * 19)
        else:
            table_data.append([Paragraph(f"<b>{texte}</b>", style_normal)] + [None] * 19)
    calculer_sous_totaux_et_maxima_secondaire(table_data, style_center)
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
    col_widths = [30*mm] + [8.22*mm] * 17 + [10*mm] + [20*mm]
    table = Table(table_data, colWidths=col_widths, rowHeights=[4*mm] * len(table_data))

    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.5),
        ('SPAN', (0, 0), (0, 2)),
        ('SPAN', (1, 0), (7, 0)),
        ('SPAN', (2, 1), (3, 1)),
        ('SPAN', (4, 1), (5, 2)),
        ('SPAN', (6, 1), (7, 2)),
        ('SPAN', (8, 0), (14, 0)),
        ('SPAN', (9, 1), (10, 1)),
        ('SPAN', (11, 1), (12, 2)),
        ('SPAN', (13, 1), (14, 2)),
        ('SPAN', (15, 0), (16, 2)),   
        ('SPAN', (17, 0), (17, 2)), 
        ('SPAN', (18, 0), (19, 1)),   
    ])

    num_rows = len(table_data)

    # Appliquer SPAN/BACKGROUND dynamiquement pour les lignes de domaine
    for row_idx in range(3, num_rows):
        row = table_data[row_idx]
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            if "<b>" in texte and "Sous Total" not in texte and "MAXIMA" not in texte and "POURCENTAGE" not in texte and "PLACE" not in texte and "CONDUITE" not in texte and "APPLICATION" not in texte and "SIGNATURE" not in texte:
                table_style.add('SPAN', (0, row_idx), (-1, row_idx))
                table_style.add('BACKGROUND', (0, row_idx), (-1, row_idx), colors.lightblue)

    # Colonne hachurée (col 17) — lignes continues au lieu de background noir
    col_hachuree = 17 
    for row_idx in range(3, num_rows):
        if col_hachuree < len(table_data[row_idx]):
            table_data[row_idx][col_hachuree] = None
    # Fusionner verticalement + bordures épaisses pour marquer la séparation
    if num_rows > 3:
        table_style.add('SPAN', (col_hachuree, 3), (col_hachuree, num_rows - 1))
        table_style.add('LINEAFTER', (col_hachuree - 1, 3), (col_hachuree - 1, num_rows - 1), 0.5, colors.black)
        table_style.add('LINEAFTER', (col_hachuree, 3), (col_hachuree, num_rows - 1), 0.5, colors.black)
            
    # Lignes finales (MAXIMA, POURCENTAGE, etc.) — fusionner les colonnes non-utilisées avec bordures
    maxima_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph) and "MAXIMA GENEREAUX" in (row[0].text or ""):
            maxima_idx = idx
            break

    if maxima_idx is not None:
        colonnes_struct = [1, 4, 6, 8, 11, 13]
        for row_idx in range(maxima_idx, min(maxima_idx + 4, num_rows)):
            for col_idx in colonnes_struct:
                if col_idx < len(table_data[row_idx]):
                    table_data[row_idx][col_idx] = None
                    table_style.add('LINEAFTER', (col_idx - 1, row_idx), (col_idx - 1, row_idx), 0.5, colors.black)
                    table_style.add('LINEAFTER', (col_idx, row_idx), (col_idx, row_idx), 0.5, colors.black)

        colonnes_struct_2 = [5, 7, 12, 14]
        for row_idx in range(maxima_idx + 2, min(maxima_idx + 4, num_rows)):
            for col_idx in colonnes_struct_2:
                if row_idx < num_rows and col_idx < len(table_data[row_idx]):
                    table_data[row_idx][col_idx] = None
                    table_style.add('LINEAFTER', (col_idx - 1, row_idx), (col_idx - 1, row_idx), 0.5, colors.black)
                    table_style.add('LINEAFTER', (col_idx, row_idx), (col_idx, row_idx), 0.5, colors.black)

    # Zone signature en bas à droite
    signature_start = num_rows - 6 if num_rows > 6 else num_rows - 1
    signature_end = num_rows - 1
    if signature_start >= 0 and signature_end < num_rows and signature_start < signature_end:
        table_style.add('SPAN', (18, signature_start), (19, signature_end))
        table_style.add('BOX', (18, signature_start), (19, signature_end), 0.5, colors.black)

    texte_visible = (
        "Passe(1)<br/>"
        "Double(1)<br/>"
        "A echoué(1)<br/>"
        "<br/>"  
        "Le chef de l'Etablissement,<br/>"
        "sceau ecole."
    )

    style_visible = ParagraphStyle(
        name='TexteVisible',
        parent=style_center,
        fontSize=10,
        leading=16,         
        alignment=1,       
        textColor=colors.black,
        spaceBefore=8,
        spaceAfter=8
    )
    if signature_start < len(table_data) and 18 < len(table_data[signature_start]):
        table_data[signature_start][18] = Paragraph(texte_visible, style_visible)
    
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 0.5*mm))
   
   
def create_footer__secondaire_rdc(elements, style_normal, style_center, classe_id):
    """Footer matching official RDC bulletin format — used by secondaire and cycle supérieur."""
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
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
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

def draw_border__secondaire_rdc(canvas, doc, eleve, margin):
    canvas.setLineWidth(0.5)
    canvas.rect(margin, margin, A4[0] - 2 * margin, A4[1] - 2 * margin)
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
        textColor=colors.red,        
        spaceBefore=0,
        spaceAfter=0
    )

    places_injectees = 0

    for col in colonnes_avec_places:
        place = get_place_secondaire(
            id_annee, id_campus, id_cycle, id_classe,
            id_eleve, id_semestre, col, semestres_data=semestres_data
        )

        ligne_place[col] = Paragraph(place, place_style)

        if place != "-":
            places_injectees += 1

    return places_injectees > 0

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
        return res.place.strip() if res and res.place and res.place.strip() else "-"

    # Colonnes examen (sem1=col5, sem2=col12)
    if col in [5, 12]:
        sem_code = "S1" if col == 5 else "S2"
        config_id = code_to_config.get(sem_code)
        if not config_id:
            return "-"
        filtre = {**filtre_base, "id_trimestre_id": config_id}
        res = Deliberation_examen_resultat.objects.filter(**filtre).first()
        return res.place.strip() if res and res.place and res.place.strip() else "-"

    # Colonnes total semestre (sem1=col7, sem2=col14)
    if col in [7, 14]:
        sem_code = "S1" if col == 7 else "S2"
        config_id = code_to_config.get(sem_code)
        if not config_id:
            return "-"
        filtre = {**filtre_base, "id_trimestre_id": config_id}
        res = Deliberation_trimistrielle_resultat.objects.filter(**filtre).first()
        return res.place.strip() if res and res.place and res.place.strip() else "-"

    # Col 16 = TOTAL GENERAL (deliberation annuelle)
    if col == 16:
        res = Deliberation_annuelle_resultat.objects.filter(**filtre_base).first()
        return res.place.strip() if res and res.place and res.place.strip() else "-"

    return "-"


