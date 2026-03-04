from django.db import models
from unidecode import unidecode


class Pays(models.Model):
    """
    Modèle représentant un pays avec sa configuration de niveaux structurels.
    """
    id_pays = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=100, unique=True, verbose_name="Nom du pays")
    sigle = models.CharField(max_length=5, unique=True, verbose_name="Code pays")
    nLevelsStructuraux = models.PositiveIntegerField(
        default=0, 
        verbose_name="Nombre de niveaux pédagogiques"
    )
    nLevelsAdministratifs = models.PositiveIntegerField(
        default=0, 
        verbose_name="Nombre de niveaux administratifs"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pays'
        verbose_name = 'Pays'
        verbose_name_plural = 'Pays'
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.sigle})"

    def is_structure_pedagogique_complete(self):
        """Vérifie si la structure pédagogique est complète."""
        return self.structures_pedagogiques.count() == self.nLevelsStructuraux

    def is_structure_administrative_complete(self):
        """Vérifie si la structure administrative est complète."""
        return self.structures_administratives.count() == self.nLevelsAdministratifs

    def is_complete(self):
        """Vérifie si les deux structures sont complètes."""
        return self.is_structure_pedagogique_complete() and self.is_structure_administrative_complete()


class StructurePedagogique(models.Model):
    """
    Modèle représentant un niveau dans la hiérarchie pédagogique d'un pays.
    Exemple: DPE → DCE → Canton → École
    """
    id_structure = models.AutoField(primary_key=True)
    code = models.CharField(max_length=3, verbose_name="Code (3 caractères)")
    nom = models.CharField(max_length=100, verbose_name="Nom du niveau")
    ordre = models.PositiveIntegerField(default=1, verbose_name="Ordre hiérarchique")
    pays = models.ForeignKey(
        Pays, 
        on_delete=models.CASCADE, 
        related_name='structures_pedagogiques',
        verbose_name="Pays"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'structuresPedagogiques'
        verbose_name = 'Structure pédagogique'
        verbose_name_plural = 'Structures pédagogiques'
        ordering = ['pays', 'ordre']
        unique_together = [['pays', 'code'], ['pays', 'ordre']]

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def save(self, *args, **kwargs):
        """Auto-génère le code à partir du nom si non fourni."""
        if not self.code:
            self.code = self.generate_code(self.nom)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_code(nom):
        """Génère un code de 3 caractères à partir du nom."""
        # Enlever les accents et prendre les 3 premiers caractères
        clean_name = unidecode(nom).upper().replace(' ', '')
        return clean_name[:3] if len(clean_name) >= 3 else clean_name.ljust(3, 'X')


class StructureAdministrative(models.Model):
    """
    Modèle représentant un niveau dans la hiérarchie administrative/géographique d'un pays.
    Exemple: Province → Commune → Secteur → Colline
    """
    id_structure = models.AutoField(primary_key=True)
    code = models.CharField(max_length=3, verbose_name="Code (3 caractères)")
    nom = models.CharField(max_length=100, verbose_name="Nom du niveau")
    ordre = models.PositiveIntegerField(default=1, verbose_name="Ordre hiérarchique")
    pays = models.ForeignKey(
        Pays, 
        on_delete=models.CASCADE, 
        related_name='structures_administratives',
        verbose_name="Pays"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'structuresAdministratives'
        verbose_name = 'Structure administrative'
        verbose_name_plural = 'Structures administratives'
        ordering = ['pays', 'ordre']
        unique_together = [['pays', 'code'], ['pays', 'ordre']]

    def __str__(self):
        return f"{self.code} - {self.nom}"

    def save(self, *args, **kwargs):
        """Auto-génère le code à partir du nom si non fourni."""
        if not self.code:
            self.code = self.generate_code(self.nom)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_code(nom):
        """Génère un code de 3 caractères à partir du nom."""
        clean_name = unidecode(nom).upper().replace(' ', '')
        return clean_name[:3] if len(clean_name) >= 3 else clean_name.ljust(3, 'X')


# Liste des pays d'Afrique de l'Est (pour pré-remplir la liste)
PAYS_AFRIQUE_EST = [
    ("BI", "Burundi"),
    ("RW", "Rwanda"),
    ("KE", "Kenya"),
    ("TZ", "Tanzanie"),
    ("UG", "Ouganda"),
    ("CD", "RD Congo"),
    ("SS", "Soudan du Sud"),
    ("ET", "Éthiopie"),
    ("SO", "Somalie"),
    ("DJ", "Djibouti"),
    ("ER", "Érythrée"),
]


# ============================================================
# TABLES DE RÉFÉRENCE (migrées depuis db_monecole → countryStructure)
# Routées vers la base countryStructure via CountryStructureRouter
# managed=False car les tables sont gérées par l'app structure_app
# ============================================================

class Session(models.Model):
    """
    Table de référence des sessions d'évaluation.
    Ex: 'session ordinaire', 'Repêchage'
    Table: countryStructure.sessions
    """
    id_session = models.AutoField(primary_key=True)
    session = models.CharField(max_length=50, unique=True)
    
    class Meta:
        db_table = 'sessions'
        managed = False
        verbose_name = 'Session'
    
    def __str__(self):
        return self.session


class Trimestre(models.Model):
    """
    Table de référence des trimestres/semestres.
    Table: countryStructure.trimestres
    """
    id_trimestre = models.AutoField(primary_key=True)
    trimestre = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'trimestres'
        managed = False
        verbose_name = 'Trimestre'
    
    def __str__(self):
        return self.trimestre


class Periode(models.Model):
    """
    Table de référence des périodes d'évaluation.
    Table: countryStructure.periodes
    """
    id_periode = models.AutoField(primary_key=True)
    periode = models.CharField(max_length=20)
    trimestre = models.ForeignKey(
        Trimestre,
        on_delete=models.PROTECT,
        db_column='trimestre_id',
        related_name='periodes'
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'periodes'
        managed = False
        verbose_name = 'Période'
    
    def __str__(self):
        return f"{self.periode}"


class Mention(models.Model):
    """
    Table de référence des mentions (barèmes de notation).
    Table: countryStructure.mentions
    """
    id_mention = models.AutoField(primary_key=True)
    mention = models.CharField(max_length=50, unique=True)
    abbreviation = models.CharField(max_length=10)
    min = models.FloatField()
    max = models.FloatField()
    
    class Meta:
        db_table = 'mentions'
        managed = False
        verbose_name = 'Mention'
    
    def __str__(self):
        return f"{self.min}%-{self.max}%"
