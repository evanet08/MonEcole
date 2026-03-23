
document.addEventListener("DOMContentLoaded", function () {
    let modal = document.getElementById("modalContainer");
    let openModalBtn = document.getElementById("openModal");
    let closeModalBtn = document.querySelector(".close-btn");
    let cancelBtn = document.getElementById("cancelBtn");
  
    if (!modal || !openModalBtn || !closeModalBtn || !cancelBtn) return;
  
    // Afficher le modal
    openModalBtn.addEventListener("click", function () {
      modal.style.display = "flex";
      document.body.style.overflow = "hidden";
    });
  
    function closeModal() {
      modal.style.display = "none";
      document.body.style.overflow = "auto";
    }
  
    closeModalBtn.addEventListener("click", closeModal);
    cancelBtn.addEventListener("click", closeModal);
  
    window.addEventListener("click", function (event) {
      if (event.target === modal) {
        closeModal();
      }
    });
  
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && modal.style.display === "flex") {
        closeModal();
      }
    });
  
    let form = document.getElementById("userForm");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        closeModal();
      });
    }
  });
  