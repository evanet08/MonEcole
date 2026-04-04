from django.db import models


class VariableCategorie(models.Model):
    id_variable_categorie = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=200,null=False)

    class Meta:
        db_table = "recouvrment_variable_categorie"

    def __str__(self):
        return f'{self.nom}'


class Variable(models.Model):
    id_variable = models.AutoField(primary_key=True)
    variable = models.CharField(max_length=200,null=False)
    id_variable_categorie = models.ForeignKey('VariableCategorie',on_delete=models.PROTECT,null=False)
    estObligatoire = models.BooleanField(default=False)

    class Meta:
        db_table = "recouvrment_variable"

    def __str__(self):
        return self.variable


class VariableDatebutoire(models.Model):
    id_datebutoire = models.AutoField(primary_key=True)
    id_variable = models.ForeignKey("Variable",on_delete=models.PROTECT,null=False)
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
    date_butoire = models.DateField()

    class Meta:
        db_table = "recouvrment_variable_datebutoire"

    def __str__(self):
        return self.id_variable


class VariableDerogation(models.Model):
    id_derogation = models.AutoField(primary_key=True)
    id_eleve = models.ForeignKey("Eleve",on_delete=models.PROTECT,null=False)
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
    date_derogation = models.DateField()

    class Meta:
        db_table = "recouvrment_variable_derogation"

    def __str__(self):
        return self.id_eleve


class VariablePrix(models.Model):
    id_prix = models.AutoField(primary_key=True)
    id_variable = models.ForeignKey("Variable",on_delete=models.PROTECT,null=False)
    prix = models.PositiveIntegerField()
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False, db_constraint=False)
    idCampus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey("MonEcole_app.Cycle",on_delete=models.PROTECT,null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('MonEcole_app.Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)

    class Meta:
        db_table = "recouvrment_variable_prix"

    def __str__(self):
        return f'{self.prix}_{self.idCampus.campus}_{self.id_classe.classe}_{self.id_annee.annee}'


class Banque(models.Model):
    id_banque = models.AutoField(primary_key=True)
    banque = models.CharField(max_length=200,null=False)
    sigle = models.CharField(max_length=120,null=True,blank=True)

    class Meta:
        db_table = "recouvrment_banque"

    def __str__(self):
        return self.banque


class Compte(models.Model):
    id_compte = models.AutoField(primary_key=True)
    compte = models.CharField(max_length=200,null=False)
    id_banque = models.ForeignKey(Banque,on_delete=models.PROTECT,null=False)

    class Meta:
        db_table = "recouvrment_compte"

    def __str__(self):
        return self.compte