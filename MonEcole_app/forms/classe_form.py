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
            'id_campus','id_annee',"cycle_id",'classe_id','groupe'
        ]
            
        labels = {
            'id_campus': 'Campus',
            'id_annee' : 'Année',
            'cycle_id' : 'Cycle',
            'classe_id': 'Classe',
            'groupe': 'groupe',
        }
        # widgets = {
            
        #     'groupe': forms.Select(attrs={'class': 'form-control', 'style': 'display: none;'}),
        #  }
        
class ClasseCycleForm(forms.ModelForm):
    class Meta:
        model = Classe_cycle
        fields = [
            'cycle'
        ]
        
        


class ClasseCycle_actifForm(forms.ModelForm):
    nbre_classe_par_cycle_actif = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Nombre de classe/cycle",
        widget=forms.NumberInput(attrs={'placeholder': '1 ou plus'})
    )

    class Meta:
        model = Classe_cycle_actif
        fields = [
            'id_campus', 'id_annee', 'cycle_id', 'nbre_classe_par_cycle_actif'
        ]
        labels = {
            'id_campus': 'Campus',
            'id_annee': 'Année',
            'cycle_id': 'Cycle',
            'nbre_classe_par_cycle_actif': 'Nombre de classe/cycle'
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
        
        
    