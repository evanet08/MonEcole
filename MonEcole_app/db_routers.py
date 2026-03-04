class CountryStructureRouter:
    """
    Un routeur pour diriger les opérations sur les modèles de structuration
    vers la base de données countryStructure.
    
    Tables routées vers countryStructure:
    - Pays, StructurePedagogique, StructureAdministrative (existant)
    - Session, Trimestre, Periode, Mention (migré depuis db_monecole)
    """
    
    # Noms des modèles qui doivent lire/écrire dans countryStructure
    ROUTED_MODELS = [
        # Structures existantes
        'Pays', 'StructurePedagogique', 'StructureAdministrative',
        # Tables de référence migrées depuis db_monecole
        'Session', 'Trimestre', 'Periode', 'Mention',
    ]
    
    # Noms lowercase pour les migrations
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
        if self._is_routed(obj1.__class__) or self._is_routed(obj2.__class__):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'MonEcole_app' and model_name in self.ROUTED_MODELS_LOWER:
            return db == 'countryStructure'
        if db == 'countryStructure':
            return False
        return None
