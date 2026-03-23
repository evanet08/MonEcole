
from django import forms
from MonEcole_app.models.personnel import *
from MonEcole_app.forms.inscription_form import PhoneNumberWithPrefixWidget
from django.core.exceptions import ValidationError
import re
from MonEcole_app.models.models_import import User_enseignement


class PersonnelCategorieForm(forms.ModelForm):
    class Meta:
        model = Personnel_categorie
        fields = '__all__'
        labels={
            "categorie":"Catégorie du personnel"
        }
        widgets = {
            'categorie': forms.TextInput(attrs={'class': 'form-control'}),
            'sigle': forms.TextInput(attrs={'class': 'form-control'}),
        }

class DiplomeForm(forms.ModelForm):
    class Meta:
        model = Diplome
        fields = '__all__'
        labels={
            "diplome":"Diplôme du personnel"
        }
        widgets = {
            'diplome': forms.TextInput(attrs={'class': 'form-control'}),
            'sigle': forms.TextInput(attrs={'class': 'form-control'}),
        }

class SpecialiteForm(forms.ModelForm):
    class Meta:
        model = Specialite
        fields = '__all__'
        labels={
            "specialite":"Spécialité du personnel"
        }
        widgets = {
            'specialite': forms.TextInput(attrs={'class': 'form-control'}),
            'sigle': forms.TextInput(attrs={'class': 'form-control'}),
        }

class VacationForm(forms.ModelForm):
    class Meta:
        model = Vacation
        fields = '__all__'
        labels = {
            "vacation":"Vacation du personnel"
        }
        widgets = {
            'vacation': forms.TextInput(attrs={'class': 'form-control'}),
            'sigle': forms.TextInput(attrs={'class': 'form-control'}),
        }

class PersonnalTypeForm(forms.ModelForm):
    class Meta:
        model =PersonnelType
        fields = '__all__'
        labels = {
            "type":"Type du personnel"
        }
        widgets = {
            'type': forms.TextInput(attrs={'class': 'form-control'}),
            'sigle': forms.TextInput(attrs={'class': 'form-control'}),
        }
class PersonnelUserForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['username']:
            self.fields[field].widget.attrs['readonly'] = True
            
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False 
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False  
    )
    class Meta:
        model=User
        fields=['first_name','last_name','email','password','username']
        labels = {
            'first_name': 'Nom',
            'last_name': 'Prénom',
            'email': 'Email',  
            'username':'Email professionnel'
        }
        widgets = {
        'password': forms.PasswordInput()
        }
    def save(self, commit=True):
        user = super().save(commit=False)
        if not self.cleaned_data["password"]: 
            user.set_unusable_password()  
        if commit:
            user.save()
        return user
    

class PersonnelForm(forms.ModelForm):
    date_naissance = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False,
        initial=timezone.now
    )
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
        model = Personnel
        fields = ['addresse','genre','imageUrl','date_naissance','pays','province','region','commune','id_diplome','id_specialite','id_categorie','id_vacation','id_personnel_type']  # Inclure tous les champs du modèle
        widgets = {
            'date_naissance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'addresse': forms.TextInput(attrs={'class': 'form-control'}),
            'matricule': forms.TextInput(attrs={'class': 'form-control'}),
            'pays': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'commune': forms.TextInput(attrs={'class': 'form-control'}),
            'zone': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_identite': forms.TextInput(attrs={'class': 'form-control'}),
            'type_identite': forms.Select(attrs={'class': 'form-control'}),
            'genre': forms.Select(attrs={'class': 'form-control'}),
            'etat_civil': forms.Select(attrs={'class': 'form-control'}),
            'id_diplome': forms.Select(attrs={'class': 'form-control'}),
            'id_specialite': forms.Select(attrs={'class': 'form-control'}),
            'id_categorie': forms.Select(attrs={'class': 'form-control'}),
            'id_vacation': forms.Select(attrs={'class': 'form-control'}),
            'id_personnel_type': forms.Select(attrs={'class': 'form-control'}),
            'imageUrl': forms.FileInput(attrs={'class': 'form-control'}),
        }

        labels = {
            'id_diplome': 'Diplome',
            'id_specialite': 'Spécialité',
            'id_categorie': 'Categorie',
            'id_vacation': "Vacation",
            'id_personnel_type': 'type du personnel',
        }



class User_enseignant_form(forms.ModelForm):
    class Meta:
        model = User_enseignement
        fields = ['id_annee','id_campus','cycle_id','classe_id']
        widgets = {
            'id_personnel': forms.Select(attrs={'class': 'form-control'}),
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'cycle_id': forms.Select(attrs={'class': 'form-control'}),
            'classe_id': forms.Select(attrs={'class': 'form-control'}),  
        }
        labels = {
           
            'id_annee': 'A/S',
            'id_campus': 'Campus',
            'cycle_id': "Niveau",
            'classe_id':'Classe'
        }