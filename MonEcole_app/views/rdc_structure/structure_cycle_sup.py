
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import mm
from django.http import HttpResponse
import os
from MonEcole_app.models import Eleve,Institution,Annee_trimestre,Cours_par_classe,Deliberation_examen_resultat,Deliberation_periodique_resultat,Deliberation_trimistrielle_resultat
from .structure_primaire import (get_student_exam_notes,
                                 get_student_period_notes,style_normal
                                 )

from .structure_secondaire import get_semestres
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from MonEcole_app.views.rdc_structure.structure_secondaire import (check_image_paths,
                                                      create_bulletin_title__secondaire_rdc,
                                                      create_header,create_line2_left,
                                                      create_footer__secondaire_rdc,create_nid_section,
                                                      create_line2_section__secondaire_rdc,
                                                      create_line2_right__secondaire_rdc,draw_border__secondaire_rdc,get_styles)


def to_int_clean(value):
    if value is None:
        return 0
    return int(Decimal(value).quantize(0, rounding=ROUND_HALF_UP))


def regrouper_cours_par_tp_tpe(cours):
    groupes = defaultdict(list)
    for c in cours:
        cle = (c["tp"], c["tpe"])
        groupes[cle].append(c["nom"])

    return dict(groupes)




def recuperer_cours_obligatoires(id_annee, id_campus, id_cycle, id_classe):
    """
    Récupère les cours obligatoires d'une classe.
    id_classe = EAC ID → résolu en Hub classe_id via Cours.
    """
    from MonEcole_app.models.country_structure import EtablissementAnneeClasse
    from MonEcole_app.models.enseignmnts.matiere import Cours

    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
        hub_classe_id = eac.classe_id
    except EtablissementAnneeClasse.DoesNotExist:
        return []

    # Hub: Cours liés à cette classe
    cours_ids = list(Cours.objects.filter(classe_id=hub_classe_id).values_list('id_cours', flat=True))
    if not cours_ids:
        return []

    qs = Cours_par_classe.objects.filter(
        id_cours_id__in=cours_ids,
        id_annee_id=id_annee,
        is_obligatory=True
    ).select_related('id_cours')

    cours = []
    for c in qs:
        cours.append({
            "nom": c.id_cours.cours,   
            "tp": c.maxima_tj,
            "tpe": c.maxima_periode,
        })

    return cours



def construire_liste_cours_ordonnee(groupes):
    cours_ordonnes = []

    for (tp, tpe), cours_list in groupes.items():
        cours_ordonnes.append("Maxima")

        for c in cours_list:
            cours_ordonnes.append(c.cours)  

    return cours_ordonnes



def ajouter_cours_groupes_dans_table(
    table_data,
    groupes_cours,
    notes_periodes,
    notes_exam,
    trimestres_data,
    style_normal,
    style_center,
    id_annee, id_campus, id_cycle, id_classe, 
    start_row=4,
    max_row=34
):
    style_maxima = ParagraphStyle(
        name="MaximaStyle",
        parent=style_normal,
        fontName="Helvetica-Bold",
        textColor=colors.black
    )

    current_row = start_row

    for (note1, note2), cours_du_groupe in groupes_cours.items():
        if current_row >= max_row:
            break

        n1 = note1 or 0
        n2 = note2 or 0

        somme_notes    = n1 + n2
        double_somme   = somme_notes * 2
        total_col9     = double_somme + double_somme  

        maxima_row = [
            Paragraph("MAXIMA", style_maxima),        
            Paragraph(str(n1), style_center),           
            Paragraph(str(n2), style_center),           
            Paragraph(str(somme_notes), style_center),  
            Paragraph(str(double_somme), style_center), 
            Paragraph(str(n1), style_center),           
            Paragraph(str(n2), style_center),           
            Paragraph(str(somme_notes), style_center),  
            Paragraph(str(double_somme), style_center), 
            Paragraph(str(total_col9), style_center),   
        ]

        maxima_row += [None] * (13 - len(maxima_row))
        table_data.append(maxima_row)
        current_row += 1

        for nom_cours in cours_du_groupe:
            if current_row >= max_row:
                break

            cpc = Cours_par_classe.objects.filter(
                id_cours__cours=nom_cours.strip(),
                id_annee_id=id_annee,
                is_obligatory=True
            ).first()

            if not cpc:
                row = [Paragraph(nom_cours, style_normal)] + [Paragraph("-", style_center) for _ in range(12)]
                table_data.append(row)
                current_row += 1
                continue

            id_cpc = cpc.id_cours_id
            notes_periode = notes_periodes.get(id_cpc, {})
            notes_ex     = notes_exam.get(id_cpc, {})
            p1      = notes_periode.get("1e P", "-")
            p2      = notes_periode.get("2e P", "-")
            exam_s1 = notes_ex.get(trimestres_data[0][0], "-") if trimestres_data and len(trimestres_data) > 0 else "-"
            p3      = notes_periode.get("3e P", "-")
            p4      = notes_periode.get("4e P", "-")
            exam_s2 = notes_ex.get(trimestres_data[1][0], "-") if trimestres_data and len(trimestres_data) > 1 else "-"

            def to_float(val):
                if val in (None, "", "-"):
                    return 0.0
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return 0.0

            somme_semestre1 = to_float(p1) + to_float(p2) + to_float(exam_s1)
            somme_semestre2 = to_float(p3) + to_float(p4) + to_float(exam_s2)

            row = [Paragraph(nom_cours, style_normal)]

            row.extend([
                Paragraph(str(p1),               style_center), 
                Paragraph(str(p2),               style_center), 
                Paragraph(str(exam_s1),          style_center),  
                Paragraph(str(round(somme_semestre1, 2)), style_center), 
                Paragraph(str(p3),               style_center),  
                Paragraph(str(p4),               style_center),  
                Paragraph(str(exam_s2),          style_center), 
                Paragraph(str(round(somme_semestre2, 2)), style_center),  
                None,                                           
            ])

            while len(row) < 13:
                row.append(None)

            table_data.append(row)
            current_row += 1

    while current_row < max_row:
        table_data.append([None] * 13)
        current_row += 1



def create_bulletin_title__secondaire_superieur(elements, style_title, style_right):
    elements.append(Spacer(1, 2*mm))
    title_data = [
        [Paragraph("<font color='black'><b>BULLETIN DE : 4ème CONSTRUCTRION</b></font>", style_title),
         Paragraph("<font color='black'><b>|ANNEE SCOLAIRE : 2025-2026</b></font>", style_right)]
    ]
    title_table = Table(title_data, colWidths=[100*mm, 100*mm])
    title_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(title_table)
    elements.append(Spacer(1, 2*mm))  
    

def create_notes_table_superieur(elements, style_center, style_normal,id_annee, id_campus, id_cycle, id_classe, id_eleve):

    table_data = []

    # =======================
    # SEMESTRES
    # =======================
    trimestres_data = get_semestres(id_annee, id_campus, id_cycle, id_classe)
    if trimestres_data and len(trimestres_data) == 2:
        nom_trim1 = trimestres_data[0][1]
        nom_trim2 = trimestres_data[1][1]

        if nom_trim1 == "Semestre 1" or nom_trim1 == "Trimestre 1":
            nom_trim1 = "PREMIER SEMESTRE"
        if nom_trim2 == "Semestre 2" or nom_trim2 == "Trimestre 2":
            nom_trim2 = "SECOND SEMESTRE"
    else:
        nom_trim1 = "PREMIER SEMESTRE"
        nom_trim2 = "SECOND SEMESTRE"

    # =======================
    # EN-TÊTES
    # =======================
    table_data.append([
        Paragraph("<b>BRANCHES</b>", style_center),
        Paragraph(f"<b>{nom_trim1}</b>", style_center), None, None, None,
        Paragraph(f"<b>{nom_trim2}</b>", style_center), None, None, None,
        Paragraph("<b>TOTAL GENERAL</b>", style_center), None,
        Paragraph("<b>EXAMEN D'ETAT</b>", style_center),
        Paragraph("<b>EXAMEN DE REPECHAGE</b>", style_center)
    ])

    table_data.append([
        None,
        Paragraph("TRAV. JOUR", style_center), None,
        Paragraph("EXAM", style_center),
        Paragraph("TOT.", style_center),
        Paragraph("TRAV. JOUR", style_center), None,
        Paragraph("EXAM", style_center),
        Paragraph("TOT.", style_center),
        Paragraph("T.G", style_center),
        Paragraph("", style_center),
        Paragraph("", style_center),
        Paragraph("Points Obtenus", style_center),
      
    ])

    table_data.append([
        Paragraph("BRANCHES", style_center),
        Paragraph("1e P", style_center), Paragraph("2e P", style_center),
        Paragraph("EXAM", style_center), Paragraph("TOT.SEM", style_center),
        Paragraph("3e P", style_center), Paragraph("4e P", style_center),
        Paragraph("EXAM", style_center), Paragraph("TOT.SEM", style_center),
        Paragraph("", style_center),
        Paragraph("", style_center),
        Paragraph("M.EC", style_center)
    ])
    id_semestre_actif = None
    for s in trimestres_data:
        try:
            sem_obj = Annee_trimestre.objects.get(id=s[0]) 
            if not sem_obj.isOpen:       
                id_semestre_actif = s[0]
                break
        except:
            pass

    if not id_semestre_actif and trimestres_data:
        id_semestre_actif = trimestres_data[0][0]  


    # =======================
    # COURS
    # =======================
    cours = recuperer_cours_obligatoires(
        id_annee, id_campus, id_cycle, id_classe
    )

    groupes = regrouper_cours_par_tp_tpe(cours)
    notes_periodes = get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    notes_exam = get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    ajouter_cours_groupes_dans_table(
        table_data,
        groupes,
        notes_periodes,
        notes_exam,
        trimestres_data,
        style_normal,
        style_center,
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe,
        start_row=4,
        max_row=34
    )
    
    
    # ============================
    # CALCUL DES MAXIMA GENERAUX
    # ============================
    maxima_generaux = {i: 0 for i in range(1, 10)}
    for (tp1, tp2), cours_du_groupe in groupes.items():
        nb_cours = len(cours_du_groupe)
        somme = tp1 + tp2
        double_somme = somme * 2

        maxima_generaux[1] += tp1 * nb_cours
        maxima_generaux[2] += tp2 * nb_cours
        maxima_generaux[3] += somme * nb_cours
        maxima_generaux[4] += double_somme * nb_cours

        maxima_generaux[5] += tp1 * nb_cours
        maxima_generaux[6] += tp2 * nb_cours
        maxima_generaux[7] += somme * nb_cours
        maxima_generaux[8] += double_somme * nb_cours

        maxima_generaux[9] += (double_somme + double_somme) * nb_cours

    # =======================
    # CALCUL DES TOTAUX DES COURS
   
    totaux_colonnes = {i: 0 for i in range(1, 10)}

    for row in table_data:
        if row[0] is not None and isinstance(row[0], Paragraph):
            texte_premiere_col = row[0].text.strip()
            if "MAXIMA" in texte_premiere_col:
                continue  
            for col in range(1, 10):
                if col < len(row):
                    cell = row[col]
                    if isinstance(cell, Paragraph):
                        try:
                            value = float(cell.text.replace(",", "."))
                            totaux_colonnes[col] += value
                        except:
                            pass


    # =======================
    # AJOUT DES LIGNES FINALES
    # =======================
    lignes_finales = [
        "MAXIMA GENEREAUX",
        "TOTAUX",
        "POURCENTAGE",
        "PLACE/NBRE D'ELEVES",
        "APPLICATION",
        "CONDUITE",
        "SIGNATURE DU RESPONSABLE"
    ]

    for texte in lignes_finales:
        if texte == "MAXIMA GENEREAUX":
            row = [Paragraph(f"<b>{texte}</b>", style_normal)]
            for col in range(1, 10):
                row.append(Paragraph(str(maxima_generaux[col]), style_center))
            row += [None] * (13 - len(row))
            table_data.append(row)


        elif texte == "TOTAUX":
          
            row = [Paragraph(f"<b>{texte}</b>", style_normal)]

            for col in range(1, 10):
                valeur = Decimal(str(totaux_colonnes[col])).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                row.append(Paragraph(f"{valeur}", style_center))

            row += [None] * (13 - len(row))
            table_data.append(row)

        else:
            table_data.append([Paragraph(f"<b>{texte}</b>", style_normal)] + [None] * 12)
    
    index_pourcentage = 35
    row_pourcentage = table_data[index_pourcentage]
    
    for col in range(1, 10):
        total = totaux_colonnes[col]
        maxima = maxima_generaux[col] or 1  
        pourcentage = (total * 100 / maxima)
        row_pourcentage[col] = Paragraph(f"{pourcentage:.2f}%", style_center)
    table_data[index_pourcentage] = row_pourcentage


    # =======================
    # TABLE & STYLE
    # =======================
    margin = 15 * mm
    largeur_interieure = A4[0] - 0.7 * margin
    branche_width = 42 * mm
    largeur_autre_col = (largeur_interieure - branche_width) / 12
    injecter_places_secondaire_superieur(
        table_data,
        id_annee, id_campus,
        id_cycle, id_classe,
        id_eleve, id_semestre_actif)

    col_widths = [branche_width] + [largeur_autre_col] * 12
    table = Table(table_data, colWidths=col_widths, rowHeights=[4 * mm] * len(table_data))

    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.3, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),

        ('SPAN', (0, 0), (0, 2)),
        ('SPAN', (1, 0), (4, 0)),
        ('SPAN', (5, 0), (9, 0)),
        ('SPAN', (10, 0), (10, 2)),
        ('SPAN', (11, 0), (12, 0)),

        ('SPAN', (1, 1), (2, 1)),
        ('SPAN', (3, 1), (3, 2)),
        ('SPAN', (4, 1), (4, 2)),
        ('SPAN', (5, 1), (6, 1)),
        ('SPAN', (7, 1), (7, 2)),
        ('SPAN', (8, 1), (8, 2)),
        ('SPAN', (9, 1), (9, 2)),
    ])

    # =================
    # COLONNE HACHURÉE
    # ================
    gris_fonce = colors.Color(0.15, 0.15, 0.15)
    col_hachuree = 10
   
    for r in range(len(table_data)-1):
        table_style.add('BACKGROUND', (col_hachuree, r), (col_hachuree, r), gris_fonce)
        table_data[r][col_hachuree] = None
    cases_a_hachurer = [
        (29, 3), (30, 3),
        (29, 7), (30, 7),
        # (36, 3), (36, 4),
        (37, 3), (37, 4),
       (36, 8),
        (36, 9), (37, 7),
        (37, 8), (37, 9),
    ]
    for row, col in cases_a_hachurer:
        if row < len(table_data) and col < len(table_data[0]):
            table_style.add(
                'BACKGROUND',
                (col, row),
                (col, row),
                gris_fonce
            )
            table_data[row][col] = None

    # =======================
    # ZONE TEXTE OFFICIEL
    # =======================
    texte_officiel = """
    Pour le contrôle, le ...................<br/>
    Nom et signature du chef center,.....................<br/>
    ....................<br/>
    Code [][][][][][][][][][][]<br/>
    Résultat final<br/>
    Diplôme (1) Avec .........%<br/>
    A échoué (1)<br/>
    Pour témoignage Le ..../...../......<br/>
    Le chef de l'établissement<br/>
    Sceau de l'école :
    """

    start_row, end_row = 4, 37
    start_col, end_col = 11, len(table_data[0]) - 1

    for r in range(start_row, end_row + 1):
        for c in range(start_col, end_col + 1):
            table_data[r][c] = None

    table_data[start_row][start_col] = Paragraph(texte_officiel, style_normal)

    table_style.add('SPAN', (start_col, start_row), (end_col, end_row))
    table_style.add('VALIGN', (start_col, start_row), (end_col, end_row), 'TOP')
    table_style.add('LEFTPADDING', (start_col, start_row), (end_col, end_row), 6)
    table_style.add('TOPPADDING', (start_col, start_row), (end_col, end_row), 6)
    # =======================
    # FINAL
    # =======================
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 0.5 * mm))




def get_place_secondaire_superieur(
    id_annee, id_campus, id_cycle,
    id_classe, id_eleve, id_semestre, col
):
    from MonEcole_app.models.country_structure import EtablissementAnneeClasse
    try:
        eac = EtablissementAnneeClasse.objects.get(id=id_classe)
        bk_classe_id = eac.classe_id
        bk_groupe = eac.groupe
        bk_section_id = eac.section_id
    except EtablissementAnneeClasse.DoesNotExist:
        return "-"

    semestres_data = get_semestres(id_annee, id_campus, id_cycle, id_classe)
    if not semestres_data or len(semestres_data) < 2:
        return "-"
    semestre1 = semestres_data[0][0]
    semestre2 = semestres_data[1][0]
    filtre_base = {
        "id_annee_id": id_annee,
        "idCampus_id": id_campus,
        "id_cycle_id": id_cycle,
        "classe_id": bk_classe_id,
        "groupe": bk_groupe,
        "section_id": bk_section_id,
        "id_eleve_id": id_eleve,
        "id_trimestre_id": id_semestre,
    }

    # ==============================
    # 1er semestre
    # ==============================
    if id_semestre == semestre1:

        # 1e P et 2e P
        if col in [1, 2]:
            sigles = {1: "1e P", 2: "2e P"}
            filtre = {
                **filtre_base,
                "id_periode__repartition__nom": sigles[col]
            }

            res = Deliberation_periodique_resultat.objects.filter(**filtre).first()
            return res.place.strip() if res and res.place else "-"
        if col == 3:
            res = Deliberation_examen_resultat.objects.filter(**filtre_base).first()
            return res.place.strip() if res and res.place else "-"

        if col == 4:
            res = Deliberation_trimistrielle_resultat.objects.filter(**filtre_base).first()
            return res.place.strip() if res and res.place else "-"

    # ==============================
    # 2ème semestre
    # ==============================
    if id_semestre == semestre2:

        # 3e P et 4e P
        if col in [5, 6]:
            sigles = {5: "3e P", 6: "4e P"}
            filtre = {
                **filtre_base,
                "id_periode__repartition__nom": sigles[col]
            }

            res = Deliberation_periodique_resultat.objects.filter(**filtre).first()
            return res.place.strip() if res and res.place else "-"

        # Examen 2e semestre
        if col == 7:
            res = Deliberation_examen_resultat.objects.filter(**filtre_base).first()
            return res.place.strip() if res and res.place else "-"

    return "-"

def injecter_places_secondaire_superieur(
    table_data,
    id_annee, id_campus, id_cycle,
    id_classe, id_eleve, id_semestre
):

    LIGNE_CIBLE_INDEX = 36

    if len(table_data) <= LIGNE_CIBLE_INDEX:
        return False

    ligne = table_data[LIGNE_CIBLE_INDEX]

    while len(ligne) < 8:
        ligne.append(None)

    colonnes_avec_places = [1, 2, 3, 4, 5, 6, 7]

    place_style = ParagraphStyle(
        name='PlaceStyleSecondaireSuperieur',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=6,
        leading=7,
        alignment=1,
        textColor=colors.red,
        spaceBefore=0,
        spaceAfter=0
    )

    places_injectees = 0

    for col in colonnes_avec_places:

        place = get_place_secondaire_superieur(
            id_annee, id_campus, id_cycle,
            id_classe, id_eleve, id_semestre, col
        )

        ligne[col] = Paragraph(place, place_style)

        if place != "-":
            places_injectees += 1

    return places_injectees > 0

