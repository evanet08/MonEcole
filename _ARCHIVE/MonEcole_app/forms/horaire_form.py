

from django import forms
from MonEcole_app.models import Horaire,Horaire_type



class HoraireTypeForm(forms.ModelForm):
     
    class Meta:
       model = Horaire_type
       fields = "__all__"
       
       
class HoraireForm(forms.ModelForm):
    
    class Meta:
       model = Horaire
       fields = "__all__"
       labels = {
            'id_campus': 'Campus',
            'id_annee': 'Année',
            'id_cycle': 'Cycle',
            'id_classe': 'Classe',
            'id_horaire_type': 'Type horaire',  
            'id_cours': 'Cours', 
            'debut': 'debut', 
            'fin': 'fin', 
            'jour': 'jour', 
        }
       widgets = {
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'jour': forms.TextInput(attrs={'class': 'form-control', 'style': 'display: none;'}),
            'id_cycle': forms.Select(attrs={'class': 'form-control', 'style': 'display: none;', 'disabled': True}),
            'id_classe': forms.Select(attrs={'class': 'form-control', 'style': 'display: none;', 'disabled': True}),
            'id_campus': forms.Select(attrs={'class': 'form-control','style': 'display: none;', 'disabled': True}),
            'id_horaire_type': forms.Select(attrs={'class': 'form-control','style': 'display: none;', 'disabled': True}),
        }
       
       
       
       
    
        
        
    