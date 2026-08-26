const homePopularGrid = document.querySelector("#homePopularGrid");
const homeNewsGrid = document.querySelector("#homeNewsGrid");

const escapeHomeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const createPopularCard = (item) => `
    <article class="popular-card">
        <img src="${escapeHomeHtml(item.image)}" alt="Póster de ${escapeHomeHtml(item.title)}">
        <span class="rating">${escapeHomeHtml(item.rating || "8.0")}</span>
        <h3>${escapeHomeHtml(item.title)}</h3>
        <p>${escapeHomeHtml(item.year || item.emissionYear || "")}</p>
    </article>
`;

const createHomeNewsCard = (item) => `
    <article class="news-card">
        <img class="news-image" src="${escapeHomeHtml(item.image)}" alt="Imagen de ${escapeHomeHtml(item.title)}">
        <div class="news-body">
            <span class="news-tag">${escapeHomeHtml(item.category)}</span>
            <h3>${escapeHomeHtml(item.title)}</h3>
            <p>${escapeHomeHtml(item.summary)}</p>
        </div>
    </article>
`;

const loadHomeSections = async () => {
    if (typeof AltoidssStore === "undefined") {
        return;
    }

    await AltoidssStore.initialize();

    try {
        const contentItems = await AltoidssStore.readSectionFiles();
        const movieItems = contentItems
            .filter((item) => item.type === "movies" || item.format === "Película")
            .slice(0, 6);

        if (movieItems.length) {
            homePopularGrid.innerHTML = movieItems.map(createPopularCard).join("");
        }
    } catch (error) {
        console.warn("No se pudieron cargar las películas del inicio.", error);
    }

    try {
        const newsItems = (await AltoidssStore.readNewsFile())
            .filter((item) => item.status === "publicada")
            .slice(0, 3);

        if (newsItems.length) {
            homeNewsGrid.innerHTML = newsItems.map(createHomeNewsCard).join("");
        }
    } catch (error) {
        console.warn("No se pudieron cargar las noticias del inicio.", error);
    }
};

loadHomeSections();
