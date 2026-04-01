-- ============================================================
-- Migration SQL : Fusion auth_user → personnel
-- Ajoute les colonnes d'authentification dans personnel
-- et corrige les FK dans les tables liées
-- ============================================================

-- ═══════════════════════════════════════════════════════
-- PHASE 1 : Ajouter les nouvelles colonnes à personnel
-- ═══════════════════════════════════════════════════════

-- Ignorer les erreurs si les colonnes existent déjà (exécuter ligne par ligne si nécessaire)
ALTER TABLE personnel ADD COLUMN username VARCHAR(150) DEFAULT NULL;
ALTER TABLE personnel ADD COLUMN password_hash VARCHAR(255) DEFAULT '';
ALTER TABLE personnel ADD COLUMN last_login DATETIME DEFAULT NULL;
ALTER TABLE personnel ADD COLUMN email_verified TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE personnel ADD COLUMN phone_verified TINYINT(1) NOT NULL DEFAULT 0;


-- ═══════════════════════════════════════════════════════
-- PHASE 2 : Migrer les données depuis auth_user → personnel
-- ═══════════════════════════════════════════════════════

-- Copier username, last_login, et compléter email/nom/prenom vides
UPDATE personnel p
JOIN auth_user au ON au.id = p.user_id
SET 
    p.username = au.username,
    p.last_login = au.last_login,
    p.email = COALESCE(NULLIF(p.email, ''), au.email),
    p.nom = COALESCE(NULLIF(p.nom, ''), au.last_name),
    p.prenom = COALESCE(NULLIF(p.prenom, ''), au.first_name)
WHERE p.user_id IS NOT NULL;

-- Générer des usernames pour les personnels sans username
UPDATE personnel 
SET username = CONCAT('pers_', id_etablissement, '_', id_personnel)
WHERE username IS NULL OR username = '';


-- ═══════════════════════════════════════════════════════
-- PHASE 3 : Corriger les FK dans les 3 tables liées
-- user_module, user_enseignement, users_other_module
-- ═══════════════════════════════════════════════════════

-- 3a. user_module : user_id = auth_user.id → remapper vers personnel.id_personnel
-- D'abord, supprimer la contrainte FK existante (si elle existe)
-- Trouver le nom de la contrainte : 
-- SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
-- WHERE TABLE_NAME = 'user_module' AND COLUMN_NAME = 'user_id' AND TABLE_SCHEMA = DATABASE();

-- Remap : remplacer auth_user.id par le personnel.id_personnel correspondant
UPDATE user_module um
JOIN personnel p ON p.user_id = um.user_id
SET um.user_id = p.id_personnel
WHERE um.user_id IS NOT NULL;

-- 3b. user_enseignement : user_id = auth_user.id → remapper vers personnel.id_personnel
UPDATE user_enseignement ue
JOIN personnel p ON p.user_id = ue.user_id  
SET ue.user_id = p.id_personnel
WHERE ue.user_id IS NOT NULL;

-- 3c. users_other_module : id_personnel_id → devrait déjà pointer vers personnel
-- Vérification seulement (pas de migration nécessaire normalement)
-- SELECT * FROM users_other_module LIMIT 5;


-- ═══════════════════════════════════════════════════════
-- PHASE 4 : Ajouter les index utiles
-- ═══════════════════════════════════════════════════════

-- Index sur email pour les lookups de login
ALTER TABLE personnel ADD INDEX idx_personnel_email (email);

-- Index sur username (unique après vérification de doublons)
-- D'abord vérifier : SELECT username, COUNT(*) c FROM personnel GROUP BY username HAVING c > 1;
-- Si pas de doublons :
-- ALTER TABLE personnel ADD UNIQUE INDEX idx_personnel_username (username);


-- ═══════════════════════════════════════════════════════
-- PHASE 5 : Vérification
-- ═══════════════════════════════════════════════════════

-- Vérifier que les user_module pointent désormais vers des id_personnel valides
-- SELECT um.user_id, p.id_personnel, p.nom, p.prenom 
-- FROM user_module um 
-- LEFT JOIN personnel p ON p.id_personnel = um.user_id 
-- WHERE p.id_personnel IS NULL;

-- Vérifier que les user_enseignement pointent vers des id_personnel valides
-- SELECT ue.user_id, p.id_personnel, p.nom, p.prenom 
-- FROM user_enseignement ue 
-- LEFT JOIN personnel p ON p.id_personnel = ue.user_id 
-- WHERE p.id_personnel IS NULL;


-- ═══════════════════════════════════════════════════════
-- NOTE: Ne PAS supprimer auth_user tant que tout fonctionne !
-- La suppression se fera dans une migration future après validation complète.
-- ═══════════════════════════════════════════════════════
