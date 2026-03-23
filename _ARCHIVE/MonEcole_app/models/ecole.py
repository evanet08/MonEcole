from django.db import models


# Institution pointe directement vers countryStructure.etablissements (Hub).
# Plus de VIEW 'ecole' ni de modèle 'Etablissement' séparé.

class Institution(models.Model):
    """
    Infos de l'école — lecture directe depuis countryStructure.etablissements.
    Remplace la VIEW 'ecole' supprimée.
    Le Campus local contient id_etablissement pour faire le lien.
    
    COMPAT ARRIÈRE: Les champs utilisent db_column pour mapper
    les noms de colonnes du Hub aux noms attendus par le code spoke.
    """
    id_ecole = models.AutoField(primary_key=True, db_column='id_etablissement')
    nom_ecole = models.CharField(max_length=250, db_column='nom')
    sigle = models.CharField(max_length=50, null=True, blank=True)
    telephone = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    logo_ecole = models.ImageField(upload_to='logos/ecole/', blank=True, null=True)
    siege = models.TextField(null=True, blank=True, db_column='adresse')
    fax = models.CharField(max_length=20, null=True, blank=True)
    representant = models.CharField(max_length=200, null=True, blank=True)
    b_postale = models.CharField(max_length=50, null=True, blank=True, db_column='boite_postale')
    emplacement = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.nom_ecole

    @property
    def logo_ministere(self):
        """Compat : logo_ministere est désormais sur le modèle Pays."""
        try:
            from MonEcole_app.models.country_structure import Pays
            pays = Pays.objects.first()
            return pays.logo_ministere if pays else None
        except Exception:
            return None

    @property
    def site(self):
        return None

    class Meta:
        db_table = 'etablissements'
        managed = False
