
from django.db import models
from django.contrib.auth.models import User
from MonEcole_app.models import Campus,Classe_active,Classe_cycle_actif,Annee,Eleve,Personnel
from MonEcole_app.variables import choices_etat_books

class Armoire(models.Model):
    nom = models.CharField(max_length=100, unique=True) 
    description = models.TextField(blank=True, null=True) 
    localisation = models.CharField(max_length=200, null=True,blank=True) 

    def __str__(self):
        return self.nom

    class Meta:
        db_table = "Biblio_armoire"
        verbose_name = "Biblio_armoire"
        verbose_name_plural = "Armoires"

class Compartiment(models.Model):
    armoire = models.ForeignKey(Armoire, on_delete=models.PROTECT,null=False) 
    numero = models.CharField(max_length=50)  
    capacite = models.PositiveIntegerField(default=10)  

    def __str__(self):
        return f"{self.armoire.nom} - {self.numero}"

    class Meta:
        db_table = "Biblio_compartiment"
        verbose_name = "Biblio_compartiment"
        verbose_name_plural = "Compartiments"
        unique_together = ('armoire', 'numero') 


class Categorie(models.Model):
    nom = models.CharField(max_length=100, unique=True)  
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nom

    class Meta:
        db_table = "Biblio_categorie"
        verbose_name = "categorie"
        verbose_name_plural = "Catégories"


class Livre(models.Model):
    titre = models.CharField(max_length=200)  
    auteur = models.CharField(max_length=100)  
    isbn = models.CharField(max_length=13, unique=True, blank=True, null=True)  
    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, null=False)  
    compartiment = models.ForeignKey(Compartiment, on_delete=models.PROTECT, null=False)  
    date_ajout = models.DateTimeField(auto_now_add=True)  
    disponible = models.BooleanField(default=True) 
    etat = models.CharField(max_length=50, choices=choices_etat_books,default='BON')
    nombre_exemplaires = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return self.titre

    class Meta:
        db_table = "Biblio_livre"
        verbose_name = "Biblio_livre"
        verbose_name_plural = "Livres"


class Exemplaire(models.Model):
    livre = models.ForeignKey(Livre, on_delete=models.CASCADE)
    numero_inventaire = models.CharField(max_length=50, unique=True) 
    etat = models.CharField(max_length=50, choices=choices_etat_books,default='BON')
    disponible = models.BooleanField(default=True)

class Emprunt(models.Model):
    id_livre = models.ForeignKey(Livre, on_delete=models.PROTECT, related_name="emprunts")  
    id_personnel = models.ForeignKey(Personnel, on_delete=models.PROTECT,null=True,blank=True) 
    id_eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT,null=True,blank=True) 
    date_retour_prevue = models.DateField()  
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null= False)
    id_campus = models.ForeignKey(Campus,on_delete=models.PROTECT,null= False)
    id_cycle_actif = models.ForeignKey(Classe_cycle_actif,on_delete=models.PROTECT,null=True,blank=True)
    id_classe_active = models.ForeignKey(Classe_active,on_delete=models.PROTECT,null=True,blank=True)
    rendu = models.BooleanField(default=False) 
    date_retour_effective = models.DateField(blank=True, null=True)  
    date_emprunt = models.DateField(auto_now_add=True)  
    
    

    def __str__(self):
        return f"{self.id_livre.titre} emprunté par {self.id_personnel.user.first_name} {self.id_personnel.user.last_name}"

    class Meta:
        db_table = "Biblio_emprunt"
        verbose_name = "Biblio_emprunt"
        verbose_name_plural = "Emprunts"
    
class Role(models.Model):
    nom = models.CharField(max_length=50, unique=True)  
    peut_emprunter = models.BooleanField(default=True)  
    limite_emprunts = models.PositiveIntegerField(default=3) 
    
    class Meta:
        db_table = "Biblio_empruteur_role"

class ProfilUtilisateur(models.Model):
    profile = models.CharField(max_length=250,null=False)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, null=True)

    def __str__(self):
        return f"{self.profile}"

    class Meta:
        db_table = "Biblio_empruteur_profile"
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"

        
