
from .structure_primaire import *
from .structure_secondaire import *
from .api import *
from .structure_cycle_sup import *
from .structure_par_module import *
from .structure_maternelle import *


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

            # ── Cas pourcentage ──
            if "%" in clean:
                pct_match = re.search(r'([\d.]+)\s*%', clean)
                if pct_match:
                    try:
                        pct_val = float(pct_match.group(1))
                        rounded_pct = int(math.floor(pct_val + 0.5))
                        new_text = original_text.replace(pct_match.group(0), f"{rounded_pct}%")
                        row[col_idx] = _Paragraph(new_text, cell.style)
                    except (ValueError, TypeError):
                        pass
                continue

            # ── Cas numérique standard ──
            try:
                float_val = float(clean)
            except (ValueError, TypeError):
                continue

            # Si c'est déjà un entier, pas besoin de toucher
            if float_val == int(float_val):
                continue

            # Arrondi classique ROUND_HALF_UP (scolaire)
            rounded_int = int(math.floor(float_val + 0.5))

            # Reconstruire le texte en préservant le formatage HTML, créer nouveau Paragraph
            new_text = original_text.replace(clean, str(rounded_int))
            row[col_idx] = _Paragraph(new_text, cell.style)

