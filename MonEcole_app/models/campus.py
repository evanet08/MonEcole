
from django.db import models


class CampusManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Campus(models.Model):
    """
    Campus = site physique d'un établissement.
    Reste dans db_monecole (propre à chaque école).
    id_etablissement = FK logique vers countryStructure.etablissements
    """
    id_campus = models.AutoField(primary_key=True) 
    campus = models.CharField(max_length=50, null=False, unique=True)  
    adresse = models.CharField(max_length=255, null=False) 
    localisation = models.CharField(max_length=255, null=True, blank=True) 
    is_active = models.BooleanField(default=True)
    # Lien logique vers countryStructure.etablissements
    id_etablissement = models.IntegerField(null=True, blank=True)
    
    # Manager par défaut (retourne uniquement les campus actifs)
    objects = CampusManager()
    # Manager pour accéder à tous les campus (actifs et inactifs)
    all_objects = models.Manager()

    class Meta:
        db_table = "campus" 
        verbose_name = "Campus"

    def __str__(self):
        return self.campus