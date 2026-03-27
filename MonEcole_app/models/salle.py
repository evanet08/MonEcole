from django.db import models
from .classe import Classe
from .campus import Campus
from .annee import Annee
from MonEcole_app.models.country_structure import Cycle, EtablissementAnneeClasse



class Salle(models.Model):
    id_salle = models.AutoField(primary_key=True)
    salle = models.CharField(max_length=250,null=False)
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null= False, db_constraint=False)
    id_campus = models.ForeignKey(Campus,on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null= False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey(EtablissementAnneeClasse,on_delete=models.PROTECT,null=False,
                                  db_column='id_classe_id', db_constraint=False)
    partage = models.BooleanField(default=False)
    capacite = models.IntegerField()
    id_etablissement = models.IntegerField(null=True, blank=True)
    
    
    class Meta:
        db_table = "salle"
        verbose_name = "salle"
        
    def __str__(self):
        return self.salle

