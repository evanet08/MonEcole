from django.db import models
from .classe import Classe
from .campus import Campus
from .annee import Annee
from MonEcole_app.models.country_structure import Cycle



class Salle(models.Model):
    """Salle. Classe identifiée par clés métier stables."""
    id_salle = models.AutoField(primary_key=True)
    salle = models.CharField(max_length=250,null=False)
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null= False, db_constraint=False)
    idCampus = models.ForeignKey(Campus,on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null= False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    partage = models.BooleanField(default=False)
    capacite = models.IntegerField()
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)


    class Meta:
        db_table = "salle"
        verbose_name = "salle"

    def __str__(self):
        return self.salle
