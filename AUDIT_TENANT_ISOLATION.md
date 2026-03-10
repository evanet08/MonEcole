# AUDIT: Isolation Multi-Tenant par id_etablissement
## Date: 2026-03-10

## Architecture
- **Clé tenant**: `id_etablissement` (résolu via TenantMiddleware depuis le sous-domaine)
- **Table pivot**: `campus.id_etablissement` → l'établissement possède un ou plusieurs campus
- **28 tables** dans db_monecole ont la colonne `id_etablissement`

## Phase 1 : Modèles Django (FAIT ✅)
Les modèles suivants ont reçu `id_etablissement = models.IntegerField(null=True, blank=True)` :

| Modèle | Table DB | Status |
|--------|----------|--------|
| Campus | campus | ✅ (existait déjà) |
| Eleve | eleve | ✅ Ajouté |
| Eleve_inscription | eleve_inscription | ✅ Ajouté |
| Eleve_note | eleve_note | ✅ Ajouté |
| Eleve_conduite | eleve_conduite | ✅ Ajouté |
| Evaluation | evaluation | ✅ Ajouté |
| Personnel | personnel | ✅ Ajouté |
| Classe_deliberation | classe_deliberation | ✅ Ajouté |
| Classe_active_responsable | classe_active_responsable | ✅ Ajouté |
| Deliberation_annuelle_condition | deliberation_annuelle_conditions | ✅ Ajouté |
| Deliberation_annuelle_resultat | deliberation_annuelle_resultats | ✅ Ajouté |
| Deliberation_periodique_resultat | deliberation_periodique_resultats | ✅ Ajouté |
| Deliberation_examen_resultat | deliberation_examen_resultats | ✅ Ajouté |
| Deliberation_trimistrielle_resultat | deliberation_trimistrielle_resultats | ✅ Ajouté |
| Deliberation_repechage_resultat | deliberation_repechage_resultats | ✅ Ajouté |
| Horaire | horaire | ✅ Ajouté |
| Horaire_presence | horaire_presence | ✅ Ajouté |
| Salle | salle | ✅ Ajouté |
| User_enseignement | user_enseignement | ✅ Ajouté |
| Users_other_module | users_other_module | ✅ Ajouté |
| UserModule | user_module | ✅ Ajouté |

### Tables restantes (recouvrement) — colonne existe dans DB :
| Table DB | Modèle Django | Status |
|----------|---------------|--------|
| attribution_cours | Attribution_cours | ⚠️ À vérifier |
| prestation | Prestation | ⚠️ À vérifier |
| recouvrment_paiement | Paiement | ⚠️ À vérifier |
| recouvrment_reduction_prix | - | ⚠️ À vérifier |
| recouvrment_variable_datebutoire | - | ⚠️ À vérifier |
| recouvrment_variable_derogation | - | ⚠️ À vérifier |
| recouvrment_variable_prix | - | ⚠️ À vérifier |

## Phase 2 : Utilitaires Tenant (FAIT ✅)
- `tenant_utils.py` → ajout de `tenant_etablissement_filter(request, queryset)` 
- Filtrage direct par `id_etablissement` (plus efficace que via Campus IDs)

## Phase 3 : Vues à mettre à jour (EN ATTENTE)

### Fichiers DÉJÀ protégés par tenant_utils :
1. `views/structure/api_structure.py` ✅
2. `views/structure/create_structure.py` ✅  
3. `views/direction_views/api_infos.py` ✅
4. `views/recouvrement/api_load.py` ✅
5. `views/enseignement/api.py` ✅
6. `views/enseignement/enseignements.py` ✅
7. `views/evaluation/api.py` ✅
8. `views/inscription/inscription.py` ✅

### Fichiers SANS protection tenant (25 fichiers) :
1. `views/__bulletin/pdf.py` ⚠️ CRITIQUE (bulletins pourraient mixer des élèves)
2. `views/direction_views/home_direct.py` ⚠️ CRITIQUE (dashboard affiche stats globales)
3. `views/enseignement/espace_enseignant.py` ⚠️
4. `views/evaluation/avancement_view.py` ⚠️
5. `views/evaluation/deliberation_annuelle.py` ⚠️ CRITIQUE
6. `views/evaluation/deliberation_criteres.py` ⚠️ CRITIQUE
7. `views/evaluation/deliberation_trimestrielle.py` ⚠️ CRITIQUE
8. `views/evaluation/evaluation.py` ⚠️ CRITIQUE
9. `views/evaluation/excel_notes_utils.py` ⚠️
10. `views/evaluation/form_select_utils.py` ⚠️
11. `views/evaluation/repechage.py` ⚠️ CRITIQUE
12. `views/evaluation/structure_bulletin.py` ⚠️
13. `views/home/home.py` ⚠️
14. `views/inscription/email_validate.py` ⚠️
15. `views/inscription/inscription_list_pdf.py` ⚠️
16. `views/inscription/inscription_status.py` ⚠️
17. `views/personnel.py` ⚠️
18. `views/rdc_structure/structure_maternelle.py` ⚠️ CRITIQUE
19. `views/rdc_structure/structure_par_module.py` ⚠️
20. `views/rdc_structure/structure_primaire.py` ⚠️ CRITIQUE
21. `views/rdc_structure/structure_secondaire.py` ⚠️ CRITIQUE
22. `views/recouvrement/invoice_paiement.py` ⚠️
23. `views/structure/delete_structure.py` ⚠️
24. `views/structure/edit_structure.py` ⚠️
25. `views/tools/utils.py` ⚠️

### Pattern de correction pour chaque vue :
```python
# AVANT (non sécurisé) :
eleves = Eleve.objects.all()
notes = Eleve_note.objects.filter(id_classe_active=classe_id)

# APRÈS (sécurisé) :
from MonEcole_app.views.tools.tenant_utils import tenant_etablissement_filter
eleves = tenant_etablissement_filter(request, Eleve.objects.all())
notes = tenant_etablissement_filter(request, Eleve_note.objects.filter(id_classe_active=classe_id))
```
