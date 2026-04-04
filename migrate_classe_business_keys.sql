-- ============================================================
-- MIGRATION SAFE PRODUCTION : id_classe_id (EAC) → Business Keys
-- Phase 1 : Ajout de colonnes + peuplement (NON-DESTRUCTIF)
-- L'ancien code continue de fonctionner pendant la transition.
-- ============================================================
-- Exécution : mysql -u root -p db_monecole < migrate_classe_business_keys.sql
-- ============================================================

SET @hub = 'countryStructure';

-- ─────────────────────────────────────────────────────────────
-- HELPER : Vérifie que la jointure EAC → classes fonctionne
-- ─────────────────────────────────────────────────────────────
SELECT 'VERIFICATION: EAC → classes mapping' AS step;
SELECT COUNT(*) AS total_eac,
       SUM(CASE WHEN c.id_classe IS NOT NULL THEN 1 ELSE 0 END) AS mapped
FROM countryStructure.etablissements_annees_classes eac
LEFT JOIN countryStructure.classes c ON c.id_classe = eac.classe_id;

-- ═════════════════════════════════════════════════════════════
-- BATCH 1 : CORE ÉVALUATIONS (4 tables)
-- ═════════════════════════════════════════════════════════════

-- ── 1. eleve_note ──
SELECT '1/19 eleve_note' AS migrating;
ALTER TABLE eleve_note
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE eleve_note t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id,
      t.groupe = eac.groupe,
      t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

SELECT COUNT(*) AS eleve_note_unmapped FROM eleve_note WHERE classe_id IS NULL AND id_classe_id IS NOT NULL;

-- ── 2. evaluation ──
SELECT '2/19 evaluation' AS migrating;
ALTER TABLE evaluation
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE evaluation t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id,
      t.groupe = eac.groupe,
      t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

SELECT COUNT(*) AS evaluation_unmapped FROM evaluation WHERE classe_id IS NULL AND id_classe_id IS NOT NULL;

-- ── 3. attribution_cours ──
SELECT '3/19 attribution_cours' AS migrating;
ALTER TABLE attribution_cours
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE attribution_cours t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id,
      t.groupe = eac.groupe,
      t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

SELECT COUNT(*) AS attribution_unmapped FROM attribution_cours WHERE classe_id IS NULL AND id_classe_id IS NOT NULL;

-- ── 4. user_enseignement ──
-- NOTE: cette table utilise classe_id_id comme nom de colonne (pas id_classe_id)
SELECT '4/19 user_enseignement' AS migrating;
ALTER TABLE user_enseignement
  ADD COLUMN IF NOT EXISTS classe_id_new INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE user_enseignement t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.classe_id_id
  SET t.classe_id_new = eac.classe_id,
      t.groupe = eac.groupe,
      t.section_id = eac.section_id
WHERE t.classe_id_new IS NULL;

SELECT COUNT(*) AS user_ens_unmapped FROM user_enseignement WHERE classe_id_new IS NULL AND classe_id_id IS NOT NULL;


-- ═════════════════════════════════════════════════════════════
-- BATCH 2 : DÉLIBÉRATIONS (6 tables)
-- ═════════════════════════════════════════════════════════════

-- ── 5. deliberation_annuelle_conditions ──
SELECT '5/19 deliberation_annuelle_conditions' AS migrating;
ALTER TABLE deliberation_annuelle_conditions
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE deliberation_annuelle_conditions t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 6. deliberation_annuelle_resultats ──
SELECT '6/19 deliberation_annuelle_resultats' AS migrating;
ALTER TABLE deliberation_annuelle_resultats
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE deliberation_annuelle_resultats t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 7. deliberation_trimistrielle_resultats ──
SELECT '7/19 deliberation_trimistrielle_resultats' AS migrating;
ALTER TABLE deliberation_trimistrielle_resultats
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE deliberation_trimistrielle_resultats t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 8. deliberation_periodique_resultats ──
SELECT '8/19 deliberation_periodique_resultats' AS migrating;
ALTER TABLE deliberation_periodique_resultats
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE deliberation_periodique_resultats t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 9. deliberation_examen_resultats ──
SELECT '9/19 deliberation_examen_resultats' AS migrating;
ALTER TABLE deliberation_examen_resultats
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE deliberation_examen_resultats t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 10. deliberation_repechage_resultats ──
SELECT '10/19 deliberation_repechage_resultats' AS migrating;
ALTER TABLE deliberation_repechage_resultats
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE deliberation_repechage_resultats t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;


-- ═════════════════════════════════════════════════════════════
-- BATCH 3 : STRUCTURE (5 tables)
-- ═════════════════════════════════════════════════════════════

-- ── 11. classe_deliberation ──
SELECT '11/19 classe_deliberation' AS migrating;
ALTER TABLE classe_deliberation
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE classe_deliberation t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 12. responsable_classe ──
SELECT '12/19 responsable_classe' AS migrating;
ALTER TABLE responsable_classe
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE responsable_classe t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 13. horaire ──
SELECT '13/19 horaire' AS migrating;
ALTER TABLE horaire
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE horaire t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 14. salle ──
SELECT '14/19 salle' AS migrating;
ALTER TABLE salle
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE salle t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 15. eleve_conduite ──
SELECT '15/19 eleve_conduite' AS migrating;
ALTER TABLE eleve_conduite
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE eleve_conduite t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;


-- ═════════════════════════════════════════════════════════════
-- BATCH 4 : RECOUVREMENT (5 tables)
-- ═════════════════════════════════════════════════════════════

-- ── 16. recouvrment_variable_datebutoire ──
SELECT '16/19 recouvrment_variable_datebutoire' AS migrating;
ALTER TABLE recouvrment_variable_datebutoire
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE recouvrment_variable_datebutoire t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 17. recouvrment_variable_derogation ──
SELECT '17/19 recouvrment_variable_derogation' AS migrating;
ALTER TABLE recouvrment_variable_derogation
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE recouvrment_variable_derogation t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 18. recouvrment_variable_prix ──
SELECT '18/19 recouvrment_variable_prix' AS migrating;
ALTER TABLE recouvrment_variable_prix
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE recouvrment_variable_prix t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 19a. recouvrment_reduction_prix ──
SELECT '19a/19 recouvrment_reduction_prix' AS migrating;
ALTER TABLE recouvrment_reduction_prix
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE recouvrment_reduction_prix t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;

-- ── 19b. recouvrment_paiement ──
SELECT '19b/19 recouvrment_paiement' AS migrating;
ALTER TABLE recouvrment_paiement
  ADD COLUMN IF NOT EXISTS classe_id INT NULL,
  ADD COLUMN IF NOT EXISTS groupe VARCHAR(5) NULL,
  ADD COLUMN IF NOT EXISTS section_id INT NULL;

UPDATE recouvrment_paiement t
  JOIN countryStructure.etablissements_annees_classes eac ON eac.id = t.id_classe_id
  SET t.classe_id = eac.classe_id, t.groupe = eac.groupe, t.section_id = eac.section_id
WHERE t.classe_id IS NULL;


-- ═════════════════════════════════════════════════════════════
-- RAPPORT FINAL : Vérification de la migration
-- ═════════════════════════════════════════════════════════════
SELECT '═══ RAPPORT DE MIGRATION ═══' AS report;

SELECT 'eleve_note' AS tbl, COUNT(*) AS total, SUM(classe_id IS NULL) AS unmapped FROM eleve_note
UNION ALL SELECT 'evaluation', COUNT(*), SUM(classe_id IS NULL) FROM evaluation
UNION ALL SELECT 'attribution_cours', COUNT(*), SUM(classe_id IS NULL) FROM attribution_cours
UNION ALL SELECT 'user_enseignement', COUNT(*), SUM(classe_id_new IS NULL) FROM user_enseignement
UNION ALL SELECT 'delib_annuelle_cond', COUNT(*), SUM(classe_id IS NULL) FROM deliberation_annuelle_conditions
UNION ALL SELECT 'delib_annuelle_res', COUNT(*), SUM(classe_id IS NULL) FROM deliberation_annuelle_resultats
UNION ALL SELECT 'delib_trim_res', COUNT(*), SUM(classe_id IS NULL) FROM deliberation_trimistrielle_resultats
UNION ALL SELECT 'delib_period_res', COUNT(*), SUM(classe_id IS NULL) FROM deliberation_periodique_resultats
UNION ALL SELECT 'delib_examen_res', COUNT(*), SUM(classe_id IS NULL) FROM deliberation_examen_resultats
UNION ALL SELECT 'delib_repechage', COUNT(*), SUM(classe_id IS NULL) FROM deliberation_repechage_resultats
UNION ALL SELECT 'classe_deliberation', COUNT(*), SUM(classe_id IS NULL) FROM classe_deliberation
UNION ALL SELECT 'responsable_classe', COUNT(*), SUM(classe_id IS NULL) FROM responsable_classe
UNION ALL SELECT 'horaire', COUNT(*), SUM(classe_id IS NULL) FROM horaire
UNION ALL SELECT 'salle', COUNT(*), SUM(classe_id IS NULL) FROM salle
UNION ALL SELECT 'eleve_conduite', COUNT(*), SUM(classe_id IS NULL) FROM eleve_conduite
UNION ALL SELECT 'var_datebutoire', COUNT(*), SUM(classe_id IS NULL) FROM recouvrment_variable_datebutoire
UNION ALL SELECT 'var_derogation', COUNT(*), SUM(classe_id IS NULL) FROM recouvrment_variable_derogation
UNION ALL SELECT 'var_prix', COUNT(*), SUM(classe_id IS NULL) FROM recouvrment_variable_prix
UNION ALL SELECT 'reduction_prix', COUNT(*), SUM(classe_id IS NULL) FROM recouvrment_reduction_prix
UNION ALL SELECT 'paiement', COUNT(*), SUM(classe_id IS NULL) FROM recouvrment_paiement;

SELECT '✅ Phase 1 terminée. Les colonnes sont ajoutées et peuplées.' AS status;
SELECT '⚠️  id_classe_id est CONSERVÉ — l ancien code fonctionne toujours.' AS status;
SELECT '→ Prochaine étape : déployer le code mis à jour (Phase 2+3).' AS status;
