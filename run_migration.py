#!/usr/bin/env python3
"""
Execute migrate_add_id_pays.sql via pymysql.
Since pymysql doesn't support DELIMITER, we decompose the SQL
into individual statements and execute procedures manually.
"""
import pymysql
import sys

DB_USER = 'link3ictgroup'
DB_PASS = 'IctGroupuser123'
DB_HOST = 'localhost'
DB_PORT = 3306

def get_conn(db_name):
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=db_name, charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def add_id_pays_if_not_exists(cur, tbl_name, db_name):
    """Add id_pays column if it doesn't exist."""
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'id_pays'
    """, (db_name, tbl_name))
    row = cur.fetchone()
    if row['cnt'] == 0:
        cur.execute(f"ALTER TABLE `{tbl_name}` ADD COLUMN `id_pays` INT NOT NULL DEFAULT 2")
        print(f"  ✅ id_pays ajouté → {db_name}.{tbl_name}")
        return True
    else:
        print(f"  ⏭️  id_pays existe déjà → {db_name}.{tbl_name}")
        return False

def table_exists(cur, tbl_name, db_name):
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
    """, (db_name, tbl_name))
    return cur.fetchone()['cnt'] > 0

def update_existing(cur, tbl_name):
    cur.execute(f"UPDATE `{tbl_name}` SET id_pays = 2 WHERE id_pays = 0")
    affected = cur.rowcount
    if affected > 0:
        print(f"    ↳ {affected} lignes mises à jour")

# ============================================================
# PARTIE 1: countryStructure (Hub)
# ============================================================
print("=" * 60)
print("PARTIE 1: countryStructure (Hub)")
print("=" * 60)

hub_tables = [
    'sessions', 'sections', 'mentions', 'classes', 'cours', 'cours_annee',
    'repartition_types', 'repartition_hierarchies', 'repartition_configs_cycle',
    'repartition_configs_etab_annee', 'etablissements_annees',
    'etablissements_annees_classes', 'evaluation_types', 'note_types',
    'gestionnaires_etablissement', 'bulletin_model', 'bulletin_classe_model'
]

conn = get_conn('countryStructure')
try:
    with conn.cursor() as cur:
        for tbl in hub_tables:
            add_id_pays_if_not_exists(cur, tbl, 'countryStructure')
        conn.commit()
        print("\n  📊 Mise à jour données existantes (Hub)...")
        for tbl in hub_tables:
            update_existing(cur, tbl)
        conn.commit()
    print(f"\n  ✅ Hub: {len(hub_tables)} tables traitées\n")
finally:
    conn.close()

# ============================================================
# PARTIE 2: db_monecole (Spoke)
# ============================================================
print("=" * 60)
print("PARTIE 2: db_monecole (Spoke)")
print("=" * 60)

spoke_tables = [
    # Identité & Auth
    'campus', 'admin_users', 'otp_codes',
    # Personnel
    'personnel_categorie', 'diplome', 'specialite', 'vacation',
    'personnel_type', 'personnel', 'prestation',
    # Élèves
    'eleve', 'eleve_inscription', 'eleve_note_type', 'eleve_note',
    'eleve_conduite', 'parents', 'professions',
    # Classes
    'classe_deliberation', 'responsable_classe',
    # Enseignements
    'attribution_type', 'attribution_cours', 'user_enseignement', 'users_other_module',
    # Évaluations & Délibérations
    'deliberation_type', 'deliberation_annuelle_finalites',
    'deliberation_annuelle_conditions', 'deliberation_annuelle_resultats',
    'deliberation_periodique_resultats', 'deliberation_examen_resultats',
    'deliberation_trimistrielle_resultats', 'deliberation_repechage_resultats',
    'evaluation', 'note_bulletin',
    # Horaires
    'horaire_type', 'horaire', 'horaire_presence',
    # Modules
    'module', 'user_module',
    # Salles
    'salle',
    # Recouvrement
    'recouvrment_variable_categorie', 'recouvrment_variable',
    'recouvrment_variable_datebutoire', 'recouvrment_variable_derogation',
    'recouvrment_variable_prix', 'recouvrment_banque', 'recouvrment_compte',
    'recouvrment_reduction_prix', 'recouvrment_paiement',
    # Communication
    'communication', 'communication_group', 'communication_group_member',
]

# Tables orphelines (sans modèle Django)
orphan_tables = [
    'personnel_presence', 'communication_meeting', 'communication_meeting_invitee',
    'evaluation_repartition', 'document_type', 'document_eleve',
]

conn = get_conn('db_monecole')
try:
    with conn.cursor() as cur:
        for tbl in spoke_tables:
            add_id_pays_if_not_exists(cur, tbl, 'db_monecole')
        conn.commit()

        print("\n  📊 Mise à jour données existantes (Spoke)...")
        for tbl in spoke_tables:
            update_existing(cur, tbl)
        conn.commit()

        print(f"\n  ✅ Spoke: {len(spoke_tables)} tables traitées")

        print(f"\n  📋 Tables orphelines ({len(orphan_tables)}):")
        for tbl in orphan_tables:
            if table_exists(cur, tbl, 'db_monecole'):
                add_id_pays_if_not_exists(cur, tbl, 'db_monecole')
                update_existing(cur, tbl)
            else:
                print(f"  ⚠️  Table {tbl} n'existe pas, ignorée")
        conn.commit()

    print(f"\n  ✅ Orphelines traitées")
finally:
    conn.close()

# ============================================================
total = len(hub_tables) + len(spoke_tables) + len(orphan_tables)
print("\n" + "=" * 60)
print(f"✅ MIGRATION TERMINÉE — {total} tables traitées")
print("=" * 60)
