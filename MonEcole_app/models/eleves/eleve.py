from django.db import models
from MonEcole_app.models.personnel import Personnel
from MonEcole_app.models.mention import Mention
from MonEcole_app.models.country_structure import (
    Session, Cycle, RepartitionInstance
)
from phonenumber_field.modelfields import PhoneNumberField
from MonEcole_app.variables import *

class Eleve(models.Model):
    id_eleve = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=250,null=False)
    prenom = models.CharField(max_length=50,null=False)
    genre = models.CharField(max_length=50,choices=sexe_choices, default='M')
    etat_civil = models.CharField(max_length=50,choices=etat_civil_choices, default='Célibataire',null=True,blank=True)
    code_eleve = models.CharField(max_length=250,null=True,blank=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    code_annee = models.IntegerField(default=0,null=True,blank=True)
    matricule = models.CharField(max_length=50,null=True,blank=True)
    email = models.EmailField(null=True,blank=True)
    password_parent=models.CharField(max_length=300,null=True,blank=True)
    password=models.CharField(max_length=300,null=True,blank=True)
    tutaire = models.CharField(max_length=250,null=True,blank=True)
    telephone = PhoneNumberField(region='BI', null=True, blank=True)
    date_naissance = models.DateField(auto_now_add=True)
    ref_administrative_naissance = models.CharField(max_length=500, blank=True, null=True)
    ref_administrative_residence = models.CharField(max_length=500, blank=True, null=True)
    imageUrl = models.ImageField(upload_to='logos/eleves/', blank=True, null=True)
    nationalite = models.CharField(max_length=50, default='',null=True,blank=True)
    profsion_tutaire= models.CharField(max_length=100, default='',null=True,blank=True)
    IDelivranceLieuEtDate = models.CharField(max_length=100, default='',null=True,blank=True)
    code_secret_parent = models.CharField(max_length=250,null=True,blank=True)
    code_secret_eleve = models.CharField(max_length=250,null=True,blank=True)
    numero_serie = models.CharField(max_length=100, null=True, blank=True)
    id_parent = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)
    IDNational = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f'{self.nom} {self.prenom}'

    class Meta:
        db_table = 'eleve'

class Eleve_inscription(models.Model):
    """
    Inscription d'un élève dans une classe pour une année.
    La classe est identifiée par (classe_id + groupe + section_id) — clés métier stables.
    """
    id_inscription = models.AutoField(primary_key=True)
    date_inscription = models.DateField(auto_now_add=True)
    id_eleve = models.ForeignKey("Eleve", on_delete=models.PROTECT, null=False)
    idCampus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False)
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False,
                                 db_constraint=False)
    id_cycle = models.ForeignKey(Cycle, on_delete=models.PROTECT, null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    redoublement = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    isDelegue = models.BooleanField(default=False)
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.id_eleve.nom} {self.id_eleve.prenom}'

    class Meta:
        db_table = 'eleve_inscription'





class Eleve_note_type(models.Model):
    id_type_note = models.AutoField(primary_key=True)
    type = models.CharField(max_length=250,null=False,choices=type_name)
    sigle = models.CharField(max_length=50,null=False,choices=sigle_name)
    date = models.DateField(auto_now_add=True)
    id_pays = models.IntegerField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if self.type and self.type in TYPE_MAPPING:
            self.sigle = TYPE_MAPPING[self.type]
        super().save(*args, **kwargs)
    def __str__(self):
        return self.type

    class Meta:
        db_table = 'eleve_note_type'

class Eleve_note(models.Model):
    """
    Notes d'un élève.
    La classe est identifiée par (classe_id + groupe + section_id) — clés métier stables.
    """
    id_note = models.AutoField(primary_key=True)
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False,
                                 db_constraint=False)
    idCampus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False)
    id_cycle = models.ForeignKey(Cycle, on_delete=models.PROTECT, null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_repartition_instance = models.ForeignKey(
        RepartitionInstance, on_delete=models.PROTECT, null=True, blank=True,
        db_column='id_repartition_instance', db_constraint=False)
    id_session = models.ForeignKey(Session, on_delete=models.PROTECT, null=False,
                                   db_constraint=False)
    id_type_note = models.ForeignKey("Eleve_note_type", on_delete=models.PROTECT, null=False)
    id_cours = models.ForeignKey("Cours", on_delete=models.PROTECT, null=True,
                                 db_column="id_cours_id")
    id_eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT, null=False)
    date_saisie = models.DateField(auto_now_add=True)
    note = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    note_repechage = models.DecimalField(decimal_places=2, max_digits=5, null=True, blank=True)
    id_evaluation = models.ForeignKey('Evaluation', on_delete=models.PROTECT, null=False)
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.id_eleve.nom} {self.id_eleve.prenom}-{self.id_cours.cours}'
    class Meta:
        db_table = 'eleve_note'

class Eleve_conduite(models.Model):
    """Conduite d'un élève. Classe identifiée par clés métier stables."""
    id_eleve_conduite = models.AutoField(primary_key=True)
    id_horaire = models.ForeignKey('Horaire',on_delete=models.PROTECT,null=False)
    id_eleve = models.ForeignKey('Eleve',on_delete=models.PROTECT,null=False)
    motif  = models.CharField(max_length=255,null=False)
    quote = models.PositiveIntegerField(default=0)
    idCampus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False,
                                 db_constraint=False)
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null=False,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_session = models.ForeignKey('Session',on_delete=models.PROTECT,null=False,
                                   db_constraint=False)
    id_trimestre = models.ForeignKey('Annee_trimestre',on_delete=models.PROTECT,null=False,
                                     db_constraint=False)
    id_periode = models.ForeignKey('Annee_periode',on_delete=models.PROTECT,null=False,
                                   db_constraint=False)
    date_enregistrement = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f'{self.id_eleve.nom} {self.id_eleve.prenom}'
    class Meta:
        db_table = 'eleve_conduite'