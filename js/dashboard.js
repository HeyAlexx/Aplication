// Elementos principales del formulario CRUD de contenido.
const contentForm = document.querySelector("#contentForm");
const contentId = document.querySelector("#contentId");
const contentTitle = document.querySelector("#contentTitle");
const contentType = document.querySelector("#contentType");
const contentFormat = document.querySelector("#contentFormat");
const contentProductionStatus = document.querySelector("#contentProductionStatus");
const contentGenre = document.querySelector("#contentGenre");
const contentYear = document.querySelector("#contentYear");
const contentSeason = document.querySelector("#contentSeason");
const contentChapters = document.querySelector("#contentChapters");
const contentSeasonsCount = document.querySelector("#contentSeasonsCount");
const contentTags = document.querySelector("#contentTags");
const contentImage = document.querySelector("#contentImage");
const contentDescription = document.querySelector("#contentDescription");
const contentTableBody = document.querySelector("#contentTableBody");
const jsonPreview = document.querySelector("#jsonPreview");
const animeReviewList = document.querySelector("#animeReviewList");
const reviewCount = document.querySelector("#reviewCount");
const reviewFilterButtons = document.querySelectorAll("[data-review-filter]");
const cancelEditButton = document.querySelector("#cancelEditButton");
const saveContentButton = document.querySelector("#saveContentButton");

// Elementos del CRUD de noticias tipo blog.
const newsForm = document.querySelector("#newsForm");
const newsId = document.querySelector("#newsId");
const newsTitle = document.querySelector("#newsTitle");
const newsCategory = document.querySelector("#newsCategory");
const newsStatus = document.querySelector("#newsStatus");
const newsDate = document.querySelector("#newsDate");
const newsSummary = document.querySelector("#newsSummary");
const newsImage = document.querySelector("#newsImage");
const newsTrailerUrl = document.querySelector("#newsTrailerUrl");
const newsRelated = document.querySelector("#newsRelated");
const newsFeatured = document.querySelector("#newsFeatured");
const newsBody = document.querySelector("#newsBody");
const saveNewsButton = document.querySelector("#saveNewsButton");
const cancelNewsEditButton = document.querySelector("#cancelNewsEditButton");
const crudModeButtons = document.querySelectorAll("[data-crud-mode]");
const crudModePanels = document.querySelectorAll("[data-crud-panel]");
const tableModeButtons = document.querySelectorAll("[data-table-mode]");

const metricSeriesSeen = document.querySelector("#metricSeriesSeen");
const metricMoviesSeen = document.querySelector("#metricMoviesSeen");
const metricAnimeSeen = document.querySelector("#metricAnimeSeen");
const metricFavorites = document.querySelector("#metricFavorites");
const metricTopGenre = document.querySelector("#metricTopGenre");
const metricLastVisit = document.querySelector("#metricLastVisit");
const metricWatchTime = document.querySelector("#metricWatchTime");
const activeProfileName = document.querySelector("#activeProfileName");
const dashboardRoleLabel = document.querySelector("#dashboardRoleLabel");
const dashboardIntro = document.querySelector("#dashboardIntro");
const profileNote = document.querySelector("#profileNote");
const dashboardTabButtons = document.querySelectorAll("[data-dashboard-tab]");
const dashboardTabTrack = document.querySelector("#dashboardTabTrack");
const adminOnlyControls = document.querySelectorAll(".admin-only-control");
const profileForm = document.querySelector("#profileForm");
const profileName = document.querySelector("#profileName");
const profileEmail = document.querySelector("#profileEmail");
const profileSocial = document.querySelector("#profileSocial");
const profileAvatar = document.querySelector("#profileAvatar");
const profileAbout = document.querySelector("#profileAbout");
const avatarPreview = document.querySelector("#avatarPreview");
const settingsForm = document.querySelector("#settingsForm");
const settingCardsPerRow = document.querySelector("#settingCardsPerRow");
const settingPreferredView = document.querySelector("#settingPreferredView");
const settingCompactMode = document.querySelector("#settingCompactMode");
const chartTotalContent = document.querySelector("#chartTotalContent");
const barMoviesValue = document.querySelector("#barMoviesValue");
const barSeriesValue = document.querySelector("#barSeriesValue");
const barAnimeValue = document.querySelector("#barAnimeValue");
const donutSeenValue = document.querySelector("#donutSeenValue");
const watchDonut = document.querySelector("#watchDonut");
const genreRadarPolygon = document.querySelector("#genreRadarPolygon");
const activityLine = document.querySelector("#activityLine");
const activityAreaLine = document.querySelector("#activityAreaLine");
const activityPeakLabel = document.querySelector("#activityPeakLabel");

const typeLabels = {
    movies: "Películas",
    series: "Series TV",
    anime: "Anime",
};

const dashboardTabs = ["overview", "crud", "json", "review", "table", "profile", "settings"];
let activeDashboardTab = "overview";
let activeCrudMode = "content";
let activeTableMode = "content";
let activeReviewFilter = "active";
let animeReviews = [];

const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

let dashboardFeedbackTimer = null;

const showDashboardFeedback = (message, type = "error") => {
    let feedback = document.querySelector("#dashboardFeedback");

    if (!feedback) {
        feedback = document.createElement("div");
        feedback.id = "dashboardFeedback";
        feedback.className = "dashboard-feedback";
        feedback.setAttribute("role", "status");
        document.querySelector(".section-heading")?.after(feedback);
    }

    feedback.textContent = message;
    feedback.classList.toggle("is-error", type === "error");
    feedback.classList.toggle("is-success", type === "success");
    feedback.classList.add("is-visible");

    clearTimeout(dashboardFeedbackTimer);
    dashboardFeedbackTimer = setTimeout(() => {
        feedback.classList.remove("is-visible");
    }, 5200);
};

const splitCommaList = (value) => String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

const getToday = () => new Date().toISOString().slice(0, 10);
const getCurrentYear = () => new Date().getFullYear();
const allowedEmissionSeasons = ["Winter", "Spring", "Summer", "Fall"];

const validateContentForm = () => {
    const currentYear = getCurrentYear();
    const emissionYear = Number(contentYear.value);
    const seasonNumber = Number(contentSeasonsCount.value);

    if (!contentTitle.value.trim()) {
        throw new Error("El título es obligatorio.");
    }

    if (!contentGenre.value.trim()) {
        throw new Error("El género principal es obligatorio.");
    }

    if (!Number.isInteger(emissionYear) || emissionYear < 1900 || emissionYear > currentYear + 2) {
        throw new Error(`El año de emisión debe estar entre 1900 y ${currentYear + 2}.`);
    }

    if (!allowedEmissionSeasons.includes(contentSeason.value)) {
        throw new Error("Seleccione una temporada de emisión válida.");
    }

    if (!Number.isInteger(seasonNumber) || seasonNumber < 1) {
        throw new Error("N. temporada debe ser un número mayor o igual a 1.");
    }
};

// Convierte el formulario de contenido en un objeto JSON listo para guardar.
const getFormData = () => ({
    title: contentTitle.value.trim(),
    type: contentType.value,
    categoryGeneral: typeLabels[contentType.value] || contentType.value,
    format: contentFormat.value,
    productionStatus: contentProductionStatus.value,
    genre: contentGenre.value.trim(),
    year: contentYear.value.trim(),
    emissionYear: Number(contentYear.value) || null,
    emissionSeason: contentSeason.value,
    chapters: Number(contentChapters.value) || 0,
    seasonsCount: Number(contentSeasonsCount.value),
    tags: splitCommaList(contentTags.value),
    image: contentImage.value.trim(),
    description: contentDescription.value.trim(),
    status: "Activo",
});

const getNewsFormData = () => {
    const title = newsTitle.value.trim();

    return {
        title,
        slug: title.toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-|-$/g, ""),
        category: newsCategory.value,
        status: newsStatus.value,
        publishedAt: newsDate.value || getToday(),
        summary: newsSummary.value.trim(),
        image: newsImage.value.trim(),
        trailerUrl: newsTrailerUrl.value.trim(),
        trailerLabel: "Tráiler oficial",
        relatedContent: splitCommaList(newsRelated.value),
        featured: newsFeatured.checked,
        body: newsBody.value.trim(),
        views: 0,
    };
};

const resetForm = () => {
    contentForm.reset();
    contentId.value = "";
    contentYear.value = getCurrentYear();
    contentSeason.value = getCurrentEmissionSeason();
    contentSeasonsCount.value = 1;
    contentForm.classList.remove("is-editing");
    saveContentButton.textContent = "Guardar contenido";
};

const getCurrentEmissionSeason = () => {
    const month = new Date().getMonth() + 1;

    if (month <= 3) return "Winter";
    if (month <= 6) return "Spring";
    if (month <= 9) return "Summer";
    return "Fall";
};

const resetNewsForm = () => {
    newsForm.reset();
    newsId.value = "";
    newsDate.value = getToday();
    newsForm.classList.remove("is-editing");
    saveNewsButton.textContent = "Guardar noticia";
};

const loadItemForEdit = (item) => {
    setCrudMode("content");
    contentId.value = item.id;
    contentTitle.value = item.title || "";
    contentType.value = item.type || "anime";
    contentFormat.value = item.format || (item.type === "movies" ? "Película" : "Serie");
    contentProductionStatus.value = item.productionStatus || "Finalizado";
    contentGenre.value = item.genre || "";
    contentYear.value = item.emissionYear || item.year || "";
    contentSeason.value = item.emissionSeason || "";
    contentChapters.value = item.chapters || "";
    contentSeasonsCount.value = item.seasonsCount || item.numberOfSeasons || "";
    contentTags.value = (item.tags || []).join(", ");
    contentImage.value = item.image || "";
    contentDescription.value = item.description || "";
    contentForm.classList.add("is-editing");
    saveContentButton.textContent = "Actualizar contenido";
    contentTitle.focus();
};

const loadNewsForEdit = (item) => {
    setCrudMode("news");
    newsId.value = item.id;
    newsTitle.value = item.title || "";
    newsCategory.value = item.category || "Estrenos";
    newsStatus.value = item.status || "borrador";
    newsDate.value = item.publishedAt || getToday();
    newsSummary.value = item.summary || "";
    newsImage.value = item.image || "";
    newsTrailerUrl.value = item.trailerUrl || "";
    newsRelated.value = (item.relatedContent || []).join(", ");
    newsFeatured.checked = Boolean(item.featured);
    newsBody.value = item.body || "";
    newsForm.classList.add("is-editing");
    saveNewsButton.textContent = "Actualizar noticia";
    newsTitle.focus();
};

const renderContentTable = (items = AltoidssStore.read()) => {
    if (!items.length) {
        contentTableBody.innerHTML = '<tr><td colspan="5">No hay contenido JSON agregado todavía.</td></tr>';
        return;
    }

    contentTableBody.innerHTML = items.map((item) => `
        <tr>
            <td>${escapeHtml(item.title)}</td>
            <td>${escapeHtml(item.emissionYear || item.year || "Sin año")}</td>
            <td>${escapeHtml(typeLabels[item.type] ?? item.type)}</td>
            <td><span class="status-badge ${getProductionStatusClass(item.productionStatus || item.status)}">${escapeHtml(item.productionStatus || item.status)}</span></td>
            <td class="text-end">
                <div class="admin-action-group">
                    <button class="btn btn-sm btn-outline-light" type="button" data-edit-id="${item.id}">Editar</button>
                    <button class="btn btn-sm btn-outline-danger" type="button" data-delete-id="${item.id}">Ocultar</button>
                </div>
            </td>
        </tr>
    `).join("");
};

const getProductionStatusClass = (status) => {
    const normalized = String(status || "").toLowerCase();

    if (normalized.includes("finalizado")) return "status-finished";
    if (normalized.includes("pausado")) return "status-paused";
    return "status-airing";
};

const renderNewsTable = (items = AltoidssStore.readNews()) => {
    if (!items.length) {
        contentTableBody.innerHTML = '<tr><td colspan="5">No hay noticias JSON agregadas todavía.</td></tr>';
        return;
    }

    contentTableBody.innerHTML = items.map((item) => `
        <tr>
            <td>${escapeHtml(item.title)}</td>
            <td>${escapeHtml(item.category)}</td>
            <td>${escapeHtml(item.featured ? "Destacada" : "Blog")}</td>
            <td><span class="badge text-bg-info">${escapeHtml(item.status)}</span></td>
            <td class="text-end">
                <div class="admin-action-group">
                    <button class="btn btn-sm btn-outline-light" type="button" data-edit-news-id="${item.id}">Editar</button>
                    <button class="btn btn-sm btn-outline-danger" type="button" data-delete-news-id="${item.id}">Ocultar</button>
                </div>
            </td>
        </tr>
    `).join("");
};

const renderTable = () => {
    if (activeTableMode === "news") {
        renderNewsTable();
        return;
    }

    renderContentTable();
};

const renderJsonPreview = () => {
    jsonPreview.textContent = JSON.stringify(AltoidssStore.exportDatabase(), null, 2);
};

const reviewFields = [
    ["title", "Título"],
    ["format", "Formato"],
    ["productionStatus", "Emisión"],
    ["chapters", "Capítulos"],
    ["seasonsCount", "Temporadas"],
    ["activeSeason", "Temporada activa"],
    ["emissionYear", "Año"],
    ["emissionSeason", "Temporada del año"],
];

const reviewEditorFields = [
    { key: "title", label: "Título principal", type: "text", wide: true, required: true },
    { key: "alternativeTitles", label: "Títulos alternos", type: "textarea", valueType: "array-lines", wide: true },
    { key: "format", label: "Formato", type: "select", options: ["Serie", "Película", "OVA", "ONA", "Especial", "Corto"] },
    { key: "productionStatus", label: "Estado de emisión", type: "select", options: ["Emisión", "Finalizado", "Pausado", "Próximamente", "Cancelado", "Pendiente"] },
    { key: "chapters", label: "Capítulos", type: "number", min: 0 },
    { key: "seasonsCount", label: "Número de temporadas", type: "number", min: 0 },
    { key: "activeSeason", label: "Temporada activa", type: "text" },
    { key: "emissionYear", label: "Año de emisión", type: "number", min: 0, max: 2100 },
    { key: "emissionSeason", label: "Temporada del año", type: "select", options: ["", "Winter", "Spring", "Summer", "Fall"] },
    { key: "genre", label: "Género principal", type: "text" },
    { key: "metadataGenres", label: "Géneros", type: "text", valueType: "array-comma", wide: true },
    { key: "rating", label: "Calificación", type: "number", min: 0, max: 10, step: "0.1" },
    { key: "image", label: "URL de imagen", type: "url", wide: true },
    { key: "description", label: "Sinopsis", type: "textarea", wide: true },
    { key: "sourceUrl", label: "URL de la fuente", type: "url", wide: true },
    { key: "externalTitle", label: "Título externo", type: "text", wide: true },
    { key: "metadataProvider", label: "Proveedor", type: "text" },
    { key: "metadataMatchScore", label: "Coincidencia API", type: "number", min: 0, max: 1, step: "0.01" },
    { key: "jikanId", label: "ID Jikan", type: "text" },
    { key: "anilistId", label: "ID AniList", type: "text" },
    { key: "kitsuId", label: "ID Kitsu", type: "text" },
];

const reviewStructuralFields = new Set([
    "title", "format", "productionStatus", "chapters", "seasonsCount",
    "activeSeason", "emissionYear", "emissionSeason",
]);

const hasReviewValue = (value) => value !== undefined
    && value !== null
    && value !== ""
    && (!Array.isArray(value) || value.length > 0);

const buildReviewPreset = (review, preset = "current") => {
    if (preset === "original") return { ...(review.original || {}) };
    if (preset === "api") return { ...(review.apiVersion || {}) };
    if (preset === "current" && review.finalVersion) return { ...review.finalVersion };

    const combined = { ...(review.original || {}) };
    reviewEditorFields.forEach(({ key }) => {
        const apiValue = review.apiVersion?.[key];
        if (hasReviewValue(apiValue) && (!reviewStructuralFields.has(key) || !hasReviewValue(combined[key]))) {
            combined[key] = apiValue;
        }
    });
    return combined;
};

const formatReviewInputValue = (value, valueType) => {
    if (!Array.isArray(value)) return value ?? "";
    return value.join(valueType === "array-lines" ? "\n" : ", ");
};

const renderReviewInput = (field, value) => {
    const attributes = [
        `data-final-field="${field.key}"`,
        `data-value-type="${field.valueType || "string"}"`,
        `aria-label="${escapeHtml(field.label)}"`,
        field.required ? "required" : "",
        field.min !== undefined ? `min="${field.min}"` : "",
        field.max !== undefined ? `max="${field.max}"` : "",
        field.step ? `step="${field.step}"` : "",
    ].filter(Boolean).join(" ");
    const formatted = formatReviewInputValue(value, field.valueType);

    if (field.type === "textarea") {
        return `<textarea class="form-control" rows="${field.key === "description" ? 5 : 3}" ${attributes}>${escapeHtml(formatted)}</textarea>`;
    }
    if (field.type === "select") {
        const availableOptions = field.options.includes(String(formatted))
            ? field.options
            : [...field.options, String(formatted)];
        const options = availableOptions.map((option) => `
            <option value="${escapeHtml(option)}" ${String(formatted) === option ? "selected" : ""}>${escapeHtml(option || "Sin especificar")}</option>
        `).join("");
        return `<select class="form-select" ${attributes}>${options}</select>`;
    }
    return `<input class="form-control" type="${field.type}" value="${escapeHtml(formatted)}" ${attributes}>`;
};

const renderReviewEditor = (review) => {
    const finalVersion = buildReviewPreset(review);
    const fields = reviewEditorFields.map((field) => {
        const originalAvailable = hasReviewValue(review.original?.[field.key]);
        const apiAvailable = hasReviewValue(review.apiVersion?.[field.key]);
        return `
            <div class="review-edit-field ${field.wide ? "is-wide" : ""}">
                <span class="review-edit-label">
                    <strong>${escapeHtml(field.label)}</strong>
                    <span class="review-source-buttons" aria-label="Copiar valor para ${escapeHtml(field.label)}">
                        <button type="button" data-review-copy="original" data-review-field="${field.key}" ${originalAvailable ? "" : "disabled"}>Original</button>
                        <button type="button" data-review-copy="api" data-review-field="${field.key}" ${apiAvailable ? "" : "disabled"}>API</button>
                    </span>
                </span>
                ${renderReviewInput(field, finalVersion[field.key])}
                ${field.key === "sourceUrl" ? `
                    <div class="review-source-import">
                        <p>Compatible con MyAnimeList, AniList y Kitsu.</p>
                        <button class="btn btn-outline-light" type="button" data-review-source-fetch>Obtener datos desde URL</button>
                    </div>
                ` : ""}
            </div>
        `;
    }).join("");

    return `
        <section class="review-final-editor" data-review-editor>
            <div class="review-editor-heading">
                <div>
                    <span class="review-version-label">Versión final editable</span>
                    <p>Combina ambas fuentes o corrige cualquier dato manualmente.</p>
                </div>
                <div class="review-presets btn-group btn-group-sm" role="group" aria-label="Copiar conjunto de datos">
                    <button class="btn btn-outline-light" type="button" data-review-preset="original">Todo original</button>
                    <button class="btn btn-outline-light" type="button" data-review-preset="combined">Combinar</button>
                    <button class="btn btn-outline-light" type="button" data-review-preset="api" ${review.apiVersion ? "" : "disabled"}>Todo API</button>
                </div>
            </div>
            <div class="review-edit-grid">${fields}</div>
        </section>
    `;
};

const renderReviewVersion = (version, label, image = "") => {
    if (!version) {
        return `
            <section class="review-version is-empty">
                <span class="review-version-label">${escapeHtml(label)}</span>
                <p>No se obtuvo una versión candidata.</p>
            </section>
        `;
    }

    const rows = reviewFields.map(([key, fieldLabel]) => `
        <div class="review-field">
            <span>${escapeHtml(fieldLabel)}</span>
            <strong>${escapeHtml(version[key] === 0 ? "0" : (version[key] || "—"))}</strong>
        </div>
    `).join("");
    const alternatives = (version.alternativeTitles || []).slice(0, 3);

    return `
        <section class="review-version">
            <span class="review-version-label">${escapeHtml(label)}</span>
            ${image ? `<img class="review-poster" src="${escapeHtml(image)}" alt="Portada de ${escapeHtml(version.title || "anime")}">` : ""}
            <div class="review-field-list">${rows}</div>
            ${alternatives.length ? `
                <div class="review-alternatives">
                    <span>Nombres alternativos</span>
                    <p>${alternatives.map(escapeHtml).join(" · ")}</p>
                </div>
            ` : ""}
            ${version.description ? `<p class="review-synopsis">${escapeHtml(version.description)}</p>` : ""}
            ${version.sourceUrl ? `<a class="review-source" href="${escapeHtml(version.sourceUrl)}" target="_blank" rel="noopener noreferrer">Abrir fuente</a>` : ""}
        </section>
    `;
};

const isUnresolvedReview = (review) => ["Pendiente", "Rechazado automático"].includes(review.status);

let reviewToastTimer;
const showReviewToast = (message, success = false) => {
    let toast = document.querySelector('#reviewSourceToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'reviewSourceToast';
        toast.className = 'review-source-toast';
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', 'polite');
        document.body.append(toast);
    }
    toast.textContent = message;
    toast.classList.toggle('is-success', success);
    toast.hidden = false;
    clearTimeout(reviewToastTimer);
    reviewToastTimer = setTimeout(() => { toast.hidden = true; }, 5200);
};

const renderAnimeReviews = () => {
    if (!animeReviewList) return;

    const pendingCount = animeReviews.filter(isUnresolvedReview).length;
    reviewCount.textContent = `${pendingCount} ${pendingCount === 1 ? "pendiente" : "pendientes"}`;
    const visible = activeReviewFilter === "active"
        ? animeReviews.filter(isUnresolvedReview)
        : animeReviews;

    if (!visible.length) {
        animeReviewList.innerHTML = '<p class="review-empty">No hay registros en esta vista.</p>';
        return;
    }

    animeReviewList.innerHTML = visible.map((review) => {
        const unresolved = isUnresolvedReview(review);
        const badgeClass = review.status === "Aprobado"
            ? "is-approved"
            : review.status === "Rechazado" || review.status === "Rechazado automático"
                ? "is-rejected"
                : "is-pending";
        return `
            <article class="review-card" data-review-id="${escapeHtml(review.id)}">
                <header class="review-card-head">
                    <div>
                        <span class="review-code">Código ${escapeHtml(review.sourceCode)}</span>
                        <h3>${escapeHtml(review.title)}</h3>
                    </div>
                    <span class="review-status ${badgeClass}">${escapeHtml(review.status)}</span>
                </header>
                <div class="review-differences">
                    ${(review.differences || []).map((difference) => `<span>${escapeHtml(difference)}</span>`).join("")}
                    <strong>${Math.round(Number(review.matchScore || 0) * 100)}% coincidencia</strong>
                </div>
                <div class="review-comparison">
                    ${renderReviewVersion(review.original, "Original")}
                    ${renderReviewVersion(review.apiVersion, `API · ${review.apiVersion?.metadataProvider || "sin proveedor"}`, review.apiVersion?.image)}
                </div>
                ${renderReviewEditor(review)}
                ${!unresolved ? `<p class="review-resolution">${escapeHtml(review.resolutionType || "Revisión guardada")} por ${escapeHtml(review.reviewedBy || "Administrador")}${review.reviewNotes ? `: ${escapeHtml(review.reviewNotes)}` : ""}</p>` : ""}
                <div class="review-actions">
                    <input class="form-control" data-review-notes type="text" value="${escapeHtml(review.reviewNotes || "")}" placeholder="Nota opcional de la decisión">
                    <button class="btn btn-primary" data-review-decision="save" type="button">Guardar versión final</button>
                    <button class="btn btn-outline-danger" data-review-decision="reject" type="button">Rechazar propuesta</button>
                </div>
            </article>
        `;
    }).join("");
};

const loadAnimeReviews = async () => {
    if (AltoidssAuth.getSession().profileMode !== "admin") {
        animeReviews = [];
        renderAnimeReviews();
        return;
    }
    animeReviews = await AltoidssApi.get("/reviews/anime");
    renderAnimeReviews();
};

const setReviewEditorField = (card, key, value) => {
    const input = card.querySelector(`[data-final-field="${key}"]`);
    const field = reviewEditorFields.find((item) => item.key === key);
    if (!input || !field) return;

    const formatted = String(formatReviewInputValue(value, field.valueType));
    if (input instanceof HTMLSelectElement && ![...input.options].some((option) => option.value === formatted)) {
        input.add(new Option(formatted || "Sin especificar", formatted));
    }
    input.value = formatted;
    input.closest(".review-edit-field")?.classList.remove("is-manual");
};

const setReviewEditorValues = (card, values) => {
    reviewEditorFields.forEach(({ key }) => setReviewEditorField(card, key, values?.[key]));
};

const collectReviewEditorData = (card) => Object.fromEntries(reviewEditorFields.map((field) => {
    const input = card.querySelector(`[data-final-field="${field.key}"]`);
    const value = input?.value.trim() || "";

    if (field.valueType === "array-lines") {
        return [field.key, value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean)];
    }
    if (field.valueType === "array-comma") {
        return [field.key, value.split(",").map((item) => item.trim()).filter(Boolean)];
    }
    if (field.type === "number") {
        return [field.key, value === "" ? 0 : Number(value)];
    }
    return [field.key, value];
}));

const countType = (items, type) => items.filter((item) => item.type === type).length;

const buildLinePoints = (values) => {
    const maxValue = Math.max(...values, 1);
    const width = 640;
    const height = 140;
    const step = width / (values.length - 1);

    return values.map((value, index) => {
        const x = Math.round(index * step);
        const y = Math.round(height - ((value / maxValue) * 96) - 22);
        return `${x},${y}`;
    }).join(" ");
};

const buildRadarPoints = (values) => {
    const center = { x: 90, y: 90 };
    const angles = [-90, -18, 54, 126, 198];
    const maxValue = Math.max(...values, 1);

    return values.map((value, index) => {
        const radius = 28 + ((value / maxValue) * 48);
        const angle = angles[index] * (Math.PI / 180);
        const x = Math.round(center.x + Math.cos(angle) * radius);
        const y = Math.round(center.y + Math.sin(angle) * radius);
        return `${x},${y}`;
    }).join(" ");
};

const renderCharts = (summary) => {
    const items = AltoidssStore.read();
    const profile = summary.profile;
    const seenSet = new Set(profile.seenIds || []);
    const chartItems = items.filter((item) => seenSet.has(item.id));
    const movies = summary.favoriteMovies || 0;
    const series = summary.favoriteSeries || 0;
    const anime = summary.favoriteAnime || 0;
    const total = Math.max(movies + series + anime, 1);
    const roundedSeenPercent = Math.round((summary.seenTotal / Math.max(items.length, 1)) * 100);
    const seenPercent = summary.seenTotal > 0 ? Math.max(1, Math.min(100, roundedSeenPercent)) : 0;
    const genreValues = ["Acción", "Drama", "Aventura", "Comedia", "Fantasía"].map((genre) => (
        chartItems.filter((item) => {
            const text = `${item.genre || ""} ${(item.tags || []).join(" ")}`.toLowerCase();
            return text.includes(genre.toLowerCase());
        }).length
    ));
    const activityValues = [
        movies + 1,
        series + 2,
        anime + 2,
        summary.favoriteTotal + 3,
        summary.seenTotal + 2,
        Math.max(1, Math.round(summary.watchTimeMinutes / 180)),
        Math.max(2, chartItems.length),
        summary.favoriteTotal + summary.seenTotal + 2,
        total + 3,
    ];
    const points = buildLinePoints(activityValues);

    chartTotalContent.textContent = summary.favoriteTotal;
    barMoviesValue.textContent = movies;
    barSeriesValue.textContent = series;
    barAnimeValue.textContent = anime;

    document.querySelector("[data-type-bar='movies']").style.width = `${Math.max(8, (movies / total) * 100)}%`;
    document.querySelector("[data-type-bar='series']").style.width = `${Math.max(8, (series / total) * 100)}%`;
    document.querySelector("[data-type-bar='anime']").style.width = `${Math.max(8, (anime / total) * 100)}%`;

    donutSeenValue.textContent = `${seenPercent}%`;
    watchDonut.style.setProperty("--donut-deg", `${seenPercent * 3.6}deg`);
    genreRadarPolygon.setAttribute("points", buildRadarPoints(genreValues));
    activityLine.setAttribute("points", points);
    activityAreaLine.setAttribute("points", points);
    activityPeakLabel.textContent = `${Math.max(...activityValues)} pts`;
};

const renderMetrics = async () => {
    const summary = await AltoidssStore.getDashboardSummary();
    const hours = Math.floor(summary.watchTimeMinutes / 60);
    const minutes = summary.watchTimeMinutes % 60;

    metricSeriesSeen.textContent = summary.seriesSeen;
    metricMoviesSeen.textContent = summary.moviesSeen;
    metricAnimeSeen.textContent = summary.animeSeen;
    metricFavorites.textContent = summary.favoriteTotal;
    metricTopGenre.textContent = summary.topGenre;
    metricLastVisit.textContent = summary.lastVisit;
    metricWatchTime.textContent = hours ? `${hours} h ${minutes} min` : `${minutes} min`;
    activeProfileName.textContent = summary.profile.displayName;
    dashboardRoleLabel.textContent = summary.profile.role;
    renderCharts(summary);

    const roleMessages = {
        visitante: "El visitante ve una lectura general limitada antes de iniciar sesión.",
        usuario: "El usuario registrado ve su progreso, favoritos y contenido visto.",
        admin: "El administrador ve las métricas de su perfil y las herramientas de gestión CRUD.",
    };

    dashboardIntro.textContent = roleMessages[summary.profile.role];
    profileNote.textContent = roleMessages[summary.profile.role];
    document.body.classList.toggle("is-admin-profile", summary.profile.role === "admin");
    adminOnlyControls.forEach((control) => {
        control.disabled = summary.profile.role !== "admin";
        control.title = summary.profile.role === "admin"
            ? ""
            : "Disponible solo para el perfil administrador";
    });

    if (summary.profile.role !== "admin" && ["crud", "json", "review", "table"].includes(activeDashboardTab)) {
        setDashboardTab("overview");
    }
};

const refreshDashboardPanels = async () => {
    renderTable();
    renderJsonPreview();
    await renderMetrics();
    await loadAnimeReviews();
    syncProfileForm();
    syncSettingsForm();
};

contentForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        validateContentForm();
        const payload = getFormData();
        saveContentButton.disabled = true;

        if (contentId.value) {
            await AltoidssStore.update(contentId.value, payload);
            showDashboardFeedback("Contenido actualizado correctamente.", "success");
        } else {
            await AltoidssStore.create(payload);
            showDashboardFeedback("Contenido guardado correctamente.", "success");
        }

        resetForm();
        activeTableMode = "content";
        syncTableModeButtons();
        refreshDashboardPanels();
    } catch (error) {
        showDashboardFeedback(error.message || "No se pudo guardar el contenido.");
    } finally {
        saveContentButton.disabled = false;
    }
});

newsForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = getNewsFormData();

    try {
        saveNewsButton.disabled = true;

        if (newsId.value) {
            await AltoidssStore.updateNews(newsId.value, payload);
            showDashboardFeedback("Noticia actualizada correctamente.", "success");
        } else {
            await AltoidssStore.createNews(payload);
            showDashboardFeedback("Noticia guardada correctamente.", "success");
        }

        resetNewsForm();
        activeTableMode = "news";
        syncTableModeButtons();
        refreshDashboardPanels();
    } catch (error) {
        showDashboardFeedback(error.message || "No se pudo guardar la noticia.");
    } finally {
        saveNewsButton.disabled = false;
    }
});

contentTableBody.addEventListener("click", async (event) => {
    const editButton = event.target.closest("[data-edit-id]");
    const deleteButton = event.target.closest("[data-delete-id]");
    const editNewsButton = event.target.closest("[data-edit-news-id]");
    const deleteNewsButton = event.target.closest("[data-delete-news-id]");

    if (editButton) {
        const item = AltoidssStore.read().find((entry) => entry.id === editButton.dataset.editId);
        if (item) {
            loadItemForEdit(item);
            setDashboardTab("crud");
        }
    }

    if (deleteButton) {
        const item = AltoidssStore.read().find((entry) => entry.id === deleteButton.dataset.deleteId);

        if (!window.confirm(`¿Desea ocultar "${item?.title || "este contenido"}"? El registro quedará guardado en JSON, pero no se mostrará en la aplicación.`)) {
            return;
        }

        try {
            await AltoidssStore.remove(deleteButton.dataset.deleteId);
            refreshDashboardPanels();
            showDashboardFeedback("Contenido ocultado correctamente.", "success");
        } catch (error) {
            showDashboardFeedback(error.message || "No se pudo ocultar el contenido.");
        }
    }

    if (editNewsButton) {
        const item = AltoidssStore.readNews().find((entry) => entry.id === editNewsButton.dataset.editNewsId);
        if (item) {
            loadNewsForEdit(item);
            setDashboardTab("crud");
        }
    }

    if (deleteNewsButton) {
        const item = AltoidssStore.readNews().find((entry) => entry.id === deleteNewsButton.dataset.deleteNewsId);

        if (!window.confirm(`¿Desea ocultar "${item?.title || "esta noticia"}"? El registro quedará guardado en JSON, pero no se mostrará en la aplicación.`)) {
            return;
        }

        try {
            await AltoidssStore.removeNews(deleteNewsButton.dataset.deleteNewsId);
            refreshDashboardPanels();
            showDashboardFeedback("Noticia ocultada correctamente.", "success");
        } catch (error) {
            showDashboardFeedback(error.message || "No se pudo ocultar la noticia.");
        }
    }
});

cancelEditButton.addEventListener("click", resetForm);
cancelNewsEditButton.addEventListener("click", resetNewsForm);

const setCrudMode = (mode) => {
    activeCrudMode = mode === "news" ? "news" : "content";

    crudModeButtons.forEach((button) => {
        const isSelected = button.dataset.crudMode === activeCrudMode;
        button.classList.toggle("btn-primary", isSelected);
        button.classList.toggle("btn-outline-light", !isSelected);
    });

    crudModePanels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.dataset.crudPanel === activeCrudMode);
    });
};

crudModeButtons.forEach((button) => {
    button.addEventListener("click", () => setCrudMode(button.dataset.crudMode));
});

const syncTableModeButtons = () => {
    tableModeButtons.forEach((button) => {
        const isSelected = button.dataset.tableMode === activeTableMode;
        button.classList.toggle("btn-primary", isSelected);
        button.classList.toggle("btn-outline-light", !isSelected);
    });
};

tableModeButtons.forEach((button) => {
    button.addEventListener("click", () => {
        activeTableMode = button.dataset.tableMode;
        syncTableModeButtons();
        renderTable();
    });
});

reviewFilterButtons.forEach((button) => {
    button.addEventListener("click", () => {
        activeReviewFilter = button.dataset.reviewFilter;
        reviewFilterButtons.forEach((current) => {
            const selected = current.dataset.reviewFilter === activeReviewFilter;
            current.classList.toggle("btn-primary", selected);
            current.classList.toggle("btn-outline-light", !selected);
        });
        renderAnimeReviews();
    });
});

animeReviewList?.addEventListener("click", async (event) => {
    const fetchSourceButton = event.target.closest("[data-review-source-fetch]");
    if (fetchSourceButton) {
        const card = fetchSourceButton.closest("[data-review-id]");
        const review = animeReviews.find((item) => item.id === card?.dataset.reviewId);
        const sourceUrl = card?.querySelector('[data-final-field="sourceUrl"]')?.value.trim() || "";
        if (!review || !sourceUrl) {
            showReviewToast("Ingresa una URL de fuente antes de obtener datos.");
            return;
        }
        try {
            fetchSourceButton.disabled = true;
            fetchSourceButton.textContent = "Obteniendo datos…";
            const result = await AltoidssApi.post(`/reviews/anime/${encodeURIComponent(review.id)}/source`, { sourceUrl });
            if (!result?.candidate) {
                showReviewToast("No hay datos compatibles");
                return;
            }
            review.apiVersion = result.candidate;
            setReviewEditorValues(card, { ...collectReviewEditorData(card), ...result.candidate });
            const comparison = card.querySelector('.review-comparison');
            comparison.innerHTML = renderReviewVersion(review.original, "Original")
                + renderReviewVersion(review.apiVersion, `API · ${review.apiVersion.metadataProvider}`, review.apiVersion.image);
            card.querySelectorAll('[data-review-copy="api"], [data-review-preset="api"]').forEach((button) => {
                button.disabled = button.dataset.reviewField
                    ? !hasReviewValue(review.apiVersion[button.dataset.reviewField]) : false;
            });
            showReviewToast("Datos de la fuente cargados. Revisa y guarda la versión final.", true);
        } catch (error) {
            showReviewToast(error.message || "No hay datos compatibles");
        } finally {
            fetchSourceButton.disabled = false;
            fetchSourceButton.textContent = "Obtener datos desde URL";
        }
        return;
    }

    const presetButton = event.target.closest("[data-review-preset]");
    const copyButton = event.target.closest("[data-review-copy]");
    const sourceButton = presetButton || copyButton;

    if (sourceButton) {
        const card = sourceButton.closest("[data-review-id]");
        const review = animeReviews.find((item) => item.id === card?.dataset.reviewId);
        if (!review) return;

        if (presetButton) {
            setReviewEditorValues(card, buildReviewPreset(review, presetButton.dataset.reviewPreset));
        } else {
            const field = copyButton.dataset.reviewField;
            const source = copyButton.dataset.reviewCopy === "api" ? review.apiVersion : review.original;
            setReviewEditorField(card, field, source?.[field]);
        }
        return;
    }

    const button = event.target.closest("[data-review-decision]");
    if (!button) return;
    const card = button.closest("[data-review-id]");
    const review = animeReviews.find((item) => item.id === card?.dataset.reviewId);
    if (!review) return;
    const decision = button.dataset.reviewDecision;
    const verb = decision === "save" ? "guardar esta combinación como versión final" : "rechazar esta propuesta";
    if (!window.confirm(`¿Desea ${verb} para "${review.title}"?`)) return;

    try {
        card.querySelectorAll("button").forEach((current) => { current.disabled = true; });
        const payload = {
            decision,
            notes: card.querySelector("[data-review-notes]")?.value || "",
        };
        if (decision === "save") payload.finalData = collectReviewEditorData(card);
        await AltoidssApi.put(`/reviews/anime/${encodeURIComponent(review.id)}`, payload);
        await refreshDashboardPanels();
        showDashboardFeedback(decision === "save" ? "Versión final guardada en el catálogo." : "Propuesta rechazada.", "success");
    } catch (error) {
        showDashboardFeedback(error.message || "No se pudo guardar la revisión.");
        card.querySelectorAll("button").forEach((current) => { current.disabled = false; });
    }
});

animeReviewList?.addEventListener("input", (event) => {
    const field = event.target.closest("[data-final-field]");
    field?.closest(".review-edit-field")?.classList.add("is-manual");
});

dashboardTabButtons.forEach((button) => {
    button.addEventListener("click", () => {
        setDashboardTab(button.dataset.dashboardTab);
    });
});

const setDashboardTab = (tab) => {
    const mode = AltoidssAuth.getSession().profileMode;

    if (mode !== "admin" && ["crud", "json", "review", "table"].includes(tab)) {
        tab = "overview";
    }

    activeDashboardTab = dashboardTabs.includes(tab) ? tab : "overview";
    const tabIndex = dashboardTabs.indexOf(activeDashboardTab);

    dashboardTabTrack.style.transform = `translateX(-${tabIndex * (100 / dashboardTabs.length)}%)`;

    dashboardTabButtons.forEach((button) => {
        const isSelected = button.dataset.dashboardTab === activeDashboardTab;
        button.classList.toggle("btn-primary", isSelected);
        button.classList.toggle("btn-outline-light", !isSelected);
    });
};

const syncProfileForm = () => {
    const profile = AltoidssStore.getProfile();

    profileName.value = profile.displayName || "";
    profileEmail.value = profile.email || "";
    profileSocial.value = profile.socialLinks || "";
    profileAvatar.value = profile.avatar || "";
    profileAbout.value = profile.about || "";

    if (profile.avatar) {
        avatarPreview.innerHTML = `<img src="${escapeHtml(profile.avatar)}" alt="Foto de perfil de ${escapeHtml(profile.displayName)}">`;
    } else {
        avatarPreview.textContent = (profile.displayName || "AL").slice(0, 2).toUpperCase();
    }
};

const syncSettingsForm = () => {
    const settings = AltoidssStore.getProfile().settings || {};

    settingCardsPerRow.value = String(settings.cardsPerRow || 5);
    settingPreferredView.value = settings.preferredView || "cards";
    settingCompactMode.checked = Boolean(settings.compactMode);
};

profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        await AltoidssStore.updateProfileDetails({
            displayName: profileName.value,
            email: profileEmail.value,
            socialLinks: profileSocial.value,
            avatar: profileAvatar.value,
            about: profileAbout.value,
        });
        refreshDashboard();
        showDashboardFeedback("Perfil actualizado correctamente.", "success");
    } catch (error) {
        showDashboardFeedback(error.message || "No se pudo actualizar el perfil.");
    }
});

settingsForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    try {
        await AltoidssStore.updateSettings({
            cardsPerRow: Number(settingCardsPerRow.value),
            preferredView: settingPreferredView.value,
            compactMode: settingCompactMode.checked,
        });
        refreshDashboard();
        showDashboardFeedback("Configuración actualizada correctamente.", "success");
    } catch (error) {
        showDashboardFeedback(error.message || "No se pudo actualizar la configuración.");
    }
});

const refreshDashboard = async () => {
    try {
        await refreshDashboardPanels();
    } catch (error) {
        showDashboardFeedback(error.message || "No se pudieron actualizar las métricas.");
    }
};

window.addEventListener("altoidss-auth-change", () => {
    refreshDashboard();
});

window.addEventListener("pageshow", () => {
    refreshDashboard();
});

document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
        refreshDashboard();
    }
});

const initializeDashboard = async () => {
    await AltoidssStore.initialize();
    const requestedTab = new URLSearchParams(window.location.search).get("tab");
    setDashboardTab(requestedTab || "overview");
    setCrudMode("content");
    syncTableModeButtons();
    resetForm();
    resetNewsForm();
    await refreshDashboard();
};

initializeDashboard();
