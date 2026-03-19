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
        fields = ['etablissement_annee', 'repartition', 'id_trimestre_annee']
        labels = {
            'etablissement_annee': 'Établissement-Année',
            'repartition': 'Période',
            'id_trimestre_annee': 'Trimestre parent',
        }
        widgets = {
            'etablissement_annee': forms.Select(attrs={'class': 'form-control'}),
            'repartition': forms.Select(attrs={'class': 'form-control'}),
            'id_trimestre_annee': forms.Select(attrs={'class': 'form-control'}),
        }

class AnneeTrimestreForm(forms.ModelForm):
    class Meta:
        model = Annee_trimestre
        fields = ['etablissement_annee', 'repartition']
        labels = {
            'etablissement_annee': 'Établissement-Année',
            'repartition': 'Trimestre',
        }
        widgets = {
            'etablissement_annee': forms.Select(attrs={'class': 'form-control'}),
            'repartition': forms.Select(attrs={'class': 'form-control'}),
        }

# Alias compat pour les imports existants
TrimesterForm = RepartitionInstanceForm
PeriodForm = RepartitionInstanceForm
