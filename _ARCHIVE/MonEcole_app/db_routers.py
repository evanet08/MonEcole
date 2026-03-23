class CountryStructureRouter:
    """
    Routeur Django pour diriger les lectures/écritures
    vers la base countryStructure (Hub).

    Hub = données structurelles partagées nationalement
    Spoke = données opérationnelles spécifiques à l'établissement

    Connexion directe spoke ↔ hub via Django ORM, sans VIEWs MySQL.
    """

    # Tous les modèles qui vivent dans countryStructure (Hub)
    ROUTED_MODELS = [
        # Structures hiérarchiques (country_structure.py)
        'Pays', 'StructurePedagogique', 'StructureAdministrative',

        # Catalogues pédagogiques (classe.py et matiere.py)
        'Classe_cycle', 'Classe', 'Cours',

        # Établissements (ecole.py → db: etablissements)
        'Institution',

        # Années scolaires (annee.py → db: annees)
        'Annee',

        # Config établissement-année (country_structure.py)
        'EtablissementAnnee', 'EtablissementAnneeClasse',

        # Ex-VIEWs → pointent maintenant vers tables Hub directes
        'Classe_active',       # → etablissements_annees_classes
        'Classe_cycle_actif',  # → cycles
        'Annee_trimestre',     # → repartition_configs_etab_annee
        'Annee_periode',       # → repartition_configs_etab_annee
        'Cours_par_classe',    # → cours_annee

        # Références académiques (country_structure.py)
        'Session', 'Mention',

        # Répartitions temporelles (country_structure.py)
        'RepartitionType', 'RepartitionInstance',
        'RepartitionConfigEtabAnnee',

        # Types d'évaluation/notes (country_structure.py)
        'EvaluationType', 'NoteType',

        # Cours par année (country_structure.py)
        'CoursAnnee',
    ]

    ROUTED_MODELS_LOWER = [m.lower() for m in ROUTED_MODELS]

    def _is_routed(self, model):
        return (
            model._meta.app_label == 'MonEcole_app' and
            model.__name__ in self.ROUTED_MODELS
        )

    def db_for_read(self, model, **hints):
        if self._is_routed(model):
            return 'countryStructure'
        return None

    def db_for_write(self, model, **hints):
        if self._is_routed(model):
            return 'countryStructure'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Autorise les relations cross-database hub ↔ spoke."""
        if self._is_routed(obj1.__class__) or self._is_routed(obj2.__class__):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Les modèles Hub ne migrent que dans countryStructure.
        Les modèles spoke ne migrent que dans default.
        """
        if app_label == 'MonEcole_app' and model_name in self.ROUTED_MODELS_LOWER:
            return db == 'countryStructure'
        if db == 'countryStructure':
            return False
        return None
