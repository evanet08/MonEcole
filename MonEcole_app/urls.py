from django.urls import path
from MonEcole_app.views import login_view, logout_view
from MonEcole_app.views import auth_views
from MonEcole_app.views.dashboard_views import (
    administration_view, enseignements_view,
    evaluations_view, scolarite_view,
    espace_enseignant_view, api_enseignant_dashboard, api_enseignant_debug,
    api_enseignant_presences,
    api_communication_messages, api_communication_send, api_communication_threads,
    api_communication_teachers,
)
from MonEcole_app.views import api_views
from MonEcole_app.views.pdf import generer_bulletin_pdf

urlpatterns = [
    # Page login
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # Auth APIs (flow multi-étapes comme eSchool)
    path('api/auth/check-email/', auth_views.check_email, name='auth_check_email'),
    path('api/auth/request-otp/', auth_views.request_otp, name='auth_request_otp'),
    path('api/auth/verify-otp/', auth_views.verify_otp, name='auth_verify_otp'),
    path('api/auth/set-password/', auth_views.set_password, name='auth_set_password'),
    path('api/auth/verify-contact/', auth_views.verify_contact, name='auth_verify_contact'),
    path('api/auth/login/', auth_views.api_login, name='auth_login'),
    path('api/auth/forgot-password/', auth_views.forgot_password, name='auth_forgot_password'),
    path('api/auth/verify-reset-otp/', auth_views.verify_reset_otp, name='auth_verify_reset_otp'),
    path('api/auth/reset-password/', auth_views.reset_password, name='auth_reset_password'),
    path('api/auth/logout/', auth_views.api_logout, name='auth_logout'),

    # ============ DASHBOARD — 4 PAGES ============
    path('dashboard/', administration_view, name='dashboard'),
    path('dashboard/administration/', administration_view, name='dashboard_administration'),
    path('dashboard/enseignements/', enseignements_view, name='dashboard_enseignements'),
    path('dashboard/evaluations/', evaluations_view, name='dashboard_evaluations'),
    path('dashboard/scolarite/', scolarite_view, name='dashboard_scolarite'),
    path('dashboard/enseignant/', espace_enseignant_view, name='dashboard_enseignant'),

    # API Enseignant
    path('api/enseignant/dashboard/', api_enseignant_dashboard, name='api_enseignant_dashboard'),
    path('api/enseignant/debug/', api_enseignant_debug, name='api_enseignant_debug'),
    path('api/enseignant/presences/', api_enseignant_presences, name='api_enseignant_presences'),

    # API Communication
    path('api/enseignant/communication/', api_communication_messages, name='api_communication_messages'),
    path('api/enseignant/communication/send/', api_communication_send, name='api_communication_send'),
    path('api/enseignant/communication/threads/', api_communication_threads, name='api_communication_threads'),
    path('api/enseignant/communication/teachers/', api_communication_teachers, name='api_communication_teachers'),

    # ============ API DASHBOARD (copiées depuis eSchool) ============
    # Dashboard — Student Management
    path('api/dashboard/add-eleve/', api_views.dashboard_add_eleve, name='dashboard_add_eleve'),
    path('api/dashboard/eleve-template/', api_views.dashboard_eleve_template, name='dashboard_eleve_template'),
    path('api/dashboard/import-eleves/', api_views.dashboard_import_eleves, name='dashboard_import_eleves'),
    path('api/dashboard/eleves-stats/', api_views.dashboard_eleves_stats, name='dashboard_eleves_stats'),
    path('api/dashboard/eleves-list/', api_views.dashboard_eleves_list, name='dashboard_eleves_list'),
    path('api/dashboard/update-eleve/', api_views.dashboard_update_eleve, name='dashboard_update_eleve'),
    path('api/dashboard/upload-photo/', api_views.dashboard_upload_photo, name='dashboard_upload_photo'),
    path('api/dashboard/delete-inscriptions/', api_views.delete_inscriptions, name='delete_inscriptions'),

    # Campus CRUD
    path('api/dashboard/campus-list/', api_views.dashboard_campus_list, name='dashboard_campus_list'),
    path('api/dashboard/campus-create/', api_views.dashboard_campus_create, name='dashboard_campus_create'),
    path('api/dashboard/campus-update/', api_views.dashboard_campus_update, name='dashboard_campus_update'),
    path('api/dashboard/campus-delete/', api_views.dashboard_campus_delete, name='dashboard_campus_delete'),

    # Personnel / Enseignants
    path('api/dashboard/personnel-list/', api_views.dashboard_personnel_list, name='dashboard_personnel_list'),
    path('api/dashboard/add-personnel/', api_views.dashboard_add_personnel, name='dashboard_add_personnel'),
    path('api/dashboard/update-personnel/', api_views.dashboard_update_personnel, name='dashboard_update_personnel'),
    path('api/dashboard/upload-personnel-photo/', api_views.dashboard_upload_personnel_photo, name='dashboard_upload_personnel_photo'),
    path('api/dashboard/personnel-ref-crud/', api_views.dashboard_personnel_ref_crud, name='dashboard_personnel_ref_crud'),
    path('api/dashboard/personnel-template/', api_views.dashboard_personnel_template, name='dashboard_personnel_template'),
    path('api/dashboard/import-personnel/', api_views.dashboard_import_personnel, name='dashboard_import_personnel'),
    path('api/dashboard/attribution-cours/', api_views.dashboard_attribution_cours, name='dashboard_attribution_cours'),
    path('api/dashboard/horaire/', api_views.dashboard_horaire, name='dashboard_horaire'),

    # Configuration (Structuration)
    path('api/get-cycles/', api_views.get_cycles_data, name='get_cycles'),
    path('api/get-sections-list/', api_views.get_sections_list, name='get_sections_list'),
    path('api/get-etablissement-config/', api_views.get_etablissement_config, name='get_etablissement_config'),
    path('api/save-etablissement-config/', api_views.save_etablissement_config, name='save_etablissement_config'),

    # Cours & Domaines
    path('api/save-domaine/', api_views.save_domaine, name='save_domaine'),
    path('api/delete-domaine/', api_views.delete_domaine, name='delete_domaine'),
    path('api/save-cours/', api_views.save_cours, name='save_cours'),
    path('api/delete-cours/', api_views.delete_cours, name='delete_cours'),
    path('api/save-cours-annee/', api_views.save_cours_annee, name='save_cours_annee'),

    # MonEcole (Fiche établissement)
    path('api/mon-etablissement/', api_views.get_mon_etablissement, name='get_mon_etablissement'),
    path('api/update-mon-etablissement/', api_views.update_mon_etablissement, name='update_mon_etablissement'),
    path('api/upload-etab-logo/', api_views.upload_etab_logo, name='upload_etab_logo'),
    path('api/upload-etab-document/', api_views.upload_etab_document, name='upload_etab_document'),
    path('api/create-admin-instance/', api_views.create_admin_instance, name='create_admin_instance'),
    path('api/update-admin-instance/', api_views.update_admin_instance, name='update_admin_instance'),
    path('api/rue-suggestions/', api_views.get_rue_suggestions, name='get_rue_suggestions'),

    # Calendrier
    path('api/toggle-calendar-synch/', api_views.toggle_calendar_synch, name='toggle_calendar_synch'),
    path('api/update-calendar-config/', api_views.update_calendar_config, name='update_calendar_config'),

    # Domaines
    path('api/get-domaines/', api_views.get_domaines_data, name='get_domaines'),
    path('api/save-domaine/', api_views.save_domaine, name='save_domaine'),
    path('api/delete-domaine/', api_views.delete_domaine, name='delete_domaine'),

    # Cours (Catalogue)
    path('api/get-cours/', api_views.get_cours_data, name='get_cours'),
    path('api/save-cours/', api_views.save_cours, name='save_cours'),
    path('api/delete-cours/', api_views.delete_cours, name='delete_cours'),

    # Cours Annee (Configuration Annuelle)
    path('api/get-cours-annee/', api_views.get_cours_annee_data, name='get_cours_annee'),
    path('api/save-cours-annee/', api_views.save_cours_annee, name='save_cours_annee'),
    path('api/delete-cours-annee/', api_views.delete_cours_annee, name='delete_cours_annee'),
    path('api/bulk-activate-cours-annee/', api_views.bulk_activate_cours_annee, name='bulk_activate_cours_annee'),

    # Évaluations
    path('api/evaluations/types/', api_views.get_evaluation_types, name='get_evaluation_types'),
    path('api/evaluations/types/save/', api_views.save_evaluation_type, name='save_evaluation_type'),
    path('api/evaluations/types/delete/', api_views.delete_evaluation_type, name='delete_evaluation_type'),
    path('api/evaluations/cours/', api_views.get_evaluation_cours, name='get_evaluation_cours'),
    path('api/evaluations/list/', api_views.get_evaluations_list, name='get_evaluations_list'),
    path('api/evaluations/save/', api_views.save_evaluation, name='save_evaluation'),
    path('api/evaluations/delete/', api_views.delete_evaluation, name='delete_evaluation'),
    path('api/evaluations/candidates/', api_views.get_evaluation_candidates, name='get_evaluation_candidates'),
    path('api/evaluations/assign/', api_views.assign_evaluations, name='assign_evaluations'),

    # Notes
    path('api/notes/grid/', api_views.get_notes_grid, name='get_notes_grid'),
    path('api/notes/save/', api_views.save_notes, name='save_notes'),
    path('api/notes/template/', api_views.download_notes_template, name='download_notes_template'),
    path('api/notes/import/', api_views.import_notes_excel, name='import_notes_excel'),
    path('api/notes/bulletin/calculate/', api_views.calculate_notes_bulletin, name='calculate_notes_bulletin'),
    path('api/notes/bulletin/calculate-period/', api_views.calculate_period_notes, name='calculate_period_notes'),
    path('api/notes/bulletin/calculate-period-batch/', api_views.calculate_period_batch, name='calculate_period_batch'),
    path('api/notes/bulletin/sync-all/', api_views.sync_all_notes_bulletin, name='sync_all_notes_bulletin'),
    path('api/notes/bulletin/get/', api_views.get_notes_bulletin, name='get_notes_bulletin'),
    path('api/notes/bulletin/overview/', api_views.get_bulletin_overview, name='get_bulletin_overview'),

    # Notes d'Examen — saisie directe
    path('api/notes/exam/grid/', api_views.get_exam_grid, name='get_exam_grid'),
    path('api/notes/exam/save/', api_views.save_exam_notes, name='save_exam_notes'),
    path('api/notes/exam/template/', api_views.download_exam_template, name='download_exam_template'),
    path('api/notes/exam/import/', api_views.import_exam_notes_excel, name='import_exam_notes_excel'),

    # Délibérations
    path('api/evaluations/sessions/', api_views.get_evaluations_sessions, name='get_evaluations_sessions'),
    path('api/evaluations/repartitions/', api_views.get_evaluations_repartitions, name='get_evaluations_repartitions'),
    path('api/deliberations/conditions/', api_views.get_deliberation_conditions, name='get_deliberation_conditions'),
    path('api/deliberations/execute/', api_views.execute_deliberation, name='execute_deliberation'),
    path('api/deliberations/cancel/', api_views.cancel_deliberation, name='cancel_deliberation'),
    path('api/deliberations/results/', api_views.get_deliberation_results, name='get_deliberation_results'),

    # Références
    path('api/get-sessions/', api_views.get_sessions_data, name='get_sessions'),
    path('api/save-session/', api_views.save_session, name='save_session'),
    path('api/get-mentions/', api_views.get_mentions_data, name='get_mentions'),
    path('api/save-mention/', api_views.save_mention, name='save_mention'),

    # Répartitions (si jamais appelées)
    path('api/repartition/types/', api_views.get_repartition_types, name='get_repartition_types'),
    path('api/repartition/instances/', api_views.get_repartition_instances, name='get_repartition_instances'),
    path('api/repartition/hierarchies/', api_views.get_repartition_hierarchies, name='get_repartition_hierarchies'),
    path('api/repartition/configs-cycle/', api_views.get_repartition_configs_cycle, name='get_repartition_configs_cycle'),
    path('api/repartition/provision-etab/', api_views.provision_repartitions_for_etab, name='provision_repartitions_for_etab'),

    # Dossier Administratif
    path('api/dashboard/transfer-eleves/', api_views.dashboard_transfer_eleves, name='dashboard_transfer_eleves'),
    path('api/document-types/', api_views.document_types_api, name='document_types_api'),
    path('api/eleve-documents/', api_views.eleve_documents_api, name='eleve_documents_api'),

    # Gestion Utilisateurs & Droits
    path('api/dashboard/users/', api_views.dashboard_users_list, name='dashboard_users_list'),
    path('api/dashboard/users/toggle/', api_views.dashboard_users_toggle, name='dashboard_users_toggle'),
    path('api/dashboard/users/modules/', api_views.dashboard_users_modules, name='dashboard_users_modules'),

    # Bulletins
    path('api/bulletins/classes/', api_views.get_deliberated_classes, name='get_deliberated_classes'),
    path('api/bulletins/eleves/', api_views.get_bulletin_eleves, name='get_bulletin_eleves'),
    path('generer_bulletin_pdf/', generer_bulletin_pdf, name='generer_bulletin_pdf'),
]
