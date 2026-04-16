-- ============================================================
-- MIGRATION PRODUCTION: Ajouter id_pays à toutes les tables
-- Valeur par défaut = 2 (pays actuel)
-- Date: 2026-04-16
-- SÉCURISÉ: Vérifie l'existence de la colonne avant ALTER
-- ============================================================

-- ============================================================
-- PARTIE 1: countryStructure (Hub)
-- ============================================================

USE countryStructure;

-- Fonction utilitaire : ajoute id_pays seulement si elle n'existe pas encore
-- On utilise des procédures stockées temporaires pour la sécurité

DELIMITER //

DROP PROCEDURE IF EXISTS add_id_pays_if_not_exists//

CREATE PROCEDURE add_id_pays_if_not_exists(IN tbl_name VARCHAR(100), IN db_name VARCHAR(100))
BEGIN
    DECLARE col_exists INT DEFAULT 0;
    
    SELECT COUNT(*) INTO col_exists
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = db_name
      AND TABLE_NAME = tbl_name
      AND COLUMN_NAME = 'id_pays';

    IF col_exists = 0 THEN
        SET @sql = CONCAT('ALTER TABLE `', db_name, '`.`', tbl_name, '` ADD COLUMN `id_pays` INT NOT NULL DEFAULT 2');
        PREPARE stmt FROM @sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
        SELECT CONCAT('✅ Colonne id_pays ajoutée à ', db_name, '.', tbl_name) AS result;
    ELSE
        SELECT CONCAT('⏭️  Colonne id_pays existe déjà dans ', db_name, '.', tbl_name) AS result;
    END IF;
END//

DELIMITER ;


-- === TABLES countryStructure ===

CALL add_id_pays_if_not_exists('sessions', 'countryStructure');
CALL add_id_pays_if_not_exists('sections', 'countryStructure');
CALL add_id_pays_if_not_exists('mentions', 'countryStructure');
CALL add_id_pays_if_not_exists('classes', 'countryStructure');
CALL add_id_pays_if_not_exists('cours', 'countryStructure');
CALL add_id_pays_if_not_exists('cours_annee', 'countryStructure');
CALL add_id_pays_if_not_exists('repartition_types', 'countryStructure');
CALL add_id_pays_if_not_exists('repartition_hierarchies', 'countryStructure');
CALL add_id_pays_if_not_exists('repartition_configs_cycle', 'countryStructure');
CALL add_id_pays_if_not_exists('repartition_configs_etab_annee', 'countryStructure');
CALL add_id_pays_if_not_exists('etablissements_annees', 'countryStructure');
CALL add_id_pays_if_not_exists('etablissements_annees_classes', 'countryStructure');
CALL add_id_pays_if_not_exists('evaluation_types', 'countryStructure');
CALL add_id_pays_if_not_exists('note_types', 'countryStructure');
CALL add_id_pays_if_not_exists('gestionnaires_etablissement', 'countryStructure');
CALL add_id_pays_if_not_exists('bulletin_model', 'countryStructure');
CALL add_id_pays_if_not_exists('bulletin_classe_model', 'countryStructure');

-- Sécurité: Forcer la valeur 2 sur toutes les lignes existantes
UPDATE `sessions` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `sections` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `mentions` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `classes` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `cours` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `cours_annee` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `repartition_types` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `repartition_hierarchies` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `repartition_configs_cycle` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `repartition_configs_etab_annee` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `etablissements_annees` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `etablissements_annees_classes` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `evaluation_types` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `note_types` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `gestionnaires_etablissement` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `bulletin_model` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `bulletin_classe_model` SET id_pays = 2 WHERE id_pays = 0;


-- ============================================================
-- PARTIE 2: db_monecole (Spoke)
-- ============================================================

USE db_monecole;

-- === Identité & Auth ===
CALL add_id_pays_if_not_exists('campus', 'db_monecole');
CALL add_id_pays_if_not_exists('admin_users', 'db_monecole');
CALL add_id_pays_if_not_exists('otp_codes', 'db_monecole');

-- === Personnel ===
CALL add_id_pays_if_not_exists('personnel_categorie', 'db_monecole');
CALL add_id_pays_if_not_exists('diplome', 'db_monecole');
CALL add_id_pays_if_not_exists('specialite', 'db_monecole');
CALL add_id_pays_if_not_exists('vacation', 'db_monecole');
CALL add_id_pays_if_not_exists('personnel_type', 'db_monecole');
CALL add_id_pays_if_not_exists('personnel', 'db_monecole');
CALL add_id_pays_if_not_exists('prestation', 'db_monecole');

-- === Élèves ===
CALL add_id_pays_if_not_exists('eleve', 'db_monecole');
CALL add_id_pays_if_not_exists('eleve_inscription', 'db_monecole');
CALL add_id_pays_if_not_exists('eleve_note_type', 'db_monecole');
CALL add_id_pays_if_not_exists('eleve_note', 'db_monecole');
CALL add_id_pays_if_not_exists('eleve_conduite', 'db_monecole');
CALL add_id_pays_if_not_exists('parents', 'db_monecole');
CALL add_id_pays_if_not_exists('professions', 'db_monecole');

-- === Classes ===
CALL add_id_pays_if_not_exists('classe_deliberation', 'db_monecole');
CALL add_id_pays_if_not_exists('responsable_classe', 'db_monecole');

-- === Enseignements ===
CALL add_id_pays_if_not_exists('attribution_type', 'db_monecole');
CALL add_id_pays_if_not_exists('attribution_cours', 'db_monecole');
CALL add_id_pays_if_not_exists('user_enseignement', 'db_monecole');
CALL add_id_pays_if_not_exists('users_other_module', 'db_monecole');

-- === Évaluations & Délibérations ===
CALL add_id_pays_if_not_exists('deliberation_type', 'db_monecole');
CALL add_id_pays_if_not_exists('deliberation_annuelle_finalites', 'db_monecole');
CALL add_id_pays_if_not_exists('deliberation_annuelle_conditions', 'db_monecole');
CALL add_id_pays_if_not_exists('deliberation_annuelle_resultats', 'db_monecole');
CALL add_id_pays_if_not_exists('deliberation_periodique_resultats', 'db_monecole');
CALL add_id_pays_if_not_exists('deliberation_examen_resultats', 'db_monecole');
CALL add_id_pays_if_not_exists('deliberation_trimistrielle_resultats', 'db_monecole');
CALL add_id_pays_if_not_exists('deliberation_repechage_resultats', 'db_monecole');
CALL add_id_pays_if_not_exists('evaluation', 'db_monecole');
CALL add_id_pays_if_not_exists('note_bulletin', 'db_monecole');

-- === Horaires ===
CALL add_id_pays_if_not_exists('horaire_type', 'db_monecole');
CALL add_id_pays_if_not_exists('horaire', 'db_monecole');
CALL add_id_pays_if_not_exists('horaire_presence', 'db_monecole');

-- === Modules ===
CALL add_id_pays_if_not_exists('module', 'db_monecole');
CALL add_id_pays_if_not_exists('user_module', 'db_monecole');

-- === Salles ===
CALL add_id_pays_if_not_exists('salle', 'db_monecole');

-- === Recouvrement ===
CALL add_id_pays_if_not_exists('recouvrment_variable_categorie', 'db_monecole');
CALL add_id_pays_if_not_exists('recouvrment_variable', 'db_monecole');
CALL add_id_pays_if_not_exists('recouvrment_variable_datebutoire', 'db_monecole');
CALL add_id_pays_if_not_exists('recouvrment_variable_derogation', 'db_monecole');
CALL add_id_pays_if_not_exists('recouvrment_variable_prix', 'db_monecole');
CALL add_id_pays_if_not_exists('recouvrment_banque', 'db_monecole');
CALL add_id_pays_if_not_exists('recouvrment_compte', 'db_monecole');
CALL add_id_pays_if_not_exists('recouvrment_reduction_prix', 'db_monecole');
CALL add_id_pays_if_not_exists('recouvrment_paiement', 'db_monecole');

-- === Communication ===
CALL add_id_pays_if_not_exists('communication', 'db_monecole');
CALL add_id_pays_if_not_exists('communication_group', 'db_monecole');
CALL add_id_pays_if_not_exists('communication_group_member', 'db_monecole');

-- Sécurité: Forcer la valeur 2 sur toutes les lignes existantes
UPDATE `campus` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `admin_users` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `otp_codes` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `personnel_categorie` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `diplome` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `specialite` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `vacation` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `personnel_type` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `personnel` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `prestation` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `eleve` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `eleve_inscription` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `eleve_note_type` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `eleve_note` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `eleve_conduite` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `parents` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `professions` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `classe_deliberation` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `responsable_classe` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `attribution_type` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `attribution_cours` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `user_enseignement` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `users_other_module` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `deliberation_type` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `deliberation_annuelle_finalites` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `deliberation_annuelle_conditions` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `deliberation_annuelle_resultats` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `deliberation_periodique_resultats` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `deliberation_examen_resultats` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `deliberation_trimistrielle_resultats` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `deliberation_repechage_resultats` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `evaluation` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `note_bulletin` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `horaire_type` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `horaire` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `horaire_presence` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `module` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `user_module` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `salle` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_variable_categorie` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_variable` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_variable_datebutoire` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_variable_derogation` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_variable_prix` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_banque` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_compte` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_reduction_prix` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `recouvrment_paiement` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `communication` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `communication_group` SET id_pays = 2 WHERE id_pays = 0;
UPDATE `communication_group_member` SET id_pays = 2 WHERE id_pays = 0;

-- === Tables sans modèle Django (raw SQL uniquement) ===
-- Ces tables existent peut-être ou pas selon l'état de la DB.
-- La procédure vérifie d'abord si la table existe avant d'agir.

DELIMITER //
DROP PROCEDURE IF EXISTS add_id_pays_if_table_exists//
CREATE PROCEDURE add_id_pays_if_table_exists(IN tbl_name VARCHAR(100), IN db_name VARCHAR(100))
BEGIN
    DECLARE tbl_exists INT DEFAULT 0;
    DECLARE col_exists INT DEFAULT 0;
    
    SELECT COUNT(*) INTO tbl_exists
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = db_name AND TABLE_NAME = tbl_name;

    IF tbl_exists > 0 THEN
        SELECT COUNT(*) INTO col_exists
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = db_name AND TABLE_NAME = tbl_name AND COLUMN_NAME = 'id_pays';

        IF col_exists = 0 THEN
            SET @sql = CONCAT('ALTER TABLE `', db_name, '`.`', tbl_name, '` ADD COLUMN `id_pays` INT NOT NULL DEFAULT 2');
            PREPARE stmt FROM @sql;
            EXECUTE stmt;
            DEALLOCATE PREPARE stmt;
            SELECT CONCAT('✅ Colonne id_pays ajoutée à ', db_name, '.', tbl_name) AS result;
        ELSE
            SELECT CONCAT('⏭️  Colonne id_pays existe déjà dans ', db_name, '.', tbl_name) AS result;
        END IF;
    ELSE
        SELECT CONCAT('⚠️  Table ', db_name, '.', tbl_name, ' n\\'existe pas, ignorée') AS result;
    END IF;
END//
DELIMITER ;

CALL add_id_pays_if_table_exists('personnel_presence', 'db_monecole');
CALL add_id_pays_if_table_exists('communication_meeting', 'db_monecole');
CALL add_id_pays_if_table_exists('communication_meeting_invitee', 'db_monecole');
CALL add_id_pays_if_table_exists('evaluation_repartition', 'db_monecole');
CALL add_id_pays_if_table_exists('document_type', 'db_monecole');
CALL add_id_pays_if_table_exists('document_eleve', 'db_monecole');

-- Mise à jour données existantes pour ces tables
-- (Sécurisé: ne fait rien si la table n'existe pas grâce au IF EXISTS pattern)
SET @sql = 'SELECT 1'; -- fallback
SET @tbl_check = (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'db_monecole' AND TABLE_NAME = 'personnel_presence');
SET @sql = IF(@tbl_check > 0, 'UPDATE db_monecole.personnel_presence SET id_pays = 2 WHERE id_pays = 0', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @tbl_check = (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'db_monecole' AND TABLE_NAME = 'communication_meeting');
SET @sql = IF(@tbl_check > 0, 'UPDATE db_monecole.communication_meeting SET id_pays = 2 WHERE id_pays = 0', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @tbl_check = (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'db_monecole' AND TABLE_NAME = 'communication_meeting_invitee');
SET @sql = IF(@tbl_check > 0, 'UPDATE db_monecole.communication_meeting_invitee SET id_pays = 2 WHERE id_pays = 0', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @tbl_check = (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'db_monecole' AND TABLE_NAME = 'evaluation_repartition');
SET @sql = IF(@tbl_check > 0, 'UPDATE db_monecole.evaluation_repartition SET id_pays = 2 WHERE id_pays = 0', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @tbl_check = (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'db_monecole' AND TABLE_NAME = 'document_type');
SET @sql = IF(@tbl_check > 0, 'UPDATE db_monecole.document_type SET id_pays = 2 WHERE id_pays = 0', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @tbl_check = (SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'db_monecole' AND TABLE_NAME = 'document_eleve');
SET @sql = IF(@tbl_check > 0, 'UPDATE db_monecole.document_eleve SET id_pays = 2 WHERE id_pays = 0', 'SELECT 1');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Nettoyage
DROP PROCEDURE IF EXISTS add_id_pays_if_not_exists;
DROP PROCEDURE IF EXISTS add_id_pays_if_table_exists;

-- ============================================================
-- FIN DE MIGRATION
-- ============================================================
SELECT '✅ Migration id_pays terminée avec succès !' AS RESULTAT;
