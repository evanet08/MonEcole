
from django.db import models
from .rubrique_variable import Variable,Compte,Banque
from MonEcole_app.models import Eleve

class Eleve_reduction_prix(models.Model):
    id_reduction_prix = models.AutoField(primary_key=True)
    id_eleve = models.ForeignKey(Eleve,on_delete=models.PROTECT,null=False)
    idCampus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False, db_constraint=False)
    id_cycle = models.ForeignKey("MonEcole_app.Cycle",on_delete=models.PROTECT,null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('MonEcole_app.Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_variable = models.ForeignKey(Variable,on_delete=models.PROTECT,null=False)
    pourcentage = models.PositiveIntegerField()
    id_pays = models.IntegerField(default=2)

    class Meta:
        db_table = 'recouvrment_reduction_prix'

    def __str__(self):
        return self.id_eleve



class Paiement(models.Model):
    id_paiement = models.AutoField(primary_key=True)
    id_variable = models.ForeignKey(Variable,on_delete=models.PROTECT,null=False)
    montant = models.PositiveIntegerField(default=0)
    id_banque = models.ForeignKey(Banque,on_delete=models.PROTECT,null=False)
    id_compte = models.ForeignKey(Compte,on_delete=models.PROTECT,null=False)
    date_saisie = models.DateField(auto_now_add= True)
    date_paie = models.DateField()
    bordereau = models.ImageField(upload_to='invoices/',null=True,blank=True)
    id_eleve = models.ForeignKey(Eleve,on_delete=models.PROTECT,null=False)
    idCampus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False, db_constraint=False)
    id_cycle = models.ForeignKey("MonEcole_app.Cycle",on_delete=models.PROTECT,null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('MonEcole_app.Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    status = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    id_pays = models.IntegerField(default=2)

    class Meta:
        db_table = 'recouvrment_paiement'

    def __str__(self):
        return self.montant