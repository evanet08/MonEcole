from MonEcole_app.views.rdc_structure.structure_cycle_sup import(get_styles,
                                                                 create_header,create_line2_left,
                                                                 create_line2_right__secondaire_rdc,
                                                                 create_nid_section,Eleve,SimpleDocTemplate,
                                                                 HttpResponse,Institution,check_image_paths,
                                                                 create_line2_section__secondaire_rdc,
                                                                 draw_border__secondaire_rdc,
                                                                 create_bulletin_title__secondaire_superieur)
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle
from MonEcole_app.models import(Cours_par_classe)
from MonEcole_app.models.eleves.eleve import Eleve_note
from collections import defaultdict


styles = getSampleStyleSheet()
style_center = styles['Normal']  
style_normal = styles['Normal']  
style_center.alignment = 1
style_normal.alignment = 0
style_normal.fontSize = 7.5
style_center.fontSize = 7.5



def create_bulletin_content_cycle_superieur(elements, style_normal, style_center,
                                            annee_id, campus_id, cycle_id, classe_id):
    table_data = [[None] * 11 for _ in range(35)]

    # Entête fixe (inchangé)
    table_data[0][0] = Paragraph("<b>BRANCHES</b>", style_center)
    table_data[0][1] = Paragraph("<b>PREMIER SEMESTRE</b>", style_center)
    table_data[0][5] = Paragraph("<b>BRANCHES</b>", style_center)
    table_data[0][6] = Paragraph("<b>SECOND SEMESTRE</b>", style_center)
    table_data[0][9] = Paragraph("<b>TOTAL GENERAL</b>", style_center)
    table_data[0][10] = Paragraph("<b>EXAMEN DE REPÊCHAGE</b>", style_center)

    table_data[1][1] = Paragraph("<b>TRAV. JOUR</b>", style_center)
    table_data[1][3] = Paragraph("<b>EXAM</b>", style_center)
    table_data[1][4] = Paragraph("<b>TOT. SEM</b>", style_center)

    table_data[1][6] = Paragraph("<b>TRAV. JOUR</b>", style_center)
    table_data[1][8] = Paragraph("<b>EXAM</b>", style_center)
    table_data[1][9] = Paragraph("<b>TOT. SEM</b>", style_center)

    petit_style = ParagraphStyle(name='PetitCentre', parent=style_center, fontSize=6.5, leading=7.2, alignment=1)

    table_data[2][1] = Paragraph("1re P", petit_style)
    table_data[2][2] = Paragraph("2e P", petit_style)
    table_data[2][6] = Paragraph("3e P", petit_style)
    table_data[2][7] = Paragraph("4e P", petit_style)

    branche_style = ParagraphStyle(
        name='BrancheStyle',
        parent=style_normal,
        fontSize=4,
        leading=5.2,
        alignment=0,
        leftIndent=2,
        rightIndent=2,
        spaceBefore=0,
        spaceAfter=0
    )

    # Résolution EAC → business keys
    from MonEcole_app.models.country_structure import EtablissementAnneeClasse
    from MonEcole_app.models.enseignmnts.matiere import Cours

    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=classe_id)
        hub_classe_id = eac.classe_id
    except EtablissementAnneeClasse.DoesNotExist:
        return elements

    cours_ids = list(Cours.objects.filter(classe_id=hub_classe_id).values_list('id_cours', flat=True))

    cours_qs = Cours_par_classe.objects.filter(
        id_cours_id__in=cours_ids,
        id_annee_id=annee_id,
    ).select_related('id_cours').order_by('ordre_cours')

    # Tous les cours (pour colonne 0)
    tous_cours = list(cours_qs)

    # Seulement second semestre (pour colonne 5)
    second_sem_cours = [c for c in tous_cours if c.is_second_semester]


    def remplir_colonne(cours_list, col_branche, col_1p, col_2p, start_row=3):
        if not cours_list:
            return start_row

        row = start_row
        compteur = 1

        for r in range(start_row, 35):
            table_data[r][col_branche] = None
            if col_1p is not None:
                table_data[r][col_1p] = None
            if col_2p is not None:
                table_data[r][col_2p] = None

        # Groupement par (TP, TPE)
        groupes = defaultdict(list)
        for cpc in cours_list:
            key = (cpc.TP or 0, cpc.TPE or 0)  
            groupes[key].append(cpc)

        # Tri des groupes par ordre d'apparition du premier cours
        ordered_keys = sorted(
            groupes.keys(),
            key=lambda k: min(c.ordre_cours or 999 for c in groupes[k])
        )

        for tp_val, tpe_val in ordered_keys:
            cours_du_groupe = groupes[(tp_val, tpe_val)]

            # Ligne Maxima – 
            if row < 35:
                table_data[row][col_branche] = Paragraph("<b>MAXIMA</b>", branche_style)

                if tpe_val and tpe_val != 0:
                    table_data[row][col_1p] = Paragraph(str(tpe_val), style_center)
                if tp_val and tp_val != 0:
                    table_data[row][col_2p] = Paragraph(str(tp_val), style_center)

                row += 1

            # Cours du groupe – 
            for cpc in cours_du_groupe:
                if row >= 28: 
                    break
                nom = cpc.id_cours.cours.strip()
                table_data[row][col_branche] = Paragraph(f"{compteur}. {nom}", branche_style)
                compteur += 1
                row += 1

        return row

    # Colonne gauche : TOUS les cours
    remplir_colonne(tous_cours, 0, 1, 2)
    remplir_colonne(second_sem_cours, 5, 6, 7)

    lignes_finales = [
        "MAXIMA GENEREAUX",
        "TOTAUX",
        "POURCENTAGE",
        "PLACE/NBRE D'ELEVES",
        "APPLICATION",
        "CONDUITE",
        "SIGNATURE DU RESPONSABLE"
    ]

    start_finales = 28
    for idx, texte in enumerate(lignes_finales):
        row = start_finales + idx
        if row < 35:
            table_data[row][0] = Paragraph(f"<b>{texte}</b>", style_normal)

    # Largeurs et tableau 
    margin_lr = 7 * mm
    usable_width = A4[0] - 2 * margin_lr
    branche_width = 30 * mm
    remaining_width = usable_width - (branche_width * 2)
    other_width = remaining_width / 9

    col_widths = [branche_width] + [other_width] * 4 + [branche_width] + [other_width] * 5

    row_height = 5.55 * mm

    table = Table(
        table_data,
        colWidths=col_widths,
        rowHeights=[row_height] * 35,
        splitByRow=1,
        repeatRows=3
    )

    ts = TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,0), (-1,-1), 7.0),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),

        ('BACKGROUND', (0,0), (-1,2), colors.Color(0.96, 0.96, 0.98)),
        ('FONTNAME', (0,0), (-1,2), 'Helvetica-Bold'),

        ('SPAN', (0,0), (0,2)),
        ('SPAN', (5,0), (5,2)),
        ('SPAN', (1,0), (4,0)),
        ('SPAN', (6,0), (9,0)),
        ('SPAN', (10,0), (10,2)),
        ('SPAN', (1,1), (2,1)),
        ('SPAN', (6,1), (7,1)),

        ('SPAN', (3,1), (3,2)),
        ('SPAN', (4,1), (4,2)),
        ('SPAN', (8,1), (8,2)),
        ('SPAN', (9,1), (9,2)),
        ('ALIGN', (3,2), (4,2), 'CENTER'),
        ('ALIGN', (8,2), (9,2), 'CENTER'),
    ])

    table.setStyle(ts)
    elements.append(table)
    elements.append(Spacer(1, 3 * mm))
   
    decision_style = ParagraphStyle(
        name='Decision',
        parent=style_normal,
        fontSize=6.5,         
        leading=7.2,          
        alignment=0,
        spaceBefore=0,
        spaceAfter=0
    )

    right_align_style = ParagraphStyle(
        name='RightAlignDecision',
        parent=decision_style,
        alignment=2,
        spaceBefore=2,
        spaceAfter=2
    )

    chef_style = ParagraphStyle(
        name='ChefStyle',
        parent=right_align_style,
        fontSize=6.8,
        leading=7.5,
        spaceBefore=0,
        spaceAfter=4
    )

    note_style = ParagraphStyle(
        name='NoteStyle',
        parent=decision_style,
        fontSize=6.0,         
        leading=6.8,
        alignment=0,
        spaceBefore=4,         
        spaceAfter=0
    )

    elements.append(Paragraph("""
    1. L'élève ne pourra pas passer dans la classe supérieure s'il(elle) n'a subi accès à un examen de repêchage en : ................................................<br/>
    2. L'élève passe dans la classe supérieure (1)<br/>
    3. L'élève double sa classe (1)<br/>
    4. L'élève a échoué (1)<br/>
    Signature de l'élève ................................................    Sceau de l'école
    """, decision_style))

    elements.append(Paragraph("Fait à ............................ / le ..... / ..... / 20....", right_align_style))
    elements.append(Paragraph("<b>Chef d'Établissement</b>", chef_style))

    elements.append(Paragraph("""
    <i><b>Note importante :</b> le bulletin est sans importance s'il est raturé ou surchargé</i>
    """, note_style))
    return elements


def recuperer_notes_par_classe_cycle_superieur(annee_id, campus_id, cycle_id, classe_id, trimestre_id, cours_classe_id):
    """
    Récupère les notes des élèves pour un cours donné (Cours_par_classe)
    en filtrant par année, campus, cycle, classe et trimestre.
    
    Args:
        annee_id: ID de l'année scolaire
        campus_id: ID du campus
        cycle_id: ID du cycle actif
        classe_id: ID de la classe active
        trimestre_id: ID du trimestre
        cours_classe_id: ID du cours par classe (Cours_par_classe)
    
    Returns:
        QuerySet des notes des élèves pour le cours donné
    """
    notes = Eleve_note.objects.filter(
        id_annee=annee_id,
        id_campus=campus_id,
        id_cycle=cycle_id,
        id_classe=classe_id,
        id_trimestre=trimestre_id,
        id_cours_classe=cours_classe_id
    ).select_related(
        'id_eleve',
        'id_cours_classe',
        'id_cours_classe__id_cours',
        'id_type_note'
    ).order_by('id_eleve__nom', 'id_eleve__prenom')
    
    return notes



def draw_border__secondaire_rdc_without_qrcode (canvas, doc, eleve, margin, watermark_path=None):
    canvas.saveState()
    
    canvas.setLineWidth(0.5) 
    canvas.rect(
        margin,
        margin,
        A4[0] - 2 * margin,
        A4[1] - 2 * margin
    )

    canvas.restoreState()
    
    # Watermark: armoirie du pays en filigrane très faible au centre
    import os
    if watermark_path and os.path.exists(watermark_path):
        canvas.saveState()
        canvas.setFillAlpha(0.06)
        page_w, page_h = A4
        wm_size = 120 * mm
        x = (page_w - wm_size) / 2
        y = (page_h - wm_size) / 2
        canvas.drawImage(watermark_path, x, y, width=wm_size, height=wm_size,
                         preserveAspectRatio=True, mask='auto')
        canvas.restoreState()

def generate_bulletin_superieur_secondLevel_rdc(request, eleve_id=103):
    id_classe = 50
    id_annee=1
    campus_id=3
    id_cycle=16

    try:
        eleve = Eleve.objects.get(id_eleve=eleve_id)
    except Eleve.DoesNotExist:
        return HttpResponse("Élève non trouvé", status=404)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bulletin_{eleve.nom}_{eleve.prenom}.pdf"'

    margin = 5 * mm
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        topMargin=margin,
        bottomMargin=margin,
        leftMargin=margin,
        rightMargin=margin
    )
    elements = []

    styles, style_normal, style_center, style_title, style_right = get_styles()

    institution = Institution.objects.get(id_ecole=3)
    logo_path = institution.logo_ecole.path if institution.logo_ecole else None
    emblem_path = institution.logo_ministere.path if institution.logo_ministere else None

    try:
        check_image_paths(logo_path, emblem_path)
    except ValueError as e:
        return HttpResponse(str(e), status=500)

    elements.append(Spacer(1, 5*mm))
    create_header(elements, logo_path, emblem_path, style_title, style_center)
    create_nid_section(elements, style_normal)
    left_table = create_line2_left(elements, style_normal)
    right_table = create_line2_right__secondaire_rdc(elements, eleve, id_classe, style_normal)
    create_line2_section__secondaire_rdc(elements, left_table, right_table)
    create_bulletin_title__secondaire_superieur(elements, style_title, style_right)
    create_bulletin_content_cycle_superieur(elements, style_normal, style_center,id_annee,campus_id,id_cycle,id_classe)
    doc.build(
        elements,
        onFirstPage=lambda canvas, doc: draw_border__secondaire_rdc_without_qrcode(canvas, doc, eleve, margin)
    )
    return response
