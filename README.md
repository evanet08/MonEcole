# MonEkole - Plateforme de Gestion Scolaire G\'en\'erique

MonEkole est une solution de gestion scolaire moderne et flexible, con\c{c}ue pour s'adapter aux syst\`emes \'educatifs de diff\'erents pays sans modification du code source.

## 🚀 Fonctionnalit\'e Phare : Structuration G\'en\'erique par Pays

Le projet int\`egre une mod\'elisation purement dynamique permettant de configurer la hi\'erarchie administrative et p\'edagogique de n'importe quel pays.

### Logique des Niveaux (Steps/Levels)
Chaque pays d\'efinit son propre nombre de niveaux entre le niveau provincial et l'\'etablissement :
- **Axe P\'edagogique** : D\'efinit l'organisation de l'enseignement (ex: Ministère $\to$ DPE $\to$ DCE $\to$ \'Ecole).
- **Axe Administratif** : D\'efinit l'organisation territoriale (ex: Province $\to$ Commune $\to$ Secteur).

### Architecture Multi-Bases de Donn\'ees
Pour garantir la robustesse, le système utilise deux bases de donn\'ees distinctes :
1.  **`db_monecole`** : Contient les donn\'ees op\'erationnelles standard (utilisateurs, sessions, notes, finances).
2.  **`countryStructure`** : Base d\'edi\'ee exclusivement à la nomenclature g\'en\'erique des pays.

Cette s\'eparation est g\'er\'ee de manière transparente par un **Database Router** Django.

## 🛠️ Installation et Configuration

### Pr\'erequis
- Python 3.12+
- MySQL / MariaDB
- Accès SSH (pour le d\'eploiment)

### Setup
1.  **Environnement** :
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
2.  **Base de donn\'ees** :
    Cr\'eez les deux bases de donn\'ees et donnez les droits à l'utilisateur configur\'e dans votre `.env`.
3.  **Migrations** :
    Django appliquera automatiquement les migrations vers les bonnes bases grâce au routeur :
    ```bash
    python manage.py migrate
    python manage.py migrate --database=countryStructure
    ```

## 📱 Interface Utilisateur
La page de param\'etrage (`/structuration_pays/`) offre une exp\'erience "Premium" :
- **Glassmorphism Design** : Interface fluide et moderne.
- **Auto-g\'en\'eration de codes** : Les codes de niveaux (3 caractères) sont g\'er\'es automatiquement.
- **Règles de coh\'erence** : La page impose la compl\'etion totale de la structure d\'efinie avant de permettre la navigation.
- **Ajustement Dynamique** : Possibilit\'e de recalibrer les niveaux existants en un clic.

## 📄 Documentation Technique
Un document technique d\'etaill\'e est disponible au format LaTeX :
- `documentation_structuration_pays.tex`

---
*D\'evelopp\'e par ICT Group pour MonEkole.*
