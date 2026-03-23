from django import forms
from ..models.country_structure import Pays, StructurePedagogique, StructureAdministrative


class PaysForm(forms.ModelForm):
    """Formulaire pour créer/modifier un pays."""
    
    class Meta:
        model = Pays
        fields = ['nom', 'sigle', 'nLevelsStructuraux', 'nLevelsAdministratifs']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du pays',
                'readonly': True
            }),
            'sigle': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code',
                'readonly': True,
                'maxlength': 5
            }),
            'nLevelsStructuraux': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de niveaux',
                'min': 0,
                'max': 10
            }),
            'nLevelsAdministratifs': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de niveaux',
                'min': 0,
                'max': 10
            }),
        }
        labels = {
            'nom': 'Nom du pays',
            'sigle': 'Code pays',
            'nLevelsStructuraux': 'Niveaux pédagogiques',
            'nLevelsAdministratifs': 'Niveaux administratifs',
        }


class StructurePedagogiqueForm(forms.ModelForm):
    """Formulaire pour ajouter une structure pédagogique."""
    
    class Meta:
        model = StructurePedagogique
        fields = ['nom', 'code']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du niveau (ex: Direction Provinciale)',
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code auto',
                'maxlength': 3,
                'readonly': True
            }),
        }


class StructureAdministrativeForm(forms.ModelForm):
    """Formulaire pour ajouter une structure administrative."""
    
    class Meta:
        model = StructureAdministrative
        fields = ['nom', 'code']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du niveau (ex: Province)',
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code auto',
                'maxlength': 3,
                'readonly': True
            }),
        }
