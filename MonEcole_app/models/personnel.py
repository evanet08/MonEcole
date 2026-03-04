from django.db import models
from django.contrib.auth.models import User,UserManager
from MonEcole_app.variables import *
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone

class Personnel_categorie(models.Model):
    id_personnel_category = models.AutoField(primary_key=True)
    categorie = models.CharField(max_length=50, unique=True)
    sigle = models.CharField(max_length=10, null=True)
    
    class Meta:
        db_table = "personnel_categorie" 
        verbose_name = "Categorie du personnel"
    
    def __str__(self):
        return self.categorie

class Diplome(models.Model):
    id_diplome = models.AutoField(primary_key=True)
    diplome = models.CharField(max_length=50, unique=True)
    sigle = models.CharField(max_length=10, unique=True)
    
    class Meta:
        db_table = "diplome" 
        verbose_name = "diplome"
    
    def __str__(self):
        return self.diplome

class Specialite(models.Model):
    id_specialite = models.AutoField(primary_key=True)
    specialite = models.CharField(max_length=200, null=False)
    sigle = models.CharField(max_length=10,null=False)
    
    class Meta:
        db_table = "specialite" 
        verbose_name = "specialite"
    
    def __str__(self):
        return self.specialite

class Vacation(models.Model):
    id_vacation = models.AutoField(primary_key=True)
    vacation = models.CharField(max_length=20, null=False)
    sigle = models.CharField(max_length=10, )
    
    class Meta:
        db_table = "vacation"  
        verbose_name = "vacation"
    
    
    def __str__(self):
        return self.vacation

class PersonnelType(models.Model):
    id_type_personnel = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, unique=True)
    sigle = models.CharField(max_length=50, unique=True)
    class Meta:
        db_table = "personnel_type"  
        verbose_name = "Type du personnel"
    def __str__(self):
        return self.type

class Personnel(models.Model):
    id_personnel = models.AutoField(primary_key=True)
    user = models.OneToOneField(User,on_delete=models.PROTECT,null=False)
    codeAnnee = models.CharField(max_length=200,null=True,blank=True)
    matricule = models.CharField(max_length=20, unique=True,null=False)
    date_naissance = models.DateField(blank=True, null=True)
    genre = models.CharField(max_length=22,null=False,choices=sexe_choices,default='M')
    etat_civil = models.CharField(max_length=200,choices=etat_civil_choices,default='Célibataire')
    type_identite = models.CharField(max_length=200,null=False,blank=True)
    numero_identite = models.CharField(max_length=20, null=True,blank=True)
    telephone = PhoneNumberField(region='BI', null=True, blank=True)
    region = models.CharField(max_length=200,null=True,blank=True)
    pays = models.CharField(max_length=200,null=True,blank=True)
    province = models.CharField(max_length=200,null=False,blank=True)
    commune = models.CharField(max_length=200,null=False,blank=True)
    code_secret = models.TextField(max_length=150,blank=True,null=True)
    zone = models.CharField(max_length=200,null=False,blank=True)
    addresse = models.CharField(max_length=200,null=False,blank=True)
    imageUrl = models.ImageField(upload_to='logos/personnel/', blank=True, null=True)
    id_diplome = models.ForeignKey(Diplome, on_delete=models.PROTECT)
    id_specialite = models.ForeignKey(Specialite, on_delete=models.PROTECT)
    id_categorie = models.ForeignKey(Personnel_categorie, on_delete=models.PROTECT)
    id_vacation = models.ForeignKey(Vacation, on_delete=models.PROTECT)
    id_personnel_type = models.ForeignKey(PersonnelType, on_delete=models.PROTECT)
    isMaitresse = models.BooleanField(default=False)
    isInstiteur = models.BooleanField(default=False)
    isDAF = models.BooleanField(default=False)
    isDirecteur = models.BooleanField(default=False)
    isUser = models.BooleanField(default=False)
    en_fonction = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    date_creation = models.DateField(auto_now_add=True)
   
    class Meta:
        db_table = "personnel"  
        verbose_name = "personnel"
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}_({self.matricule})"

class Prestation(models.Model):
    id_prestation = models.AutoField(primary_key=True)
    heureD = models.CharField(max_length=20)
    heureF = models.CharField(max_length=20)
    id_horaire = models.IntegerField()
    id_etudiant = models.IntegerField()
    id_personnel = models.ForeignKey(Personnel, on_delete=models.PROTECT,null=False)
    date_creation = models.DateField(auto_now_add=True)
    
    
    class Meta:
        db_table = "prestation"  
        verbose_name = "prestation"
    
    
    
    def __str__(self):
        return f"{self.heureD} to {self.heureF}"
