from django.db import models
from unidecode import unidecode


# ============================================================
# MODÈLES HUB (managed=False, routés vers countryStructure)
#
# Seuls les modèles qui ne sont PAS définis dans d'autres
# fichiers spoke (classe.py, matiere.py, annee.py).
#
# Classe → défini dans classe.py (managed=False, routé)
# Classe_cycle → défini dans classe.py (managed=False, routé)
# Cours → défini dans matiere.py (managed=False, routé)
# ============================================================


# --- STRUCTURES HIÉRARCHIQUES ---

class Pays(models.Model):
    id_pays = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100, unique=True)
    sigle = models.CharField(max_length=5, unique=True)

    domaine = models.CharField(max_length=255)
    nLevelsPedagogiques = models.PositiveIntegerField(default=0)
    nLevelsAdministratifs = models.PositiveIntegerField(default=0)
    logo_ministere = models.CharField(max_length=255, blank=True, null=True)
    logo_pays = models.CharField(max_length=255, db_column='logoPays', blank=True, default='')
    armoirePays = models.CharField(max_length=255, db_column='armoirePays', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pays'
        managed = False
        verbose_name = 'Pays'
        verbose_name_plural = 'Pays'

    def __str__(self):
        return f"{self.nom} ({self.sigle})"


class StructurePedagogique(models.Model):
    id_structure = models.AutoField(primary_key=True)
    code = models.CharField(max_length=3)
    nom = models.CharField(max_length=100)
    ordre = models.PositiveIntegerField(default=1)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='structures_pedagogiques')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'structuresPedagogiques'
        managed = False
        verbose_name = 'Structure pédagogique'


class StructureAdministrative(models.Model):
    id_structure = models.AutoField(primary_key=True)
    code = models.CharField(max_length=3)
    nom = models.CharField(max_length=100)
    ordre = models.PositiveIntegerField(default=1)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='structures_administratives')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'structuresAdministratives'
        managed = False
        verbose_name = 'Structure administrative'


# --- ÉTABLISSEMENTS ---
# Le modèle unique est 'Institution' dans ecole.py (db_table='etablissements')
# Les modèles ci-dessous le référencent via la string 'Institution'



# --- ANNÉE SCOLAIRE ---
# Le modèle unique est 'Annee' dans annee.py (db_table='annees')
# Les modèles ci-dessous le référencent via la string 'Annee'


# --- CONFIG ÉTABLISSEMENT-ANNÉE ---
# Ces tables Hub remplacent les VIEWs cross-database supprimées

class EtablissementAnnee(models.Model):
    """
    Lie un établissement à une année scolaire dans le Hub.
    Utilisé pour toutes les jointures que faisaient les VIEWs.
    """
    id = models.AutoField(primary_key=True)
    etablissement = models.ForeignKey('Etablissement', on_delete=models.CASCADE,
                                      db_column='etablissement_id')
    annee = models.ForeignKey('Annee', on_delete=models.CASCADE,
                              db_column='annee_id')
    id_pays = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'etablissements_annees'
        managed = False
        verbose_name = 'Config Établissement-Année'

    def __str__(self):
        return f"{self.etablissement} - {self.annee}"


class EtablissementAnneeClasse(models.Model):
    """
    Classes activées pour un établissement/année.
    Le spoke lit directement cette table Hub + filtre par campus local.
    """
    id = models.AutoField(primary_key=True)
    etablissement_annee = models.ForeignKey(EtablissementAnnee, on_delete=models.CASCADE,
                                            db_column='etablissement_annee_id',
                                            related_name='classes_config')
    classe = models.ForeignKey('Classe', on_delete=models.CASCADE,
                               db_column='classe_id')
    section = models.ForeignKey('Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id')
    groupe = models.CharField(max_length=5, null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'etablissements_annees_classes'
        managed = False
        verbose_name = 'Classe Activée'

    def __str__(self):
        return f"{self.classe} - {self.groupe or ''}"


# --- RÉFÉRENCES ACADÉMIQUES ---

class Session(models.Model):
    id_session = models.AutoField(primary_key=True)
    session = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'sessions'
        managed = False
        verbose_name = 'Session'

    def __str__(self):
        return self.session


# Les tables 'trimestres' et 'periodes' n'existent plus.
# Tout le code utilise RepartitionInstance directement.



class Mention(models.Model):
    id_mention = models.AutoField(primary_key=True)
    mention = models.CharField(max_length=50, unique=True)
    abbreviation = models.CharField(max_length=10)
    min = models.FloatField()
    max = models.FloatField()
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'mentions'
        managed = False
        verbose_name = 'Mention'

    def __str__(self):
        return f"{self.min}%-{self.max}%"


# --- RÉPARTITIONS TEMPORELLES ---

class RepartitionType(models.Model):
    id = models.AutoField(primary_key=True)
    id_type = models.IntegerField()  # business key, per-country
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'repartition_types'
        managed = False

    def __str__(self):
        return f"{self.nom} ({self.code})"


class RepartitionInstance(models.Model):
    id = models.AutoField(primary_key=True)
    id_instance = models.IntegerField()  # business key, per-country
    type = models.ForeignKey(RepartitionType, on_delete=models.CASCADE,
                             db_column='type_id', related_name='hub_instances')
    annee = models.ForeignKey('Annee', on_delete=models.CASCADE,
                              db_column='annee_id', null=True, blank=True)
    pays = models.ForeignKey('Pays', on_delete=models.CASCADE,
                             db_column='pays_id', null=True, blank=True)
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    ordre = models.PositiveIntegerField(default=1)
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    taux_participation = models.DecimalField(max_digits=6, decimal_places=2, default=100.00)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'repartition_instances'
        managed = False

    def __str__(self):
        return f"{self.nom} ({self.code})"


class RepartitionConfigEtabAnnee(models.Model):
    """
    Configuration effective d'une répartition pour un établissement/année.
    Table unifiée remplaçant les anciennes tables trimestres/periodes.
    """
    id = models.AutoField(primary_key=True)
    etablissement_annee = models.ForeignKey(EtablissementAnnee, on_delete=models.CASCADE,
                                            db_column='etablissement_annee_id')
    repartition = models.ForeignKey(RepartitionInstance, on_delete=models.PROTECT,
                                    db_column='repartition_id')
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True, db_column='parent_id',
                               related_name='enfants')
    has_parent = models.BooleanField(default=False)
    classe = models.ForeignKey('Classe', on_delete=models.CASCADE,
                               null=True, blank=True, db_column='classe_id')
    has_classe_specifique = models.BooleanField(default=False)
    debut = models.DateField(null=True, blank=True)
    fin = models.DateField(null=True, blank=True)
    is_open = models.BooleanField(default=True)
    is_national = models.BooleanField(default=True)
    id_pays = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'repartition_configs_etab_annee'
        managed = False

    def __str__(self):
        return f"{self.etablissement_annee} - {self.repartition}"


# --- TYPES D'ÉVALUATION ET NOTES ---

class EvaluationType(models.Model):
    id_type_eval = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    sigle = models.CharField(max_length=20)
    description = models.TextField(default='')
    is_active = models.BooleanField(default=True)
    id_pays = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evaluation_types'
        managed = False

    def __str__(self):
        return f"{self.nom} ({self.sigle})"


class NoteType(models.Model):
    id_type_note = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    sigle = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'note_types'
        managed = False

    def __str__(self):
        return f"{self.nom} ({self.sigle})"


# --- COURS ANNÉE ---

class CoursAnnee(models.Model):
    """
    Configuration d'un cours pour une année avec pondérations.
    Remplace la VIEW 'cours_par_classe' supprimée.
    """
    id_cours_annee = models.AutoField(primary_key=True)
    cours = models.ForeignKey('Cours', on_delete=models.CASCADE, db_column='cours_id')
    annee = models.ForeignKey('Annee', on_delete=models.CASCADE, db_column='annee_id')
    etablissement = models.ForeignKey('Institution', on_delete=models.CASCADE,
                                      db_column='etablissement_id', null=True, blank=True)
    maxima_exam = models.IntegerField(null=True, blank=True, db_column='maxima_exam')
    maxima_tj = models.IntegerField(null=True, blank=True, db_column='maxima_tj')
    maxima_periode = models.IntegerField(null=True, blank=True, db_column='maxima_periode')
    compte_au_nombre_echec = models.BooleanField(default=False)
    total_considerable_trimestre = models.BooleanField(default=False)
    est_considerer_echec_lorsque_pourcentage_est = models.IntegerField(null=True, blank=True)
    credits = models.IntegerField(null=True, blank=True)
    is_obligatory = models.BooleanField(default=False)
    heure_semaine = models.IntegerField(null=True, blank=True)
    ordre = models.IntegerField(null=True, blank=True)
    domaine_id = models.IntegerField(null=True, blank=True)
    is_second_semester = models.BooleanField(default=False)
    id_pays = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cours_annee'
        managed = False
        verbose_name = 'Cours Année'

    def __str__(self):
        return f"{self.cours} - {self.annee}"


# --- MODÈLES HUB SUPPLÉMENTAIRES (Cours/Domaines/Sections) ---

class TypeSubdivision(models.Model):
    id_type = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=50)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='type_subdivisions')

    class Meta:
        db_table = 'type_subdivisions'
        managed = False

    def __str__(self):
        return self.nom


class Section(models.Model):
    id_section = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    type_subdivision = models.ForeignKey(TypeSubdivision, on_delete=models.CASCADE,
                                          null=True, blank=True, related_name='subdivisions')
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'sections'
        managed = False

    def __str__(self):
        return f"{self.code} - {self.nom}"


class Programme(models.Model):
    id_programme = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='programmes')

    class Meta:
        db_table = 'programmes'
        managed = False

    def __str__(self):
        return self.nom


class Domaine(models.Model):
    id_domaine = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=150)
    code = models.CharField(max_length=30, blank=True, default='')
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='domaines')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True,
                               db_column='parent_id', related_name='sous_domaines')
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'domaines'
        managed = False

    def __str__(self):
        return self.nom


# NOTE: Le modèle Cours est défini dans enseignmnts/matiere.py (db_table='cours')
# Ne PAS le redéfinir ici pour éviter les conflits Django.

# --- CONSTANTES ---

PAYS_AFRIQUE_EST = [
    ("BI", "Burundi"), ("RW", "Rwanda"), ("KE", "Kenya"),
    ("TZ", "Tanzanie"), ("UG", "Ouganda"), ("CD", "RD Congo"),
    ("SS", "Soudan du Sud"), ("ET", "Éthiopie"), ("SO", "Somalie"),
    ("DJ", "Djibouti"), ("ER", "Érythrée"),
]


# ============================================================
# MODÈLES HUB SUPPLÉMENTAIRES — nécessaires au dashboard MonEcole
# (managed=False, routés vers countryStructure)
# ============================================================


class GestionnaireEtablissement(models.Model):
    id_gestionnaire = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100)
    postnom = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=20)
    id_pays = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gestionnaires_etablissement'
        managed = False
        verbose_name = 'Gestionnaire Etablissement'

    def __str__(self):
        return f"{self.nom} {self.postnom}"


class PedagogicStructureInstance(models.Model):
    id_structure = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)
    ordre = models.PositiveIntegerField()
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='pedag_instances')
    code = models.CharField(max_length=255, blank=True, default='')
    administrative_parent = models.ForeignKey(
        'AdministrativeStructureInstance', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedagogic_locations')

    class Meta:
        db_table = 'pedagogicStructures'
        managed = False


class Etablissement(models.Model):
    """
    Version complète du modèle Etablissement (Hub), avec tous les champs
    nécessaires au dashboard. Distinct de 'Institution' (version simplifiée).
    """
    id = models.BigAutoField(primary_key=True)
    id_etablissement = models.IntegerField()  # business key, per-country
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='hub_etablissements')
    nom = models.CharField(max_length=255)
    sigle = models.CharField(max_length=50, blank=True, null=True)
    id_regime = models.IntegerField(null=True, blank=True)
    structure_pedagogique = models.ForeignKey(
        PedagogicStructureInstance, on_delete=models.SET_NULL,
        null=True, related_name='hub_etablissements'
    )
    gestionnaire = models.ForeignKey(
        GestionnaireEtablissement, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    code_ecole = models.CharField(max_length=100, blank=True, null=True)
    matricule = models.CharField(max_length=100, blank=True, null=True)
    no_dinacope = models.CharField(max_length=100, blank=True, null=True)
    reference_agrement = models.CharField(max_length=100, blank=True, null=True)
    document_agrement = models.CharField(max_length=500, blank=True, null=True)
    annee_creation = models.CharField(max_length=10, blank=True, null=True)
    annee_agrement = models.CharField(max_length=10, blank=True, null=True)
    adresse = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    telephone = models.CharField(max_length=50, blank=True, null=True)
    fax = models.CharField(max_length=50, blank=True, null=True)
    boite_postale = models.CharField(max_length=50, blank=True, null=True)
    representant = models.CharField(max_length=255, blank=True, null=True)
    emplacement = models.CharField(max_length=255, blank=True, null=True)
    ref_administrative = models.CharField(max_length=500, blank=True, null=True)
    nom_rue = models.CharField(max_length=255, blank=True, null=True)
    numero_rue = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    logo_ecole = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=500, blank=True)
    is_calendar_synched = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'etablissements'
        managed = False
        verbose_name = 'Établissement (Hub)'

    def __str__(self):
        return self.nom


class Regime(models.Model):
    id_regime = models.AutoField(primary_key=True)
    regime = models.CharField(max_length=100)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='hub_regimes')

    class Meta:
        db_table = 'regimes'
        managed = False
        verbose_name = 'Régime'

    def __str__(self):
        return self.regime


class Cycle(models.Model):
    """Version complète du modèle Cycle (Hub), avec tous les champs."""
    id = models.BigAutoField(primary_key=True)
    id_cycle = models.IntegerField()
    nom = models.CharField(max_length=100)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='cycles')
    ordre = models.PositiveIntegerField(default=1)
    duree = models.PositiveIntegerField(default=1)
    hasSections = models.BooleanField(default=False)
    coursUniformes = models.BooleanField(default=True)
    labelSection = models.ForeignKey(
        'TypeSubdivision', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='labelSection_id',
        related_name='cycles_using_label'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cycles'
        managed = False
        verbose_name = 'Cycle (Hub)'

    def __str__(self):
        return self.nom


class AdministrativeStructureType(models.Model):
    id_structure = models.AutoField(primary_key=True)
    code = models.CharField(max_length=10)
    nom = models.CharField(max_length=100)
    ordre = models.PositiveIntegerField(default=1)
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='administrative_types')

    class Meta:
        db_table = 'administrativeStructuresTypes'
        managed = False
        verbose_name = 'Type Structure Administrative'

    def __str__(self):
        return self.nom


class AdministrativeStructureInstance(models.Model):
    id_structure = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)
    ordre = models.PositiveIntegerField()
    pays = models.ForeignKey(Pays, on_delete=models.CASCADE, related_name='admin_instances')
    code = models.CharField(max_length=255, blank=True, default='')
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)

    class Meta:
        db_table = 'administrativeStructures'
        managed = False
        verbose_name = 'Instance Structure Administrative'

    def __str__(self):
        return self.nom


class RepartitionHierarchie(models.Model):
    id = models.AutoField(primary_key=True)
    id_hierarchie = models.IntegerField()  # business key, per-country
    type_parent = models.ForeignKey(RepartitionType, on_delete=models.CASCADE,
                                     related_name='enfants_hierarchie')
    type_enfant = models.ForeignKey(RepartitionType, on_delete=models.CASCADE,
                                     related_name='parents_hierarchie')
    nombre_enfants = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'repartition_hierarchies'
        managed = False

    def __str__(self):
        return f"{self.type_parent.nom} → {self.type_enfant.nom}"


class RepartitionConfigCycle(models.Model):
    id = models.AutoField(primary_key=True)
    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE,
                              db_column='cycle_id', related_name='repartition_configs')
    type_racine = models.ForeignKey(RepartitionType, on_delete=models.CASCADE,
                                     db_column='type_racine_id', related_name='configs_cycle')
    nombre_au_niveau_racine = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'repartition_configs_cycle'
        managed = False

    def __str__(self):
        return f"{self.cycle.nom} → {self.type_racine.nom}"

