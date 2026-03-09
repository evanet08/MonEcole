from .structure_bulletin import *
import logging
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from MonEcole_app.views.decorators.decorators import module_required

logger = logging.getLogger(__name__)


def determiner_mention_abrev(pourcentage):
    mentions = Mention.objects.all()
    for mention in mentions:
        if mention.min <= pourcentage <= mention.max:
            return mention
    return None

def get_trimestres(id_annee, id_campus, id_cycle, id_classe):
    
    try:
        campus = Campus.objects.get(id_campus=id_campus)
        localisation = campus.localisation.upper() 
    except Campus.DoesNotExist:
        return None

 
    trimestres_qs = Annee_trimestre.objects.filter(
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe
    ).order_by('id_trimestre').distinct()[:3]

    if len(trimestres_qs) != 3:
        return None

    result = []
    for trimestre in trimestres_qs:
        nom_original = trimestre.trimestre.trimestre  

     
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


def get_note_types():
    """Récupère les sigles des types de notes (T.J et Ex.)."""
    cache_key = 'note_types'
    result = cache.get(cache_key)
    if result is None:
        note_types = Eleve_note_type.objects.filter(sigle__in=['T.J', 'Ex.']).values_list('sigle', flat=True)
        result = ('T.J' if 'T.J' in note_types else '-', 'Ex.' if 'Ex.' in note_types else '-')
        cache.set(cache_key, result, timeout=3600)
    return result

def get_cours_classe(id_annee, id_campus, id_cycle, id_classe):
    """Récupère les cours associés à une classe."""
    return Cours_par_classe.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe
    ).select_related('id_cours').order_by('id_cours__domaine')

def clean_text(text, max_length, split_length):
    """Nettoie et gère les retours à la ligne pour un texte trop long."""
    if not text:
        return ''
    text = text.replace('\n\n', '\n').strip()
    if len(text) <= max_length:
        return text
    words = text.split()
    first_line, second_line = [], []
    total_length = 0
    for word in words:
        if total_length + len(word) <= split_length:
            first_line.append(word)
            total_length += len(word) + 1
        else:
            second_line.append(word)
    return ' '.join(first_line) + '\n' + ' '.join(second_line)

def build_domaines_dict(cours_classe):
    domaines_dict = {}
    for cc in cours_classe:
        cours = cc.id_cours
        domaine = cours.domaine if cours.domaine else None
        if domaine not in domaines_dict:
            domaines_dict[domaine] = []
        domaines_dict[domaine].append({
            'nom': cours.cours,
            'tp': cc.TP if hasattr(cc, 'TP') else None,
            'tpe': cc.TPE if hasattr(cc, 'TPE') else None
        })
    return domaines_dict

def build_groupes(domaines_dict):
    groupes = []
    for domaine, cours_list in domaines_dict.items():
        domaine_clean = clean_text(domaine, 20, 10) if domaine else ''
        cours_clean_list = [
            {
                'nom': clean_text(cours['nom'], 20, 12 if domaine else 8),
                'tp': cours['tp'],
                'tpe': cours['tpe']
            }
            for cours in cours_list
        ]
        groupes.append({"domaine": domaine_clean, "cours": cours_clean_list})
    return groupes

def initialize_table_data(trimestre_noms, tj_sigle, ex_sigle):
    """Initialise les en-têtes du tableau."""
    return [
        ['Matières', '', 'Maxima', '', '', trimestre_noms[0], '', '', trimestre_noms[1], '', '', trimestre_noms[2], '', '', 'Résultats annuels', '', '', ''],
        ['', '', tj_sigle, ex_sigle, 'Tot', tj_sigle, ex_sigle, 'Tot', tj_sigle, ex_sigle, 'Tot', tj_sigle, ex_sigle, 'Tot', 'Max.an.', 'Tot.an.', '%', 'Obs']
    ]

def clean_cours_name(name, for_comparison=True):
    if for_comparison:
        return re.sub(r'\s+', ' ', name.replace('\n', ' ').strip())
    return re.sub(r'\s+', ' ', name.strip())  

def get_student_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe):
   
    try:
        trimestres = get_trimestres(id_annee,id_campus,id_cycle,id_classe)
        trimestre_ids = [t[0] for t in trimestres]
        trimestre_noms = [t[1] for t in trimestres]
    except ValueError as e:
        return {}

    cours_classe = Cours_par_classe.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe
    ).select_related('id_cours')

    if not cours_classe:
        return {tid: {} for tid in trimestre_ids}

    note_types = Eleve_note_type.objects.filter(sigle__in=['T.J', 'Ex.'])
    sigles_map = {nt.id_type_note: nt.sigle for nt in note_types}

    if not sigles_map:
        return {tid: {} for tid in trimestre_ids}

    results = {trimestre_id: {} for trimestre_id in trimestre_ids}
    for trimestre_id in trimestre_ids:
        for cc in cours_classe:
            cours_key = clean_cours_name(cc.id_cours.cours, for_comparison=True)
            results[trimestre_id][cours_key] = {'T.J': '-', 'Ex.': '-'}

    cours_ids = [cc.id_cours_id for cc in cours_classe]

    all_notes = Eleve_note.objects.filter(
        id_eleve_id=id_eleve,
        id_annee_id=id_annee,
        id_campus_id=id_campus
    ).values('id_trimestre_id', 'id_cours_id', 'id_cours__cours', 'note', 'id_type_note__sigle')

    for trimestre_id in trimestre_ids:

        notes = Eleve_note.objects.filter(
            id_eleve_id=id_eleve,
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_actif = id_cycle,
            id_classe_active = id_classe,
            id_trimestre_id=trimestre_id,
            id_cours_id__in=cours_ids,
            id_type_note_id__in=sigles_map.keys()
        ).select_related('id_cours', 'id_type_note')


        for cc in cours_classe:
            cours_key = clean_cours_name(cc.id_cours.cours, for_comparison=True)
            for type_note_id, sigle in sigles_map.items():
                type_notes = notes.filter(id_cours_id=cc.id_cours_id, id_type_note_id=type_note_id)
                if type_notes.exists():
                    tot_note = type_notes.aggregate(Sum('note'))['note__sum']
                    results[trimestre_id][cours_key][sigle] = str(int(tot_note)) if tot_note is not None else '-'
                    
    return results


def fill_notes_ponderations_columns(notes_by_trimestre, search_nom, trimestre_ids, cours_classe_obj):
    """Retourne les colonnes 2 à 14 pour un cours."""
    search_nom_normalized = clean_cours_name(search_nom, for_comparison=True)
    

    columns = ['-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-']

    if cours_classe_obj:
        tp = getattr(cours_classe_obj, 'TP', 0) or 0
        tpe = getattr(cours_classe_obj, 'TPE', 0) or 0
        max_tot = tp + tpe

        columns[0] = '-' if tp == 0 else str(int(tp))
        columns[1] = '-' if tpe == 0 else str(int(tpe))
        columns[2] = str(int(max_tot))
        columns[12] = str(int(max_tot * 3))

    
    cours_key = None
    for tid in notes_by_trimestre:
        for key in notes_by_trimestre[tid]:
            key_normalized = clean_cours_name(key, for_comparison=True)
            if key_normalized.lower() == search_nom_normalized.lower(): 
                cours_key = key
                break
        if cours_key:
            break

    if not cours_key:
        return columns

    for i, tid in enumerate(trimestre_ids, start=0):
        col_base = 3 + i * 3
        notes_cours = notes_by_trimestre.get(tid, {}).get(cours_key, {'T.J': '-', 'Ex.': '-'})
        tj = notes_cours.get('T.J', '-')
        ex = notes_cours.get('Ex.', '-')
        columns[col_base] = tj
        columns[col_base + 1] = ex

        try:
            tot = int(tj) + int(ex) if tj != '-' and ex != '-' else (int(tj) if tj != '-' else (int(ex) if ex != '-' else 0))
            columns[col_base + 2] = str(tot) if tot > 0 else '0'
        except (ValueError, TypeError):
            columns[col_base + 2] = '0'

    return columns

def add_cours__notes_in_rows(table_data, groupes, id_eleve, id_annee, id_campus, id_cycle, id_classe):
    totals_by_trimestre = {tid: {'tj': 0, 'ex': 0, 'tot': 0, 'tot_an': 0} for tid in range(1, 4)}
    notes_by_trimestre = get_student_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    trimestre_ids = list(notes_by_trimestre.keys()) if notes_by_trimestre else ['-','-', '-']
    
    cours_classe_dict = {
        clean_cours_name(cc.id_cours.cours, for_comparison=True): cc for cc in Cours_par_classe.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe
        ).select_related('id_cours')
    }
   
    
    total_tp = 0
    total_tpe = 0
    total_max_tot = 0
    
    for groupe in groupes:
        domaine = groupe["domaine"]
        for cours in groupe["cours"]:
            display_nom = cours['nom'] 
            search_nom = clean_cours_name(cours['nom'], for_comparison=True)  
            col0 = domaine if domaine else display_nom
            col1 = display_nom if domaine else ''
            
            cours_classe_obj = cours_classe_dict.get(search_nom, None)
            
            if cours_classe_obj is None:
                
                for key in cours_classe_dict:
                    if search_nom in key or key in search_nom:
                        cours_classe_obj = cours_classe_dict[key]
                        break
            
            notes_columns = fill_notes_ponderations_columns(notes_by_trimestre, search_nom, trimestre_ids, cours_classe_obj)
            
            if notes_columns[0] != '-':
                total_tp += int(float(notes_columns[0])) 
            if notes_columns[1] != '-':
                total_tpe += int(float(notes_columns[1]))
            if notes_columns[2] != '-':
                total_max_tot += int(float(notes_columns[2]))
            
            for i, tid in enumerate([1, 2, 3], start=0):
                tj_note = notes_columns[3 + i * 3]
                ex_note = notes_columns[3 + i * 3 + 1]
                tot = notes_columns[3 + i * 3 + 2]
                
                if tj_note != '-':
                    totals_by_trimestre[tid]['tj'] += int(float(tj_note))
                if ex_note != '-':
                    totals_by_trimestre[tid]['ex'] += int(float(ex_note))
                if tot != '-':
                    totals_by_trimestre[tid]['tot'] += int(float(tot))
            
            if notes_columns[12] != '-':
                totals_by_trimestre[1]['tot_an'] += int(float(notes_columns[12]))
            
            ligne = [col0, col1] + notes_columns + ['', '-', '']
            table_data.append(ligne)
    
    
    return table_data, totals_by_trimestre, total_tp, total_tpe, total_max_tot

def get_totals_of_ponderation_cours(table_data, totals_by_trimestre, trimestre_ids, total_tp, total_tpe, total_max_tot):
    total_row = ['Total', '']
    total_c2 = int(total_tp)
    total_c3 = int(total_tpe)
    total_c4 = int(total_max_tot)
    total_row.extend([str(total_c2), str(total_c3), str(total_c4)])
    total_tot_sum = 0
    for tid in trimestre_ids:
        totals = totals_by_trimestre.get(tid, {'tj': 0, 'ex': 0, 'tot': 0})
        tj_val = int(totals['tj'])
        ex_val = int(totals['ex'])
        tot_val = int(totals['tot'])
        total_row.extend([
            str(tj_val) if tid in trimestre_ids and tj_val != 0 else '-',
            str(ex_val) if tid in trimestre_ids and ex_val != 0 else '-',
            str(tot_val) if tid in trimestre_ids and tot_val != 0 else '-'
        ])
        total_tot_sum += tot_val
    total_tot_an = int(total_max_tot * 3)
    total_row.extend([str(total_tot_an), '', '', ''])
    table_data.append(total_row)
    
    return table_data

def finalize_table_data_bulletin(table_data, ligne_idx, id_eleve, id_annee, id_campus, id_cycle, id_classe):
  
    styles = getSampleStyleSheet()
    p_style = styles['Normal']

    place = "1"  

    paragraph_text = f"<font color='red'>{place}</font>"

    para = Paragraph(paragraph_text, p_style)
    total_index = None
    for i, row in enumerate(table_data):
        if row[0] == 'Total':
            total_index = i
            break
    if total_index is None:
        table_data.append(['Total', ''] + ['-'] * 16 + [''])
        total_index = len(table_data) - 1

    table_data.extend([
        ['%', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['Place', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
    ])

    total_notes_obtenues = 0
    total_max_tot_annee = 0
    cours_inclus = []

    col_sums = {5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0, 13: 0}
    for row in table_data[2:]:
        if row[0] in ['Total', '%', 'Place']:
            continue
        notes_obtenues = 0
        try:
            max_tot = int(float(row[4])) if row[4] != '-' else 0
            max_tot_annee = max_tot * 3
        except (ValueError, TypeError) as e:
            max_tot_annee = 0

        for col_idx in [5, 6, 8, 9, 11, 12]:
            try:
                note = int(float(row[col_idx])) if row[col_idx] != '-' else 0
                notes_obtenues += note
                col_sums[col_idx] += note
                row[col_idx] = {"value": str(note) if note > 0 else '', "highlight": False}

            except (ValueError, TypeError) as e:
                row[col_idx] = {"value": '-', "highlight": False}
        for col_idx in [7, 10, 13]:
            try:
                note = int(float(row[col_idx])) if row[col_idx] != '-' else 0
                col_sums[col_idx] += note
                highlight = max_tot > 0 and note < max_tot / 2
                row[col_idx] = {"value": str(note) if note > 0 else '', "highlight": highlight}

            except (ValueError, TypeError) as e:
                row[col_idx] = {"value": "-", "highlight": False}

        total_notes_obtenues += notes_obtenues
        total_max_tot_annee += max_tot_annee
        cours_nom = str(row[1]) if row[1] else str(row[0])
        cours_inclus.append(cours_nom)

        try:
            highlight = max_tot_annee > 0 and notes_obtenues < max_tot_annee / 2
            row[15] = {"value": str(notes_obtenues) if notes_obtenues > 0 else '0', "highlight": highlight}
        except (ValueError, TypeError) as e:
            row[15] = {"value": '-', "highlight": False}

        try:
            if max_tot_annee > 0:
                cours_percentage = (notes_obtenues * 100) / max_tot_annee
                highlight = cours_percentage < 50
                row[16] = {"value": f"{cours_percentage:.2f}%", "highlight": highlight}
                mention = determiner_mention_abrev(cours_percentage)
                row[17] = {"value": mention.abbreviation if mention else '-', "highlight": False}
            else:
                row[16] = {"value": '-', "highlight": False}
                row[17] = {"value": '-', "highlight": False}
        except (ValueError, TypeError) as e:
            row[16] = {"value": '-', "highlight": False}
            row[17] = {"value": '-', "highlight": False}


    try:
        for col_idx, total in col_sums.items():
            table_data[total_index][col_idx] = {"value": str(total) if total > 0 else '', "highlight": False}
        table_data[total_index][14] = {"value": str(total_max_tot_annee) if total_max_tot_annee > 0 else '0', "highlight": False}
        table_data[total_index][15] = {"value": str(total_notes_obtenues) if total_notes_obtenues > 0 else '0', "highlight": False}
    except (ValueError, TypeError) as e:
        for col_idx in [5, 6, 7, 8, 9, 10, 11, 12, 13]:
            table_data[total_index][col_idx] = {"value": '-', "highlight": False}
        table_data[total_index][14] = {"value": '-', "highlight": False}
        table_data[total_index][15] = {"value": '-', "highlight": False}

    total_percentage = 0
    percent_index = next(i for i, row in enumerate(table_data) if row[0] == '%')
    try:
        if total_max_tot_annee > 0:
            total_percentage = (total_notes_obtenues * 100) / total_max_tot_annee
            highlight = total_percentage < 50
            table_data[percent_index][15] = {"value": f"{total_percentage:.2f}%", "highlight": highlight}
        else:
            table_data[percent_index][15] = {"value": '-', "highlight": False}
    except (ValueError, TypeError) as e:
        table_data[percent_index][15] = {"value": '-', "highlight": False}

    try:
        tj_max = int(float(table_data[total_index][2])) if table_data[total_index][2] != '-' else 0
        ex_max = int(float(table_data[total_index][3])) if table_data[total_index][3] != '-' else 0
        tot_max = int(float(table_data[total_index][4])) if table_data[total_index][4] != '-' else 0
        for col_idx in [5, 8, 11]:
            if tj_max > 0:
                col_percent = (col_sums[col_idx] * 100) / tj_max
                highlight = col_percent < 50
                table_data[percent_index][col_idx] = {"value": f"{col_percent:.2f}%", "highlight": highlight}
            else:
                table_data[percent_index][col_idx] = {"value": '-', "highlight": False}
        for col_idx in [6, 9, 12]:
            if ex_max > 0:
                col_percent = (col_sums[col_idx] * 100) / ex_max
                highlight = col_percent < 50
                table_data[percent_index][col_idx] = {"value": f"{col_percent:.2f}%", "highlight": highlight}
            else:
                table_data[percent_index][col_idx] = {"value": '-', "highlight": False}
        for col_idx in [7, 10, 13]:
            if tot_max > 0:
                col_percent = (col_sums[col_idx] * 100) / tot_max
                highlight = col_percent < 50
                table_data[percent_index][col_idx] = {"value": f"{col_percent:.2f}%", "highlight": highlight}
            else:
                table_data[percent_index][col_idx] = {"value": '-', "highlight": False}
    except (ValueError, TypeError) as e:
        for col_idx in [5, 6, 7, 8, 9, 10, 11, 12, 13]:
            table_data[percent_index][col_idx] = {"value": '-', "highlight": False}

    try:
        place_index = next(i for i, row in enumerate(table_data) if row[0] == 'Place')
        deliberations = Deliberation_trimistrielle_resultat.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe,
            id_eleve_id=id_eleve
        )

        trimestre_col_mapping = {
            "Trimestre 1": 7,
            "Trimestre 2": 10,
            "Trimestre 3": 13
        }
        table_data[place_index][7] = {"value": '-', "highlight": False}
        table_data[place_index][10] = {"value": '-', "highlight": False}
        table_data[place_index][13] = {"value": '-', "highlight": False}
        for deliberation in deliberations:
            annee_trimestre = deliberation.id_trimestre
            trimestre = annee_trimestre.trimestre
            nom_trimestre = trimestre.trimestre
            place = deliberation.place if deliberation.place else '-'
            col_target = trimestre_col_mapping.get(nom_trimestre)
            if col_target:
                paragraph_text = f"<font color='red'>{place}</font>"
                table_data[place_index][col_target] = {
                    "value": Paragraph(paragraph_text, p_style)
                }

        annual_deliberation = Deliberation_annuelle_resultat.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_cycle_id=id_cycle,
            id_classe_id=id_classe,
            id_eleve_id=id_eleve
        ).first()
        place_annual = annual_deliberation.place if annual_deliberation and annual_deliberation.place else '-'
        paragraph_text_anuel = f"<font color='red'>{place_annual}</font>"
        
        table_data[place_index][15] = {"value": Paragraph(paragraph_text_anuel, p_style)}
    except Exception as e:
        place_index = next(i for i, row in enumerate(table_data) if row[0] == 'Place')
        table_data[place_index][7] = {"value": '-', "highlight": False}
        table_data[place_index][10] = {"value": '-', "highlight": False}
        table_data[place_index][13] = {"value": '-', "highlight": False}
        table_data[place_index][15] = {"value": '-', "highlight": False}


    table_data_display = [
        [cell["value"] if isinstance(cell, dict) else cell for cell in row]
        for row in table_data
    ]

    return table_data, table_data_display, total_percentage
  
def create_results_table(id_eleve, id_annee, id_campus, id_cycle, id_classe):
    try:
        trimestres = get_trimestres(id_annee,id_campus,id_cycle,id_classe)
        trimestre_ids = [t[0] for t in trimestres]
        trimestre_noms = [t[1] for t in trimestres]
    except ValueError as e:
        raise ValueError(f"Erreur lors de la récupération des trimestres : {str(e)}")

    # deliberations = Deliberation_trimistrielle_resultat.objects.filter(
    #     id_annee=id_annee,
    #     id_campus=id_campus,
    #     id_cycle=id_cycle,
    #     id_classe=id_classe,
    #     id_eleve=id_eleve
    # )

    tj_sigle, ex_sigle = get_note_types()
    cours_classe = get_cours_classe(id_annee, id_campus, id_cycle, id_classe)
    domaines_dict = build_domaines_dict(cours_classe)
    groupes = build_groupes(domaines_dict)
    table_data = initialize_table_data(trimestre_noms, tj_sigle, ex_sigle)

    table_data, totals_by_trimestre, total_tp, total_tpe, total_max_tot = add_cours__notes_in_rows(
        table_data, groupes, id_eleve, id_annee, id_campus, id_cycle, id_classe
    )
    ligne_idx = len(table_data)
    table_data = get_totals_of_ponderation_cours(
        table_data, totals_by_trimestre, trimestre_ids,
        total_tp=total_tp, total_tpe=total_tpe, total_max_tot=total_max_tot
    )
    table_data, table_data_display, total_percentage = finalize_table_data_bulletin( 
        table_data, ligne_idx, id_eleve, id_annee, id_campus, id_cycle, id_classe
    )
    col_widths = [1.4 * inch, 1.1 * inch] + [0.55 * inch] * 17
    table = Table(table_data_display, colWidths=col_widths, repeatRows=2)  
    styled_table = stylize_table(table, table_data)  
    return [styled_table], total_percentage  

def get_repechage_courses_on_bulletin(table_data):
  
    repechage_courses = []
    
    for row in table_data:
        if not row or len(row) < 17 or row[0] in ['Total', '%', 'Place']:
            continue
        
        try:
            percentage_str = row[16]
            if isinstance(percentage_str, dict):
                value = percentage_str.get('value')
                if hasattr(value, 'text'):
                    percentage_str = value.text
                elif value:
                    percentage_str = str(value)
                else:
                    raise ValueError("Valeur vide dans dict")
            percentage_str = str(percentage_str).replace('%', '').strip()
            if not percentage_str:
                raise ValueError("Chaîne vide")

            percentage = float(percentage_str)

        except (ValueError, TypeError, AttributeError, IndexError) as e:
            continue

        if percentage < 50.0:
            cours_nom = None
            if isinstance(row[1], dict):
                cours_nom = row[1].get('value')
            else:
                cours_nom = row[1]

            if not cours_nom:  
                if isinstance(row[0], dict):
                    cours_nom = row[0].get('value')
                else:
                    cours_nom = row[0]
            if cours_nom and cours_nom not in ['Total', '%', 'Place']:
                repechage_courses.append((cours_nom, percentage))

    repechage_courses.sort(key=lambda x: x[1])
    return repechage_courses[:3]

def create_back_page(id_annee, id_eleve, id_cycle, id_campus, id_classe, total_percentage=0):
    elements = []
    styles = getSampleStyleSheet()
    h2_style = styles['Heading2']
    h2_style.fontSize = 10
    h2_style.fontName = 'Helvetica'
    h2_style.alignment = 0

    h3_style = styles['Heading3']
    h3_style.fontSize = 10
    h3_style.fontName = 'Helvetica'
    h3_style.alignment = 0

    h3_bordure_style = styles['Heading3']
    h3_bordure_style.fontSize = 10
    h3_bordure_style.fontName = 'Helvetica'
    h3_bordure_style.alignment = 0

    h4_style = styles['Heading4']
    h4_style.fontSize = 10
    h4_style.fontName = 'Helvetica'
    h4_style.alignment = 0

    p_style = styles['Normal']
    p_style.fontSize = 10
    p_style.fontName = 'Helvetica'
    p_style.alignment = 0
    p_style.leading = 14

    p_nb_style = styles['Normal']
    p_nb_style.fontSize = 10
    p_nb_style.fontName = 'Helvetica'
    p_nb_style.alignment = 0

    section_width = 392
    line_width = 8
    right_elements = []

    try:
        institution = Institution.objects.order_by('id_ecole').first()
        nom_ecole = institution.nom_ecole if institution else "École inconnue"
    except Institution.DoesNotExist:
        nom_ecole = "Ecole inconnue"

    try:
        annee = Annee.objects.get(id_annee=id_annee)
        annee_scolaire = f"  {annee.annee}  "
    except Annee.DoesNotExist:
        annee_scolaire = "  ------------------------------------  "

    try:
        eleve = Eleve.objects.get(id_eleve=id_eleve)
        nom_prenom = f"  {eleve.nom} {eleve.prenom}  "
        adresse = f"  {eleve.naissance_province or '------------------------------------'}  "
    except Eleve.DoesNotExist:
        nom_prenom = "  Non renseigné  "
        adresse = " --------------------------------- "

    try:
        classe_active = Classe_active.objects.get(id_annee=id_annee, id_campus=id_campus, cycle_id=id_cycle, id_classe_active=id_classe)
        classe = f"  {classe_active.classe_id.classe}_{classe_active.groupe}" if classe_active.groupe else classe_active.classe_id.classe
    except Classe_active.DoesNotExist:
        classe = " --------------------------------- "

    try:
        cycle_active = Classe_cycle_actif.objects.get(id_annee=id_annee, id_campus=id_campus, id_cycle_actif=id_cycle)
        cycle = f"  {cycle_active.cycle_id.cycle}  "
    except Classe_cycle_actif.DoesNotExist:
        cycle = " --------------------------------- "

    entete_data = [
        [Paragraph(f"<font color='black'><b>République du Burundi</b></font>", h2_style)],
        [Paragraph("<font color='black'><b>Enseignement Fondamental</b></font>", h3_style)],
        [Paragraph("Direction Provinciale de l'enseignement de : .............................................", p_style)],
        [Paragraph("Direction Communale de l'enseignement de : .............................................", p_style)],
        [Paragraph(f"<font color='black'>Établissement : <b>{nom_ecole}</b></font>", p_style)]
    ]
    entete_table = Table(entete_data, colWidths=[section_width])
    entete_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    right_elements.append(entete_table)
    right_elements.append(Spacer(1, 8))

    student_info_data = [
        [Paragraph(f"<font color='black'>Bulletin de l'Enseignement Fondamental, Section : <b>{cycle}</b></font>", h2_style)],
        [Paragraph(f"<font color='black'>Année scolaire : <b>{annee_scolaire}</b></font>", p_style)],
        [Paragraph(f"<font color='black'>Nom et Prénom :  <b>{nom_prenom}</b></font>", p_style)],
        [Paragraph(f"<font color='black'>Classe : <b>{classe}</b></font>", p_style)],
        [Paragraph(f"<font color='black'>Adresse : <b>{adresse}</b></font>", p_style)],
    ]
    student_info_table = Table(student_info_data, colWidths=[section_width])
    student_info_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    right_elements.append(student_info_table)
    right_elements.append(Spacer(1, 8))

    performance_data = [[Paragraph(f"<font color='black'><b> Appréciation des Performances </b></font>", h3_style)]]
    performance_text = f"<font color='black'><b>PA : Performances à Améliorer</b></font>"
    if total_percentage >= 90:
        performance_text = f"<font color='black'><b>P.E : Performances Excellentes </b></font>"
    elif total_percentage >= 70:
        performance_text = f"<font color='black'><b>PTB : Performances Très Bonnes </b></font>"
    elif total_percentage >= 50:
        performance_text = f"<font color='black'><b> PB : Performances Bonnes </b></font>"
    performance_data.append([Paragraph(performance_text, p_style)])
   
    performance_table = Table(performance_data, colWidths=[section_width])
    performance_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    right_elements.append(performance_table)
    right_elements.append(Spacer(1, 16))

    right_elements.append(Paragraph("NB : Toute rature rend ce bulletin nul.", p_nb_style))

    left_elements = []
    trimestres = Annee_trimestre.objects.filter(id_annee=id_annee, id_campus=id_campus, id_cycle=id_cycle, id_classe=id_classe).order_by('id_trimestre').distinct()[:3]
    trimestre_noms = [trimestre.trimestre.trimestre for trimestre in trimestres[:3]]
    trimestre_ids = [trimestre.id_trimestre for trimestre in trimestres[:3]]
    if not trimestre_noms:
        trimestre_noms = ['Aucun trimestre']
        trimestre_ids = []

    appreciation_data = [
        [Paragraph("Appréciation du Conseil de Classe", h3_bordure_style)],
    ]
    for nom in trimestre_noms[:3]:
        appreciation_data.extend([
            [Paragraph(nom, h4_style)],
            [Paragraph("......................................................................", p_style)],
        ])
    while len(appreciation_data) < 7:
        appreciation_data.extend([
            [Paragraph("", h4_style)],
            [Paragraph("......................................................................", p_style)],
        ])

    appreciation_table = Table(appreciation_data, colWidths=[section_width])
    appreciation_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    left_elements.append(appreciation_table)
    left_elements.append(Spacer(1, 5))

    decisions_data = [[Paragraph("Décisions", h3_bordure_style)]]
    decision_text =f"<font color='black'><b>✔ L'élève est admis à redoubler la classe.</b></font>"
    if total_percentage >= 60:
        decision_text = f"<font color='black'><b>✔ L'élève est admis à la classe suivante.</b></font>"
    elif total_percentage >= 50:
        decision_text =f"<font color='black'><b>✔ L'élève est admis aux examens de repêchage.</b></font>"
    decisions_data.append([Paragraph(decision_text, p_style)])

    decisions_table = Table(decisions_data, colWidths=[section_width])
    decisions_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    left_elements.append(decisions_table)
    try:
        tj_sigle, ex_sigle = get_note_types()
        table_data = initialize_table_data(trimestre_noms, tj_sigle, ex_sigle)
        cours_classe = get_cours_classe(id_annee, id_campus, id_cycle, id_classe)
        domaines_dict = build_domaines_dict(cours_classe)
        groupes = build_groupes(domaines_dict)
        table_data, totals, total_tp, total_tpe, total_max_tot = add_cours__notes_in_rows(
            table_data, groupes, id_eleve, id_annee, id_campus, id_cycle, id_classe
        )
        totals_by_trimestre = {tid: totals.get(tid, {'tj': 0, 'ex': 0, 'tot': 0}) for tid in trimestre_ids}
        table_data = get_totals_of_ponderation_cours(
            table_data, totals_by_trimestre, trimestre_ids, total_tp, total_tpe, total_max_tot
        )
        
        cours_data = [{'nom': str(c.id_cours.cours), 'TP': c.TP, 'TPE': c.TPE} for c in cours_classe]
        table_data, table_data_display, total_percentage = finalize_table_data_bulletin(
            table_data, len(table_data), id_eleve, id_annee, id_campus, id_cycle, id_classe
        )

        repechage_courses = get_repechage_courses_on_bulletin(table_data)

        periode_qs = Annee_periode.objects.filter(
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle=id_cycle,
            id_classe=id_classe,
            id_trimestre_annee=trimestre_ids[-1]
        ).order_by('id_periode')

        periodes_id = [p.id_periode for p in periode_qs]
        if not periodes_id:
            raise ValueError("Aucune période trouvée pour le dernier trimestre.")
        
        id_periode_final = periodes_id[-1]

        type_note = Eleve_note_type.objects.get(sigle__iexact='Ex.')
        id_type_note = type_note.id_type_note

        repechage_courses = get_repechage_courses_on_bulletin(table_data)

        list_cours_classe_id = []
        note_repechages = []

        for i in range(min(3, len(repechage_courses))):
            try:
                course_name = repechage_courses[i][0]
                cours_obj = Cours_par_classe.objects.get(
                    id_annee=id_annee,
                    id_campus=id_campus,
                    id_cycle=id_cycle,
                    id_classe=id_classe,
                    id_cours__cours__iexact=course_name
                )
                list_cours_classe_id.append((cours_obj.id_cours_classe, cours_obj.TPE))
            except:
                list_cours_classe_id.append((None, None))

        for id_cours_classe, tpe in list_cours_classe_id:
            try:
                if id_cours_classe is None:
                    note_repechages.append("")
                    continue

                note_obj = Eleve_note.objects.get(
                    id_annee_id=id_annee,
                    id_campus_id=id_campus,
                    id_cycle_actif_id=id_cycle,
                    id_classe_active_id=id_classe,
                    id_eleve_id=id_eleve,
                    id_trimestre_id=trimestre_ids[-1],
                    id_periode_id=id_periode_final,
                    id_type_note_id=id_type_note,
                    id_cours_id=id_cours_classe
                )

                note_val = note_obj.note_repechage
                if note_val is None:
                    note_repechages.append("")
                    continue

                if tpe:
                    note_ponderee = round(float(note_val) * 100/float(tpe), 2)
                    note_format = f"{int(round(note_ponderee))}%"
                else:
                    note_format = f"{int(round(float(note_val)))}%"

                note_repechages.append(note_format)

            except:
                note_repechages.append("")

        if len(repechage_courses) > 1:
            repechage_data = [['No', 'Domaines', 'Résultats aux Examens de Repêchage']]
            for i in range(3):
                course_name = repechage_courses[i][0] if i < len(repechage_courses) else ''
                note = note_repechages[i] if i < len(note_repechages) else ''
                repechage_data.append([str(i+1), course_name, note])
            
            t = Table(repechage_data, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
        else:
            repechage_data = [
            ['No', 'Domaines', 'Résultats aux Examens de Repêchage'],
            ['1', '', ''],
            ['2', '', ''],
            ['3', '', '']
        ]
            


    except:
        repechage_data = [
            ['No', 'Domaines', 'Résultats aux Examens de Repêchage'],
            ['1', '', ''],
            ['2', '', ''],
            ['3', '', '']
        ]



    repechage_table = Table(repechage_data, colWidths=[50, 162, 180])
    repechage_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    left_elements.extend([repechage_table, Spacer(1, 5)])
    trimestre_dates = [
        
        f"<font color='black'><b>{trimestre.debut.strftime('%d/%m/%Y')} au {trimestre.fin.strftime('%d/%m/%Y')}</b></font>"
        if trimestre.debut and trimestre.fin
        else "------------------------------------"
        for trimestre in trimestres[:3]
    ]

    reopening_data = [
        [Paragraph("La rentrée scolaire aura lieu :", h3_bordure_style)],
    ]
    for nom, date in zip(trimestre_noms[:3], trimestre_dates[:3]):
        reopening_data.append([Paragraph(f"{nom} : {date}", p_style)])
    while len(reopening_data) < 4:
        reopening_data.append([Paragraph("------------------------------------", p_style)])

    reopening_table = Table(reopening_data, colWidths=[section_width])
    reopening_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    left_elements.append(reopening_table)

    left_elements.append(Spacer(1, 15))
    signature_data = [
        [Paragraph("Signature du Chef d’Établissement", p_style), Paragraph("Sceau de l’école", p_style)]
    ]
    signature_table = Table(signature_data, colWidths=[section_width / 2, section_width / 2])
    signature_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    left_elements.append(signature_table)

    left_height = sum(getattr(e, '_height', 0) for e in left_elements if hasattr(e, '_height')) + sum(s.height for s in left_elements if isinstance(s, Spacer))
    right_height = sum(getattr(e, '_height', 0) for e in right_elements if hasattr(e, '_height')) + sum(s.height for s in right_elements if isinstance(s, Spacer))
    max_height = max(left_height, right_height)

    main_table_data = [
        [left_elements[:], VerticalLineFlowable(max_height), right_elements[:]]
    ]

    main_table = Table(main_table_data, colWidths=[section_width, line_width, section_width])
    main_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(KeepTogether(main_table))

    return elements

