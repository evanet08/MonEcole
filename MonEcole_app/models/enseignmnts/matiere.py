from django.db import models


# ============================================================
# TABLE STRUCTURELLE HUB (managed=False, routé vers countryStructure)
# ============================================================

class Cours(models.Model):
    """
    Catalogue national des cours/matières.
    Table Hub : countryStructure.cours (402 lignes)
    """
    id = models.BigAutoField(primary_key=True)
    id_cours = models.IntegerField()
    cours = models.CharField(max_length=150, null=False)
    code_cours = models.CharField(max_length=30, null=True, blank=True)
    classe = models.ForeignKey("Classe", on_delete=models.CASCADE,
                               db_column='classe_id', null=True,
                               related_name='cours_hub')
    domaine_id = models.IntegerField(null=True, blank=True)
    section_id = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cours"
        managed = False
        verbose_name = "Cours"
        verbose_name_plural = "Cours"

    def __str__(self):
        return self.cours


# ============================================================
# TABLES HUB — ex-VIEWs supprimées, accès direct aux tables Hub
# ============================================================

class Cours_par_classe(models.Model):
    """
    Configuration annuelle d'un cours avec pondérations.
    Table Hub DIRECTE : countryStructure.cours_annee (402 lignes)
    (ancienne VIEW db_monecole.cours_par_classe supprimée)

    Colonnes Hub : id_cours_annee, cours_id, annee_id, etablissement_id,
                   domaine_id, maxima_exam, maxima_tj, maxima_periode,
                   credits, heure_semaine, is_obligatory, ordre,
                   compte_au_nombre_echec, total_considerable_trimestre,
                   est_considerer_echec_lorsque_pourcentage_est,
                   is_second_semester, created_at, updated_at
    """
    id_cours_classe = models.AutoField(primary_key=True, db_column='id_cours_annee')
    id_cours = models.ForeignKey("Cours", on_delete=models.CASCADE,
                                 db_column='cours_id', related_name='configs_annuelles')
    id_annee = models.ForeignKey("Annee", on_delete=models.CASCADE,
                                     db_column='annee_id', related_name='cours_configs')
    etablissement = models.ForeignKey("Institution", on_delete=models.CASCADE,
                                      db_column='etablissement_id',
                                      null=True, blank=True, related_name='cours_configs')
    domaine_id = models.IntegerField(null=True, blank=True)
    maxima_exam = models.IntegerField(null=True, blank=True, db_column='maxima_exam')
    maxima_tj = models.IntegerField(null=True, blank=True, db_column='maxima_tj')
    maxima_periode = models.IntegerField(null=True, blank=True, db_column='maxima_periode')
    compte_au_nombre_echec = models.BooleanField(default=False)
    total_considerable_trimestre = models.BooleanField(default=False)
    est_considerer_echec_lorsque_pourcentage_est = models.IntegerField(null=True, blank=True)
    credits = models.IntegerField(null=True, blank=True)
    is_obligatory = models.BooleanField(default=False)
    heure_semaine = models.IntegerField(null=True, blank=True)
    ordre_cours = models.IntegerField(null=True, blank=True, db_column='ordre')
    is_second_semester = models.BooleanField(default=False)
    id_pays = models.IntegerField(null=True, blank=True)
    date_creation = models.DateTimeField(db_column='created_at')

    class Meta:
        db_table = "cours_annee"
        managed = False
        verbose_name = "Cours_par_classe"

    def __str__(self):
        return f"{self.id_cours}-{self.id_annee}"


# ============================================================
# TABLES LOCALES SPOKE — spécifiques à l'établissement
# ============================================================

# NOTE: Cours_par_cycle supprimé — les cours sont gérés dans le Hub
# (countryStructure.cours + countryStructure.cours_annee)



class Attribution_type(models.Model):
    id_attribution_type = models.AutoField(primary_key=True)
    attribution_type = models.CharField(max_length=250, null=False)
    date_creation = models.DateField(auto_now_add=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "attribution_type"
        verbose_name = "Attribution de cours"

    def __str__(self):
        return self.attribution_type


class Attribution_cours(models.Model):
    """Attribution de cours. Classe identifiée par clés métier stables."""
    id_attribution = models.AutoField(primary_key=True)
    idCampus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False)
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False, db_constraint=False)
    id_cycle = models.ForeignKey("MonEcole_app.Cycle", on_delete=models.PROTECT, null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    attribution_type = models.ForeignKey("Attribution_type", on_delete=models.PROTECT, null=False)
    id_cours = models.ForeignKey("Cours_par_classe", on_delete=models.PROTECT, null=False)
    id_personnel = models.ForeignKey("Personnel", on_delete=models.PROTECT, null=False)
    date_attribution = models.DateField(auto_now_add=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "attribution_cours"
        verbose_name = "Attribution de cours"

    def __str__(self):
        return f"{self.id_attribution} -{self.id_cours}"
