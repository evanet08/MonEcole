-- Migration: Create communication table
-- Run on the SPOKE database (db_monecole or equivalent)

CREATE TABLE IF NOT EXISTS `communication` (
    `id_communication` INT AUTO_INCREMENT PRIMARY KEY,
    `id_etablissement` INT NOT NULL,
    `id_annee` INT NULL,
    
    -- Sender (personnel ou parent d'élève)
    `sender_personnel_id` INT NULL,
    `sender_eleve_id` INT NULL,
    `sender_name` VARCHAR(255) DEFAULT '',

    -- Portée et direction
    `scope` VARCHAR(20) NOT NULL DEFAULT 'individual' COMMENT 'individual, class, etab, teacher',
    `direction` VARCHAR(5) NOT NULL DEFAULT 'out' COMMENT 'out=sortant, in=entrant',

    -- Cibles
    `target_eleve_id` INT NULL,
    `target_classe_id` INT NULL,
    `target_personnel_id` INT NULL,

    -- Contenu
    `subject` VARCHAR(255) DEFAULT '',
    `message` TEXT NOT NULL,
    `thread_id` VARCHAR(100) DEFAULT '' COMMENT 'Identifiant du fil de discussion',

    -- Statut
    `status` VARCHAR(20) DEFAULT 'sent' COMMENT 'sent, delivered, read, failed',
    `is_read` TINYINT(1) DEFAULT 0,
    `read_at` DATETIME NULL,

    -- Timestamps
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Index
    INDEX `idx_etab_thread` (`id_etablissement`, `thread_id`),
    INDEX `idx_etab_sender_date` (`id_etablissement`, `sender_personnel_id`, `created_at`),
    INDEX `idx_etab_target_eleve` (`id_etablissement`, `target_eleve_id`, `created_at`),
    INDEX `idx_etab_target_classe` (`id_etablissement`, `target_classe_id`, `created_at`),
    INDEX `idx_thread_id` (`thread_id`),
    INDEX `idx_sender_eleve` (`sender_eleve_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
