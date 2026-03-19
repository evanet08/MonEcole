from django import forms
from MonEcole_app.models.models_import import Annee, Annee_periode, Annee_trimestre, RepartitionInstance


class AnneeForm(forms.ModelForm):
    class Meta:
        model = Annee
        fields = ['annee', 'date_ouverture', 'date_cloture']
        widgets = {
            'date_ouverture': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_cloture': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class RepartitionInstanceForm(forms.ModelForm):
    """Remplace TrimesterForm et PeriodForm — gère les instances de répartition."""
    class Meta:
        model = RepartitionInstance
        fields = ['nom', 'code']

class AnneePeriodeForm(forms.ModelForm):
    class Meta:
        model = Annee_periode
        fields = ['id_campus', 'id_annee', 'id_cycle', 'id_classe', 'id_trimestre_annee']
        labels = {
            'id_campus': 'Campus',
            'id_annee': 'Annee',
            'id_cycle': 'Cycle',
            'id_classe': 'Classe',
            'id_trimestre_annee': 'Trimestre'
        }
        widgets = {
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle': forms.Select(attrs={'class': 'form-control', 'disabled': True}),
            'id_classe': forms.Select(attrs={'class': 'form-control', 'disabled': True}),
            'id_trimestre_annee': forms.Select(attrs={'class': 'form-control', 'style': 'display: none;', 'disabled': True}),
        }

class AnneeTrimestreForm(forms.ModelForm):
    class Meta:
        model = Annee_trimestre
        fields = ['id_campus', 'id_annee', 'id_cycle', 'id_classe']
        labels = {
            'id_campus': 'Campus',
            'id_annee': 'Annee',
            'id_cycle': 'Cycle',
            'id_classe': 'Classe',
        }
        widgets = {
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle': forms.Select(attrs={'class': 'form-control', 'style': 'display: none;', 'disabled': True}),
            'id_classe': forms.Select(attrs={'class': 'form-control', 'style': 'display: none;', 'disabled': True}),
        }

# Alias compat pour les imports existants
TrimesterForm = RepartitionInstanceForm
PeriodForm = RepartitionInstanceForm
