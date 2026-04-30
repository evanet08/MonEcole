from django.db import models


class CategorieOperation(models.Model):
    id_categorie = models.AutoField(primary_key=True)
    id_annee = models.ForeignKey('Annee', on_delete=models.PROTECT)
    idCampus = models.ForeignKey('Campus', on_delete=models.PROTECT)
    type_operation = models.CharField(
        max_length=10,
        choices=[('ENTREE', "Entrée d'argent"), ('SORTIE', "Sortie d'argent")],
    )
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    est_active = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    id_pays = models.IntegerField(null=True, blank=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "recouvrement_categorie_operation"
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        unique_together = ('type_operation', 'nom', 'id_pays')
        ordering = ['type_operation', 'nom']

    def __str__(self):
        return f"{self.type_operation}-{self.nom}"


class OperationCaisse(models.Model):
    id_operation = models.AutoField(primary_key=True)
    id_annee = models.ForeignKey('Annee', on_delete=models.PROTECT)
    idCampus = models.ForeignKey('Campus', on_delete=models.PROTECT)
    categorie = models.ForeignKey(
        CategorieOperation, on_delete=models.PROTECT, related_name='operations'
    )
    montant = models.IntegerField(verbose_name="Montant")
    date_operation = models.DateField(verbose_name="Date")
    date_enregistrement = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    source_beneficiaire = models.CharField(
        max_length=200, blank=True, null=True,
        help_text="Source (entrée) ou bénéficiaire (sortie)"
    )
    mode_paiement = models.CharField(
        max_length=20,
        choices=[
            ('ESPECES', 'Espèces'),
            ('CHEQUE', 'Chèque'),
            ('VIREMENT', 'Virement'),
            ('AUTRE', 'Autre'),
        ],
        default='ESPECES',
    )
    reference = models.CharField(max_length=100, blank=True, null=True)
    justificatif = models.FileField(upload_to='justificatifs/', blank=True, null=True)
    id_pays = models.IntegerField(null=True, blank=True)
    id_etablissement = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "recouvrement_operation"
        verbose_name = "Opération"
        verbose_name_plural = "Opérations"
        ordering = ['-date_operation', '-date_enregistrement']
        indexes = [
            models.Index(fields=['id_annee', 'idCampus', 'date_operation']),
        ]

    def __str__(self):
        type_op = self.categorie.type_operation
        return f"{'ENTRÉE' if type_op == 'ENTREE' else 'SORTIE'} - {self.montant} - {self.date_operation}"
