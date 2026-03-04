from .__initials import *


class VerticalLineFlowable(Flowable):
    def __init__(self, height, width=8):
        Flowable.__init__(self)
        self.height = height
        self.width = width

    def draw(self):
        self.canv.saveState()
        self.canv.setLineWidth(0.5)
        self.canv.line(self.width / 2, 0, self.width / 2, self.height)
        self.canv.restoreState()

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

def create_header_elements():
    styles = getSampleStyleSheet()
    style_title = styles['Title']
    style_title.fontSize = 16  

    try:
        institution = Institution.objects.order_by('id_ecole').first()
    except Institution.DoesNotExist:
        institution = None
        nom_ecole = "École inconnue"

    nom_ecole = institution.nom_ecole if institution else "École inconnue"

    logo_gauche = None
    logo_droite = None

    if institution and institution.logo_ministere:
        logo_ministere_path = os.path.join(settings.MEDIA_ROOT, institution.logo_ministere.name)
        if os.path.exists(logo_ministere_path):
            logo_gauche = Image(
                logo_ministere_path,
                width=1.1 * inch,
                height=1.1 * inch
            )

    if institution and institution.logo_ecole:
        logo_ecole_path = os.path.join(settings.MEDIA_ROOT, institution.logo_ecole.name)
        if os.path.exists(logo_ecole_path):
            logo_droite = Image(
                logo_ecole_path,
                width=1.1 * inch,
                height=1.1 * inch
            )

    logo_gauche = logo_gauche or None
    logo_droite = logo_droite or None

    titre = Paragraph(nom_ecole, style_title)

    entete_table = Table(
        [[logo_gauche, titre, logo_droite]],
        colWidths=[1.3 * inch, 6.4 * inch, 1.3 * inch]
    )
    entete_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))

    return [
        entete_table,
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=0.7, color=colors.black),
        Spacer(1, 4)
    ]

def stylize_table(table, table_data):
    style_commands = [
        # Header spans
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (0, 1), (0, 0)),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (1, 1)),
        ('SPAN', (2, 0), (4, 0)),
        ('SPAN', (5, 0), (7, 0)),
        ('SPAN', (8, 0), (10, 0)),
        ('SPAN', (11, 0), (13, 0)),
        ('SPAN', (14, 0), (17, 0)),
        # Row span
        ('SPAN', (0, 2), (1, 2)),
        ('SPAN', (0, 1), (1, 0)),
        ('SPAN', (0, 1), (1, 1)),
        # Row span:
        ('SPAN', (0, 3), (1, 3)),
        ('SPAN', (0, 4), (1, 4)),
        ('SPAN', (0, 5), (1, 5)),
        ('SPAN', (0, 6), (1, 6)),
        ('SPAN', (0, 7), (1, 7)),
        ('SPAN', (0, 8), (1, 8)),
        ('SPAN', (0, 13), (1, 13)),
        ('SPAN', (0, 14), (1, 14)),
        ('SPAN', (0, 15), (1, 15)),
                
        # Alignement à gauche pour les cellules fusionnées (lignes 14 à 19)
        ('ALIGN', (0, 14), (0, 14), 'LEFT'),
        ('ALIGN', (0, 15), (0, 15), 'LEFT'),
        ('ALIGN', (0, 16), (0, 16), 'LEFT'),
        ('ALIGN', (0, 17), (0, 17), 'LEFT'),
        ('ALIGN', (0, 18), (0, 18), 'LEFT'),
        ('ALIGN', (0, 19), (0, 19), 'LEFT'),
        # Alignement cours sans domaine
        ('ALIGN', (0, 11), (1, 11), 'LEFT'),
        ('ALIGN', (0, 12), (1, 12), 'LEFT'),
        ('ALIGN', (0, 13), (1, 13), 'LEFT'),
        # Mettre en gras les colonnes "Tot" (indices 4, 7, 10, 14, 15)
        ('FONTNAME', (4, 2), (4, -1), 'Helvetica-Bold'),
        ('FONTNAME', (7, 2), (7, -1), 'Helvetica-Bold'),
        ('FONTNAME', (10, 2), (10, -1), 'Helvetica-Bold'),
        ('FONTNAME', (14, 2), (14, -1), 'Helvetica-Bold'),
        ('FONTNAME', (15, 2), (15, -1), 'Helvetica-Bold'),
        # Base styles
        ('BACKGROUND', (0, 0), (-1, 1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('BACKGROUND', (0, 2), (-1, -1), colors.beige),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('ALIGN', (2, 0), (18, -1), 'CENTER'),
    ]

    # Fusion verticale des domaines
    start = 2
    while start < len(table_data):
        domaine = table_data[start][0]
        end = start + 1
        while end < len(table_data) and table_data[end][0] == domaine:
            table_data[end][0] = ''
            end += 1
        style_commands.append(('SPAN', (0, start), (0, end - 1)))
        style_commands.append(('VALIGN', (0, start), (0, end - 1), 'MIDDLE'))
        style_commands.append(('ALIGN', (0, start), (0, end - 1), 'LEFT'))
        style_commands.append(('TEXTCOLOR', (0, start), (0, end - 1), colors.black))
        style_commands.append(('FONTSIZE', (0, start), (0, end - 1), 10))
        start = end

    for row_idx, row in enumerate(table_data):
        for col_idx, cell in enumerate(row):
            if isinstance(cell, dict) and cell.get('highlight', False):
                style_commands.append(('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.grey))
                style_commands.append(('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.whitesmoke))

    table.setStyle(TableStyle(style_commands))
    return table

def create_student_info_tables(id_eleve, id_annee, id_campus, id_cycle, id_classe):
    # Récupérer les informations de l'élève
    try:
        eleve = Eleve.objects.get(id_eleve=id_eleve)
        nom_eleve = f"{eleve.nom} {eleve.prenom}"
    except Eleve.DoesNotExist:
        nom_eleve = "Élève inconnu"
        raise ValueError(f"Élève non trouvé pour id_eleve={id_eleve}")

    # Récupérer le nom de la classe
    try:
        
        classe = Classe_active.objects.get(id_annee =id_annee,id_campus = id_campus,cycle_id=id_cycle,id_classe_active=id_classe)
        nom_classe = f"{classe.classe_id.classe}_{classe.groupe}" if classe.groupe else classe.classe_id.classe
    except Classe_active.DoesNotExist:
        nom_classe = "Classe inconnue"
        raise ValueError(f"Classe non trouvée pour id_classe_active={id_classe}")

    try:
        annee = Annee.objects.get(id_annee=id_annee)
        annee_scolaire = annee.annee  
    except Annee.DoesNotExist:
        annee_scolaire = "Année inconnue"
        raise ValueError(f"Année non trouvée pour id_annee={id_annee}")
    
    # Compter le nombre d'élèves inscrits
    nombre_eleves = Eleve_inscription.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_classe_cycle=id_cycle,
        id_classe=id_classe, 
        status=1
    ).values('id_eleve').distinct().count()

    date_naissance = eleve.date_naissance.strftime('%d/%m/%Y') if eleve.date_naissance else ""

    header_left = [
        ['Nom et Prénom:', nom_eleve],
        ['Classe:', nom_classe]
    ]

    header_right = [
        ['Année scolaire:', annee_scolaire, 'Nombre d\'élèves:', str(nombre_eleves)],
        ['', '', 'Date de naissance:', date_naissance],
    ]

    table_left = Table(header_left, colWidths=[1.6 * inch, 2.3 * inch])
    table_right = Table(header_right, colWidths=[1.2 * inch, 1.2 * inch, 1.4 * inch, 1.2 * inch])

    table_style = TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ])
    table_left.setStyle(table_style)
    table_right.setStyle(table_style)

    header_tables = Table([[table_left, table_right]], colWidths=[3.9 * inch, 3.8 * inch])

    return [header_tables, Spacer(1, 4)], nom_eleve

def create_signature_table():
    trimestres = Trimestre.objects.all().order_by('id_trimestre')
    trimestre_noms = [trimestre.trimestre for trimestre in trimestres[:3]]  
    if not trimestre_noms:
        trimestre_noms = ['Aucun trimestre']  
    
    
    while len(trimestre_noms) < 3:
        trimestre_noms.append('')

    signature_data = [
        ['Signature'] + trimestre_noms + ['Direction'],
        ['Titulaire'] + [''] * len(trimestre_noms) + [''],
        ['Parent'] + [''] * len(trimestre_noms) + ['']
    ]

    nombre_colonnes = len(signature_data[0])  
    largeur_totale = 9.5 * inch  
    col_widths = [largeur_totale / nombre_colonnes] * nombre_colonnes

    signature_table = Table(signature_data, colWidths=col_widths)
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.7, colors.black),
        ('SPAN', (-1, 1), (-1, 2)), 
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    return [Spacer(1, 6), signature_table]

def page_template(canvas, doc):
    page_num = canvas.getPageNumber()
    canvas.saveState()
    if page_num == 2:  
        canvas.rotate(180)
        canvas.translate(-landscape(A4)[0], -landscape(A4)[1])
    canvas.restoreState()

