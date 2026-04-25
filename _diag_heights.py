"""Diagnostic: measure exact heights of all flowables for EAC 495"""
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MonEcole_project.settings")
django.setup()

from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4

margin = 5 * mm
page_w, page_h = A4
frame_h = page_h - margin - margin
print(f"A4: {page_h/mm:.1f}mm, frame_h: {frame_h/mm:.1f}mm")

from MonEcole_app.views.rdc_structure.structure_cycle_sup import (
    get_styles, create_header, create_nid_section, create_line2_left,
    create_line2_right__secondaire_rdc, create_line2_section__secondaire_rdc,
    create_bulletin_title__secondaire_superieur
)
from MonEcole_app.views.rdc_structure.structure_par_module import create_bulletin_content_cycle_superieur
from MonEcole_app.models.eleves.eleve import Eleve

styles_t, style_normal, style_center, _a, _b, style_title, style_right = get_styles()
eleve = Eleve.objects.get(id_eleve=1364)

elements = []
create_header(elements, None, None, style_title, style_center, eleve=eleve)
create_nid_section(elements, style_normal, eleve=eleve, id_campus=2)
left_table = create_line2_left(elements, style_normal, id_campus=2)
right_table = create_line2_right__secondaire_rdc(elements, eleve, 495, style_normal)
create_line2_section__secondaire_rdc(elements, left_table, right_table)
create_bulletin_title__secondaire_superieur(elements, style_title, style_right)
create_bulletin_content_cycle_superieur(elements, style_normal, style_center, 1, 2, 3, 495, 1364)

avail_w = page_w - 2 * margin
total_h = 0
for i, el in enumerate(elements):
    w, h = el.wrap(avail_w, frame_h)
    name = type(el).__name__
    print(f"  [{i}] {name}: {h/mm:.1f}mm (w={w/mm:.0f}mm)")
    total_h += h

print(f"\nTOTAL: {total_h/mm:.1f}mm vs frame: {frame_h/mm:.1f}mm")
if total_h > frame_h:
    print(f"OVERFLOW: {(total_h - frame_h)/mm:.1f}mm")
else:
    print("FITS OK")

# Also check EAC 495 section mapping
from MonEcole_app.models.country_structure import EtablissementAnneeClasse
eac = EtablissementAnneeClasse.objects.get(id=495)
print(f"\nEAC 495: classe_id={eac.classe_id}, groupe={eac.groupe}, section_id={eac.section_id}")
