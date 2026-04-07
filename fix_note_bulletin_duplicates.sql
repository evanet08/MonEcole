-- ============================================================
-- FIX: note_bulletin — Supprimer doublons + Ajouter UNIQUE INDEX
-- À exécuter sur la base SPOKE (db_monecole) en production
-- ============================================================

-- ÉTAPE 1: Identifier et supprimer les doublons
-- Garder UNIQUEMENT la ligne la plus récente (id_note_bulletin le plus élevé)
-- pour chaque combinaison (eleve, cours, config, note_type)

DELETE nb1 FROM note_bulletin nb1
INNER JOIN note_bulletin nb2
  ON nb1.id_eleve_id = nb2.id_eleve_id
  AND nb1.id_cours_annee = nb2.id_cours_annee
  AND nb1.id_repartition_config = nb2.id_repartition_config
  AND nb1.id_note_type = nb2.id_note_type
  AND nb1.id_note_bulletin < nb2.id_note_bulletin;

-- ÉTAPE 2: Vérifier qu'il n'y a plus de doublons
SELECT id_eleve_id, id_cours_annee, id_repartition_config, id_note_type, COUNT(*) AS cnt
FROM note_bulletin
GROUP BY id_eleve_id, id_cours_annee, id_repartition_config, id_note_type
HAVING cnt > 1;

-- ÉTAPE 3: Ajouter la contrainte UNIQUE
-- (va échouer s'il reste des doublons — relancer ÉTAPE 1 si nécessaire)
ALTER TABLE note_bulletin
ADD UNIQUE INDEX uq_note_bulletin_eleve_cours_config_type
  (id_eleve_id, id_cours_annee, id_repartition_config, id_note_type);

-- ÉTAPE 4: Vérifier que l'index a été créé
SHOW INDEX FROM note_bulletin WHERE Key_name = 'uq_note_bulletin_eleve_cours_config_type';
