from django import forms
from library_manager.models.structure_base import Armoire,Compartiment,Categorie,Livre,Exemplaire,Emprunt

class ArmoireForm(forms.ModelForm):
    class Meta:
        model = Armoire
        fields = ['nom','localisation']  
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l’armoire'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Description (facultatif)',
                'rows': 3
            }),
            'localisation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Salle A - Coin gauche'
            }),
        }
        
        


class CompartimentForm(forms.ModelForm):
    class Meta:
        model = Compartiment
        fields = ['armoire', 'numero', 'capacite']
        widgets = {
            'armoire': forms.Select(attrs={'class': 'form-control'}),
            'numero': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro du compartiment'}),
            'capacite': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }
        labels = {
            'armoire': 'Armoire',
            'numero': 'Numéro du compartiment',
            'capacite': 'Capacité (nombre de livres)',
        }


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom']  
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la catégorie'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description (facultatif)'
            }),
        }
        labels = {
            'nom': 'Nom',
            'description': 'Description',
        }



class LivreForm(forms.ModelForm):
    class Meta:
        model = Livre
        fields = [
            "titre",
            "auteur",
            # "isbn",
            "categorie",
            "compartiment",
            "nombre_exemplaires",
            "etat",
        ]
        labels = {
            "titre": "Titre du livre",
            "auteur": "Auteur",
            # "isbn": "ISBN",
            "categorie": "Catégorie",
            "compartiment": "Compartiment",
            "nombre_exemplaires": "Nombre exemplaire",
            "etat": "État du livre",
        }
        widgets = {
            "titre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Entrez le titre"}),
            "auteur": forms.TextInput(attrs={"class": "form-control", "placeholder": "Entrez l'auteur"}),
            # "isbn": forms.TextInput(attrs={"class": "form-control", "placeholder": "Numéro ISBN"}),
            "categorie": forms.Select(attrs={"class": "form-select"}),
            "compartiment": forms.Select(attrs={"class": "form-select"}),
            'nombre_exemplaires': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            "etat": forms.Select(attrs={"class": "form-select"}),
        }
        
        


class ExemplaireForm(forms.ModelForm):
    class Meta:
        model = Exemplaire
        fields = ['livre', 'numero_inventaire']
        widgets = {
            'livre': forms.Select(attrs={'class': 'form-control'}),
            'numero_inventaire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Numéro inventaire'}),
            'etat': forms.Select(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EmpruntForm(forms.ModelForm):
    class Meta:
        model = Emprunt
        fields = [
            # 'livre', 'id_personnel', 'id_eleve',
            'date_retour_prevue', 'date_retour_effective',
            'id_campus', 'id_cycle_actif', 'id_classe_active', 'id_annee', 'rendu'
        ]
        widgets = {
            # 'livre': forms.Select(attrs={'class': 'form-control'}),
            'id_personnel': forms.Select(attrs={'class': 'form-control'}),
            'id_eleve': forms.Select(attrs={'class': 'form-control'}),
            'date_retour_prevue': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_retour_effective': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'id_campus': forms.Select(attrs={'class': 'form-control'}),
            'id_cycle_actif': forms.Select(attrs={'class': 'form-control'}),
            'id_classe_active': forms.Select(attrs={'class': 'form-control'}),
            'id_annee': forms.Select(attrs={'class': 'form-control'}),
            'rendu': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


