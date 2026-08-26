// Paneles de categoría general: películas, series TV y anime.
const catalogPanels = document.querySelectorAll(".catalog-panel");

// Botones que permiten cambiar la categoría general del catálogo.
const categoryButtons = document.querySelectorAll("[data-category-view]");

// Grillas de tarjetas dentro de cada categoría general.
const catalogGrids = document.querySelectorAll(".catalog-grid");

// Botones que permiten elegir 3, 5 o 7 tarjetas por línea.
const gridButtons = document.querySelectorAll("[data-grid]");
const catalogViewButtons = document.querySelectorAll("[data-catalog-view]");
const gridDensityGroups = document.querySelectorAll(".grid-density");
const catalogFilterForm = document.querySelector("#catalogFilterForm");
const catalogSearchInput = document.querySelector("#sidebar-search");
const filterInitial = document.querySelector("#filter-initial");
const filterGenre = document.querySelector("#filter-genre");
const filterFormat = document.querySelector("#filter-format");
const filterSeasons = document.querySelector("#filter-seasons");
const filterSeasonsGroup = document.querySelector("#filter-seasons-group");
const filterStatus = document.querySelector("#filter-status");
const filterYearMin = document.querySelector("#filter-year-min");
const filterYearMax = document.querySelector("#filter-year-max");
const filterYearMinValue = document.querySelector("#filter-year-min-value");
const filterYearMaxValue = document.querySelector("#filter-year-max-value");
const filterYearOutput = document.querySelector("#filter-year-output");
const filterResults = document.querySelector("#filter-results");
const clearCatalogFilters = document.querySelector("#clearCatalogFilters");
const mobileFilterToggle = document.querySelector("#mobileFilterToggle");
const catalogSidebar = document.querySelector(".sidebar");
const ITEMS_PER_PAGE = 35;
const currentPages = { movies: 1, series: 1, anime: 1 };
let catalogItems = [];

const createFilterState = () => ({
    initial: "",
    genre: "",
    format: "",
    seasons: "",
    status: "",
    yearMin: null,
    yearMax: null,
});

const catalogFilters = {
    movies: createFilterState(),
    series: createFilterState(),
    anime: createFilterState(),
};

const setMobileFiltersOpen = (isOpen) => {
    catalogSidebar?.classList.toggle("is-filter-open", isOpen);
    mobileFilterToggle?.setAttribute("aria-expanded", String(isOpen));
    const label = mobileFilterToggle?.querySelector("span");
    if (label) {
        label.textContent = isOpen ? "Ocultar filtros" : "Mostrar filtros";
    }
};

mobileFilterToggle?.addEventListener("click", () => {
    setMobileFiltersOpen(!catalogSidebar.classList.contains("is-filter-open"));
});

const tagClassNames = [
    "tag-action",
    "tag-adventure",
    "tag-drama",
    "tag-comedy",
    "tag-fantasy",
    "tag-family",
    "tag-romance",
    "tag-new",
];

const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const eyeIcon = `
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-eye" viewBox="0 0 16 16" aria-hidden="true">
        <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8M1.173 8a13 13 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5s3.879 1.168 5.168 2.457A13 13 0 0 1 14.828 8q-.086.13-.195.288c-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5s-3.879-1.168-5.168-2.457A13 13 0 0 1 1.172 8z"/>
        <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5M6.5 8a1.5 1.5 0 1 1 3 0 1.5 1.5 0 0 1-3 0"/>
    </svg>
`;

const heartIcon = `
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-heart-fill" viewBox="0 0 16 16" aria-hidden="true">
        <path fill-rule="evenodd" d="M8 1.314C12.438-3.248 23.534 4.735 8 15-7.534 4.736 3.562-3.248 8 1.314"/>
    </svg>
`;

const fallbackPoster = "this.replaceWith(Object.assign(document.createElement('div'), { className: 'poster-placeholder', textContent: 'Imagen no disponible' }))";
let catalogFeedbackTimer = null;
let activeCatalogDetail = null;
const allowedCategories = ["movies", "series", "anime"];

const showCatalogFeedback = (message, type = "error") => {
    let feedback = document.querySelector("#catalogFeedback");

    if (!feedback) {
        feedback = document.createElement("div");
        feedback.id = "catalogFeedback";
        feedback.className = "catalog-feedback";
        feedback.setAttribute("role", "status");
        document.querySelector(".content")?.prepend(feedback);
    }

    feedback.textContent = message;
    feedback.classList.toggle("is-error", type === "error");
    feedback.classList.toggle("is-success", type === "success");
    feedback.classList.add("is-visible");

    clearTimeout(catalogFeedbackTimer);
    catalogFeedbackTimer = setTimeout(() => {
        feedback.classList.remove("is-visible");
    }, 4200);
};

const getCardSnapshot = (card) => {
    const panel = card.closest(".catalog-panel");
    const catalogItem = card.catalogItem || {};
    const image = card.querySelector(".poster img")?.getAttribute("src") || "";
    const title = card.querySelector("h2")?.textContent.trim() || "Contenido sin título";
    const description = card.querySelector("p")?.textContent.trim() || "Contenido guardado desde catálogo.";
    const tags = [...card.querySelectorAll(".tag")].map((tag) => tag.textContent.trim()).filter(Boolean);

    return {
        ...catalogItem,
        id: card.dataset.contentId || title.toLowerCase().replace(/\s+/g, "-"),
        title,
        type: panel?.id?.replace("catalog-", "") || "anime",
        genre: catalogItem.genre || tags[0] || "General",
        year: catalogItem.year || "",
        tags: Array.isArray(catalogItem.tags) ? catalogItem.tags : tags.slice(1, 4),
        image,
        description,
        source: catalogItem.source || (card.dataset.dynamic ? "json" : "catalogo-estatico"),
    };
};

const refreshCardActionState = (card) => {
    const snapshot = getCardSnapshot(card);
    const seenButton = card.querySelector("[data-card-action='seen']");
    const favoriteButton = card.querySelector("[data-card-action='favorite']");
    const viewStatusTag = card.querySelector("[data-view-status-tag]");
    const isSeen = AltoidssStore.isSeen(snapshot);
    const isFavorite = AltoidssStore.isFavorite(snapshot);

    seenButton?.classList.toggle("is-active", isSeen);
    favoriteButton?.classList.toggle("is-favorite", isFavorite);
    seenButton?.setAttribute("aria-pressed", String(isSeen));
    favoriteButton?.setAttribute("aria-pressed", String(isFavorite));
    seenButton?.setAttribute("aria-label", isSeen ? "Marcar como no visto" : "Marcar como visto");
    seenButton?.setAttribute("title", isSeen ? "Visto" : "No visto");

    if (viewStatusTag) {
        viewStatusTag.textContent = isSeen ? "Visto" : "No visto";
        viewStatusTag.classList.toggle("is-seen", isSeen);
    }
};

const animateSeenConfirmation = (container) => {
    const seenButton = container?.querySelector("[data-card-action='seen'], [data-detail-action='seen']");
    const viewStatusTag = container?.querySelector("[data-view-status-tag]");

    [seenButton, viewStatusTag].forEach((element) => {
        if (!element) {
            return;
        }

        element.classList.remove("is-confirmed");
        void element.offsetWidth;
        element.classList.add("is-confirmed");
        window.setTimeout(() => element.classList.remove("is-confirmed"), 520);
    });
};

const addCardActions = (card) => {
    const poster = card.querySelector(".poster");
    const title = card.querySelector("h2")?.textContent.trim() || "contenido";

    card.tabIndex = 0;
    card.setAttribute("aria-label", `Ver detalles de ${title}`);

    if (!poster || poster.querySelector(".card-actions")) {
        return;
    }

    const actions = document.createElement("div");
    actions.className = "card-actions";
    actions.innerHTML = `
        <button class="card-toggle card-toggle-seen" type="button" data-card-action="seen" aria-label="Marcar como visto" aria-pressed="false">${eyeIcon}</button>
        <button class="card-toggle card-toggle-favorite" type="button" data-card-action="favorite" aria-label="Agregar a favoritos" aria-pressed="false">${heartIcon}</button>
    `;

    poster.appendChild(actions);
    refreshCardActionState(card);
};

const enhanceCatalogCards = () => {
    if (typeof AltoidssStore === "undefined") {
        return;
    }

    document.querySelectorAll(".anime-card").forEach(addCardActions);
};

// Aplica la preferencia guardada en Dashboard para mantener consistencia visual.
const applyStoredGridPreference = () => {
    const cardsPerRow = AltoidssStore.getProfile().settings?.cardsPerRow || 5;

    catalogGrids.forEach((grid) => {
        grid.style.setProperty("--cards-per-row", cardsPerRow);
    });

    gridButtons.forEach((button) => {
        const isSelected = Number(button.dataset.grid) === Number(cardsPerRow);
        button.classList.toggle("btn-primary", isSelected);
        button.classList.toggle("btn-outline-light", !isSelected);
    });
};

const applyCatalogView = (view = "cards") => {
    const selectedView = view === "list" ? "list" : "cards";

    catalogGrids.forEach((grid) => {
        grid.classList.toggle("is-list-view", selectedView === "list");
    });

    catalogViewButtons.forEach((button) => {
        const isSelected = button.dataset.catalogView === selectedView;
        button.classList.toggle("btn-primary", isSelected);
        button.classList.toggle("btn-outline-light", !isSelected);
        button.setAttribute("aria-pressed", String(isSelected));
    });

    gridDensityGroups.forEach((group) => {
        group.hidden = selectedView === "list";
    });
};

// Crea una tarjeta de catálogo a partir de un registro JSON guardado desde Dashboard.
const createCatalogCard = (item) => {
    const card = document.createElement("article");
    card.className = "anime-card";
    card.dataset.dynamic = "true";
    card.dataset.contentId = item.id || "";
    card.catalogItem = item;

    const descriptiveTags = (item.tags || []).filter((tag) => !/^(no\s+)?visto$|^por\s+ver$/i.test(String(tag).trim()));
    const tags = [item.genre, ...descriptiveTags, item.year].filter(Boolean).slice(0, 3);
    const tagMarkup = tags.map((tag, index) => (
        `<span class="tag ${tagClassNames[index % tagClassNames.length]}">${escapeHtml(tag)}</span>`
    )).join("") + '<span class="tag tag-view-status" data-view-status-tag>No visto</span>';

    const posterMarkup = item.image
        ? `<img src="${escapeHtml(item.image)}" alt="Imagen de ${escapeHtml(item.title)}" loading="lazy" onerror="${fallbackPoster}">`
        : '<div class="poster-placeholder">Buscando imagen</div>';

    const sourceUrl = /^https:\/\//i.test(String(item.sourceUrl || "")) ? item.sourceUrl : "";
    const sourceLinkMarkup = sourceUrl
        ? `<a class="source-link" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">Ver ficha externa</a>`
        : "";

    card.innerHTML = `
        <div class="poster">${posterMarkup}</div>
        <div class="anime-card-body">
            <div class="tag-list">${tagMarkup}</div>
            <h2>${escapeHtml(item.title)}</h2>
            <p>${escapeHtml(item.description)}</p>
            ${sourceLinkMarkup}
        </div>
    `;

    return card;
};

const normalizeFilterText = (value) => String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLocaleLowerCase("es");

const getItemYear = (item) => Number(item.emissionYear || item.year || 0);

const getItemGenres = (item) => {
    const excluded = /^(serie|pel[ií]cula|ova|ona|especial|visto|no visto|por ver|finalizado|emisi[oó]n|pr[oó]ximamente|\d{4})$/i;
    return [...new Set([
        item.genre,
        ...(Array.isArray(item.metadataGenres) ? item.metadataGenres : []),
        ...(Array.isArray(item.tags) ? item.tags : []),
    ].map((value) => String(value || "").trim()).filter((value) => value && !excluded.test(value)))];
};

const getTitleInitial = (item) => {
    const initial = String(item.title || "").trim().charAt(0).toUpperCase();
    return /^[A-Z]$/.test(initial) ? initial : "#";
};

const setFilterOptions = (select, values, emptyLabel, selectedValue) => {
    if (!select) {
        return;
    }

    select.replaceChildren(
        new Option(emptyLabel, ""),
        ...values.map((value) => new Option(value, value))
    );
    select.value = values.includes(selectedValue) ? selectedValue : "";
};

const updateYearLabels = (state) => {
    if (!filterYearMin || !filterYearMax) {
        return;
    }

    filterYearMinValue.textContent = filterYearMin.value;
    filterYearMaxValue.textContent = filterYearMax.value;
    filterYearOutput.textContent = `${filterYearMin.value}–${filterYearMax.value}`;
    state.yearMin = Number(filterYearMin.value);
    state.yearMax = Number(filterYearMax.value);
};

const configureFilterPanel = (category, reset = false) => {
    const state = catalogFilters[category];
    const items = catalogItems.filter((item) => item.type === category);
    const years = items.map(getItemYear).filter((year) => year > 0).sort((a, b) => a - b);
    const minimumYear = years[0] || new Date().getFullYear();
    const maximumYear = years.at(-1) || minimumYear;

    if (reset || state.yearMin === null || state.yearMin < minimumYear || state.yearMin > maximumYear) {
        state.yearMin = minimumYear;
    }
    if (reset || state.yearMax === null || state.yearMax > maximumYear || state.yearMax < minimumYear) {
        state.yearMax = maximumYear;
    }

    const initials = [...new Set(items.map(getTitleInitial))].sort((a, b) => (
        a === "#" ? -1 : b === "#" ? 1 : a.localeCompare(b)
    ));
    const genres = [...new Set(items.flatMap(getItemGenres))].sort((a, b) => a.localeCompare(b, "es"));
    const formats = [...new Set(items.map((item) => String(item.format || "").trim()).filter(Boolean))]
        .sort((a, b) => a.localeCompare(b, "es"));
    const seasonCounts = [...new Set(items.map((item) => Number(item.seasonsCount || 0)).filter((value) => value > 0))]
        .sort((a, b) => a - b)
        .map(String);
    const statuses = [...new Set(items.map((item) => String(item.productionStatus || "").trim()).filter(Boolean))]
        .sort((a, b) => a.localeCompare(b, "es"));

    setFilterOptions(filterInitial, initials, "Todas", state.initial);
    setFilterOptions(filterGenre, genres, "Todos", state.genre);
    setFilterOptions(filterFormat, formats, "Todos", state.format);
    setFilterOptions(filterSeasons, seasonCounts, "Todas", state.seasons);
    setFilterOptions(filterStatus, statuses, "Todos", state.status);
    state.initial = filterInitial.value;
    state.genre = filterGenre.value;
    state.format = filterFormat.value;
    state.seasons = filterSeasons.value;
    state.status = filterStatus.value;
    filterSeasonsGroup.hidden = category === "movies" || !seasonCounts.length;

    [filterYearMin, filterYearMax].forEach((input) => {
        input.min = minimumYear;
        input.max = maximumYear;
        input.disabled = minimumYear === maximumYear;
    });
    filterYearMin.value = Math.min(state.yearMin, state.yearMax);
    filterYearMax.value = Math.max(state.yearMin, state.yearMax);
    updateYearLabels(state);
};

const readFilterControls = (category) => {
    const state = catalogFilters[category];
    state.initial = filterInitial.value;
    state.genre = filterGenre.value;
    state.format = filterFormat.value;
    state.seasons = filterSeasonsGroup.hidden ? "" : filterSeasons.value;
    state.status = filterStatus.value;

    if (Number(filterYearMin.value) > Number(filterYearMax.value)) {
        const changedMinimum = document.activeElement === filterYearMin;
        if (changedMinimum) {
            filterYearMax.value = filterYearMin.value;
        } else {
            filterYearMin.value = filterYearMax.value;
        }
    }
    updateYearLabels(state);
    return state;
};

const itemMatchesFilters = (item, state) => {
    const year = getItemYear(item);
    const matchesYear = state.yearMin === null || state.yearMax === null || !year
        || (year >= state.yearMin && year <= state.yearMax);
    const matchesInitial = !state.initial || getTitleInitial(item) === state.initial;
    const matchesGenre = !state.genre || getItemGenres(item).some((genre) => (
        normalizeFilterText(genre) === normalizeFilterText(state.genre)
    ));
    const matchesFormat = !state.format || normalizeFilterText(item.format) === normalizeFilterText(state.format);
    const matchesSeasons = !state.seasons || Number(item.seasonsCount || 0) === Number(state.seasons);
    const matchesStatus = !state.status || normalizeFilterText(item.productionStatus) === normalizeFilterText(state.status);
    return matchesYear && matchesInitial && matchesGenre && matchesFormat && matchesSeasons && matchesStatus;
};

const getCategoryItems = (category) => catalogItems.filter((item) => (
    item.type === category && itemMatchesFilters(item, catalogFilters[category])
));

const updateFilterResultCount = (category) => {
    if (!filterResults || category !== getCategoryFromUrl()) {
        return;
    }

    const count = getCategoryItems(category).length;
    filterResults.textContent = `${count} resultado${count === 1 ? "" : "s"}`;
};

const applyCurrentFilters = (category) => {
    currentPages[category] = 1;
    renderCatalogPage(category);
    updatePageInUrl(category, 1);
    updateFilterResultCount(category);
};

const updatePageInUrl = (category, page) => {
    if (category !== getCategoryFromUrl()) {
        return;
    }

    const params = new URLSearchParams(window.location.search);
    page > 1 ? params.set("page", page) : params.delete("page");
    window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
};

const getVisiblePageNumbers = (currentPage, totalPages) => {
    const firstPage = Math.max(1, Math.min(currentPage - 2, totalPages - 4));
    const lastPage = Math.min(totalPages, firstPage + 4);
    return Array.from({ length: lastPage - firstPage + 1 }, (_, index) => firstPage + index);
};

const renderPagination = (category, totalItems, totalPages) => {
    const panel = document.querySelector(`#catalog-${category}`);
    let pagination = panel?.querySelector(".catalog-pagination");

    if (!panel) {
        return;
    }

    if (!pagination) {
        pagination = document.createElement("nav");
        pagination.className = "catalog-pagination";
        pagination.setAttribute("aria-label", `Paginación de ${category}`);
        panel.appendChild(pagination);
    }

    if (!totalItems) {
        pagination.innerHTML = '<p class="pagination-summary">No hay contenido para mostrar.</p>';
        return;
    }

    const currentPage = currentPages[category];
    const pageButtons = getVisiblePageNumbers(currentPage, totalPages).map((page) => `
        <button class="pagination-page${page === currentPage ? " is-active" : ""}" type="button"
            data-pagination-category="${category}" data-page="${page}"
            aria-label="Ir a la página ${page}" aria-current="${page === currentPage ? "page" : "false"}">${page}</button>
    `).join("");

    pagination.innerHTML = `
        <p class="pagination-summary">Página ${currentPage} de ${totalPages} · ${totalItems} resultados</p>
        <div class="pagination-actions">
            <button class="pagination-page pagination-arrow" type="button" data-pagination-category="${category}"
                data-page="${currentPage - 1}" aria-label="Página anterior" ${currentPage === 1 ? "disabled" : ""}>‹</button>
            ${pageButtons}
            <button class="pagination-page pagination-arrow" type="button" data-pagination-category="${category}"
                data-page="${currentPage + 1}" aria-label="Página siguiente" ${currentPage === totalPages ? "disabled" : ""}>›</button>
        </div>
    `;
};

const renderCatalogPage = (category) => {
    const targetGrid = document.querySelector(`#catalog-${category} .catalog-grid`);

    if (!targetGrid) {
        return;
    }

    const categoryItems = getCategoryItems(category);
    const totalPages = Math.max(1, Math.ceil(categoryItems.length / ITEMS_PER_PAGE));
    currentPages[category] = Math.min(Math.max(1, currentPages[category]), totalPages);
    const startIndex = (currentPages[category] - 1) * ITEMS_PER_PAGE;
    const visibleItems = categoryItems.slice(startIndex, startIndex + ITEMS_PER_PAGE);

    targetGrid.replaceChildren(...visibleItems.map(createCatalogCard));
    targetGrid.style.setProperty("--cards-per-row", AltoidssStore.getProfile().settings?.cardsPerRow || 5);
    renderPagination(category, categoryItems.length, totalPages);
    enhanceCatalogCards();
    updateFilterResultCount(category);
};

const renderAllCatalogPages = () => {
    allowedCategories.forEach(renderCatalogPage);
};

const getCatalogContent = async () => {
    if (typeof AltoidssStore === "undefined") {
        return [];
    }

    try {
        const sectionItems = await AltoidssStore.readSectionFiles();
        const adminItems = AltoidssStore.read();
        const existingIds = new Set(sectionItems.map((item) => item.id));
        const extraItems = adminItems.filter((item) => !existingIds.has(item.id));

        return [...sectionItems, ...extraItems];
    } catch (error) {
        console.warn("No se pudieron cargar los JSON de catálogo.", error);
        return AltoidssStore.read();
    }
};

// Inserta en el catálogo los registros guardados en archivos JSON por sección.
const renderStoredContent = async (nextItems) => {
    if (typeof AltoidssStore === "undefined") {
        return;
    }

    const items = nextItems ?? await getCatalogContent();

    if (!items.length) {
        catalogItems = [];
        renderAllCatalogPages();
        enhanceCatalogCards();
        return;
    }

    catalogItems = items;
    renderAllCatalogPages();
};

const getDetailTargetRect = () => {
    const pagePadding = window.innerWidth <= 680 ? 12 : 24;
    const width = Math.min(840, window.innerWidth - (pagePadding * 2));
    const preferredHeight = window.innerWidth <= 680 ? 680 : 420;
    const height = Math.min(preferredHeight, window.innerHeight - (pagePadding * 2));

    return {
        top: Math.max(pagePadding, (window.innerHeight - height) / 2),
        left: Math.max(pagePadding, (window.innerWidth - width) / 2),
        width,
        height,
    };
};

const getAnimationDuration = () => (
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 1 : 420
);

const setDetailActionState = (detail, snapshot) => {
    const seenButton = detail.querySelector("[data-detail-action='seen']");
    const favoriteButton = detail.querySelector("[data-detail-action='favorite']");
    const viewStatusTag = detail.querySelector("[data-view-status-tag]");
    const isSeen = AltoidssStore.isSeen(snapshot);
    const isFavorite = AltoidssStore.isFavorite(snapshot);

    seenButton?.classList.toggle("is-active", isSeen);
    favoriteButton?.classList.toggle("is-favorite", isFavorite);
    seenButton?.setAttribute("aria-pressed", String(isSeen));
    favoriteButton?.setAttribute("aria-pressed", String(isFavorite));

    if (seenButton) {
        seenButton.querySelector("span").textContent = isSeen ? "Marcar como no visto" : "Marcar como visto";
    }

    if (favoriteButton) {
        favoriteButton.querySelector("span").textContent = isFavorite ? "Quitar de favoritos" : "Agregar a favoritos";
    }

    if (viewStatusTag) {
        viewStatusTag.textContent = isSeen ? "Visto" : "No visto";
        viewStatusTag.classList.toggle("is-seen", isSeen);
    }
};

const createDetailMarkup = (snapshot) => {
    const descriptiveTags = (snapshot.tags || []).filter((tag) => !/^(no\s+)?visto$|^por\s+ver$/i.test(String(tag).trim()));
    const tags = [snapshot.genre, ...descriptiveTags, snapshot.year].filter(Boolean).slice(0, 3);
    const tagMarkup = tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")
        + '<span class="catalog-detail-view-status" data-view-status-tag>No visto</span>';
    const imageMarkup = snapshot.image
        ? `<img src="${escapeHtml(snapshot.image)}" alt="Imagen de ${escapeHtml(snapshot.title)}">`
        : '<div class="catalog-detail-placeholder">Imagen no disponible</div>';
    const sourceUrl = /^https:\/\//i.test(String(snapshot.sourceUrl || "")) ? snapshot.sourceUrl : "";
    const sourceMarkup = sourceUrl
        ? `<a class="catalog-detail-source" href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener noreferrer">Ver ficha externa</a>`
        : "";

    return `
        <div class="catalog-detail-content">
            <button class="catalog-detail-close" type="button" data-detail-close aria-label="Cerrar detalles">×</button>
            <div class="catalog-detail-poster">${imageMarkup}</div>
            <div class="catalog-detail-info">
                <h2 id="catalogDetailTitle">${escapeHtml(snapshot.title)}</h2>
                <div class="catalog-detail-tags">${tagMarkup}</div>
                <div class="catalog-detail-description">
                    <h3>Descripción</h3>
                    <p>${escapeHtml(snapshot.description || "No hay una descripción disponible.")}</p>
                    ${sourceMarkup}
                </div>
                <div class="catalog-detail-actions">
                    <button type="button" data-detail-action="seen" aria-pressed="false">${eyeIcon}<span>Marcar como visto</span></button>
                    <button type="button" data-detail-action="favorite" aria-pressed="false">${heartIcon}<span>Agregar a favoritos</span></button>
                </div>
            </div>
        </div>
    `;
};

const closeCatalogDetail = async ({ restoreFocus = true, immediate = false } = {}) => {
    if (!activeCatalogDetail || activeCatalogDetail.closing) {
        return;
    }

    const detailState = activeCatalogDetail;
    detailState.closing = true;
    const { overlay, shell, placeholder, card, snapshot, originBorderRadius } = detailState;
    const targetRect = placeholder.getBoundingClientRect();
    const currentRect = shell.getBoundingClientRect();
    const duration = immediate ? 1 : getAnimationDuration();

    overlay.classList.remove("is-open");
    shell.classList.remove("is-content-visible");

    await shell.animate([
        {
            top: `${currentRect.top}px`,
            left: `${currentRect.left}px`,
            width: `${currentRect.width}px`,
            height: `${currentRect.height}px`,
            borderRadius: "8px",
        },
        {
            top: `${targetRect.top}px`,
            left: `${targetRect.left}px`,
            width: `${targetRect.width}px`,
            height: `${targetRect.height}px`,
            borderRadius: originBorderRadius,
        },
    ], {
        duration,
        easing: "cubic-bezier(.22, 1, .36, 1)",
        fill: "forwards",
    }).finished.catch(() => {});

    placeholder.replaceWith(card);
    refreshCardActionState(card);
    overlay.remove();
    document.body.classList.remove("catalog-detail-open");
    activeCatalogDetail = null;

    if (restoreFocus) {
        card.focus({ preventScroll: true });
    }

    if (snapshot) {
        card.catalogItem = { ...(card.catalogItem || {}), ...snapshot };
    }
};

const openCatalogDetail = async (card) => {
    if (activeCatalogDetail || !card?.isConnected) {
        return;
    }

    const originRect = card.getBoundingClientRect();
    const originBorderRadius = getComputedStyle(card).borderRadius;
    const snapshot = getCardSnapshot(card);
    const placeholder = document.createElement("div");
    const overlay = document.createElement("div");
    const shell = document.createElement("section");
    const duration = getAnimationDuration();

    placeholder.className = "catalog-card-placeholder";
    placeholder.setAttribute("aria-hidden", "true");
    overlay.className = "catalog-detail-overlay";
    overlay.innerHTML = '<div class="catalog-detail-backdrop" data-detail-close></div>';
    shell.className = "catalog-detail-shell";
    shell.setAttribute("role", "dialog");
    shell.setAttribute("aria-modal", "true");
    shell.setAttribute("aria-labelledby", "catalogDetailTitle");
    shell.innerHTML = createDetailMarkup(snapshot);
    shell.style.cssText = `top:${originRect.top}px;left:${originRect.left}px;width:${originRect.width}px;height:${originRect.height}px;`;
    overlay.appendChild(shell);
    card.replaceWith(placeholder);
    document.body.appendChild(overlay);
    document.body.classList.add("catalog-detail-open");
    activeCatalogDetail = { overlay, shell, placeholder, card, snapshot, originBorderRadius, closing: false };
    overlay.querySelectorAll("[data-detail-close]").forEach((closeControl) => {
        closeControl.addEventListener("click", () => closeCatalogDetail());
    });
    setDetailActionState(shell, snapshot);

    requestAnimationFrame(() => overlay.classList.add("is-open"));
    const targetRect = getDetailTargetRect();
    const animation = shell.animate([
        {
            top: `${originRect.top}px`,
            left: `${originRect.left}px`,
            width: `${originRect.width}px`,
            height: `${originRect.height}px`,
            borderRadius: originBorderRadius,
        },
        {
            top: `${targetRect.top}px`,
            left: `${targetRect.left}px`,
            width: `${targetRect.width}px`,
            height: `${targetRect.height}px`,
            borderRadius: "8px",
        },
    ], {
        duration,
        easing: "cubic-bezier(.22, 1, .36, 1)",
        fill: "forwards",
    });

    window.setTimeout(() => shell.classList.add("is-content-visible"), Math.min(140, duration));
    await animation.finished.catch(() => {});
    Object.assign(shell.style, {
        top: `${targetRect.top}px`,
        left: `${targetRect.left}px`,
        width: `${targetRect.width}px`,
        height: `${targetRect.height}px`,
    });
    shell.querySelector("[data-detail-close]")?.focus({ preventScroll: true });
};

document.addEventListener("click", async (event) => {
    const actionButton = event.target.closest("[data-card-action]");

    if (!actionButton) {
        return;
    }

    event.preventDefault();

    const card = actionButton.closest(".anime-card");
    const snapshot = getCardSnapshot(card);

    try {
        if (actionButton.dataset.cardAction === "seen") {
            await AltoidssStore.toggleSeen(snapshot);
            showCatalogFeedback(
                AltoidssStore.isSeen(snapshot) ? "Marcado como visto." : "Marcado como no visto.",
                "success"
            );
        }

        if (actionButton.dataset.cardAction === "favorite") {
            await AltoidssStore.toggleFavorite(snapshot);
            showCatalogFeedback("Lista de favoritos actualizada.", "success");
        }

        refreshCardActionState(card);
        if (actionButton.dataset.cardAction === "seen") {
            animateSeenConfirmation(card);
        }
    } catch (error) {
        showCatalogFeedback(error.message || "No se pudo completar la acción.");
    }
});

document.addEventListener("click", async (event) => {
    if (event.target.closest("[data-detail-close]")) {
        await closeCatalogDetail();
        return;
    }

    const detailAction = event.target.closest("[data-detail-action]");

    if (detailAction && activeCatalogDetail) {
        const { shell, snapshot } = activeCatalogDetail;
        detailAction.disabled = true;

        try {
            if (detailAction.dataset.detailAction === "seen") {
                await AltoidssStore.toggleSeen(snapshot);
            }

            if (detailAction.dataset.detailAction === "favorite") {
                await AltoidssStore.toggleFavorite(snapshot);
            }

            setDetailActionState(shell, snapshot);
            if (detailAction.dataset.detailAction === "seen") {
                animateSeenConfirmation(shell);
            }
        } catch (error) {
            showCatalogFeedback(error.message || "No se pudo completar la acción.");
        } finally {
            detailAction.disabled = false;
        }

        return;
    }

    const card = event.target.closest(".anime-card");

    if (card && !event.target.closest("button, a")) {
        await openCatalogDetail(card);
    }
});

document.addEventListener("keydown", async (event) => {
    if (activeCatalogDetail) {
        if (event.key === "Escape") {
            event.preventDefault();
            await closeCatalogDetail();
            return;
        }

        if (event.key === "Tab") {
            const focusable = [...activeCatalogDetail.shell.querySelectorAll("button:not(:disabled), a[href]")];
            const firstItem = focusable[0];
            const lastItem = focusable.at(-1);

            if (event.shiftKey && document.activeElement === firstItem) {
                event.preventDefault();
                lastItem?.focus();
            } else if (!event.shiftKey && document.activeElement === lastItem) {
                event.preventDefault();
                firstItem?.focus();
            }
        }

        return;
    }

    const card = event.target.closest?.(".anime-card");

    if (card && event.target === card && ["Enter", " "].includes(event.key)) {
        event.preventDefault();
        await openCatalogDetail(card);
    }
});

window.addEventListener("resize", () => {
    if (!activeCatalogDetail || activeCatalogDetail.closing) {
        return;
    }

    const targetRect = getDetailTargetRect();
    Object.assign(activeCatalogDetail.shell.style, {
        top: `${targetRect.top}px`,
        left: `${targetRect.left}px`,
        width: `${targetRect.width}px`,
        height: `${targetRect.height}px`,
    });
});

// Al hacer clic, se cambia la variable CSS --cards-per-row.
gridButtons.forEach((button) => {
    button.addEventListener("click", async () => {
        catalogGrids.forEach((grid) => {
            grid.style.setProperty("--cards-per-row", button.dataset.grid);
        });

        await AltoidssStore.updateSettings({
            cardsPerRow: Number(button.dataset.grid),
        });

        // Actualiza el color del botón seleccionado para mostrar el estado activo.
        gridButtons.forEach((item) => {
            item.classList.toggle("btn-primary", item === button);
            item.classList.toggle("btn-outline-light", item !== button);
        });
    });
});

catalogViewButtons.forEach((button) => {
    button.addEventListener("click", async () => {
        const preferredView = button.dataset.catalogView === "list" ? "list" : "cards";
        applyCatalogView(preferredView);

        try {
            await AltoidssStore.updateSettings({ preferredView });
        } catch (error) {
            console.warn("La vista se aplicó solo durante esta sesión.", error);
        }
    });
});

const getCategoryFromUrl = () => {
    const category = new URLSearchParams(window.location.search).get("category");
    return allowedCategories.includes(category) ? category : "movies";
};

const openRequestedCatalogDetail = async (category) => {
    const requestedId = new URLSearchParams(window.location.search).get("focus");

    if (!requestedId) {
        return;
    }

    const categoryItems = getCategoryItems(category);
    const itemIndex = categoryItems.findIndex((item) => item.id === requestedId);

    if (itemIndex < 0) {
        showCatalogFeedback("El contenido solicitado ya no está disponible.");
        return;
    }

    currentPages[category] = Math.floor(itemIndex / ITEMS_PER_PAGE) + 1;
    renderCatalogPage(category);
    const requestedCard = [...document.querySelectorAll(`#catalog-${category} .anime-card`)]
        .find((card) => card.dataset.contentId === requestedId);

    if (requestedCard) {
        requestedCard.scrollIntoView({ block: "center", behavior: "auto" });
        await openCatalogDetail(requestedCard);
    }
};

const selectCategory = (selectedCategory) => {
    const category = allowedCategories.includes(selectedCategory) ? selectedCategory : "movies";

    catalogPanels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.id === `catalog-${category}`);
    });

    categoryButtons.forEach((item) => {
        const isSelected = item.dataset.categoryView === category;
        item.classList.toggle("btn-primary", isSelected);
        item.classList.toggle("btn-outline-light", !isSelected);
    });
};

const performCatalogSearch = async (query, category = getCategoryFromUrl()) => {
    const normalizedQuery = String(query || "").trim();
    currentPages[category] = 1;
    updatePageInUrl(category, 1);

    if (!normalizedQuery) {
        await renderStoredContent(AltoidssStore.read());
        configureFilterPanel(category);
        applyCurrentFilters(category);
        showCatalogFeedback("Se restauró el catálogo completo.", "success");
        return;
    }

    const results = await AltoidssStore.searchCatalog(category, normalizedQuery);
    const otherCategories = AltoidssStore.read().filter((item) => item.type !== category);
    await renderStoredContent([...otherCategories, ...results]);
    selectCategory(category);
    configureFilterPanel(category);
    applyCurrentFilters(category);

    showCatalogFeedback(
        results.length
            ? `${results.length} resultado(s) encontrados.`
            : "No se encontraron resultados para esta búsqueda.",
        results.length ? "success" : "error"
    );
};

const initializeCatalog = async () => {
    await AltoidssStore.initialize();
    const category = getCategoryFromUrl();
    const requestedPage = Number(new URLSearchParams(window.location.search).get("page"));
    currentPages[category] = Number.isInteger(requestedPage) && requestedPage > 0 ? requestedPage : 1;
    await renderStoredContent(AltoidssStore.read());
    configureFilterPanel(category, true);
    enhanceCatalogCards();
    applyStoredGridPreference();
    applyCatalogView(AltoidssStore.getProfile().settings?.preferredView || "cards");
    const initialQuery = new URLSearchParams(window.location.search).get("query") || "";
    selectCategory(category);

    if (initialQuery) {
        catalogSearchInput.value = initialQuery;
        await performCatalogSearch(initialQuery, category);
    }

    await openRequestedCatalogDetail(category);
};

initializeCatalog();

catalogFilterForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = catalogSearchInput.value.trim();
    const category = getCategoryFromUrl();
    readFilterControls(category);
    const params = new URLSearchParams(window.location.search);
    params.set("category", category);
    query ? params.set("query", query) : params.delete("query");
    window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
    await performCatalogSearch(query, category);
    if (window.matchMedia("(max-width: 768px)").matches) {
        setMobileFiltersOpen(false);
    }
});

[filterInitial, filterGenre, filterFormat, filterSeasons, filterStatus].forEach((control) => {
    control?.addEventListener("change", () => {
        const category = getCategoryFromUrl();
        readFilterControls(category);
        applyCurrentFilters(category);
    });
});

[filterYearMin, filterYearMax].forEach((control) => {
    control?.addEventListener("input", () => {
        const category = getCategoryFromUrl();
        readFilterControls(category);
        applyCurrentFilters(category);
    });
});

clearCatalogFilters?.addEventListener("click", async () => {
    const category = getCategoryFromUrl();
    catalogFilters[category] = createFilterState();
    catalogSearchInput.value = "";
    const params = new URLSearchParams(window.location.search);
    params.delete("query");
    params.delete("page");
    window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
    await renderStoredContent(AltoidssStore.read());
    configureFilterPanel(category, true);
    applyCurrentFilters(category);
    showCatalogFeedback("Filtros restablecidos.", "success");
});

// Cambia la vista preliminar entre Películas, Series TV y Anime.
categoryButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const category = button.dataset.categoryView;
        currentPages[category] = 1;
        selectCategory(category);
        const params = new URLSearchParams(window.location.search);
        params.set("category", category);
        params.delete("page");
        window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
        configureFilterPanel(category);
        renderCatalogPage(category);
    });
});

document.addEventListener("click", (event) => {
    const pageButton = event.target.closest("[data-pagination-category][data-page]");

    if (!pageButton || pageButton.disabled) {
        return;
    }

    const category = pageButton.dataset.paginationCategory;
    const requestedPage = Number(pageButton.dataset.page);
    const totalPages = Math.max(1, Math.ceil(getCategoryItems(category).length / ITEMS_PER_PAGE));

    if (!allowedCategories.includes(category) || !Number.isInteger(requestedPage)) {
        return;
    }

    currentPages[category] = Math.min(Math.max(1, requestedPage), totalPages);
    renderCatalogPage(category);
    updatePageInUrl(category, currentPages[category]);
    document.querySelector(".section-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
});

