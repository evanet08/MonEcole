
from django.db import models
from MonEcole_app.models.personnel import Personnel
from MonEcole_app.variables import modules_name, url_module_name, MODULE_URL_MAPPING


class Module(models.Model):
    id_module = models.AutoField(primary_key=True)
    module = models.CharField(max_length=100, null=False, choices=modules_name, unique=True)
    description = models.TextField(null=True, blank=True)
    url_name = models.CharField(max_length=100, null=True, blank=True, choices=url_module_name)
    id_pays = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Assurer que url_name correspond au module
        if self.module and self.module in MODULE_URL_MAPPING:
            self.url_name = MODULE_URL_MAPPING[self.module]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.module}"

    class Meta:
        db_table = 'module'


class UserModule(models.Model):
    id_user_module = models.AutoField(primary_key=True)
    id_annee = models.ForeignKey('Annee', on_delete=models.PROTECT, null=False)
    user = models.ForeignKey(Personnel, on_delete=models.PROTECT, null=False,
                              db_column='user_id', db_constraint=False)
    module = models.ForeignKey(Module, on_delete=models.PROTECT, null=False)
    is_active = models.BooleanField(default=True)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.prenom or ''} {self.user.nom or ''}"

    class Meta:
        db_table = 'user_module'