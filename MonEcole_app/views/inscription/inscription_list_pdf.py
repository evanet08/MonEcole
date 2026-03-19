

from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import json
import logging
from MonEcole_app.models import Institution, Annee, Campus, Classe_cycle_actif, Classe_active
from MonEcole_app.views.tools.tenant_utils import validate_campus_access

logger = logging.getLogger(__name__)

@login_required
def generate_pupils_pdf(request):
    if request.method != 'POST':
        logger.warning("Méthode non autorisée pour generate_pupils_pdf")
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
        annee_id = data.get('annee_id')
        campus_id = data.get('campus_id')
        cycle_id = data.get('cycle_id')
        classe_id = data.get('classe_id')
        pupils = data.get('pupils', [])

        if not all([annee_id, campus_id, cycle_id, classe_id]):
            logger.warning(f"Paramètres manquants pour generate_pupils_pdf : {data}")
            return HttpResponse(status=400)

        # Tenant validation
        if not validate_campus_access(request, campus_id):
            logger.warning(f"Accès interdit au campus {campus_id} pour le tenant actuel")
            return HttpResponse(status=403)

        institution = Institution.objects.first() 
        annee = Annee.objects.filter(id_annee=annee_id).first()
        campus = Campus.objects.filter(id_campus=campus_id).first()
        cycle = Classe_cycle_actif.objects.filter(id_cycle_actif=cycle_id).first()
        classe = Classe_active.objects.filter(id_classe_active=classe_id).first()

        if not all([institution, annee, campus, cycle, classe]):
            missing = []
            if not institution:
                missing.append("institution")
            if not annee:
                missing.append("année")
            if not campus:
                missing.append("campus")
            if not cycle:
                missing.append("cycle")
            if not classe:
                missing.append("classe")
            logger.error(f"Données manquantes pour l'en-tête du PDF : {missing}")
            return HttpResponse(status=400)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="liste_eleves_{annee_id}_{classe_id}.pdf"'
        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            leftMargin=1*cm, 
            rightMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        elements = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            name='Title',
            fontSize=14,
            alignment=0, 
            spaceAfter=10,
            fontName='Helvetica-Bold',
            leftIndent=0  
        )
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            fontSize=12,
            alignment=0,  
            spaceAfter=6,
            leftIndent=0  
        )

        elements.append(Paragraph(f"{institution}", title_style))
        elements.append(Paragraph(f"Année scolaire : {annee.annee}", subtitle_style))
        elements.append(Paragraph(f"Campus : {campus.campus}", subtitle_style))
        elements.append(Paragraph(f"Cycle : {cycle.cycle}", subtitle_style))
        classe_info = f"Classe : {classe.classe_id.classe if hasattr(classe, 'classe_id') and classe.classe_id else str(classe)}"
        if hasattr(classe, 'groupe') and classe.groupe:
            classe_info += f" - Groupe : {classe.groupe}"
        elements.append(Paragraph(classe_info, subtitle_style))
        elements.append(Spacer(1, 0.5*cm))

        line_data = [['']]
        line_table = Table(line_data, colWidths=[18*cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 2, colors.black),
        ]))
        elements.append(line_table)
        elements.append(Spacer(1, 0.5*cm))

        table_data = [['N°', 'Nom et prénom', 'Statut', 'Redoublant?', '']]
        for index, pupil in enumerate(pupils, start=1):
            table_data.append([
                str(index), 
                pupil['nom_complet'],
                'V' if pupil['status'] else '-',
                'V' if pupil['redoublement'] else '-',
                ''
            ])

        table = Table(table_data, colWidths=[2*cm, 6*cm, 3*cm, 3*cm, 4*cm]) 
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)

        doc.build(elements)
        return response

    except Exception as e:
        return HttpResponse(status=500)