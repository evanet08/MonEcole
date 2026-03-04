
from django import forms
from MonEcole_app.models.evaluations.note import Evaluation 
from MonEcole_app.models.models_import import *

class EvaluationForm(forms.ModelForm):
    
    class Meta:
        model = Evaluation
        fields = ['id_annee','title','id_campus','id_cycle_actif','id_classe_active','id_cours_classe','ponderer_eval','date_eval',
                  'date_soumission','date_eval','id_type_note','contenu_evaluation','id_session','id_trimestre','id_periode']
        labels = {
            'id_annee': 'Année',
            'id_campus': 'Campus',
            'title': 'Title de l\'évaluation',
            'id_cycle_actif': 'Cycle',
            'id_classe_active': 'Classe',
            'ponderer_eval': 'pondérer sur ',
            'date_eval': "Date d'évaluation",
            'id_session': 'Session',
            'id_trimestre': 'Trimestre',
            'id_periode': 'Période',
            'id_cours_classe': 'Cours',
            'date_soumission': 'Date de soumission',
            'contenu_evaluation': 'Contenu',
            'id_type_note': 'Type de note',  
        }
        widgets = {
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle_actif': forms.Select(attrs={'class': 'form-control'}),
            'id_classe_active': forms.Select(attrs={'class': 'form-control'}),
            'ponderer_eval': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_eval': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),  
            'id_session': forms.Select(attrs={'class': 'form-control'}),
            'id_trimestre': forms.Select(attrs={'class': 'form-control'}),
            'id_periode': forms.Select(attrs={'class': 'form-control'}),
            'id_cours_classe': forms.Select(attrs={'class': 'form-control'}),
            'date_soumission': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}), 
            'contenu_evaluation': forms.FileInput(attrs={'class': 'form-control', 'id': 'id_contenu_evaluation'}),
            'id_type_note': forms.Select(attrs={'class': 'form-control'}),
        }
    def clean_contenu_evaluation(self):
        contenu = self.cleaned_data.get('contenu_evaluation')
        if not contenu:
            raise forms.ValidationError('Ce champ est requis.')
        if contenu.size > 5 * 1024 * 1024:  
            raise forms.ValidationError('Le fichier est trop volumineux (max 5MB).')
        return contenu

class Eleve_NoteForm(forms.ModelForm):
    class Meta:
        model = Eleve_note
        fields = ['id_annee','id_campus','id_cycle_actif','id_classe_active','id_cours',
                  'id_session','id_trimestre','id_periode','id_type_note','id_evaluation','id_eleve']
        labels = {
            'id_annee': 'Année',
            'id_campus': 'Campus',
            'id_cycle_actif': 'Cycle',
            'id_classe_active': 'Classe',
            'id_cours': 'Cours',
            'id_session': 'Session',
            'id_trimestre': 'Trimestre',
            'id_periode': 'Période',
            'id_type_note': 'Type de note', 
            'id_evaluation': 'Evaluation trouvée',
            'id_eleve': 'choisir un élève',
        }
        widgets = {
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle_actif': forms.Select(attrs={'class': 'form-control'}),
            'id_classe_active': forms.Select(attrs={'class': 'form-control'}),
            'id_session': forms.Select(attrs={'class': 'form-control'}),
            'id_trimestre': forms.Select(attrs={'class': 'form-control'}),
            'id_periode': forms.Select(attrs={'class': 'form-control'}),
            'id_cours': forms.Select(attrs={'class': 'form-control'}),
            'id_type_note': forms.Select(attrs={'class': 'form-control'}),
            'id_evaluation': forms.Select(attrs={'class': 'form-control'}),
            'id_eleve': forms.Select(attrs={'class': 'form-control'}),
        }        

class Note_type_Form(forms.ModelForm):
    class Meta:
        model = Eleve_note_type
        fields = "__all__"
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control', 'id': 'type_select'}),
            'sigle': forms.Select(attrs={'class': 'form-control', 'id': 'sigle_select'}),
        }
        labels = {
            'type': 'Type de notes',
          
        }
        
class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = "__all__"
        widgets = {
            'session':forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'id_session': 'session',
          
        }
        
class MentionForm(forms.ModelForm):
    class Meta:
        model = Mention
        fields = "__all__"
        widgets = {
            'mention': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'abbreviation': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'min': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': True}),
            'max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'required': True}),
        }

        labels = {
            'id_mention': 'Mention',
            'abbreviation':'abbreviation',
            'min':'Minimum',
            'max':'Maximum',
            
          
        }
    def clean(self):
        cleaned_data = super().clean()
        min_val = cleaned_data.get('min')
        max_val = cleaned_data.get('max')
        if min_val is not None and max_val is not None and min_val >= max_val:
            raise forms.ValidationError("La valeur minimale doit être inférieure à la valeur maximale.")
        return cleaned_data
    
class DeliberationTypeForm(forms.ModelForm):
    class Meta:
        model = Deliberation_type
        fields = "__all__"
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'type': 'Type de Délibération',
        }

class DeliberationFinaliteForm(forms.ModelForm):
    class Meta:
        model = Deliberation_annuelle_finalite
        fields = ['finalite','sigle', 'droit_avancement']
        
class DeliberationConditionForm(forms.ModelForm):
    class Meta:
        model = Deliberation_annuelle_condition
        fields = ['id_annee','id_campus','id_cycle','id_classe','id_mention',
                  'max_echecs_acceptable'
                  ,'seuil_profondeur_echec','sanction_disciplinaire','id_finalite']
        widgets = {
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle': forms.Select(attrs={'class': 'form-control'}),
            'id_classe': forms.Select(attrs={'class': 'form-control'}),
            'id_mention': forms.Select(attrs={'class': 'form-control'}),
            'max_echecs_acceptable': forms.NumberInput(attrs={'class': 'form-control', 'step': '0', 'required': True}),
            'seuil_profondeur_echec': forms.NumberInput(attrs={'class': 'form-control', 'step': '0', 'required': True}),
            'sanction_disciplinaire': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'id_finalite': forms.Select(attrs={'class': 'form-control'}),
            
        }
        labels = {
            'id_annee': 'Année scolaire',
            'id_campus': 'Campus',
            'id_cycle': 'Niveau',
            'id_classe': 'Classe',
            'id_mention': 'Mention',
            'max_echecs_acceptable': 'Echec acceptable',
            'seuil_profondeur_echec': '% Echec profondeur',
            'sanction_disciplinaire': 'commentaire displinaire',
            'id_finalite': 'Finalité',
        
          
        }
  
class DeliberationAnnuelleForm(forms.ModelForm):
    class Meta:
        model = Deliberation_annuelle_resultat
        fields = ['id_annee','id_campus','id_cycle','id_classe','id_session']
        widgets = {
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle': forms.Select(attrs={'class': 'form-control'}),
            'id_classe': forms.Select(attrs={'class': 'form-control'}),
            'id_session': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'id_annee': 'Année scolaire',
            'id_campus': 'Campus',
            'id_cycle': 'Niveau',
            'id_classe': 'Classe',
            'id_session': 'Session',
        }
             
class DeliberationTrimestreForm(forms.ModelForm):
    class Meta:
        model = Deliberation_trimistrielle_resultat
        fields = ['id_annee','id_campus','id_cycle','id_classe','id_trimestre']
        widgets = {
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle': forms.Select(attrs={'class': 'form-control'}),
            'id_classe': forms.Select(attrs={'class': 'form-control'}),
            'id_trimestre': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'id_annee': 'Année scolaire',
            'id_campus': 'Campus',
            'id_cycle': 'Niveau',
            'id_classe': 'Classe',
            'id_trimestre': 'Trimestre',
        }
   
   
        