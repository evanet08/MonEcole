#!/usr/bin/env python3
"""
Script one-shot : synchronise les notes pondérées depuis eleve_note → note_bulletin
pour TOUTES les classes de l'année courante.
"""
import os, sys, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'MonEcole_project.settings'
sys.path.insert(0, '/var/www/vhosts/monecole.pro/httpdocs/monecole_pro')
django.setup()

from django.db import connections
import pymysql

def get_spoke_conn():
    db = connections['default'].settings_dict
    return pymysql.connect(
        host=db['HOST'], port=int(db.get('PORT', 3306)),
        user=db['USER'], password=db['PASSWORD'], database=db['NAME'],
        cursorclass=pymysql.cursors.DictCursor, autocommit=False
    )

def sync_class(cur, hub_cur, eac_id, etab_id, etab_annee_id):
    """Sync notes for one class (EAC)."""
    # Get business keys
    hub_cur.execute("""
        SELECT eac.classe_id AS bk_classe, eac.groupe AS bk_groupe, eac.section_id AS bk_section,
               ea.annee_id AS id_annee
        FROM etablissements_annees_classes eac
        JOIN etablissements_annees ea ON ea.id = eac.etablissement_annee_id
        WHERE eac.id = %s
    """, [eac_id])
    ctx = hub_cur.fetchone()
    if not ctx:
        return 0

    # Get campus
    cur.execute("SELECT idCampus FROM campus WHERE id_etablissement = %s AND is_active=1 LIMIT 1", [etab_id])
    campus_row = cur.fetchone()
    campus_id = campus_row['idCampus'] if campus_row else None

    # Get enrolled students
    cur.execute("""
        SELECT DISTINCT e.id_eleve
        FROM eleve_inscription ei JOIN eleve e ON e.id_eleve = ei.id_eleve_id
        WHERE ei.id_annee_id = %s AND ei.idCampus_id = %s
          AND ei.classe_id = %s AND ei.groupe <=> %s AND ei.section_id <=> %s AND ei.status = 1
    """, [ctx['id_annee'], campus_id, ctx['bk_classe'], ctx['bk_groupe'], ctx['bk_section']])
    eleve_ids = [r['id_eleve'] for r in cur.fetchall()]
    if not eleve_ids:
        return 0

    # Get cours_annee for this class
    hub_cur.execute("""
        SELECT cann.id_cours_annee, cann.maxima_tj, cann.maxima_exam
        FROM cours_annee cann
        JOIN cours ca ON ca.id_cours = cann.cours_id
        WHERE ca.classe_id = %s
    """, [ctx['bk_classe']])
    cours_rows = hub_cur.fetchall()
    if not cours_rows:
        return 0
    cours_ids = [r['id_cours_annee'] for r in cours_rows]
    cours_maximas_tj = {r['id_cours_annee']: r['maxima_tj'] for r in cours_rows}

    # Get ALL repartition configs
    hub_cur.execute("""
        SELECT rc.id AS config_id, rc.repartition_id, rc.parent_id, rc.has_parent,
               r.type_id, r.code, r.nom, r.taux_participation
        FROM repartition_configs_etab_annee rc
        JOIN repartition_instances r ON r.id_instance = rc.repartition_id
        WHERE rc.etablissement_annee_id = %s AND rc.is_open = 1
        ORDER BY rc.has_parent ASC, r.ordre ASC
    """, [etab_annee_id])
    all_configs = hub_cur.fetchall()

    child_configs = [c for c in all_configs if c['has_parent']]
    parent_configs = [c for c in all_configs if not c['has_parent']]

    # Get note_types per repartition type
    type_ids = set(c['type_id'] for c in all_configs)
    nt_by_type = {}
    for tid in type_ids:
        hub_cur.execute("""
            SELECT rtn.ponderation_max, rtn.source_type, nt.id_type_note, nt.sigle
            FROM repartition_type_notes rtn
            JOIN note_types nt ON nt.id_type_note = rtn.note_type_id
            WHERE rtn.repartition_type_id = %s AND rtn.is_active = 1
            ORDER BY rtn.ordre
        """, [tid])
        nt_by_type[tid] = hub_cur.fetchall()

    calculated = 0

    # PHASE 1: Children (periods → TJ from evaluations)
    for cfg in child_configs:
        config_id = cfg['config_id']
        nts = nt_by_type.get(cfg['type_id'], [])
        tj_nt = next((n for n in nts if n['sigle'] == 'TJ'), None)
        if not tj_nt:
            continue
        tj_nt_id = tj_nt['id_type_note']
        taux = float(cfg['taux_participation']) if cfg['taux_participation'] else 100.0

        # Total taux for siblings
        hub_cur.execute("""
            SELECT COALESCE(SUM(r.taux_participation), 0) AS total_taux
            FROM repartition_configs_etab_annee rc
            JOIN repartition_instances r ON r.id_instance = rc.repartition_id
            WHERE rc.etablissement_annee_id = %s AND r.type_id = %s AND rc.is_open = 1
        """, [etab_annee_id, cfg['type_id']])
        total_taux = float(hub_cur.fetchone()['total_taux']) or taux

        for cours_id in cours_ids:
            c_maxima_tj = cours_maximas_tj.get(cours_id)
            if c_maxima_tj and total_taux > 0:
                period_max = round(float(c_maxima_tj) * (taux / total_taux), 2)
            else:
                period_max = tj_nt['ponderation_max'] or 20

            # Evaluations assigned to this config+cours
            cur.execute("""
                SELECT ev.id_evaluation, ev.ponderer_eval
                FROM evaluation ev
                JOIN evaluation_repartition er ON er.id_evaluation = ev.id_evaluation
                WHERE er.id_repartition_config = %s AND ev.id_cours_classe_id = %s AND ev.id_etablissement = %s
            """, [config_id, cours_id, etab_id])
            evals = cur.fetchall()
            if not evals:
                continue

            eval_ids = [e['id_evaluation'] for e in evals]
            total_max_evals = sum(e['ponderer_eval'] or 0 for e in evals)
            if total_max_evals == 0:
                continue

            ph = ','.join(['%s'] * len(eval_ids))
            for eleve_id in eleve_ids:
                cur.execute(f"""
                    SELECT COALESCE(SUM(en.note), 0) AS total_note
                    FROM eleve_note en WHERE en.id_eleve_id = %s AND en.id_evaluation_id IN ({ph})
                """, [eleve_id] + eval_ids)
                row = cur.fetchone()
                raw_total = float(row['total_note']) if row else 0
                scaled = round((raw_total / total_max_evals) * period_max, 2)

                cur.execute("""
                    INSERT INTO note_bulletin
                        (id_eleve_id, id_cours_annee, id_repartition_config, id_note_type,
                         note, maxima, source_type, date_calcul, id_etablissement)
                    VALUES (%s, %s, %s, %s, %s, %s, 'EVALUATIONS', NOW(), %s)
                    ON DUPLICATE KEY UPDATE
                        note = VALUES(note), maxima = VALUES(maxima), date_calcul = NOW(), updated_at = NOW()
                """, [eleve_id, cours_id, config_id, tj_nt_id, scaled, period_max, etab_id])
                calculated += 1

    # PHASE 2: Parents (HERITAGE + FORMULE)
    for cfg in parent_configs:
        config_id = cfg['config_id']
        nts = nt_by_type.get(cfg['type_id'], [])
        tj_nt = next((n for n in nts if n['sigle'] == 'TJ'), None)
        tot_nt = next((n for n in nts if n['sigle'] in ('TOTAL', 'TOT')), None)

        child_cfg_ids = [c['config_id'] for c in child_configs if c['parent_id'] == config_id]
        if not child_cfg_ids:
            hub_cur.execute("SELECT type_enfant_id FROM repartition_hierarchies WHERE type_parent_id = %s LIMIT 1", [cfg['type_id']])
            hr = hub_cur.fetchone()
            if hr:
                child_cfg_ids = [c['config_id'] for c in child_configs if c['type_id'] == hr['type_enfant_id']]

        # TJ HERITAGE
        if tj_nt and child_cfg_ids:
            tj_nt_id = tj_nt['id_type_note']
            child_type_ids = set(c['type_id'] for c in child_configs if c['config_id'] in child_cfg_ids)
            child_tj_nt_id = tj_nt_id
            for ct_id in child_type_ids:
                child_nts = nt_by_type.get(ct_id, [])
                ctj = next((n for n in child_nts if n['sigle'] == 'TJ'), None)
                if ctj:
                    child_tj_nt_id = ctj['id_type_note']
                    break

            ch_ph = ','.join(['%s'] * len(child_cfg_ids))
            for cours_id in cours_ids:
                c_maxima_tj = cours_maximas_tj.get(cours_id)
                heritage_max = int(c_maxima_tj) if c_maxima_tj else (tj_nt['ponderation_max'] or 20)
                for eleve_id in eleve_ids:
                    cur.execute(f"""
                        SELECT COALESCE(SUM(nb.note), 0) AS total, COALESCE(SUM(nb.maxima), 0) AS total_max
                        FROM note_bulletin nb
                        WHERE nb.id_eleve_id = %s AND nb.id_cours_annee = %s
                          AND nb.id_note_type = %s AND nb.id_repartition_config IN ({ch_ph})
                    """, [eleve_id, cours_id, child_tj_nt_id] + child_cfg_ids)
                    row = cur.fetchone()
                    raw_total = float(row['total']) if row and row['total'] else None
                    raw_max = float(row['total_max']) if row and row['total_max'] else None
                    if raw_total is not None and raw_max and raw_max > 0:
                        note_val = round((raw_total / raw_max) * heritage_max, 2)
                        cur.execute("""
                            INSERT INTO note_bulletin
                                (id_eleve_id, id_cours_annee, id_repartition_config, id_note_type,
                                 note, maxima, source_type, date_calcul, id_etablissement)
                            VALUES (%s, %s, %s, %s, %s, %s, 'HERITAGE', NOW(), %s)
                            ON DUPLICATE KEY UPDATE
                                note = VALUES(note), maxima = VALUES(maxima), date_calcul = NOW(), updated_at = NOW()
                        """, [eleve_id, cours_id, config_id, tj_nt_id, note_val, heritage_max, etab_id])
                        calculated += 1

        # TOTAL FORMULE
        if tot_nt:
            tot_nt_id = tot_nt['id_type_note']
            other_nt_ids = [n['id_type_note'] for n in nts if n['sigle'] not in ('TOTAL', 'TOT') and n['id_type_note'] != tot_nt_id]
            if other_nt_ids:
                o_ph = ','.join(['%s'] * len(other_nt_ids))
                for cours_id in cours_ids:
                    for eleve_id in eleve_ids:
                        cur.execute(f"""
                            SELECT COALESCE(SUM(nb.note), 0) AS total, COALESCE(SUM(nb.maxima), 0) AS total_max
                            FROM note_bulletin nb
                            WHERE nb.id_eleve_id = %s AND nb.id_cours_annee = %s
                              AND nb.id_repartition_config = %s AND nb.id_note_type IN ({o_ph})
                        """, [eleve_id, cours_id, config_id] + other_nt_ids)
                        row = cur.fetchone()
                        note_val = round(float(row['total']), 2) if row and row['total'] else None
                        total_max_val = int(row['total_max']) if row and row['total_max'] else (tot_nt['ponderation_max'] or 40)
                        if note_val is not None and note_val > 0:
                            cur.execute("""
                                INSERT INTO note_bulletin
                                    (id_eleve_id, id_cours_annee, id_repartition_config, id_note_type,
                                     note, maxima, source_type, date_calcul, id_etablissement)
                                VALUES (%s, %s, %s, %s, %s, %s, 'FORMULE', NOW(), %s)
                                ON DUPLICATE KEY UPDATE
                                    note = VALUES(note), maxima = VALUES(maxima), date_calcul = NOW(), updated_at = NOW()
                            """, [eleve_id, cours_id, config_id, tot_nt_id, note_val, total_max_val, etab_id])
                            calculated += 1

    return calculated

# MAIN
print("=== SYNC eleve_note → note_bulletin ===")
hub_db = connections['countryStructure'].settings_dict
hub_conn = pymysql.connect(
    host=hub_db['HOST'], port=int(hub_db.get('PORT', 3306)),
    user=hub_db['USER'], password=hub_db['PASSWORD'], database=hub_db['NAME'],
    cursorclass=pymysql.cursors.DictCursor
)
spoke_conn = get_spoke_conn()

try:
    with hub_conn.cursor() as hub_cur:
        # Get all active EACs with their etab info
        hub_cur.execute("""
            SELECT eac.id AS eac_id, ea.id AS etab_annee_id, ea.etablissement_id AS etab_id,
                   c.classe AS classe_nom
            FROM etablissements_annees_classes eac
            JOIN etablissements_annees ea ON ea.id = eac.etablissement_annee_id
            JOIN classes c ON c.id_classe = eac.classe_id
            WHERE ea.annee_id = (SELECT MAX(annee_id) FROM etablissements_annees)
            ORDER BY eac.id
        """)
        all_eacs = hub_cur.fetchall()
        print(f"Found {len(all_eacs)} classes to sync")

        total = 0
        with spoke_conn.cursor() as cur:
            for eac in all_eacs:
                print(f"  Syncing classe '{eac['classe_nom']}' (eac={eac['eac_id']}, etab={eac['etab_id']})...", end=" ")
                try:
                    n = sync_class(cur, hub_cur, eac['eac_id'], eac['etab_id'], eac['etab_annee_id'])
                    print(f"{n} notes")
                    total += n
                except Exception as e:
                    print(f"ERROR: {e}")

        spoke_conn.commit()
        print(f"\n=== DONE: {total} notes synchronized ===")
finally:
    hub_conn.close()
    spoke_conn.close()
