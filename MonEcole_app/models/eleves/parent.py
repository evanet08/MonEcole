from django.db import models


class Profession(models.Model):
    id_profession = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)

    def __str__(self):
        return self.nom

    class Meta:
        db_table = 'professions'


class Parent(models.Model):
    id_parent = models.AutoField(primary_key=True)
    # Père
    nomPere = models.CharField(max_length=255, null=True, blank=True)
    postnomPere = models.CharField(max_length=255, null=True, blank=True)
    prenomPere = models.CharField(max_length=255, null=True, blank=True)
    telephonePere = models.CharField(max_length=50, null=True, blank=True)
    emailPere = models.EmailField(null=True, blank=True)
    id_profession_pere = models.ForeignKey(
        Profession, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_profession_pere', related_name='parents_pere'
    )
    pere_en_vie = models.BooleanField(default=True)
    # Mère
    nomMere = models.CharField(max_length=255, null=True, blank=True)
    postnomMere = models.CharField(max_length=255, null=True, blank=True)
    prenomMere = models.CharField(max_length=255, null=True, blank=True)
    telephoneMere = models.CharField(max_length=50, null=True, blank=True)
    emailMere = models.EmailField(null=True, blank=True)
    id_profession_mere = models.ForeignKey(
        Profession, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_profession_mere', related_name='parents_mere'
    )
    mere_en_vie = models.BooleanField(default=True)

    def __str__(self):
        parts = []
        if self.nomPere:
            parts.append(f"P: {self.nomPere}")
        if self.nomMere:
            parts.append(f"M: {self.nomMere}")
        return ' | '.join(parts) if parts else f'Parent #{self.id_parent}'

    class Meta:
        db_table = 'parents'