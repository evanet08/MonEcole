
from django.db import models
from MonEcole_app.models.enseignmnts.matiere import Cours 
from MonEcole_app.models.personnel import Personnel
from MonEcole_app.models.mention import Mention
from MonEcole_app.models.country_structure import Session, Cycle

class User_enseignement(models.Model):
    """Accès enseignant. Classe identifiée par clés métier stables."""
    id_user_enseignant = models.AutoField(primary_key=True)
    user = models.ForeignKey("Personnel", on_delete=models.PROTECT, null=False,
                              db_column='user_id', db_constraint=False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False, db_constraint=False)
    idCampus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    classe_id = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id_new', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    cycle_id = models.ForeignKey(Cycle,on_delete=models.PROTECT,null=False,
                                 db_column='cycle_id_id', db_constraint=False)
    canModify = models.BooleanField(default=False)
    canOnlyView = models.BooleanField(default=False)
    date_inscrite = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)


    class Meta:
        db_table = 'user_enseignement'

    def __str__(self):
        return self.user.prenom or self.user.nom or str(self.user.matricule)
        
class Users_other_module(models.Model):
    id_user_per_module = models.AutoField(primary_key=True)
    id_module = models.IntegerField()
    id_personnel = models.ForeignKey("Personnel",on_delete=models.PROTECT,null=False)
    user = models.BooleanField(default=False)
    date_creation = models.DateField(auto_now_add=True)
    id_pays = models.IntegerField(null=True, blank=True)
    

    class Meta:
        db_table = 'users_other_module'
        
        
    def __str__(self):
        return self.id_personnel