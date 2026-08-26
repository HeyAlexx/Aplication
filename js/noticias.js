const featuredNewsGrid = document.querySelector("#featuredNewsGrid");
const newsListGrid = document.querySelector("#newsListGrid");
const newsDetailDialog = document.querySelector("#newsDetailDialog");
const newsDetailContent = document.querySelector("#newsDetailContent");
let publishedNewsItems = [];

const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const formatNewsDate = (value) => {
    if (!value) return "Sin fecha";
    const date = new Date(`${value}T00:00:00`);
    if (Number.isNaN(date.getTime())) return value;

    return new Intl.DateTimeFormat("es-CR", {
        day: "2-digit",
        month: "long",
        year: "numeric",
    }).format(date);
};

const getYouTubeId = (url) => {
    if (!url) return "";

    try {
        const parsedUrl = new URL(url);
        if (parsedUrl.hostname === "youtu.be") return parsedUrl.pathname.slice(1).split("/")[0];
        if (parsedUrl.pathname.startsWith("/embed/")) return parsedUrl.pathname.split("/")[2] || "";
        return parsedUrl.searchParams.get("v") || "";
    } catch {
        return "";
    }
};

const createVideoBadge = (item) => item.trailerUrl ? `
    <span class="news-video-badge">
        <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
            <path d="M16 8a8 8 0 1 1-16 0 8 8 0 0 1 16 0M6.79 5.093A.5.5 0 0 0 6 5.5v5a.5.5 0 0 0 .79.407l3.5-2.5a.5.5 0 0 0 0-.814z"/>
        </svg>
        Tráiler
    </span>
` : "";

const createOpenButton = (item) => `
    <button class="news-card-action" type="button" data-news-id="${escapeHtml(item.id)}" aria-label="Abrir noticia: ${escapeHtml(item.title)}"></button>
`;

const createFeaturedCard = (item, isLarge = false) => `
    <article class="headline-card ${isLarge ? "headline-large" : ""}">
        <img src="${escapeHtml(item.image)}" alt="Imagen de ${escapeHtml(item.title)}">
        <div class="headline-body">
            <div class="news-card-meta">
                <span class="news-chip">${escapeHtml(item.category)}</span>
                ${createVideoBadge(item)}
            </div>
            <h2>${escapeHtml(item.title)}</h2>
            ${isLarge ? `<p>${escapeHtml(item.summary)}</p>` : ""}
        </div>
        ${createOpenButton(item)}
    </article>
`;

const createNewsListCard = (item) => `
    <article class="news-list-card">
        <img src="${escapeHtml(item.image)}" alt="Imagen de ${escapeHtml(item.title)}">
        <div>
            <div class="news-card-meta">
                <span>${escapeHtml(item.category)} · ${escapeHtml(formatNewsDate(item.publishedAt))}</span>
                ${createVideoBadge(item)}
            </div>
            <h3>${escapeHtml(item.title)}</h3>
            <p>${escapeHtml(item.summary)}</p>
        </div>
        ${createOpenButton(item)}
    </article>
`;

const createNewsDetail = (item) => {
    const videoId = getYouTubeId(item.trailerUrl);
    const relatedContent = (item.relatedContent || [])
        .map((title) => `<span>${escapeHtml(title)}</span>`)
        .join("");
    const video = videoId ? `
        <section class="news-detail-video" aria-labelledby="newsTrailerTitle">
            <div class="news-detail-section-heading">
                <p class="eyebrow">Multimedia</p>
                <h3 id="newsTrailerTitle">${escapeHtml(item.trailerLabel || "Tráiler oficial")}</h3>
            </div>
            <div class="news-video-frame">
                <iframe
                    src="https://www.youtube-nocookie.com/embed/${escapeHtml(videoId)}?rel=0"
                    title="${escapeHtml(item.trailerLabel || "Tráiler oficial")} de ${escapeHtml(item.title)}"
                    loading="lazy"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    referrerpolicy="strict-origin-when-cross-origin"
                    allowfullscreen></iframe>
            </div>
            <a class="news-video-source" href="${escapeHtml(item.trailerUrl)}" target="_blank" rel="noopener noreferrer">Ver tráiler en YouTube</a>
        </section>
    ` : "";

    return `
        <article class="news-detail-article">
            <img class="news-detail-cover" src="${escapeHtml(item.image)}" alt="Imagen de ${escapeHtml(item.title)}">
            <div class="news-detail-copy">
                <div class="news-detail-meta">
                    <span class="news-chip">${escapeHtml(item.category)}</span>
                    <time datetime="${escapeHtml(item.publishedAt)}">${escapeHtml(formatNewsDate(item.publishedAt))}</time>
                </div>
                <h2 id="newsDetailTitle">${escapeHtml(item.title)}</h2>
                <p class="news-detail-summary">${escapeHtml(item.summary)}</p>
                <p>${escapeHtml(item.body)}</p>
                ${relatedContent ? `<div class="news-related" aria-label="Contenido relacionado">${relatedContent}</div>` : ""}
                ${video}
            </div>
        </article>
    `;
};

const openNewsDetail = (newsId) => {
    const item = publishedNewsItems.find((entry) => entry.id === newsId);
    if (!item) return;

    newsDetailContent.innerHTML = createNewsDetail(item);
    newsDetailDialog.showModal();
};

const closeNewsDetail = () => {
    newsDetailDialog.close();
    newsDetailContent.innerHTML = "";
};

const getNewsContent = async () => {
    if (typeof AltoidssStore === "undefined") return [];

    try {
        await AltoidssStore.initialize();
        return AltoidssStore.readNews();
    } catch (error) {
        console.warn("No se pudo cargar el JSON de noticias.", error);
        return AltoidssStore.readNews();
    }
};

const renderStoredNews = async () => {
    if (typeof AltoidssStore === "undefined") return;

    publishedNewsItems = (await getNewsContent())
        .filter((item) => item.status === "publicada")
        .sort((a, b) => Number(Boolean(b.featured)) - Number(Boolean(a.featured)));

    if (!publishedNewsItems.length) return;

    const featured = publishedNewsItems.filter((item) => item.featured).slice(0, 3);
    const fallbackFeatured = publishedNewsItems.filter((item) => !item.featured).slice(0, 3 - featured.length);
    const topNews = [...featured, ...fallbackFeatured];

    featuredNewsGrid.innerHTML = topNews.map((item, index) => createFeaturedCard(item, index === 0)).join("");
    newsListGrid.innerHTML = publishedNewsItems.map(createNewsListCard).join("");
};

document.addEventListener("click", (event) => {
    const openButton = event.target.closest("[data-news-id]");
    if (openButton) openNewsDetail(openButton.dataset.newsId);
    if (event.target.closest("[data-close-news]")) closeNewsDetail();
});

newsDetailDialog.addEventListener("click", (event) => {
    const bounds = newsDetailDialog.getBoundingClientRect();
    const isBackdrop = event.clientX < bounds.left || event.clientX > bounds.right
        || event.clientY < bounds.top || event.clientY > bounds.bottom;
    if (isBackdrop) closeNewsDetail();
});

newsDetailDialog.addEventListener("close", () => {
    newsDetailContent.innerHTML = "";
});

renderStoredNews();
