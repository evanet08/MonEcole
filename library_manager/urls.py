

from django.contrib import admin
from django.urls import path
from library_manager.views.structure_library import( add_armoire_library,add_livre_library,
                                                    add_compartiment_library,
                                                    add_category_livre_library,
                                                    add_livre_exemplaire_library,
                                                    save_emprunt,displaying_emprunt,
                                                    redirect_ajout_emprunt,displaying_retour_emprunt)
from library_manager.views.update_views import (update_armoire,update_compartiment,
                                                update_categorie,update_livre,
                                                update_livre_exemplaire,update_emprunt,update_rendu)
from library_manager.views.api_request import (get_armoires,
                                               list_categories,
                                               list_compartiments,
                                               list_livres,
                                               get_categories_and_books
                                               ,get_annees,get_campus_options)

from library_manager.views.report_library import (generate_books_most_used_report,emprunt_books_per_periode_all_pupils,
                                                  emprunt_books_cycle,home_emprunt_most,home_emprunt_byEleve_land,home_emprunt_byPeriod_land
)

app_name = 'library'
# HOME URLS
urlpatterns = [
   path('create_armory_library/',add_armoire_library, name='create_armory_library'),
   path('create_livre_library/',add_livre_library, name='create_livre_library'),
   path('create_livre_exemplaire_library/',add_livre_exemplaire_library, name='create_livre_exemplaire_library'),
   path('create_compartiment_library/',add_compartiment_library, name='create_compartiment_library'),
   path('create_category_livre_library/',add_category_livre_library, name='create_category_livre_library'),
   path('api/armoire/<int:id>/update/', update_armoire, name='update_armoire'),
   path('api/categorie/<int:id>/update/', update_categorie, name='update_categorie'),
   path('api/emprunt/<int:id>/update/', update_emprunt, name='update_emprunt'),
   path('api/armoires/', get_armoires, name='get_armoires'),
   path('api/compartiment/<int:id>/update/',update_compartiment, name='update_compartiment'),
   path('api/livre/<int:id>/update/', update_livre, name='update_livre'),
   path('api/categories/', list_categories, name='list_categories'),
   path('api/compartiments/',list_compartiments, name='list_compartiments'),
   path('api/livres/',list_livres, name='list_livres'),
   path('api/livre-exemplaire/<int:id>/update/',update_livre_exemplaire, name='update_livre_exemplaire'),
   path('api/categories-and-books/',get_categories_and_books, name='get_categories_and_books'),
   path('api/save-emprunt/', save_emprunt, name='save_emprunt'),
   path('ajout_emprunt/', redirect_ajout_emprunt, name='ajout_emprunt'),
   path('list_emprunt/', displaying_emprunt, name='list_emprunt'),
   path('api/get_annees/', get_annees, name='api/get_annees/'),
   path('api/campus-options/', get_campus_options, name='campus_options'),
   path('list_emprunt_retour/',displaying_retour_emprunt, name='list_emprunt_retour'),
   path("update-rendu/", update_rendu, name="update_rendu"),
   
   path('report_generate_books_most_used', generate_books_most_used_report, name='report_generate_books_most_used'),
   path('emprunt_books_cycle', emprunt_books_cycle, name='emprunt_books_cycle'),
   path('emprunt_books_per_periode', emprunt_books_per_periode_all_pupils, name='emprunt_books_per_periode'),
   
   path('report_by_most_land_home', home_emprunt_most, name='report_by_most_land_home'),
   path('report_by_periode_home', home_emprunt_byPeriod_land, name='report_by_periode_home'),
   path('report_by_eleve_home',home_emprunt_byEleve_land, name='report_by_eleve_home'),
]