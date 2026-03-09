from django.db import models
from MonEcole_app.variables import etat_annee

# NOTE: Trimestre et Periode ont été migrés vers countryStructure
# Ils sont maintenant dans models/country_structure.py
# Les imports se font depuis là-bas via le __init__.py


class Annee(models.Model):
    """
    Année scolaire locale à l'établissement.
    NOTE: À terme, cette table sera remplacée par countryStructure.annees
    via EtablissementAnnee. Pour l'instant, on garde la compatibilité.
    """
    id_annee = models.AutoField(primary_key=True)
    debut = models.IntegerField(null=True, blank=True)  
    fin = models.IntegerField(null=True, blank=True)  
    annee = models.CharField(max_length=20, null=False) 
    etat_annee = models.CharField(max_length=50, choices=etat_annee, default='En attente') 
    date_ouverture = models.DateField()  
    date_cloture = models.DateField()  
    is_active = models.BooleanField(default=True)
    # Lien logique vers countryStructure.annees
    id_annee_structure = models.IntegerField(null=True, blank=True)
     
    class Meta:
        db_table = "annee"  
        managed = False
        verbose_name = "Année_scolaire"

    def __str__(self):
        return f"{self.annee}"


class Annee_periode(models.Model):
    """
    Configuration d'une période pour une année/campus/cycle/classe.
    FK vers Periode qui est maintenant dans countryStructure.
    """
    id_periode = models.AutoField(primary_key=True) 
    periode = models.ForeignKey("Periode", on_delete=models.PROTECT, null=False) 
    debut = models.DateField(null=True, blank=True) 
    fin = models.DateField(null=True, blank=True) 
    isOpen = models.BooleanField(default=True) 
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False) 
    id_campus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False) 
    id_cycle = models.ForeignKey("Classe_cycle_actif", on_delete=models.PROTECT, null=False) 
    id_classe = models.ForeignKey("Classe_active", on_delete=models.PROTECT, null=False) 
    id_trimestre_annee = models.ForeignKey('Annee_trimestre', on_delete=models.PROTECT, null=False)
    
    class Meta:
        db_table = "annee_periode"  
        managed = False
        verbose_name = "Période_AnnéeScolaire"

    def __str__(self):
        return f"{self.periode.periode} "
    
    
class Annee_trimestre(models.Model):
    """
    Configuration d'un trimestre pour une année/campus/cycle/classe.
    FK vers Trimestre qui est maintenant dans countryStructure.
    """
    id_trimestre = models.AutoField(primary_key=True)  
    trimestre = models.ForeignKey('Trimestre', on_delete=models.PROTECT, null=False)
    debut = models.DateField(null=True, blank=True) 
    fin = models.DateField(null=True, blank=True) 
    isOpen = models.BooleanField(default=True) 
    id_cycle = models.ForeignKey("Classe_cycle_actif", on_delete=models.PROTECT, null=False) 
    id_classe = models.ForeignKey("Classe_active", on_delete=models.PROTECT, null=False)  
    id_annee = models.ForeignKey("Annee", on_delete=models.PROTECT, null=False) 
    id_campus = models.ForeignKey("Campus", on_delete=models.PROTECT, null=False) 

    class Meta:
        db_table = "annee_trimestre" 
        managed = False
        verbose_name = "Trimestre_AnnéeScolaire"

    def __str__(self):
        return f"{self.trimestre.trimestre}"
