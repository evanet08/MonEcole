from django.db import models
from .classe import Classe
from .campus import Campus
from .annee import Annee
from MonEcole_app.models.models_import import Classe_cycle_actif,Classe_active



class Salle(models.Model):
    id_salle = models.AutoField(primary_key=True)
    salle = models.CharField(max_length=250,null=False)
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null= False)
    id_campus = models.ForeignKey(Campus,on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey(Classe_cycle_actif,on_delete=models.PROTECT,null= False)
    id_classe = models.ForeignKey(Classe_active,on_delete=models.PROTECT,null=False)
    partage = models.BooleanField(default=False)
    capacite = models.IntegerField()
    
    
    class Meta:
        db_table = "salle"
        verbose_name = "salle"
        
    def __str__(self):
        return self.salle

