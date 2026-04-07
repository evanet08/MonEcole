from django.db import models
from MonEcole_app.models.annee import Annee
from MonEcole_app.models.campus import Campus
from MonEcole_app.models.mention import Mention
from MonEcole_app.models.country_structure import Session, Cycle
import os
from django.core.exceptions import ValidationError
from MonEcole_app.variables import type_deliberations

# NOTE: Session a été migré vers countryStructure.
# Il est maintenant importé depuis models/country_structure.py

    
class Deliberation_type(models.Model):
    id_deliberation_type = models.AutoField(primary_key=True)
    type = models.CharField(max_length=200, unique=True,choices=type_deliberations)
    class Meta:
        db_table = "deliberation_type"
        managed = False
        verbose_name = "deliberation_type"
        
    def __str__(self):
        return self.type
    
class Deliberation_annuelle_finalite(models.Model):
    id_finalite = models.AutoField(primary_key=True)
    finalite = models.CharField(max_length=200,null=False,unique=True) 
    sigle = models.CharField(max_length=50,null=True,blank=True)  
    droit_avancement = models.BooleanField(default=False)  
    class Meta:
        db_table = "deliberation_annuelle_finalites"  
        managed = False
        verbose_name = "Finalité_délibération"
    def __str__(self):
        return self.finalite  

class Deliberation_annuelle_condition(models.Model):
    id_decision = models.AutoField(primary_key=True)  
    id_annee = models.ForeignKey("Annee", on_delete=models.DO_NOTHING, null=False, db_constraint=False)
    id_campus = models.IntegerField(null=False, db_column='id_campus_id')
    id_cycle = models.ForeignKey(Cycle, on_delete=models.DO_NOTHING, null=False, db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.DO_NOTHING, null=False,
                                  db_column='id_classe_id', db_constraint=False)
    id_mention = models.ForeignKey(Mention, on_delete=models.DO_NOTHING, null=False, db_constraint=False)
    max_echecs_acceptable = models.IntegerField(null=True, blank=True) 
    seuil_profondeur_echec = models.IntegerField(null=True, blank=True) 
    sanction_disciplinaire = models.CharField(max_length=100, null=True, blank=True) 
    id_finalite = models.ForeignKey(Deliberation_annuelle_finalite, on_delete=models.DO_NOTHING, null=False, db_constraint=False)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "deliberation_annuelle_conditions" 
        managed = False
        verbose_name = "Condition_délibération annuelle"

    def __str__(self):
        return f"Condition {self.id_decision}"

class Deliberation_annuelle_resultat(models.Model):
    id_deliberation = models.AutoField(primary_key=True) 
    id_eleve = models.ForeignKey("Eleve",on_delete=models.PROTECT,null=False)  
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null=False, db_constraint=False) 
    idCampus = models.ForeignKey(Campus,on_delete=models.PROTECT,null=False) 
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_session = models.ForeignKey(Session,on_delete=models.PROTECT,null=False, db_constraint=False)   
    id_mention = models.ForeignKey(Mention,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_decision = models.ForeignKey(Deliberation_annuelle_condition,on_delete=models.PROTECT,null=False, db_constraint=False) 
    pourcentage = models.FloatField() 
    place = models.CharField(max_length=200,null=False) 
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = "deliberation_annuelle_resultats"  
        verbose_name = "Résultat de délibération annuelle"

    def __str__(self):
        return f" {self.id_eleve} - Session {self.id_session}"

class Deliberation_periodique_resultat(models.Model):
    id_deliberation = models.AutoField(primary_key=True)
    id_eleve = models.ForeignKey("Eleve",on_delete=models.PROTECT,null=False)  
    idCampus = models.ForeignKey(Campus,on_delete=models.PROTECT,null=False)
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_trimestre = models.ForeignKey("Annee_trimestre",on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_periode = models.ForeignKey("Annee_periode",on_delete=models.PROTECT,null=False, db_constraint=False) 
    pourcentage = models.FloatField() 
    place = models.CharField(max_length=200,null=False) 
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "deliberation_periodique_resultats" 
        verbose_name = "Résultat de délibération périodique"

    def __str__(self):
        return f"{self.id_eleve} - Session {self.id_deliberation}"

class Deliberation_examen_resultat(models.Model):
    id_deliberation = models.AutoField(primary_key=True)
    id_eleve = models.ForeignKey("Eleve",on_delete=models.PROTECT,null=False)  
    idCampus = models.ForeignKey(Campus,on_delete=models.PROTECT,null=False)
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_trimestre = models.ForeignKey("Annee_trimestre",on_delete=models.PROTECT,null=False, db_constraint=False) 
    pourcentage = models.FloatField() 
    place = models.CharField(max_length=200,null=False) 
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "deliberation_examen_resultats" 
        verbose_name = "Résultat de délibération des examen"

    def __str__(self):
        return f"{self.id_eleve} - Session {self.id_deliberation}"





class Deliberation_trimistrielle_resultat(models.Model):
    id_deliberation = models.AutoField(primary_key=True)
    id_eleve = models.ForeignKey("Eleve",on_delete=models.PROTECT,null=False)  
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null=False, db_constraint=False)  
    idCampus = models.ForeignKey(Campus,on_delete=models.PROTECT,null=False)
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_trimestre = models.ForeignKey("Annee_trimestre",on_delete=models.PROTECT,null=False, db_constraint=False)  
    pourcentage = models.FloatField() 
    place = models.CharField(max_length=200,null=False) 
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = "deliberation_trimistrielle_resultats" 
        verbose_name = "Résultat de délibération trimestrielle"

    def __str__(self):
        return f"{self.id_eleve} - Session {self.id_deliberation}"



class Evaluation(models.Model):
    id_evaluation = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200,null=False)
    id_type_eval = models.IntegerField(null=True, blank=True)
    ponderer_eval = models.PositiveIntegerField(default=0)
    date_eval  = models.DateField()
    date_soumission = models.DateField(null=True,blank=True)
    idCampus = models.ForeignKey("Campus",on_delete=models.PROTECT,null=False)
    id_annee = models.ForeignKey("Annee",on_delete=models.PROTECT,null=False, db_constraint=False)
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null=True, blank=True,
                                 db_column='id_cycle_id', db_constraint=False)
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_type_note = models.ForeignKey("Eleve_note_type",on_delete=models.PROTECT,null=True, blank=True,
                                     db_constraint=False)
    id_cours_classe = models.ForeignKey("Cours_par_classe", on_delete=models.PROTECT,null=False)
    id_session = models.ForeignKey("Session",on_delete=models.PROTECT,null=True, blank=True,
                                   db_constraint=False)
    id_repartition_instance = models.ForeignKey(
        'RepartitionInstance', on_delete=models.PROTECT, null=True, blank=True,
        db_column='id_repartition_instance', db_constraint=False)
    contenu_evaluation = models.FileField(upload_to='evaluations/')
    document_url = models.CharField(max_length=500, null=True, blank=True)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    def __str__(self):
        return self.title

    class Meta:
        db_table = 'evaluation'
 
class Deliberation_repechage_resultat(models.Model):
    id_repechage = models.AutoField(primary_key=True) 
    id_eleve = models.ForeignKey("Eleve",on_delete=models.PROTECT,null=False)  
    id_annee = models.ForeignKey(Annee,on_delete=models.PROTECT,null=False, db_constraint=False) 
    idCampus = models.ForeignKey(Campus,on_delete=models.PROTECT,null=False) 
    id_cycle = models.ForeignKey(Cycle,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_classe = models.ForeignKey('Classe', on_delete=models.PROTECT, null=False,
                                  db_column='classe_id', db_constraint=False)
    groupe = models.CharField(max_length=5, null=True, blank=True)
    section = models.ForeignKey('MonEcole_app.Section', on_delete=models.SET_NULL,
                                null=True, blank=True, db_column='section_id',
                                db_constraint=False)
    id_session = models.ForeignKey(Session,on_delete=models.PROTECT,null=False, db_constraint=False)   
    id_finalite = models.ForeignKey(Deliberation_annuelle_finalite,on_delete=models.PROTECT,null=False, db_constraint=False) 
    id_cours_classe = models.ForeignKey("Cours_par_classe",on_delete=models.PROTECT,null=False, db_constraint=False)
    valid_repechage = models.BooleanField(default=False)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "deliberation_repechage_resultats"  
        verbose_name = "Résultat de délibération repechage"

    def __str__(self):
        return f"{self.id_eleve}"