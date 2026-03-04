from django.db import models
from MonEcole_app.models.personnel import Personnel
from MonEcole_app.models.mention import Mention
from MonEcole_app.models.evaluations.note import Session
from MonEcole_app.models.annee import Annee_trimestre
from phonenumber_field.modelfields import PhoneNumberField
from MonEcole_app.variables import *

class Eleve(models.Model):
    id_eleve = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=250,null=False)
    prenom = models.CharField(max_length=50,null=False)
    genre = models.CharField(max_length=50,choices=sexe_choices, default='M')
    etat_civil = models.CharField(max_length=50,choices=etat_civil_choices, default='Célibataire',null=True,blank=True)
    code_eleve = models.CharField(max_length=250,null=True,blank=True)
    code_annee = models.IntegerField(default=0,null=True,blank=True)
    matricule = models.CharField(max_length=50,null=True,blank=True)
    nom_pere = models.CharField(max_length=200, default='',null=True,blank=True)
    prenom_pere = models.CharField(max_length=200, default='',null=True,blank=True)
    nom_mere = models.CharField(max_length=200, default='',null=True,blank=True)
    prenom_mere = models.CharField(max_length=200, default='',null=True,blank=True)
    email = models.EmailField(null=True,blank=True)
    email_parent = models.EmailField(null=True,blank=True)
    password_parent=models.CharField(max_length=300,null=True,blank=True)
    password=models.CharField(max_length=300,null=True,blank=True)
    tutaire = models.CharField(max_length=250,null=True,blank=True)
    telephone = PhoneNumberField(region='BI', null=True, blank=True)
    date_naissance = models.DateField(auto_now_add=True)
    naissance_region = models.CharField(max_length=30, default='',null=True,blank=True)
    naissance_pays = models.CharField(max_length=30, default='',null=True,blank=True)
    naissance_province = models.CharField(max_length=30, default='',null=True,blank=True)
    naissance_commune = models.CharField(max_length=30, default='',null=True,blank=True)
    naissance_zone = models.CharField(max_length=30, default='',null=True,blank=True)
    province_actuelle = models.CharField(max_length=20, default='',null=True,blank=True)
    commune_actuelle = models.CharField(max_length=20, default='',null=True,blank=True)
    zone_actuelle = models.CharField(max_length=20, default='',null=True,blank=True)
    imageUrl = models.ImageField(upload_to='logos/eleves/', blank=True, null=True)
    nationalite = models.CharField(max_length=50, default='',null=True,blank=True)
    professionPere = models.CharField(max_length=100, default='',null=True,blank=True)
    professionMere = models.CharField(max_length=100, default='',null=True,blank=True)
    profsion_tutaire= models.CharField(max_length=100, default='',null=True,blank=True)
    IDelivranceLieuEtDate = models.CharField(max_length=100, default='',null=True,blank=True)
    code_secret_parent = models.CharField(max_length=250,null=True,blank=True)
    code_secret_eleve = models.CharField(max_length=250,null=True,blank=True)
   
    
    def __str__(self):
        return f'{self.nom} {self.prenom}'

    class Meta:
        db_table = 'eleve'

class Eleve_inscription(models.Model):
    id_inscription = models.AutoField(primary_key=True)
    date_inscription = models.DateField(auto_now_add=True)
    id_eleve = models.ForeignKey("Eleve", on_delete=models.PROTECT,null=False)  
    id_trimestre = models.ForeignKey(Annee_trimestre,on_delete=models.PROTECT,null=False)
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)
    id_classe_cycle = models.ForeignKey("Classe_cycle_actif", on_delete=models.PROTECT, null=False)
    id_classe = models.ForeignKey("Classe_active",on_delete=models.PROTECT,null=False)
    redoublement = models.BooleanField(default=False) 
    status = models.BooleanField(default=True) 
    isDelegue = models.BooleanField(default=False)  

    def __str__(self):
        return f'{self.id_eleve.nom} {self.id_eleve.prenom}'

    class Meta:
        db_table = 'eleve_inscription'




class Eleve_note_type(models.Model):
    id_type_note = models.AutoField(primary_key=True)
    type = models.CharField(max_length=250,null=False,choices=type_name)
    sigle = models.CharField(max_length=50,null=False,choices=sigle_name)
    date = models.DateField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if self.type and self.type in TYPE_MAPPING:
            self.sigle = TYPE_MAPPING[self.type]
        super().save(*args, **kwargs)
    def __str__(self):
        return self.type

    class Meta:
        db_table = 'eleve_note_type'

class Eleve_note(models.Model):
    id_note = models.AutoField(primary_key=True)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_cycle_actif = models.ForeignKey("Classe_cycle_actif",on_delete=models.PROTECT,null=False)
    id_classe_active = models.ForeignKey("Classe_active",on_delete=models.PROTECT,null=False)    
    id_session = models.ForeignKey('Session',on_delete=models.PROTECT,null=False)
    id_trimestre = models.ForeignKey('Annee_trimestre',on_delete=models.PROTECT,null=False)
    id_periode = models.ForeignKey('Annee_periode',on_delete=models.PROTECT,null=False)
    id_type_note = models.ForeignKey("Eleve_note_type",on_delete=models.PROTECT,null=False)
    id_cours = models.ForeignKey("Cours", on_delete=models.PROTECT, null=True, db_column="id_cours_id")  
    id_eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT,null=False) 
    date_saisie = models.DateField(auto_now_add=True)
    note = models.DecimalField(decimal_places=2, max_digits=5, null=True,blank=True)
    note_repechage = models.DecimalField(decimal_places=2, max_digits=5, null=True,blank=True)
    id_evaluation = models.ForeignKey('Evaluation',on_delete=models.PROTECT,null=False)

    
    def __str__(self):
        return f'{self.id_eleve.nom} {self.id_eleve.prenom}-{self.id_cours.cours}'
    class Meta:
        db_table = 'eleve_note'

class Eleve_conduite(models.Model):
    id_eleve_conduite = models.AutoField(primary_key=True)
    id_horaire = models.ForeignKey('Horaire',on_delete=models.PROTECT,null=False)
    id_eleve = models.ForeignKey('Eleve',on_delete=models.PROTECT,null=False)
    motif  = models.CharField(max_length=255,null=False)
    quote = models.PositiveIntegerField(default=0)
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey("Classe_cycle_actif",on_delete=models.PROTECT,null=False)
    id_classe = models.ForeignKey("Classe_active",on_delete=models.PROTECT,null=False)    
    id_session = models.ForeignKey('Session',on_delete=models.PROTECT,null=False)
    id_trimestre = models.ForeignKey('Annee_trimestre',on_delete=models.PROTECT,null=False)
    id_periode = models.ForeignKey('Annee_periode',on_delete=models.PROTECT,null=False)
    date_enregistrement = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f'{self.id_eleve.nom} {self.id_eleve.prenom}-{self.id_cours.cours}'
    class Meta:
        db_table = 'eleve_conduite'
    