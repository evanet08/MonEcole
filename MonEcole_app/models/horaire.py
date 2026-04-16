
from django.db import models
from MonEcole_app.models.enseignmnts.matiere import *
from .annee import Annee
from .classe import Classe
from .campus import Campus
from .salle import Salle
from MonEcole_app.models.country_structure import Cycle
from MonEcole_app.models.eleves import Eleve


class Horaire_type(models.Model):
    id_horaire_type = models.AutoField(primary_key=True)
    horaire_type = models.CharField(max_length=200,null=False)
    id_pays = models.IntegerField(default=2)

    def __str__(self):
        return self.horaire_type
    class Meta:
        db_table = 'horaire_type'

class Horaire(models.Model):
    """Horaire. Classe identifiée par clés métier stables."""
    id_horaire = models.AutoField(primary_key=True)
    id_horaire_type = models.ForeignKey(Horaire_type,on_delete=models.PROTECT,null=False)
    idCampus = models.ForeignKey("Campus",on_delete=models.PROTECT,null= False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null= False, db_constraint=False)
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null= False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_cours = models.ForeignKey("Cours_par_classe",on_delete=models.PROTECT,null=False)
    date = models.DateField(null=False)
    debut = models.CharField(max_length=100,null=False)
    fin = models.CharField(max_length=100,null=False)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(default=2)
      
    def __str__(self):
        return f"{self.id_classe} - {self.date} {self.debut}-{self.fin}"

    class Meta:
        db_table = 'horaire'

class Horaire_presence(models.Model):
    id_horaire_presence = models.AutoField(primary_key=True)
    id_horaire = models.ForeignKey(Horaire, on_delete=models.PROTECT,null=False)
    id_eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT,null=False)
    present_ou_absent = models.BooleanField()
    date_presence = models.DateField(null=False)
    si_absent_motif = models.CharField(max_length=255,null=True)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(default=2)
    

    def __str__(self):
        return f"Presence {self.id_horaire_presence} for Eleve {self.id_eleve}"
    class Meta:
        db_table = 'horaire_presence'
