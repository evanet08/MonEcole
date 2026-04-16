
from django.db import models


class CampusManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class Campus(models.Model):
    """
    Campus = site physique d'un établissement.
    Reste dans db_monecole (propre à chaque école).
    idCampus = PK auto_increment (identifiant global unique)
    id_campus = numéro séquentiel par établissement (1, 2, 3...)
    id_etablissement = FK logique vers countryStructure.etablissements
    """
    idCampus = models.AutoField(primary_key=True)
    id_campus = models.IntegerField(default=1, verbose_name="N° campus par établissement")
    campus = models.CharField(max_length=50, null=False, unique=True)  
    adresse = models.CharField(max_length=255, null=False) 
    localisation = models.CharField(max_length=255, null=True, blank=True) 
    is_active = models.BooleanField(default=True)
    # Lien logique vers countryStructure.etablissements
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(default=2)
    
    # Manager par défaut (retourne uniquement les campus actifs)
    objects = CampusManager()
    # Manager pour accéder à tous les campus (actifs et inactifs)
    all_objects = models.Manager()

    class Meta:
        db_table = "campus" 
        verbose_name = "Campus"

    def save(self, *args, **kwargs):
        # Auto-increment id_campus par établissement lors de la création
        if not self.pk and self.id_etablissement is not None:
            max_id = Campus.all_objects.filter(
                id_etablissement=self.id_etablissement
            ).aggregate(models.Max('id_campus'))['id_campus__max'] or 0
            self.id_campus = max_id + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.campus
