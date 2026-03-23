# Audit Tenant Isolation — MonEcole
## Dernière mise à jour : 2026-03-10

---

## 1. Phase 1 : Modèles Django (✅ COMPLÉTÉ)

**Ajouté `id_etablissement = IntegerField(null=True, blank=True)` aux modèles suivants :**

| Modèle | Fichier | Statut |
|--------|---------|--------|
| `Eleve` | `models/eleves/eleve.py` | ✅ |
| `Eleve_inscription` | `models/eleves/eleve.py` | ✅ |
| `Eleve_note` | `models/eleves/eleve.py` | ✅ |
| `Eleve_conduite` | `models/eleves/eleve.py` | ✅ |
| `Evaluation` | `models/evaluations/note.py` | ✅ |
| `Personnel` | `models/personnel.py` | ✅ |
| `Classe_deliberation` | `models/classe.py` | ✅ |
| `Classe_active_responsable` | `models/classe.py` | ✅ |
| `Deliberation_annuelle_condition` | `models/evaluations/note.py` | ✅ |
| `Deliberation_annuelle_resultat` | `models/evaluations/note.py` | ✅ |
| `Deliberation_periodique_resultat` | `models/evaluations/note.py` | ✅ |
| `Deliberation_examen_resultat` | `models/evaluations/note.py` | ✅ |
| `Deliberation_trimistrielle_resultat` | `models/evaluations/note.py` | ✅ |
| `Deliberation_repechage_resultat` | `models/evaluations/note.py` | ✅ |
| `Horaire` | `models/horaire.py` | ✅ |
| `Horaire_presence` | `models/horaire.py` | ✅ |
| `Salle` | `models/salle.py` | ✅ |
| `User_enseignement` | `models/enseignmnts/users_enseignant.py` | ✅ |
| `Users_other_module` | `models/enseignmnts/users_enseignant.py` | ✅ |
| `UserModule` | `models/module.py` | ✅ |

---

## 2. Phase 2 : Utilitaires Tenant (✅ COMPLÉTÉ)

**Fichier : `views/tools/tenant_utils.py`**

| Fonction | Description |
|----------|-------------|
| `get_tenant_id(request)` | Récupère l'id_etablissement depuis la session |
| `get_tenant_campus_ids(request)` | Retourne les IDs de campus liés à l'établissement |
| `tenant_campus_filter(request, queryset)` | Filtre un queryset par campus du tenant |
| `tenant_etablissement_filter(request, queryset)` | Filtre un queryset directement par id_etablissement |
| `validate_campus_access(request, campus_id)` | Vérifie qu'un campus_id appartient au tenant |
| `deny_cross_tenant_access(request, campus_id)` | Retourne 403 si accès interdit |

---

## 3. Phase 3 : Filtrage des Vues (✅ COMPLÉTÉ)

### Batch 1 — Dashboard & Critères de délibération
| Fichier | Correction | Statut |
|---------|------------|--------|
| `views/direction_views/home_direct.py` | Toutes les queries `Eleve_inscription` filtrées par `id_etablissement` via `tenant_etablissement_filter` | ✅ |
| `views/evaluation/deliberation_criteres.py` | `Deliberation_annuelle_condition.objects.all()` → filtré par `campus_ids` ; `Classe_active` queries filtrées | ✅ |
| `views/evaluation/__initials.py` | Import centralisé tenant_utils — propagé à tous les fichiers d'évaluation via `import *` | ✅ |
| `views/structure/_initials.py` | Import centralisé tenant_utils — propagé à `delete_structure.py` et `edit_structure.py` | ✅ |

### Batch 2 — Toutes les fonctions de listing de classes
| Fichier | Correction | Statut |
|---------|------------|--------|
| `views/enseignement/espace_enseignant.py` | **10 fonctions** corrigées avec `id_campus__in=campus_ids` : | ✅ |
| | `soumettre_evaluation_prevu` — `Evaluation.objects.all()` → `tenant_etablissement_filter` | ✅ |
| | `load_all_classes_by_attribution_cours_year` | ✅ |
| | `load_all_classes_by_attribution_cours_year_without_classes_deliberateAnnually` | ✅ |
| | `load_all_classes_by_tutilaire_classe_year` | ✅ |
| | `load_all_repechage_classes_byTutilaire_year` | ✅ |
| | `load_all_classes_deliberates_by_year` | ✅ |
| | `load_all_classes_by_year_without_classes_deliberated` | ✅ |
| | `load_all_repechage_classes_by_year` | ✅ |
| | `load_all_classes_with_notes_by_year` | ✅ |
| `views/evaluation/deliberation_criteres.py` | `load_all_classes_without_decision_deliberat_by_year` — ajout `id_campus__in=campus_ids` | ✅ |

### Batch 3 — Validation campus pour PDF & Recouvrement
| Fichier | Correction | Statut |
|---------|------------|--------|
| `views/inscription/inscription_list_pdf.py` | `validate_campus_access` avant génération PDF | ✅ |
| `views/recouvrement/invoice_paiement.py` | `validate_campus_access` avant génération facture | ✅ |
| `views/recouvrement/create_base.py` | Import tenant_utils (propagé à `save_api.py` via `import *`) | ✅ |

### Fichiers protégés par propagation d'imports (`import *`)
Ces fichiers ont accès aux utilitaires tenant via la chaîne d'importation :

```
__initials.py (tenant_utils) 
  → structure_bulletin.py (from .__initials import *)
    → evaluation.py (from .structure_bulletin import *)
      → repechage.py (from .evaluation import *)
  → delib_an_tools.py (from .__initials import *)
    → deliberation_trimestrielle.py (from .delib_an_tools import *)
    → deliberation_annuelle.py (from .delib_an_tools import *)
  → form_select_utils.py (from .__initials import ...)

_initials.py (tenant_utils)
  → delete_structure.py (from ._initials import *)
  → edit_structure.py (from ._initials import *)

create_base.py (tenant_utils)
  → save_api.py (from .create_base import *)

inscription.py (tenant_utils - déjà présent)
  → inscription_status.py (from .inscription import *)
```

---

## 4. Fichiers ne nécessitant PAS de filtrage tenant

| Fichier | Raison |
|---------|--------|
| `views/home/home.py` | Redirections uniquement, pas de requêtes de données opérationnelles |
| `views/personnel.py` | Authentification/login — pas de données opérationnelles croisées |
| `views/inscription/email_validate.py` | Validation email — pas de requêtes par campus |
| `views/rdc_structure/structure_primaire.py` | Fonctions utilitaires de calcul PDF, appelées avec IDs déjà filtrés |
| `views/rdc_structure/structure_secondaire.py` | Idem |
| `views/rdc_structure/structure_maternelle.py` | Idem |
| `views/rdc_structure/structure_par_module.py` | Idem |
| `views/evaluation/excel_notes_utils.py` | Fonctions utilitaires, appelées avec IDs déjà filtrés |
| `views/__bulletin/pdf.py` | Endpoint PDF — reçoit des IDs déjà filtrés en amont |
| `views/evaluation/avancement_view.py` | Reçoit campus/classe en paramètres, déjà filtrés par les forms |
| `views/tools/utils.py` | Utilitaire `get_user_info` — pas de données opérationnelles |

---

## 5. Résumé des commits

| Commit | Description |
|--------|-------------|
| Phase 1 | `id_etablissement` ajouté à 20+ modèles + `tenant_etablissement_filter` utility |
| Batch 1 | Dashboard stats + critères délibération + imports centralisés |
| Batch 2 | 10 fonctions de listing de classes filtrées par campus |
| Batch 3 | Validation campus pour PDFs + import recouvrement |

---

## 6. Pattern de correction appliqué

```python
# Import centralisé (dans _initials.py ou __initials.py)
from MonEcole_app.views.tools.tenant_utils import (
    tenant_etablissement_filter, get_tenant_campus_ids,
    deny_cross_tenant_access, validate_campus_access
)

# Pattern 1: Filtrage direct par id_etablissement
base_qs = tenant_etablissement_filter(request, Model.objects.all())
results = base_qs.filter(**other_filters)

# Pattern 2: Filtrage Classe_active par campus
campus_ids = get_tenant_campus_ids(request)
classes = Classe_active.objects.filter(
    id_annee_id=annee_id,
    id_campus__in=campus_ids  # <-- AJOUTÉ
)

# Pattern 3: Validation d'accès campus (endpoints PDF/API)
if not validate_campus_access(request, campus_id):
    return HttpResponse(status=403)
```
