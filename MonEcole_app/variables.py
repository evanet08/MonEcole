


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
    # ('Secondaire','Secondaire'),
    
]
cycle_list_rdc = []

CYCLES_ORDER = ['Maternelle', 'Fondamentale', 'Post Fondamentale']


trimestres_default =[('Trimestre 1','Trimestre 1'),
    ('Trimestre 2','Trimestre 2'),
    ('Trimestre 3','Trimestre 3'),
    ('Trimestre 4','Trimestre 4'),
    ('Trimestre 5','Trimestre 5'),
    ('Trimestre 6','Trimestre 6'),
    ('Trimestre 7','Trimestre 7'),
    ('Semestre 1','Semestre 1'),
    ('Semestre 2','Semestre 2'),
]

periodes_default =[('P1','P1'),
    ('P2','P2'),
    ('P3','P3'),
    ('P4','P4'),
    ('P5','P5'),
    ('P6','P6'),
    ('P7','P7'),
    ('P8','P8'),
    ('P9','P9')
]



# models.py
MODULE_URL_MAPPING = {
    'Administration': 'home_administration',
    'Inscription': 'home_inscription',
    'Evaluation': 'home_evaluation',
    'Enseignement': 'home_enseignement',
    'Institeur et son Espace': 'home_zone_pedagogique',
    'Recouvrement': 'home_recouvrement',
    'Portail des parents': 'home_parent',
    'Archive': 'home_archive',
    'Bibliotheque': 'home_bibliotheque',
    'Direction': 'home_direction',
}

modules_name = [
    ('Administration', 'Administration'),
    ('Inscription', 'Inscription'),
    ('Evaluation', 'Evaluation'),
    ('Enseignement', 'Enseignement'),
    ('Institeur et son Espace', 'Institeur et son Espace'),
    ('Recouvrement', 'Recouvrement'),
    ('Portail des parents', 'Portail des parents'),
    ('Archive', 'Archive'), 
    ('Bibliotheque', 'Bibliotheque'),
    ('Direction', 'Direction'),
    
]

url_module_name = [
    ('home_administration', 'home_administration'),
    ('home_inscription', 'home_inscription'),
    ('home_evaluation', 'home_evaluation'),
    ('home_enseignement', 'home_enseignement'),
    ('home_zone_pedagogique', 'home_zone_pedagogique'),
    ('home_recouvrement', 'home_recouvrement'),
    ('home_parent', 'home_parent'),
    ('home_archive', 'home_archive'),
    ('home_bibliotheque', 'home_bibliotheque'),
    ('home_direction', 'home_direction'),
    
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
    """Charge dynamiquement les préfixes de pays"""
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