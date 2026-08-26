// Contenedor principal de favoritos.
const favoritesPanel = document.querySelector("#favoritesPanel");

// Botones de filtros rápidos por tipo de contenido.
const filterButtons = document.querySelectorAll("[data-filter]");

// Botones para cambiar el modo de vista: tarjetas, detallada o sencilla.
const viewButtons = document.querySelectorAll("[data-view]");

const normalizeFilter = (value) => String(value || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim();

const escapeHtml = (value) => String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const fallbackPoster = "this.replaceWith(Object.assign(document.createElement('div'), { className: 'favorite-placeholder', textContent: 'Imagen no disponible' }))";

const getActiveFilter = () => document.querySelector("[data-filter].btn-primary")?.dataset.filter || "all";

const getCatalogDetailUrl = (item) => {
    const category = ["movies", "series", "anime"].includes(item.type) ? item.type : "movies";
    const params = new URLSearchParams({ category, focus: item.id });
    return `catalogo.html?${params.toString()}`;
};

// Convierte un favorito del perfil en una fila/tarjeta visual.
const createFavoriteItem = (item) => {
    const favorite = document.createElement("article");
    favorite.className = "favorite-item";
    favorite.dataset.category = normalizeFilter(item.type || "general");
    favorite.dataset.favoriteId = item.id;

    const imageMarkup = item.image
        ? `<img src="${escapeHtml(item.image)}" alt="Imagen de ${escapeHtml(item.title)}" loading="lazy" onerror="${fallbackPoster}">`
        : '<div class="favorite-placeholder">Sin imagen</div>';

    const description = item.description || "Contenido agregado a favoritos desde el catálogo.";
    const moreLink = description.length > 160
        ? `<a class="favorite-more-link" href="${escapeHtml(getCatalogDetailUrl(item))}">Ver más</a>`
        : "";

    favorite.innerHTML = `
        <div class="favorite-thumb">${imageMarkup}</div>
        <div class="favorite-copy">
            <span class="favorite-category">${escapeHtml(item.categoryGeneral || item.format || item.type || "General")}</span>
            <h2>${escapeHtml(item.title)}</h2>
            <div class="favorite-description">
                <p>${escapeHtml(description)}</p>
                ${moreLink}
            </div>
        </div>
        <button class="btn btn-outline-light btn-sm" type="button" data-remove-favorite="${escapeHtml(item.id)}">Eliminar</button>
    `;

    return favorite;
};

const applyFavoriteFilter = () => {
    const selectedFilter = getActiveFilter();

    document.querySelectorAll(".favorite-item").forEach((item) => {
        const shouldShow = selectedFilter === "all" || item.dataset.category === selectedFilter;
        item.classList.toggle("is-hidden", !shouldShow);
    });
};

const renderFavoritesFromProfile = () => {
    if (typeof AltoidssStore === "undefined") {
        return;
    }

    const profile = AltoidssStore.getProfile();
    const favorites = Object.values(profile.favoriteItems);

    favoritesPanel.innerHTML = "";

    if (!favorites.length) {
        favoritesPanel.innerHTML = `
            <article class="favorite-empty">
                <h2>No hay favoritos seleccionados</h2>
                <p>Marca el corazón en una tarjeta del catálogo para agregar contenido a esta sección.</p>
            </article>
        `;
        return;
    }

    favorites.forEach((item) => {
        favoritesPanel.appendChild(createFavoriteItem(item));
    });

    applyFavoriteFilter();
};

filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
        // Cambia el estilo visual del botón activo.
        filterButtons.forEach((item) => {
            item.classList.toggle("btn-primary", item === button);
            item.classList.toggle("btn-outline-light", item !== button);
        });

        applyFavoriteFilter();
    });
});

// Cambia la clase de vista del panel para modificar el diseño con CSS.
viewButtons.forEach((button) => {
    button.addEventListener("click", () => {
        favoritesPanel.classList.remove("view-cards", "view-detailed", "view-simple");
        favoritesPanel.classList.add(`view-${button.dataset.view}`);

        // Marca visualmente la vista seleccionada.
        viewButtons.forEach((item) => {
            item.classList.toggle("btn-primary", item === button);
            item.classList.toggle("btn-outline-light", item !== button);
        });
    });
});

document.addEventListener("click", async (event) => {
    const removeButton = event.target.closest("[data-remove-favorite]");

    if (!removeButton || typeof AltoidssStore === "undefined") {
        return;
    }

    await AltoidssStore.removeFavorite(removeButton.dataset.removeFavorite);
    renderFavoritesFromProfile();
});

const initializeFavorites = async () => {
    await AltoidssStore.initialize();
    renderFavoritesFromProfile();
};

initializeFavorites();
