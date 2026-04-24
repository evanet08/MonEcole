from django.db import models
from MonEcole_app.variables import *
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
import hashlib
import secrets


class Personnel_categorie(models.Model):
    id_personnel_category = models.AutoField(primary_key=True)
    categorie = models.CharField(max_length=50, unique=True)
    sigle = models.CharField(max_length=10, null=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "personnel_categorie"
        verbose_name = "Categorie du personnel"

    def __str__(self):
        return self.categorie


class Diplome(models.Model):
    id_diplome = models.AutoField(primary_key=True)
    diplome = models.CharField(max_length=50, unique=True)
    sigle = models.CharField(max_length=10, unique=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "diplome"
        verbose_name = "diplome"

    def __str__(self):
        return self.diplome


class Specialite(models.Model):
    id_specialite = models.AutoField(primary_key=True)
    specialite = models.CharField(max_length=200, null=False)
    sigle = models.CharField(max_length=10, null=False)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "specialite"
        verbose_name = "specialite"

    def __str__(self):
        return self.specialite


class Vacation(models.Model):
    id_vacation = models.AutoField(primary_key=True)
    vacation = models.CharField(max_length=20, null=False)
    sigle = models.CharField(max_length=10)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vacation"
        verbose_name = "vacation"

    def __str__(self):
        return self.vacation


class PersonnelType(models.Model):
    id_type_personnel = models.AutoField(primary_key=True)
    type = models.CharField(max_length=50, unique=True)
    sigle = models.CharField(max_length=50, unique=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "personnel_type"
        verbose_name = "Type du personnel"

    def __str__(self):
        return self.type


class Personnel(models.Model):
    """
    Modèle unifié d'utilisateur MonEcole.
    Remplace auth_user — gère authentification + profil en une seule table.
    """
    id_personnel = models.AutoField(primary_key=True)

    # ── Champs d'authentification (ex-auth_user) ──
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True, db_index=True)
    password_hash = models.CharField(max_length=255, blank=True, default='')
    last_login = models.DateTimeField(null=True, blank=True)

    # ── Identité ──
    nom = models.CharField(max_length=200, null=True, blank=True)
    postnom = models.CharField(max_length=200, null=True, blank=True)
    prenom = models.CharField(max_length=200, null=True, blank=True)

    # ── Legacy FK (gardé pour compatibilité DB, mais plus utilisé dans le code) ──
    user_id = models.IntegerField(null=True, blank=True, db_index=True)

    codeAnnee = models.CharField(max_length=200, null=True, blank=True)
    matricule = models.CharField(max_length=20, unique=True, null=False)
    date_naissance = models.DateField(blank=True, null=True)
    genre = models.CharField(max_length=22, null=False, choices=sexe_choices, default='M')
    etat_civil = models.CharField(max_length=200, choices=etat_civil_choices, default='Célibataire')
    type_identite = models.CharField(max_length=200, null=False, blank=True)
    numero_identite = models.CharField(max_length=20, null=True, blank=True)
    telephone = PhoneNumberField(region='BI', null=True, blank=True)
    region = models.CharField(max_length=200, null=True, blank=True)
    pays = models.CharField(max_length=200, null=True, blank=True)
    province = models.CharField(max_length=200, null=False, blank=True)
    commune = models.CharField(max_length=200, null=False, blank=True)
    code_secret = models.TextField(max_length=150, blank=True, null=True)
    zone = models.CharField(max_length=200, null=False, blank=True)
    addresse = models.CharField(max_length=200, null=False, blank=True)
    imageUrl = models.ImageField(upload_to='logos/personnel/', blank=True, null=True)
    id_diplome = models.ForeignKey(Diplome, on_delete=models.PROTECT)
    id_specialite = models.ForeignKey(Specialite, on_delete=models.PROTECT)
    id_categorie = models.ForeignKey(Personnel_categorie, on_delete=models.PROTECT)
    id_vacation = models.ForeignKey(Vacation, on_delete=models.PROTECT)
    id_personnel_type = models.ForeignKey(PersonnelType, on_delete=models.PROTECT)
    isMaitresse = models.BooleanField(default=False)
    isInstiteur = models.BooleanField(default=False)
    isDAF = models.BooleanField(default=False)
    isDirecteur = models.BooleanField(default=False)
    isUser = models.BooleanField(default=False)
    en_fonction = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    date_creation = models.DateField(auto_now_add=True)
    id_etablissement = models.IntegerField(null=True, blank=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "personnel"
        managed = False  # La table existe déjà, on ne la migre pas
        verbose_name = "personnel"

    def __str__(self):
        nom = self.nom or ''
        prenom = self.prenom or ''
        return f"{prenom} {nom}_({self.matricule})"

    # ── Propriétés pour compatibilité Django auth ──

    @property
    def first_name(self):
        return self.prenom or ''

    @property
    def last_name(self):
        return self.nom or ''

    @property
    def pk(self):
        return self.id_personnel

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return self.en_fonction

    @property
    def is_anonymous(self):
        return False

    def get_full_name(self):
        parts = [self.prenom or '', self.nom or '']
        return ' '.join(p for p in parts if p).strip()

    def get_short_name(self):
        return self.prenom or self.email or self.username or ''

    # ── Méthodes d'authentification ──

    def set_password(self, raw_password):
        """Hash le mot de passe avec PBKDF2-SHA256 (sel aléatoire de 16 chars)."""
        salt = secrets.token_hex(8)  # 16 chars hex
        hashed = hashlib.pbkdf2_hmac('sha256', raw_password.encode(), salt.encode(), 260000)
        self.password_hash = f"{salt}${hashed.hex()}"

    def check_password(self, raw_password):
        """Vérifie un mot de passe contre le hash stocké."""
        if not self.password_hash or '$' not in self.password_hash:
            return False
        try:
            salt, hash_value = self.password_hash.split('$', 1)
            hashed = hashlib.pbkdf2_hmac('sha256', raw_password.encode(), salt.encode(), 260000)
            return hashed.hex() == hash_value
        except Exception:
            return False

    def has_usable_password(self):
        """Retourne True si le personnel a un mot de passe hashé valide."""
        return bool(self.password_hash) and '$' in self.password_hash

    def update_last_login(self):
        """Met à jour le timestamp du dernier login."""
        self.last_login = timezone.now()
        Personnel.objects.filter(id_personnel=self.id_personnel).update(last_login=self.last_login)


class Prestation(models.Model):
    id_prestation = models.AutoField(primary_key=True)
    heureD = models.CharField(max_length=20)
    heureF = models.CharField(max_length=20)
    id_horaire = models.IntegerField()
    id_etudiant = models.IntegerField()
    id_personnel = models.ForeignKey(Personnel, on_delete=models.PROTECT, null=False)
    date_creation = models.DateField(auto_now_add=True)
    id_pays = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "prestation"
        verbose_name = "prestation"

    def __str__(self):
        return f"{self.heureD} to {self.heureF}"
