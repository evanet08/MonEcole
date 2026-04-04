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
# TABLES LOCALES SPOKE — spécifiques à l'établissement
# ============================================================

class Classe_deliberation(models.Model):
    """Délibération de classe. Classe identifiée par clés métier stables."""
    id_deliberation = models.AutoField(primary_key=True)
    date_deliberation = models.DateField()
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False)
    idCampus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False)
    id_cycle = models.ForeignKey("MonEcole_app.Cycle", on_delete=models.PROTECT, null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
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


class Responsable_classe(models.Model):
    """Responsable (titulaire) d'une classe. Classe identifiée par clés métier stables."""
    id_responsable = models.AutoField(primary_key=True)
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False)
    idCampus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False)
    id_cycle = models.ForeignKey("MonEcole_app.Cycle", on_delete=models.PROTECT, null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_personnel = models.ForeignKey("Personnel", on_delete=models.PROTECT, null=False)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "responsable_classe"
        verbose_name = "Responsable de Classe"

    def __str__(self):
        return f"Responsable {self.id_personnel} - Classe {self.id_classe} - Année {self.id_annee}"

