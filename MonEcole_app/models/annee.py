from django.db import models


# ============================================================
# TABLE HUB — Année scolaire nationale
# ============================================================

class Annee(models.Model):
    """
    Année scolaire — lecture directe depuis countryStructure.annees

    Hub colonnes : id_annee, pays_id, annee, dateOuverture, dateCloture, isOpen
    isOpen = 1 si l'année est en cours, 0 sinon
    """
    id_annee = models.AutoField(primary_key=True)
    pays_id = models.IntegerField(null=True, blank=True)
    annee = models.CharField(max_length=20, null=False)
    date_ouverture = models.DateField(db_column='dateOuverture')
    date_cloture = models.DateField(db_column='dateCloture')
    isOpen = models.BooleanField(default=True, db_column='isOpen')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "annees"
        managed = False
        verbose_name = "Année_scolaire"

    def __str__(self):
        return f"{self.annee}"


# ============================================================
# TABLES HUB — ex-VIEWs supprimées
# Accès direct via repartition_configs_etab_annee
# ============================================================

class Annee_trimestre(models.Model):
    """
    Config trimestre/semestre pour un établissement/année.
    Table Hub : countryStructure.repartition_configs_etab_annee
    Trimestres = configs RACINE (has_parent=False).
    """
    id_trimestre = models.AutoField(primary_key=True, db_column='id')
    etablissement_annee = models.ForeignKey(
        'EtablissementAnnee', on_delete=models.CASCADE,
        db_column='etablissement_annee_id', related_name='trimestres_cfg')
    repartition = models.ForeignKey(
        'RepartitionInstance', on_delete=models.PROTECT,
        db_column='repartition_id', related_name='trimestres_cfg')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        null=True, blank=True, db_column='parent_id')
    has_parent = models.BooleanField(default=False)
    classe = models.ForeignKey(
        'Classe', on_delete=models.CASCADE,
        null=True, blank=True, db_column='classe_id')
    has_classe_specifique = models.BooleanField(default=False)
    debut = models.DateField(null=True, blank=True)
    fin = models.DateField(null=True, blank=True)
    isOpen = models.BooleanField(default=True, db_column='is_open')
    date_creation = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = "repartition_configs_etab_annee"
        managed = False
        verbose_name = "Trimestre_AnnéeScolaire"

    def __str__(self):
        return f"{self.repartition}"


class Annee_periode(models.Model):
    """
    Config période pour un établissement/année.
    Table Hub : countryStructure.repartition_configs_etab_annee
    Périodes = configs ENFANTS (has_parent=True).
    """
    id_periode = models.AutoField(primary_key=True, db_column='id')
    etablissement_annee = models.ForeignKey(
        'EtablissementAnnee', on_delete=models.CASCADE,
        db_column='etablissement_annee_id', related_name='periodes_cfg')
    repartition = models.ForeignKey(
        'RepartitionInstance', on_delete=models.PROTECT,
        db_column='repartition_id', related_name='periodes_cfg')
    id_trimestre_annee = models.ForeignKey(
        'Annee_trimestre', on_delete=models.CASCADE,
        null=True, blank=True, db_column='parent_id',
        related_name='periodes_enfants')
    has_parent = models.BooleanField(default=True)
    classe = models.ForeignKey(
        'Classe', on_delete=models.CASCADE,
        null=True, blank=True, db_column='classe_id')
    has_classe_specifique = models.BooleanField(default=False)
    debut = models.DateField(null=True, blank=True)
    fin = models.DateField(null=True, blank=True)
    isOpen = models.BooleanField(default=True, db_column='is_open')
    date_creation = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = "repartition_configs_etab_annee"
        managed = False
        verbose_name = "Période_AnnéeScolaire"

    def __str__(self):
        return f"{self.repartition}"
