from django import forms
from MonEcole_app.models.models_import import Classe,Classe_cycle,Classe_cycle_actif,Classe_active,Classe_active_responsable


class ClasseForm(forms.ModelForm):
    class Meta:
        model = Classe
        fields = [
            'id_classe','classe'
        ]
        
class Classe_active_Form(forms.ModelForm):
    class Meta:
        model = Classe_active
        fields = [
            'etablissement_annee', 'classe_id', 'groupe'
        ]
            
        labels = {
            'etablissement_annee': 'Établissement-Année',
            'classe_id': 'Classe',
            'groupe': 'Groupe',
        }
        
class ClasseCycleForm(forms.ModelForm):
    class Meta:
        model = Classe_cycle
        fields = [
            'cycle'
        ]
        
        


class ClasseCycle_actifForm(forms.ModelForm):
    class Meta:
        model = Classe_cycle_actif
        fields = [
            'cycle'
        ]
        labels = {
            'cycle': 'Cycle',
        }

        
        

class ClasseActiveResponsableForm(forms.ModelForm):
    class Meta:
        model = Classe_active_responsable
        fields = ['id_annee', 'id_classe']
        labels = {
            'id_annee': 'Année scolaire',
            'id_classe': 'Classe',
        }
        widgets = {
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_classe': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['id_annee'].empty_label = '------'
        self.fields['id_classe'].empty_label = '------'
        
        
    