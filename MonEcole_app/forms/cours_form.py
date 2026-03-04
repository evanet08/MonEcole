from django import forms
from MonEcole_app.models.enseignmnts.matiere import *
from MonEcole_app.models.models_import import *


class Cours_F(forms.ModelForm):
    class Meta:
        model = Cours
        fields = [
             'cours', 'code_cours','domaine'
        ]
        labels = {
    
            "domaine": "Domaine/Groupe",
            
        }
        
class Cours_cyleForm(forms.ModelForm):
    class Meta:
        model = Cours_par_cycle
        fields = ['id_campus',"id_annee",'cycle_id','cours_id']
        labels = {
    
            "id_annee": "Année",
            "id_campus": "Campus",
            "cycle_id": "Cycle",
            "cours_id": "Cours",
        }


class CoursForm(forms.ModelForm):
    class Meta:
        model = Cours_par_classe
        fields = [
            'id_campus', 'id_annee', 'id_cycle', 'id_classe', 'id_cours', 'ponderation', 'TD', 'TP', 'TPE'
        ]
        labels = {
            'id_campus': 'Campus',
            'id_annee': 'Année',
            'id_cycle': 'Cycle',
            'id_classe': 'Classe',
            'id_cours': 'Cours',  
            'ponderation': 'Pondération', 
            'CM': 'CM',
            'TD': 'TD',
            'TP': 'TP',
            'TPE': 'TPE',
        }
        
        widgets = {
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle': forms.Select(attrs={'class': 'form-control', 'style': 'display: none;', 'disabled': True}),
            'id_classe': forms.Select(attrs={'class': 'form-control', 'style': 'display: none;', 'disabled': True}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_cours': forms.NumberInput(attrs={'class': 'form-control', 'style': 'display: none;', 'placeholder': 'Cours'}),
            # 'code_cours': forms.TextInput(attrs={'class': 'form-control', 'style': 'display: none;','placeholder': 'Code du cours'}),
            'ponderation': forms.NumberInput(attrs={'class': 'form-control', 'style': 'display: none;', 'placeholder': 'Pondération'}),
            'CM': forms.NumberInput(attrs={'class': 'form-control', 'style': 'display: none;', 'placeholder': 'CM'}),
            'TD': forms.NumberInput(attrs={'class': 'form-control', 'style': 'display: none;', 'placeholder': 'TD'}),
            'TP': forms.NumberInput(attrs={'class': 'form-control','style': 'display: none;', 'placeholder': 'TP'}),
            'TPE': forms.NumberInput(attrs={'class': 'form-control', 'style': 'display: none;', 'placeholder': 'TPE'}),
        }
       

class AttributionType_coursF(forms.ModelForm):
    
    class Meta:
        model = Attribution_type
        fields = [
            'attribution_type'
        ]
        
        
class Attribution_coursForm(forms.ModelForm):
    class Meta:
        model = Attribution_cours
        fields = ['id_campus','id_cours', 'id_annee', 'id_cycle','id_classe','id_personnel', 'attribution_type']
        labels ={
            'id_campus':'Campus',
            'id_annee':'Annee',
            'id_classe':'Classe'
        }
        widgets = {
            'id_campus': forms.Select(attrs={'class': 'form-select'}),
            'id_annee': forms.Select(attrs={'class': 'form-select'}),
            'id_cycle': forms.Select(attrs={'class': 'form-select'}),
            'id_classe': forms.Select(attrs={'class': 'form-select'}),
            'id_personnel': forms.Select(attrs={'class': 'form-select'}),
            'attribution_type': forms.Select(attrs={'class': 'form-select'}),
            
        }

    # Définir 'id_personnel' ici en dehors de la section Meta avec le queryset filtré
    id_personnel = forms.ModelChoiceField(
        queryset=Personnel.objects.filter(isUser=True, en_fonction=True, is_verified=True),  
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )