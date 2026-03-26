class CountryStructureRouter:
    """
    Routeur Django pour diriger les lectures/écritures
    vers la base countryStructure (Hub).

    Hub = données structurelles partagées nationalement
    Spoke = données opérationnelles spécifiques à l'établissement
    """

    # Modèles qui vivent dans countryStructure (Hub)
    ROUTED_MODELS = [
        # Structures hiérarchiques
        'Pays', 'StructurePedagogique', 'StructureAdministrative',
        'PedagogicStructureInstance',
        'AdministrativeStructureType', 'AdministrativeStructureInstance',

        # Catalogues pédagogiques
        'Classe_cycle', 'Classe', 'Cours', 'Cycle',
        'TypeSubdivision', 'Section', 'Programme', 'Domaine',

        # Établissements
        'Institution', 'Etablissement',
        'GestionnaireEtablissement', 'Regime',

        # Années scolaires
        'Annee',

        # Config établissement-année
        'EtablissementAnnee', 'EtablissementAnneeClasse',

        # Vues compatibilité → tables Hub
        'Classe_active', 'Classe_cycle_actif',
        'Annee_trimestre', 'Annee_periode',
        'Cours_par_classe',

        # Références académiques
        'Session', 'Mention',

        # Répartitions temporelles
        'RepartitionType', 'RepartitionInstance',
        'RepartitionConfigEtabAnnee',
        'RepartitionHierarchie', 'RepartitionConfigCycle',

        # Types d'évaluation/notes
        'EvaluationType', 'NoteType',

        # Cours par année
        'CoursAnnee',

        # Délibérations (config Hub)
        'Deliberation_type',
        'Deliberation_annuelle_finalite',
        'Deliberation_annuelle_condition',
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
        if app_label == 'MonEcole_app' and model_name in self.ROUTED_MODELS_LOWER:
            return db == 'countryStructure'
        if db == 'countryStructure':
            return False
        return None
