from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from MonEcole_app import views
from MonEcole_app.views.__bulletin import generer_bulletin_pdf
from .views import country_structure as country_views


# HOME URLS
urlpatterns = [
    path('', lambda request: redirect('log_in'), name='root'),
    path('admin_user/', admin.site.urls),
    path('log_in/', views.login_view,name='log_in'),
    path('log_out/', views.log_out_view,name='log_out'),
    path('sign_up/', views.signup_page,name="sign_up"),
    path('home_administration/', views.redirect_to_parametrage,name="home_administration"),
    path('home_evaluation/', views.redirect_to_evaluation,name="home_evaluation"),
    path('home_inscription/', views.redirect_to_inscription,name="home_inscription"),
    path('home_enseignement/', views.redirect_to_enseignement,name="home_enseignement"),
    path('home_recouvrement/', views.redirect_to_recouvrement,name="home_recouvrement"),
    path('home_direction/', views.redirect_to_direction,name="home_direction"),
    path('home_suivi/', views.redirect_to_suivi_eleve,name="home_suivi"),
    path('home_archive/', views.redirect_to_achive,name="home_archive"),
    path('home_bibliotheque/', views.redirect_to_library,name="home_bibliotheque"),
    path('home_zone_pedagogique/', views.redirect_to_espace_enseignat,name="home_zone_pedagogique"),
]

# EVALUATION URLS
urlpatterns += [
    path('toggle_droit_avancement/', views.toggle_droit_avancement,name='toggle_droit_avancement'),
    path('generer_excel_file/', views.select_by_field_to_generate_file_note,name="generer_excel_file"),
    path('generer_bulletin_pdf/', generer_bulletin_pdf, name='generer_bulletin_pdf'),
    # path('generer_bulletin_pdf/', views.generer_bulletin_pdf, name='generer_bulletin_pdf'),
    path('generer_bulletin_eleve/', views.select_by_field_to_generate_bulletin, name='generer_bulletin_eleve'),
    path('import_file_note/', views.importation_notes, name='import_file_note'),
    path('create_mention/', views.create_mention, name='create_mention'),
    path('mention_edit/', views.mention_edit, name='mention_edit'),
    path('create_deliberation_type/',views.create_deliberation_type,name='create_deliberation_type'),
    path('create_deliberation_finalite/',views.create_deliberation_finalite,name='create_deliberation_finalite'),
    path('create_deliberation_condition/',views.create_deliberation_condition,name='create_deliberation_condition'),
    path('deliberation_type_edit/', views.deliberation_type_edit, name='deliberation_type_edit'),
    path('deliberation_finalite_edit/', views.deliberation_finalite_edit, name='deliberation_finalite_edit'),
    path('get_all_classes_by_year/', views.load_all_classes_by_attribution_cours_year, name='load_all_classes_by_year'),
    path('classes_by_year_without_deliberate_annual/', views.load_all_classes_by_attribution_cours_year_without_classes_deliberateAnnually, name='classes_by_year_without_deliberate_annual'),
    path('declencher_deliberation/', views.select_by_field_to_deliberate_classe, name='declencher_deliberation'),
    path('generer_deliberation_annuelle/', views.select_by_field_to_deliberate_annual, name='generer_deliberation_annuelle'),
    path('get_all_classes_with_notes/', views.load_all_classes_with_notes_by_year, name='get_all_classes_with_notes'),
    path('get_notes_by_selection/', views.get_notes_by_selection, name='get_notes_by_selection'),
    path('update_deliberation_condition/<int:id_decision>/', views.update_deliberation_condition, name='update_deliberation_condition'),
    # path('annuler_deliberation/', views.annulation_deliberations, name='annuler_deliberation'),
    path("annuler_deliberation/", views.annuler_deliberation, name="annuler_deliberation"),
    path('get_classes_year_by_tutilaire/', views.load_all_classes_by_tutilaire_classe_year, name='get_classes_year_by_tutilaire'),
    path('deliberation_par_trimestre/', views.deliberate_class_par_trimestre, name='deliberation_par_trimestre'),
    path('deliberation_par_annee/', views.deliberate_class_par_annee, name='deliberation_par_annee'),
    path('get_available_trimestres/', views.get_available_trimestres, name='get_available_trimestres'),
    path('get_all_classes_deliberate_by_year/', views.load_all_classes_deliberates_by_year, name='get_all_classes_deliberate_by_year'),
    path('get_all_classes_deliberate_by_year_tutulaire/', views.load_all_classes_deliberates_by_yea_byTutilaire, name='get_all_classes_deliberate_by_year_tutulaire'),
    # `/get_available_sessions/`
    
    path('get_all_classes_repechages/', views.load_all_repechage_classes_by_year, name='get_all_classes_repechages'),
    path('get_all_classes_repechages_tutilaire/', views.load_all_repechage_classes_byTutilaire_year, name='get_all_classes_repechages_tutilaire'),
    path('get_all_classes_deliberations_all_trimestres/', views.get_all_classes_deliberations_alliers, name='get_all_classes_deliberations_all_trimestres'),
    path('get_all_classes_deliberate_all_trimestres_Titulaire/', views.get_all_classes_deliberations_parTitulaire, name='get_all_classes_deliberate_all_trimestres_Titulaire'),
    path('get_available_sessions/', views.get_sessions_disponible, name='get_available_sessions'),
    path('get_sessions_reclammations/', views.get_sessions_reclammations, name='get_sessions_reclammations'),
    path('get_sessions_repechage/', views.get_sessions_non_usable_in_evaluations, name='get_sessions_repechage'),
    path('generate_notes_pdf/', views.generate_notes_pdf, name='generate_notes_pdf'),
    
]
# INSCRIPTION URLS
urlpatterns += [
    path('edit_eleve/<int:id_eleve>/', views.edit_eleve, name='edit_eleve'),
    # path('admin_user/', admin.site.urls),
    path('create_inscription/', views.create_inscription_eleve,name="create_inscription"),
    path('inscription_excel_file/', views.generate_excel_template,name="inscription_excel_file"),
    path('import_inscription/', views.import_eleves,name="import_inscription"),
    path('get_pupils_registred_classe/', views.get_pupils_registred_classe,name="get_pupils_registred_classe"),
    path('changer_inscription/', views.select_by_field_to_reaffect_inscription, name='changer_inscription'),
    path('charger_classes/', views.load_all_classes_by_year_without_classes_deliberated, name='charger_classes'),
    path("update_pupil_inscription/", views.reaffectation_pupil_inscription, name="update_pupil_inscription"),
    path('update_redoublement/', views.update_redoublement, name='update_redoublement'),
    path('update_status/', views.update_status, name='update_status'),
    path('generate_pupils_pdf/', views.generate_pupils_pdf, name='generate_pupils_pdf'),
    # generate_excel_template
]

# PARAMETRAGES URLS
urlpatterns += [
    # verfied_user:
    path('create_module/', views.create_module, name='create_module'),
    path('refus_user/', views.displaying_module_attribute_users, name='refus_user'),
    path('assigner_module/', views.assigner_module_user, name='assigner_module'),
    # assigner_module:
    path('check_username/', views.verified_user_test, name='check_username'),
    path("api/user-modules/", views.get_user_modules, name="get_user_modules"),
    path("api/user-modules/update/", views.update_user_module_access, name="update_user_module_access"),
    # Personnel :
    path('ajouter_personnel/', views.ajouter_personnel, name='ajouter_personnel'),
    path('acces_personnel/', views.get_all_users, name='acces_personnel'),
    # path('ajouter_personnel/', views.ajouter_personnel, name='ajouter_personnel'),
    path('get_trimestres_table/', views.get_trimestres_table, name='get_trimestres_table'),
    path('get_trimestre_par_classe/', views.get_trimestre_par_classe, name='get_trimestre_par_classe'),
    path('get_periodes_table/', views.get_periodes_table, name='get_periodes_table'),
    # editer_personnel:
    path('editer_personnel/<int:personnel_id>/', views.editer_personnel, name='editer_personnel'),
    path('ajouter_personnel_categorie/', views.ajouter_personnel_categorie, name='ajouter_personnel_categorie'),
    path('ajouter_diplome/', views.ajouter_diplome, name='ajouter_diplome'),
    path('ajouter_specialite/',views.ajouter_specialite, name='ajouter_specialite'),
    path('ajouter_vacation/', views.ajouter_vacation, name='ajouter_vacation'),
    path('ajouter_type_personnel/', views.ajouter_type_personnels, name='ajouter_type_personnel'),
    # Edition de données!!
    path('update_personnel_categorie/<int:id_personnel_category>/', views.update_personnel_categorie, name='update_personnel_categorie'),
    path('update_diplome/<int:id_diplome>/', views.update_personnel_diplome, name='update_diplome'),
    path('update_specialite/<int:id_specialite>/', views.update_personnel_speciality, name='update_specialite'),
    path('update_vacation/<int:id_vacation>/', views.update_personnel_vacation, name='update_vacation'),
    path('update_type/<int:id_type_personnel>/', views.update_personnel_type_personnel, name='update_type'),

    # campus and instutions
    path('create_institution/',views.create_institution,name='create_institution' ),
    path('edit_institution/<int:id_ecole>/',views.edit_institution,name='edit_institution' ),
    path('create_campus/',views.create_campus,name='create_campus' ),
    path('update_campus/<int:campus_id>/', views.update_campus, name="update_campus"),
    path('delete_campus/<int:campus_id>/', views.delete_campus, name='delete_campus'),
    path('delete_classes/<int:id_classe>/', views.delete_classe, name='delete_classes'),
    path('delete_cycles/<int:cycle_id>/', views.delete_cycle, name='delete_cycles'),
    # classes
    path('update_class/<int:class_id>/', views.update_class, name="update_class"),
    path('update_cycle/<int:cycle_id>/', views.update_cycle, name="update_cycle"),
    path('create_classes/',views.create_classe,name='create_classes' ),
    path('create_classes_active/',views.create_classe_active,name='create_classes_active' ),
    path('create_classes_cycle/',views.create_classe_cycle,name='create_classes_cycle' ),
    path('create_classes_cycle_active/',views.create_classe_cycle_active,name='create_classes_cycle_active' ),
    path('toggle-terminale/', views.toggle_terminale_status, name='toggle_terminale_status'),

    path('update_classe_cycle_actif/<int:id_cycle_actif>/', views.update_classe_cycle_actif, name='update_classe_cycle_actif'),
    path('delete_classe_cycle_actif/<int:id_cycle_actif>/', views.delete_classe_cycle_actif, name='delete_classe_cycle_actif'),
    path('update_classe_active/<int:id_classe_active>/',  views.update_classe_active, name='update_classe_active'),
    path('delete_classe_active/<int:id_classe_active>/', views.delete_classe_active, name='delete_classe_active'),
    path('get_active_annees/', views.get_active_annees, name='get_active_annees'),
    path('get_active_campus/', views.get_active_campus, name='get_active_campus'),
    path('get_active_cycles/', views.get_active_cycles, name='get_active_cycles'),
    path('get_active_cycles_actifs/', views.get_active_cycles_actifs, name='get_active_cycles_actifs'),
    path('get_active_classes/', views.get_active_classes, name='get_active_classes'),
    path('get_active_cycles_by_campus_annee/', views.get_active_cycles_by_campus_annee, name='get_active_cycles_by_campus_annee'),
    path('get_all_classes/', views.get_all_classes, name='get_all_classes'),
    # path('get_active_classes_by_campus_annee_cycle/', views.get_active_classes_by_campus_annee_cycle, name='get_active_classes_by_campus_annee_cycle'),
    # path('get_groupe_by_campus_annee_cycle_classe/', views.get_groupe_by_campus_annee_cycle_classe, name='get_groupe_by_campus_annee_cycle_classe'),
    # Annees
    path('create_annees/',views.create_annee_scolaire,name='create_annees' ),
    path('create_trimestre/',views.create_trimestre,name='create_trimestre' ),
    path('create_trimestre_annee/',views.create_annee_trimestre,name='create_trimestre_annee' ),
    path('create_periode/',views.create_periode,name='create_periode' ),
    path('delete_annee/<int:id_annee>/', views.delete_annee, name='delete_annee'),
    
    # get_all_trimestres
    
    path('update_annee/<int:id_annee>/',views.update_annee,name='update_annee'),
    path('create_annee_periode/', views.create_annee_periode, name='create_annee_periode'),
    path('update_trimestre/<int:id_trimestre>/', views.update_trimestre, name='update_trimestre'),
    path('delete_trimestre/<int:id_trimestre>/', views.delete_trimestre, name='delete_trimestre'),
    path('update_periode/<int:id_periode>/', views.update_periode, name='update_periode'),
    path('delete_periode/<int:id_periode>/', views.delete_periode, name='delete_periode'),
    path('get_active_trimestres/',views.get_active_trimestres, name='get_active_trimestres'),

    path('get_all_years/', views.get_all_years, name='get_all_years'),
    path('update_annee_periode/', views.update_annee_periode, name='update_annee_periode'),
    path('update_annee_trimestre/', views.update_annee_trimestre, name='update_annee_trimestre'),
    path('classe_active_responsable_form/', views.create_responsabl_class_form, name='classe_active_responsable_form'),
    path('get_personnel/', views.get_personnel, name='get_personnel'),
    # path('get_classe_responsables/', views.get_classe_responsables, name='get_classe_responsables'),
]
# Enseignement:
urlpatterns += [
    # check_course_in_cycle
    path("create_cours/", views.create_cours, name="create_cours"),
    path("list_cours_attribution/", views.get_all_course_attribute, name="list_cours_attribution"),
    # no useble===============
    path("check_course_in_cycle/", views.check_cours_parCycle_pop, name="check_course_in_cycle"),
    path("check_courseClasse_pop/", views.check_cours_parClasse_pop, name="check_courseClasse_pop"),
    # 1111=============
    path("attribution_type_cours/", views.create_attribution_type, name="attribution_type_cours"),
    path('attribution_create/', views.attribution_create, name='attribution_create'),
    path("attribution_cours/", views.attribute_cours_display, name="attribution_cours"),
    path("attribution_par_classe/", views.attribute_cours_display, name="attribution_par_classe"),
    path("organiser_cours_classes/", views.create_cours_par_classe, name="organiser_cours_classes"),
    path("create_cours_cycle/", views.create_cours_par_cycle, name="create_cours_cycle"),
    path('update_cours/<int:cours_id>/', views.update_cours, name='update_cours'),
    path('get_cycles_parCours/', views.get_cycles_parCours, name='get_cycles_parCours'),
    path('get_cours_par_annnee/', views.get_all_coursPar_cycle_annee, name='get_cours_par_annnee'),
    path('get_attributions_by_classe/', views.get_attributions_html, name='get_attributions_by_classe'),
    # Espace_enseignant urls :

    path('visualiser_mescours/', views.get_all_coursPar_cycle_annee, name='visualiser_mescours'),
    path('get_active_cours/', views.get_active_cours, name='get_active_cours'),
    # path('update_cours_active/<int:id_cours>/', views.update_cours_classe, name='update_cours_active'),
    path('update_cours_classe/<int:id_cours>/', views.update_cours_classe, name='update_cours_classe'),
    path('update_cours_par_cycle/<int:id_cours_cycle>/', views.update_cours_par_cycle, name='update_cours_par_cycle'),
    path('update_attribution_cours/<int:id_attribution>/', views.update_attribution_cours, name='update_attribution_cours'),
    path('get_active_attribution_types/', views.get_active_attribution_types, name='get_active_attribution_types'),
   
    # classes par annee en fonction d'utilisateur connecté!
    path('get_classes_for_user/', views.list_ofclasses_next_pour_avancement, name='get_classes_for_user'),
    path('get_active_personnel/', views.get_active_personnel, name='get_active_personnel'),
    path('get_evaluations/', views.get_evaluations, name='get_evaluations'),
    path('avancement_next_class/', views.get_students_for_next_or_same_class_year, name='avancement_next_class'),

    # ========================Gestions des horaires et calendriers scolaires
    path('type_horaire/', views.etablir_type_horaire, name='type_horaire'),
    path('create_horaire/', views.etablir_horaire_annuelle, name='create_horaire'),
    path('get_horaire_type/', views.get_horaire_type, name='get_horaire_type'),
    path("get_cours_by_classe/", views.get_cours_by_classe, name="get_cours_by_classe"),
    path("get_cours_by_classe_with_typeNotes/", views.get_cours_by_classe_par_type_notes, name="get_cours_by_classe_with_typeNotes"),
    path("get_cours_by_classe_titulaire/", views.get_cours_by_classe_titulaire, name="get_cours_by_classe_titulaire"),
    path("get_cours_non_attribuer_by_classe/", views.get_non_attributed_cours_by_classe, name="get_cours_non_attribuer_by_classe"),
    path("get_cours_by_classe_Evaluataion/", views.displaying_course_by_classe_with_evaluation, name="get_cours_by_classe_Evaluataion"),
    path('save_session_data/', views.save_session_data, name='save_session_data'),
    path('afficher_horaire/', views.view_horaire, name='afficher_horaire'),
    path('filter_horaire/', views.afficher_horaire, name='filter_horaire'),
    path('get_types_notes/', views.get_note_type, name='get_types_notes'),
    path('get_types_notes_devoir/', views.get_note_type_devoir, name='get_types_notes_devoir'),
    path('get_types_notes_par_evaluation/', views.get_note_type_par_cours_evaluer, name='get_types_notes_par_evaluation'),
    path('get_types_notes_repechages/', views.get_note_type_pour_repechage, name='get_types_notes_repechages'),
    path('get_trimestres/', views.get_all_trimestres, name='get_trimestres'),
    path('get_trimestres_par_classe/', views.get_all_trimestres_par_classe, name='get_trimestres_par_classe'),
    path('get_trimestres_par_classe_with_notes/', views.get_all_trimestres_par_classe_avec_notes, name='get_trimestres_par_classe_with_notes'),
    path('get_last_trimestre_par_classe/', views.get_last_trimestres_par_classe, name='get_last_trimestre_par_classe'),
    path('get_periodes_par_classe/', views.get_all_periodes_par_classe, name='get_periodes_par_classe'),
    
    path('get_periodes_par_classe_with_notes/', views.get_all_periodes_par_classe_avec_notes, name='get_periodes_par_classe_with_notes'),
    path('get_periodes/', views.get_all_periodes, name='get_periodes'),
    
    # path('get_trimestres_par_annee/', views.get_all_trimestres_par_annee, name='get_trimestres_par_annee'),
    
    path('get_trimestre_by_evaluation/', views.get_trimestres_by_evaluationsCours_soumises, name='get_trimestre_by_evaluation'),
    path('get_periode_by_trimestre/', views.get_periodes_by_trimestre, name='get_periode_by_trimestre'),
    path('get_periode_by_trimestre_coursEvaluer/', views.get_periodes_by_trimestre_coursEvaluation, name='get_periode_by_trimestre_coursEvaluer'),
    path('generate_excel/', views.generate_excel_file_notes, name='generate_excel'),
    path('create_session/', views.add_session, name='create_session'),
    path('session_edit/', views.session_edit, name='session_edit'),
    path('get_all_sessions/', views.get_all_sessions_created, name='get_all_sessions'),
    path('get_all_sessions_without_repechage/', views.get_all_sessions_created_excludeOne, name='get_all_sessions_without_repechage'),
    path('get_sessions_par_coursEvaluer/', views.get_sessions_created_parCours_evaluation, name='get_sessions_par_coursEvaluer'),
    
    # get_all_sessions
    path('add_types_notes/', views.add_note_type, name='add_types_notes'),
    path('generate_horaire_pdf/', views.generate_horaire_pdf, name='generate_horaire_pdf'),
    path('get_classes_with_horaire/', views.get_classes_with_horaire, name='get_classes_with_horaire'),
    path('get_classe_cycle_active_year/', views.load_classes_by_year_exclude_classes_schedule, name="get_classe_cycle_active_year"),
    path('get_classes_by_year_registed/', views.load_all_classes_with_pupils_registred_by_year, name='get_classes_by_year_registed'),
    path('get_all_classes_without_condition_by_year/', views.load_all_classes_without_decision_deliberat_by_year, name='get_all_classes_without_condition_by_year'),
    path('get_all_classes_by_evaluations/', views.load_all_classes_have_evaluations_by_year, name='get_all_classes_by_evaluations'),
    path('get_evaluations_by_cours_select/', views.get_evalutions_by_select_specific, name="get_evaluations_by_cours_select"),
    path('get_available_finalites/', views.load_available_finalites, name='load_available_finalites'),
    path('get_all_finalites/', views.load_all_finalites, name='load_all_finalites'),
    path('update_deliberation_condition/<int:id_decision>/', views.update_deliberation_condition, name='update_deliberation_condition'),
    path('get_cycles_by_classe/', views.get_cycles_by_classe, name='get_cycles_by_classe'),
    path('get_classe_exclude_responsable_year/', views.load_classes_by_year_exclude_responsible, name="get_classe_exclude_responsable_year"),
    path('delete_responsable/', views.delete_responsable, name='delete_responsable'),

]
# Espace_enseignant
urlpatterns +=[
    path('get_campus_localisation/',views.get_campus_localisation, name='get_campus_localisation'),
    path('add_evaluation/', views.soumettre_evaluation_prevu,name="add_evaluation"),
    path('affichage_notes/', views.get_notes_by_type_displaying,name="affichage_notes"),
    path('soumettre_devoir/', views.soumettre_evaluation_prevu,name="soumettre_devoir"),
    path('reclammations/', views.select_by_field_for_complaints,name="reclammations"),
    path('repechages_notes/', views.select_by_field_for_repechages,name="repechages_notes"),
    path('reclammations_submit/', views.update_note_after_reclammations,name="reclammations_submit"),
    path('get_pupils_to_complaint/', views.get_pupils_list_for_complaints,name="get_pupils_to_complaint"),
    path('get_course_to_complaint_by_pupil/', views.get_repechage_courses_by_pupil,name="get_course_to_complaint_by_pupil"),
    # services_mail:api
    path('test-sendgrid/', views.test_sendgrid_email, name='test_sendgrid'),
    path('repechage_submit/', views.update_note_after_repechages,name="repechage_submit"),
    path("get_cours_notes_by_classe/", views.get_cours_with_notes_by_classe, name="get_cours_notes_by_classe"),
    path("get_notes_type_with_notes/", views.get_note_type_by_cours_with_notes, name="get_notes_type_with_notes"),
    path("get_trimestres_notes_par_classe/", views.get_trimestres_with_notes, name="get_trimestres_notes_par_classe"),
    path("get_periode_notes_par_classe/", views.get_periodes_notes_par_classe, name="get_periode_notes_par_classe"),
    path("get_session_notes_par_classe/", views.get_notes_sessions_created, name="get_session_notes_par_classe"),
]

# RECOUVREMENT :
urlpatterns +=[
   path('categorie_variable/', views.ajouter_categorie_variable, name='categorie_variable'),
   path('create_variable_frais/', views.ajouter_variable, name='create_variable_frais'),
   path('update_categorie/<int:categorie_id>/', views.update_categorie, name='update_categorie'),
   path('update_variable/<int:variable_id>/', views.update_variable, name='update_variable'),
   path('get_categories/', views.get_categories, name='get_categories'),
   path('create_banque/', views.ajouter_banque_epargne, name='create_banque'),
   path('create_compte/', views.ajouter_compte_epargne, name='create_compte'),
   path('update_banque/<int:banque_id>/', views.update_banque, name='update_banque'),
   path('get_banques/', views.get_banques, name='get_banques'),
   path('update_compte/<int:compte_id>/', views.update_compte, name='update_compte'),
   path('create_variable_prix', views.ajouter_variable_prix, name='create_variable_prix'),
   path('create_variable_reduction', views.ajouter_reduction_for_pupil, name='create_variable_reduction'),
   path('create_derogation_classe', views.ajouter_variable_derogation, name='create_derogation_classe'),
   path('store_annee_session/', views.store_annee_session, name='store_annee_session'),
   path('get_classes_actives/<int:annee_id>/', views.get_classes_actives, name='get_classes_actives'),
   path('get_classes_actives_with_paie/<int:annee_id>/', views.get_classes_actives_avec_paiement, name='get_classes_actives_with_paie'),
   path('save_variable_prix/', views.save_variable_prix, name='save_variable_prix'),
   path('save_variable_derogation/', views.save_variable_derogation, name='save_variable_derogation'),
   path('save_variable_reduction/', views.save_variable_reduction, name='save_variable_reduction'),
   path('ajouter_date_butoire/', views.ajouter_date_butoire_for_anyclass, name='ajouter_date_butoire'),
   path('save_date_butoire/', views.save_variable_date_butoire, name='save_date_butoire'),
   path('ajouter_paiement/', views.add_paiement_for_anyclass, name='ajouter_paiement'),
   path('get_comptes_banque/<int:id_banque>/', views.get_comptes_banque, name='get_comptes_banque'),
   path('save_paiement/', views.save_paiement, name='save_paiement'),
   path('afficher_paiement_submitted/', views.get_all_paiement_soumises, name='afficher_paiement_submitted'),
   path('paiement_valider/', views.get_all_paiement_soumises, name='paiement_valider'),
   path('get_paiements_submitted/', views.get_paiements_submitted, name='get_paiements_submitted'),
   path('get_paiements_validated/', views.get_paiements_validated, name='get_paiements_validated'),
   path('update_paiement_field/', views.update_paiement_field, name='update_paiement_field'),
   path('generate_invoice/<int:id_paiement>/', views.generate_invoice, name='generate_invoice'),
   path('generate_fiche_paie_classe/', views.generate_fiche_paie_classe, name='generate_fiche_paie_classe'),
   
]


# Direction :
urlpatterns +=[
   path('api/inscription-stats/', views.get_inscription_stats, name='inscription_stats'),
   path('api/campus-options/', views.get_campus_options, name='campus_options'),
   path('api/cycle-options/', views.get_cycle_options, name='cycle_options'),
   path('api/classe-options/', views.get_classe_options, name='classe_options'),
   path('generate_b/<int:eleve_id>/', views.generate_bulletin_superieur_secondLevel_rdc, name='classe_options'),
   path('generate_m/<int:eleve_id>/', views.generate_bulletin_maternelle_rdc, name='classe_options'),
   

]


# JS urls
urlpatterns += [
    path('get_class_for_edit/<int:class_id>/', views.get_class_for_edit, name="get_class_for_edit"),
    path('get_cycle_for_edit/<int:cycle_id>/', views.get_cycle_for_edit, name="get_cycle_for_edit"),
    path('get_cycles_parAnnee/', views.get_cycles_parFiltration, name='get_cycles_parAnnee'),
    path('get_classes/', views.get_classes_actives_by_cycle_annee, name='get_classes'),
    path('get_classes_pop/', views.get_classes_pop, name='get_classes_pop'),
    path('get_cours_table/', views.get_cours_table, name='get_cours_table'),
    path('get_horaire_parclasse_annee/', views.get_horaire_parclasse_annee, name='get_horaire_parclasse_annee'),
    path('get_campus/', views.get_campus, name='get_campus'),
    path('get_annees/', views.get_annees, name='get_annees'),
    path('update-checkbox/', views.update_checkbox, name='update_checkbox'),
    path('update_is_second_semester/', views.update_is_second_semester, name='update_is_second_semester'),
    
]
# STRUCTURATION PAR PAYS
urlpatterns += [
    path('structuration_pays/', country_views.structuration_pays_view, name='structuration_pays'),
    path('structuration_pays/api/pays/get/', country_views.get_pays_data, name='get_pays_data'),
    path('structuration_pays/api/pays/save/', country_views.save_pays, name='save_pays'),
    path('structuration_pays/api/structure-pedagogique/add/', country_views.add_structure_pedagogique, name='add_structure_pedagogique'),
    path('structuration_pays/api/structure-administrative/add/', country_views.add_structure_administrative, name='add_structure_administrative'),
    path('structuration_pays/api/structure-pedagogique/delete/', country_views.delete_structure_pedagogique, name='delete_structure_pedagogique'),
    path('structuration_pays/api/structure-administrative/delete/', country_views.delete_structure_administrative, name='delete_structure_administrative'),
    path('structuration_pays/api/pays/adjust-levels/', country_views.adjust_levels, name='adjust_levels'),
    path('structuration_pays/api/generate-code/', country_views.generate_code_api, name='generate_code_api'),
]

