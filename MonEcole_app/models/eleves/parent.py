from django.db import models


class Profession(models.Model):
    id_profession = models.AutoField(primary_key=True)
    nom = models.CharField(max_length=255)
    id_pays = models.IntegerField(default=2)

    def __str__(self):
        return self.nom

    class Meta:
        db_table = 'professions'


class Parent(models.Model):
    id_parent = models.AutoField(primary_key=True)
    # Père
    nomsPere = models.CharField(max_length=500, null=True, blank=True)
    telephonePere = models.CharField(max_length=50, null=True, blank=True)
    emailPere = models.EmailField(null=True, blank=True)
    id_profession_pere = models.ForeignKey(
        Profession, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_profession_pere', related_name='parents_pere'
    )
    pere_en_vie = models.BooleanField(default=True)
    # Mère
    nomsMere = models.CharField(max_length=500, null=True, blank=True)
    telephoneMere = models.CharField(max_length=50, null=True, blank=True)
    emailMere = models.EmailField(null=True, blank=True)
    id_profession_mere = models.ForeignKey(
        Profession, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_profession_mere', related_name='parents_mere'
    )
    mere_en_vie = models.BooleanField(default=True)
    id_pays = models.IntegerField(default=2)

    def __str__(self):
        parts = []
        if self.nomsPere:
            parts.append(f"P: {self.nomsPere}")
        if self.nomsMere:
            parts.append(f"M: {self.nomsMere}")
        return ' | '.join(parts) if parts else f'Parent #{self.id_parent}'

    class Meta:
        db_table = 'parents'