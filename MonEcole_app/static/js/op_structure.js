
// Configuration des entités
const entityConfig = {
    categorie: {
      name: "catégorie",
      updateUrl: (id) => `/update_personnel_categorie/${id}/`,
      requiredFields: ["name"],
      errorMessage: "Erreur lors de la mise à jour de la catégorie.",
    },
    diplome: {
      name: "diplôme",
      updateUrl: (id) => `/update_diplome/${id}/`,
      requiredFields: ["name", "sigle"],
      errorMessage: "Erreur lors de la mise à jour du diplôme.",
    },
    vacation: {
      name: "vacation",
      updateUrl: (id) => `/update_vacation/${id}/`,
      requiredFields: ["name", "sigle"],
      errorMessage: "Erreur lors de la mise à jour de la vacation.",
    },
    specialite: {
      name: "spécialité",
      updateUrl: (id) => `/update_specialite/${id}/`,
      requiredFields: ["name", "sigle"],
      errorMessage: "Erreur lors de la mise à jour de la spécialité.",
    },
    type: {
      name: "type",
      updateUrl: (id) => `/update_type/${id}/`,
      requiredFields: ["name", "sigle"],
      errorMessage: "Erreur lors de la mise à jour du type.",
    },
  };
  
  // Fonction utilitaire pour récupérer le token CSRF
  const getCSRFToken = () => {
    const token = document.querySelector('[name=csrfmiddlewaretoken]');
    return token ? token.value : "";
  };
  
  // Fonction générique pour démarrer l'édition
  const editEntity = (entity, id) => {
    const row = document.getElementById(`row-${entity}-${id}`);
    if (!row) {
      console.error(`Ligne non trouvée pour ${entity} ID: ${id}`);
      alert(`Erreur : Ligne non trouvée pour ${entity}.`);
      return;
    }
  
    const name = document.getElementById(`${entity}-name-${id}`).textContent.trim();
    const sigle = document.getElementById(`${entity}-sigle-${id}`).textContent.trim();
  
    row.innerHTML = `
      <td>
        <input type="text" class="form-control" id="edit-${entity}-${id}" value="${name}">
      </td>
      <td>
        <input type="text" class="form-control" id="edit-sigle-${id}" value="${sigle}">
      </td>
      <td>
        <button class="btn btn-sm btn-success me-2" id="save-btn-${id}">
          <i class="fas fa-check"></i> ${entity === "specialite" ? "Enregistrer" : ""}
        </button>
        <button class="btn btn-sm btn-danger" id="cancel-btn-${id}">
          <i class="fas fa-times"></i> ${entity === "specialite" ? "Annuler" : ""}
        </button>
      </td>
    `;
  
    document.getElementById(`save-btn-${id}`).addEventListener("click", () => updateEntity(entity, id));
    document.getElementById(`cancel-btn-${id}`).addEventListener("click", () => cancelEditEntity(entity, id, name, sigle));
  };
  
  // Fonction générique pour annuler l'édition
  const cancelEditEntity = (entity, id, name, sigle) => {
    const row = document.getElementById(`row-${entity}-${id}`);
    row.innerHTML = `
      <td id="${entity}-name-${id}">${name}</td>
      <td id="${entity}-sigle-${id}">${sigle}</td>
      <td>
        <a href="#" class="btn btn-sm btn-outline-primary edit-btn-${entity}" data-id="${id}">
          <i class="fas fa-edit"></i> Éditer
        </a>
      </td>
    `;
    window.location.reload();
  };
  
  // Fonction générique pour mettre à jour l'entité
  const updateEntity = (entity, id) => {
    const config = entityConfig[entity];
    const name = document.getElementById(`edit-${entity}-${id}`).value;
    const sigle = document.getElementById(`edit-sigle-${id}`).value;
  
    // Validation des champs requis
    const missingFields = config.requiredFields.filter((field) =>
      field === "name" ? !name : !sigle
    );
    if (missingFields.length > 0) {
      alert(`Les champs ${missingFields.join(" et ")} sont requis.`);
      return;
    }
  
    console.log(`Envoi de la mise à jour pour ${config.name} ID: ${id}, ${config.name}: ${name}, sigle: ${sigle}`);
    fetch(config.updateUrl(id), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        [entity]: name, 
        sigle: sigle || null,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          alert(data.message);
          window.location.reload();
        } else {
          alert(`Erreur : ${data.error}`);
        }
      })
      .catch((error) => {
        console.error(`Erreur lors de la mise à jour de ${config.name} :`, error);
        alert(config.errorMessage);
      });
  };
  
  // Point d'entrée principal
  const init = () => {
    // Attacher les écouteurs pour chaque type d'entité
    Object.keys(entityConfig).forEach((entity) => {
      document.querySelectorAll(`.edit-btn-${entity}`).forEach((button) => {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          const id = button.getAttribute("data-id");
          if (!id || isNaN(id)) {
            console.error(`ID de ${entity} invalide: ${id}`);
            alert(`Erreur : ID de ${entity} invalide.`);
            return;
          }
          console.log(`Édition démarrée pour ${entity} ID: ${id}`);
          editEntity(entity, id);
        });
      });
    });
  };
  
  // Lancer l'initialisation
  document.addEventListener("DOMContentLoaded", init);