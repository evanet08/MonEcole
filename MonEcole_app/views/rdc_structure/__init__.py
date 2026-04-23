
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

    Args:
        table_data: liste de listes de cellules (Paragraph ou None)
        skip_rows: set d'indices de lignes à ne pas toucher (headers)
    """
    import re
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

            original_text = cell.text or ""
            stripped = original_text.strip()

            # Ne pas toucher aux cellules vides, tirets, pourcentages, ou texte non-numérique
            if not stripped or stripped in ("-", " ", "0"):
                continue
            if "%" in stripped:
                # Arrondir le pourcentage aussi
                pct_match = re.match(r'^([\d.]+)%$', stripped)
                if pct_match:
                    try:
                        pct_val = float(pct_match.group(1))
                        rounded_pct = round(pct_val)
                        cell.text = f"{rounded_pct}%"
                    except (ValueError, TypeError):
                        pass
                continue

            # Extraire la valeur numérique — gérer les balises HTML (font color, bold, etc.)
            clean = re.sub(r'<[^>]+>', '', stripped).strip()
            if not clean or clean in ("-", " "):
                continue

            try:
                float_val = float(clean)
            except (ValueError, TypeError):
                continue

            # Si c'est déjà un entier, pas besoin de toucher
            if float_val == int(float_val):
                continue

            # Arrondir à l'entier (standard: round() fait ROUND_HALF_EVEN en Python,
            # mais pour les bulletins scolaires on veut ROUND_HALF_UP classique)
            import math
            rounded_int = math.floor(float_val + 0.5)

            # Reconstruire le texte en préservant le formatage HTML
            new_text = original_text.replace(clean, str(rounded_int))
            cell.text = new_text
