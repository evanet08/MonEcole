"""
Modèles Hub pour la gestion des bulletins.
managed=False — ces tables sont dans la DB Hub (countryStructure).
Le Spoke les lit en lecture seule via le database router.
"""
from django.db import models


class BulletinModel(models.Model):
    """Catalogue des modèles de bulletin (Primaire, Maternelle, Secondaire, etc.)"""
    id_model = models.AutoField(primary_key=True)
    model_name = models.CharField(max_length=200)
    code_model = models.CharField(max_length=50)
    id_pays = models.IntegerField(default=2)

    class Meta:
        db_table = 'bulletin_model'
        managed = False
        verbose_name = 'Modèle de Bulletin'

    def __str__(self):
        return self.model_name


class BulletinClasseModel(models.Model):
    """
    Affectation d'un modèle de bulletin à une classe Hub + cycle + année.
    id_classe_id → classes.id_classe (catalogue Hub, PAS EtablissementAnneeClasse)
    id_model_id  → bulletin_model.id_model
    id_annee_id  → annees.id_annee
    id_cycle_id  → cycles.id_cycle
    """
    id_model_classe = models.AutoField(primary_key=True)
    id_classe = models.ForeignKey(
        'Classe', on_delete=models.DO_NOTHING,
        db_column='id_classe_id', db_constraint=False,
        related_name='bulletin_classe_models'
    )
    id_model = models.ForeignKey(
        BulletinModel, on_delete=models.DO_NOTHING,
        db_column='id_model_id', db_constraint=False,
        related_name='bulletin_classe_models'
    )
    id_annee = models.ForeignKey(
        'Annee', on_delete=models.DO_NOTHING,
        db_column='id_annee_id', db_constraint=False,
        related_name='bulletin_classe_models'
    )
    id_cycle = models.ForeignKey(
        'Classe_cycle', on_delete=models.DO_NOTHING,
        db_column='id_cycle_id', db_constraint=False,
        related_name='bulletin_classe_models'
    )
    id_pays = models.IntegerField(default=2)

    class Meta:
        db_table = 'bulletin_classe_model'
        managed = False
        verbose_name = 'Affectation Bulletin-Classe'

    def __str__(self):
        return f"{self.id_classe} → {self.id_model}"
