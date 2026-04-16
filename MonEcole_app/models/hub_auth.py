"""
Modèles d'authentification pour MonEcole.
Tables propres dans le spoke (db_monecole) — 100% autonome.
"""
from django.db import models
from django.utils import timezone


class AdminUser(models.Model):
    """
    Utilisateur administrateur MonEcole.
    Table: db_monecole.admin_users
    """
    id_admin = models.AutoField(primary_key=True)

    # Identifiants
    email = models.EmailField(verbose_name="Email")
    telephone = models.CharField(max_length=20, blank=True, default='', verbose_name="Téléphone")
    password_hash = models.CharField(max_length=128, blank=True, verbose_name="Mot de passe hashé")

    # Rôle / niveau
    ROLE_CHOICES = [
        ('directeur', 'Directeur'),
        ('prefet', 'Préfet des études'),
        ('secretaire', 'Secrétaire'),
        ('comptable', 'Comptable'),
        ('enseignant', 'Enseignant'),
        ('admin', 'Administrateur'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='admin', verbose_name="Rôle")
    nom = models.CharField(max_length=100, blank=True, default='', verbose_name="Nom")
    prenom = models.CharField(max_length=100, blank=True, default='', verbose_name="Prénom")

    # Validation du compte
    email_verified = models.BooleanField(default=False, verbose_name="Email vérifié")
    phone_verified = models.BooleanField(default=False, verbose_name="Téléphone vérifié")
    is_active = models.BooleanField(default=True, verbose_name="Compte actif")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    id_pays = models.IntegerField(default=2)

    class Meta:
        db_table = 'admin_users'
        verbose_name = 'Utilisateur Admin'
        verbose_name_plural = 'Utilisateurs Admin'
        ordering = ['email']

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def niveau_nom(self):
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    @property
    def niveau_ordre(self):
        ordre_map = {
            'directeur': 0, 'prefet': 1, 'secretaire': 2,
            'comptable': 3, 'admin': 4, 'enseignant': 5,
        }
        return ordre_map.get(self.role, 99)

    @property
    def scope_name(self):
        if self.nom or self.prenom:
            return f"{self.prenom} {self.nom}".strip()
        return self.email

    @property
    def scope_code(self):
        return self.role

    @property
    def is_validated(self):
        return self.email_verified or self.phone_verified

    @property
    def has_password(self):
        return bool(self.password_hash)

    @property
    def full_name(self):
        return f"{self.prenom} {self.nom}".strip() or self.email


class OTPCode(models.Model):
    """
    Code OTP pour validation email/téléphone.
    Table: db_monecole.otp_codes
    """
    TYPE_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
    ]

    id_otp = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        AdminUser, on_delete=models.CASCADE,
        related_name='otp_codes', verbose_name="Utilisateur"
    )
    code = models.CharField(max_length=6, verbose_name="Code OTP")
    type = models.CharField(max_length=5, choices=TYPE_CHOICES)
    expires_at = models.DateTimeField(verbose_name="Expire à")
    attempts = models.PositiveIntegerField(default=0)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    id_pays = models.IntegerField(default=2)

    class Meta:
        db_table = 'otp_codes'
        verbose_name = 'Code OTP'
        verbose_name_plural = 'Codes OTP'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP {self.code} pour {self.user.email}"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_expired and not self.used and self.attempts < 3

    def increment_attempts(self):
        self.attempts += 1
        self.save(update_fields=['attempts'])

    def mark_used(self):
        self.used = True
        self.save(update_fields=['used'])
