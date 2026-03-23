

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from MonEcole_app.models import Paiement, Institution,Eleve_inscription,Campus,Eleve,Classe_active,Classe_cycle_actif,Annee
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.pagesizes import A4
import os
from django.conf import settings
import logging
from datetime import datetime
from MonEcole_app.views.tools.tenant_utils import validate_campus_access



@login_required
def generate_invoice(request, id_paiement):
    try:
 
        paiement = Paiement.objects.select_related(
            'id_campus', 'id_cycle_actif', 'id_classe_active', 'id_annee', 'id_variable', 'id_eleve'
        ).get(id_paiement=id_paiement)

        # Validation tenant
        if not validate_campus_access(request, paiement.id_campus_id):
            return HttpResponse("Erreur : Accès interdit à ce paiement.", status=403)

        institution = Institution.objects.first()  
        if not institution:
            return HttpResponse("Erreur : Institution non trouvée.", status=404)

      
        campus = paiement.id_campus.campus
        cycle = paiement.id_cycle_actif.cycle_id.cycle
        classe = paiement.id_classe_active.classe_id.classe
        groupe = paiement.id_classe_active.groupe or ''
        annee = f"{paiement.id_annee.annee}"
        variable = paiement.id_variable.variable
        montant = f"{paiement.montant} Fbu"
        eleve = f"{paiement.id_eleve.nom} {paiement.id_eleve.prenom}"
        date_generation = datetime.now().strftime("%d/%m/%Y %H:%M")
        encaisseur = request.user.get_full_name() or request.user.username

     
        page_width = 100 * mm
        page_height = 150 * mm
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture_{id_paiement}.pdf"'
        doc = SimpleDocTemplate(response, pagesize=(page_width, page_height), rightMargin=5*mm, leftMargin=5*mm, topMargin=5*mm, bottomMargin=5*mm)


        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(name='Normal', fontSize=8, leading=10, wordWrap='CJK') 
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ])

       
        elements = []

      
        logo_cell = []
        if institution and institution.logo_ecole:
            logo_ecole_path = os.path.join(settings.MEDIA_ROOT, institution.logo_ecole.name)
            if os.path.exists(logo_ecole_path):
                logo = Image(logo_ecole_path, width=0.8 * inch, height=0.8 * inch)
                logo_cell.append(logo)
            else:
                logo_cell.append(Paragraph("Logo non disponible", normal_style))
        else:
            logo_cell.append(Paragraph("Aucun logo configuré", normal_style))

       
        classe_info = f"{classe} {groupe}".strip() if groupe else classe
        
        info_text = (
            f"Campus: <font color='black'><b>{campus}</b></font><br/>"
            f"Cycle: <font color='black'><b>{cycle}</b></font><br/>"
            f"Classe: <font color='black'><b>{classe_info}</b></font><br/>"
            f"Année scolaire: <font color='black'><b>{annee}</b></font><br/>"
            f"Elève: <font color='black'><b>{eleve}</b></font><br/>"
            f"Date: <font color='black'><b>{date_generation}</b></font>"
        )
        
       
        info_paragraph = Paragraph(info_text, normal_style)

       
        header_table = Table([
            [info_paragraph, logo_cell]
        ], colWidths=[60*mm, 30*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)

       
        variable_length = len(variable)
        if variable_length > 30:  
            variable_col_width = min(65*mm, page_width - 25*mm)  
            montant_col_width = page_width - variable_col_width - 10*mm  
        else:
            variable_col_width = 50*mm
            montant_col_width = 40*mm

        data = [
            ["Variable", "Montant"],
            [Paragraph(variable, normal_style), montant] 
        ]
        table = Table(data, colWidths=[variable_col_width, montant_col_width])
        table.setStyle(table_style)
        elements.append(Spacer(1, 10*mm))
        elements.append(table)

        encaisseur_text = Paragraph(f"Encaissé par: {encaisseur}", ParagraphStyle(name='Encaisseur', fontSize=8, alignment=2))
        elements.append(Spacer(1, 10*mm))
        elements.append(encaisseur_text)
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph("Signature: ____________________", ParagraphStyle(name='Signature', fontSize=8, alignment=2)))

        doc.build(elements)
        return response

    except Paiement.DoesNotExist:
        return HttpResponse("Erreur : Paiement non trouvé.", status=404)
    except Exception as e:
        return HttpResponse(f"Erreur serveur : {str(e)}", status=500)
    


def build_page_number(canvas, doc):
    """Ajoute la numérotation des pages en bas à droite."""
    page_num = canvas.getPageNumber()
    text = f"Page {page_num}"
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(doc.width + doc.rightMargin, doc.bottomMargin, text)

@login_required
def generate_fiche_paie_classe(request):
    try:
        id_campus = request.GET.get('id_campus')
        id_cycle = request.GET.get('id_cycle')
        id_classe_active = request.GET.get('id_classe_active')
        id_annee = request.GET.get('id_annee')

        if not all([id_campus, id_cycle, id_classe_active, id_annee]):
            return HttpResponse("Erreur : Paramètres requis manquants.", status=400)

        # Tenant validation
        if not validate_campus_access(request, id_campus):
            return HttpResponse("Erreur : Accès interdit à ce campus.", status=403)

        inscriptions = Eleve_inscription.objects.filter(
            id_campus_id=id_campus,
            id_classe_cycle_id=id_cycle,
            id_classe_id=id_classe_active,
            id_annee_id=id_annee,
            status=1
        ).select_related('id_eleve').values('id_eleve__id_eleve', 'id_eleve__nom', 'id_eleve__prenom').distinct()

        if not inscriptions.exists():
            return HttpResponse("Erreur : Aucune inscription validée trouvée.", status=404)

        variables = Paiement.objects.filter(
            id_campus_id=id_campus,
            id_cycle_actif_id=id_cycle,
            id_classe_active_id=id_classe_active,
            id_annee_id=id_annee,
            status=True
        ).values('id_variable__variable').distinct()[:4]

        variable_names = [v['id_variable__variable'] for v in variables]
        if not variable_names:
            return HttpResponse("Erreur : Aucun paiement validé trouvé pour cette combinaison.", status=404)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="fiche_paie_classe_{id_annee}_{id_classe_active}.pdf"'
        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            rightMargin=10*mm,
            leftMargin=10*mm,
            topMargin=10*mm,
            bottomMargin=15*mm
        )

        styles = getSampleStyleSheet()
        normal_style = ParagraphStyle(name='Normal', fontSize=8, leading=10, wordWrap='CJK')
        title_style = ParagraphStyle(name='Title', fontSize=12, leading=14, spaceAfter=10, alignment=1)
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('SPAN', (0, -1), (1, -1)),  
        ])

        elements = []

        institution = Institution.objects.first()
        logo_cell = []
        if institution and institution.logo_ecole:
            logo_ecole_path = os.path.join(settings.MEDIA_ROOT, institution.logo_ecole.name)
            if os.path.exists(logo_ecole_path):
                logo = Image(logo_ecole_path, width=0.8 * inch, height=0.8 * inch)
                logo_cell.append(logo)
            else:
                logo_cell.append(Paragraph("Logo non disponible", normal_style))
        else:
            logo_cell.append(Paragraph("Aucun logo configuré", normal_style))

        try:
            annee = Annee.objects.get(id_annee=id_annee).annee
            campus = Campus.objects.get(id_campus=id_campus).campus
            cycle = Classe_cycle_actif.objects.get(id_campus=id_campus, id_annee=id_annee, id_cycle_actif=id_cycle, is_active=True).cycle_id.cycle
            classe = Classe_active.objects.get(id_campus=id_campus, id_annee=id_annee, cycle_id=id_cycle, id_classe_active=id_classe_active, is_active=True)
            classe_info = f"{classe.classe_id.classe} {classe.groupe}".strip() if classe.groupe else classe.classe_id.classe
        except Exception as e:
            return HttpResponse(f"Erreur : Données de classe non trouvées.", status=404)

        info_text = (
            f"Campus: <font color='black'><b>{campus}</b></font><br/>"
            f"Cycle: <font color='black'><b>{cycle}</b></font><br/>"
            f"Classe: <font color='black'><b>{classe_info}</b></font><br/>"
            f"Année scolaire: <font color='black'><b>{annee}</b></font><br/>"
            f"Date: <font color='black'><b>{datetime.now().strftime('%d/%m/%Y %H:%M')}</b></font>"
        )
        info_paragraph = Paragraph(info_text, normal_style)

        header_table = Table([[info_paragraph, logo_cell]], colWidths=[120*mm, 70*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)

        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(f"<font color='black'><b>Situation des paiements effectués</b></font>", title_style))
        
        elements.append(Spacer(1, 10*mm))

        data = [
            [Paragraph("N°", ParagraphStyle(name='Header', fontSize=8, fontName='Helvetica-Bold', wordWrap='CJK'))] +
            [Paragraph("Élève", ParagraphStyle(name='Header', fontSize=8, fontName='Helvetica-Bold', wordWrap='CJK'))] +
            [Paragraph(var_name, ParagraphStyle(name='Header', fontSize=8, fontName='Helvetica-Bold', wordWrap='CJK')) for var_name in variable_names]
        ]

        totals = [0] * len(variable_names)

        for idx, inscription in enumerate(inscriptions, start=1):
            eleve = f"{inscription['id_eleve__nom']} {inscription['id_eleve__prenom']}"
            row = [
                Paragraph(str(idx), ParagraphStyle(name='Normal', fontSize=8, leading=10, wordWrap='CJK')), 
                Paragraph(eleve, ParagraphStyle(name='Normal', fontSize=8, leading=10, wordWrap='CJK'))  
            ]
            for i, var_name in enumerate(variable_names):
                paiement = Paiement.objects.filter(
                    id_eleve__id_eleve=inscription['id_eleve__id_eleve'],
                    id_variable__variable=var_name,
                    id_campus_id=id_campus,
                    id_cycle_actif_id=id_cycle,
                    id_classe_active_id=id_classe_active,
                    id_annee_id=id_annee,
                    status=True
                ).first()
                montant = paiement.montant if paiement else 0
                row.append(f"{montant} Fbu" if montant else "-")
                totals[i] += montant if montant else 0
            data.append(row)

        totals_row = [
            Paragraph("Totaux", ParagraphStyle(name='Total', fontSize=8, fontName='Helvetica-Bold')), ""
        ]
        for total in totals:
            totals_row.append(f"{total} Fbu" if total else "-")
        data.append(totals_row)

        total_width = 190 * mm  
        num_col_width = 10 * mm 
        eleve_col_width = 70 * mm 
        variable_col_width = (total_width - num_col_width - eleve_col_width) / max(1, len(variable_names))
        col_widths = [num_col_width, eleve_col_width] + [variable_col_width] * len(variable_names)

        table = Table(data, colWidths=col_widths)
        table.setStyle(table_style)
        elements.append(table)

        doc.build(elements, onFirstPage=build_page_number, onLaterPages=build_page_number)
        return response

    except Exception as e:
        return HttpResponse(f"Erreur serveur : {str(e)}", status=500)

