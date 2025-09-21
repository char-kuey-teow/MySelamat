document.addEventListener("DOMContentLoaded", () => {
    // Figure out which page we're on based on <body class="xxx-page">
    const bodyClass = document.body.classList[0]; 
    const activePage = bodyClass ? bodyClass.replace("-page", "") : "";

    // Load the menu and highlight active item
    fetch("menu.html")
        .then(res => res.text())
        .then(html => {
            document.getElementById("menu-container").innerHTML = html;

            // Highlight active menu item
            document.querySelectorAll("#menu-container .nav-item").forEach(item => {
                if (item.dataset.page === activePage) {
                    item.classList.add("active");
                }
            });
        })
        .catch(err => console.error("Menu load failed:", err));
});
