from django.db import models
from MonEcole_app.variables import groupes, cycles_list


# ============================================================
# TABLES STRUCTURELLES HUB (managed=False, routés vers countryStructure)
# ============================================================


class Classe_cycle(models.Model):
    """
    Cycles d'enseignement nationaux (Fondamental, Post-Fondamental...).
    Table Hub : countryStructure.cycles
    L'activation se fait via EtablissementAnneeClasse (quelles classes/cycles
    un établissement utilise), pas au niveau du catalogue.
    """
    id_cycle = models.AutoField(primary_key=True)
    cycle = models.CharField(max_length=200, db_column='nom')

    class Meta:
        db_table = "cycles"
        managed = False
        verbose_name = "Cycle de Classe"

    def __str__(self):
        return self.cycle


class Classe(models.Model):
    """
    Catalogue national des classes.
    Table Hub : countryStructure.classes
    """
    id_classe = models.AutoField(primary_key=True)
    classe = models.CharField(max_length=100, db_column='nom')
    cycle = models.ForeignKey(Classe_cycle, on_delete=models.CASCADE,
                              db_column='cycle_id', null=True,
                              related_name='classes_hub')
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "classes"
        managed = False
        verbose_name = "Classe"

    def __str__(self):
        return self.classe


# ============================================================
# TABLES HUB — ex-VIEWs supprimées, accès direct aux tables Hub
# ============================================================

class Classe_active(models.Model):
    """
    Classes activées pour un établissement/année.
    Table Hub DIRECTE : countryStructure.etablissements_annees_classes
    (ancienne VIEW db_monecole.classe_active supprimée)

    Colonnes Hub : id, etablissement_annee_id, classe_id, section_id, groupe, created_at
    """
    id_classe_active = models.AutoField(primary_key=True, db_column='id')
    etablissement_annee = models.ForeignKey(
        'EtablissementAnnee', on_delete=models.CASCADE,
        db_column='etablissement_annee_id', related_name='classes_activees')
    classe_id = models.ForeignKey(
        'Classe', on_delete=models.CASCADE,
        db_column='classe_id', related_name='activations')
    section_id = models.IntegerField(null=True, blank=True)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    date_creation = models.DateTimeField(db_column='created_at')

    # Propriétés dérivées (anciennement calculées par la VIEW via JOINs)
    @property
    def is_active(self):
        return True

    @property
    def isTerminale(self):
        return False

    @property
    def ordre(self):
        return self.classe_id.ordre if self.classe_id else None

    class Meta:
        db_table = "etablissements_annees_classes"
        managed = False
        verbose_name = "Classe Active"

    def __str__(self):
        return f"{self.classe_id}"


class Classe_cycle_actif(models.Model):
    """
    Cycles actifs — dérivés des classes activées dans le Hub.

    NOTE : Il n'existe PAS de table physique pour ceci dans le Hub.
    C'était un GROUP BY dans la VIEW. On garde le modèle comme proxy
    en lisant directement depuis cycles (Hub) et filtrant par
    les cycles qui ont des classes actives via EtablissementAnneeClasse.

    Pour les requêtes, utiliser :
      Classe_cycle.objects.filter(
          id_cycle__in=EtablissementAnneeClasse.objects.filter(
              etablissement_annee__etablissement_id=etab_id
          ).values('classe__cycle_id')
      )
    """
    id_cycle_actif = models.AutoField(primary_key=True, db_column='id_cycle')
    cycle = models.CharField(max_length=200, db_column='nom')

    class Meta:
        db_table = "cycles"
        managed = False
        verbose_name = "Cycle Actif"

    def __str__(self):
        return self.cycle


# ============================================================
# TABLES LOCALES SPOKE — spécifiques à l'établissement
# ============================================================

class Classe_deliberation(models.Model):
    id_deliberation = models.AutoField(primary_key=True)
    date_deliberation = models.DateField()
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False)
    id_campus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False)
    id_cycle = models.ForeignKey("Classe_cycle_actif", on_delete=models.PROTECT, null=False)
    id_classe = models.ForeignKey("Classe_active", on_delete=models.PROTECT, null=False)
    id_session = models.ForeignKey("Session", on_delete=models.PROTECT, null=False)
    showResults = models.BooleanField(default=False)
    showsResultsEnOrdre = models.BooleanField(default=False)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "classe_deliberation"
        verbose_name = "Délibération de classe"

    def __str__(self):
        return f"{self.id_deliberation}-{self.id_classe}-{self.id_annee}"


# NOTE: Classe_section supprimé — les sections/filières sont gérées dans le Hub
# (countryStructure.sections via EtablissementAnneeClasse.section_id)


class Responsable_classe(models.Model):
    """
    Responsable (titulaire) d'une classe pour une année.
    Table locale spoke : db_monecole.responsable_classe
    """
    id_classe_active_resp = models.AutoField(primary_key=True)
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False)
    id_campus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False)
    id_cycle = models.ForeignKey("Classe_cycle_actif", on_delete=models.PROTECT, null=False)
    id_classe = models.ForeignKey("Classe_active", on_delete=models.PROTECT, null=False)
    id_personnel = models.ForeignKey("Personnel", on_delete=models.PROTECT, null=False)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "responsable_classe"
        verbose_name = "Responsable de Classe"

    def __str__(self):
        return f"Responsable {self.id_personnel} - Classe {self.id_classe} - Année {self.id_annee}"


# Alias de compatibilité arrière
Classe_active_responsable = Responsable_classe
