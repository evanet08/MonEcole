
from .structure_primaire import *
from .structure_secondaire import *
from .api import *
from .structure_cycle_sup import *
from .structure_par_module import *
from .structure_maternelle import *


def compute_single_page_layout(table_data, page_orientation='portrait',
                                other_elements_h=92, top_margin=0, bottom_margin=5,
                                ideal_rh=4.5, min_rh=2.2):
    """
    Compute row heights to guarantee a bulletin table fits on a single A4 page.

    This function dynamically scales row heights (and optionally font sizes)
    to constrain any bulletin to exactly one page, regardless of how many
    rows of courses/domaines are present.

    Args:
        table_data:         list of rows (each row = list of cells)
        page_orientation:   'portrait' or 'landscape'
        other_elements_h:   estimated height (mm) consumed by header+NID+line2+title+footer
        top_margin:         top margin in mm
        bottom_margin:      bottom margin in mm
        ideal_rh:           ideal row height in mm (used when rows fit comfortably)
        min_rh:             absolute minimum row height in mm

    Returns:
        list of row heights (in ReportLab points) — one per row in table_data.
        Also mutates Paragraph styles in table_data if font scaling is needed.
    """
    from reportlab.lib.units import mm as _mm
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import Paragraph as _Paragraph
    from reportlab.lib.styles import ParagraphStyle as _ParagraphStyle

    page_h = A4[1] if page_orientation == 'portrait' else A4[0]
    available_h = page_h - (top_margin * _mm) - (bottom_margin * _mm) - (other_elements_h * _mm)

    num_rows = len(table_data)
    if num_rows == 0:
        return []

    _ideal = ideal_rh * _mm
    _min = min_rh * _mm

    if num_rows * _ideal <= available_h:
        row_heights = [_ideal] * num_rows
    else:
        computed = available_h / num_rows
        row_heights = [max(_min, computed)] * num_rows

    # ── Auto-scale font sizes when rows are very tight ──
    actual_rh = row_heights[0]
    threshold = 3.5 * _mm
    if actual_rh < threshold:
        scale_delta = 1.0 if actual_rh >= 2.8 * _mm else 1.5
        _seen_styles = {}  # cache to avoid creating duplicate styles
        for row in table_data:
            for ci, cell in enumerate(row):
                if isinstance(cell, _Paragraph) and hasattr(cell, 'style'):
                    s = cell.style
                    cache_key = (s.name, s.fontSize)
                    if cache_key not in _seen_styles:
                        new_fs = max(3, s.fontSize - scale_delta)
                        new_lead = max(3.5, new_fs + 0.5)
                        _seen_styles[cache_key] = _ParagraphStyle(
                            name=s.name + '_sc',
                            parent=s,
                            fontSize=new_fs,
                            leading=new_lead,
                        )
                    cell.style = _seen_styles[cache_key]

    return row_heights




def apply_rounded_values(table_data, skip_rows=None):
    """
    Post-traitement d'affichage : arrondit toutes les valeurs numériques
    dans les cellules Paragraph d'un table_data ReportLab.

    ⚠ Purement cosmétique — les notes en base restent inchangées.

    Règle d'arrondi standard :
        ≥ 0.5 → arrondi par excès   (9.5 → 10)
        < 0.5 → arrondi par défaut  (9.45 → 9)

    IMPORTANT : On REMPLACE la cellule Paragraph par une nouvelle instance
    car modifier Paragraph.text ne reconstruit pas le rendu interne.

    Args:
        table_data: liste de listes de cellules (Paragraph ou None)
        skip_rows: set d'indices de lignes à ne pas toucher (headers)
    """
    import re
    import math
    from reportlab.platypus import Paragraph as _Paragraph

    if skip_rows is None:
        skip_rows = {0, 1, 2}  # En-têtes par défaut

    for row_idx, row in enumerate(table_data):
        if row_idx in skip_rows:
            continue
        for col_idx, cell in enumerate(row):
            if cell is None:
                continue
            if not isinstance(cell, _Paragraph):
                continue

            # Colonne 0 = noms de cours/domaines → ne pas toucher
            if col_idx == 0:
                continue

            original_text = cell.text or ""
            stripped = original_text.strip()

            # Ne pas toucher aux cellules vides, tirets, ou texte "0"
            if not stripped or stripped in ("-", " ", "0"):
                continue

            # Extraire le texte numérique brut (sans balises HTML)
            clean = re.sub(r'<[^>]+>', '', stripped).strip()
            if not clean or clean in ("-", " ", "0"):
                continue

            # ── Cas pourcentage : garder 1 décimale ──
            if "%" in clean:
                pct_match = re.search(r'([\d.]+)\s*%', clean)
                if pct_match:
                    try:
                        pct_val = float(pct_match.group(1))
                        # Arrondir à 1 décimale (ex: 77.09% → 77.1%)
                        rounded_pct = round(pct_val, 1)
                        # Formater sans trailing zero inutile (ex: 85.0% → 85%)
                        pct_str = f"{rounded_pct:.1f}".rstrip('0').rstrip('.')
                        new_text = original_text.replace(pct_match.group(0), f"{pct_str}%")
                        row[col_idx] = _Paragraph(new_text, cell.style)
                    except (ValueError, TypeError):
                        pass
                continue

            # ── Cas numérique standard ──
            try:
                float_val = float(clean)
            except (ValueError, TypeError):
                continue

            # Si c'est déjà un entier exact, nettoyer l'affichage (30.0 → 30)
            if float_val == int(float_val):
                if '.' in clean:
                    new_text = original_text.replace(clean, str(int(float_val)))
                    row[col_idx] = _Paragraph(new_text, cell.style)
                continue

            # Arrondi classique ROUND_HALF_UP (scolaire)
            rounded_int = int(math.floor(float_val + 0.5))

            # Reconstruire le texte en préservant le formatage HTML, créer nouveau Paragraph
            new_text = original_text.replace(clean, str(rounded_int))
            row[col_idx] = _Paragraph(new_text, cell.style)


def resolve_bulletin_title(titre_template, id_classe, id_annee, id_campus=None):
    """
    Résout un titre de bulletin dynamique en remplaçant les variables [xxx].

    Variables supportées :
        [classe]        → nom de la classe (ex: "1ère Primaire")
        [annee]         → année scolaire (ex: "2025-2026")
        [etablissement] → nom de l'établissement
        [cycle]         → nom du cycle (ex: "Primaire")

    Args:
        titre_template: str avec variables entre crochets, ou vide/None
        id_classe: EAC surrogate ID (pour résoudre classe)
        id_annee: business key id_annee (pour résoudre année)
        id_campus: campus ID (pour résoudre établissement)

    Returns:
        str: titre résolu, ou None si titre_template est vide/None
             (le caller utilise alors le titre par défaut)
    """
    if not titre_template or not titre_template.strip():
        return None

    import re
    import logging
    logger = logging.getLogger(__name__)

    titre = titre_template.strip()
    variables = re.findall(r'\[(\w+)\]', titre)

    if not variables:
        return titre  # Pas de variables, retourner tel quel

    context = {}

    # Résoudre les variables nécessaires
    # IMPORTANT: utiliser les mêmes imports que create_bulletin_title (structure_primaire.py)
    if 'classe' in variables or 'cycle' in variables:
        try:
            from MonEcole_app.models import EtablissementAnneeClasse
            eac = EtablissementAnneeClasse.objects.select_related('classe').get(id=id_classe)
            context['classe'] = eac.classe.classe.strip() if eac.classe else ''
            if 'cycle' in variables and eac.classe and eac.classe.cycle_id:
                context['cycle'] = str(eac.classe.cycle).strip() if eac.classe.cycle else ''
            else:
                context['cycle'] = ''
        except Exception as e:
            logger.warning(f"[resolve_bulletin_title] EAC {id_classe} not found: {e}")
            context['classe'] = ''
            context['cycle'] = ''

    if 'annee' in variables:
        try:
            from MonEcole_app.models import Annee
            annee_obj = Annee.objects.filter(id_annee=id_annee).first()
            context['annee'] = str(annee_obj.annee).strip() if annee_obj else ''
        except Exception as e:
            logger.warning(f"[resolve_bulletin_title] Annee {id_annee} not found: {e}")
            context['annee'] = ''

    if 'etablissement' in variables:
        try:
            from MonEcole_app.models import Institution
            if id_campus:
                inst = Institution.objects.filter(id_ecole=id_campus).first()
                context['etablissement'] = inst.ecole.strip() if inst and inst.ecole else ''
            else:
                context['etablissement'] = ''
        except Exception as e:
            logger.warning(f"[resolve_bulletin_title] Institution {id_campus} not found: {e}")
            context['etablissement'] = ''

    # Remplacer les variables
    for var in variables:
        value = context.get(var, '')
        titre = titre.replace(f'[{var}]', value)

    return titre

