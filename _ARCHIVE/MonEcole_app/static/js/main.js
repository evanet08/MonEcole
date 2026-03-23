
// Toggle mobile sidebar
document.querySelector('.mobile-nav-toggle').addEventListener('click', function () {
    document.body.classList.toggle('sidebar-active');
    this.querySelector('i').classList.toggle('fa-bars');
    this.querySelector('i').classList.toggle('fa-times');
});

// Menu item click handler
document.querySelectorAll('.menu-item > a').forEach(item => {
    item.addEventListener('click', function (e) {
        if (this.parentElement.querySelector('.submenu')) {
            e.preventDefault();
            this.parentElement.classList.toggle('active');

            // Close other open menus
            document.querySelectorAll('.menu-item').forEach(otherItem => {
                if (otherItem !== this.parentElement && otherItem.classList.contains('active')) {
                    otherItem.classList.remove('active');
                }
            });
        }
    });
});

// Close menu when clicking outside
document.addEventListener('click', function (e) {
    if (!e.target.closest('.sidebar') && !e.target.closest('.mobile-nav-toggle')) {
        document.body.classList.remove('sidebar-active');
        document.querySelector('.mobile-nav-toggle i').classList.remove('fa-times');
        document.querySelector('.mobile-nav-toggle i').classList.add('fa-bars');
    }
});

// ==================messages'sections
window.onload = function () {
    setTimeout(() => {
        document.querySelectorAll('.message-box').forEach((box) => {
            box.classList.add('falling');
        });
    }, 700);

    // Gestion du bouton de fermeture
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            let box = this.parentElement;
            box.classList.add('disappear');
            setTimeout(() => { box.remove(); }, 1000);
        });
    });

    // Disparition automatique après 5 secondes avec animation
    setTimeout(() => {
        document.querySelectorAll('.message-box').forEach(box => {
            box.classList.add('disappear');
            setTimeout(() => box.remove(), 4000);
        });
    }, 19000);
};



// ======================= search bar 

document.getElementById("searchInput").addEventListener("keyup", function () {
    let filter = this.value.toLowerCase();
    let rows = document.querySelectorAll("#studentTable tr");

    rows.forEach(row => {
        let nom = row.cells[0].textContent.toLowerCase();
        let prenom = row.cells[1].textContent.toLowerCase();

        if (nom.includes(filter) || prenom.includes(filter)) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });
});





