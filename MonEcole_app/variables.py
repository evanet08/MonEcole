

etat_annee=[('En attente','En attente'),
             ('En Cours','En Cours'),
             ('Cloturée','Cloturée'),
]

sexe_choices=[('M','M'),
             ('F','F'),
]

etat_civil_choices=[('Célibataire','Célibataire'),
             ('Marié(e)','Marié(e)'),
             ('Autres','Autres'),
]

groupes =[('A','A'),
    ('B','B'),
    ('C','C'),
    ('D','D'),
    ('E','E'),
    ('F','F')
]

cycles_list =[('Maternelle','Maternelle'),
    ('Fondamentale','Fondamentale'),
    ('Post Fondamentale','Post Fondamentale'),
    ('Primaire','Primaire'),
]
cycle_list_rdc = []

CYCLES_ORDER = ['Maternelle', 'Fondamentale', 'Post Fondamentale']


# ============================================================
# MODULE → URL MAPPING (pour la nouvelle architecture 4 pages)
# ============================================================

# Ancien mapping eSchool → nouveau mapping MonEcole dashboard
MODULE_URL_MAPPING = {
    'Administration': 'dashboard_administration',
    'Scolarite': 'dashboard_scolarite',
    'Evaluation': 'dashboard_evaluations',
    'Enseignement': 'dashboard_enseignements',
    'Institeur et son Espace': 'dashboard_administration',  # redirect vers admin pour l'instant
    'Recouvrement': 'dashboard_administration',
    'Bibliotheque': 'dashboard_administration',
    'Direction': 'dashboard_administration',
}

# Mapping module_id → nouvelle page dashboard
MODULE_ID_TO_PAGE = {
    1: {'page': 'administration', 'url': '/dashboard/administration/', 'icon': 'fas fa-cogs', 'label': 'Administration'},
    2: {'page': 'scolarite', 'url': '/dashboard/scolarite/', 'icon': 'fas fa-user-graduate', 'label': 'Scolarité'},
    3: {'page': 'evaluations', 'url': '/dashboard/evaluations/', 'icon': 'fas fa-clipboard-check', 'label': 'Évaluations'},
    4: {'page': 'enseignements', 'url': '/dashboard/enseignements/', 'icon': 'fas fa-chalkboard-teacher', 'label': 'Enseignements'},
    5: {'page': 'administration', 'url': '/dashboard/administration/', 'icon': 'fas fa-school', 'label': 'Inst. & Espace'},
    6: {'page': 'administration', 'url': '/dashboard/administration/', 'icon': 'fas fa-money-bill', 'label': 'Recouvrement'},
    7: {'page': 'administration', 'url': '/dashboard/administration/', 'icon': 'fas fa-book', 'label': 'Bibliothèque'},
    8: {'page': 'administration', 'url': '/dashboard/administration/', 'icon': 'fas fa-crown', 'label': 'Direction'},
}

modules_name = [
    ('Administration', 'Administration'),
    ('Scolarite', 'Scolarite'),
    ('Evaluation', 'Evaluation'),
    ('Enseignement', 'Enseignement'),
    ('Institeur et son Espace', 'Institeur et son Espace'),
    ('Recouvrement', 'Recouvrement'),
    ('Bibliotheque', 'Bibliotheque'),
    ('Direction', 'Direction'),
]

url_module_name = [
    ('dashboard_administration', 'dashboard_administration'),
    ('dashboard_scolarite', 'dashboard_scolarite'),
    ('dashboard_evaluations', 'dashboard_evaluations'),
    ('dashboard_enseignements', 'dashboard_enseignements'),
]

type_name = [('Travail Journalier','Travail Journalier'),
             ('Examen','Examen'),
             ('Devoir','Devoir'),
             ('1ère Période','1ère Période'),
             ('2ème Période','2ème Période'),
             ('3ème Période','3ème Période'),
             ('4ème Période','4ème Période'),
             ('5ème Période','5ème Période'),
             ('6ème Période','6ème Période'),]

sigle_name = [('T.J','T.J'),
             ('Ex.','Ex.'),
             ('DàD','DàD'),
             ('1e P','1e P'),
             ('2e P','2e P'),
             ('3e P','3e P'),
             ('4e P','4e P'),
             ('5e P','5e P'),
             ('6e P','6e P'),
             ]

type_deliberations = [('Par période','Par période'),
             ('Par trimestre','Par trimestre'),
             ('Par année','Par année'),
             ('Par repêchage','Par repêchage'),
             ]

TYPE_MAPPING = {
    'Travail Journalier' : 'T.J',
    'Examen':'Ex.',
    'Devoir':'DàD'
}

sessions_available = [('Repêchage','Repêchage'),
             ('session ordinaire','session ordinaire'),
             ]


def load_country_codes():
    return [
        {"code": "+257", "country": "Burundi (+257)"},
        {"code": "+33", "country": "France (+33)"},
        {"code": "+1", "country": "USA (+1)"},
        {"code": "+44", "country": "UK (+44)"},
    ]

choices_etat_books = [('NEUF', 'Neuf'),
                      ('BON', 'Bon'),
                      ('USÉ', 'Usé'),
                      ('ENDOMMAGÉ', 'Endommagé')]
