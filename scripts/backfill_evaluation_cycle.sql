-- =====================================================================
-- BACKFILL: Ajouter id_cycle_id aux évaluations existantes
-- 
-- Ce script met à jour les évaluations dont id_cycle_id est NULL
-- en résolvant le cycle depuis la classe (classe_id → classes.cycle_id)
--
-- SAFE: Ne modifie que les lignes avec id_cycle_id NULL
-- IDEMPOTENT: Peut être exécuté plusieurs fois sans effet secondaire
-- =====================================================================

-- 1. Diagnostic: Combien d'évaluations sont concernées?
SELECT 
    COUNT(*) AS total_evaluations,
    SUM(CASE WHEN e.id_cycle_id IS NULL THEN 1 ELSE 0 END) AS sans_cycle,
    SUM(CASE WHEN e.id_cycle_id IS NOT NULL THEN 1 ELSE 0 END) AS avec_cycle
FROM evaluation e;

-- 2. Preview: voir ce qui va être mis à jour
SELECT 
    e.id_evaluation, 
    e.title,
    e.classe_id,
    e.id_cycle_id AS cycle_actuel,
    c.cycle_id AS cycle_resolu
FROM evaluation e
JOIN countryStructure.classes c ON c.id = e.classe_id
WHERE e.id_cycle_id IS NULL
LIMIT 20;

-- 3. BACKFILL: Mettre à jour id_cycle_id depuis la classe
UPDATE evaluation e
JOIN countryStructure.classes c ON c.id = e.classe_id
SET e.id_cycle_id = c.cycle_id
WHERE e.id_cycle_id IS NULL
  AND c.cycle_id IS NOT NULL;

-- 4. Vérification post-update
SELECT 
    COUNT(*) AS total_evaluations,
    SUM(CASE WHEN e.id_cycle_id IS NULL THEN 1 ELSE 0 END) AS encore_sans_cycle,
    SUM(CASE WHEN e.id_cycle_id IS NOT NULL THEN 1 ELSE 0 END) AS avec_cycle
FROM evaluation e;

-- =====================================================================
-- BACKFILL eleve_note: même logique pour les notes existantes
-- =====================================================================

-- 5. Diagnostic eleve_note
SELECT 
    COUNT(*) AS total_notes,
    SUM(CASE WHEN en.id_cycle_id = 0 OR en.id_cycle_id IS NULL THEN 1 ELSE 0 END) AS sans_cycle
FROM eleve_note en;

-- 6. BACKFILL eleve_note via evaluation → classe → cycle
UPDATE eleve_note en
JOIN evaluation ev ON ev.id_evaluation = en.id_evaluation_id
JOIN countryStructure.classes c ON c.id = ev.classe_id
SET en.id_cycle_id = c.cycle_id
WHERE (en.id_cycle_id = 0 OR en.id_cycle_id IS NULL)
  AND c.cycle_id IS NOT NULL;
