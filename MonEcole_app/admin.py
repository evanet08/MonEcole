from django.contrib import admin
# Register your models here.
from MonEcole_app.models.models_import import *
admin.site.register(PersonnelType)
admin.site.register(Personnel)
admin.site.register(Diplome)
admin.site.register(Personnel_categorie)
admin.site.register(Specialite)
admin.site.register(Vacation)
admin.site.register(Module)
admin.site.register(UserModule)
admin.site.register(Institution)
