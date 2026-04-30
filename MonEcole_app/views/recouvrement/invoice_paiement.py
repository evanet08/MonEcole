"""
Recouvrement — PDF/Excel invoice & report generation.
Ported from standalone with id_pays + id_etablissement scoping.
"""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum
from datetime import datetime
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm, inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from MonEcole_app.models import Annee, Campus, Eleve_inscription, Institution
from MonEcole_app.models.recouvrement import (
    Paiement, Variable, VariablePrix, Eleve_reduction_prix,
    CategorieOperation, OperationCaisse,
)
from .helpers import _require_tenant, _tenant_error, logger


def _build_pdf_header(institution, titre=None, extra_info=None):
    """Build a professional PDF header with institution info."""
    NAVY = colors.HexColor('#1e3c72')
    GOLD = colors.HexColor('#c9a84c')
    WHITE = colors.white
    LIGHT_BG = colors.HexColor('#f8fafc')

    s_ecole = ParagraphStyle('NomEcole', fontSize=14, fontName='Helvetica-Bold',
                              alignment=TA_CENTER, textColor=WHITE, leading=18)
    s_titre = ParagraphStyle('Titre', fontSize=12, fontName='Helvetica-Bold',
                              alignment=TA_CENTER, textColor=NAVY, leading=16)
    s_info = ParagraphStyle('Info', fontSize=8, fontName='Helvetica',
                             alignment=TA_CENTER, textColor=colors.HexColor('#b0bdd4'), leading=10)

    elements = []

    nom_ecole = (institution.nom_ecole or 'ÉTABLISSEMENT').upper() if institution else 'ÉTABLISSEMENT'
    banner_data = [[Paragraph(nom_ecole, s_ecole)]]
    if institution and institution.sigle:
        banner_data[0][0] = [Paragraph(nom_ecole, s_ecole),
                              Paragraph(institution.sigle, s_info)]
    banner = Table([[Paragraph(nom_ecole, s_ecole)]], colWidths=[17*cm])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), NAVY),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('ROUNDEDCORNERS', [6,6,0,0]),
    ]))
    elements.append(banner)

    gold_line = Table([['']], colWidths=[17*cm], rowHeights=[3])
    gold_line.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), GOLD)]))
    elements.append(gold_line)
    elements.append(Spacer(1, 6))

    if extra_info:
        info_p = Paragraph(extra_info, ParagraphStyle('ExtraInfo', fontSize=9, alignment=TA_LEFT, leading=13))
        elements.append(info_p)
        elements.append(Spacer(1, 4))

    if titre:
        titre_t = Table([[Paragraph(f'<b>{titre.upper()}</b>', s_titre)]], colWidths=[17*cm])
        titre_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), LIGHT_BG),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 1, NAVY),
            ('LINEBELOW', (0,0), (-1,-1), 2, GOLD),
        ]))
        elements.append(titre_t)
        elements.append(Spacer(1, 5))

    return elements


@login_required(login_url='login')
def rec_generate_invoice(request, id_paiement):
    """Génère une facture PDF pour un paiement."""
    id_pays, id_etab = _require_tenant(request)
    if not id_pays:
        return HttpResponse('Tenant non identifié', status=403)
    try:
        p = Paiement.objects.select_related(
            'idCampus', 'id_classe', 'id_annee', 'id_variable', 'id_eleve'
        ).get(id_paiement=id_paiement, id_pays=id_pays, id_etablissement=id_etab)

        institution = Institution.objects.first()

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="facture_{id_paiement}.pdf"'
        doc = SimpleDocTemplate(response, pagesize=(100*mm, 150*mm),
                                 rightMargin=5*mm, leftMargin=5*mm,
                                 topMargin=5*mm, bottomMargin=5*mm)

        styles = getSampleStyleSheet()
        normal = ParagraphStyle('N', fontSize=8, leading=10, wordWrap='CJK')

        elts = []
        info_text = (
            f"Campus: <b>{p.idCampus.campus}</b><br/>"
            f"Classe: <b>{p.id_classe.classe}</b><br/>"
            f"Année: <b>{p.id_annee.annee}</b><br/>"
            f"Élève: <b>{p.id_eleve.nom} {p.id_eleve.prenom}</b><br/>"
            f"Date: <b>{datetime.now().strftime('%d/%m/%Y %H:%M')}</b>"
        )
        elts.append(Paragraph(info_text, normal))
        elts.append(Spacer(1, 8*mm))

        data = [['Variable', 'Montant'],
                [Paragraph(p.id_variable.variable, normal), f"{p.montant} Fbu"]]
        t = Table(data, colWidths=[50*mm, 40*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        elts.append(t)
        elts.append(Spacer(1, 10*mm))
        elts.append(Paragraph("Signature: ____________________",
                               ParagraphStyle('Sig', fontSize=8, alignment=2)))

        doc.build(elts)
        return response
    except Paiement.DoesNotExist:
        return HttpResponse('Paiement non trouvé', status=404)
    except Exception as e:
        return HttpResponse(f'Erreur: {e}', status=500)


@login_required(login_url='login')
def rec_generate_fiche_paie_classe(request):
    """Fiche de paiement par classe (PDF)."""
    id_pays, id_etab = _require_tenant(request)
    if not id_pays:
        return HttpResponse('Tenant non identifié', status=403)
    try:
        annee_id = request.GET.get('id_annee')
        classe_id = request.GET.get('id_classe')
        if not all([annee_id, classe_id]):
            return HttpResponse('Paramètres manquants', status=400)

        inscriptions = Eleve_inscription.objects.filter(
            id_annee_id=annee_id, id_classe_id=classe_id, status=True,
            id_pays=id_pays, id_etablissement=id_etab
        ).select_related('id_eleve').values(
            'id_eleve__id_eleve', 'id_eleve__nom', 'id_eleve__prenom'
        ).distinct()

        if not inscriptions.exists():
            return HttpResponse('Aucune inscription trouvée', status=404)

        variables = Paiement.objects.filter(
            id_annee_id=annee_id, id_classe_id=classe_id,
            status=True, id_pays=id_pays, id_etablissement=id_etab
        ).values('id_variable__variable').distinct()[:6]
        var_names = [v['id_variable__variable'] for v in variables]
        if not var_names:
            return HttpResponse('Aucun paiement trouvé', status=404)

        institution = Institution.objects.first()
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="fiche_paie_{classe_id}.pdf"'
        doc = SimpleDocTemplate(response, pagesize=A4,
                                 rightMargin=10*mm, leftMargin=10*mm,
                                 topMargin=10*mm, bottomMargin=15*mm)
        elts = _build_pdf_header(institution, titre='Situation des paiements')
        elts.append(Spacer(1, 5*mm))

        header_style = ParagraphStyle('H', fontSize=8, fontName='Helvetica-Bold', wordWrap='CJK')
        normal_style = ParagraphStyle('N', fontSize=8, leading=10, wordWrap='CJK')

        data = [
            [Paragraph('N°', header_style), Paragraph('Élève', header_style)] +
            [Paragraph(v, header_style) for v in var_names]
        ]
        totals = [0] * len(var_names)
        for idx, ins in enumerate(inscriptions, 1):
            row = [Paragraph(str(idx), normal_style),
                   Paragraph(f"{ins['id_eleve__nom']} {ins['id_eleve__prenom']}", normal_style)]
            for i, vn in enumerate(var_names):
                p = Paiement.objects.filter(
                    id_eleve__id_eleve=ins['id_eleve__id_eleve'],
                    id_variable__variable=vn, id_annee_id=annee_id,
                    id_classe_id=classe_id, status=True,
                    id_pays=id_pays, id_etablissement=id_etab
                ).aggregate(total=Sum('montant'))['total'] or 0
                row.append(f"{p} Fbu" if p else "-")
                totals[i] += p
            data.append(row)

        totals_row = [Paragraph('Totaux', header_style), '']
        totals_row += [f"{t} Fbu" if t else "-" for t in totals]
        data.append(totals_row)

        total_w = 190*mm
        col_ws = [10*mm, 60*mm] + [(total_w - 70*mm) / max(1, len(var_names))] * len(var_names)
        t = Table(data, colWidths=col_ws)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ]))
        elts.append(t)
        doc.build(elts)
        return response
    except Exception as e:
        return HttpResponse(f'Erreur: {e}', status=500)
