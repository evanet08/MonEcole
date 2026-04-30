from django.urls import path
from MonEcole_app.views import login_view, logout_view
from MonEcole_app.views import auth_views
from MonEcole_app.views.dashboard_views import (
    administration_view, enseignements_view,
    evaluations_view, scolarite_view,
    espace_enseignant_view, communication_view,
    recouvrement_view,
    api_enseignant_dashboard, api_enseignant_debug,
    api_enseignant_presences,
    api_communication_contacts,
    api_communication_messages, api_communication_send, api_communication_threads,
    api_communication_teachers,
    api_communication_group_create, api_communication_group_update,
    api_communication_heartbeat, api_communication_visio,
    api_communication_meeting_create, api_communication_meetings_list,
    api_communication_meeting_join, api_communication_meeting_cancel,
)
from MonEcole_app.views.recouvrement import api_load as rec_api
from MonEcole_app.views.recouvrement import save_api as rec_save
from MonEcole_app.views.recouvrement import update_views as rec_upd
from MonEcole_app.views.recouvrement import create_base as rec_base
from MonEcole_app.views.recouvrement import invoice_paiement as rec_inv
from MonEcole_app.views import api_views
from MonEcole_app.views.pdf import generer_bulletin_pdf
from MonEcole_app.views.parent import parent_views as pv
from MonEcole_app.views.parent import parent_eval_api, parent_payment_api, parent_dashboard_api, parent_comm_api

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
    path('dashboard/communication/', communication_view, name='dashboard_communication'),
    path('dashboard/recouvrement/', recouvrement_view, name='dashboard_recouvrement'),

    # API Enseignant
    path('api/enseignant/dashboard/', api_enseignant_dashboard, name='api_enseignant_dashboard'),
    path('api/enseignant/debug/', api_enseignant_debug, name='api_enseignant_debug'),
    path('api/enseignant/presences/', api_enseignant_presences, name='api_enseignant_presences'),

    # API Communication (standalone module)
    path('api/communication/contacts/', api_communication_contacts, name='api_communication_contacts'),
    path('api/communication/', api_communication_messages, name='api_communication_messages'),
    path('api/communication/send/', api_communication_send, name='api_communication_send'),
    path('api/communication/threads/', api_communication_threads, name='api_communication_threads'),
    path('api/communication/teachers/', api_communication_teachers, name='api_communication_teachers'),
    path('api/communication/groups/create/', api_communication_group_create, name='api_communication_group_create'),
    path('api/communication/groups/update/', api_communication_group_update, name='api_communication_group_update'),
    path('api/communication/heartbeat/', api_communication_heartbeat, name='api_communication_heartbeat'),
    path('api/communication/visio/', api_communication_visio, name='api_communication_visio'),
    path('api/communication/meetings/create/', api_communication_meeting_create, name='api_communication_meeting_create'),
    path('api/communication/meetings/', api_communication_meetings_list, name='api_communication_meetings_list'),
    path('api/communication/meetings/join/', api_communication_meeting_join, name='api_communication_meeting_join'),
    path('api/communication/meetings/cancel/', api_communication_meeting_cancel, name='api_communication_meeting_cancel'),
    # Legacy routes (backward compatibility)
    path('api/enseignant/communication/', api_communication_messages),
    path('api/enseignant/communication/send/', api_communication_send),
    path('api/enseignant/communication/threads/', api_communication_threads),
    path('api/enseignant/communication/teachers/', api_communication_teachers),

    # ============ API DASHBOARD (copiées depuis eSchool) ============
    # Dashboard — Student Management
    path('api/dashboard/search-parents/', api_views.search_parents, name='search_parents'),
    path('api/dashboard/add-eleve/', api_views.dashboard_add_eleve, name='dashboard_add_eleve'),
    path('api/dashboard/eleve-template/', api_views.dashboard_eleve_template, name='dashboard_eleve_template'),
    path('api/dashboard/import-eleves/', api_views.dashboard_import_eleves, name='dashboard_import_eleves'),
    path('api/dashboard/eleves-stats/', api_views.dashboard_eleves_stats, name='dashboard_eleves_stats'),
    path('api/dashboard/eleves-list/', api_views.dashboard_eleves_list, name='dashboard_eleves_list'),
    path('api/dashboard/update-eleve/', api_views.dashboard_update_eleve, name='dashboard_update_eleve'),
    path('api/dashboard/upload-photo/', api_views.dashboard_upload_photo, name='dashboard_upload_photo'),
    path('api/dashboard/delete-inscriptions/', api_views.delete_inscriptions, name='delete_inscriptions'),
    path('api/dashboard/parent-update-template/', api_views.parent_update_template, name='parent_update_template'),
    path('api/dashboard/import-parent-updates/', api_views.import_parent_updates, name='import_parent_updates'),

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
    path('api/download-cours-template/', api_views.download_cours_template, name='download_cours_template'),
    path('api/import-cours-excel/', api_views.import_cours_excel, name='import_cours_excel'),

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

    # ============ RECOUVREMENT ============
    path('api/recouvrement/dashboard-data/', rec_base.rec_dashboard_data, name='rec_dashboard_data'),
    path('api/recouvrement/dashboard-details/', rec_base.rec_dashboard_details, name='rec_dashboard_details'),
    path('api/recouvrement/classes/', rec_api.rec_get_classes_actives, name='rec_get_classes'),
    path('api/recouvrement/eleves/', rec_api.rec_get_eleves_classe, name='rec_get_eleves'),
    path('api/recouvrement/variables-restant/', rec_api.rec_get_variables_restant, name='rec_get_variables'),
    path('api/recouvrement/banques/', rec_api.rec_get_banques, name='rec_get_banques'),
    path('api/recouvrement/categories/', rec_api.rec_get_categories, name='rec_get_categories'),
    path('api/recouvrement/comptes/<int:id_banque>/', rec_api.rec_get_comptes_banque, name='rec_get_comptes'),
    path('api/recouvrement/paiements-submitted/', rec_api.rec_get_paiements_submitted, name='rec_paiements_submitted'),
    path('api/recouvrement/paiements-validated/', rec_api.rec_get_paiements_validated, name='rec_paiements_validated'),
    path('api/recouvrement/paiements-eleve/', rec_api.rec_get_paiements_eleve, name='rec_paiements_eleve'),
    path('api/recouvrement/derogation-reduction/', rec_api.rec_get_existing_derogation_reduction, name='rec_derog_red'),
    path('api/recouvrement/penalites/', rec_api.rec_get_penalites, name='rec_get_penalites'),
    path('api/recouvrement/operations/', rec_api.rec_get_operations_caisse, name='rec_get_operations'),
    path('api/recouvrement/categories-operations/', rec_api.rec_get_categories_operations, name='rec_get_cat_ops'),
    path('api/recouvrement/dates-butoires/', rec_api.rec_get_date_butoires, name='rec_get_dates'),
    path('api/recouvrement/variables-all/', rec_api.rec_get_all_variables, name='rec_get_all_vars'),
    path('api/recouvrement/prix-classe/', rec_api.rec_get_prix_classe, name='rec_get_prix_classe'),
    # Save
    path('api/recouvrement/save-categorie-variable/', rec_save.rec_save_categorie_variable, name='rec_save_cat'),
    path('api/recouvrement/save-variable/', rec_save.rec_save_variable, name='rec_save_var'),
    path('api/recouvrement/save-banque/', rec_save.rec_save_banque, name='rec_save_banque'),
    path('api/recouvrement/save-compte/', rec_save.rec_save_compte, name='rec_save_compte'),
    path('api/recouvrement/save-variable-prix/', rec_save.rec_save_variable_prix, name='rec_save_prix'),
    path('api/recouvrement/save-paiement/', rec_save.rec_save_paiement, name='rec_save_paiement'),
    path('api/recouvrement/save-derogation/', rec_save.rec_save_derogation, name='rec_save_derog'),
    path('api/recouvrement/save-reduction/', rec_save.rec_save_reduction, name='rec_save_red'),
    path('api/recouvrement/save-date-butoire/', rec_save.rec_save_date_butoire, name='rec_save_date'),
    path('api/recouvrement/save-penalite/', rec_save.rec_save_penalite, name='rec_save_pen'),
    path('api/recouvrement/save-categorie-operation/', rec_save.rec_save_categorie_operation, name='rec_save_cat_op'),
    path('api/recouvrement/save-operation/', rec_save.rec_save_operation_caisse, name='rec_save_op'),
    path('api/recouvrement/delete-paiement/<int:id_paiement>/', rec_save.rec_delete_paiement, name='rec_del_paie'),
    path('api/recouvrement/delete-operation/<int:id_operation>/', rec_save.rec_delete_operation, name='rec_del_op'),
    # Update
    path('api/recouvrement/update-paiement-field/', rec_upd.rec_update_paiement_field, name='rec_upd_field'),
    path('api/recouvrement/update-categorie/<int:categorie_id>/', rec_upd.rec_update_categorie, name='rec_upd_cat'),
    path('api/recouvrement/update-variable/<int:variable_id>/', rec_upd.rec_update_variable, name='rec_upd_var'),
    path('api/recouvrement/update-banque/<int:banque_id>/', rec_upd.rec_update_banque, name='rec_upd_banque'),
    path('api/recouvrement/update-compte/<int:compte_id>/', rec_upd.rec_update_compte, name='rec_upd_compte'),
    path('api/recouvrement/update-paiement/<int:id_paiement>/', rec_upd.rec_update_paiement, name='rec_upd_paie'),
    path('api/recouvrement/update-variable-obligatoire/', rec_upd.rec_update_variable_obligatoire, name='rec_upd_oblig'),
    # PDF
    path('api/recouvrement/invoice/<int:id_paiement>/', rec_inv.rec_generate_invoice, name='rec_invoice'),
    path('api/recouvrement/fiche-paie/', rec_inv.rec_generate_fiche_paie_classe, name='rec_fiche_paie'),

    # ============ PARENT PORTAL (PWA) ============
    path('parent/login/', pv.parent_login_view, name='parent_login'),
    path('parent/logout/', pv.parent_logout, name='parent_logout'),
    path('parent/api/check-email/', pv.parent_check_email, name='parent_check_email'),
    path('parent/api/request-otp/', pv.parent_request_otp, name='parent_request_otp'),
    path('parent/api/verify-otp/', pv.parent_verify_otp, name='parent_verify_otp'),
    path('parent/api/set-password/', pv.parent_set_password, name='parent_set_password'),
    path('parent/api/login-password/', pv.parent_login_password, name='parent_login_password'),
    path('parent/', pv.parent_home, name='parent_home'),
    path('parent/child/<int:id_eleve>/', pv.parent_child_view, name='parent_child'),
    path('parent/api/children/', pv.api_parent_children, name='api_parent_children'),
    path('parent/api/child-notes/', pv.api_parent_child_notes, name='api_parent_child_notes'),
    path('parent/api/child-payments/', pv.api_parent_child_payments, name='api_parent_child_payments'),

    # ── Parent: Profil complet + update + photo ──
    path('parent/api/profile/', pv.api_parent_child_profile, name='api_parent_child_profile'),
    path('parent/api/profile/update/', pv.api_parent_update_profile, name='api_parent_update_profile'),
    path('parent/api/profile/photo/', pv.api_parent_upload_photo, name='api_parent_upload_photo'),

    # ── Parent: Évaluations & Notes ──
    path('parent/api/evaluations/', parent_eval_api.api_parent_evaluations, name='api_parent_evaluations'),
    path('parent/api/notes/', parent_eval_api.api_parent_notes, name='api_parent_notes'),
    path('parent/api/bulletin/', parent_eval_api.api_parent_bulletin, name='api_parent_bulletin'),
    path('parent/api/resultats/', parent_eval_api.api_parent_resultats, name='api_parent_resultats'),

    # ── Parent: Paiements ──
    path('parent/api/payments/summary/', parent_payment_api.api_parent_payments_summary, name='api_parent_payments_summary'),
    path('parent/api/payments/options/', parent_payment_api.api_parent_payment_options, name='api_parent_payment_options'),
    path('parent/api/payments/submit/', parent_payment_api.api_parent_payment_submit, name='api_parent_payment_submit'),

    # ── Parent: Dashboard synthétique ──
    path('parent/api/dashboard/', parent_dashboard_api.api_parent_dashboard, name='api_parent_dashboard'),

    # ── Parent: Communication ──
    path('parent/api/messages/', parent_comm_api.api_parent_messages, name='api_parent_messages'),
    path('parent/api/messages/send/', parent_comm_api.api_parent_send_message, name='api_parent_send_message'),
    path('parent/api/messages/contacts/', parent_comm_api.api_parent_contacts, name='api_parent_contacts'),
    path('parent/api/messages/read/', parent_comm_api.api_parent_mark_read, name='api_parent_mark_read'),
]

