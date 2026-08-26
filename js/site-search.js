// Convierte el icono del navbar en un buscador desplegable sin alterar su distribución.
document.querySelectorAll(".search-icon").forEach((searchIcon) => {
    if (searchIcon.closest(".site-search")) {
        return;
    }

    const form = document.createElement("form");
    const input = document.createElement("input");
    const submitButton = document.createElement("button");
    form.className = "site-search";
    form.setAttribute("role", "search");
    input.className = "site-search-input";
    input.type = "search";
    input.name = "query";
    input.placeholder = "Buscar películas o series";
    input.setAttribute("aria-label", "Buscar películas o series");
    submitButton.type = "submit";
    submitButton.className = "visually-hidden";
    submitButton.tabIndex = -1;
    submitButton.textContent = "Buscar";

    searchIcon.parentNode.insertBefore(form, searchIcon);
    form.append(input, submitButton, searchIcon);
    searchIcon.setAttribute("role", "button");
    searchIcon.setAttribute("aria-expanded", "false");
    searchIcon.setAttribute("aria-controls", "site-search-input");
    input.id = "site-search-input";

    const closeSearch = () => {
        form.classList.remove("is-open");
        searchIcon.setAttribute("aria-expanded", "false");
    };

    searchIcon.addEventListener("click", (event) => {
        event.preventDefault();
        const willOpen = !form.classList.contains("is-open");
        form.classList.toggle("is-open", willOpen);
        searchIcon.setAttribute("aria-expanded", String(willOpen));

        if (willOpen) {
            input.focus();
            input.select();
        }
    });

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const query = input.value.trim();

        if (!query) {
            input.focus();
            return;
        }

        const currentCategory = new URLSearchParams(window.location.search).get("category");
        const category = ["movies", "series"].includes(currentCategory) ? currentCategory : "movies";
        const destination = new URL("catalogo.html", window.location.href);
        destination.searchParams.set("category", category);
        destination.searchParams.set("query", query);
        window.location.assign(destination.href);
    });

    input.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeSearch();
            searchIcon.focus();
        }

        if (event.key === "Enter") {
            event.preventDefault();
            form.requestSubmit();
        }
    });

    document.addEventListener("click", (event) => {
        if (!form.contains(event.target)) {
            closeSearch();
        }
    });
});
