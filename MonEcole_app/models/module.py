
from django.db import models
from django.contrib.auth.models import User
from MonEcole_app.models.personnel import Personnel
from MonEcole_app.variables import modules_name,url_module_name,MODULE_URL_MAPPING

class Module(models.Model):
    id_module= models.AutoField(primary_key=True)
    module = models.CharField(max_length=100,null=False,choices=modules_name,unique = True)
    description = models.TextField(null=True,blank=True)
    url_name = models.CharField(max_length=100,null=True,blank=True,choices=url_module_name)  
    
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
    id_annee = models.ForeignKey('Annee',on_delete=models.PROTECT,null=False)
    user = models.ForeignKey(Personnel, on_delete=models.PROTECT,null=False)
    module = models.ForeignKey(Module, on_delete=models.PROTECT,null=False)
    is_active = models.BooleanField(default=True) 
    date_creation = models.DateField(auto_now_add=True)
    
    
    def __str__(self):
       return f"{self.user.user.first_name} {self.user.user.last_name}"

    class Meta:
        db_table = 'user_module'



# models pour stocker les urls effectués!
# class ModuleUrlMapping(models.Model):
#     module = models.ForeignKey(Module, on_delete=models.PROTECT)
#     url_pattern = models.CharField(max_length=255)

#     class Meta:
#         indexes = [
#             models.Index(fields=['module', 'url_pattern']),
#         ]
# models pour suivres les navigations
# class UserNavigation(models.Model):
#     user = models.ForeignKey(Personnel, on_delete=models.CASCADE)
#     url = models.CharField(max_length=255)
#     module = models.CharField(max_length=100, null=True)  # Nom du module détecté
#     timestamp = models.DateTimeField(auto_now_add=True)
#     session_key = models.CharField(max_length=40, null=True)  # Pour les utilisateurs non authentifiés ou suivi de session

#     class Meta:
#         indexes = [
#             models.Index(fields=['user', 'timestamp']),
#             models.Index(fields=['session_key', 'timestamp']),
#         ]
#         ordering = ['-timestamp']