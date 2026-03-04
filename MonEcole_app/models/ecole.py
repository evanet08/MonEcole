
from django.db import models
# from MonEcole_app.models.eleves import Eleve
class Institution(models.Model):
    id_ecole = models.AutoField(primary_key=True)
    nom_ecole = models.CharField(max_length=250,null=False,unique=True)
    sigle = models.CharField(max_length=50,null=False)
    telephone = models.CharField(max_length=50,null=False,blank=True)
    email = models.EmailField(max_length=50,null=False,blank=True)
    domaine = models.CharField(max_length=50,null=False,blank=True)
    site = models.URLField(max_length=50,null=False,blank=True)
    logo_ecole = models.ImageField(upload_to='logos/ecole/', blank=True, null=True)  
    logo_ministere = models.ImageField(upload_to='logos/ministere/', blank=True, null=True)  
    siege = models.CharField(max_length=50,null=False,blank=True)
    fax = models.CharField(max_length=20,null=False,blank=True)
    representant = models.CharField(max_length=50,null=False,blank=True)
    b_postale = models.CharField(max_length=50,null=False,blank=True)
    emplacement = models.CharField(max_length=50,null=False,blank=True)

    def __str__(self):
        return self.nom_ecole

    class Meta:
        db_table = 'ecole'
        managed = False
