// Fachada de datos compartida. Usa PHP + JSON y mantiene una previsualización local si PHP no está activo.
const AltoidssStore = (() => {
    const localContentKey = "altoidss_content_json";
    const localNewsKey = "altoidss_news_json";
    const localProfilesKey = "altoidss_user_profiles";
    let contentItems = [];
    let newsItems = [];
    let activeProfile = null;
    let initializePromise = null;
    let backendMode = false;

    const visitorProfile = () => ({
        id: "visitor", role: "visitante", displayName: "Visitante", email: "", socialLinks: "",
        about: "Explora el catálogo antes de crear una cuenta.", avatar: "", lastVisit: "Sesión actual",
        watchTimeMinutes: 0, seenIds: [], favoriteIds: [], favoriteItems: {},
        settings: { cardsPerRow: 5, preferredView: "cards", compactMode: false },
    });

    const readLocal = (key, fallback) => {
        try {
            return JSON.parse(localStorage.getItem(key)) || fallback;
        } catch (error) {
            return fallback;
        }
    };
    const visibleContent = (items) => items.filter((item) => item.status !== "Oculto");
    const visibleNews = (items) => items.filter((item) => item.visibilityStatus !== "Oculto");

    const readJsonFile = async (path) => {
        const response = await fetch(path);
        if (!response.ok) {
            throw new Error(`No se pudo cargar ${path}`);
        }
        return response.json();
    };

    const loadStaticData = async () => {
        const [movies, series, anime, news] = await Promise.all([
            readJsonFile("../data/peliculas.json"), readJsonFile("../data/series.json"),
            readJsonFile("../data/anime.json"), readJsonFile("../data/noticias.json"),
        ]);
        const localContent = readLocal(localContentKey, []);
        const localNews = readLocal(localNewsKey, []);
        const baseContent = [...movies, ...series, ...anime];
        const contentIds = new Set(baseContent.map((item) => item.id));
        const newsIds = new Set(news.map((item) => item.id));
        contentItems = visibleContent([...baseContent, ...localContent.filter((item) => !contentIds.has(item.id))]);
        newsItems = visibleNews([...news, ...localNews.filter((item) => !newsIds.has(item.id))]);

        const session = window.AltoidssAuth?.getSession() || { id: "visitor", role: "visitante", name: "Visitante", email: "" };
        const profiles = readLocal(localProfilesKey, {});
        activeProfile = normalizeProfile(profiles[session.id], session);
    };

    const normalizeProfile = (profile = {}, session = {}) => ({
        ...visitorProfile(),
        id: session.id || profile.id || "visitor",
        role: session.role || profile.role || "visitante",
        displayName: profile.displayName || session.name || "Visitante",
        email: profile.email || session.email || "",
        ...profile,
        seenIds: Array.isArray(profile.seenIds) ? profile.seenIds : [],
        favoriteIds: Array.isArray(profile.favoriteIds) ? profile.favoriteIds : [],
        favoriteItems: profile.favoriteItems && typeof profile.favoriteItems === "object" ? profile.favoriteItems : {},
        settings: {
            ...visitorProfile().settings,
            ...(profile.settings || {}),
        },
    });

    const initialize = async (force = false) => {
        if (initializePromise && !force) {
            return initializePromise;
        }

        initializePromise = (async () => {
            await window.AltoidssAuth?.initialize(force);
            try {
                const [contentGroups, loadedNews, loadedProfile] = await Promise.all([
                    Promise.all([
                        AltoidssApi.get("/content/movies"),
                        AltoidssApi.get("/content/series"),
                        AltoidssApi.get("/content/anime"),
                    ]),
                    AltoidssApi.get("/news"),
                    AltoidssApi.get("/profile"),
                ]);
                contentItems = contentGroups.flat();
                newsItems = loadedNews;
                activeProfile = loadedProfile;
                contentItems = visibleContent(contentItems);
                newsItems = visibleNews(newsItems);
                activeProfile = normalizeProfile(activeProfile, window.AltoidssAuth?.getSession());
                backendMode = true;
            } catch (error) {
                backendMode = false;
                await loadStaticData();
            }
            window.dispatchEvent(new CustomEvent("altoidss-store-ready"));
            return { contents: contentItems, news: newsItems, profile: activeProfile };
        })();

        return initializePromise;
    };

    const reload = () => initialize(true);
    const read = () => [...contentItems];
    const readNews = () => [...newsItems];
    const writeLocalContent = () => localStorage.setItem(localContentKey, JSON.stringify(contentItems, null, 2));
    const writeLocalNews = () => localStorage.setItem(localNewsKey, JSON.stringify(newsItems, null, 2));

    const writeLocalProfile = () => {
        const profiles = readLocal(localProfilesKey, {});
        profiles[activeProfile.id] = activeProfile;
        localStorage.setItem(localProfilesKey, JSON.stringify(profiles, null, 2));
    };

    const readSectionFile = async (section) => {
        await initialize();
        if (section === "noticias") return readNews();
        const type = section === "peliculas" ? "movies" : section;
        return contentItems.filter((item) => item.type === type);
    };

    const readSectionFiles = async () => {
        await initialize();
        return read();
    };

    const readNewsFile = async () => {
        await initialize();
        return readNews();
    };

    const searchCatalog = async (type, query) => {
        await initialize();
        const normalizedQuery = String(query || "").trim().toLocaleLowerCase("es");
        const localResults = contentItems.filter((item) => (
            item.type === type && String(item.title || "").toLocaleLowerCase("es").includes(normalizedQuery)
        ));

        if (!normalizedQuery || !backendMode) {
            return localResults;
        }

        try {
            return await AltoidssApi.get(`/discover/${type}/${encodeURIComponent(query.trim())}`);
        } catch (error) {
            console.warn("Watchmode no respondió; se utiliza el catálogo JSON local.", error);
            return localResults;
        }
    };

    const getProfile = () => activeProfile || visitorProfile();
    const requireActiveUser = () => {
        const session = window.AltoidssAuth?.getSession() || {};

        if (backendMode && !session.isAuthenticated) {
            const error = new Error("Debe iniciar sesión para guardar favoritos o marcar contenido como visto.");
            error.status = 401;
            throw error;
        }
    };

    const contentKey = (item) => item.id || String(item.title || "").toLowerCase().replace(/\s+/g, "-");
    const isSeen = (item) => getProfile().seenIds.includes(contentKey(item));
    const isFavorite = (item) => getProfile().favoriteIds.includes(contentKey(item));

    const toggleSeen = async (item) => {
        const id = contentKey(item);
        const watched = !isSeen(item);

        if (backendMode) {
            requireActiveUser();
            activeProfile = await AltoidssApi.put(`/viewing/${encodeURIComponent(id)}`, { watched });
        } else {
            activeProfile.seenIds = watched
                ? [...activeProfile.seenIds, id]
                : activeProfile.seenIds.filter((currentId) => currentId !== id);
            writeLocalProfile();
        }
        return activeProfile;
    };

    const toggleFavorite = async (item) => {
        const id = contentKey(item);
        const removing = isFavorite(item);

        if (backendMode) {
            requireActiveUser();
            const favorites = removing
                ? await AltoidssApi.delete(`/favorites/${encodeURIComponent(id)}`)
                : await AltoidssApi.post(`/favorites/${encodeURIComponent(id)}`, item);
            activeProfile.favoriteIds = favorites.map((favorite) => favorite.id);
            activeProfile.favoriteItems = Object.fromEntries(favorites.map((favorite) => [favorite.id, favorite]));
        } else if (removing) {
            activeProfile.favoriteIds = activeProfile.favoriteIds.filter((currentId) => currentId !== id);
            delete activeProfile.favoriteItems[id];
            writeLocalProfile();
        } else {
            activeProfile.favoriteIds.push(id);
            activeProfile.favoriteItems[id] = { ...item, id, favoriteAt: new Date().toISOString() };
            writeLocalProfile();
        }
        return activeProfile;
    };

    const removeFavorite = async (id) => {
        if (backendMode) {
            requireActiveUser();
            const favorites = await AltoidssApi.delete(`/favorites/${encodeURIComponent(id)}`);
            activeProfile.favoriteIds = favorites.map((favorite) => favorite.id);
            activeProfile.favoriteItems = Object.fromEntries(favorites.map((favorite) => [favorite.id, favorite]));
        } else {
            activeProfile.favoriteIds = activeProfile.favoriteIds.filter((currentId) => currentId !== id);
            delete activeProfile.favoriteItems[id];
            writeLocalProfile();
        }
        return activeProfile;
    };

    const updateProfileDetails = async (details) => {
        if (backendMode) activeProfile = await AltoidssApi.put("/profile", details);
        else {
            activeProfile = { ...activeProfile, ...details };
            writeLocalProfile();
        }
        return activeProfile;
    };

    const updateSettings = async (settings) => {
        if (backendMode) activeProfile.settings = await AltoidssApi.put("/settings", { ...activeProfile.settings, ...settings });
        else {
            activeProfile.settings = { ...activeProfile.settings, ...settings };
            writeLocalProfile();
        }
        return activeProfile.settings;
    };

    const create = async (item) => {
        const created = backendMode ? await AltoidssApi.post("/content", item) : { ...item, id: crypto.randomUUID(), createdAt: new Date().toISOString() };
        contentItems.push(created);
        if (!backendMode) writeLocalContent();
        return created;
    };

    const update = async (id, nextItem) => {
        const updated = backendMode
            ? await AltoidssApi.put(`/content/${encodeURIComponent(id)}`, nextItem)
            : { ...contentItems.find((item) => item.id === id), ...nextItem, id, updatedAt: new Date().toISOString() };
        contentItems = contentItems.map((item) => item.id === id ? updated : item);
        if (!backendMode) writeLocalContent();
        return updated;
    };

    const remove = async (id) => {
        if (backendMode) await AltoidssApi.delete(`/content/${encodeURIComponent(id)}`);
        contentItems = contentItems.map((item) => item.id === id ? { ...item, status: "Oculto", hiddenAt: new Date().toISOString() } : item)
            .filter((item) => item.status !== "Oculto");
        if (!backendMode) writeLocalContent();
    };

    const createNews = async (item) => {
        const created = backendMode ? await AltoidssApi.post("/news", item) : { ...item, id: crypto.randomUUID(), createdAt: new Date().toISOString() };
        newsItems.push(created);
        if (!backendMode) writeLocalNews();
        return created;
    };

    const updateNews = async (id, nextItem) => {
        const updated = backendMode
            ? await AltoidssApi.put(`/news/${encodeURIComponent(id)}`, nextItem)
            : { ...newsItems.find((item) => item.id === id), ...nextItem, id, updatedAt: new Date().toISOString() };
        newsItems = newsItems.map((item) => item.id === id ? updated : item);
        if (!backendMode) writeLocalNews();
        return updated;
    };

    const removeNews = async (id) => {
        if (backendMode) await AltoidssApi.delete(`/news/${encodeURIComponent(id)}`);
        newsItems = newsItems.map((item) => item.id === id ? { ...item, visibilityStatus: "Oculto", hiddenAt: new Date().toISOString() } : item)
            .filter((item) => item.visibilityStatus !== "Oculto");
        if (!backendMode) writeLocalNews();
    };

    const summarizeProfile = () => {
        const profile = getProfile();
        const seenSet = new Set(profile.seenIds);
        const seenItems = contentItems.filter((item) => seenSet.has(item.id));
        const favoriteItems = Object.values(profile.favoriteItems || {});
        const byType = (type) => seenItems.filter((item) => item.type === type).length;
        const favoritesByType = (type) => favoriteItems.filter((item) => item.type === type).length;
        const genreCounts = seenItems.reduce((counts, item) => {
            const genre = item.genre || "General";
            counts[genre] = (counts[genre] || 0) + 1;
            return counts;
        }, {});
        const topGenre = Object.entries(genreCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "Sin datos";
        return {
            profile, totalContent: contentItems.length, seenTotal: seenItems.length,
            favoriteTotal: profile.favoriteIds.length, moviesSeen: byType("movies"), seriesSeen: byType("series"),
            animeSeen: byType("anime"), topGenre, lastVisit: profile.lastVisit,
            favoriteMovies: favoritesByType("movies"), favoriteSeries: favoritesByType("series"),
            favoriteAnime: favoritesByType("anime"),
            watchTimeMinutes: profile.watchTimeMinutes || 0,
        };
    };

    const getDashboardSummary = async () => {
        await initialize();

        if (!backendMode) {
            return summarizeProfile();
        }

        const summary = await AltoidssApi.get("/dashboard");
        activeProfile = normalizeProfile(summary.profile, window.AltoidssAuth?.getSession());
        return { ...summary, profile: activeProfile };
    };

    const exportDatabase = () => ({ contents: read(), news: readNews(), profiles: [getProfile()] });
    const importMany = async (items) => Promise.all(items.map(create));
    const seedExcelData = () => [];
    const hydrateMissingImages = async () => read();

    return {
        initialize, reload, read, readNews, exportDatabase, readSectionFile, readSectionFiles, readNewsFile, searchCatalog,
        importMany, seedExcelData, hydrateMissingImages,
        getProfile, summarizeProfile, getDashboardSummary, isSeen, isFavorite, toggleSeen, toggleFavorite, removeFavorite,
        updateProfileDetails, updateSettings, create, update, remove, createNews, updateNews, removeNews,
        isBackendMode: () => backendMode,
    };
})();
