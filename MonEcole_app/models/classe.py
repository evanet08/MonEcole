from django.db import models
from MonEcole_app.variables import groupes,cycles_list
# from MonEcole_app.models.eleves import Eleve

class Classe(models.Model):
    id_classe = models.AutoField(primary_key=True) 
    classe = models.CharField(max_length=50,null=False,unique=True)  
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = "classes"
        managed = False
        verbose_name = "Classe"
        # verbose_name_plural = "Classes"

    def __str__(self):
        return self.classe

class CycleManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
class Classe_cycle(models.Model):
    id_cycle = models.AutoField(primary_key=True) 
    cycle = models.CharField(max_length=200, null=False,unique=True,choices=cycles_list)  
    is_active = models.BooleanField(default=True)
    
     # Manager par défaut (retourne uniquement les campus actifs)
    objects = CycleManager()
    # Manager pour accéder à tous les campus (actifs et inactifs)
    all_objects = models.Manager()
    
    class Meta:
        db_table = "classe_cycle"
        managed = False
        verbose_name = "Cycle de Classe"
        # verbose_name_plural = "Cycles de Classe"
    def __str__(self):
        return self.cycle

class Classe_active(models.Model):
    id_classe_active = models.AutoField(primary_key=True) 
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)  
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)
    cycle_id = models.ForeignKey("Classe_cycle_actif",on_delete=models.PROTECT,null=False) 
    classe_id = models.ForeignKey("Classe",on_delete=models.PROTECT,null=False) 
    groupe = models.CharField(max_length=10,choices=groupes,null=True, blank=True)
    isTerminale = models.BooleanField(default=False) 
    is_active  = models.BooleanField(default= True)
    date_creation = models.DateField(auto_now_add=True)
    ordre = models.PositiveIntegerField(null=True,blank=True)
    
    class Meta:
        db_table = "classe_active" 
        verbose_name = "Classe Active"
        # verbose_name_plural = "Classes Actives"

    def __str__(self):
        return f"{self.classe_id}"

class Classe_cycle_actif(models.Model):
    id_cycle_actif = models.AutoField(primary_key=True) 
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)  
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False) 
    cycle_id = models.ForeignKey("Classe_cycle",on_delete=models.PROTECT,null=False) 
    role = models.CharField(max_length=255,null=True,blank=True) 
    is_active  = models.BooleanField(default= True)
    date_creation = models.DateField(auto_now_add=True)
    nbre_classe_par_cycle_actif = models.PositiveIntegerField(default=1,null=True,blank=True)
    ordre = models.PositiveIntegerField(null=True,blank=True)
    
    class Meta:
        db_table = "classe_cycle_actif"  
        verbose_name = "Cycle Actif"
        # verbose_name_plural = "Cycles Actifs"
        
    def __str__(self):
        return f"{self.cycle_id.cycle}"
  
class Classe_deliberation(models.Model):
    id_deliberation = models.AutoField(primary_key=True)  
    date_deliberation = models.DateField() 
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)  
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False) 
    id_cycle = models.ForeignKey("Classe_cycle_actif",on_delete=models.PROTECT,null=False) 
    id_classe = models.ForeignKey("Classe_active",on_delete=models.PROTECT,null=False) 
    id_session = models.ForeignKey("Session",on_delete=models.PROTECT,null=False) 
    showResults = models.BooleanField(default=False)  
    showsResultsEnOrdre = models.BooleanField(default=False)  
    date_creation = models.DateField(auto_now_add=True)
    

    class Meta:
        db_table = "classe_deliberation"
        verbose_name = "Délibération de classe"
        # verbose_name_plural = "Délibérations de classes"

    def __str__(self):
        return f"{self.id_deliberation}-{self.id_classe}-{self.id_annee}"

class Classe_section(models.Model):
    id_section = models.AutoField(primary_key=True)
    section = models.CharField(max_length=100,null=False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False)  
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey("Classe_cycle_actif",on_delete=models.PROTECT,null=False) 
    id_classe = models.ForeignKey("Classe_active",on_delete=models.PROTECT,null=False) 
    

    class Meta:
        db_table = "classe_section"
        verbose_name = "section classes"
        # verbose_name_plural = "Délibérations de classes"

    def __str__(self):
        return f"{self.section}"
    
class Classe_active_responsable(models.Model):
    id_classe_active_resp =models.AutoField(primary_key=True)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False) 
    id_campus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)  
    id_cycle = models.ForeignKey("Classe_cycle_actif",on_delete=models.PROTECT,null=False) 
    id_classe = models.ForeignKey("Classe_active",on_delete=models.PROTECT,null=False) 
    id_personnel = models.ForeignKey("Personnel",on_delete=models.PROTECT,null=False) 
    date_creation = models.DateField(auto_now_add=True)
    
    class Meta:
        db_table = "classe_active_responsable" 
        verbose_name = "Responsable de Classe"
        # verbose_name_plural = "Responsables de Classes Actives"
    def __str__(self):
        return f"Responsable {self.id_personnel} - Classe {self.id_classe} - Année {self.id_annee}"

