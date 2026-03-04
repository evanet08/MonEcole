from django import forms
from MonEcole_app.models.models_import import Institution,Campus
from django import forms

class InstitutionForm(forms.ModelForm):
    class Meta:
        model = Institution
        fields = [
            'nom_ecole', 'sigle', 'telephone', 'email', 'domaine', 'site',
            'logo_ecole', 'logo_ministere', 'siege', 'fax', 'representant',
            'b_postale', 'emplacement'
        ]
        widgets = {
            'nom_ecole': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de l\'école'}),
            'sigle': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sigle'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Téléphone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'domaine': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Domaine'}),
            'site': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Site web'}),
            'siege': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Siège'}),
            'fax': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Fax'}),
            'representant': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Représentant'}),
            'b_postale': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Boîte postale'}),
            'emplacement': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Emplacement'}),
        }
        
        
        
class CampusForm(forms.ModelForm):
    class Meta:
        model = Campus
        fields = [
            'campus','adresse'
        ]
        
