
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from MonEcole_app.views.rdc_structure.structure_cycle_sup import(get_styles,
                                                                 create_header,create_line2_left,
                                                                 create_line2_right__secondaire_rdc,
                                                                 create_nid_section,Eleve,SimpleDocTemplate,
                                                                 HttpResponse,Institution,check_image_paths,
                                                                 create_line2_section__secondaire_rdc,
                                                                 draw_border__secondaire_rdc,Cours_par_classe,
                                                                 create_bulletin_title__secondaire_superieur)

from reportlab.platypus import KeepTogether
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from collections import defaultdict





# ############Ligne non  casse!
# def create_bulletin_maternelle(elements, style_normal, style_center, style_title):
#     table_data = []

#     bold_center = ParagraphStyle('BoldCenter', parent=style_center, fontName='Helvetica-Bold', fontSize=9, alignment=1)
#     small_center = ParagraphStyle('SmallCenter', parent=style_center, fontSize=8, alignment=1)
#     left_bold = ParagraphStyle('LeftBold', parent=style_normal, fontName='Helvetica-Bold', fontSize=10, alignment=0)

#     table_data.append([
#         Paragraph("<b>Groupe</b>", bold_center),
#         Paragraph("<b>Trimestre</b>", bold_center),
#         Paragraph("<b>1e p</b>", bold_center),
#         Paragraph("<b>2e P</b>", bold_center),
#         Paragraph("<b>3e P</b>", bold_center),
#         Paragraph("<b>Total</b>", bold_center),
#         Paragraph("<b>Qual.</b>", bold_center),
#         Paragraph("<b>coul</b>", bold_center),
#     ])

#     table_data.append([
#         Paragraph("<b>GroupeI</b>", left_bold),
#         Paragraph("Maxima", bold_center),
#         Paragraph("30", small_center),
#         Paragraph("30", small_center),
#         Paragraph("30", small_center),
#         None,
#         None,
#         None
#     ])

#     cours_g1 = [
#         "01. Religion", "02. Français", "03. Mathématiques",
#         "04. Sciences", "05. Étude du milieu", "06. Histoire",
#         "07. Géographie", "08. Éducation civique"
#     ]
#     for cours in cours_g1:
#         table_data.append([
#             Paragraph(cours, style_normal),
#             None,
#             None, None, None, None, None, None
#         ])

#     table_data.append([
#         Paragraph("sous-total", left_bold),
#         None, None, None, None,
#         Paragraph("", small_center),
#         None,
#         None
#     ])

#     table_data.append([
#         Paragraph("<b>Groupe II</b>", left_bold),
#         Paragraph("Maxima", bold_center),
#         Paragraph("20", small_center),
#         Paragraph("20", small_center),
#         Paragraph("20", small_center),
#         None,
#         None,
#         None
#     ])

#     cours_g2 = ["09. Éducation physique", "10. Arts plastiques", "11. Musique", "12. Informatique"]
#     for cours in cours_g2:
#         table_data.append([
#             Paragraph(cours, style_normal),
#             None,
#             None, None, None, None, None, None
#         ])

#     table_data.append([
#         Paragraph("sous-total", left_bold),
#         None, None, None, None,
#         Paragraph("", small_center),
#         None,
#         None
#     ])

#     # === SECTION APPRÉCIATION GÉNÉRALE ===
#     table_data.append([
#         Paragraph("<b>Appréciation générale</b>", left_bold),
#         Paragraph("<b>Tot gen.</b>", small_center),
#         None, None, None, None, None, None
#     ])

#     table_data.append([
#         None,
#         Paragraph("<b>Qualité</b>", small_center),
#         None, None, None, None, None, None
#     ])

#     table_data.append([
#         None,
#         Paragraph("<b>Couleur</b>", small_center),
#         None, None, None, None, None, None
#     ])

#     # === PARTIE SIGNATURES ===
#     table_data.append([
#         Paragraph("<b>Signatures</b>", bold_center),  
#         None,
#         None, None, None, None, None, None
#     ])

#     margin = 5 * mm
#     usable_width = A4[0] - 2 * margin
#     col_widths = [65*mm, 22*mm, 22*mm, 22*mm, 35*mm, 30*mm, 30*mm, 30*mm]
#     total_w = sum(col_widths)
#     if total_w > usable_width:
#         ratio = usable_width / total_w
#         col_widths = [w * ratio for w in col_widths]
#     sub_col_widths = [col_widths[0] / 2, col_widths[0] / 2]

#     sub_header_data = [[Paragraph("<b>Trimestre</b>", small_center), Paragraph("<b>Parent</b>", small_center)]]
#     sub_header_table = Table(sub_header_data, colWidths=sub_col_widths, rowHeights=6.2*mm)
#     sub_header_table.setStyle(TableStyle([
        
#         ('LINEBEFORE', (4, 0), (4, -1), 1.5, colors.black),
        
#         ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
#         ('ALIGN', (0,0), (-1,-1), 'CENTER'),
#     ]))
#     table_data.append([
#         sub_header_table,
#         Paragraph("<b>Instituteur</b>", small_center),
#         None, None, None, None, None, None
#     ])

#     def make_trim_row(trim_text):
#         trim_data = [[Paragraph(trim_text, style_normal), None]]
#         trim_table = Table(trim_data, colWidths=sub_col_widths, rowHeights=6.2*mm)
#         trim_table.setStyle(TableStyle([
#             ('LINEBEFORE', (4, 0), (4, -1), 1.5, colors.black),
#             ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
#             ('ALIGN', (0,0), (0,0), 'LEFT'),
#             ('LEFTPADDING', (0,0), (0,0), 6),
#         ]))
#         return trim_table

#     table_data.append([make_trim_row("1e Trim"), None, None, None, None, None, None, None])
#     table_data.append([make_trim_row("2e Trim"), None, None, None, None, None, None, None])
#     table_data.append([make_trim_row("3e Trim"), None, None, None, None, None, None, None])

#     # === 2 LIGNES VIDES APRÈS 3e TRIM ===
#     table_data.append([None] * 8)
#     table_data.append([None] * 8)

#     table_data.append([
#         Paragraph("Légende Qual. : appréciation qualitative", style_normal),
#         None, None, None, None, None, None, None
#     ])

#     table_data.append([
#         Paragraph("Coul. : couleur correspondante", style_normal),
#         None, None, None, None, None, None, None
#     ])

#     table_data.append([None] * 8)

#     table_data.append([
#         Paragraph("Observation : ................................................", style_normal),
#         None, None, None,
#         Paragraph("Fait à ....... le .../.../20..", style_normal),
#         None, None, None
#     ])

#     table_data.append([
#         None, None, None, None,
#         Paragraph("Sceau de l'école .................................... le (la) Directeur(trice)", style_normal),
#         None, None, None
#     ])

#     table_data.append([
#         None, None, None, None,
#         Paragraph("<i><b>Note importante :</b> le bulletin soit sans valeur s'il est raturé ou surchargé</i>", style_normal),
#         None, None, None
#     ])

#     # === 2 LIGNES VIDES À LA FIN ===
#     table_data.append([None] * 8)
#     table_data.append([None] * 8)
    
#     main_table = Table(
#         table_data,
#         colWidths=col_widths,
#         rowHeights=6.2*mm,
#         splitByRow=0,
#         repeatRows=1
#     )

#     main_end_row = 24  

#     ts = TableStyle([
#         ('GRID', (0, 0), (-1, main_end_row), 0.5, colors.black),
#         ('LINEBEFORE', (4, 0), (4, -1), 1.5, colors.black),

#         ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
#         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
#         ('FONTSIZE', (0, 0), (-1, -1), 9),
#         ('LEFTPADDING', (0, 0), (-1, -1), 3),
#         ('RIGHTPADDING', (0, 0), (-1, -1), 3),

#         ('SPAN', (0, 0), (0, 1)),
#         ('SPAN', (0, 2), (1, 2)),
#         ('SPAN', (0, 17), (0, 19)),
#         ('VALIGN', (0, 17), (0, 19), 'MIDDLE'),
#         ('LEFTPADDING', (0, 17), (0, 19), 6),

#         ('SPAN', (0, 3), (1, 3)),
#         ('SPAN', (0, 4), (1, 4)),
#         ('SPAN', (0, 5), (1, 5)),
#         ('SPAN', (0, 6), (1, 6)),
#         ('SPAN', (0, 7), (1, 7)),
#         ('SPAN', (0, 8), (1, 8)),
#         ('SPAN', (0, 9), (1, 9)),
#         ('SPAN', (0, 10), (1, 10)),

#         ('SPAN', (0, 12), (1, 12)),
#         ('SPAN', (0, 13), (1, 13)),
#         ('SPAN', (0, 14), (1, 14)),
#         ('SPAN', (0, 15), (1, 15)),
#         ('SPAN', (0, 16), (1, 16)),

#         ('SPAN', (0, 20), (1, 20)),

#         ('SPAN', (0, 27), (3, 27)),
#         ('SPAN', (0, 28), (3, 28)),
#         ('SPAN', (0, 29), (3, 29)),
#         ('SPAN', (0, 31), (3, 31)),
#         ('SPAN', (4, 31), (7, 31)),
#         ('SPAN', (4, 32), (7, 32)),
#         ('SPAN', (4, 33), (7, 33)),

#         ('ALIGN', (0, 27), (7, -1), 'LEFT'),
#         ('VALIGN', (0, 27), (7, -1), 'TOP'),
#     ])

#     main_table.setStyle(ts)
#     elements.append(KeepTogether(main_table))
#     return elements



def create_bulletin_maternelle(elements, style_normal, style_center, style_title,
                               annee_id, campus_id, cycle_id, classe_id):
   
    table_data = []
    ts_commands = []

    bold_center = ParagraphStyle('BoldCenter', parent=style_center, fontName='Helvetica-Bold', fontSize=9, alignment=1)
    small_center = ParagraphStyle('SmallCenter', parent=style_center, fontSize=8, alignment=1)
    left_bold = ParagraphStyle('LeftBold', parent=style_normal, fontName='Helvetica-Bold', fontSize=10, alignment=0)

  
    table_data.append([
        Paragraph("<b></b>", bold_center),   
        Paragraph("<b>Trimestre</b>", bold_center),
        Paragraph("<b>1er</b>", bold_center),
        Paragraph("<b>2ème</b>", bold_center),
        Paragraph("<b>3ème</b>", bold_center),
        Paragraph("<b>Total</b>", bold_center),
        Paragraph("<b>Qual.</b>", bold_center),
        Paragraph("<b>coul</b>", bold_center),
    ])
    current_row = 1


    # Résolution EAC → business keys pour trouver les cours
    from MonEcole_app.models.country_structure import EtablissementAnneeClasse
    from MonEcole_app.models.enseignmnts.matiere import Cours

    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=classe_id)
        hub_classe_id = eac.classe_id
    except EtablissementAnneeClasse.DoesNotExist:
        return elements

    cours_ids = list(Cours.objects.filter(classe_id=hub_classe_id).values_list('id_cours', flat=True))

    cours_par_classe_qs = Cours_par_classe.objects.filter(
        id_cours_id__in=cours_ids,
        id_annee_id=annee_id,
    ).select_related('id_cours').order_by('ordre_cours')

   
    groupes = defaultdict(list)
    seen_cours_ids = set()

    for cpc in cours_par_classe_qs:
        cours_id = cpc.id_cours.id_cours
        if cours_id in seen_cours_ids:
            continue 
        seen_cours_ids.add(cours_id)

        domaine = (cpc.id_cours.domaine or "Sans groupe").strip()
        groupes[domaine].append(cpc)

 
    def groupe_order(domaine):
        mapping = {'I': 1, 'II': 2, 'III': 3}
        try:
            return mapping[domaine.split()[-1]]
        except (IndexError, KeyError):
            return 99

    ordered_domaines = sorted(groupes.keys(), key=groupe_order)

    for domaine in ordered_domaines:
        groupes[domaine].sort(key=lambda cpc: cpc.ordre_cours or 999)

    compteur_cours = 1

  
    for domaine in ordered_domaines:
        if not groupes[domaine]:
            continue

       
        maxima_periode = groupes[domaine][0].maxima_periode
        max_val = str(maxima_periode) if maxima_periode is not None else ""

        # Ligne "Groupe X" + Maxima
        table_data.append([
            Paragraph(f"<b>{domaine}</b>", left_bold),
            Paragraph("Maxima", bold_center),
            Paragraph(max_val, small_center),
            Paragraph(max_val, small_center),
            Paragraph(max_val, small_center),
            None, None, None
        ])
        current_row += 1

        # Lignes des cours (une seule boucle)
        for cpc in groupes[domaine]:
            table_data.append([
                Paragraph(f"{compteur_cours:02d}. {cpc.id_cours.cours}", style_normal),
                None, None, None, None, None, None, None
            ])
            ts_commands.append(('SPAN', (0, current_row), (1, current_row)))
            current_row += 1
            compteur_cours += 1

        # Sous-total (un seul par groupe)
        table_data.append([
            Paragraph("sous-total", left_bold),
            None, None, None, None,
            Paragraph("", small_center),
            None, None
        ])
        current_row += 1

    row_apprec = current_row
    table_data.append([Paragraph("<b>Appréciation générale</b>", left_bold), Paragraph("<b>Tot gen.</b>", small_center), None, None, None, None, None, None])
    current_row += 1
    table_data.append([None, Paragraph("<b>Qualité</b>", small_center), None, None, None, None, None, None])
    current_row += 1
    table_data.append([None, Paragraph("<b>Couleur</b>", small_center), None, None, None, None, None, None])
    current_row += 1
    ts_commands.extend([
        ('SPAN', (0, row_apprec), (0, row_apprec + 2)),
        ('VALIGN', (0, row_apprec), (0, row_apprec + 2), 'MIDDLE')
    ])

    table_data.append([Paragraph("<b>Signatures</b>", bold_center), None, None, None, None, None, None, None])
    current_row += 1

    margin = 5 * mm
    usable_width = A4[0] - 2 * margin
    col_widths = [65*mm, 22*mm, 22*mm, 22*mm, 35*mm, 30*mm, 30*mm, 30*mm]
    total_w = sum(col_widths)
    if total_w > usable_width:
        ratio = usable_width / total_w
        col_widths = [w * ratio for w in col_widths]
    sub_col_widths = [col_widths[0] / 2, col_widths[0] / 2]

    # Sous-titre Trimestre / Parent
    sub_header_data = [[Paragraph("<b>Trimestre</b>", small_center), Paragraph("<b>Parent</b>", small_center)]]
    sub_header_table = Table(sub_header_data, colWidths=sub_col_widths, rowHeights=6.2*mm)
    sub_header_table.setStyle(TableStyle([
        ('LINEBEFORE', (1,0), (1,0), 0.5, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    table_data.append([sub_header_table, Paragraph("<b>Instituteur</b>", small_center), None, None, None, None, None, None])
    current_row += 1

    # Lignes Trimestres (1e, 2e, 3e)
    def make_trim_row(trim_text):
        trim_data = [[Paragraph(trim_text, style_normal), None]]
        trim_table = Table(trim_data, colWidths=sub_col_widths, rowHeights=6.2*mm)
        trim_table.setStyle(TableStyle([
            ('LINEBEFORE', (1,0), (1,0), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('LEFTPADDING', (0,0), (0,0), 6),
        ]))
        return trim_table

    for trim in ["1er Trimestre", "2ème Trimestre", "3ème Trimistre"]:
        table_data.append([make_trim_row(trim), None, None, None, None, None, None, None])
        current_row += 1

    row_after_trim = current_row

    # Espaces + bas de page
    table_data.extend([[None]*8] * 2)  
    current_row += 2

    row_legende = current_row
    table_data.extend([
        [Paragraph("<b>Légende :</b>", style_normal), None, None, None, None, None, None, None],
        [Paragraph("Qual. : appréciation qualitative", style_normal), None, None, None, None, None, None, None],
        [Paragraph("Coul. : couleur correspondante", style_normal), None, None, None, None, None, None, None],
        [None]*8,
    ])
    current_row += 4

    row_obs = current_row
    table_data.extend([
        [Paragraph("Observation : ................................................", style_normal), None, None, None,
         Paragraph("Fait à ....... le .../.../20..", style_normal), None, None, None],
        [None, None, None, None,
         Paragraph("Sceau de l'école .................................... le (la) Directeur(trice)", style_normal), None, None, None],
    ])
    current_row += 2

    row_note = current_row
    table_data.extend([
        [Paragraph("<i><b>Note importante :</b> le bulletin soit sans valeur s'il est raturé ou surchargé</i>", style_normal),
         None, None, None, None, None, None, None],
        [None]*8,
        [None]*8
    ])

    # STYLES GLOBAUX + DYNAMIQUES
    ts_commands.extend([
        ('GRID', (0, 0), (-1, row_after_trim - 1), 0.5, colors.black),
        ('LINEBEFORE', (4, 0), (4, -1), 1.5, colors.black),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('ALIGN', (0, row_legende), (7, -1), 'LEFT'),
        ('VALIGN', (0, row_legende), (7, -1), 'TOP'),
        ('SPAN', (1, row_legende), (3, row_legende)),
        ('SPAN', (0, row_legende + 1), (3, row_legende + 1)),
        ('SPAN', (0, row_legende + 2), (3, row_legende + 2)),
        ('SPAN', (0, row_obs), (3, row_obs)),
        ('SPAN', (4, row_obs), (7, row_obs)),
        ('SPAN', (4, row_obs + 1), (7, row_obs + 1)),
        ('SPAN', (0, row_note), (7, row_note)),
        ('ALIGN', (0, row_note), (7, row_note), 'CENTER'),
    ])

    # Création du tableau principal
    main_table = Table(
        table_data,
        colWidths=col_widths,
        rowHeights=5.5*mm,          # réduit pour mieux rentrer sur page 1
        splitByRow=1,               # permet le fractionnement si trop long
        repeatRows=1                # répète l'entête sur page 2 si besoin
    )
    main_table.setStyle(TableStyle(ts_commands))

    elements.append(main_table)

    return elements


def draw_border__maternelle_rdc(canvas, doc, eleve, margin=5*mm):
    canvas.setLineWidth(0.5)
    canvas.rect(margin, margin, A4[0] - 2 * margin, A4[1] - 2 * margin)

    col_widths = [65*mm, 22*mm, 22*mm, 22*mm, 35*mm, 30*mm, 30*mm, 30*mm]
    total_w = sum(col_widths)
    usable_width = A4[0] - 2 * margin
    if total_w > usable_width:
        ratio = usable_width / total_w
        col_widths = [w * ratio for w in col_widths]

    x_line = margin + sum(col_widths[:4])

    canvas.setLineWidth(1.5)          # 
    canvas.setStrokeColor(colors.black)
    
    qr_value = f"Généré par Application MonEkole,ce Bulletin est de : {eleve.nom} {eleve.prenom} Conçue par entreprise ICT Group"
    qr_code = QrCodeWidget(qr_value)
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



def generate_bulletin_maternelle_rdc(request, eleve_id=103):
    
    id_annee=1
    id_campus=3
    id_cycle=14
    id_classe=51

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
    create_bulletin_maternelle(elements, style_normal, style_center,style_title,id_annee,id_campus,id_cycle,id_classe)
    doc.build(
        elements,
        onFirstPage=lambda canvas, doc: draw_border__maternelle_rdc(canvas, doc, eleve, margin)
    )
    return response








# # droite prolonge:
# def draw_border__maternelle_rdc(canvas, doc, eleve, margin=5*mm):
#     # Bordure extérieure (déjà présente)
#     canvas.setLineWidth(0.5)
#     canvas.rect(margin, margin, A4[0] - 2 * margin, A4[1] - 2 * margin)

#     # === AJOUT : GROSSE LIGNE VERTICALE DE SÉPARATION ===
#     # Position : après la colonne "2e P" (index 4)
#     # On calcule la position x exacte en utilisant les mêmes col_widths que dans la fonction bulletin
#     col_widths = [65*mm, 22*mm, 22*mm, 22*mm, 35*mm, 30*mm, 30*mm, 30*mm]
#     total_w = sum(col_widths)
#     usable_width = A4[0] - 2 * margin
#     if total_w > usable_width:
#         ratio = usable_width / total_w
#         col_widths = [w * ratio for w in col_widths]

#     # Position x de la ligne = marge gauche + somme des 4 premières colonnes
#     x_line = margin + sum(col_widths[:4])

#     canvas.setLineWidth(1.5)          # épaisseur comme avant
#     canvas.setStrokeColor(colors.black)
#     canvas.line(x_line, margin, x_line, A4[1] - margin)  # descend de haut en bas

#     # QR code (déjà présent)
#     qr_value = f"Généré par Application MonEkole,ce Bulletin est de : {eleve.nom} {eleve.prenom} Conçue par entreprise ICT Group"
#     qr_code = QrCodeWidget(qr_value)
#     bounds = qr_code.getBounds()
#     qr_width = bounds[2] - bounds[0]
#     qr_height = bounds[3] - bounds[1]
#     qr_size = 20*mm
#     d = Drawing(qr_size, qr_size, transform=[qr_size/qr_width, 0, 0, qr_size/qr_height, 0, 0])
#     d.add(qr_code)
#     canvas.saveState()
#     canvas.translate(180*mm, 5*mm)  
#     d.drawOn(canvas, 0, 0)
#     canvas.restoreState()
