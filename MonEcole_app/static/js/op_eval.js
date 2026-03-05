
// Fonctions utilitaires communes
const saveToSession = (key, value) => sessionStorage.setItem(key, value);
const getFromSession = (key) => sessionStorage.getItem(key);

function sanitize(str) {
  return String(str).replace(/[&<>"'`=\/]/g, function (s) {
    return {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
      '`': '&#96;',
      '=': '&#61;',
      '/': '&#47;',
    }[s];
  });
}

const hideFields = (...fields) => {
  fields.forEach((field) => {
    if (field) {
      field.parentElement.style.display = "none";
      field.disabled = true;
    }
  });
};

const showField = (field) => {
  if (field) {
    field.parentElement.style.display = "block";
    field.style.display = "block";
    field.disabled = false;
  }
};

const updateDropdown = (url, dropdown, idKey, nameKey, extraData = {}) => {
  return fetch(url)
    .then((response) => {
      if (!response.ok) throw new Error("Erreur réseau ou serveur");
      return response.json();
    })
    .then((responseData) => {
      const data = responseData.data || responseData.cours_list || responseData.trimestres || responseData.sessions || responseData || [];
      const items = Array.isArray(data) ? data : [];
      dropdown.innerHTML = '<option value="">------</option>';
      if (items.length > 0) {
        items.forEach((item) => {
          const option = document.createElement("option");
          option.value = item[idKey];
          option.textContent = item[nameKey];
          if (item.id_campus) option.dataset.campus = item.id_campus;
          if (item.id_cycle) option.dataset.cycle = item.id_cycle;
          if (item.id_classe) option.dataset.classe = item.id_classe;
          dropdown.appendChild(option);
        });
        showField(dropdown);
        return { hasData: true, count: items.length };
      } else {
        console.log("Aucune donnée trouvée pour cette sélection effectuée");
        return { hasData: false, count: 0 };
      }
    })
    .catch((error) => {
      console.error("Erreur lors du chargement :", error);
      return { hasData: false, count: 0, error: true };
    });
};

// Gestion du modal (global)
const setupModal = () => {
  const modal = document.getElementById("modalContainer");
  const openModalButtons = document.querySelectorAll(".open-modal-btn");
  const closeModalBtn = document.querySelector(".close-btn");
  const cancelBtn = document.getElementById("cancelBtn");

  if (!modal || !openModalButtons.length || !closeModalBtn || !cancelBtn) {
    console.error("Un ou plusieurs éléments du modal sont manquants.");
    return;
  }

  const closeModal = () => {
    modal.style.display = "none";
    document.body.style.overflow = "auto";
  };

  openModalButtons.forEach((button) => {
    button.addEventListener("click", () => {
      modal.style.display = "flex";
      document.body.style.overflow = "hidden";
    });
  });

  closeModalBtn.addEventListener("click", closeModal);
  cancelBtn.addEventListener("click", closeModal);
  window.addEventListener("click", (event) => {
    if (event.target === modal) closeModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && modal.style.display === "flex") closeModal();
  });

  const form = document.getElementById("userForm");
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      closeModal();
    });
  }
};

// Logique pour /generer_excel_file/
const setupExcelFile = () => {
  const fields = {
    idAnnee: document.getElementById("id_id_annee"),
    idCampus: document.getElementById("id_id_campus"),
    idClasseCycle: document.getElementById("id_id_cycle_actif"),
    idClasse: document.getElementById("id_id_classe_active"),
    coursField: document.getElementById("id_id_cours_classe"),
    jrField: document.getElementById("id_id_session"),
    horaireTypeField: document.getElementById("id_id_trimestre"),
    periodeField: document.getElementById("id_id_periode"),
    typeNoteField: document.getElementById("id_id_type_note"),
    evaluationField: document.getElementById("id_id_evaluation"),
    trimestreTable: document.getElementById("table-download-btn"),
    modal: document.getElementById("modalContainer"),
    downloadBtn: document.getElementById("downloadBtn"),
    idEleve: document.getElementById('id_id_eleve'),

  };

  if (!fields.idAnnee || !fields.trimestreTable) {
    console.error("Éléments requis manquants pour /generer_excel_file/");
    return;
  }

  hideFields(
    fields.idCampus,
    fields.idClasseCycle,
    fields.idClasse,
    fields.coursField,
    fields.evaluationField,
    fields.jrField,
    fields.horaireTypeField,
    fields.periodeField,
    fields.typeNoteField,
    fields.idEleve
  );
  fields.trimestreTable.style.display = "none";

  const savedAnnee = getFromSession("id_annee");
  if (savedAnnee && fields.idAnnee) {
    fields.idAnnee.value = savedAnnee;
    updateDropdown(
      `/get_all_classes_by_evaluations?id_annee=${savedAnnee}`,
      fields.idClasse,
      "id",
      "label"
    );
  }

  fields.idAnnee?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.idClasse,
      fields.coursField,
      fields.evaluationField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.typeNoteField,
      fields.idEleve


    );
    fields.trimestreTable.style.display = "none";
    if (this.value) {
      saveToSession("id_annee", this.value);
      document.getElementById("id_id_annee").value = this.value;
      updateDropdown(
        `/get_all_classes_by_evaluations?id_annee=${this.value}`,
        fields.idClasse,
        "id",
        "label"
      );
    }
  });

  fields.idClasse?.addEventListener("change", function () {
    const selectedOption = this.options[this.selectedIndex];
    const campusId = selectedOption.dataset.campus;
    const cycleId = selectedOption.dataset.cycle;
    const classeId = this.value;
    const anneeId = fields.idAnnee.value;

    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.coursField,
      fields.evaluationField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.typeNoteField,
      fields.idEleve

    );
    fields.trimestreTable.style.display = "none";

    if (classeId && campusId && cycleId) {
      const selectedData = { id_campus: campusId, id_cycle: cycleId, id_classe: classeId };
      saveToSession("selected_classe_data", JSON.stringify(selectedData));

      document.getElementById("id_id_campus").value = campusId;
      document.getElementById("id_id_cycle_actif").value = cycleId;
      document.getElementById("id_id_classe_active").value = classeId;

      const url = `/get_cours_by_classe_Evaluataion/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe=${classeId}`;
      fetch(url)
        .then((response) => response.json())
        .then((responseData) => {
          const data = responseData.cours_list || responseData || [];
          fields.coursField.innerHTML = '<option value="">------</option>';
          if (data.length > 0) {
            data.forEach((item) => {
              const option = document.createElement("option");
              option.value = item.id;
              option.textContent = item.label;
              fields.coursField.appendChild(option);
            });
            showField(fields.coursField);
          } else {
            console.log("Aucun cours trouvé");
          }
        })
        .catch((error) => console.error("Erreur lors du chargement des cours :", error));
    }
  });

  fields.coursField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;
    const coursId = this.value;

    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.evaluationField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.typeNoteField,
      fields.idEleve

    );
    fields.trimestreTable.style.display = "none";

    if (campusId && cycleId && classeId) {
      document.getElementById("id_id_campus").value = campusId;
      document.getElementById("id_id_cycle_actif").value = cycleId;
      document.getElementById("id_id_classe_active").value = classeId;
    }

    if (coursId && campusId && cycleId && classeId && anneeId) {
      saveToSession("id_cours", coursId);
      fields.coursField.parentElement.after(fields.typeNoteField.parentElement);
      const url = `/get_types_notes_par_evaluation/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}&id_cours=${coursId}`;
      updateDropdown(url, fields.typeNoteField, "id", "label").then((result) => {
        if (!result.hasData) {
          // No type notes found — close modal and show download action
          if (fields.modal) fields.modal.style.display = "none";
          fields.trimestreTable.style.display = "block";
        }
      });
    }
  });

  fields.typeNoteField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;
    const coursId = fields.coursField.value;
    const typeNoteId = this.value;

    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.evaluationField,
      fields.jrField,
      fields.periodeField,
      fields.idEleve

    );
    fields.trimestreTable.style.display = "none";

    if (campusId && cycleId && classeId) {
      document.getElementById("id_id_campus").value = campusId;
      document.getElementById("id_id_cycle_actif").value = cycleId;
      document.getElementById("id_id_classe_active").value = classeId;
    }

    if (typeNoteId && coursId && campusId && cycleId && classeId && anneeId) {
      saveToSession("id_type_note", typeNoteId);
      const url = `/get_trimestre_by_evaluation/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}&id_cours=${coursId}&id_type_note=${typeNoteId}`;
      updateDropdown(url, fields.horaireTypeField, "id", "label").then((result) => {
        if (!result.hasData) {
          if (fields.modal) fields.modal.style.display = "none";
          fields.trimestreTable.style.display = "block";
        }
      });
    }
  });

  fields.horaireTypeField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;
    const coursId = fields.coursField.value;
    const typeNoteId = fields.typeNoteField.value;
    const trimestreId = this.value;

    hideFields(fields.idCampus, fields.idClasseCycle, fields.evaluationField, fields.jrField, fields.idEleve);
    fields.trimestreTable.style.display = "none";

    if (campusId && cycleId && classeId) {
      document.getElementById("id_id_campus").value = campusId;
      document.getElementById("id_id_cycle_actif").value = cycleId;
      document.getElementById("id_id_classe_active").value = classeId;
    }

    if (trimestreId && typeNoteId && coursId && campusId && cycleId && classeId && anneeId) {
      saveToSession("id_trimestre", trimestreId);
      const url = `/get_periode_by_trimestre_coursEvaluer/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}&id_cours=${coursId}&id_type_note=${typeNoteId}&id_trimestre=${trimestreId}`;
      updateDropdown(url, fields.periodeField, "id", "label").then((result) => {
        if (!result.hasData) {
          if (fields.modal) fields.modal.style.display = "none";
          fields.trimestreTable.style.display = "block";
        }
      });
    }
  });

  fields.periodeField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;
    const coursId = fields.coursField.value;
    const typeNoteId = fields.typeNoteField.value;
    const trimestreId = fields.horaireTypeField.value;
    const periodeId = this.value;

    hideFields(fields.idCampus, fields.idClasseCycle, fields.evaluationField, fields.idEleve, fields.jrField);

    if (campusId && cycleId && classeId) {
      document.getElementById("id_id_campus").value = campusId;
      document.getElementById("id_id_cycle_actif").value = cycleId;
      document.getElementById("id_id_classe_active").value = classeId;
    }

    if (periodeId && trimestreId && typeNoteId && coursId && campusId && cycleId && classeId && anneeId) {
      saveToSession("id_periode", periodeId);
      fields.periodeField.parentElement.after(fields.jrField.parentElement);
      const url = `/get_sessions_par_coursEvaluer/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}&id_cours=${coursId}&id_type_note=${typeNoteId}&id_trimestre=${trimestreId}&id_periode=${periodeId}`;
      updateDropdown(url, fields.jrField, "id", "label").then((result) => {
        if (!result.hasData) {
          if (fields.modal) fields.modal.style.display = "none";
          fields.trimestreTable.style.display = "block";
        }
      });
    }
  });

  fields.jrField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;
    const coursId = fields.coursField.value;
    const typeNoteId = fields.typeNoteField.value;
    const trimestreId = fields.horaireTypeField.value;
    const periodeId = fields.periodeField.value;
    const sessionId = this.value;

    hideFields(fields.idCampus, fields.idEleve, fields.idClasseCycle, fields.evaluationField);

    if (sessionId && periodeId && trimestreId && typeNoteId && coursId && campusId && cycleId && classeId && anneeId) {
      saveToSession("id_session", sessionId);
      const url = `/get_evaluations_by_cours_select/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}&id_cours=${coursId}&id_type_note=${typeNoteId}&id_trimestre=${trimestreId}&id_periode=${periodeId}&id_session=${sessionId}`;
      fetch(url)
        .then((response) => {
          if (!response.ok) throw new Error("Erreur réseau ou serveur");
          return response.json();
        })
        .then((responseData) => {
          const data = responseData.data || [];
          fields.evaluationField.innerHTML = '<option value="">------</option>';
          if (data.length > 0) {
            data.forEach((item) => {
              const option = document.createElement("option");
              option.value = item.id;
              option.textContent = item.label;
              fields.evaluationField.appendChild(option);
            });
            showField(fields.evaluationField);
          } else {
            alert("Désolé, vous ne pouvez pas générer une fiche 2 fois pour une seule évaluation");
            window.location.href = "/generer_excel_file";
          }
        })
        .catch((error) => console.error("Erreur lors du chargement des évaluations :", error));
    }
  });

  fields.evaluationField?.addEventListener("change", function () {
    hideFields(fields.idCampus, fields.idEleve, fields.idClasseCycle);
    if (this.value) {
      saveToSession("id_evaluation", this.value);
      if (fields.modal) fields.modal.style.display = "none";
      fields.trimestreTable.style.display = "block";
    } else {
      fields.trimestreTable.style.display = "none";
      if (fields.modal) fields.modal.style.display = "block";
    }
  });

  if (fields.downloadBtn) {
    fields.downloadBtn.addEventListener("click", function (event) {
      event.preventDefault();
      const id_annee = getFromSession("id_annee");
      const selected_classe_data = JSON.parse(getFromSession("selected_classe_data") || "{}");
      const id_cours = getFromSession("id_cours");
      const id_type_note = getFromSession("id_type_note");
      const id_trimestre = getFromSession("id_trimestre");
      const id_periode = getFromSession("id_periode");
      const id_session = getFromSession("id_session");
      const id_evaluation = getFromSession("id_evaluation");

      if (
        id_annee &&
        selected_classe_data.id_classe &&
        selected_classe_data.id_campus &&
        selected_classe_data.id_cycle &&
        id_cours &&
        id_type_note &&
        id_trimestre &&
        id_periode &&
        id_session && id_evaluation
      ) {
        document.getElementById("form_id_annee").value = id_annee;
        document.getElementById("form_id_campus").value = selected_classe_data.id_campus;
        document.getElementById("form_id_cycle").value = selected_classe_data.id_cycle;
        document.getElementById("form_id_classe").value = selected_classe_data.id_classe;
        document.getElementById("form_id_cours").value = id_cours;
        document.getElementById("form_id_type_note").value = id_type_note;
        document.getElementById("form_id_trimestre").value = id_trimestre;
        document.getElementById("form_id_periode").value = id_periode;
        document.getElementById("form_id_session").value = id_session;
        document.getElementById("form_id_evaluation").value = id_evaluation;

        document.getElementById("downloadForm").submit();
      } else {
        alert("Veuillez sélectionner toutes les options avant de télécharger.");
      }
    });
  }
};

// Logique pour /Affichage_notes:

const setupAffichageNotes = () => {
  const fields = {
    idAnnee: document.getElementById("id_id_annee"),
    idCampus: document.getElementById("id_id_campus"),
    idClasseCycle: document.getElementById("id_id_cycle_actif"),
    idClasse: document.getElementById("id_id_classe_active"),
    coursField: document.getElementById("id_id_cours_classe"),
    titleField: document.getElementById("id_title"),
    debutField: document.getElementById("id_ponderer_eval"),
    finField: document.getElementById("id_date_eval"),
    jrField: document.getElementById("id_id_session"),
    horaireTypeField: document.getElementById("id_id_trimestre"),
    periodeField: document.getElementById("id_id_periode"),
    contenuField: document.getElementById("id_contenu_evaluation"),
    dateSoumField: document.getElementById("id_date_soumission"),
    typeNoteField: document.getElementById("id_id_type_note"),
    trimestreTable: document.getElementById("btnsubmit"),
    modal: document.getElementById("modalContainer"),
    formtitleField: document.getElementById("form_title"),
    formIdAnnee: document.getElementById("form_id_annee"),
    formIdCampus: document.getElementById("form_id_campus"),
    formIdCycle: document.getElementById("form_id_cycle"),
    formIdClasse: document.getElementById("form_id_classe"),
    formCoursField: document.getElementById("form_id_cours"),
    formDebutField: document.getElementById("form_ponderer_eval"),
    formFinField: document.getElementById("form_date_eval"),
    formJrField: document.getElementById("form_id_session"),
    formHoraireTypeField: document.getElementById("form_id_trimestre"),
    formPeriodeField: document.getElementById("form_id_periode"),
    formDateSoumField: document.getElementById("form_date_soumission"),
    formTypeNoteField: document.getElementById("form_id_type_note"),
  };
  fields.trimestreTable.style.display = "none";


  // if (!fields.idAnnee) {
  //   console.error("Éléments requis manquants pour /affichage_notes/");
  //   return;
  // }

  // Initialisation
  hideFields(
    fields.idCampus,
    fields.idClasseCycle,
    fields.idClasse,
    fields.coursField,
    fields.debutField,
    fields.finField,
    fields.jrField,
    fields.horaireTypeField,
    fields.periodeField,
    fields.contenuField,
    fields.dateSoumField,
    fields.titleField,
    fields.typeNoteField
  );

  const savedAnnee = getFromSession("id_annee");
  if (savedAnnee && fields.idAnnee) {
    fields.idAnnee.value = savedAnnee;
    fields.formIdAnnee.value = savedAnnee;
    updateDropdown(
      `/get_all_classes_with_notes?id_annee=${savedAnnee}`,
      fields.idClasse,
      "id",
      "label"
    );
  }

  // Événements
  fields.idAnnee?.addEventListener("change", function () {
    hideFields(
      fields.idClasse,
      fields.coursField,
      fields.typeNoteField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.jrField
    );
    if (this.value) {
      saveToSession("id_annee", this.value);
      fields.idAnnee.value = this.value;
      fields.formIdAnnee.value = this.value;
      fields.trimestreTable.style.display = "none";

      updateDropdown(
        `/get_all_classes_with_notes?id_annee=${this.value}`,
        fields.idClasse,
        "id",
        "label"
      );
    }
  });

  fields.idClasse?.addEventListener("change", function () {
    const selectedOption = this.options[this.selectedIndex];
    const campusId = selectedOption.dataset.campus;
    const cycleId = selectedOption.dataset.cycle;
    const classeId = this.value;
    const anneeId = fields.idAnnee.value;
    fields.trimestreTable.style.display = "none";


    hideFields(
      fields.coursField,
      fields.typeNoteField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.jrField,
    );
    if (campusId && cycleId && classeId) {
      document.getElementById("id_id_campus").value = campusId;
      document.getElementById("id_id_cycle_actif").value = cycleId;
      document.getElementById("id_id_classe_active").value = classeId;
    }

    if (classeId && campusId && cycleId) {
      const selectedData = { id_campus: campusId, id_cycle: cycleId, id_classe: classeId };
      saveToSession("selected_classe_data", JSON.stringify(selectedData));

      fields.formIdCampus.value = campusId;
      fields.formIdCycle.value = cycleId;
      fields.formIdClasse.value = classeId;

      updateDropdown(
        `/get_cours_notes_by_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe=${classeId}`,
        fields.coursField,
        "id",
        "label"
      );
    }
  });

  fields.coursField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;


    hideFields(
      fields.typeNoteField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.jrField
    );
    if (this.value && campusId && cycleId && classeId && anneeId) {
      saveToSession("id_cours", this.value);
      fields.formCoursField.value = this.value;
      fields.trimestreTable.style.display = "none";


      updateDropdown(
        `/get_notes_type_with_notes/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}&id_cours_classe=${this.value}`,
        fields.typeNoteField,
        "id",
        "label"
      );
    }
  });

  fields.typeNoteField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;
    const coursId = fields.coursField.value;


    hideFields(
      fields.horaireTypeField,
      fields.periodeField,
      fields.jrField
    );
    fields.trimestreTable.style.display = "none";

    if (this.value && coursId && campusId && cycleId && classeId && anneeId) {
      saveToSession("id_type_note", this.value);
      fields.formTypeNoteField.value = this.value;
      const anneeId = fields.idAnnee.value;
      const campusId = fields.formIdCampus.value;
      const cycleId = fields.formIdCycle.value;
      const classeId = fields.formIdClasse.value;
      updateDropdown(
        `/get_trimestres_notes_par_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe=${classeId}&&id_cours=${coursId}&id_type_note=${this.value}`,
        fields.horaireTypeField,
        "id",
        "label"
      ).then((result) => {
        if (!result.hasData) {
          // No trimestres with notes — show table directly
          document.getElementById("AffichageNote")?.classList.remove("hidden");
          if (fields.modal) fields.modal.style.display = "none";
        }
      });
    }
  });

  fields.horaireTypeField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;
    const coursId = fields.coursField.value;
    hideFields(
      fields.periodeField,
      fields.jrField
    );
    if (this.value && coursId && campusId && cycleId && classeId && anneeId) {
      saveToSession("id_trimestre", this.value);
      fields.formHoraireTypeField.value = this.value;
      const anneeId = fields.idAnnee.value;
      const campusId = fields.formIdCampus.value;
      const cycleId = fields.formIdCycle.value;
      const classeId = fields.formIdClasse.value;
      const coursId = fields.coursField.value;
      const typeNoteId = fields.typeNoteField.value;


      updateDropdown(
        `/get_periode_notes_par_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe=${classeId}&id_cours=${coursId}&id_type_note=${typeNoteId}&id_trimestre=${this.value}`,
        fields.periodeField,
        "id",
        "label"
      ).then((result) => {
        if (!result.hasData) {
          document.getElementById("AffichageNote")?.classList.remove("hidden");
          if (fields.modal) fields.modal.style.display = "none";
        }
      });
    }
  });

  fields.periodeField?.addEventListener("change", function () {
    const selectedClasseData = JSON.parse(getFromSession("selected_classe_data") || "{}");
    const campusId = selectedClasseData.id_campus;
    const cycleId = selectedClasseData.id_cycle;
    const classeId = selectedClasseData.id_classe;
    const anneeId = fields.idAnnee.value;
    const coursId = fields.coursField.value;
    const typeNoteId = fields.typeNoteField.value;
    const trimestreId = fields.horaireTypeField.value;



    hideFields(fields.jrField);
    if (this.value && coursId && campusId && cycleId && classeId && anneeId && typeNoteId) {
      saveToSession("id_periode", this.value);
      fields.periodeField.parentElement.after(fields.jrField.parentElement);
      const url = `/get_session_notes_par_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}&id_cours=${coursId}&id_type_note=${typeNoteId}&id_trimestre=${trimestreId}&id_periode=${this.value}`;
      fields.formPeriodeField.value = this.value;
      updateDropdown(
        url,
        fields.jrField,
        "id",
        "label"
      ).then((result) => {
        if (!result.hasData) {
          document.getElementById("AffichageNote")?.classList.remove("hidden");
          if (fields.modal) fields.modal.style.display = "none";
        }
      });
    }
  });


  fields.jrField?.addEventListener("change", function () {
    if (this.value) {
      saveToSession("id_session", this.value);
      fields.formJrField.value = this.value;

      const anneeId = fields.idAnnee.value;
      const campusId = fields.formIdCampus.value;
      const cycleId = fields.formIdCycle.value;
      const classeId = fields.idClasse.value;
      const trimestreId = fields.horaireTypeField.value;
      const periodeId = fields.periodeField.value;
      const sessionId = this.value;
      const coursId = fields.coursField.value;
      const typeNoteId = fields.typeNoteField.value;

      // Récupérer les élèves
      const pupilsUrl = `/get_pupils_registred_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}`;
      fetch(pupilsUrl)
        .then((response) => response.json())
        .then((pupilsData) => {
          const pupils = pupilsData.data || pupilsData || [];
          if (pupils.length === 0) {
            console.warn("Aucun élève trouvé");
            fields.modal.style.display = "none";
            document.getElementById("AffichageNote").classList.remove("hidden");
            document.getElementById("AffichageNoteTbody").innerHTML = "<tr><td colspan='5'>Aucun élève trouvé</td></tr>";
            return;
          }

          // Récupérer les notes
          const notesUrl = `/get_notes_by_selection/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle_actif=${cycleId}&id_classe_active=${classeId}&id_trimestre=${trimestreId}&id_periode=${periodeId}&id_session=${sessionId}&id_cours_classe=${coursId}&id_type_note=${typeNoteId}`;
          fetch(notesUrl)
            .then((response) => response.json())
            .then((notesData) => {
              const notes = notesData.data || notesData || [];
              const tbody = document.getElementById("AffichageNoteTbody");
              tbody.innerHTML = "";

              const notesByType = {};
              notes.forEach((note) => {
                const key = `${note.id_type_note}_${note.id_cours_classe}_${note.id_evaluation}`;
                if (!notesByType[key]) {
                  notesByType[key] = {
                    type: note.type,
                    ponderer_eval: parseFloat(note.ponderer_eval) || 20,
                    notes: [],
                  };
                }
                notesByType[key].notes.push(note);
              });

              // Créer les colonnes dynamiques
              const typeColumns = Object.values(notesByType);
              const thead = document.querySelector("#evaluationsTable thead tr");
              thead.innerHTML = "<th>Nom et prénom</th>";
              if (typeColumns.length === 0) {
                thead.innerHTML += "<th>Notes</th>";
              } else {
                typeColumns.forEach((typeData, index) => {
                  const typeName = typeData.type || `Type ${index + 1}`;
                  const ponderation = typeData.ponderer_eval || 20;
                  thead.innerHTML += `<th>${typeName}/${ponderation}</th>`;
                });
              }
              thead.innerHTML += "<th>Titre évaluation</th><th>Total</th><th>Actions</th>";

              // Grouper les notes par élève
              const notesByEleve = {};
              notes.forEach((note) => {
                if (!notesByEleve[note.id_eleve]) {
                  notesByEleve[note.id_eleve] = [];
                }
                notesByEleve[note.id_eleve].push(note);
              });

              // Construire les lignes du tableau
              pupils.forEach((eleve) => {
                const row = document.createElement("tr");
                const fullName = eleve.nom_complet ? sanitize(eleve.nom_complet) : '';
                //const nomPrenom = `${eleve.nom} ${eleve.prenom}`;
                row.innerHTML = `<td>${fullName}</td>`;

                let total = 0;
                let ponderationTotale = 0;
                let titreEvaluation = "";

                if (typeColumns.length === 0) {
                  row.innerHTML += "<td></td>";
                } else {
                  typeColumns.forEach((typeData) => {
                    const note = notesByEleve[eleve.id_eleve]?.find(
                      (n) =>
                        n.id_type_note === typeData.notes[0]?.id_type_note &&
                        n.id_cours_classe === typeData.notes[0]?.id_cours_classe &&
                        n.id_evaluation === typeData.notes[0]?.id_evaluation
                    );
                    if (note) {
                      const noteValue = parseFloat(note.note) || parseFloat(note.note_repechage) || 0;
                      row.innerHTML += `<td>${noteValue ? noteValue.toFixed(2) + "/" + typeData.ponderer_eval : ""}</td>`;
                      total += noteValue;
                      ponderationTotale += typeData.ponderer_eval;
                      titreEvaluation = note.title || titreEvaluation;
                    } else {
                      row.innerHTML += "<td></td>";
                    }
                  });
                }

                row.innerHTML += `<td>${titreEvaluation}</td>`;
                row.innerHTML += `<td>${total.toFixed(2)}/${ponderationTotale}</td>`;
                row.innerHTML += `<td><button class="btn btn-sm btn-primary" style="display:none" onclick="editNote(${eleve.id})">Éditer</button></td>`;

                tbody.appendChild(row);
              });

              // Afficher le tableau et masquer le modal
              document.getElementById("AffichageNote").classList.remove("hidden");
              fields.modal.style.display = "none";
            })
            .catch((error) => {
              console.error("Erreur lors du chargement des notes :", error);
              document.getElementById("AffichageNote").classList.remove("hidden");
              document.getElementById("AffichageNoteTbody").innerHTML = "<tr><td colspan='5'>Erreur lors du chargement des notes</td></tr>";
              fields.modal.style.display = "none";
            });
        })
        .catch((error) => {
          console.error("Erreur lors du chargement des élèves :", error);
          document.getElementById("AffichageNote").classList.remove("hidden");
          document.getElementById("AffichageNoteTbody").innerHTML = "<tr><td colspan='5'>Aucun élève trouvé</td></tr>";
          fields.modal.style.display = "none";
        });
    }
  });
  // Fonction pour générer le PDF
  window.generatePDF = function () {
    const anneeId = fields.idAnnee.value;
    const campusId = fields.formIdCampus.value;
    const cycleId = fields.formIdCycle.value;
    const classeId = fields.idClasse.value;
    const trimestreId = fields.horaireTypeField.value;
    const periodeId = fields.periodeField.value;
    const sessionId = fields.jrField.value;
    const coursId = fields.coursField.value;
    const typeNoteId = fields.typeNoteField.value;

    // Construire l'URL pour générer le PDF
    const pdfUrl = `/generate_notes_pdf/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle_actif=${cycleId}&id_classe_active=${classeId}&id_trimestre=${trimestreId}&id_periode=${periodeId}&id_session=${sessionId}&id_cours_classe=${coursId}&id_type_note=${typeNoteId}`;

    // Rediriger vers l'URL pour télécharger le PDF
    window.location.href = pdfUrl;
  };

};


// Logique pour /add_evaluation/
const setupAddEvaluation = () => {
  const fields = {
    idAnnee: document.getElementById("id_id_annee"),
    idCampus: document.getElementById("id_id_campus"),
    idClasseCycle: document.getElementById("id_id_cycle_actif"),
    idClasse: document.getElementById("id_id_classe_active"),
    coursField: document.getElementById("id_id_cours_classe"),
    titleField: document.getElementById("id_title"),
    debutField: document.getElementById("id_ponderer_eval"),
    finField: document.getElementById("id_date_eval"),
    jrField: document.getElementById("id_id_session"),
    horaireTypeField: document.getElementById("id_id_trimestre"),
    periodeField: document.getElementById("id_id_periode"),
    contenuField: document.getElementById("id_contenu_evaluation"),
    dateSoumField: document.getElementById("id_date_soumission"),
    typeNoteField: document.getElementById("id_id_type_note"),
    trimestreTable: document.getElementById("btnsubmit"),
    modal: document.getElementById("modalContainer"),
    formtitleField: document.getElementById("form_title"),
    formIdAnnee: document.getElementById("form_id_annee"),
    formIdCampus: document.getElementById("form_id_campus"),
    formIdCycle: document.getElementById("form_id_cycle"),
    formIdClasse: document.getElementById("form_id_classe"),
    formCoursField: document.getElementById("form_id_cours"),
    formDebutField: document.getElementById("form_ponderer_eval"),
    formFinField: document.getElementById("form_date_eval"),
    formJrField: document.getElementById("form_id_session"),
    formHoraireTypeField: document.getElementById("form_id_trimestre"),
    formPeriodeField: document.getElementById("form_id_periode"),
    formDateSoumField: document.getElementById("form_date_soumission"),
    formTypeNoteField: document.getElementById("form_id_type_note"),
  };
  const isDevoir = window.location.pathname.includes("/soumettre_devoir/");


  if (!fields.idAnnee || !fields.trimestreTable) {
    console.error("Éléments requis manquants pour /add_evaluation/");
    return;
  }

  // Initialisation
  hideFields(
    fields.idCampus,
    fields.idClasseCycle,
    fields.idClasse,
    fields.coursField,
    fields.debutField,
    fields.finField,
    fields.jrField,
    fields.horaireTypeField,
    fields.periodeField,
    fields.contenuField,
    fields.dateSoumField,
    fields.titleField,
    fields.typeNoteField
  );
  fields.trimestreTable.style.display = "none";

  const savedAnnee = getFromSession("id_annee");
  if (savedAnnee && fields.idAnnee) {
    fields.idAnnee.value = savedAnnee;
    fields.formIdAnnee.value = savedAnnee;
    updateDropdown(
      `/classes_by_year_without_deliberate_annual?id_annee=${savedAnnee}`,
      fields.idClasse,
      "id",
      "label"
    );
  }

  // Événements
  fields.idAnnee?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.idClasse,
      fields.coursField,
      fields.debutField,
      fields.finField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.contenuField,
      fields.dateSoumField,
      fields.titleField,
      fields.typeNoteField
    );
    fields.trimestreTable.style.display = "none";
    if (this.value) {
      saveToSession("id_annee", this.value);
      fields.idAnnee.value = this.value;
      fields.formIdAnnee.value = this.value;
      updateDropdown(
        `/get_all_classes_by_year?id_annee=${this.value}`,
        fields.idClasse,
        "id",
        "label"
      );
    }
  });

  fields.idClasse?.addEventListener("change", function () {
    const selectedOption = this.options[this.selectedIndex];
    const campusId = selectedOption.dataset.campus;
    const cycleId = selectedOption.dataset.cycle;
    const classeId = this.value;
    const anneeId = fields.idAnnee.value;

    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.coursField,
      fields.debutField,
      fields.finField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.contenuField,
      fields.dateSoumField,
      fields.titleField,
      fields.typeNoteField
    );
    fields.trimestreTable.style.display = "none";

    if (classeId && campusId && cycleId) {
      const selectedData = { id_campus: campusId, id_cycle: cycleId, id_classe: classeId };
      saveToSession("selected_classe_data", JSON.stringify(selectedData));

      fields.idCampus.value = campusId;
      fields.idClasseCycle.value = cycleId;
      fields.idClasse.value = classeId;
      fields.formIdCampus.value = campusId;
      fields.formIdCycle.value = cycleId;
      fields.formIdClasse.value = classeId;

      const url = `/get_cours_by_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe=${classeId}`;
      fetch(url)
        .then((response) => response.json())
        .then((responseData) => {
          const data = responseData.data || responseData || [];
          fields.coursField.innerHTML = '<option value="">------</option>';
          if (data.length > 0) {
            data.forEach((item) => {
              const option = document.createElement("option");
              option.value = item.id;
              option.textContent = item.label;
              fields.coursField.appendChild(option);
            });
            showField(fields.coursField);
          } else {
            console.log("Aucun cours trouvé");
          }
        })
        .catch((error) => console.error("Erreur lors du chargement des cours :", error));
    }
  });

  fields.coursField?.addEventListener("change", function () {
    //console.log(this.value)
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.debutField,
      fields.finField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.contenuField,
      fields.dateSoumField,
      fields.titleField,
      fields.typeNoteField
    );
    fields.trimestreTable.style.display = "none";
    if (this.value) {
      const url = isDevoir
        ? `/get_types_notes_devoir` :
        `/get_types_notes/`
        ;
      saveToSession("id_cours", this.value);
      fields.formCoursField.value = this.value;
      fields.coursField.parentElement.after(fields.typeNoteField.parentElement);

      updateDropdown(url, fields.typeNoteField, "id", "label");
    }
  });

  fields.typeNoteField?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.debutField,
      fields.finField,
      fields.jrField,
      fields.periodeField,
      fields.contenuField,
      fields.titleField,
      fields.dateSoumField
    );
    fields.trimestreTable.style.display = "none";
    if (this.value) {
      saveToSession("id_type_note", this.value);
      fields.formTypeNoteField.value = this.value;
      const anneeId = fields.idAnnee.value;
      const campusId = fields.idCampus.value;
      const cycleId = fields.idClasseCycle.value;
      const classeId = fields.idClasse.value;
      const url = `/get_trimestres_par_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe=${classeId}`;

      updateDropdown(url, fields.horaireTypeField, "id", "label").then((result) => {
        if (!result.hasData) {
          // No trimestres found — show submit button so user isn't stuck
          fields.trimestreTable.style.display = "block";
          if (fields.modal) fields.modal.style.display = "none";
        }
      });
    }
  });

  fields.horaireTypeField?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.debutField,
      fields.finField,
      fields.jrField,
      fields.contenuField,
      fields.titleField,
      fields.dateSoumField
    );
    fields.trimestreTable.style.display = "none";
    if (this.value) {
      saveToSession("id_trimestre", this.value);
      fields.formHoraireTypeField.value = this.value;
      const anneeId = fields.idAnnee.value;
      const campusId = fields.idCampus.value;
      const cycleId = fields.idClasseCycle.value;
      const classeId = fields.idClasse.value;
      const url = `/get_periodes_par_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe=${classeId}&id_trimestre=${this.value}`;

      updateDropdown(
        url,
        fields.periodeField,
        "id",
        "label"
      ).then((result) => {
        if (!result.hasData) {
          fields.trimestreTable.style.display = "block";
          if (fields.modal) fields.modal.style.display = "none";
        }
      });
    }
  });

  fields.periodeField?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.debutField,
      fields.finField,
      fields.jrField,
      fields.contenuField,
      fields.titleField,
      fields.dateSoumField
    );
    if (this.value) {
      saveToSession("id_periode", this.value);
      fields.formPeriodeField.value = this.value;
      fields.periodeField.parentElement.after(fields.jrField.parentElement);
      updateDropdown("/get_all_sessions_without_repechage/", fields.jrField, "id", "label").then((result) => {
        if (!result.hasData) {
          fields.trimestreTable.style.display = "block";
          if (fields.modal) fields.modal.style.display = "none";
        }
      });
    }
  });

  fields.jrField?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.contenuField,
      fields.debutField,
      fields.titleField,
      fields.finField,
      fields.dateSoumField
    );
    if (this.value) {
      saveToSession("id_session", this.value);
      fields.formJrField.value = this.value;
      fields.jrField.parentElement.after(fields.finField.parentElement);
      showField(fields.finField);
    }
  });

  fields.finField?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.debutField,
      fields.contenuField,
      fields.titleField,
      fields.dateSoumField
    );
    if (this.value) {
      saveToSession("date_eval", this.value);
      fields.formFinField.value = this.value;
      fields.finField.parentElement.after(fields.contenuField.parentElement);
      showField(fields.contenuField);
    }
  });

  fields.contenuField?.addEventListener("change", function () {
    hideFields(fields.idCampus, fields.idClasseCycle, fields.debutField, fields.titleField, fields.dateSoumField);
    if (this.files && this.files.length > 0) {
      saveToSession("contenu_evaluation", this.files[0].name);
      console.log("Fichier sélectionné:", this.files[0].name);
      fields.contenuField.parentElement.after(fields.dateSoumField.parentElement);
      showField(fields.dateSoumField);
    } else {
      console.warn("Aucun fichier sélectionné");
    }
  });

  fields.dateSoumField?.addEventListener("change", function () {
    hideFields(fields.idCampus, fields.idClasseCycle, fields.titleField, fields.debutField);
    if (this.value) {
      saveToSession("date_soumission", this.value);
      fields.formDateSoumField.value = this.value;
      fields.dateSoumField.parentElement.after(fields.titleField.parentElement);
      showField(fields.titleField);
    }
  });

  fields.titleField?.addEventListener("change", function () {
    hideFields(fields.idCampus, fields.idClasseCycle, fields.debutField);
    if (this.value) {
      saveToSession("title", this.value);
      fields.formtitleField.value = this.value;
      fields.titleField.parentElement.after(fields.debutField.parentElement);
      showField(fields.debutField);
    }
  });

  fields.debutField?.addEventListener("change", function () {
    hideFields(fields.idCampus, fields.idClasseCycle);
    if (this.value) {
      saveToSession("ponderer_eval", this.value);
      fields.formDebutField.value = this.value;
      fields.trimestreTable.style.display = "block";
    }
  });

  fields.idCampus?.addEventListener("change", function () {
    if (this.value) {
      saveToSession("id_campus", this.value);
      fields.formIdCampus.value = this.value;
    }
  });

  document.querySelector("form")?.addEventListener("submit", function (e) {
    if (!fields.formIdCampus.value || !fields.formIdCycle.value || !fields.contenuField.files.length) {
      e.preventDefault();
      alert("Veuillez remplir tous les champs requis, y compris le fichier d'évaluation.");
    } else {
      console.log("Form submitted with values:", {
        annee: fields.formIdAnnee.value,
        campus: fields.formIdCampus.value,
        cycle: fields.formIdCycle.value,
        fichier: fields.contenuField.files[0]?.name,
      });
    }
  });
};

// Logique pour /generer_bulletin_eleve/
const setupBulletinEleve = () => {
  const fields = {
    idAnnee: document.getElementById("id_id_annee"),
    idCampus: document.getElementById("id_id_campus"),
    idClasseCycle: document.getElementById("id_id_cycle_actif"),
    idClasse: document.getElementById("id_id_classe_active"),
    coursField: document.getElementById("id_id_cours_classe"),
    jrField: document.getElementById("id_id_session"),
    horaireTypeField: document.getElementById("id_id_trimestre"),
    periodeField: document.getElementById("id_id_periode"),
    typeNoteField: document.getElementById("id_id_type_note"),
    evaluationField: document.getElementById("id_id_evaluation"),
    trimestreTable: document.getElementById("table-download-btn"),
    elevesContainer: document.getElementById("table-display-pupils"),
    tableContent: document.querySelector("#table-display-pupils .table-responsive"),
    modal: document.getElementById("modalContainer"),
    idEleve: document.getElementById('id_id_eleve'),

  };

  if (!fields.idAnnee || !fields.elevesContainer || !fields.tableContent) {
    console.error("Éléments requis manquants pour /generer_bulletin_eleve/");
    return;
  }

  const loadRegisteredPupils = (anneeId, campusId, cycleId, classeId) => {
    const url = `/get_pupils_registred_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}`;
    fetch(url)
      .then((response) => response.json())
      .then((data) => {
        const pupils = data.data || data || [];
        const selectedOption = fields.idClasse.options[fields.idClasse.selectedIndex];
        const className = selectedOption.textContent;
        const tableHeader = fields.elevesContainer.querySelector(".table-header h3");
        if (tableHeader) {
          tableHeader.textContent = `LISTE DES ELEVES INSCRITS DANS LA CLASSE ${className}`;
        }

        let html = `
                <div class="mb-3 text-end">
                    <button id="btn-generate-selected" class="btn btn-success" disabled>
                        📄 Générer les bulletins sélectionnés (<span id="selected-count">0</span>)
                    </button>
                </div>

                <table id="basic-datatables" class="display table table-striped table-hover">
                    <thead>
                        <tr>
                            <th style="width: 40px;"><input type="checkbox" id="select-all"></th>
                            <th>Selectionner tous les bulletins à la fois</th>
                        </tr>
                    </thead>
                    <tbody>`;

        if (pupils.length > 0) {
          pupils.forEach((pupil) => {
            const fullName = pupil.nom_complet ? sanitize(pupil.nom_complet) : '';
            html += `
                        <tr data-eleve-id="${pupil.id_eleve}">
                            <td>
                                <input type="checkbox" class="eleve-checkbox" value="${pupil.id_eleve}">
                            </td>
                            <td>${fullName}</td>
                        </tr>`;
          });
        } else {
          html += `
                    <tr>
                        <td colspan="2" class="text-center text-muted">Aucun élève trouvé.</td>
                    </tr>`;
        }

        html += `</tbody></table>`;
        fields.tableContent.innerHTML = html;
        fields.elevesContainer.style.display = "block";
        if (fields.modal) fields.modal.style.display = "none";


        const selectAll = document.getElementById("select-all");
        const checkboxes = document.querySelectorAll(".eleve-checkbox");
        const btnGenerate = document.getElementById("btn-generate-selected");
        const countSpan = document.getElementById("selected-count");

        const updateCount = () => {
          const checked = document.querySelectorAll(".eleve-checkbox:checked").length;
          countSpan.textContent = checked;
          btnGenerate.disabled = checked === 0;
        };

        selectAll.addEventListener("change", () => {
          checkboxes.forEach(cb => cb.checked = selectAll.checked);
          updateCount();
        });

        checkboxes.forEach(cb => {
          cb.addEventListener("change", () => {
            if (!cb.checked) selectAll.checked = false;
            else if (document.querySelectorAll(".eleve-checkbox:checked").length === checkboxes.length) {
              selectAll.checked = true;
            }
            updateCount();
          });
        });

        btnGenerate.addEventListener("click", () => {
          const selectedIds = Array.from(document.querySelectorAll(".eleve-checkbox:checked"))
            .map(cb => cb.value);

          if (selectedIds.length === 0) return;

          generateBulletinsForMultiple(selectedIds);
        });

        updateCount();
      })
      .catch((error) => {
        console.error("Erreur lors du chargement des élèves:", error);
        fields.tableContent.innerHTML = '<div class="alert alert-danger">Erreur lors du chargement des élèves</div>';
        fields.elevesContainer.style.display = "block";
      });
  };

  hideFields(
    fields.idCampus,
    fields.idClasseCycle,
    fields.idClasse,
    fields.coursField,
    fields.evaluationField,
    fields.jrField,
    fields.horaireTypeField,
    fields.periodeField,
    fields.typeNoteField,
    fields.idEleve,
  );
  fields.trimestreTable.style.display = "none";
  fields.elevesContainer.style.display = "none";
  if (fields.modal) fields.modal.style.display = "none";

  const savedAnnee = getFromSession("id_annee");
  if (savedAnnee && fields.idAnnee) {
    fields.idAnnee.value = savedAnnee;
    updateDropdown(
      // `/get_all_classes_by_year?id_annee=${this.value}`,
      `/get_all_classes_deliberate_by_year_tutulaire?id_annee=${savedAnnee}`,
      fields.idClasse,
      "id",
      "label"
    );
  }

  fields.idAnnee?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.idClasse,
      fields.coursField,
      fields.evaluationField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.typeNoteField,
      fields.idEleve,

    );
    fields.trimestreTable.style.display = "none";
    fields.elevesContainer.style.display = "none";
    if (this.value) {
      saveToSession("id_annee", this.value);
      document.getElementById("id_id_annee").value = this.value;
      updateDropdown(
        // `/get_all_classes_by_year?id_annee=${this.value}`,
        `/get_all_classes_deliberate_by_year_tutulaire?id_annee=${this.value}`,
        fields.idClasse,
        "id",
        "label"
      );
    }
  });

  fields.idClasse?.addEventListener("change", function () {
    const selectedOption = this.options[this.selectedIndex];
    const campusId = selectedOption.dataset.campus;
    const cycleId = selectedOption.dataset.cycle;
    const classeId = this.value;
    const anneeId = fields.idAnnee.value;

    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.coursField,
      fields.evaluationField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.typeNoteField,
      fields.idEleve,

    );
    fields.trimestreTable.style.display = "none";
    fields.elevesContainer.style.display = "none";

    if (classeId && campusId && cycleId) {
      const selectedData = {
        id_annee: anneeId,
        id_campus: campusId,
        id_cycle: cycleId,
        id_classe: classeId,
      };
      saveToSession("selected_classe_data", JSON.stringify(selectedData));

      document.getElementById("id_id_campus").value = campusId;
      document.getElementById("id_id_cycle_actif").value = cycleId;
      document.getElementById("id_id_classe_active").value = classeId;

      loadRegisteredPupils(anneeId, campusId, cycleId, classeId);
    }
  });
};

window.generateBulletinsForMultiple = (eleveIds) => {
  const fields = {
    idAnnee: document.getElementById("id_id_annee"),
    idCampus: document.getElementById("id_id_campus"),
    idClasseCycle: document.getElementById("id_id_cycle_actif"),
    idClasse: document.getElementById("id_id_classe_active"),
  };

  const selectedData = JSON.parse(getFromSession("selected_classe_data") || "{}");
  const id_annee = selectedData.id_annee || fields.idAnnee?.value;
  const id_campus = selectedData.id_campus || fields.idCampus?.value;
  const id_cycle = selectedData.id_cycle || fields.idClasseCycle?.value;
  const id_classe = selectedData.id_classe || fields.idClasse?.value;

  if (!id_annee || !id_campus || !id_cycle || !id_classe) {
    alert("Erreur : Année, campus, cycle ou classe non sélectionnés.");
    return;
  }

  if (eleveIds.length === 0) {
    alert("Aucun élève sélectionné.");
    return;
  }

  const form = document.createElement("form");
  form.method = "POST";
  form.action = "/generer_bulletin_pdf/";
  form.target = "_blank";
  const commonParams = { id_annee, id_campus, id_cycle, id_classe };
  for (const [key, value] of Object.entries(commonParams)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = key;
    input.value = value;
    form.appendChild(input);
  }


  eleveIds.forEach(id => {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = "id_eleve";
    input.value = id;
    form.appendChild(input);
  });


  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
    document.querySelector('[name=csrfmiddlewaretoken]')?.value;
  if (csrfToken) {
    const csrfInput = document.createElement("input");
    csrfInput.type = "hidden";
    csrfInput.name = "csrfmiddlewaretoken";
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
  }

  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
};


const setupChangerInscriptionEleve = () => {
  const fields = {
    idAnnee: document.getElementById("id_id_annee"),
    idCampus: document.getElementById("id_id_campus"),
    idClasseCycle: document.getElementById("id_id_cycle_actif"),
    idClasse: document.getElementById("id_id_classe_active"),
    coursField: document.getElementById("id_id_cours_classe"),
    jrField: document.getElementById("id_id_session"),
    horaireTypeField: document.getElementById("id_id_trimestre"),
    periodeField: document.getElementById("id_id_periode"),
    typeNoteField: document.getElementById("id_id_type_note"),
    evaluationField: document.getElementById("id_id_evaluation"),
    trimestreTable: document.getElementById("table-download-btn"),
    elevesContainer: document.getElementById("table-display-pupils"),
    tableContent: document.querySelector("#table-display-pupils .table-responsive"),
    modal: document.getElementById("modalContainer"),
    idEleve: document.getElementById('id_id_eleve'),

  };

  if (!fields.idAnnee || !fields.elevesContainer || !fields.tableContent) {
    console.error("Éléments requis manquants pour /changer_inscription/");
    return;
  }



  const loadRegisteredPupils = (anneeId, campusId, cycleId, classeId) => {
    const url = `/get_pupils_registred_classe/?id_annee=${anneeId}&id_campus=${campusId}&id_cycle=${cycleId}&id_classe_active=${classeId}`;
    fetch(url)
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Erreur HTTP : ${response.status}`);
        }
        return response.json();
      })
      .then((data) => {
        const pupils = (data.data || data || []).filter(pupil => pupil.status === true)
        //const pupils = data.data || data || [];
        const selectedOption = fields.idClasse.options[fields.idClasse.selectedIndex];
        const className = selectedOption.textContent;
        const tableHeader = fields.elevesContainer.querySelector(".table-header h3");
        if (tableHeader) {
          tableHeader.innerHTML = `
                  LISTE DES ELEVES INSCRITS DANS LA CLASSE ${className}
                  <button class="btn btn-secondary btn-sm" style="margin-left: 10px;" onclick="generatePupilsPDF('${anneeId}', '${campusId}', '${cycleId}', '${classeId}')">
                      Générer la liste de cette classe
                  </button>`;
        }

        let html = `
              <table id="basic-datatables" class="display table table-striped table-hover">
                  <thead>
                      <tr>
                          <th>Nom complet</th>
                          <th>Statut</th>
                          <th>Est redoublant ?</th>
                          <th>Actions</th>
                      </tr>
                  </thead>
                  <tbody>`;

        if (pupils.length > 0) {
          pupils.forEach((pupil) => {
            const fullName = pupil.nom_complet ? sanitize(pupil.nom_complet) : '';
            const statusChecked = pupil.status ? 'checked' : '';
            const redoublementChecked = pupil.redoublement ? 'checked' : '';

            html += `
                      <tr>
                          <td>${fullName}</td>
                          <td>
                              <input type="checkbox" class="status-checkbox" 
                                     data-eleve-id="${pupil.id_eleve}" 
                                     data-annee-id="${anneeId}" 
                                     data-campus-id="${campusId}" 
                                     data-cycle-id="${cycleId}" 
                                     data-classe-id="${classeId}" 
                                     ${statusChecked} 
                                     onchange="updateStatus(this)">
                          </td>
                          <td>
                              <input type="checkbox" class="redoublement-checkbox" 
                                     data-eleve-id="${pupil.id_eleve}" 
                                     data-annee-id="${anneeId}" 
                                     data-campus-id="${campusId}" 
                                     data-cycle-id="${cycleId}" 
                                     data-classe-id="${classeId}" 
                                     ${redoublementChecked} 
                                     onchange="updateRedoublement(this)">
                          </td>
                          <td>
                              <button class="btn btn-success btn-sm" onclick="Update_eleve(${pupil.id_eleve})" title="Changer l'inscription">
                                  <i class="fas fa-edit"></i>
                              </button>
                          </td>
                      </tr>`;
          });
        } else {
          html += `
                  <tr>
                      <td colspan="4" class="text-center text-muted">Aucun élève trouvé.</td>
                  </tr>`;
        }

        html += `
                  </tbody>
              </table>`;
        fields.tableContent.innerHTML = html;
        fields.elevesContainer.style.display = "block";
        if (fields.modal) fields.modal.style.display = "none";
      })
      .catch((error) => {
        console.error("Erreur lors du chargement des élèves:", error);
        fields.tableContent.innerHTML = '<div class="alert alert-danger">Erreur lors du chargement des élèves</div>';
        fields.elevesContainer.style.display = "block";
        Swal.fire({
          icon: 'error',
          title: 'Erreur',
          text: `Erreur lors du chargement des élèves : ${error.message}`,
          confirmButtonText: 'OK',
          timer: 6000
        });
      });
  };


  // Initialisation
  hideFields(
    fields.idCampus,
    fields.idClasseCycle,
    fields.idClasse,
    fields.coursField,
    fields.evaluationField,
    fields.jrField,
    fields.horaireTypeField,
    fields.periodeField,
    fields.typeNoteField,
    fields.idEleve,
  );
  fields.trimestreTable.style.display = "none";
  fields.elevesContainer.style.display = "none";
  if (fields.modal) fields.modal.style.display = "none";

  const savedAnnee = getFromSession("id_annee");
  if (savedAnnee && fields.idAnnee) {
    fields.idAnnee.value = savedAnnee;
    updateDropdown(
      `/charger_classes?id_annee=${savedAnnee}`,
      fields.idClasse,
      "id",
      "label"
    );
  }

  // Événements
  fields.idAnnee?.addEventListener("change", function () {
    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.idClasse,
      fields.coursField,
      fields.evaluationField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.typeNoteField,
      fields.idEleve,

    );
    fields.trimestreTable.style.display = "none";
    fields.elevesContainer.style.display = "none";
    if (this.value) {
      saveToSession("id_annee", this.value);
      document.getElementById("id_id_annee").value = this.value;
      updateDropdown(
        `/charger_classes?id_annee=${this.value}`,
        fields.idClasse,
        "id",
        "label"
      );
    }
  });

  fields.idClasse?.addEventListener("change", function () {
    const selectedOption = this.options[this.selectedIndex];
    const campusId = selectedOption.dataset.campus;
    const cycleId = selectedOption.dataset.cycle;
    const classeId = this.value;
    const anneeId = fields.idAnnee.value;

    hideFields(
      fields.idCampus,
      fields.idClasseCycle,
      fields.coursField,
      fields.evaluationField,
      fields.jrField,
      fields.horaireTypeField,
      fields.periodeField,
      fields.typeNoteField,
      fields.idEleve,

    );
    fields.trimestreTable.style.display = "none";
    fields.elevesContainer.style.display = "none";

    if (classeId && campusId && cycleId) {
      const selectedData = {
        id_annee: anneeId,
        id_campus: campusId,
        id_cycle: cycleId,
        id_classe: classeId,
      };
      saveToSession("selected_classe_data", JSON.stringify(selectedData));

      document.getElementById("id_id_campus").value = campusId;
      document.getElementById("id_id_cycle_actif").value = cycleId;
      document.getElementById("id_id_classe_active").value = classeId;

      loadRegisteredPupils(anneeId, campusId, cycleId, classeId);
    }
  });
};

window.Update_eleve = (id_eleve) => {
  // Créer le modal dynamiquement
  const modal = document.createElement("div");
  modal.className = "modal";
  modal.style.display = "block";
  modal.style.position = "fixed";
  modal.style.top = "0";
  modal.style.left = "0";
  modal.style.width = "100%";
  modal.style.height = "100%";
  modal.style.backgroundColor = "rgba(0,0,0,0.5)";
  modal.style.zIndex = "1000";
  modal.innerHTML = `
      <div style="background: white; width: 400px; margin: 100px auto; padding: 20px; border-radius: 5px;">
        <h3>Changer l'inscription</h3>
        <form id="updatePupilForm">
          <div class="form-group">
            <label for="modal_id_annee">Année scolaire</label>
            <select id="modal_id_annee" class="form-control" required>
              <option value="">----------</option>
            </select>
          </div>
          <div class="form-group">
            <label for="modal_id_classe">Classe</label>
            <select id="modal_id_classe" class="form-control" required>
              <option value="">----------</option>
            </select>
          </div>
          <button type="submit" class="btn btn-primary">Mettre à jour</button>
          <button type="button" class="btn btn-secondary" onclick="this.closest('.modal').remove()">Annuler</button>
        </form>
      </div>
    `;

  document.body.appendChild(modal);

  // Charger les années scolaires dans le dropdown
  const modalAnnee = modal.querySelector("#modal_id_annee");
  fetch("/get_all_years/")
    .then((response) => response.json())
    .then((data) => {
      data.forEach((annee) => {
        const option = document.createElement("option");
        option.value = annee.id_annee;
        option.textContent = annee.annee;
        modalAnnee.appendChild(option);
      });
    });

  // Charger les classes en fonction de l'année sélectionnée
  modalAnnee.addEventListener("change", function () {
    const modalClasse = modal.querySelector("#modal_id_classe");
    modalClasse.innerHTML = '<option value="">Sélectionner une classe</option>';
    if (this.value) {
      updateDropdown(
        `/charger_classes?id_annee=${this.value}`,
        modalClasse,
        "id",
        "label"
      );
    }
  });

  // Gérer la soumission du formulaire
  const form = modal.querySelector("#updatePupilForm");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const newAnneeId = modalAnnee.value;
    const newClasseId = modal.querySelector("#modal_id_classe").value;
    const selectedOption = modal.querySelector("#modal_id_classe").options[modal.querySelector("#modal_id_classe").selectedIndex];
    const campusId = selectedOption.dataset.campus;
    const cycleId = selectedOption.dataset.cycle;

    if (!newAnneeId || !newClasseId || !campusId || !cycleId) {
      alert("Veuillez sélectionner une année et une classe.");
      return;
    }

    // Créer un formulaire pour soumettre les données
    const submitForm = document.createElement("form");
    submitForm.method = "POST";
    submitForm.action = "/update_pupil_inscription/";
    submitForm.style.display = "none";

    const fieldsToSubmit = {
      id_eleve,
      id_annee: newAnneeId,
      id_campus: campusId,
      id_cycle: cycleId,
      id_classe: newClasseId,
    };


    for (const [key, value] of Object.entries(fieldsToSubmit)) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = key;
      input.value = value;
      submitForm.appendChild(input);
    }

    // Ajouter le jeton CSRF
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
    if (csrfToken) {
      const csrfInput = document.createElement("input");
      csrfInput.type = "hidden";
      csrfInput.name = "csrfmiddlewaretoken";
      csrfInput.value = csrfToken;
      submitForm.appendChild(csrfInput);
    }

    document.body.appendChild(submitForm);
    submitForm.submit();
    modal.remove();
  });
};

const init = () => {
  setupModal();
  if (window.location.pathname.includes("/generer_excel_file/")) {
    setupExcelFile();
  } else if (window.location.pathname.includes("/add_evaluation/") || window.location.pathname.includes("/soumettre_devoir/")) {
    setupAddEvaluation();
  } else if (window.location.pathname.includes("/generer_bulletin_eleve/")) {
    setupBulletinEleve();
  }
  else if (window.location.pathname.includes("/changer_inscription/")) {
    setupChangerInscriptionEleve();
  }
  else if (window.location.pathname.includes("/affichage_notes/")) {
    setupAffichageNotes();
  }
};
// Lancer l'initialisation une fois le DOM chargé
document.addEventListener("DOMContentLoaded", init);

