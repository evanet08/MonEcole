from django.db import models

class Cours(models.Model):
    id_cours = models.AutoField(primary_key=True)  
    cours = models.CharField(max_length=150,null=False)
    code_cours = models.CharField(max_length=15, null=True, blank=True)  
    domaine = models.CharField(max_length=255,null=True,blank=True)  
    date_creation = models.DateField(auto_now_add=True)
    
    class Meta:
        db_table = "cours"
        managed = False
        verbose_name = "Cours"
        verbose_name_plural = "Cours"
        
    def __str__(self):
        return self.cours
    
    
    
class Cours_par_cycle(models.Model):
    id_cours_cycle= models.AutoField(primary_key=True) 
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)  
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)
    cours_id= models.ForeignKey("Cours", on_delete=models.PROTECT, null=False)
    cycle_id = models.ForeignKey("Classe_cycle_actif", on_delete=models.PROTECT, null=False)
    date_creation = models.DateField(auto_now_add=True)
    
    class Meta:
        db_table = "cours_par_cycle"  
        verbose_name = "Cours_par_cycle"
        unique_together = ('cours_id', 'cycle_id', 'id_annee') 

class Cours_par_classe(models.Model):
    id_cours_classe= models.AutoField(primary_key=True)  
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)  
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey("Classe_cycle_actif",on_delete=models.PROTECT,null=False) 
    id_classe = models.ForeignKey("Classe_active",on_delete=models.PROTECT,null=False) 
    id_cours= models.ForeignKey("Cours", on_delete=models.PROTECT, null=False)
    ponderation = models.IntegerField(null=True,blank=True) 
    CM = models.IntegerField(null=True, blank=True) 
    TD = models.IntegerField( null=True, blank=True)  
    TP = models.IntegerField(null=True, blank=True)  
    TPE = models.IntegerField(null=True, blank=True) 
    compte_au_nombre_echec = models.BooleanField(default=False, null=True, blank=True)
    total_considerable_trimestre = models.BooleanField(default=False, null=True, blank=True)
    est_considerer_echec_lorsque_pourcentage_est = models.IntegerField(null=True, blank=True)
    credits = models.IntegerField(null=True, blank=True)
    is_obligatory = models.BooleanField(default=False)
    heure_semaine = models.IntegerField(null=True, blank=True)
    ordre_cours = models.IntegerField(null=True, blank=True)
    is_second_semester = models.BooleanField(default=False)
    date_creation = models.DateField(auto_now_add=True)
    
    
    class Meta:
        db_table = "cours_par_classe"  
        verbose_name = "Cours_par_classe"
        # verbose_name_plural = "Cours_parAnnee"
        
    def __str__(self):
        return f"{self.id_cours.cours}-{self.id_classe} -{self.id_annee}"

class Attribution_type(models.Model):
    id_attribution_type = models.AutoField(primary_key=True) 
    attribution_type = models.CharField(max_length=250,null=False) 
    date_creation = models.DateField(auto_now_add=True)
    
    class Meta:
        db_table = "attribution_type"
        verbose_name = "Attribution de cours"
        
    def __str__(self):
        return self.attribution_type

class Attribution_cours(models.Model):
    id_attribution = models.AutoField(primary_key=True) 
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)  
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey("Classe_cycle_actif",on_delete=models.PROTECT,null=False) 
    id_classe = models.ForeignKey("Classe_active",on_delete=models.PROTECT,null=False) 
    attribution_type = models.ForeignKey("Attribution_type",on_delete=models.PROTECT,null=False)  
    id_cours = models.ForeignKey("Cours_par_classe",on_delete=models.PROTECT,null=False)  
    id_personnel = models.ForeignKey("Personnel",on_delete=models.PROTECT,null=False)  
    date_attribution = models.DateField(auto_now_add=True)
    
    class Meta:
        db_table = "attribution_cours"  
        verbose_name = "Attribution de cours"
        # verbose_name_plural = "Attributions de cours"

    def __str__(self):
        return f"{self.id_attribution} -{self.id_cours}"
