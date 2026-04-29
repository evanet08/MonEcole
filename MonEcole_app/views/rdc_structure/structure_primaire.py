
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
        campus = Campus.objects.get(idCampus=id_campus)
        localisation = campus.localisation.upper() 
    except Exception:
        localisation = 'RDC'  # Fallback safe — ne pas bloquer la génération

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
    style_normal = ParagraphStyle(name='NormalSmall', fontSize=5, leading=6, alignment=0, fontName='Times-Roman')  
    style_center = ParagraphStyle(name='CenterSmall', fontSize=5, leading=6, alignment=1, fontName='Times-Roman')  
    style_center_bold = ParagraphStyle(name='CenterSmallBold', fontName='Helvetica-Bold', fontSize=5, leading=6, alignment=1)
    style_normal_bold = ParagraphStyle(name='NormalSmallBold', fontName='Helvetica-Bold', fontSize=5, leading=6, alignment=0)
    style_title = ParagraphStyle(name='TitleSmall', fontSize=8, leading=9, alignment=1, fontName='Helvetica-Bold')
    style_right = ParagraphStyle(name='RightSmall', fontSize=7, leading=8, alignment=2, fontName='Times-Italic') 
    return styles, style_normal, style_center, style_center_bold, style_normal_bold, style_title, style_right

def check_image_paths(logo_path, emblem_path):
    if logo_path and not os.path.exists(logo_path):
        raise ValueError(f"Fichier logo introuvable : {logo_path}")
    if emblem_path and not os.path.exists(emblem_path):
        raise ValueError(f"Fichier emblème introuvable : {emblem_path}")

def _resolve_logo_paths(logo_path, emblem_path):
    """Fallback: si les logos Institution/Pays ne sont pas trouvés, chercher à la racine du projet."""
    from django.conf import settings
    base = getattr(settings, 'BASE_DIR', '')
    if not logo_path or not os.path.exists(logo_path):
        fallback = os.path.join(base, 'logoRDC')
        if os.path.exists(fallback):
            logo_path = fallback
        else:
            fallback2 = os.path.join(base, 'logoRDC.png')
            if os.path.exists(fallback2):
                logo_path = fallback2
    if not emblem_path or not os.path.exists(emblem_path):
        # Priorité au logo officiel MINEDUC
        fallback = os.path.join(base, 'logomineduc.png')
        if os.path.exists(fallback):
            emblem_path = fallback
        else:
            fallback2 = os.path.join(base, 'logoMinistere.png')
            if os.path.exists(fallback2):
                emblem_path = fallback2
    return logo_path, emblem_path

def create_header(elements, logo_path, emblem_path, style_title, style_center, eleve=None):
    logo_path, emblem_path = _resolve_logo_paths(logo_path, emblem_path)
    # Drapeau RDC à gauche — grand format officiel
    logo = Image(logo_path, width=24*mm, height=16*mm) if logo_path and os.path.exists(logo_path) else Paragraph("", style_center)
    # Logo MINEDUC à droite — circulaire
    emblem = Image(emblem_path, width=18*mm, height=18*mm) if emblem_path and os.path.exists(emblem_path) else Paragraph("", style_center)
    header_title_style = ParagraphStyle('HeaderTitle', fontSize=10, leading=12, alignment=1, fontName='Times-Bold')
    header_data = [
        [logo, Paragraph("<font color='black'><b>REPUBLIQUE DEMOCRATIQUE DU CONGO<br/>MINISTERE DE L'EDUCATION NATIONALE<br/>ET NOUVELLE CITOYENNETE</b></font>", header_title_style), emblem]
    ]
    header_table = Table(header_data, colWidths=[30*mm, 134*mm, 30*mm], rowHeights=[22*mm], hAlign='LEFT')
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (-1, -1), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(header_table)


def create_line2_left(elements, style_normal, id_campus=None):
    """Left info section — 40% du bulletin, format officiel RDC."""
    
    # Retrieve matricule + nom école
    matricule = ""
    ecole_display = ""
    if id_campus:
        try:
            campus = Campus.objects.get(idCampus=id_campus)
            if campus.id_etablissement:
                from django.db import connections
                with connections['countryStructure'].cursor() as cursor:
                    cursor.execute(
                        "SELECT matricule, nom FROM etablissements WHERE id_etablissement = %s",
                        [campus.id_etablissement]
                    )
                    row = cursor.fetchone()
                    if row:
                        if row[0]:
                            matricule = str(row[0]).strip()
                        if row[1]:
                            ecole_display = str(row[1]).strip().upper()
        except Exception:
            pass

    # CODE boxes
    nb_cases = len(matricule) if matricule else 7
    matricule_cells = [list(matricule)] if matricule else [[''] * nb_cases]
    code_squares_table = Table(matricule_cells, colWidths=[4*mm]*nb_cases, rowHeights=5*mm)
    code_squares_table.setStyle(TableStyle([
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
        code_squares_table.setStyle(TableStyle([
            ('BOX', (i,0), (i,0), 0.5, colors.black),
        ]))

    # Styles — libellés NORMAL, valeurs GRAS, valeurs au-dessus des pointillés
    lbl_style = ParagraphStyle(name='InfoLabel', fontSize=7, leading=8, alignment=0, fontName='Helvetica')
    colon_style = ParagraphStyle(name='InfoColon', fontSize=7, leading=8, alignment=1, fontName='Helvetica')

    # Helper: valeur en gras sans pointillés
    def val_bold(value):
        return Paragraph(f"<b>{value}</b>", ParagraphStyle(
            name='ValBold', fontSize=7, leading=8, alignment=0, fontName='Helvetica-Bold'))

    left_w = 97*mm  # 50% de ~194mm
    lbl_w = 32*mm
    col_w = 3*mm
    val_w = left_w - lbl_w - col_w

    left_data = [
        [Paragraph("PROVINCE EDUC.", lbl_style), Paragraph(":", colon_style), val_bold("SUD-KIVU")],
        [Paragraph("VILLE", lbl_style), Paragraph(":", colon_style), val_bold("BUKAVU")],
        [Paragraph("COMMUNE/TER.", lbl_style), Paragraph(":", colon_style), val_bold("D'IBANDA")],
        [Paragraph("ECOLE", lbl_style), Paragraph(":", colon_style), val_bold(ecole_display or "")],
        [Paragraph("CODE", lbl_style), Paragraph(":", colon_style), code_squares_table],
    ]
    left_table = Table(left_data, colWidths=[lbl_w, col_w, val_w], rowHeights=[4.5*mm]*4 + [6*mm])
    left_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return left_table  

def create_nid_section(elements, style_normal, eleve=None, id_campus=None):
    """N.ID section: numero_serie_eleve - matricule_ecole displayed in bold detached boxes."""
    # Build the NID string: numero_serie - matricule
    nid_value = ""
    numero_serie = ""
    matricule = ""

    if eleve and hasattr(eleve, 'numero_serie') and eleve.numero_serie:
        numero_serie = str(eleve.numero_serie).strip()

    if id_campus:
        try:
            campus = Campus.objects.get(idCampus=id_campus)
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

    if numero_serie and matricule:
        nid_value = f"{numero_serie}-{matricule}"
    elif numero_serie:
        nid_value = numero_serie
    elif matricule:
        nid_value = matricule

    # Create individual character boxes (bold, detached)
    nb_cases = max(len(nid_value), 20)  # minimum 20 boxes
    chars = list(nid_value.ljust(nb_cases))  # pad with spaces if shorter

    nid_squares = [chars]
    nid_squares_table = Table(nid_squares, colWidths=[4*mm]*nb_cases, rowHeights=4*mm)
    nid_squares_table.setStyle(TableStyle([
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
        nid_squares_table.setStyle(TableStyle([
            ('BOX', (i,0), (i,0), 0.5, colors.black),
        ]))

    nid_label_style = ParagraphStyle(name='NIDLabel', fontSize=6, leading=8, alignment=1, fontName='Helvetica-Bold')
    nid_data = [[Paragraph("N\u00b0ID.", nid_label_style), nid_squares_table]]
    nid_table = Table(nid_data, colWidths=[12*mm, nb_cases*4*mm + 4*mm], hAlign='CENTER')
    nid_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    elements.append(nid_table)


def create_line2_right(elements, eleve, style_normal, id_classe):
    """Right info section — format image officiel: labels gras inline avec pointillés."""
    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
        classe_name = eac.classe.classe.strip().upper()
    except:
        return HttpResponse('<script>history.back();</script>', status=404)
    
    # N° PERM. boxes
    nperm_str = str(eleve.numero_serie).strip() if hasattr(eleve, 'numero_serie') and eleve.numero_serie else ''
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

    # Style — labels normal, valeurs en gras via <b>
    p_style = ParagraphStyle(name='InfoRightP', fontSize=7, leading=8, alignment=0, fontName='Helvetica')

    nom_upper = (eleve.nom or '').upper()
    prenom_title = (eleve.prenom or '').title()
    sexe = (eleve.genre or '').upper()
    
    date_str = ''
    if eleve.date_naissance:
        try:
            d = eleve.date_naissance
            date_str = f"{d.day:02d} / {d.month:02d} / {d.year}"
        except:
            date_str = str(eleve.date_naissance)

    # Lieu de naissance: récupérer VILLE/TERRITOIRE (2ème niveau) depuis ref_administrative_naissance
    lieu_naissance = ''
    ref_naissance = getattr(eleve, 'ref_administrative_naissance', None) or ''
    if ref_naissance:
        try:
            ids_chain = ref_naissance.split('-')
            if len(ids_chain) >= 2:
                ville_id = ids_chain[1]  # 2ème élément = VILLE/TERRITOIRE
                # Resolve pays_id from the eleve's establishment
                eleve_pays_id = getattr(eleve, 'id_pays', None) or 2  # fallback RDC
                from django.db import connections
                with connections['countryStructure'].cursor() as cursor:
                    cursor.execute('SELECT nom FROM administrativeStructures WHERE id_structure = %s AND pays_id = %s', [ville_id, eleve_pays_id])
                    row = cursor.fetchone()
                    if row and row[0]:
                        lieu_naissance = row[0].upper()
        except Exception:
            pass

    dots_long = '<font size="3" color="#aaaaaa">' + ' .' * 60 + '</font>'
    dots_mid = '<font size="3" color="#aaaaaa">' + ' .' * 35 + '</font>'
    dots_short = '<font size="3" color="#aaaaaa">' + ' .' * 15 + '</font>'

    right_w = 97*mm
    nperm_box_w = nb_cases*4*mm + 1*mm
    text_w = right_w - nperm_box_w

    # Position fixe pour SEXE / LE date : 30mm à droite
    sexe_col_w = 30*mm
    eleve_col_w = right_w - sexe_col_w  # full spanned width, not text_w

    # Mini-table ELEVE : [nom + dots | SEXE + dots]
    eleve_inner = Table(
        [[Paragraph(f"ELEVE : <b>{nom_upper} {prenom_title}</b>{dots_mid if not nom_upper else ''}", p_style),
          Paragraph(f"SEXE : <b>{sexe}</b>{dots_short if not sexe else ''}", p_style)]],
        colWidths=[eleve_col_w, sexe_col_w], rowHeights=[4.5*mm]
    )
    eleve_inner.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    # Mini-table NE(E) A : [lieu + dots | LE date + dots]
    nea_inner = Table(
        [[Paragraph(f"NE(E) A : <b>{lieu_naissance}</b>{dots_mid if not lieu_naissance else ''}", p_style),
          Paragraph(f"LE <b>{date_str if date_str else '..... / ..... / ..........'}</b>{dots_short if not date_str else ''}", p_style)]],
        colWidths=[eleve_col_w, sexe_col_w], rowHeights=[4.5*mm]
    )
    nea_inner.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))

    final_rows = [
        [eleve_inner, None],
        [nea_inner, None],
        [Paragraph(f"CLASSE : <b>{classe_name}</b>{dots_long if not classe_name else ''}", p_style), None],
        [Paragraph("N° PERM. :", p_style), nperm_squares_table],
    ]

    right_table = Table(final_rows, colWidths=[text_w, nperm_box_w], rowHeights=[4.5*mm]*3 + [6*mm])
    right_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('SPAN', (0, 0), (1, 0)),  # ELEVE inner spans full width
        ('SPAN', (0, 1), (1, 1)),  # NE(E) A inner spans full width
        ('SPAN', (0, 2), (1, 2)),  # CLASSE spans full width
    ]))

    return right_table

def create_line2_section(elements, left_table, right_table):
    """Combine left (50%) + right (50%) avec séparateur vertical."""
    if isinstance(right_table, tuple):
        right_table = right_table[0]

    left_w = 100*mm   # 50%
    right_w = 100*mm   # 50%
    line2_data = [[left_table, right_table]]
    line2_table = Table(line2_data, colWidths=[left_w, right_w])

    line2_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (0, 0), 'TOP'),
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.black),
        ('LINEBEFORE', (1, 0), (1, -1), 0.3, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
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
    elements.append(Spacer(1, 1*mm))
    elements.append(Paragraph(f"<font color='black'><b>BULLETIN DE L'ELEVE DE DEGRE ({classe_name}) | Année Scolaire: {annee_obj.annee}</b></font>", style_title))
    elements.append(Spacer(1, 1*mm))

def get_periodes_par_trimestre(trimestres_data, id_annee, id_campus, id_cycle, id_classe):
    """
    Récupère les noms des périodes par trimestre.
    Gère deux structures de données :
      1) Périodes liées via parent_id (has_parent=1)
      2) Périodes plates indépendantes (has_parent=0) — distribuées par ordre
    """
    from django.db import connections

    periodes_labels = []

    # Résoudre EAC → etab_annee_id
    try:
        eac = EtablissementAnneeClasse.objects.get(id=id_classe)
        etab_annee_id = eac.etablissement_annee_id
    except EtablissementAnneeClasse.DoesNotExist:
        return [["-", "-"]] * 3

    # === Tentative 1 : périodes liées par parent_id ===
    found_linked = False
    for trimestre_tuple in trimestres_data:
        config_id_trimestre = trimestre_tuple[0]
        labels_trimestre = []
        try:
            periodes = Annee_periode.objects.filter(
                id_trimestre_annee_id=config_id_trimestre,
                has_parent=True
            ).select_related('repartition').order_by('id_periode')[:2]
            for p in periodes:
                nom = p.repartition.code if p.repartition and p.repartition.code else "-"
                labels_trimestre.append(nom)
                found_linked = True
        except Exception:
            pass
        while len(labels_trimestre) < 2:
            labels_trimestre.append("-")
        periodes_labels.append(labels_trimestre)

    if found_linked:
        while len(periodes_labels) < 3:
            periodes_labels.append(["-", "-"])
        return periodes_labels

    # === Tentative 2 : périodes plates (pas de parent_id) ===
    # Récupérer toutes les configs de type "Période" pour cet etab_annee
    periodes_labels = []
    try:
        with connections['countryStructure'].cursor() as cur:
            cur.execute("""
                SELECT ri.code
                FROM repartition_configs_etab_annee rc
                JOIN repartition_instances ri ON ri.id = rc.repartition_id
                JOIN repartition_types rt ON rt.id = ri.type_id
                WHERE rc.etablissement_annee_id = %s
                  AND rt.code = 'P'
                  AND rc.is_open = 1
                ORDER BY ri.code, rc.id
            """, [etab_annee_id])
            all_period_names = [row[0] for row in cur.fetchall()]
    except Exception:
        all_period_names = []

    # Distribuer les périodes sur les trimestres (2 par trimestre)
    nb_trim = len(trimestres_data) or 3
    per_trim = max(len(all_period_names) // nb_trim, 1) if all_period_names else 0
    for i in range(nb_trim):
        start = i * per_trim
        end = start + per_trim
        chunk = all_period_names[start:end] if per_trim > 0 else []
        while len(chunk) < 2:
            chunk.append("-")
        periodes_labels.append(chunk[:2])

    while len(periodes_labels) < 3:
        periodes_labels.append(["-", "-"])

    return periodes_labels


def calculer_pts_obt_trimestriels_et_annuel(table_data, style_center):

    protected_rows = {0, 1}

    def safe_float(value):
        if value is None:
            return 0.0
        try:
            import re
            text = str(value.text if hasattr(value, 'text') else value).strip()
            text = re.sub(r'<[^>]+>', '', text).strip()
            if text in ("", "-", " "):
                return 0.0
            return float(text)
        except (ValueError, AttributeError, TypeError):
            return 0.0

    def format_note(val):
       
        if val <= 0:
            return "-"
        
        # On arrondit à 2 décimales pour nettoyer les erreurs flottantes
        rounded = round(val, 2)
        
        if rounded == int(rounded):
            return str(int(rounded))
        return f"{rounded:.2f}".rstrip('0').rstrip('.')

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
            import re
            text = str(value.text if hasattr(value, 'text') else value).strip()
            text = re.sub(r'<[^>]+>', '', text).strip()
            if text in ("", "-", " "):
                return 0.0
            return float(text)
        except (ValueError, AttributeError, TypeError):
            return 0.0

    def format_note(val, force_decimal=False):
        """Formatage propre et lisible"""
        if val <= 0:
            return "-"
        
        rounded = round(val, 2)
        
        if rounded == int(rounded):
            return str(int(rounded))
        return f"{rounded:.2f}".rstrip('0').rstrip('.')

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
                import re
                text = str(row[col].text).strip()
                text = re.sub(r'<[^>]+>', '', text).strip()
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
        
        if val_ar == int(val_ar):
            return str(int(val_ar))
    
        return f"{val_ar:.2f}".rstrip('0').rstrip('.')

    mg_row[7]  = Paragraph(format_note(somme_col_7),  style_center)
    mg_row[14] = Paragraph(format_note(somme_col_14), style_center)
    mg_row[21] = Paragraph(format_note(somme_col_21), style_center)
    mg_row[23] = Paragraph(format_note(somme_col_23), style_center)

def _get_periode_to_col(eac):
    """Détermine dynamiquement le mapping période→colonne depuis la config de répartition."""
    from MonEcole_app.models.country_structure import RepartitionInstance
    # Récupérer TOUS les repartition_ids de la config pour cet établissement/année
    from django.db import connections
    try:
        with connections['countryStructure'].cursor() as cur:
            cur.execute("""
                SELECT DISTINCT repartition_id 
                FROM repartition_configs_etab_annee 
                WHERE etablissement_annee_id = %s
            """, [eac.etablissement_annee_id])
            config_rep_ids = [row[0] for row in cur.fetchall()]
    except Exception:
        config_rep_ids = []
    
    if not config_rep_ids:
        # Fallback: utiliser les repartition_instance existants dans les notes
        config_rep_ids = list(range(1, 20))
    
    # Résoudre les codes des RepartitionInstance — filtrer seulement les codes "P*"
    period_codes = []
    for ri in RepartitionInstance.objects.filter(pk__in=config_rep_ids):
        if ri.code and ri.code.startswith('P'):
            period_codes.append(ri.code)
    period_codes = sorted(set(period_codes))
    
    # Mapping colonnes : P1→2, P2→3 | P3→9, P4→10 | P5→16, P6→17
    col_positions = [2, 3, 9, 10, 16, 17]
    return {code: col_positions[i] for i, code in enumerate(period_codes) if i < len(col_positions)}


def _get_bulletin_context(eac):
    """
    Construit les mappings nécessaires pour lire note_bulletin :
    - cours_annee_to_cours: {id_cours_annee: id_cours_id}
    - config_to_rep: {id_repartition_config: repartition_id}
    - rep_to_code: {repartition_id: code}  (P1, P2, S1, S2, T1, etc.)
    """
    from django.db import connections
    import logging
    logger = logging.getLogger(__name__)

    etab_annee_id = eac.etablissement_annee_id

    # 1. cours_annee → id_cours (Hub)
    cours_annee_to_cours = {}
    try:
        with connections['countryStructure'].cursor() as cur:
            cur.execute("""
                SELECT ca.id_cours_annee, ca.cours_id
                FROM cours_annee ca
                WHERE ca.cours_id IN (
                    SELECT id FROM cours WHERE classe_id = %s
                )
            """, [eac.classe_id])
            for row in cur.fetchall():
                cours_annee_to_cours[row[0]] = row[1]
    except Exception as e:
        logger.warning(f"[_get_bulletin_context] cours_annee query failed: {e}")

    # 2. repartition_config → repartition_id (Hub)
    config_to_rep = {}
    try:
        with connections['countryStructure'].cursor() as cur:
            cur.execute("""
                SELECT id, repartition_id
                FROM repartition_configs_etab_annee
                WHERE etablissement_annee_id = %s
            """, [etab_annee_id])
            for row in cur.fetchall():
                config_to_rep[row[0]] = row[1]
    except Exception as e:
        logger.warning(f"[_get_bulletin_context] config query failed: {e}")

    # 3. repartition_id → code (Hub)
    rep_to_code = {}
    if config_to_rep:
        from MonEcole_app.models.country_structure import RepartitionInstance
        rep_ids = set(config_to_rep.values())
        for ri in RepartitionInstance.objects.filter(pk__in=rep_ids):
            rep_to_code[ri.pk] = ri.code

    return cours_annee_to_cours, config_to_rep, rep_to_code


def _get_deliberated_config_ids(id_eleve, eac):
    """
    Retourne les config_ids délibérés pour un élève :
    - deliberated_period_configs: set de config_ids de périodes délibérées (TJ)
    - deliberated_trim_configs: set de config_ids de trimestres/semestres délibérés (Examen)
    Seules les notes associées à ces configs apparaîtront sur le bulletin.
    """
    from MonEcole_app.models.evaluations.note import (
        Deliberation_periodique_resultat,
        Deliberation_examen_resultat,
        Deliberation_trimistrielle_resultat,
    )
    import logging
    logger = logging.getLogger(__name__)

    etab_annee_id = eac.etablissement_annee_id
    classe_id = eac.classe_id

    # 1. Période configs délibérées (id_periode = config_id de repartition_configs_etab_annee)
    deliberated_period_configs = set(
        Deliberation_periodique_resultat.objects.filter(
            id_eleve_id=id_eleve,
            id_classe_id=eac.classe_id,
        ).values_list('id_periode_id', flat=True)
    )
    # Fallback par id_annee si aucun résultat par classe_id
    if not deliberated_period_configs:
        deliberated_period_configs = set(
            Deliberation_periodique_resultat.objects.filter(
                id_eleve_id=id_eleve,
                id_annee=eac.etablissement_annee.annee_id,
            ).values_list('id_periode_id', flat=True)
        )
        if deliberated_period_configs:
            logger.warning(f"[_get_deliberated_config_ids] Period fallback par id_annee pour élève={id_eleve}")

    # 2. Trimestre/Semestre configs délibérés pour examens
    deliberated_exam_configs = set(
        Deliberation_examen_resultat.objects.filter(
            id_eleve_id=id_eleve,
            id_classe_id=eac.classe_id,
        ).values_list('id_trimestre_id', flat=True)
    )
    if not deliberated_exam_configs:
        deliberated_exam_configs = set(
            Deliberation_examen_resultat.objects.filter(
                id_eleve_id=id_eleve,
                id_annee=eac.etablissement_annee.annee_id,
            ).values_list('id_trimestre_id', flat=True)
        )
        if deliberated_exam_configs:
            logger.warning(f"[_get_deliberated_config_ids] Exam fallback par id_annee pour élève={id_eleve}")

    # 3. Trimestre/Semestre configs délibérés (trimestriels)
    deliberated_trim_configs = set(
        Deliberation_trimistrielle_resultat.objects.filter(
            id_eleve_id=id_eleve,
            id_classe_id=eac.classe_id,
        ).values_list('id_trimestre_id', flat=True)
    )
    if not deliberated_trim_configs:
        deliberated_trim_configs = set(
            Deliberation_trimistrielle_resultat.objects.filter(
                id_eleve_id=id_eleve,
                id_annee=eac.etablissement_annee.annee_id,
            ).values_list('id_trimestre_id', flat=True)
        )
        if deliberated_trim_configs:
            logger.warning(f"[_get_deliberated_config_ids] Trim fallback par id_annee pour élève={id_eleve}")

    # Union des configs trimestre (examen + trimestriel)
    all_trim_configs = deliberated_exam_configs | deliberated_trim_configs

    logger.info(f"[_get_deliberated_config_ids] eleve={id_eleve}: "
                f"period_configs={deliberated_period_configs}, "
                f"trim_configs={all_trim_configs}")

    return deliberated_period_configs, all_trim_configs


def _has_annual_deliberation(id_eleve, eac):
    """Vérifie si l'élève a une délibération annuelle."""
    from MonEcole_app.models.evaluations.note import Deliberation_annuelle_resultat
    import logging
    logger = logging.getLogger(__name__)

    # Filtre principal : par business key (classe_id)
    exists = Deliberation_annuelle_resultat.objects.filter(
        id_eleve_id=id_eleve,
        id_classe_id=eac.classe_id,
    ).exists()

    if not exists:
        # Fallback : filtre par année (au cas où les données utilisent un ancien schéma)
        exists = Deliberation_annuelle_resultat.objects.filter(
            id_eleve_id=id_eleve,
            id_annee=eac.etablissement_annee.annee_id,
        ).exists()
        if exists:
            logger.warning(
                f"[_has_annual_deliberation] Fallback par id_annee pour élève={id_eleve} "
                f"(classe_id={eac.classe_id} non trouvé, mais annee_id={eac.etablissement_annee.annee_id} trouvé)"
            )

    logger.info(f"[_has_annual_deliberation] eleve={id_eleve}, classe_id={eac.classe_id}, exists={exists}")
    return exists


def blank_non_deliberated_columns(table_data, id_eleve, id_classe, trimestres_data,
                                   style_center, bulletin_type='primaire'):
    """
    Post-processing : vide complètement les colonnes des périodes non-délibérées.
    Seuls les maxima structurels (Max per, Max Exam, Max Trim, Max Total) restent.
    Les colonnes non-délibérées deviennent des cellules vides (pas de '-', pas de '0.00%').
    
    bulletin_type: 'primaire' (3 trimestres, 24 cols) ou 'secondaire' (2 semestres, 20 cols)
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe', 'etablissement_annee').get(id=id_classe)
    except EtablissementAnneeClasse.DoesNotExist:
        return

    # Récupérer les configs délibérées
    deliberated_period_configs, deliberated_trim_configs = _get_deliberated_config_ids(id_eleve, eac)
    has_annual = _has_annual_deliberation(id_eleve, eac)

    # Construire le mapping config_id → colonne pour les périodes
    cours_annee_to_cours, config_to_rep, rep_to_code = _get_bulletin_context(eac)
    periode_to_col = _get_periode_to_col(eac)

    # Reverse map: pour chaque config_id de période, trouver la colonne
    config_to_col = {}
    for cfg_id, rep_id in config_to_rep.items():
        code = rep_to_code.get(rep_id, '')
        if code.startswith('P'):
            col = periode_to_col.get(code)
            if col is not None:
                config_to_col[cfg_id] = col

    # Déterminer les colonnes à effacer
    columns_to_blank = set()

    # 1. Colonnes de périodes non-délibérées
    # config_to_col contient déjà tous les config_ids de périodes → colonnes
    for cfg_id, col in config_to_col.items():
        if cfg_id not in deliberated_period_configs:
            columns_to_blank.add(col)

    # 2. Colonnes d'examen et TOT trimestre/semestre non-délibérées
    if bulletin_type == 'secondaire':
        # Secondaire: 2 semestres
        # T1 → exam=col5, tot=col7 ; T2 → exam=col12, tot=col14
        trim_col_map = {}
        if len(trimestres_data) >= 1:
            trim_col_map[trimestres_data[0][0]] = {'exam': 5, 'tot': 7}
        if len(trimestres_data) >= 2:
            trim_col_map[trimestres_data[1][0]] = {'exam': 12, 'tot': 14}

        for trim_id, cols in trim_col_map.items():
            if trim_id not in deliberated_trim_configs:
                columns_to_blank.add(cols['exam'])
                columns_to_blank.add(cols['tot'])

        # 3. Total général (col 16) : blanker SEULEMENT si un des semestres n'est pas délibéré
        #    (le total est la somme des TOT.SEM, donc si les deux semestres sont visibles, le total l'est aussi)
        if 7 in columns_to_blank or 14 in columns_to_blank:
            columns_to_blank.add(16)

    elif bulletin_type == 'primaire':
        # Primaire: 3 trimestres
        # T1 → exam=col5, tot=col7 ; T2 → exam=col12, tot=col14 ; T3 → exam=col19, tot=col21
        trim_col_map = {}
        if len(trimestres_data) >= 1:
            trim_col_map[trimestres_data[0][0]] = {'exam': 5, 'tot': 7}
        if len(trimestres_data) >= 2:
            trim_col_map[trimestres_data[1][0]] = {'exam': 12, 'tot': 14}
        if len(trimestres_data) >= 3:
            trim_col_map[trimestres_data[2][0]] = {'exam': 19, 'tot': 21}

        for trim_id, cols in trim_col_map.items():
            if trim_id not in deliberated_trim_configs:
                columns_to_blank.add(cols['exam'])
                columns_to_blank.add(cols['tot'])

        # 3. Total annuel (col 23) : blanker SEULEMENT si un trimestre n'est pas délibéré
        if 7 in columns_to_blank or 14 in columns_to_blank or 21 in columns_to_blank:
            columns_to_blank.add(23)

    if not columns_to_blank:
        logger.info(f"[blank_non_deliberated] Rien à effacer pour élève {id_eleve}")
        return

    logger.info(f"[blank_non_deliberated] élève={id_eleve}, colonnes à effacer: {columns_to_blank}")

    # Colonnes structurelles + TOTAL GENERAL + TOT.SEM à ne JAMAIS blanker
    if bulletin_type == 'secondaire':
        structural_cols = {1, 4, 6, 7, 8, 11, 13, 14, 15, 16}  # Max + TOT.SEM + Total Général
    else:
        structural_cols = {1, 4, 6, 7, 8, 11, 13, 14, 15, 18, 20, 21, 22, 23}  # Primaire: Max + TOT + Total

    # Mots-clés des lignes spéciales à protéger
    protected_keywords = {
        'MAXIMA GENEREAUX', 'POURCENTAGE', 'PLACE', 'CONDUITE',
        'APPLICATION', 'SIGNATURE'
    }

    # Appliquer le blanking sur les lignes de cours/sous-totaux uniquement
    for row_idx, row in enumerate(table_data):
        if row_idx < 3:  # Skip header rows (0, 1, 2)
            continue
        if len(row) == 0 or row[0] is None:
            continue

        # Vérifier si c'est une ligne protégée (MAXIMA, POURCENTAGE, PLACE, etc.)
        row_text = ''
        if isinstance(row[0], Paragraph):
            row_text = (row[0].text or '').upper()
        else:
            row_text = str(row[0]).upper()
        
        is_protected_row = any(kw in row_text for kw in protected_keywords)
        if is_protected_row:
            continue  # Ne jamais blanker les lignes spéciales

        for col in columns_to_blank:
            if col in structural_cols:
                continue  # Ne pas blanker les colonnes Max structurelles
            if col < len(row):
                row[col] = Paragraph("", style_center)


def get_student_notes_rdc(id_eleve, id_annee, id_campus, id_cycle, id_classe):
    """
    Retourne les notes TJ par cours depuis note_bulletin, indexées par code de période.
    Source: note_bulletin WHERE id_note_type=1 AND source_type IN ('EVALUATIONS','HERITAGE')
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe', 'etablissement_annee').get(id=id_classe)
    except EtablissementAnneeClasse.DoesNotExist:
        return defaultdict(dict)

    periode_to_col = _get_periode_to_col(eac)
    if not periode_to_col:
        return defaultdict(dict)

    cours_annee_to_cours, config_to_rep, rep_to_code = _get_bulletin_context(eac)
    if not cours_annee_to_cours:
        logger.warning(f"[get_student_notes_rdc] No cours_annee mapping for classe_id={eac.classe_id}")
        return defaultdict(dict)

    from MonEcole_app.models.evaluations.note import NoteBulletin
    from MonEcole_app.models.campus import Campus
    campus = Campus.objects.filter(idCampus=id_campus).first()
    etab_id = campus.id_etablissement if campus else 1

    # TJ notes from note_bulletin (type=1, source=EVALUATIONS for periods)
    # order_by id_note_bulletin ASC so latest entry overwrites older duplicates
    notes_qs = NoteBulletin.objects.filter(
        id_eleve_id=id_eleve,
        id_etablissement=etab_id,
        id_note_type=1,  # TJ
        id_cours_annee__in=cours_annee_to_cours.keys(),
    ).order_by('id_note_bulletin')

    notes_par_cours = defaultdict(dict)
    for nb in notes_qs:
        cours_id = cours_annee_to_cours.get(nb.id_cours_annee)
        if not cours_id:
            continue
        config_id = nb.id_repartition_config
        rep_id = config_to_rep.get(config_id)
        if not rep_id:
            continue
        code = rep_to_code.get(rep_id)
        if not code or code not in periode_to_col:
            continue
        col = periode_to_col[code]
        val = nb.note
        if val is not None:
            val_r = round(float(val), 1)
            valeur_affichee = str(int(val_r)) if val_r == int(val_r) else f"{val_r:.1f}"
        else:
            valeur_affichee = "-"
        notes_par_cours[cours_id][code] = {
            'valeur': valeur_affichee,
            'colonne': col
        }

    logger.warning(f"[get_student_notes_rdc] note_bulletin: found TJ for {len(notes_par_cours)} cours")
    return notes_par_cours


def get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe):
    """
    Retourne les notes d'examen par cours depuis note_bulletin.
    Seules les notes des trimestres/semestres DELIBERES apparaissent.
    Source: note_bulletin WHERE id_note_type=2 (EX)
    Indexées par config_id pour compatibilité avec le template existant.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe', 'etablissement_annee').get(id=id_classe)
    except EtablissementAnneeClasse.DoesNotExist:
        return defaultdict(dict)

    cours_annee_to_cours, config_to_rep, rep_to_code = _get_bulletin_context(eac)
    if not cours_annee_to_cours:
        return defaultdict(dict)

    # Filtre délibération : récupérer les config_ids de trimestres délibérés
    _, deliberated_trim_configs = _get_deliberated_config_ids(id_eleve, eac)

    from MonEcole_app.models.evaluations.note import NoteBulletin
    from MonEcole_app.models.campus import Campus
    campus = Campus.objects.filter(idCampus=id_campus).first()
    etab_id = campus.id_etablissement if campus else 1

    # EX notes from note_bulletin (type=2)
    notes_qs = NoteBulletin.objects.filter(
        id_eleve_id=id_eleve,
        id_etablissement=etab_id,
        id_note_type=2,  # EX
        id_cours_annee__in=cours_annee_to_cours.keys(),
    ).order_by('id_note_bulletin')

    notes_par_cours = defaultdict(dict)
    for nb in notes_qs:
        cours_id = cours_annee_to_cours.get(nb.id_cours_annee)
        if not cours_id:
            continue
        config_id = nb.id_repartition_config

        # Filtre délibération : ignorer les trimestres non délibérés
        if deliberated_trim_configs and config_id not in deliberated_trim_configs:
            continue

        notes_par_cours[cours_id][config_id] = (
            float(nb.note) if nb.note is not None else "-"
        )

    logger.warning(f"[get_student_exam_notes] note_bulletin: found EX for {len(notes_par_cours)} cours, "
                   f"deliberated_trims={deliberated_trim_configs}")
    return notes_par_cours




def calculer_pts_obt_et_somme_finale(table_data, style_center):
    
    protected_rows = {0, 1}

    def safe_float(value):
        """Convertit proprement en float, retourne 0.0 en cas d'erreur"""
        if value is None:
            return 0.0
        try:
            import re
            text = str(value.text).strip() if hasattr(value, 'text') else str(value).strip()
            text = re.sub(r'<[^>]+>', '', text).strip()
            if text in ("", "-", " "):
                return 0.0
            return float(text)
        except (ValueError, AttributeError, TypeError):
            return 0.0

    def format_note(val, decimals=2):
        """Formatage propre : entier si possible, sinon décimales sans zéros inutiles"""
        if val <= 0:
            return "-"
        rounded = round(val, decimals)
        if rounded == int(rounded):
            return str(int(rounded))
        return f"{rounded:.{decimals}f}".rstrip('0').rstrip('.')

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
    """
    Calcule les pourcentages sur la ligne POURCENTAGE.
    Formule : pourcentage = PTS.OBT / MAX * 100
    - Pour les trimestres (cols 7, 14, 21) : PTS.OBT_trim / MAX_TRIM
    - Pour l'annuel (col 23) : PTS.OBT_annuel / MAX_annuel  
    - Pour les périodes et exams : somme notes / somme maxima depuis les Sous Total
    """
    import logging
    _logger = logging.getLogger(__name__)
    
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
            cell = table_data[row_idx][col]
            if cell is None:
                return 0.0
            try:
                text = str(cell.text).strip() if hasattr(cell, 'text') else str(cell).strip()
                # Nettoyer les tags HTML
                import re
                text = re.sub(r'<[^>]+>', '', text).strip()
                if text in ("", "-"):
                    return 0.0
                return float(text)
            except (ValueError, AttributeError, TypeError):
                return 0.0
        return 0.0

    def format_pct(val):
        """Formater le pourcentage sans zéros inutiles"""
        if val <= 0:
            return "0%"
        rounded = round(val, 2)
        if rounded == int(rounded):
            return f"{int(rounded)}%"
        return f"{rounded:.2f}".rstrip('0').rstrip('.') + "%"

    pourcentage_row = table_data[ligne_pourcentage_idx]
    while len(pourcentage_row) < 24:
        pourcentage_row.append(None)

    # --- Collecter les totaux depuis les lignes Sous Total ---
    # Pour chaque colonne, sommer les valeurs des lignes Sous Total
    sous_total_sums = [0.0] * 24
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            text = row[0].text or ""
            if "Sous Total" in text:
                for col in range(1, 24):
                    if col < len(row):
                        sous_total_sums[col] += get_val(idx, col)

    # Maxima depuis la ligne MAXIMA GENEREAUX
    max_vals = {}
    for col in range(1, 24):
        max_vals[col] = get_val(max_gen_idx, col)

    _logger.warning(f"[POURCENTAGE] sous_total_sums[2]={sous_total_sums[2]}, [3]={sous_total_sums[3]}, [5]={sous_total_sums[5]}")
    _logger.warning(f"[POURCENTAGE] max_vals[1]={max_vals[1]}, [4]={max_vals[4]}, [6]={max_vals[6]}")
    _logger.warning(f"[POURCENTAGE] sous_total_sums[7]={sous_total_sums[7]}, max_vals[6]={max_vals[6]}")

    # --- Pourcentages par période (cols 2,3,9,10,16,17) ---
    # Période : somme_sous_totaux[col] / maxima_genereaux[col_max_per] * 100
    # col_max_per pour T1=1, T2=8, T3=15
    period_map = {
        2: 1, 3: 1,      # T1 periods → max in col 1
        9: 8, 10: 8,     # T2 periods → max in col 8
        16: 15, 17: 15,  # T3 periods → max in col 15
    }
    for col, max_col in period_map.items():
        max_per = max_vals.get(max_col, 0)
        # max_per = somme des pondérations par période (déjà = maxima_tj / 2)
        if max_per > 0:
            pct = sous_total_sums[col] / max_per * 100
            pourcentage_row[col] = Paragraph(format_pct(pct), style_center)
        else:
            pourcentage_row[col] = Paragraph("-", style_center)

    # --- Pourcentages examen (cols 5, 12, 19) ---
    exam_map = {5: 4, 12: 11, 19: 18}
    for col, max_col in exam_map.items():
        max_exam = max_vals.get(max_col, 0)
        if max_exam > 0:
            pct = sous_total_sums[col] / max_exam * 100
            pourcentage_row[col] = Paragraph(format_pct(pct), style_center)
        else:
            pourcentage_row[col] = Paragraph("-", style_center)

    # --- Pourcentages trimestre (cols 7, 14, 21) ---
    trim_map = {7: 6, 14: 13, 21: 20}
    for col, max_col in trim_map.items():
        max_trim = max_vals.get(max_col, 0)
        if max_trim > 0:
            pct = sous_total_sums[col] / max_trim * 100
            pourcentage_row[col] = Paragraph(format_pct(pct), style_center)
        else:
            pourcentage_row[col] = Paragraph("-", style_center)

    # --- Pourcentage annuel (col 23) ---
    max_annuel = max_vals.get(22, 0)
    if max_annuel > 0:
        pct = sous_total_sums[23] / max_annuel * 100
        pourcentage_row[23] = Paragraph(format_pct(pct), style_center)
    else:
        pourcentage_row[23] = Paragraph("-", style_center)


def get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe):
    """
    Retourne les notes TJ par cours depuis note_bulletin,
    indexées par position de colonne (2, 3, 9, 10, 16, 17).
    Seules les notes des périodes DELIBEREES apparaissent.
    Source: note_bulletin WHERE id_note_type = TJ (type 1)
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        eac = EtablissementAnneeClasse.objects.select_related('classe', 'etablissement_annee').get(id=id_classe)
    except EtablissementAnneeClasse.DoesNotExist:
        return defaultdict(dict)

    periode_to_col = _get_periode_to_col(eac)
    if not periode_to_col:
        logger.warning(f"[get_student_period_notes] No periode_to_col mapping")
        return defaultdict(dict)

    cours_annee_to_cours, config_to_rep, rep_to_code = _get_bulletin_context(eac)
    if not cours_annee_to_cours:
        logger.warning(f"[get_student_period_notes] No cours_annee mapping")
        return defaultdict(dict)

    # Filtre délibération : récupérer les config_ids délibérés
    deliberated_period_configs, _ = _get_deliberated_config_ids(id_eleve, eac)

    from MonEcole_app.models.evaluations.note import NoteBulletin
    from MonEcole_app.models.campus import Campus
    campus = Campus.objects.filter(idCampus=id_campus).first()
    etab_id = campus.id_etablissement if campus else 1

    # TJ notes from note_bulletin (type=1)
    notes_qs = NoteBulletin.objects.filter(
        id_eleve_id=id_eleve,
        id_etablissement=etab_id,
        id_note_type=1,  # TJ
        id_cours_annee__in=cours_annee_to_cours.keys(),
    ).order_by('id_note_bulletin')

    notes_par_cours = defaultdict(dict)
    for nb in notes_qs:
        cours_id = cours_annee_to_cours.get(nb.id_cours_annee)
        if not cours_id:
            continue
        config_id = nb.id_repartition_config

        # Filtre délibération : ignorer les périodes non délibérées
        if deliberated_period_configs and config_id not in deliberated_period_configs:
            continue

        rep_id = config_to_rep.get(config_id)
        if not rep_id:
            continue
        code = rep_to_code.get(rep_id)
        if not code:
            continue

        # Map code to column position
        col = periode_to_col.get(code)
        if col is None:
            continue

        val = nb.note
        if val is not None:
            val_f = round(float(val), 1)
            valeur = str(int(val_f)) if val_f == int(val_f) else f"{val_f:.1f}"
        else:
            valeur = "-"
        notes_par_cours[cours_id][col] = valeur

    logger.warning(f"[get_student_period_notes] note_bulletin: found TJ for {len(notes_par_cours)} cours, "
                   f"deliberated_periods={deliberated_period_configs}")
    return notes_par_cours




def get_place_for_column(id_annee, id_campus, id_cycle, id_classe, id_eleve, col):
    """
    Récupère le classement depuis les tables de délibération.
    Utilise config_id (PK de repartition_configs_etab_annee) car c'est ce que
    execute_deliberation stocke dans id_periode_id / id_trimestre_id.
    Même pattern que get_place_secondaire.
    """
    from django.db import connections
    from .structure_secondaire import _normalize_place

    # Resolve EAC → business keys
    try:
        eac = EtablissementAnneeClasse.objects.get(id=id_classe)
        bk_classe_id = eac.classe_id
        bk_groupe = eac.groupe
        bk_section_id = eac.section_id
        etab_annee_id = eac.etablissement_annee_id
    except EtablissementAnneeClasse.DoesNotExist:
        return "-"

    filtre_base = {
        "id_classe_id": bk_classe_id,
        "groupe": bk_groupe,
        "section_id": bk_section_id,
        "id_eleve_id": id_eleve,
    }

    # Build code→config_id mapping from Hub
    code_to_config = {}
    try:
        with connections['countryStructure'].cursor() as cur:
            cur.execute("""
                SELECT rc.id, ri.code
                FROM repartition_configs_etab_annee rc
                JOIN repartition_instances ri ON ri.id = rc.repartition_id
                WHERE rc.etablissement_annee_id = %s
            """, [etab_annee_id])
            for row in cur.fetchall():
                code_to_config[row[1]] = row[0]
    except Exception:
        pass

    # Mapping colonne → code de période/trimestre
    # Primaire: 3 trimestres × 2 périodes = P1..P6, T1..T3
    col_to_code_periode = {
        2: "P1", 3: "P2",
        9: "P3", 10: "P4",
        16: "P5", 17: "P6",
    }
    col_to_code_examen = {
        5: "T1", 12: "T2", 19: "T3",
    }
    col_to_code_trimestre = {
        7: "T1", 14: "T2", 21: "T3",
    }

    # Colonnes périodes (TJ)
    if col in col_to_code_periode:
        code = col_to_code_periode[col]
        config_id = code_to_config.get(code)
        if not config_id:
            return "-"
        filtre = {**filtre_base, "id_periode_id": config_id}
        res = Deliberation_periodique_resultat.objects.filter(**filtre).first()
        raw = res.place.strip() if res and res.place and res.place.strip() else "-"
        return _normalize_place(raw, Deliberation_periodique_resultat, "id_periode_id", filtre_base, config_id)

    # Colonnes examen
    if col in col_to_code_examen:
        code = col_to_code_examen[col]
        config_id = code_to_config.get(code)
        if not config_id:
            return "-"
        filtre = {**filtre_base, "id_trimestre_id": config_id}
        res = Deliberation_examen_resultat.objects.filter(**filtre).first()
        raw = res.place.strip() if res and res.place and res.place.strip() else "-"
        return _normalize_place(raw, Deliberation_examen_resultat, "id_trimestre_id", filtre_base, config_id)

    # Colonnes total trimestre
    if col in col_to_code_trimestre:
        code = col_to_code_trimestre[col]
        config_id = code_to_config.get(code)
        if not config_id:
            return "-"
        filtre = {**filtre_base, "id_trimestre_id": config_id}
        res = Deliberation_trimistrielle_resultat.objects.filter(**filtre).first()
        raw = res.place.strip() if res and res.place and res.place.strip() else "-"
        return _normalize_place(raw, Deliberation_trimistrielle_resultat, "id_trimestre_id", filtre_base, config_id)

    # Col 23 = TOTAL ANNUEL
    if col == 23:
        res = Deliberation_annuelle_resultat.objects.filter(**filtre_base).first()
        raw = res.place.strip() if res and res.place and res.place.strip() else "-"
        return _normalize_place(raw, Deliberation_annuelle_resultat, None, filtre_base)

    return "-"


def injecter_places_dans_tableau(table_data, id_annee, id_campus, id_cycle, id_classe, id_eleve, id_trimestre):
    # Trouver dynamiquement la ligne PLACE/NBRE D'ELEVES
    place_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            if "PLACE" in texte:
                place_idx = idx
                break

    if place_idx is None:
        logger.warning("[injecter_places_dans_tableau] Ligne PLACE non trouvée")
        return False

    ligne_place = table_data[place_idx]
    while len(ligne_place) < 24:
        ligne_place.append(None)

    place_style = ParagraphStyle(
        name='PlaceStyle',
        parent=style_normal,
        fontName='Helvetica-Bold',  
        fontSize=5,
        leading=6,
        alignment=1,
        textColor=colors.HexColor('#0000CC'),
        spaceBefore=0,
        spaceAfter=0
    )

    colonnes_avec_places = [2, 3, 5, 7, 9, 10, 12, 14, 16, 17, 19, 21, 23]
    places_injectees = 0

    for col in colonnes_avec_places:
        try:
            place = get_place_for_column(
                id_annee, id_campus, id_cycle, id_classe,
                id_eleve, col
            )
        except Exception:
            place = "-"

        ligne_place[col] = Paragraph(f"<font color='#0000CC'><b>{place}</b></font>", place_style)
        if place != "-":
            places_injectees += 1

    return places_injectees > 0


def create_notes_table(elements, style_center, style_normal, id_annee, id_campus, id_cycle, id_classe, id_eleve,
                       style_center_bold=None, style_normal_bold=None, rounded_values=False):
    # Fallback bold styles if not passed
    if style_center_bold is None:
        style_center_bold = ParagraphStyle(name='CenterSmallBoldFB', fontName='Helvetica-Bold', fontSize=5, leading=6, alignment=1)
    if style_normal_bold is None:
        style_normal_bold = ParagraphStyle(name='NormalSmallBoldFB', fontName='Helvetica-Bold', fontSize=5, leading=6, alignment=0)

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
        Paragraph("<b>BRANCHES</b>", style_center_bold),
        Paragraph(f"<b>{nom_trim1}</b>", style_center_bold), None, None, None, None, None, None,
        Paragraph(f"<b>{nom_trim2}</b>", style_center_bold), None, None, None, None, None, None,
        Paragraph(f"<b>{nom_trim3}</b>", style_center_bold), None, None, None, None, None, None,
        Paragraph("<b>TOTAL</b>", style_center_bold), None
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
    sous_header = [Paragraph("<b>BRANCHES</b>", style_center_bold)]
    for i in range(3):
        p1 = periodes_par_trim[i][0] if len(periodes_par_trim[i]) > 0 else "-"
        p2 = periodes_par_trim[i][1] if len(periodes_par_trim[i]) > 1 else "-"
        sous_header.extend([
            Paragraph("<b>Max per</b>", style_center_bold), Paragraph(f"<b>{p1}</b>", style_center_bold), Paragraph(f"<b>{p2}</b>", style_center_bold),
            Paragraph("<b>Max<br/>Exam</b>", style_center_bold), Paragraph("PTS.OBT", style_center),
            Paragraph("<b>MAX TRIM</b>", style_center_bold), Paragraph("<b>PTS.OBT</b>", style_center_bold),
        ])
    sous_header.extend([Paragraph("<b>MAX</b>", style_center_bold), Paragraph("<b>PTS.OBT</b>", style_center_bold)])
    table_data.append(sous_header)
    domaines_cours = get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe)
    notes_periodes = get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    notes_exam = get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    for groupe in domaines_cours:
        domaine_nom = groupe['domaine']
        row_domaine = [Paragraph(f"<b>{domaine_nom}</b>", style_center_bold)]
        table_data.append(row_domaine + [None] * 22)

        # Support sous-domaines: itérer par sous-domaine si disponible
        sous_domaines = groupe.get('sous_domaines', [{'nom': None, 'cours': groupe['cours']}])
        for sd in sous_domaines:
            # Afficher l'en-tête du sous-domaine s'il en a un
            if sd['nom']:
                row_sd = [Paragraph(f"<font color='#333'><i>{sd['nom']}</i></font>", style_center)]
                table_data.append(row_sd + [None] * 22)

            for cpc in sd['cours']:
                nom_cours = cpc.id_cours.cours
                # max_par_periode = maxima_tj / nombre_de_periodes (2 par trimestre)
                maxima_tj_val = cpc.maxima_tj if cpc.maxima_tj is not None else "-"
                if maxima_tj_val != "-":
                    ponderation = float(maxima_tj_val) / 2  # 2 périodes par trimestre
                    ponderation = int(ponderation) if ponderation == int(ponderation) else ponderation
                else:
                    ponderation = "-"
                max_exam = cpc.maxima_exam if cpc.maxima_exam is not None else "-"
                # Max Trim = maxima_tj (full) + maxima_exam
                if maxima_tj_val != "-" and max_exam != "-":
                    max_trim_val = float(maxima_tj_val) + float(max_exam)
                else:
                    max_trim_val = "-"
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
                    if col in [1, 8, 15]:          # Max per (bold)
                        row.append(Paragraph(str(ponderation), style_center_bold))
                    elif col in [4, 11, 18]:       # Max Exam (bold)
                        row.append(Paragraph(str(max_exam), style_center_bold))
                    elif col in [5, 12, 19]:       # PTS.OBT Exam
                        note_ex = exam_notes.get(col, "-")
                        # Echec examen: rouge si < 50% du max examen
                        echec_ex = False
                        if note_ex != "-" and max_exam != "-":
                            try:
                                echec_ex = float(note_ex) < float(max_exam) / 2
                            except (ValueError, TypeError):
                                pass
                        if echec_ex:
                            row.append(Paragraph(f"<font color='red'>{note_ex}</font>", style_center))
                        else:
                            row.append(Paragraph(str(note_ex), style_center))
                    elif col in [6, 13, 20]:       # MAX TRIM (bold)
                        row.append(Paragraph(str(max_trim_val), style_center_bold)) 
                    elif col == 22:                # MAX annuel (bold)
                        row.append(Paragraph(str(float(max_annee) if max_trim_val != "-" else "-"), style_center_bold))
                    elif col == 23:                # PTS.OBT annuel
                        row.append(Paragraph("-", style_center))
                    elif col in [2, 3, 9, 10, 16, 17]: # notes de période
                        note_val = notes_cours_periodes.get(col, "-")
                        # Echec période: rouge si < 50% du max PAR PÉRIODE
                        # ponderation = max par période (maxima_tj / 2)
                        # seuil d'échec = 50% du max par période = ponderation / 2
                        echec_p = False
                        if note_val != "-" and ponderation != "-":
                            try:
                                echec_p = float(note_val) < float(ponderation) / 2
                            except (ValueError, TypeError):
                                pass
                        if echec_p:
                            row.append(Paragraph(f"<font color='red'>{note_val}</font>", style_center))
                        else:
                            row.append(Paragraph(str(note_val), style_center))
                    else:
                        row.append(Paragraph("-", style_center))
                table_data.append(row)
        row_sous_total = [Paragraph("<b>Sous Total</b>", style_normal_bold)] + [None] * 22
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
        table_data.append([Paragraph(f"<b>{texte}</b>", style_normal_bold)] + [None] * 22)
    calculer_sous_totaux_et_maxima(table_data, style_center_bold)
    calculer_pts_obt_et_somme_finale(table_data, style_center)
    calculer_somme_pts_obt_maxima(table_data, style_center_bold)
    calculer_pourcentages(table_data, style_center_bold)
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

    # Post-processing : vider les colonnes non-délibérées
    blank_non_deliberated_columns(
        table_data, id_eleve, id_classe, trimestres_data,
        style_center, bulletin_type='primaire'
    )

    # ── Arrondi d'affichage (purement cosmétique, notes inchangées en base) ──
    if rounded_values:
        from MonEcole_app.views.rdc_structure import apply_rounded_values
        apply_rounded_values(table_data)

    num_rows = len(table_data)
    col_widths = [30*mm] + [7.4*mm] * 22

    # ── Hauteur dynamique : adapter à la page A4 pour rester sur 1 page ──
    # Éléments avant le tableau : header(~26mm) + NID(~6mm) + line2(~20mm) + title(~6mm) = ~58mm
    # Footer : spacer(1mm) + footer_table(~15mm) = ~16mm  |  Total hors-tableau ≈ 77mm
    # Page A4 portrait = 297mm, topMargin=0, bottomMargin=5mm → usable=292mm
    _page_h = 297 * mm
    _other_elements_h = 77 * mm   # header + NID + line2 + title + footer + spacers
    _bottom_margin = 5 * mm
    _available_h = _page_h - _bottom_margin - _other_elements_h
    _ideal_rh = 4.5 * mm
    _min_rh = 3 * mm

    if num_rows * _ideal_rh <= _available_h:
        _rh = [_ideal_rh] * num_rows
    elif num_rows * _min_rh <= _available_h:
        _rh = [_available_h / num_rows] * num_rows
    else:
        _rh = [_min_rh] * num_rows  # Minimum — may still be tight

    table = Table(table_data, colWidths=col_widths, rowHeights=_rh)
    
    # ── Colonnes structurelles (Max per, Max Exam, MAX TRIM) en gras ──
    # Colonnes maxima : 1,4,6,8,11,13,15,18,20,22 (vertical bold)
    cols_maxima_vert = [1, 4, 6, 8, 11, 13, 15, 18, 20, 22]
    
    table_style = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('SPAN', (0, 0), (0, 1)),
        ('SPAN', (1, 0), (7, 0)),
        ('SPAN', (8, 0), (14, 0)),
        ('SPAN', (15, 0), (21, 0)),
        ('SPAN', (22, 0), (23, 0)),
    ])

    # ── Gris foncé (hachage) pour colonnes structurelles ──
    gris_fonce = colors.Color(0.45, 0.45, 0.45)
    
    # Trouver dynamiquement les lignes MAXIMA, POURCENTAGE, PLACE, CONDUITE, etc.
    maxima_idx = None
    pourcentage_idx = None
    place_idx = None
    conduite_idx = None
    application_idx = None
    sig_institeur_idx = None
    sig_responsable_idx = None
    
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            if "MAXIMA GENEREAUX" in texte:
                maxima_idx = idx
            elif "POURCENTAGE" in texte:
                pourcentage_idx = idx
            elif "PLACE" in texte:
                place_idx = idx
            elif "CONDUITE" in texte:
                conduite_idx = idx
            elif "APPLICATION" in texte:
                application_idx = idx
            elif "INSTITEUR" in texte:
                sig_institeur_idx = idx
            elif "RESPONSABLE" in texte:
                sig_responsable_idx = idx

    # Colonnes structurelles (Max per, Max Exam, MAX TRIM) pour hachage
    # Pattern comme image 2: colonnes structurelles noires sur lignes finales
    colonnes_struct = [1, 4, 6, 8, 11, 13, 15, 18, 20]
    
    if maxima_idx is not None:
        # POURCENTAGE et PLACE : hachage sur colonnes Max per (1,8,15)
        for row_idx in [pourcentage_idx, place_idx]:
            if row_idx is not None:
                for col_idx in colonnes_struct:
                    if col_idx < len(table_data[row_idx]):
                        table_data[row_idx][col_idx] = None
                        table_style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), gris_fonce)

        # CONDUITE + APPLICATION : hachage sur TOUTES les colonnes sauf col 0 (label)
        for row_idx in [conduite_idx, application_idx]:
            if row_idx is not None:
                for col_idx in range(1, 24):
                    if col_idx < len(table_data[row_idx]):
                        table_data[row_idx][col_idx] = None
                        table_style.add('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), gris_fonce)

        # SIGNATURE DE L'INSTITEUR + RESPONSABLE : fusionner horizontalement
        for row_idx in [sig_institeur_idx, sig_responsable_idx]:
            if row_idx is not None:
                for col_idx in range(1, 23):
                    if col_idx < len(table_data[row_idx]):
                        table_data[row_idx][col_idx] = None
                table_style.add('SPAN', (0, row_idx), (-1, row_idx))

    # ── Fusion/Background dynamique des lignes de domaine et sous-domaine ──
    for ridx, row in enumerate(table_data):
        if ridx < 2 or not row or not row[0]:
            continue
        texte = str(row[0]) if row[0] else ""
        if not texte:
            continue
        # Détection ligne domaine: <b> tag, pas "Sous Total", pas les lignes finales
        is_domaine = ("<b>" in texte and "Sous Total" not in texte 
                      and "MAXIMA" not in texte and "POURCENTAGE" not in texte
                      and "PLACE" not in texte and "CONDUITE" not in texte
                      and "APPLICATION" not in texte and "SIGNATURE" not in texte)
        # Détection sous-domaine: <i> tag
        is_sous_domaine = "<i>" in texte and "<b>" not in texte
        
        if is_domaine:
            table_style.add('SPAN', (0, ridx), (-1, ridx))
            table_style.add('BACKGROUND', (0, ridx), (-1, ridx), colors.lightblue)
        elif is_sous_domaine:
            table_style.add('SPAN', (0, ridx), (-1, ridx))
            table_style.add('BACKGROUND', (0, ridx), (-1, ridx), colors.Color(0.85, 0.88, 0.95))  # lavender léger

    # ── Ligne PLACE : background bleu clair + texte bleu foncé + gras ──
    if place_idx is not None:
        table_style.add('BACKGROUND', (0, place_idx), (-1, place_idx), colors.Color(0.85, 0.92, 1.0))  # bleu clair
        table_style.add('TEXTCOLOR', (0, place_idx), (-1, place_idx), colors.HexColor('#0000CC'))
        table_style.add('FONTNAME', (0, place_idx), (-1, place_idx), 'Helvetica-Bold')

    # ── Ligne MAXIMA GENEREAUX : gras (via style déjà appliqué) ──
    if maxima_idx is not None:
        table_style.add('FONTNAME', (0, maxima_idx), (-1, maxima_idx), 'Helvetica-Bold')

    # ── Lignes Sous Total : gras ──
    for ridx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph):
            texte = row[0].text or ""
            if "Sous Total" in texte:
                table_style.add('FONTNAME', (0, ridx), (-1, ridx), 'Helvetica-Bold')

    # ── Post-traitement : notes < 50% du max ⇒ rouge ──
    import re
    for row_idx in range(2, len(table_data)):
        row = table_data[row_idx]
        if len(row) < 24:
            continue
        texte = str(row[0]) if row[0] else ""
        texte_upper = texte.upper()
        # Ignorer les lignes non-cours
        if any(mot in texte_upper for mot in [
            "APPLICATION", "MAXIMA", "POURCENTAGE",
            "PLACE", "CONDUITE", "SIGNATURE", "SOUS TOTAL", "BRANCHES"
        ]):
            continue
        if "<b>" in texte and "SOUS TOTAL" not in texte_upper and len(texte) > 20:
            continue  # Ligne domaine

        # PTS.OBT trimestriels: col 7 vs max col 6, col 14 vs max col 13, col 21 vs max col 20
        for pts_col, max_col in [(7, 6), (14, 13), (21, 20)]:
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

        # PTS.OBT annuel: col 23 vs max col 22
        try:
            pts_txt = str(row[23]) if row[23] else ""
            max_txt = str(row[22]) if row[22] else ""
            pts_nums = re.findall(r'[\d.]+', pts_txt)
            max_nums = re.findall(r'[\d.]+', max_txt)
            if pts_nums and max_nums:
                pts_val = float(pts_nums[-1])
                max_val = float(max_nums[-1])
                if max_val > 0 and pts_val < max_val / 2:
                    row[23] = Paragraph(f"<font color='red'><b>{pts_nums[-1]}</b></font>", style_center)
        except:
            pass

    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 0.5*mm))



def create_footer(elements, style_normal, style_center, id_classe=None, etab_url=''):
    """Footer matching official RDC bulletin format."""
    elements.append(Spacer(1, 1*mm))  # Detach footer from content
    # Retrieve institution info for dynamic footer
    chef_nom = ""
    ville = ""
    ecole_nom = ""
    if id_classe:
        try:
            _eac = EtablissementAnneeClasse.objects.select_related('etablissement_annee').get(id=id_classe)
            etab_id = _eac.etablissement_annee.etablissement_id
            from django.db import connections
            with connections['countryStructure'].cursor() as cur:
                cur.execute(
                    "SELECT nom, representant, emplacement, url FROM etablissements WHERE id_etablissement = %s",
                    [etab_id]
                )
                row = cur.fetchone()
                if row:
                    ecole_nom = row[0] or ""
                    chef_nom = row[1] or ""
                    ville = row[2] or ""
                    if not etab_url and row[3]:
                        etab_url = row[3]
        except Exception:
            pass

    style_footer = ParagraphStyle(name='FooterText', fontSize=4, leading=5, alignment=0, fontName='Times-Roman')
    style_footer_center = ParagraphStyle(name='FooterCenter', fontSize=4, leading=5, alignment=1, fontName='Times-Roman')
    style_footer_right = ParagraphStyle(name='FooterRight', fontSize=4, leading=5, alignment=0, fontName='Times-Roman')
    style_footer_bold = ParagraphStyle(name='FooterBold', fontSize=4, leading=5, alignment=0, fontName='Times-Bold')

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

    # Build the footer table
    footer_data = [
        [repechage_line, None, None],
        [left_col, center_col, right_col],
        [note_line, None, None],
    ]
    footer_table = Table(footer_data, colWidths=[70*mm, 50*mm, 70*mm])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0, 0), (2, 0)),   # repêchage line spans full width
        ('SPAN', (0, 2), (2, 2)),   # note line spans full width
        ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(footer_table)


def create_footer_8eme(elements, style_normal, style_center, id_classe=None, etab_url=''):
    """Footer for 8ème année (Education de Base) — includes RESULTAT FINAL section."""
    elements.append(Spacer(1, 0.5*mm))

    # Retrieve institution info
    chef_nom = ""
    ville = ""
    if id_classe:
        try:
            _eac = EtablissementAnneeClasse.objects.select_related('etablissement_annee').get(id=id_classe)
            etab_id = _eac.etablissement_annee.etablissement_id
            from django.db import connections
            with connections['countryStructure'].cursor() as cur:
                cur.execute(
                    "SELECT nom, representant, emplacement, url FROM etablissements WHERE id_etablissement = %s",
                    [etab_id]
                )
                row = cur.fetchone()
                if row:
                    chef_nom = row[1] or ""
                    ville = row[2] or ""
                    if not etab_url and row[3]:
                        etab_url = row[3]
        except Exception:
            pass

    style_ft = ParagraphStyle(name='Ft8', fontSize=5, leading=7, alignment=0, fontName='Helvetica')
    style_ft_c = ParagraphStyle(name='Ft8C', fontSize=5, leading=7, alignment=1, fontName='Helvetica')
    style_ft_r = ParagraphStyle(name='Ft8R', fontSize=5, leading=7, alignment=0, fontName='Helvetica')

    import datetime
    date_str = datetime.date.today().strftime('%d/%m/%Y')
    fait_a = f"Fait à {ville} le <b>{date_str}</b>" if ville else f"Fait le <b>{date_str}</b>"

    # ── Row 0: Repêchage ──
    repechage = Paragraph(
        "L'élève ne pourra pas passer dans la classe supérieure s'il n'a pas subi avec succès "
        "un examen de repêchage en .........................................................................",
        style_ft
    )

    # ── RESULTAT FINAL table ──
    rf_s = ParagraphStyle(name='RFS', fontSize=5, leading=6, alignment=1, fontName='Helvetica-Bold')
    rf_c = ParagraphStyle(name='RFC2', fontSize=5, leading=6, alignment=1, fontName='Helvetica')

    resultat_data = [
        [Paragraph("<b>RESULTAT</b>", rf_s), Paragraph("<b>POINTS</b>", rf_s), Paragraph("<b>MAX</b>", rf_s)],
        [Paragraph("<b>FINAL</b>", rf_s), Paragraph("<b>OBT.</b>", rf_s), None],
        [Paragraph("MOYENNE ECOLE", rf_c), None, Paragraph("50", rf_c)],
        [Paragraph("ENAFEP", rf_c), None, Paragraph("50", rf_c)],
        [Paragraph("TOTAL", rf_c), None, Paragraph("100", rf_c)],
    ]
    resultat_table = Table(resultat_data, colWidths=[22*mm, 14*mm, 10*mm], rowHeights=[4*mm]*5)
    resultat_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.3, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('SPAN', (0, 0), (0, 1)),
    ]))

    # ── Passe/Double ──
    passe_double = Paragraph(
        "L'élève passe dans la classe supérieure (1)<br/>"
        "L'élève double la classe (1)",
        style_ft
    )

    # ── Nom et Signature (right-aligned, detached) ──
    nom_signature = Paragraph(
        f"Nom et Signature<br/>"
        f"<b>{chef_nom}</b>",
        style_ft_r
    )

    # ── Notes de bas ──
    note_biffer = Paragraph("(1): Biffer la mention inutile", style_ft)
    note_importante = Paragraph(
        "<b>NOTE IMPORTANTE</b>: Le bulletin est sans importance s'il est raturé ou surchargé",
        style_ft
    )

    # Build footer table — 6 rows matching official layout
    footer_data = [
        # Row 0: Repêchage (full width)
        [repechage, None, None],
        # Row 1: Resultat table | Sceau | Fait à + Chef
        [resultat_table,
         Paragraph("<b>Sceau de l'école</b>", style_ft_c),
         Paragraph(f"{fait_a}<br/>Le chef d'Établissement", style_ft_r)],
        # Row 2: Passe/Double (left) | empty | empty
        [passe_double, None, None],
        # Row 3: empty | empty | Nom et Signature (right)
        [None, None, nom_signature],
        # Row 4: Biffer (full width)
        [note_biffer, None, None],
        # Row 5: NOTE IMPORTANTE (full width)
        [note_importante, None, None],
    ]
    footer_table = Table(footer_data, colWidths=[65*mm, 55*mm, 80*mm])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        # Spans for full-width rows
        ('SPAN', (0, 0), (2, 0)),  # repêchage
        ('SPAN', (0, 2), (2, 2)),  # passe/double
        ('SPAN', (0, 4), (2, 4)),  # biffer
        ('SPAN', (0, 5), (2, 5)),  # note importante
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 1*mm),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5*mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        # Line below repêchage
        ('LINEBELOW', (0, 0), (-1, 0), 0.3, colors.black),
    ]))
    elements.append(footer_table)


def draw_border(canvas, doc, eleve, margin, watermark_path=None, is_eschool=False, etab_url=''):
    canvas.setLineWidth(0.5)
    canvas.rect(margin, margin, A4[0] - 2 * margin, A4[1] - 2 * margin)
    page_w, page_h = A4
    # Watermark: armoirie du pays en filigrane au centre
    if watermark_path and os.path.exists(watermark_path):
        canvas.saveState()
        canvas.setFillAlpha(0.15)
        wm_size = 140 * mm
        x = (page_w - wm_size) / 2
        y = (page_h - wm_size) / 2
        canvas.drawImage(watermark_path, x, y, width=wm_size, height=wm_size,
                         preserveAspectRatio=True, mask='auto')
        canvas.restoreState()
    # Filigrane diagonal texte (dessiné AU-DESSUS de l'armoire)
    canvas.saveState()
    wm_text = "BULLETIN ORIGINAL" if is_eschool else "COPIE CONFORME"
    diagonal = (page_w**2 + page_h**2) ** 0.5
    target_width = diagonal * 0.40
    wm_font_size = 45
    wm_font = 'Helvetica-Bold'
    canvas.setFont(wm_font, wm_font_size)
    canvas.setFillColor(colors.HexColor('#4A6FA5'))
    canvas.setFillAlpha(0.28)
    canvas.translate(page_w / 2, page_h / 2)
    canvas.rotate(45)
    # Dessiner chaque caractère avec espacement pour couvrir 60% de la diagonale
    char_widths = [canvas.stringWidth(c, wm_font, wm_font_size) for c in wm_text]
    total_natural = sum(char_widths)
    num_chars = len(wm_text)
    extra_space = (target_width - total_natural) / max(num_chars - 1, 1) if num_chars > 1 else 0
    x_start = -target_width / 2
    for i, ch in enumerate(wm_text):
        canvas.drawString(x_start, 0, ch)
        x_start += char_widths[i] + (extra_space if i < num_chars - 1 else 0)
    canvas.restoreState()
    # Branding collé à la bordure basse du cadre (à l'intérieur)
    canvas.saveState()
    y_brand = margin + 1.2 * mm
    brand_url = f"https://{etab_url}" if etab_url and '.' in etab_url else "https://monecole.pro"
    parts = [
        ("Bulletin g\xe9n\xe9r\xe9 par ", 'Helvetica', 4.5, colors.black),
        ("MonEkole", 'Helvetica-Bold', 4.5, colors.HexColor('#0000CC')),
        (f" ({brand_url})", 'Helvetica', 4.5, colors.black),
        (" et Authentifi\xe9 par ", 'Helvetica', 4.5, colors.black),
        ("eSchoolRDC", 'Helvetica-Bold', 4.5, colors.HexColor('#0000CC')),
        (" (https://eschool-rdc.pro)", 'Helvetica', 4.5, colors.black),
    ]
    total_w = sum(canvas.stringWidth(t, f, s) for t, f, s, _ in parts)
    x_brand = (page_w - total_w) / 2
    for text, font, size, color in parts:
        canvas.setFont(font, size)
        canvas.setFillColor(color)
        canvas.drawString(x_brand, y_brand, text)
        x_brand += canvas.stringWidth(text, font, size)
    canvas.restoreState()
    # QR code
    qr_value = f"G\xe9n\xe9r\xe9 par  MonEkole App,ce Bulletin est de : {eleve.nom}{eleve.prenom} Con\xe7ue par entreprise ICT Group"
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
