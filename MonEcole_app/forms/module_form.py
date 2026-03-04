from django import forms
from MonEcole_app.models.module import *

class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['module','url_name']
        labels = {
            "url_name":"Adresse du module"
        }
        widgets = {
            'module': forms.Select(attrs={'class': 'form-control', 'id': 'module_select'}),
            'url_name': forms.Select(attrs={'class': 'form-control', 'id': 'url_name_select'}),
        }


class ModuleUserForm(forms.ModelForm):
    class Meta:
        model = UserModule
        fields = ['id_annee', 'user', 'module']
        labels = {  
            'id_annee': 'Année',
            'user': 'Utilisateur',
            'module': 'Module',
        }
