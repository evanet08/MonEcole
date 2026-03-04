# views.py
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from library_manager.models import Emprunt, Livre,Categorie
from MonEcole_app.models import Institution, Classe_cycle_actif, Classe_active, Eleve
from django.db.models import Count
from datetime import datetime
import os
from django.conf import settings
from MonEcole_app.views.decorators.decorators import module_required
from MonEcole_app.views.tools.utils import get_user_info
from django.shortcuts import render,redirect



@login_required
@module_required("Bibliotheque")
def home_emprunt_most(request):
    user_info = get_user_info(request)
    user_modules = user_info
    most_land_form = True
    return render(request,'library/index_library.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name'],
                    "most_land_form":most_land_form,
                    
                     })
    
    
@login_required
@module_required("Bibliotheque")
def home_emprunt_byPeriod_land(request):
    user_info = get_user_info(request)
    user_modules = user_info
    periode_land_form = True
    return render(request,'library/index_library.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name'],
                    "periode_land_form":periode_land_form,
                     })


@login_required
@module_required("Bibliotheque")
def home_emprunt_byEleve_land(request):
    user_info = get_user_info(request)
    user_modules = user_info
    eleve_land_form = True
    return render(request,'library/index_library.html',
                   {"photo_profil":user_modules['photo_profil'],
                    "modules": user_modules['modules'],
                    "last_name": user_modules['last_name'],
                    "eleve_land_form":eleve_land_form,
                     })




@login_required
@module_required("Bibliotheque")
def emprunt_books_cycle(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    emprunts = Emprunt.objects.select_related(
        'id_livre', 'id_eleve', 'id_classe_active', 'id_cycle_actif'
    ).all()
    if start_date:
        emprunts = emprunts.filter(date_retour_prevue__gte=start_date)
    if end_date:
        emprunts = emprunts.filter(date_retour_prevue__lte=end_date)

    cycles = Classe_cycle_actif.objects.values('cycle_id').distinct()
    data_by_cycle = {}
    
    for cycle in cycles:
        cycle_id = cycle['cycle_id']  
        cycle_instances = Classe_cycle_actif.objects.filter(cycle_id=cycle_id)
        cycle_emprunts = emprunts.filter(id_cycle_actif__in=cycle_instances)
        
        if cycle_emprunts.exists():
            classes = Classe_active.objects.filter(
                id_classe_active__in=cycle_emprunts.values('id_classe_active').distinct()
            )
            data_by_cycle[cycle_id] = {}
            
            for classe in classes:
                classe_emprunts = cycle_emprunts.filter(id_classe_active=classe)
                eleves = Eleve.objects.filter(
                    id_eleve__in=classe_emprunts.values('id_eleve').distinct()
                )
                data_by_cycle[cycle_id][classe] = [
                    {
                        'eleve': f"{eleve.nom} {eleve.prenom}",
                        'livre': emprunt.id_livre.titre,
                        'date_retour': emprunt.date_retour_prevue.strftime('%d/%m/%Y')
                    }
                    for eleve in eleves
                    for emprunt in classe_emprunts.filter(id_eleve=eleve)
                ]

    summary_data = []
    for cycle_id, classes in data_by_cycle.items():
        cycle_total = sum(len(emprunts) for emprunts in classes.values())
        try:
            cycle_obj = Classe_cycle_actif.objects.filter(cycle_id=cycle_id).first()
            cycle_name = cycle_obj.cycle_id.cycle if cycle_obj and hasattr(cycle_obj.cycle_id, 'cycle') else cycle_id
        except:
            cycle_name = cycle_id  
        summary_data.append({
            'cycle': cycle_name,
            'classes': [
                {
                    'nom': f"{classe.classe_id.classe}{f' ({classe.groupe})' if classe.groupe else ''}",
                    'total': len(classes[classe])
                }
                for classe in classes
            ],
            'total_cycle': cycle_total
        })

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_emprunts_par_cycle.pdf"'

    doc = SimpleDocTemplate(
        response, pagesize=A4, rightMargin=0.5*inch, leftMargin=0.5*inch,
        topMargin=0.5*inch, bottomMargin=0.5*inch
    )
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='Title', fontSize=16, leading=20, alignment=1,
        spaceAfter=10, fontName='Helvetica-Bold', underline=True
    )
    subtitle_style = ParagraphStyle(
        name='Subtitle', fontSize=12, leading=15, alignment=1,
        spaceAfter=10, fontName='Helvetica', underline=True
    )
    normal_style = styles['Normal']
    section_style = ParagraphStyle(
        name='Section', fontSize=12, leading=15, spaceBefore=10,
        spaceAfter=5, fontName='Helvetica-Bold'
    )

    institution = Institution.objects.first()
    logo_cell = []
    if institution and institution.logo_ecole:
        logo_ecole_path = os.path.join(settings.MEDIA_ROOT, institution.logo_ecole.name)
        if os.path.exists(logo_ecole_path):
            logo = Image(logo_ecole_path, width=0.8*inch, height=0.8*inch)
            logo_cell.append(logo)
        else:
            logo_cell.append(Paragraph("Logo non disponible", normal_style))
    else:
        logo_cell.append(Paragraph("Aucun logo configuré", normal_style))

    institution_name = institution.nom_ecole if institution else "Bibliothèque"
    institution_paragraph = Paragraph(f"<font color='black'><b>{institution_name}</b></font>", normal_style)

    header_table = Table([[logo_cell, institution_paragraph]], colWidths=[1.5*inch, 6*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(header_table)

    title = Paragraph(f"<font color='black'><b>Rapport des emprunts par cycle</b></font>", title_style)
    subtitle_text = f"Fait le {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if start_date or end_date:
        subtitle_text += "<br/>Période : "
        if start_date:
            subtitle_text += f"Du {start_date} "
        if end_date:
            subtitle_text += f"au {end_date}"
    subtitle = Paragraph(subtitle_text, subtitle_style)
    elements.extend([Spacer(1, 0.25*inch), title, subtitle, Spacer(1, 0.25*inch)])

    for cycle_id, classes in data_by_cycle.items():
        try:
            cycle_obj = Classe_cycle_actif.objects.filter(cycle_id=cycle_id).first()
            cycle_name = cycle_obj.cycle_id.cycle if cycle_obj and hasattr(cycle_obj.cycle_id, 'cycle') else cycle_id
        except:
            cycle_name = cycle_id
        elements.append(Paragraph(f"Cycle : {cycle_name}", section_style))
        elements.append(Spacer(1, 0.15*inch))

        for classe, emprunts in classes.items():
            classe_nom = f"{classe.classe_id.classe}{f' ({classe.groupe})' if classe.groupe else ''}"
            elements.append(Paragraph(f"Classe : {classe_nom}", normal_style))
            elements.append(Spacer(1, 0.1*inch))

            data = [['Élève', 'Livre', 'Date de retour']]
            for emprunt in emprunts:
                data.append([
                    emprunt['eleve'][:25] + ('...' if len(emprunt['eleve']) > 25 else ''),
                    emprunt['livre'][:30] + ('...' if len(emprunt['livre']) > 30 else ''),
                    emprunt['date_retour']
                ])

            table = Table(data, colWidths=[2.5*inch, 3*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.2*inch))

    elements.append(Paragraph("Résumé des emprunts par cycle et classe", section_style))
    elements.append(Spacer(1, 0.15*inch))
    summary_table_data = [['Cycle', 'Classe', 'Nombre d’emprunts']]
    for cycle_data in summary_data:
        for classe in cycle_data['classes']:
            summary_table_data.append([
                cycle_data['cycle'],
                classe['nom'],
                str(classe['total'])
            ])
        summary_table_data.append([
            f"Total {cycle_data['cycle']}",
            '',
            str(cycle_data['total_cycle'])
        ])

    summary_table = Table(summary_table_data, colWidths=[2.5*inch, 3*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)

    doc.build(elements)
    return response

@login_required
def generate_books_most_used_report(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    emprunts = Emprunt.objects.select_related('id_livre__categorie').all()
    if start_date:
        emprunts = emprunts.filter(date_emprunt__gte=start_date)
    if end_date:
        emprunts = emprunts.filter(date_emprunt__lte=end_date)

    total_emprunts_available = emprunts.count()
    is_limited = total_emprunts_available > 1000

    emprunts_summary = (
        emprunts.values('id_livre__titre', 'id_livre__auteur', 'id_livre__categorie__nom')
        .annotate(total_emprunts=Count('id_livre'))
        .order_by('-total_emprunts')[:1000] 
    )

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_livres_plus_empruntes.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='Title',
        fontSize=16,
        leading=20,
        alignment=1,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        underline=True
    )
    subtitle_style = ParagraphStyle(
        name='Subtitle',
        fontSize=12,
        leading=15,
        alignment=1,
        spaceAfter=10,
        fontName='Helvetica',
        underline=True
    )
    normal_style = styles['Normal']

    institution = Institution.objects.first()
    logo_cell = []
    if institution and institution.logo_ecole:
        logo_ecole_path = os.path.join(settings.MEDIA_ROOT, institution.logo_ecole.name)
        if os.path.exists(logo_ecole_path):
            logo = Image(logo_ecole_path, width=0.8*inch, height=0.8*inch)
            logo_cell.append(logo)
        else:
            logo_cell.append(Paragraph("Logo non disponible", normal_style))
    else:
        logo_cell.append(Paragraph("Aucun logo configuré", normal_style))

    institution_name = institution.nom_ecole if institution else "Bibliothèque"
    institution_paragraph = Paragraph(f"<font color='black'><b>{institution_name}</b></font>", normal_style)
    

    header_table = Table([[logo_cell, institution_paragraph]], colWidths=[1.5*inch, 6*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(header_table)

    title = Paragraph("Rapport des livres par ordre de plus au moins empruntés/période", title_style)
    # subtitle_text = f"Fait le {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    subtitle_text = f"Fait le {datetime.now().strftime('%d-%m-%Y %H:%M')}"
    if start_date or end_date:
        subtitle_text += "<br/>Période : "
        if start_date:
            subtitle_text += f"Du {start_date} "
        if end_date:
            subtitle_text += f"au {end_date}"
    subtitle = Paragraph(subtitle_text, subtitle_style)
    elements.extend([Spacer(1, 0.25*inch), title, subtitle, Spacer(1, 0.25*inch)])

    data = [['No', 'Titre', 'Auteur', 'Catégorie', 'Emprunts']]
    for index, emprunt in enumerate(emprunts_summary, start=1):
        data.append([
            str(index),
            emprunt['id_livre__titre'][:30] + ('...' if len(emprunt['id_livre__titre']) > 30 else ''),
            emprunt['id_livre__auteur'][:20] + ('...' if len(emprunt['id_livre__auteur']) > 20 else ''),
            emprunt['id_livre__categorie__nom'][:20] or 'Non spécifié',
            str(emprunt['total_emprunts'])
        ])

    table = Table(data, colWidths=[0.5*inch, 2.5*inch, 2*inch, 1.5*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    total_emprunts = sum(emprunt['total_emprunts'] for emprunt in emprunts_summary)
    total_livres = len(emprunts_summary)
    summary = Paragraph(
        f"<br/>Résumé : {total_livres} livres uniques empruntés pour un total de {total_emprunts} emprunts.",
        normal_style
    )
    elements.extend([Spacer(1, 0.25*inch), summary])

    if is_limited:
        warning = Paragraph("Attention : Seuls les 1000 premiers emprunts sont pris en compte.", normal_style)
        elements.append(Spacer(1, 0.15*inch))
        elements.append(warning)

    doc.build(elements)
    return response


@login_required
def emprunt_books_per_periode_all_pupils(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    emprunts = Emprunt.objects.select_related('id_eleve', 'id_livre').all()
    if start_date:
        emprunts = emprunts.filter(date_emprunt__gte=start_date)
    if end_date:
        emprunts = emprunts.filter(date_emprunt__lte=end_date)

    total_emprunts_available = emprunts.count()
    is_limited = total_emprunts_available > 1000

    eleve_ids = Emprunt.objects.filter(id__in=emprunts).values('id_eleve').distinct()
    eleves = Eleve.objects.filter(id_eleve__in=eleve_ids)

    data_by_eleve = {}
    total_emprunts_count = 0
    for eleve in eleves:
        eleve_emprunts = emprunts.filter(id_eleve=eleve).order_by('date_emprunt')
        if total_emprunts_count + len(eleve_emprunts) > 1000:
            eleve_emprunts = eleve_emprunts[:1000 - total_emprunts_count]
        if eleve_emprunts:
            data_by_eleve[eleve] = [
                {
                    'livre': emprunt.id_livre.titre,
                    'date_emprunt': emprunt.date_emprunt.strftime('%d-%m-%Y'),
                    
                    'date_retour_effective': emprunt.date_retour_effective.strftime('%d-%m-%Y') if emprunt.date_retour_effective else 'Non rendu',
                    'rendu': 'Oui' if emprunt.rendu else 'Non'
                }
                for emprunt in eleve_emprunts
            ]
            total_emprunts_count += len(eleve_emprunts)
        if total_emprunts_count >= 1000:
            break
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport_emprunts_par_eleve.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='Title',
        fontSize=16,
        leading=20,
        alignment=1,
        spaceAfter=10,
        fontName='Helvetica-Bold',
        underline=True
    )
    subtitle_style = ParagraphStyle(
        name='Subtitle',
        fontSize=12,
        leading=15,
        alignment=1,
        spaceAfter=10,
        fontName='Helvetica',
        underline=True
    )
    normal_style = styles['Normal']

    institution = Institution.objects.first()
    logo_cell = []
    if institution and institution.logo_ecole:
        logo_ecole_path = os.path.join(settings.MEDIA_ROOT, institution.logo_ecole.name)
        if os.path.exists(logo_ecole_path):
            logo = Image(logo_ecole_path, width=0.8*inch, height=0.8*inch)
            logo_cell.append(logo)
        else:
            logo_cell.append(Paragraph("Logo non disponible", normal_style))
    else:
        logo_cell.append(Paragraph("Aucun logo configuré", normal_style))

    institution_name = institution.nom_ecole if institution else "Bibliothèque"
    institution_paragraph = Paragraph(f"<font color='black'><b>{institution_name}</b></font>", normal_style)
    

    header_table = Table([[logo_cell, institution_paragraph]], colWidths=[1.5*inch, 6*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(header_table)

    title = Paragraph("Rapport des emprunts et  retour", title_style)
    subtitle_text = f"Fait le {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    if start_date or end_date:
        subtitle_text += "<br/>Période : "
        if start_date:
            subtitle_text += f"Du {start_date} "
        if end_date:
            subtitle_text += f"au {end_date}"
    subtitle = Paragraph(subtitle_text, subtitle_style)
    elements.extend([Spacer(1, 0.25*inch), title, subtitle, Spacer(1, 0.25*inch)])

    data = [['Élève', 'Livre', 'Date d’emprunt', 'Date de retour', 'Rendu']]
    row_index = 1  
    for eleve, emprunts in data_by_eleve.items():
        if not emprunts:
            continue
        nom_complet = f"{eleve.nom} {eleve.prenom}"[:25] + ('...' if len(f"{eleve.nom} {eleve.prenom}") > 25 else '')
        data.append([
            nom_complet,
            emprunts[0]['livre'][:25] + ('...' if len(emprunts[0]['livre']) > 25 else ''),
            emprunts[0]['date_emprunt'],
            emprunts[0]['date_retour_effective'],
            emprunts[0]['rendu']
        ])
        for emprunt in emprunts[1:]:
            data.append([
                '',  
                emprunt['livre'][:25] + ('...' if len(emprunt['livre']) > 25 else ''),
                emprunt['date_emprunt'],
                emprunt['date_retour_effective'],
                emprunt['rendu']
            ])

    table = Table(data, colWidths=[2.6*inch, 1.7*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ])

    current_row = 1
    for eleve, emprunts in data_by_eleve.items():
        if not emprunts:
            continue
        num_rows = len(emprunts)
        if num_rows > 1:
            table_style.add('SPAN', (0, current_row), (0, current_row + num_rows - 1))
        current_row += num_rows

    table.setStyle(table_style)
    elements.append(table)

    total_emprunts = sum(len(emprunts) for emprunts in data_by_eleve.values())
    total_eleves = len([e for e, emprunts in data_by_eleve.items() if emprunts])
    summary = Paragraph(
        f"<br/>Résumé : {total_emprunts} emprunts effectués par {total_eleves} élèves.",
        normal_style
    )
    elements.extend([Spacer(1, 0.25*inch), summary])

    if is_limited:
        warning = Paragraph("Attention : Seuls les 1000 premiers emprunts sont affichés.", normal_style)
        elements.append(Spacer(1, 0.15*inch))
        elements.append(warning)

    doc.build(elements)
    return response