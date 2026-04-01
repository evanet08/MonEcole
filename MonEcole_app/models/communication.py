from django.db import models


class Communication(models.Model):
    """
    Table unifiée de communication pour l'Espace Enseignant.

    Gère tous les flux de messages :
    - Enseignant → Parents (d'une classe entière, de tout l'établissement, ou d'un élève)
    - Parents → Enseignant / École
    - École → Parents / Enseignants

    Le champ `scope` détermine la portée du message :
    - 'individual' : Un parent/élève spécifique (via target_eleve_id)
    - 'class'      : Tous les parents d'une classe (via target_classe_id)  
    - 'etab'       : Tous les parents de l'établissement
    - 'teacher'    : Message adressé à un enseignant spécifique

    Le champ `direction` indique le sens du message :
    - 'out' : Sortant (l'enseignant/école envoie)
    - 'in'  : Entrant (un parent répond)
    """

    SCOPE_CHOICES = [
        ('individual', 'Élève/Parent individuel'),
        ('class', 'Classe entière'),
        ('etab', 'Tout l\'établissement'),
        ('teacher', 'Enseignant spécifique'),
    ]

    DIRECTION_CHOICES = [
        ('out', 'Sortant'),
        ('in', 'Entrant'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Envoyé'),
        ('delivered', 'Délivré'),
        ('read', 'Lu'),
        ('failed', 'Échoué'),
    ]

    id_communication = models.AutoField(primary_key=True)

    # Contexte établissement + année (multi-tenant)
    id_etablissement = models.IntegerField()
    id_annee = models.IntegerField(null=True, blank=True)

    # Qui envoie (personnel ou parent — l'un des deux est renseigné)
    sender_personnel_id = models.IntegerField(null=True, blank=True, db_index=True)
    sender_eleve_id = models.IntegerField(null=True, blank=True, db_index=True)
    sender_name = models.CharField(max_length=255, blank=True, default='')

    # Portée du message
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default='individual')
    direction = models.CharField(max_length=5, choices=DIRECTION_CHOICES, default='out')

    # Cibles (utilisés selon le scope)
    target_eleve_id = models.IntegerField(null=True, blank=True, db_index=True)
    target_classe_id = models.IntegerField(null=True, blank=True, db_index=True)
    target_personnel_id = models.IntegerField(null=True, blank=True, db_index=True)

    # Contenu
    subject = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField()
    
    # Fil de discussion (pour regrouper les messages dans une conversation)
    thread_id = models.CharField(max_length=100, blank=True, default='', db_index=True)

    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'communication'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['id_etablissement', 'thread_id']),
            models.Index(fields=['id_etablissement', 'sender_personnel_id', 'created_at']),
            models.Index(fields=['id_etablissement', 'target_eleve_id', 'created_at']),
            models.Index(fields=['id_etablissement', 'target_classe_id', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.direction}] {self.sender_name} → {self.get_scope_display()} | {self.message[:50]}"
