-- Migration: Add ref_administrative_naissance and ref_administrative_residence to eleve table
-- Run this on db_monecole (spoke database) BEFORE deploying the code update
-- Date: 2026-04-12

-- Add ref_administrative_naissance (lieu de naissance normalisé)
ALTER TABLE eleve ADD COLUMN IF NOT EXISTS ref_administrative_naissance VARCHAR(500) NULL DEFAULT NULL;

-- Add ref_administrative_residence (résidence actuelle normalisée)
ALTER TABLE eleve ADD COLUMN IF NOT EXISTS ref_administrative_residence VARCHAR(500) NULL DEFAULT NULL;

-- Verify
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'eleve'
  AND COLUMN_NAME IN ('ref_administrative_naissance', 'ref_administrative_residence');
