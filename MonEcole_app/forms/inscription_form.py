from django import forms
import json
from MonEcole_app.models.eleves import *
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget
from django.forms import MultiWidget, Select, NumberInput,TextInput
from django.core.exceptions import ValidationError
import re
from MonEcole_app.variables import load_country_codes




class PhoneNumberWithPrefixWidget(MultiWidget):
    def __init__(self, attrs=None):
        country_codes = load_country_codes()
        choices = [(item['code'], item['country']) for item in country_codes]

        widgets = [
            Select(choices=choices, attrs={'class': 'country-select'}),
            TextInput(attrs={'placeholder': 'Numéro de téléphone', 'class': 'phone-number'})
        ]
        super().__init__(widgets, attrs)
        
    def decompress(self, value):
        """Sépare le préfixe et le numéro"""
        if value:
            value_str = str(value)  
            for code, _ in load_country_codes():
                if value_str.startswith(code): 
                    return [code, value_str[len(code):].strip()]
        return [load_country_codes()[0]['code'], ''] 

    
    def value_from_datadict(self, data, files, name):
        """Récupère les valeurs des champs et les assemble"""
        prefix = data.get(f"{name}_0", "").strip()
        phone_number = data.get(f"{name}_1", "").strip()
        return f"{prefix}{phone_number}" if phone_number else None

class EleveForm(forms.ModelForm):
    telephone = forms.CharField(widget=PhoneNumberWithPrefixWidget(),required=False)
    def clean_telephone(self):
        phone = self.cleaned_data.get('telephone')

        if phone:
            phone_str = str(phone) if not isinstance(phone, str) else phone 
            phone_regex = re.compile(r'^\+\d{1,3}\d{6,15}$')

            if not phone_regex.match(phone_str):
                raise ValidationError("Le numéro de téléphone n'est pas valide.")

        return phone


    class Meta:
        model = Eleve
        fields = [
            'nom', 'prenom', 'genre', 'date_naissance', 'etat_civil', 'telephone',
            'nationalite', 'nom_pere', 'prenom_pere', 'nom_mere', 'prenom_mere',
            'naissance_region', 'naissance_pays', 'naissance_province',
            'naissance_commune', 'naissance_zone', 'province_actuelle',
            'commune_actuelle', 'zone_actuelle','email_parent'
        ]
        exclude = ['code_annee', 'matricule', 'code_eleve', 'email', 'password','date_naissance','telephone','etat_civil']  # Exclure 
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date'}),
            'password': forms.PasswordInput(),
            'email': forms.EmailInput(),
            'email_parent': forms.EmailInput(),
            'imageUrl': forms.ClearableFileInput(),
        }
        labels = {
            'nom': 'Nom',
            'prenom': 'Prénom',
            'email': 'Email',
            'email_parent': "Email du Parent",
            'password': 'Mot de passe',
            'telephone': 'Téléphone',
            'date_naissance': 'Date de naissance',
            'nationalite': 'Nationalité',
        }
       
class EleveInscriptionForm(forms.ModelForm):
    class Meta:
        model = Eleve_inscription
        fields = ['id_campus','id_annee','id_classe_cycle','id_classe']
        widgets = {
            'id_eleve': forms.Select(attrs={'class': 'form-control'}),
            'id_trimestre': forms.Select(attrs={'class': 'form-control'}),
            'id_classe': forms.Select(attrs={'class': 'form-control'}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_classe_cycle': forms.Select(attrs={'class': 'form-control'}),
            'redoublement': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'isDelegue': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'id_campus': 'Campus',
            'id_annee': 'A/S',
            'id_classe_cycle': 'Cycle',
            'id_classe': "Classe",
            'id_trimestre':'Trimestre'
           
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'




class EleveConduiteForm(forms.ModelForm):
    class Meta:
        model = Eleve_conduite
        fields = ['id_campus','id_annee','id_cycle','id_classe','id_trimestre','id_session','id_periode','id_eleve','id_horaire','motif','quote']
        widgets = {
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle': forms.Select(attrs={'class': 'form-control'}),
            'id_classe': forms.Select(attrs={'class': 'form-control'}),
            'id_trimestre': forms.Select(attrs={'class': 'form-control'}),           
            'id_session': forms.Select(attrs={'class': 'form-control'}),           
            'id_periode': forms.Select(attrs={'class': 'form-control'}),           
            'id_eleve': forms.Select(attrs={'class': 'form-control'}),
            'id_horaire': forms.Select(attrs={'class': 'form-control'}),
            'motif': forms.TextInput(attrs={'class': 'form-control'}),
            'quote': forms.TextInput(attrs={'class': 'form-control'}),
            
        }
        labels = {
            'id_campus': 'Campus',
            'id_annee': 'A/S',
            'id_classe_cycle': 'Cycle',
            'id_classe': "Classe",
            'id_trimestre':'Trimestre',
            'id_session':'Session',
            'id_periode':'Période',
            'id_eleve':'choisir élève',
            'id_horaire' : 'Horaire',
            'motif':'Motif',
            'quote':'Quote'
           
        }

