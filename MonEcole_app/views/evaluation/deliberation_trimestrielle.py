
    
from django.db import transaction
from collections import defaultdict
from django.core.exceptions import ObjectDoesNotExist
from .delib_an_tools import *
logger = logging.getLogger(__name__)
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from MonEcole_app.views.decorators.decorators import module_required
from MonEcole_app.models import Deliberation_trimistrielle_resultat,Deliberation_examen_resultat

from MonEcole_app.views.rdc_structure.structure_secondaire import (calculer_pourcentages_secondaire,
                                                                   calculer_sous_totaux_et_maxima_secondaire,get_semestres)
from MonEcole_app.views.rdc_structure.structure_primaire import (get_periodes_par_trimestre,get_cours_classe_rdc,
                                                                 get_student_period_notes,get_student_exam_notes,
                                                                 calculer_pourcentages,calculer_pts_obt_et_somme_finale,calculer_pts_obt_trimestriels_et_annuel,calculer_somme_pts_obt_maxima,
                                                                 calculer_sous_totaux_et_maxima,style_center,style_normal)


from MonEcole_app.views.rdc_structure import (regrouper_cours_par_tp_tpe,
                                              recuperer_cours_obligatoires,
                                              ajouter_cours_groupes_dans_table)

@login_required
@module_required("Evaluation")
def select_by_field_to_deliberate_annual(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_select = DeliberationAnnuelleForm(request.POST or None)
    return render(request, 'evaluation/index_evaluation.html', {
        'form_select':form_select,
        'form_type': 'select_form',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
    })

@login_required
@module_required("Evaluation")
def select_by_field_to_deliberate_classe(request):
    user_info = get_user_info(request)
    user_modules = user_info
    form_select = DeliberationTrimestreForm(request.POST or None)
    return render(request, 'evaluation/index_evaluation.html', {
        'form_select':form_select,
        'form_type': 'select_form',
        'photo_profil': user_modules['photo_profil'],
        'modules': user_modules['modules'],
        'last_name': user_modules['last_name'],
    })
    
def verify_evaluations_ponderations(id_annee, id_campus, id_cycle, id_classe, id_trimestre):
    
    try:
        trimestre = Annee_trimestre.objects.filter(
            id_trimestre=id_trimestre, id_annee_id=id_annee,
            id_campus_id=id_campus, id_cycle_id=id_cycle, id_classe_id=id_classe
        ).first()
    except Annee_trimestre.DoesNotExist:
        return False, f"Trimestre {id_trimestre} non trouvé ou inactif."

    if not trimestre:
        return False, f"Trimestre {id_trimestre} non trouvé ou inactif."

    cours_classe = Cours_par_classe.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe
    ).select_related('id_cours')
    
    if not cours_classe:
        return False, "Aucun cours trouvé pour cette classe."

    note_types = Eleve_note_type.objects.filter(sigle__in=['T.J', 'Ex.'])
    sigles_map = {nt.id_type_note: nt.sigle for nt in note_types}
    if not sigles_map:
        return False, "Aucun type de note (T.J, Ex.) trouvé."

    errors = []
    for cc in cours_classe:
        cours_nom = cc.id_cours.cours
        tp = getattr(cc, 'TP', 0) or 0
        tpe = getattr(cc, 'TPE', 0) or 0

        evaluations = Evaluation.objects.filter(
            id_cours_classe_id=cc.id_cours_classe,
            id_trimestre_id=id_trimestre,
            id_type_note_id__in=sigles_map.keys()
        ).values('id_type_note_id').annotate(total_ponderation=Sum('ponderer_eval'))

        tj_ponderation = 0
        ex_ponderation = 0
        for eval in evaluations:
            type_note_id = eval['id_type_note_id']
            total_ponderation = eval['total_ponderation'] or 0
            sigle = sigles_map.get(type_note_id)
            if sigle == 'T.J':
                tj_ponderation = total_ponderation
            elif sigle == 'Ex.':
                ex_ponderation = total_ponderation

        if tj_ponderation != tp:
            errors.append(f"Cours {cours_nom}: Somme des pondérations T.J ({tj_ponderation}) != TP ({tp})")
        if ex_ponderation != tpe:
            errors.append(f"Cours {cours_nom}: Somme des pondérations Ex. ({ex_ponderation}) != TPE ({tpe})")

    if errors:
        return False, "; ".join(errors)
    
    return True, "Toutes les pondérations sont valides."

def get_student_notes_par_trimestre(id_eleve, id_annee, id_campus, id_cycle, id_classe, id_trimestre):
    

    try:
        trimestre = Annee_trimestre.objects.get(id_trimestre=id_trimestre, id_annee = id_annee,id_campus = id_campus,id_cycle = id_cycle,id_classe = id_classe)

    except Annee_trimestre.DoesNotExist:
        return {}

    cours_classe = Cours_par_classe.objects.filter(
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_cycle_id=id_cycle,
        id_classe_id=id_classe
    ).select_related('id_cours')

    if not cours_classe:
        return {}

    note_types = Eleve_note_type.objects.filter(sigle__in=['T.J', 'Ex.'])
    sigles_map = {nt.id_type_note: nt.sigle for nt in note_types}

    if not sigles_map:
        return {}

    results = {}
    for cc in cours_classe:
        cours_key = clean_cours_name(cc.id_cours.cours, for_comparison=True)
        results[cours_key] = {'T.J': '-', 'Ex.': '-'}

    # Eleve_note a id_cours (FK vers Cours), PAS id_cours_classe
    cours_ids = [cc.id_cours_id for cc in cours_classe]
    # Mapping cours_id -> cours_classe pour reverse lookup
    cours_id_to_cc = {cc.id_cours_id: cc for cc in cours_classe}

    notes = Eleve_note.objects.filter(
        id_eleve_id=id_eleve,
        id_annee_id=id_annee,
        id_campus_id=id_campus,
        id_trimestre_id=id_trimestre,
        id_cours_id__in=cours_ids,
        id_type_note_id__in=sigles_map.keys()
    ).select_related('id_cours', 'id_type_note')
    for cc in cours_classe:
        cours_key = clean_cours_name(cc.id_cours.cours, for_comparison=True)
        for type_note_id, sigle in sigles_map.items():
            type_notes = notes.filter(id_cours_id=cc.id_cours_id, id_type_note_id=type_note_id)
            if type_notes.exists():
                tot_note = type_notes.aggregate(Sum('note'))['note__sum']
                results[cours_key][sigle] = str(int(tot_note)) if tot_note is not None else '-'

    return results

def fill_notes_ponderations_columns_par_trimestre(notes, search_nom, trimestre_id, trimestre_ids, cours_classe_obj):
    """Retourne les colonnes 2 à 15 pour un cours, pour un trimestre spécifique."""
    search_nom_normalized = clean_cours_name(search_nom, for_comparison=True)

    columns = ['-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-']

    if cours_classe_obj:
        tp = getattr(cours_classe_obj, 'TP', 0) or 0
        tpe = getattr(cours_classe_obj, 'TPE', 0) or 0
        max_tot = tp + tpe
        columns[0] = str(int(tp))
        columns[1] = str(int(tpe))
        columns[2] = str(int(max_tot))
        columns[13] = str(int(max_tot)) 

    cours_key = None
    for key in notes:
        key_normalized = clean_cours_name(key, for_comparison=True)
        if key_normalized.lower() == search_nom_normalized.lower():
            cours_key = key
            break

    if not cours_key:
        return columns

    try:
        idx = trimestre_ids.index(trimestre_id)
        col_base = 3 + idx * 3
        notes_cours = notes.get(cours_key, {'T.J': '-', 'Ex.': '-'})
        tj = notes_cours.get('T.J', '-')
        ex = notes_cours.get('Ex.', '-')
        columns[col_base] = tj
        columns[col_base + 1] = ex

        try:
            tot = int(tj) + int(ex) if tj != '-' and ex != '-' else (int(tj) if tj != '-' else (int(ex) if ex != '-' else 0))
            columns[col_base + 2] = str(tot) if tot > 0 else '0'
        except (ValueError, TypeError):
            columns[col_base + 2] = '0'
        
        tot_an = 0
        for i in [6, 9, 12]:  
            if columns[i] != '-' and columns[i] != '0':
                tot_an += int(float(columns[i]))
        columns[12] = str(tot_an) if tot_an > 0 else '-' 
    except ValueError:
        logger.error(f"Trimestre {trimestre_id} non trouvé dans trimestre_ids")

    return columns

def add_cours__notes_in_rows_par_trimestre(table_data, groupes, id_eleve, id_annee, id_campus, id_cycle, id_classe, id_trimestre, trimestre_ids):
    totals = {'tj': 0, 'ex': 0, 'tot': 0, 'tot_an': 0}
    notes = get_student_notes_par_trimestre(id_eleve, id_annee, id_campus, id_cycle, id_classe, id_trimestre)
    
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
                if cours_classe_obj is None:
                    notes_columns = ['-'] * 14
                else:
                    notes_columns = fill_notes_ponderations_columns_par_trimestre(notes, search_nom, id_trimestre, trimestre_ids, cours_classe_obj)
            else:
                notes_columns = fill_notes_ponderations_columns_par_trimestre(notes, search_nom, id_trimestre, trimestre_ids, cours_classe_obj)
            
            if len(notes_columns) != 14:
                notes_columns.extend(['-'] * (14 - len(notes_columns)))
            
            if notes_columns[0] != '-':
                total_tp += int(float(notes_columns[0]))
            if notes_columns[1] != '-':
                total_tpe += int(float(notes_columns[1]))
            if notes_columns[2] != '-':
                total_max_tot += int(float(notes_columns[2]))
            
            tj_index = 5 + trimestre_ids.index(id_trimestre) * 3
            ex_index = tj_index + 1
            tot_index = tj_index + 2
            
            tj_note = notes_columns[tj_index]
            ex_note = notes_columns[ex_index]
            tot = notes_columns[tot_index]
            
            
            if tj_note != '-':
                totals['tj'] += int(float(tj_note))
            if ex_note != '-':
                totals['ex'] += int(float(ex_note))
            if tot != '-':
                totals['tot'] += int(float(tot))
            
            if notes_columns[12] != '-':
                totals['tot_an'] += int(float(notes_columns[12]))
            
            ligne = [col0, col1] + notes_columns + ['', '-', '']
            table_data.append(ligne)
            logger.info(f"Ligne ajoutée: {ligne}")
    
    if not any(row[0] == 'Total' for row in table_data):
        table_data.append(['Total'] + ['-'] * 17)
    
    total_row = next(row for row in table_data if row[0] == 'Total')
    total_row[tj_index] = str(totals['tj']) if totals['tj'] else '-'
    total_row[ex_index] = str(totals['ex']) if totals['ex'] else '-'
    total_row[tot_index] = str(totals['tot']) if totals['tot'] else '-'
    
    return table_data, totals, total_tp, total_tpe, total_max_tot

def add_conduite_and_totals_par_trimestre(table_data, totals, trimestre_id, trimestre_ids, total_tp, total_tpe, total_max_tot):
    """Ajoute la ligne des totaux pour un trimestre spécifique, sans la ligne Conduite."""
    idx = trimestre_ids.index(trimestre_id) if trimestre_id in trimestre_ids else -1
    if idx < 0:
        return table_data
    
    total_row = ['Total', '']
    total_c2 = int(total_tp)  
    total_c3 = int(total_tpe)
    total_c4 = int(total_max_tot) 
    total_row.extend(['-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-', '-'])
    total_row[2] = str(total_c2)
    total_row[3] = str(total_c3)
    total_row[4] = str(total_c4)
    tj_val = int(totals['tj'])
    ex_val = int(totals['ex'])
    tot_val = int(totals['tot'])
    total_row[3 + idx * 3] = str(tj_val) if tj_val != 0 else '-'
    total_row[3 + idx * 3 + 1] = str(ex_val) if ex_val != 0 else '-'
    total_row[3 + idx * 3 + 2] = str(tot_val) if tot_val != 0 else '-'
    total_tot_an = int(total_max_tot) 
    total_row.extend([str(total_tot_an), '', '', ''])
    table_data.append(total_row)
    
    return table_data

def finalize_table_data_par_trimestre(table_data, ligne_idx, trimestre_id, trimestre_ids, cours_data):
    table_data.extend([
        ['%', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''],
        ['Place', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
    ])

    total_notes_obtenues = 0
    total_max_tot = 0
    cours_inclus = []

    try:
        idx = trimestre_ids.index(trimestre_id)
    except ValueError:
        return table_data

    col_sums = {5 + idx * 3: 0, 6 + idx * 3: 0, 7 + idx * 3: 0}  
    for row in table_data[2:]:
        if row[0] in ['%', 'Place']:
            continue
        notes_obtenues = 0
        cours_nom = row[1] or row[0]
        cours_info = next((c for c in cours_data if c['nom'] == cours_nom), None)

        if cours_info:
            for col_idx in [5 + idx * 3, 6 + idx * 3]:  
                if col_idx == 6 + idx * 3 and cours_info['TPE'] == 0:  
                    continue
                try:
                    note = int(float(row[col_idx])) if row[col_idx] != '-' else 0
                    notes_obtenues += note
                    col_sums[col_idx] += note
                except (ValueError, TypeError):
                    pass
            col_idx = 7 + idx * 3  
            try:
                note = int(float(row[col_idx])) if row[col_idx] != '-' else 0
                col_sums[col_idx] += note
            except (ValueError, TypeError):
                pass

            max_tot = cours_info['TP'] + cours_info['TPE']
        else:
            max_tot = 0

        total_notes_obtenues += notes_obtenues
        total_max_tot += max_tot
        cours_inclus.append(cours_nom)

        try:
            row[15] = str(notes_obtenues) if notes_obtenues > 0 else '0'
        except (ValueError, TypeError):
            row[15] = '-'

    total_index = next(i for i, row in enumerate(table_data) if row[0] == 'Total')
    try:
        table_data[total_index][15] = str(total_notes_obtenues) if total_notes_obtenues > 0 else '0'
    except (ValueError, TypeError):
        table_data[total_index][15] = '-'

    percent_index = next(i for i, row in enumerate(table_data) if row[0] == '%')
    try:
        tj_max = sum(c['TP'] for c in cours_data)
        ex_max = sum(c['TPE'] for c in cours_data)
        tot_max = tj_max + ex_max


        for col_idx in [5 + idx * 3, 6 + idx * 3, 7 + idx * 3]:
            max_val = tj_max if col_idx == 5 + idx * 3 else ex_max if col_idx == 6 + idx * 3 else tot_max
            if max_val > 0:
                col_percent = (col_sums[col_idx] * 100) / max_val
                table_data[percent_index][col_idx] = f"{col_percent:.2f}%"
            else:
                table_data[percent_index][col_idx] = '-'

        total_col = 7 if idx == 0 else 10 if idx == 1 else 13
        if tot_max > 0:
            total_percent = (col_sums[7 + idx * 3] * 100) / tot_max
            table_data[total_index][total_col] = f"{total_percent:.2f}%"
        else:
            table_data[total_index][total_col] = '-'

    except (ValueError, TypeError) as e:
        for col_idx in [5 + idx * 3, 6 + idx * 3, 7 + idx * 3]:
            table_data[percent_index][col_idx] = '-'

    return table_data

def create_results_table_par_trimestre(id_eleve, id_annee, id_campus, id_cycle, id_classe, id_trimestre):
    """Fonction principale pour créer le tableau de résultats pour un trimestre."""
    try:
        trimestres = get_trimestres(id_annee,id_campus,id_cycle,id_classe)
        trimestre_ids = [t[0] for t in trimestres]
        trimestre_noms = [t[1] for t in trimestres]
        if id_trimestre not in trimestre_ids:
            raise ValueError(f"Trimestre {id_trimestre} non actif.")
    except ValueError as e:
        raise ValueError(f"Erreur lors de la récupération des trimestres : {str(e)}")

    tj_sigle, ex_sigle = get_note_types()
    cours_classe = get_cours_classe(id_annee, id_campus, id_cycle, id_classe)
    domaines_dict = build_domaines_dict(cours_classe)
    groupes = build_groupes(domaines_dict)
    table_data = initialize_table_data(trimestre_noms, tj_sigle, ex_sigle)
    
    table_data, totals, total_tp, total_tpe, total_max_tot = add_cours__notes_in_rows_par_trimestre(
        table_data, groupes, id_eleve, id_annee, id_campus, id_cycle, id_classe, id_trimestre, trimestre_ids
    )
    ligne_idx = len(table_data)
    table_data = add_conduite_and_totals_par_trimestre(
        table_data, totals, id_trimestre, trimestre_ids, total_tp, total_tpe, total_max_tot
    )
    table_data = finalize_table_data_par_trimestre(table_data, ligne_idx, id_trimestre, trimestre_ids)
    col_widths = [1.4 * inch, 1.2 * inch] + [0.55 * inch] * 17
    table = Table(table_data, colWidths=col_widths, repeatRows=2)
    styled_table = stylize_table(table, table_data)
    return [styled_table]


@csrf_exempt
@require_POST
@module_required("Evaluation")
@transaction.atomic
def annuler_deliberation(request):
    try:
        data = json.loads(request.body)

        required_fields = ["id_annee", "id_classe", "id_campus", "id_cycle", "type"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return JsonResponse(
                {"error": f"Paramètres manquants : {', '.join(missing)}"},
                status=400
            )

        id_annee   = data["id_annee"]
        id_classe  = data["id_classe"]
        id_campus  = data["id_campus"]
        id_cycle   = data["id_cycle"]
        type_annul = data["type"]

        id_trimestre = data.get("id_trimestre")
        id_periode   = data.get("id_periode")

        deleted_count = 0
        message_suffix = ""

        if type_annul == "periode":
            if not id_trimestre or not id_periode:
                return JsonResponse({"error": "id_trimestre et id_periode requis pour type 'periode'"}, status=400)

            # Suppression des résultats périodiques pour cette période précise
            deleted_count = Deliberation_periodique_resultat.objects.filter(
                id_annee_id=id_annee,
                id_classe_id=id_classe,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_trimestre_id=id_trimestre,
                id_periode_id=id_periode,
            ).delete()[0]

            if deleted_count > 0:
                # Remise en "En cours" de la période et du trimestre
                Annee_periode.objects.filter(
                    id_trimestre_annee__id_trimestre=id_trimestre,
                    id_periode=id_periode,
                    id_annee_id=id_annee,
                    id_campus_id=id_campus,
                    id_cycle_id=id_cycle,
                    id_classe_id=id_classe,
                ).values_list('id_periode', flat=True)
                from django.db import connection
                with connection.cursor() as cursor:
                    if per_ids:
                        phs = ','.join(['%s'] * len(per_ids))
                        cursor.execute(f"UPDATE countryStructure.etablissements_annees_periodes SET isOpen=1 WHERE id IN ({phs})", list(per_ids))
                    cursor.execute("UPDATE countryStructure.etablissements_annees_trimestres SET isOpen=1 WHERE id=%s", [id_trimestre])

            message_suffix = f"période {id_periode} du trimestre {id_trimestre}"

        elif type_annul == "trimestre":
            if not id_trimestre:
                return JsonResponse({"error": "id_trimestre requis pour type 'trimestre'"}, status=400)

            # Suppression de TOUS les résultats liés à ce trimestre
            deleted_trim = Deliberation_trimistrielle_resultat.objects.filter(
                id_annee_id=id_annee,
                id_classe_id=id_classe,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_trimestre_id=id_trimestre,
            ).delete()[0]

            deleted_per = Deliberation_periodique_resultat.objects.filter(
                id_annee_id=id_annee,
                id_classe_id=id_classe,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_trimestre_id=id_trimestre,
            ).delete()[0]

            deleted_ex = Deliberation_examen_resultat.objects.filter(
                id_annee_id=id_annee,
                id_classe_id=id_classe,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
                id_trimestre_id=id_trimestre,
            ).delete()[0]

            deleted_count = deleted_trim + deleted_per + deleted_ex

            if deleted_count > 0:
                # Remise en "En cours" du trimestre et de toutes ses périodes
                from django.db import connection
                per_ids = list(Annee_periode.objects.filter(id_trimestre_annee__id_trimestre=id_trimestre).values_list('id_periode', flat=True).distinct())
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE countryStructure.etablissements_annees_trimestres SET isOpen=1 WHERE id=%s", [id_trimestre])
                    if per_ids:
                        phs = ','.join(['%s'] * len(per_ids))
                        cursor.execute(f"UPDATE countryStructure.etablissements_annees_periodes SET isOpen=1 WHERE id IN ({phs})", list(per_ids))

            message_suffix = f"trimestre {id_trimestre} (total supprimé : {deleted_count})"

        elif type_annul == "annee":
            deleted_count = Deliberation_annuelle_resultat.objects.filter(
                id_annee_id=id_annee,
                id_classe_id=id_classe,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
            ).delete()[0]

            if deleted_count > 0:
                # Remise en "En cours" du premier trimestre de l'année
                premier_trim = Annee_trimestre.objects.filter(
                    id_annee_id=id_annee,
                    id_classe_id=id_classe,
                    id_campus_id=id_campus,
                    id_cycle_id=id_cycle,
                ).order_by('id_trimestre').first()

                if premier_trim:
                    from django.db import connection
                    per_ids = list(Annee_periode.objects.filter(id_trimestre_annee=premier_trim).values_list('id_periode', flat=True).distinct())
                    with connection.cursor() as cursor:
                        cursor.execute("UPDATE countryStructure.etablissements_annees_trimestres SET isOpen=1 WHERE id=%s", [premier_trim.id_trimestre])
                        if per_ids:
                            phs = ','.join(['%s'] * len(per_ids))
                            cursor.execute(f"UPDATE countryStructure.etablissements_annees_periodes SET isOpen=1 WHERE id IN ({phs})", list(per_ids))

            message_suffix = "délibération annuelle"

        elif type_annul == "repechage":
            deleted_count = Deliberation_repechage_resultat.objects.filter(
                id_annee_id=id_annee,
                id_classe_id=id_classe,
                id_campus_id=id_campus,
                id_cycle_id=id_cycle,
            ).delete()[0]
            message_suffix = "repêchage"

        else:
            return JsonResponse({"error": f"Type d'annulation invalide : {type_annul}"}, status=400)

        if deleted_count == 0:
            return JsonResponse(
                {"warning": f"Aucune délibération trouvée pour {message_suffix}"},
                status=200
            )

        return JsonResponse({
            "success": True,
            "message": f"Délibération annulée avec succès ({deleted_count} enregistrement(s) supprimé(s)) – {message_suffix}"
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Format JSON invalide"}, status=400)
    except Exception as e:
        logger.exception("Erreur lors de l'annulation de délibération")
        return JsonResponse({"error": f"Erreur serveur : {str(e)}"}, status=500)


def safe_float(value, default=0.0):
    
    if value in (None, "-", "", " "):
        return default
    
    if isinstance(value, (int, float)):
        return float(value)
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def compute_percentages_from_table(id_annee, id_campus, id_cycle, id_classe, id_eleve, id_trimestre, style_center, style_normal):
    """
    Construit la table complète comme dans create_notes_table,
    applique tous les calculs, et retourne les pourcentages du trimestre donné.
    Retourne dict ou None en cas d'erreur.
    """
    table_data = []

    trimestres_data = get_trimestres(id_annee, id_campus, id_cycle, id_classe)
    if not trimestres_data or len(trimestres_data) != 3:
        logger.error("Trimestres non valides")
        return None

    # Entête trimestres
    nom_trim1 = trimestres_data[0][2] if trimestres_data else "PREMIER TRIMESTRE"
    nom_trim2 = trimestres_data[1][2] if trimestres_data else "SECOND TRIMESTRE"
    nom_trim3 = trimestres_data[2][2] if trimestres_data else "TROISIEME TRIMESTRE"

    table_data.append([
        Paragraph("<font color='black'><b>BRANCHES</b></font>", style_center),
        Paragraph(f"<font color='black'><b>{nom_trim1}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph(f"<font color='black'><b>{nom_trim2}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph(f"<font color='black'><b>{nom_trim3}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph("<font color='black'><b>TOTAL</b></font>", style_center), None
    ])

    periodes_par_trim = get_periodes_par_trimestre(trimestres_data, id_annee, id_campus, id_cycle, id_classe)
    sous_header = [Paragraph("BRANCHES", style_center)]
    for i in range(3):
        p1 = periodes_par_trim[i][0] if len(periodes_par_trim[i]) > 0 else "-"
        p2 = periodes_par_trim[i][1] if len(periodes_par_trim[i]) > 1 else "-"
        sous_header.extend([
            Paragraph("Max per", style_center), Paragraph(p1, style_center), Paragraph(p2, style_center),
            Paragraph("Max<br/>Exam", style_center), Paragraph("PTS.OBT", style_center),
            Paragraph("MAX TRIM", style_center), Paragraph("PTS.OBT", style_center),
        ])
    sous_header.extend([Paragraph("MAX", style_center), Paragraph("PTS.OBT", style_center)])
    table_data.append(sous_header)

    domaines_cours = get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe)
    notes_periodes = get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    notes_exam = get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)

    for groupe in domaines_cours:
        domaine_nom = groupe['domaine']
        table_data.append([Paragraph(f"<font color='black'><b>{domaine_nom}</b></font>", style_center)] + [None] * 22)

        for cpc in groupe['cours']:
            nom_cours = cpc.id_cours.cours
            ponderation = cpc.TPE if cpc.TPE is not None else "-"
            max_exam = float(ponderation) * 2 if isinstance(ponderation, (int, float)) else "-"
            max_trim_val = max_exam * 2 if max_exam != "-" else "-"
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
                if col in [1, 8, 15]:
                    row.append(Paragraph(str(ponderation), style_center))
                elif col in [4, 11, 18]:
                    row.append(Paragraph(str(max_exam), style_center))
                elif col in [5, 12, 19]:
                    note_ex = exam_notes.get(col, "-")
                    row.append(Paragraph(str(note_ex), style_center))
                elif col in [6, 13, 20]:
                    row.append(Paragraph(str(max_trim_val), style_center))
                elif col == 22:
                    row.append(Paragraph(str(float(max_annee) if max_trim_val != "-" else "-"), style_center))
                elif col == 23:
                    row.append(Paragraph("-", style_center))
                elif col in [2, 3, 9, 10, 16, 17]:
                    col_to_sigle = {2: "1e P", 3: "2e P", 9: "3e P", 10: "4e P", 16: "5e P", 17: "6e P"}
                    sigle = col_to_sigle[col]
                    note_val = notes_cours_periodes.get(sigle, "-")
                    row.append(Paragraph(str(note_val), style_center))
                else:
                    row.append(Paragraph("-", style_center))

            table_data.append(row)

        table_data.append([Paragraph("<b>Sous Total</b>", style_normal)] + [None] * 22)

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
        table_data.append([Paragraph(f"<b>{texte}</b>", style_normal)] + [None] * 22)

    # Calculs complets (comme dans le bulletin)
    calculer_sous_totaux_et_maxima(table_data, style_center)
    calculer_pts_obt_et_somme_finale(table_data, style_center)
    calculer_somme_pts_obt_maxima(table_data, style_center)
    calculer_pourcentages(table_data, style_center)
    calculer_pts_obt_trimestriels_et_annuel(table_data, style_center)

    # Recherche ligne POURCENTAGE
    ligne_pct_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph) and "POURCENTAGE" in str(row[0].text or "").upper():
            ligne_pct_idx = idx
            break

    if ligne_pct_idx is None:
        logger.error("Ligne POURCENTAGE introuvable")
        return None

    row_pct = table_data[ligne_pct_idx]
    while len(row_pct) < 24:
        row_pct.append(None)

    def safe_pct(col):
        if col >= len(row_pct) or not row_pct[col]:
            return 0.0
        try:
            txt = str(row_pct[col].text or "").strip().replace('%', '')
            return float(txt) if txt else 0.0
        except:
            return 0.0

    # Mapping selon trimestre
    if id_trimestre == trimestres_data[0][0]:
        return {
            "1e P": safe_pct(2),
            "2e P": safe_pct(3),
            "Ex T1": safe_pct(5),
            "Trim T1": safe_pct(7),
        }
    elif id_trimestre == trimestres_data[1][0]:
        return {
            "3e P": safe_pct(9),
            "4e P": safe_pct(10),
            "Ex T2": safe_pct(12),
            "Trim T2": safe_pct(14),
        }
    else:
        return {
            "5e P": safe_pct(16),
            "6e P": safe_pct(17),
            "Ex T3": safe_pct(19),
            "Trim T3": safe_pct(21),
        }

def compute_percentages_from_table_secondaire(id_annee, id_campus, id_cycle, id_classe, id_eleve, id_semestre, style_center, style_normal):
    table_data = []

    semestres_data = get_semestres(id_annee, id_campus, id_cycle, id_classe)
    if not semestres_data or len(semestres_data) != 2:
        logger.error("Configuration semestres incomplète (2 attendus)")
        return None

    nom_sem1 = semestres_data[0][1] if semestres_data else "PREMIER SEMESTRE"
    nom_sem2 = semestres_data[1][1] if semestres_data else "SECOND SEMESTRE"

    if nom_sem1 == "Semestre 1":
        nom_sem1 = "PREMIER SEMESTRE"
    if nom_sem2 == "Semestre 2":
        nom_sem2 = "SECOND SEMESTRE"

    # Entête
    table_data.append([
        Paragraph("<font color='black'><b>BRANCHES</b></font>", style_center),
        Paragraph(f"<font color='black'><b>{nom_sem1}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph(f"<font color='black'><b>{nom_sem2}</b></font>", style_center), None, None, None, None, None, None,
        Paragraph("<font color='black'><b>TOTAL GENERAL</b></font>", style_center), None,
        Paragraph("<font color='black'><b></b></font>", style_center),
        Paragraph("<font color='black'><b>EXAMEN DE REPECHAGE</b></font>", style_center)
    ])

    # Sous-header
    table_data.append([
        None,
        None, Paragraph("<font color='black'><b>TRAV.JOUR.</b></font>", style_center), None,
        Paragraph("<font color='black'><b>EXAM</b></font>", style_center), None,
        Paragraph("<font color='black'><b>TOT.SEM</b></font>", style_center), None,
        None, Paragraph("<font color='black'><b>TRAV.JOUR.</b></font>", style_center), None,
        Paragraph("<font color='black'><b>EXAM</b></font>", style_center), None,
        Paragraph("<font color='black'><b>TOT.SEM</b></font>", style_center), None,
        None, None,
        None,
        None
    ])

    table_data.append([
        Paragraph("BRANCHES", style_center),
        Paragraph("Max", style_center), Paragraph("1e P", style_center), Paragraph("2e P", style_center),
        None, None, None, None,
        Paragraph("Max", style_center), Paragraph("3e P", style_center), Paragraph("4e P", style_center),
        None, None, None, None,
        None, None,
        Paragraph("", style_center),
        Paragraph("%", style_center),
        Paragraph("Sign. prof.", style_center)
    ])

    domaines_cours = get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe)
    notes_periodes = get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    notes_exam = get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)

    for groupe in domaines_cours:
        domaine_nom = groupe['domaine']
        table_data.append([Paragraph(f"<font color='black'><b>{domaine_nom}</b></font>", style_center)] + [None] * 19)

        for cpc in groupe['cours']:
            nom_cours = cpc.id_cours.cours
            ponderation = cpc.TP if cpc.TP is not None else "-"
            exam = cpc.ponderation if cpc.ponderation is not None else "-"

            row = [Paragraph(nom_cours, style_normal)]
            id_cpc = cpc.id_cours_id
            notes_cours_periodes = notes_periodes.get(id_cpc, {})
            notes_cours_exam = notes_exam.get(id_cpc, {})

            exam_notes = {
                5: notes_cours_exam.get(semestres_data[0][0], "-"),
                12: notes_cours_exam.get(semestres_data[1][0], "-"),
            }

            val_exam_s1 = 0.0
            val_exam_s2 = 0.0

            for col in range(1, 20):
                if col in [2, 3, 9, 10]:
                    col_to_sigle = {2: "1e P", 3: "2e P", 9: "3e P", 10: "4e P"}
                    sigle = col_to_sigle[col]
                    note_val = notes_cours_periodes.get(sigle, "-")
                    row.append(Paragraph(str(note_val), style_center))

                elif col in [1, 8]:
                    row.append(Paragraph(str(ponderation), style_center))

                elif col in [4, 11]:
                    exam_val = exam if exam != "-" else "0"
                    row.append(Paragraph(str(exam_val), style_center))
                    if col == 4:
                        val_exam_s1 = float(exam_val)
                    if col == 11:
                        val_exam_s2 = float(exam_val)

                elif col in [5, 12]:
                    note_ex = exam_notes.get(col, "-")
                    row.append(Paragraph(str(note_ex), style_center))

                elif col == 6:  
                    val_tot_sem_s1 = val_exam_s1 * 2
                    row.append(Paragraph(str(round(val_tot_sem_s1, 2)), style_center))

                elif col == 13:  
                    val_tot_sem_s2 = val_exam_s2 * 2
                    row.append(Paragraph(str(round(val_tot_sem_s2, 2)), style_center))

                elif col == 7:  
                    tot_s1 = 0.0
                    try:
                        tot_s1 += float(row[2].text or 0) if len(row) > 2 and row[2] else 0.0
                        tot_s1 += float(row[3].text or 0) if len(row) > 3 and row[3] else 0.0
                        tot_s1 += float(row[5].text or 0) if len(row) > 5 and row[5] else 0.0
                    except:
                        tot_s1 = 0.0
                    row.append(Paragraph(str(round(tot_s1, 2)), style_center))

                elif col == 14: 
                    tot_s2 = 0.0
                    try:
                        tot_s2 += float(row[9].text or 0) if len(row) > 9 and row[9] else 0.0
                        tot_s2 += float(row[10].text or 0) if len(row) > 10 and row[10] else 0.0
                        tot_s2 += float(row[12].text or 0) if len(row) > 12 and row[12] else 0.0
                    except:
                        tot_s2 = 0.0
                    row.append(Paragraph(str(round(tot_s2, 2)), style_center))

                elif col == 15:
                    val_total_gen = val_tot_sem_s2 * 2  
                    row.append(Paragraph(str(val_total_gen), style_center))

                elif col in [16, 17, 18, 19]:
                    row.append(None)

                else:
                    row.append(Paragraph("-", style_center))

            table_data.append(row)

        table_data.append([Paragraph("<b>Sous Total</b>", style_normal)] + [None] * 19)

    table_data.append([None] * 20)

    lignes_finales = [
        "MAXIMA GENEREAUX",
        "POURCENTAGE",
        "PLACE/NBRE D'ELEVES",
        "CONDUITE",
        "APPLICATION",
        "SIGNATURE DU RESPONSABLE"
    ]

    for texte in lignes_finales:
        table_data.append([Paragraph(f"<b>{texte}</b>", style_normal)] + [None] * 19)

   
    calculer_sous_totaux_et_maxima_secondaire(table_data, style_center)
    calculer_pourcentages_secondaire(table_data, style_center)

   
    ligne_pct_idx = None
    for idx, row in enumerate(table_data):
        if len(row) > 0 and isinstance(row[0], Paragraph) and "POURCENTAGE" in str(row[0].text or "").upper():
            ligne_pct_idx = idx
            break

    if ligne_pct_idx is None:
        logger.error("Ligne POURCENTAGE non trouvée")
        return None

    row_pct = table_data[ligne_pct_idx]
    while len(row_pct) < 20:
        row_pct.append(None)

    def safe_pct(col):
        if col >= len(row_pct) or not row_pct[col]:
            return 0.0
        try:
            txt = str(row_pct[col].text or "").strip().replace('%', '')
            return float(txt) if txt else 0.0
        except:
            return 0.0

 
    if id_semestre == semestres_data[0][0]:
        return {
            "1e P": safe_pct(2),
            "2e P": safe_pct(3),
            "Ex semestre 1": safe_pct(5),
            "semestre 1": safe_pct(7),  
        }
    else:
        return {
            "3e P": safe_pct(9),
            "4e P": safe_pct(10),
            "Ex semestre 2": safe_pct(12),
            "semestre 2": safe_pct(14),
        }

def compute_percentages_from_table_superieur_terminal(id_annee, id_campus, id_cycle, id_classe, id_eleve, id_semestre, style_center, style_normal):
    table_data = []

    semestres_data = get_semestres(id_annee, id_campus, id_cycle, id_classe)
    if not semestres_data or len(semestres_data) != 2:
        logger.error("Configuration semestres incomplète (2 attendus)")
        return None

    semestre_idx = 0 if id_semestre == semestres_data[0][0] else 1

    nom_sem1 = semestres_data[0][1] if semestres_data else "PREMIER SEMESTRE"
    nom_sem2 = semestres_data[1][1] if semestres_data else "SECOND SEMESTRE"

    if nom_sem1 == "Semestre 1":
        nom_sem1 = "PREMIER SEMESTRE"
    if nom_sem2 == "Semestre 2":
        nom_sem2 = "SECOND SEMESTRE"

    table_data.append([
        Paragraph("<b>BRANCHES</b>", style_center),
        Paragraph(f"<b>{nom_sem1}</b>", style_center), None, None, None,
        Paragraph(f"<b>{nom_sem2}</b>", style_center), None, None, None,
        Paragraph("<b>TOTAL GENERAL</b>", style_center), None,
        Paragraph("<b>EXAMEN D'ETAT</b>", style_center),
        Paragraph("<b>EXAMEN DE REPECHAGE</b>", style_center)
    ])

    table_data.append([
        None,
        Paragraph("TRAV. JOUR", style_center), None,
        Paragraph("EXAM", style_center),
        Paragraph("TOT.", style_center),
        Paragraph("TRAV. JOUR", style_center), None,
        Paragraph("EXAM", style_center),
        Paragraph("TOT.", style_center),
        Paragraph("T.G", style_center),
        Paragraph("", style_center),
        Paragraph("", style_center),
        Paragraph("Points Obtenus", style_center),
    ])

    table_data.append([
        Paragraph("BRANCHES", style_center),
        Paragraph("1e P", style_center), Paragraph("2e P", style_center),
        Paragraph("EXAM", style_center), Paragraph("TOT.SEM", style_center),
        Paragraph("3e P", style_center), Paragraph("4e P", style_center),
        Paragraph("EXAM", style_center), Paragraph("TOT.SEM", style_center),
        Paragraph("", style_center),
        Paragraph("", style_center),
        Paragraph("M.EC", style_center)
    ])

    cours = recuperer_cours_obligatoires(id_annee, id_campus, id_cycle, id_classe)
    groupes = regrouper_cours_par_tp_tpe(cours)
    notes_periodes = get_student_period_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)
    notes_exam = get_student_exam_notes(id_eleve, id_annee, id_campus, id_cycle, id_classe)


    ajouter_cours_groupes_dans_table(
        table_data,
        groupes,
        notes_periodes,
        notes_exam,
        semestres_data,
        style_normal,
        style_center,
        id_annee=id_annee,
        id_campus=id_campus,
        id_cycle=id_cycle,
        id_classe=id_classe,
        start_row=4,
        max_row=40
    )

    
    lignes_finales = [
        "MAXIMA GENEREAUX",
        "TOTAUX",
        "POURCENTAGE",
        "PLACE/NBRE D'ELEVES",
        "APPLICATION",
        "CONDUITE",
        "SIGNATURE DU RESPONSABLE"
    ]

    for texte in lignes_finales:
        table_data.append([Paragraph(f"<b>{texte}</b>", style_normal)] + [None] * 12)

    totaux_col = [0.0] * 13
    maxima_col = [0.0] * 13

    # 1. Calcul des maxima (comme dans ton code original)
    for (tp1, tp2), cours_du_groupe in groupes.items():
        nb_cours = len(cours_du_groupe)
        somme = tp1 + tp2
        double_somme = somme * 2

        maxima_col[1] += tp1 * nb_cours
        maxima_col[2] += tp2 * nb_cours
        maxima_col[3] += somme * nb_cours
        maxima_col[4] += double_somme * nb_cours

        maxima_col[5] += tp1 * nb_cours
        maxima_col[6] += tp2 * nb_cours
        maxima_col[7] += somme * nb_cours
        maxima_col[8] += double_somme * nb_cours

        maxima_col[9] += (double_somme + double_somme) * nb_cours

    # 2. Calcul des totaux des cours (boucle sur les lignes de cours)
    for row in table_data[3:]:  
        if len(row) < 9 or row[0] is None or not isinstance(row[0], Paragraph):
            continue

        texte = row[0].text.strip()
        if "Sous Total" in texte or "MAXIMA" in texte or "POURCENTAGE" in texte:
            continue

        for col in range(1, 10):
            if col < len(row) and row[col]:
                try:
                    val_text = str(row[col].text).strip()
                    if val_text and val_text not in ["", "-"]:
                        val = float(val_text)
                        totaux_col[col] += val
                except:
                    pass

    # 3. Calcul des pourcentages par composante
    pct_dict = {}
    nb_cours = len(groupes) if groupes else 1

    def safe_pct(val, max_val=100.0):
        if max_val == 0:
            return 0.0
        pct = (val / max_val) * 100
        return max(0.0, min(100.0, pct))

    if id_semestre == semestres_data[0][0]:
        pct_dict["1e P"] = safe_pct(totaux_col[1], maxima_col[1])
        pct_dict["2e P"] = safe_pct(totaux_col[2], maxima_col[2])
        pct_dict["Ex semestre 1"] = safe_pct(totaux_col[3], maxima_col[3])
        pct_dict["semestre 1"] = round(
            (pct_dict["1e P"] + pct_dict["2e P"] + pct_dict["Ex semestre 1"]) / 3,
            2
        )
    else:
        pct_dict["3e P"] = safe_pct(totaux_col[5], maxima_col[5])
        pct_dict["4e P"] = safe_pct(totaux_col[6], maxima_col[6])
        pct_dict["Ex semestre 2"] = safe_pct(totaux_col[7], maxima_col[7])
        pct_dict["semestre 2"] = round(
            (pct_dict["3e P"] + pct_dict["4e P"] + pct_dict["Ex semestre 2"]) / 3,
            2
        )
    return pct_dict

@transaction.atomic
def deliberer_primaire_bytrimestre_rdc(id_annee, id_campus, id_cycle, id_classe, id_trimestre):
    try:
        annee     = Annee.objects.get(id_annee=id_annee)
        campus    = Campus.objects.get(id_campus=id_campus)
        cycle     = Classe_cycle_actif.objects.get(id_cycle_actif=id_cycle)
        classe    = Classe_active.objects.get(id_classe_active=id_classe)
        trimestre = Annee_trimestre.objects.get(
            id_annee=id_annee, id_campus=id_campus, id_cycle=id_cycle,
            id_classe=id_classe, id_trimestre=id_trimestre
        )

        if not trimestre.isOpen:
            return False, f"Trimestre non disponible (clôturé)", []

        inscriptions = Eleve_inscription.objects.filter(
            id_annee_id=id_annee, id_campus_id=id_campus,
            id_classe_cycle_id=id_cycle, id_classe_id=id_classe,
            status=1
        ).select_related('id_eleve')

        if not inscriptions.exists():
            return False, "Aucun élève inscrit", []

        total_eleves = inscriptions.count()

        trimestres_data = get_trimestres(id_annee, id_campus, id_cycle, id_classe)
        trimestre_idx = next((i for i, t in enumerate(trimestres_data) if t[0] == id_trimestre), -1)
        if trimestre_idx == -1:
            return False, "Trimestre invalide", []
        
        if trimestre_idx == 0:
            mapping = [
                ("1e P", 2, True),
                ("2e P", 3, True),
                ("Ex T1", 5, False),
                ("Trim T1", 7, False),
            ]
        elif trimestre_idx == 1:
            mapping = [
                ("3e P", 9, True),
                ("4e P", 10, True),
                ("Ex T2", 12, False),
                ("Trim T2", 14, False),
            ]
        else:
            mapping = [
                ("5e P", 16, True),
                ("6e P", 17, True),
                ("Ex T3", 19, False),
                ("Trim T3", 21, False),
            ]

        results_global = []  
        period_classements = defaultdict(list)   
        exam_classements   = defaultdict(list)   

        for inscription in inscriptions:
            eleve = inscription.id_eleve

            pct_dict = compute_percentages_from_table(
                id_annee, id_campus, id_cycle, id_classe,
                eleve.id_eleve, id_trimestre,
                style_center, style_normal
            )

            if pct_dict is None:
                logger.error(f"Échec calcul pour {eleve}")
                continue

            pct_trimestre = pct_dict.get(f"Trim T{trimestre_idx+1}", 0.0)

            results_global.append({
                'eleve': eleve,
                'pourcentage': pct_trimestre,
                'place': None
            })

           
            for label, col, is_periode in mapping:
                pct = pct_dict.get(label, 0.0)
                if is_periode:
                    period_classements[label].append((eleve, pct))
                else:
                    exam_classements[label].append((eleve, pct))

        # ───────────────────────────────────────────────
        # 1. Classement trimestriel global (1/N)
        # ───────────────────────────────────────────────
        results_global.sort(key=lambda x: x['pourcentage'], reverse=True)
        for rank, res in enumerate(results_global, 1):
            res['place'] = f"{rank}/{total_eleves}"

 
        Deliberation_trimistrielle_resultat.objects.filter(
            id_annee=annee, id_campus=campus,
            id_cycle=cycle, id_classe=classe,
            id_trimestre=trimestre
        ).delete()

        for res in results_global:
            Deliberation_trimistrielle_resultat.objects.create(
                id_eleve=res['eleve'],
                id_annee=annee,
                id_campus=campus,
                id_cycle=cycle,
                id_classe=classe,
                id_trimestre=trimestre,
                pourcentage=res['pourcentage'],
                place=res['place']
            )

        # ───────────────────────────────────────────────
        # 2. Classement séparé + sauvegarde pour chaque période
        # ───────────────────────────────────────────────
        for label, eleves_list in period_classements.items():
            eleves_list.sort(key=lambda x: x[1], reverse=True)
            for rank, (eleve, pct) in enumerate(eleves_list, 1):
                place_str = f"{rank}/{total_eleves}"

                periode_obj = Annee_periode.objects.filter(
                    id_annee_id=id_annee,
                    id_campus_id=id_campus,
                    id_cycle_id=id_cycle,
                    id_classe_id=id_classe,
                    id_trimestre_annee_id=trimestre.id_trimestre,
                    periode__periode=label.strip()
                ).first()
                if periode_obj:

                    Deliberation_periodique_resultat.objects.update_or_create(
                        id_eleve=eleve,
                        id_annee=annee,
                        id_campus=campus,
                        id_cycle=cycle,
                        id_classe=classe,
                        id_trimestre=trimestre,
                        id_periode=periode_obj,  
                        defaults={
                            'pourcentage': pct,
                            'place': place_str
                        }
                    )
                else :
                   return False, f"Période '{label}' non trouvée pour trimestre {trimestre.id_trimestre}", []
                    
                    

        # ───────────────────────────────────────────────
        # 3. Classement séparé + sauvegarde pour chaque examen
        # ───────────────────────────────────────────────
        for label, eleves_list in exam_classements.items():
            eleves_list.sort(key=lambda x: x[1], reverse=True)
            for rank, (eleve, pct) in enumerate(eleves_list, 1):
                place_str = f"{rank}/{total_eleves}"

                Deliberation_examen_resultat.objects.update_or_create(
                    id_eleve=eleve,
                    id_annee=annee,
                    id_campus=campus,
                    id_cycle=cycle,
                    id_classe=classe,
                    id_trimestre=trimestre,
                    defaults={
                        'pourcentage': pct,
                        'place': place_str
                    }
                )

        _update_trimestre_etat_et_inscriptions(annee, campus, cycle, classe, trimestre, inscriptions)

        return True, f"Délibération terminée – {total_eleves} élèves classés", results_global

    except Exception as e:
        logger.exception("Erreur délibération RDC")
        return False, str(e), []



@transaction.atomic
def deliberer_trimestre_bdi(id_annee, id_campus, id_cycle, id_classe, id_trimestre):
    
    try:
        annee     = Annee.objects.get(id_annee=id_annee)
        campus    = Campus.objects.get(id_campus=id_campus)
        cycle     = Classe_cycle_actif.objects.get(id_cycle_actif=id_cycle)
        classe    = Classe_active.objects.get(id_classe_active=id_classe)
        trimestre = Annee_trimestre.objects.get(
            id_annee=id_annee, id_campus=id_campus, id_cycle=id_cycle,
            id_classe=id_classe, id_trimestre=id_trimestre
        )

        is_valid, msg = verify_evaluations_ponderations(id_annee, id_campus, id_cycle, id_classe, id_trimestre)
        if not is_valid:
            return False, msg, []

        inscriptions = Eleve_inscription.objects.filter(
            id_annee_id=id_annee, id_campus_id=id_campus,
            id_classe_cycle_id=id_cycle, id_classe_id=id_classe,
            status=1
        ).select_related('id_eleve')

        if not inscriptions.exists():
            return False, "Aucun élève inscrit", []

        trimestres     = get_trimestres(id_annee, id_campus, id_cycle, id_classe)
        trimestre_ids  = [t[0] for t in trimestres]
        trimestre_noms = [t[1] for t in trimestres]

        tj_sigle, ex_sigle = get_note_types()
        cours_classe = get_cours_classe(id_annee, id_campus, id_cycle, id_classe)
        domaines_dict = build_domaines_dict(cours_classe)
        groupes = build_groupes(domaines_dict)

        results = []

        for inscription in inscriptions:
            eleve = inscription.id_eleve
            id_eleve = eleve.id_eleve

            table_data = initialize_table_data(trimestre_noms, tj_sigle, ex_sigle)

            table_data, totals, total_tp, total_tpe, total_max_tot = add_cours__notes_in_rows_par_trimestre(
                table_data, groupes, id_eleve, id_annee, id_campus, id_cycle, id_classe, id_trimestre, trimestre_ids
            )

            table_data = add_conduite_and_totals_par_trimestre(
                table_data, totals, id_trimestre, trimestre_ids, total_tp, total_tpe, total_max_tot
            )

            table_data = finalize_table_data_par_trimestre(table_data, len(table_data), id_trimestre, trimestre_ids, [{'nom': str(c.id_cours.cours), 'TP': c.TP, 'TPE': c.TPE} for c in cours_classe])

            total_index = next(i for i, row in enumerate(table_data) if row[0] == 'Total')
            col = 7 if id_trimestre == trimestre_ids[0] else 10 if id_trimestre == trimestre_ids[1] else 13
            pourcentage_str = table_data[total_index][col]
            pourcentage = float(pourcentage_str.replace('%', '')) if pourcentage_str and pourcentage_str != '-' else 0.0

            results.append({
                'id_eleve': id_eleve,
                'eleve': eleve,
                'pourcentage': pourcentage,
                'place': None
            })

        results.sort(key=lambda x: x['pourcentage'], reverse=True)

        def format_place(rank, genre):
            if rank == 1: return '1ère' if genre == 'F' else '1er'
            if rank == 2: return '2ème'
            if rank == 3: return '3ème'
            return f"{rank}ème"

        for rank, res in enumerate(results, 1):
            res['place'] = format_place(rank, res['eleve'].genre)

        Deliberation_trimistrielle_resultat.objects.filter(
            id_annee_id=id_annee, id_campus_id=id_campus,
            id_cycle_id=id_cycle, id_classe_id=id_classe,
            id_trimestre=trimestre
        ).delete()

        for r in results:
            Deliberation_trimistrielle_resultat.objects.create(
                id_eleve=r['eleve'], id_annee=annee, id_campus=campus,
                id_cycle=cycle, id_classe=classe, id_trimestre=trimestre,
                pourcentage=r['pourcentage'], place=r['place']
            )

        _update_trimestre_etat_et_inscriptions(annee, campus, cycle, classe, trimestre, inscriptions)

        return True, f"Délibération terminée – {len(results)} élèves", results

    except Exception as e:
        logger.exception("Erreur BDI délibération")
        return False, f"Erreur : {str(e)}", []



@transaction.atomic
def _update_trimestre_etat_et_inscriptions(annee, campus, cycle, classe, current_trimestre, inscriptions):
    from django.db import connection

    # Close current trimestre in hub table (annee_trimestre is a VIEW, can't use .save())
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE countryStructure.etablissements_annees_trimestres SET isOpen = 0 WHERE id = %s",
            [current_trimestre.id_trimestre]
        )

    trimestre_ids = list(Annee_trimestre.objects.filter(
        id_annee=annee, id_campus=campus, id_cycle=cycle, id_classe=classe
    ).order_by('id_trimestre').values_list('id_trimestre', flat=True).distinct())

    idx = trimestre_ids.index(current_trimestre.id_trimestre)
    if idx < len(trimestre_ids) - 1:
        next_id = trimestre_ids[idx + 1]

        # Next trimestre stays open (isOpen=1 by default, no change needed)

        # Close periodes of current trimestre in hub table
        current_periode_ids = list(
            Annee_periode.objects.filter(
                id_trimestre_annee_id=current_trimestre.id_trimestre,
                id_annee=annee, id_campus=campus, id_cycle=cycle, id_classe=classe
            ).values_list('id_periode', flat=True).distinct()
        )

        with connection.cursor() as cursor:
            if current_periode_ids:
                placeholders = ','.join(['%s'] * len(current_periode_ids))
                cursor.execute(
                    f"UPDATE countryStructure.etablissements_annees_periodes SET isOpen = 0 WHERE id IN ({placeholders})",
                    current_periode_ids
                )
            # Next trimestre's periodes are already open by default

        # Note: No need to create inscriptions per trimester.
        # Students are enrolled per class — once enrolled, they're automatically
        # enrolled for all trimesters, semesters, and periods.


@transaction.atomic
def delibere_educationBase_rdc(id_annee, id_campus, id_cycle, id_classe, id_trimestre):
    try:
        annee     = Annee.objects.get(id_annee=id_annee)
        campus    = Campus.objects.get(id_campus=id_campus)
        cycle     = Classe_cycle_actif.objects.get(id_cycle_actif=id_cycle)
        classe    = Classe_active.objects.get(id_classe_active=id_classe)

        trimestre = Annee_trimestre.objects.get(
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle=id_cycle,
            id_classe=id_classe,
            id_trimestre=id_trimestre
        )

        if not trimestre.isOpen:
            return False, f"Trimestre {trimestre.trimestre.trimestre} non disponible (clôturé)", []

        inscriptions = Eleve_inscription.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_classe_cycle_id=id_cycle,
            id_classe_id=id_classe,
            status=1
        ).select_related('id_eleve').order_by('id_eleve__nom', 'id_eleve__prenom')

        if not inscriptions.exists():
            return False, "Aucun élève inscrit actif pour ce trimestre", []

        total_eleves = inscriptions.count()
        logger.info(f"Délibération Trimestre {trimestre.trimestre.trimestre} – {total_eleves} élèves")

        # Récupération des semestres (2 attendus)
        semestres_data = get_semestres(id_annee, id_campus, id_cycle, id_classe)
        if len(semestres_data) != 2:
            return False, "Configuration semestres incomplète (2 attendus)", []

        semestre_idx = next((i for i, s in enumerate(semestres_data) if s[0] == id_trimestre), -1)
        if semestre_idx == -1:
            return False, "Semestre/Trimestre sélectionné non trouvé", []

        domaines_cours = get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe)
        if not domaines_cours:
            return False, "Aucun cours défini", []

        # Mapping selon semestre/trimestre
        if semestre_idx == 0:
            mapping = [
                ("1e P", 2, True),
                ("2e P", 3, True),
                ("Ex semestre 1", 5, False),
                ("semestre 1", 7, False),
            ]
        else:
            mapping = [
                ("3e P", 9, True),
                ("4e P", 10, True),
                ("Ex semestre 2", 12, False),
                ("semestre 2", 14, False),
            ]

        results_global = []
        classements_detail = defaultdict(list)

        for inscription in inscriptions:
            eleve = inscription.id_eleve

            pct_dict = compute_percentages_from_table_secondaire(
                id_annee, id_campus, id_cycle, id_classe,
                eleve.id_eleve, id_trimestre,
                style_center, style_normal
            )

            if pct_dict is None:
                logger.error(f"Échec calcul pour {eleve}")
                continue

            # Calcul manuel du % semestre (moyenne des composantes)
            if semestre_idx == 0:
                pct_semestre = round(
                    (pct_dict.get("1e P", 0.0) + pct_dict.get("2e P", 0.0) + pct_dict.get("Ex semestre 1", 0.0)) / 3,
                    2
                )
            else:
                pct_semestre = round(
                    (pct_dict.get("3e P", 0.0) + pct_dict.get("4e P", 0.0) + pct_dict.get("Ex semestre 2", 0.0)) / 3,
                    2
                )

            logger.info(f"{eleve.nom} {eleve.prenom} → PCT Semestre calculé = {pct_semestre}% | Détails = {pct_dict}")

            results_global.append({
                'eleve': eleve,
                'pourcentage': pct_semestre,
                'place': None,
                'details_pct': pct_dict
            })

            # Détails pour classements séparés
            for label, col, is_periode in mapping:
                pct = pct_dict.get(label, 0.0)
                classements_detail[label].append((eleve, pct, len(results_global)-1))

        # Classement global
        results_global.sort(key=lambda x: x['pourcentage'], reverse=True)
        for rank, res in enumerate(results_global, 1):
            res['place'] = f"{rank}/{total_eleves}"

        # Sauvegarde globale (trimestrielle ou semestrielle)
        Deliberation_trimistrielle_resultat.objects.filter(
            id_annee=annee, id_campus=campus,
            id_cycle=cycle, id_classe=classe,
            id_trimestre=trimestre
        ).delete()

        for res in results_global:
            Deliberation_trimistrielle_resultat.objects.create(
                id_eleve=res['eleve'],
                id_annee=annee,
                id_campus=campus,
                id_cycle=cycle,
                id_classe=classe,
                id_trimestre=trimestre,
                pourcentage=res['pourcentage'],
                place=res['place']
            )

        # Sauvegarde détaillée (périodes + examens)
        for label, items in classements_detail.items():
            items.sort(key=lambda x: x[1], reverse=True)
            for rank, (eleve_obj, pct, _) in enumerate(items, 1):
                place_str = f"{rank}/{total_eleves}"

                is_periode = "P" in label
                model = Deliberation_periodique_resultat if is_periode else Deliberation_examen_resultat

                defaults = {
                    'pourcentage': pct,
                    'place': place_str
                }

                filtre = {
                    'id_eleve': eleve_obj,
                    'id_annee': annee,
                    'id_campus': campus,
                    'id_cycle': cycle,
                    'id_classe': classe,
                    'id_trimestre': trimestre,
                }

                if is_periode:
                    # Pour les périodes → on cherche la période correspondante
                    periode_obj = Annee_periode.objects.filter(
                        id_annee_id=id_annee,
                        id_campus_id=id_campus,
                        id_cycle_id=id_cycle,
                        id_classe_id=id_classe,
                        id_trimestre_annee_id=trimestre.id_trimestre,  # ← semestre.id (pas id_trimestre)
                        periode__periode=label.strip()
                    ).first()

                    if periode_obj:
                        filtre['id_periode'] = periode_obj
                    else:
                        logger.warning(f"id_periode non trouvé pour {label} - élève {eleve_obj}")
                        continue  

                else:
            
                    pass

                # Sauvegarde
                model.objects.update_or_create(
                    **filtre,
                    defaults=defaults
                )
        # Mise à jour des états
        _update_trimestre_etat_et_inscriptions(annee, campus, cycle, classe, trimestre, inscriptions)

        return True, f"Délibération terminée – {total_eleves} élèves", results_global

    except ObjectDoesNotExist as e:
        return False, f"Objet manquant : {str(e)}", []
    except Exception as e:
        return False, f"Erreur système : {str(e)}", []
      
@transaction.atomic
def deliberer_superieur_terminal_rdc(id_annee, id_campus, id_cycle, id_classe, id_semestre):
    try:
        annee     = Annee.objects.get(id_annee=id_annee)
        campus    = Campus.objects.get(id_campus=id_campus)
        cycle     = Classe_cycle_actif.objects.get(id_cycle_actif=id_cycle)
        classe    = Classe_active.objects.get(id_classe_active=id_classe)

        semestre  = Annee_trimestre.objects.get(
            id_annee=id_annee,
            id_campus=id_campus,
            id_cycle=id_cycle,
            id_classe=id_classe,
            id_trimestre=id_semestre
        )

        if not semestre.isOpen:
            return False, f"Semestre {semestre.trimestre.trimestre} non disponible (clôturé)", []

        inscriptions = Eleve_inscription.objects.filter(
            id_annee_id=id_annee,
            id_campus_id=id_campus,
            id_classe_cycle_id=id_cycle,
            id_classe_id=id_classe,
            status=1
        ).select_related('id_eleve').order_by('id_eleve__nom', 'id_eleve__prenom')

        if not inscriptions.exists():
            return False, "Aucun élève inscrit actif pour ce semestre", []

        total_eleves = inscriptions.count()
        logger.info(f"Délibération Semestre {semestre.trimestre.trimestre} – {total_eleves} élèves")

        semestres_data = get_semestres(id_annee, id_campus, id_cycle, id_classe)
        if len(semestres_data) != 2:
            return False, "Configuration semestres incomplète (2 attendus)", []

        semestre_idx = next((i for i, s in enumerate(semestres_data) if s[0] == id_semestre), -1)
        if semestre_idx == -1:
            return False, "Semestre sélectionné non trouvé", []

        domaines_cours = get_cours_classe_rdc(id_annee, id_campus, id_cycle, id_classe)
        if not domaines_cours:
            return False, "Aucun cours défini", []

        if semestre_idx == 0:
            mapping = [
                ("1e P", 1, True),       
                ("2e P", 2, True),
                ("Ex semestre 1", 3, False),
                ("semestre 1", 4, False),
            ]
        else:
            mapping = [
                ("3e P", 5, True),
                ("4e P", 6, True),
                ("Ex semestre 2", 7, False),
                ("semestre 2", 8, False),
            ]

        results_global = []
        classements_detail = defaultdict(list)

        for inscription in inscriptions:
            eleve = inscription.id_eleve

            pct_dict = compute_percentages_from_table_superieur_terminal(
                id_annee, id_campus, id_cycle, id_classe,
                eleve.id_eleve, id_semestre,
                style_center, style_normal
            )

            if pct_dict is None:
                logger.error(f"Échec calcul pour {eleve}")
                continue

            if semestre_idx == 0:
                pct_semestre = round(
                    (pct_dict.get("1e P", 0.0) + pct_dict.get("2e P", 0.0) + pct_dict.get("Ex semestre 1", 0.0)) / 3,
                    2
                )
            else:
                pct_semestre = round(
                    (pct_dict.get("3e P", 0.0) + pct_dict.get("4e P", 0.0) + pct_dict.get("Ex semestre 2", 0.0)) / 3,
                    2
                )

            logger.info(f"{eleve.nom} {eleve.prenom} → PCT Semestre calculé = {pct_semestre}% | Détails = {pct_dict}")

            results_global.append({
                'eleve': eleve,
                'pourcentage': pct_semestre,
                'place': None,
                'details_pct': pct_dict
            })

            for label, col, is_periode in mapping:
                pct = pct_dict.get(label, 0.0)
                classements_detail[label].append((eleve, pct, len(results_global)-1))

        results_global.sort(key=lambda x: x['pourcentage'], reverse=True)
        for rank, res in enumerate(results_global, 1):
            res['place'] = f"{rank}/{total_eleves}"

        Deliberation_trimistrielle_resultat.objects.filter(
            id_annee=annee, id_campus=campus,
            id_cycle=cycle, id_classe=classe,
            id_trimestre=semestre
        ).delete()

        for res in results_global:
            Deliberation_trimistrielle_resultat.objects.create(
                id_eleve=res['eleve'],
                id_annee=annee,
                id_campus=campus,
                id_cycle=cycle,
                id_classe=classe,
                id_trimestre=semestre,
                pourcentage=res['pourcentage'],
                place=res['place']
            )

        for label, items in classements_detail.items():
            items.sort(key=lambda x: x[1], reverse=True)
            for rank, (eleve_obj, pct, _) in enumerate(items, 1):
                place_str = f"{rank}/{total_eleves}"

                is_periode = "P" in label
                model = Deliberation_periodique_resultat if is_periode else Deliberation_examen_resultat

                defaults = {
                    'pourcentage': pct,
                    'place': place_str
                }

                filtre = {
                    'id_eleve': eleve_obj,
                    'id_annee': annee,
                    'id_campus': campus,
                    'id_cycle': cycle,
                    'id_classe': classe,
                    'id_trimestre': semestre,
                }

                if is_periode:
                    periode_obj = Annee_periode.objects.filter(
                        id_annee_id=id_annee,
                        id_campus_id=id_campus,
                        id_cycle_id=id_cycle,
                        id_classe_id=id_classe,
                        id_trimestre_annee_id=semestre.id_trimestre,  
                        periode__periode=label.strip()
                    ).first()

                    if periode_obj:
                        filtre['id_periode'] = periode_obj
                    else:
                        continue  

                else:
            
                    pass

                model.objects.update_or_create(
                    **filtre,
                    defaults=defaults
                )
        _update_trimestre_etat_et_inscriptions(annee, campus, cycle, classe, semestre, inscriptions)

        return True, f"Délibération terminée – {total_eleves} élèves", results_global

    except ObjectDoesNotExist as e:
        return False, f"Objet manquant : {str(e)}", []
    except Exception as e:
        logger.exception("Erreur délibération supérieur RDC")
        return False, f"Erreur système : {str(e)}", []
    
    
@csrf_protect
@login_required
@module_required("Evaluation")
def deliberate_class_par_trimestre(request):
    if request.method != "GET" or not request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "error", "message": "Requête non autorisée"}, status=403)

    params = ['id_annee', 'id_campus', 'id_cycle', 'id_classe', 'id_trimestre']
    values = {p: request.GET.get(p) for p in params}

    if not all(values.values()):
        return JsonResponse({"status": "error", "message": "Paramètres manquants"}, status=400)

    try:
        ids = {k: int(v) for k, v in values.items()}
    except (ValueError, TypeError):
        return JsonResponse({"status": "error", "message": "Paramètres invalides"}, status=400)

    try:
        campus = Campus.objects.get(id_campus=ids['id_campus'])
        localisation = campus.localisation.upper() 

        if localisation == "RDC":
            gt_classe_objet = Classe_active.objects.filter(id_classe_active = ids['id_classe']).first()
            if not gt_classe_objet:
                return JsonResponse({"status": "error", "message": f"Classe active {ids['id_classe']} introuvable"}, status=404)
            classe_id = gt_classe_objet.classe_id
            classe_name = classe_id.classe.strip() if classe_id and classe_id.classe else ""

            # Classes primaires (1ère Année, 1ère Primaire, ... 6ème Primaire, 1er Langue, 1er SC, 1er Eco)
            classes_primaires = ['1ère Année', '1er Langue', '1er SC', '1er Eco',
                                 '1ère Primaire', '2ème Primaire', '3ème Primaire',
                                 '4ème Primaire', '5ème Primaire', '6ème Primaire']
            # Classes secondaire éducation de base (7ème, 8ème)
            classes_secondaire_eb = ['7ème A E.B', '8ème A E.B', '7ème', '8ème']
            # Classes cycle supérieur
            classes_superieur = ['4ème construction', '2ème Niveau Eléctricité Industrielle',
                                 '2sc MTP', '2ème LANGUE', '2ème Eco', '2ème BCT',
                                 '3ème MPT', '3ème BCT', '3ème ECO']

            if classe_name in classes_primaires:
                success, message, results = deliberer_primaire_bytrimestre_rdc(
                    ids['id_annee'], ids['id_campus'], ids['id_cycle'],
                    ids['id_classe'], ids['id_trimestre']
                )
            elif classe_name in classes_secondaire_eb:
                success, message, results = delibere_educationBase_rdc(
                    ids['id_annee'], ids['id_campus'], ids['id_cycle'],
                    ids['id_classe'], ids['id_trimestre']
                )
            elif classe_name in classes_superieur:
                success, message, results = deliberer_superieur_terminal_rdc(
                    ids['id_annee'], ids['id_campus'], ids['id_cycle'],
                    ids['id_classe'], ids['id_trimestre']
                )
            else:
               return JsonResponse({"status": "error", "message": f"Classe '{classe_name}' non prise en charge pour la délibération. Merci de vérifier."}, status=400)
                
                
        else:  
            success, message, results = deliberer_trimestre_bdi(
                ids['id_annee'], ids['id_campus'], ids['id_cycle'],
                ids['id_classe'], ids['id_trimestre']
            )

        response = {
            "status": "success" if success else "error",
            "message": message,
            "count": len(results) if results else 0,
        }

        if success:
            response["resultats"] = [
                {"id_eleve": r['eleve'].id_eleve, "pourcentage": r['pourcentage'], "place": r['place']}
                for r in results
            ]

        return JsonResponse(response, status=200 if success else 400)

    except ObjectDoesNotExist as e:
        return JsonResponse({"status": "error", "message": f"Objet introuvable : {str(e)}"}, status=404)
    except Exception as e:
        logger.exception("Erreur globale dans deliberate_class_par_trimestre")
        return JsonResponse({"status": "error", "message": f"Erreur serveur : {str(e)}"}, status=500)

