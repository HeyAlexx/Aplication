// Private catalog requests. The API rechecks administrator authority before publication.
(() => {
    const list = document.querySelector("#catalogRequestList");
    const feedback = document.querySelector("#catalogRequestFeedback");
    const refreshButton = document.querySelector("#refreshCatalogRequests");
    if (!list || !feedback || !refreshButton) return;
    const labels = {pending:"Pendiente", approving:"Procesando", approved:"Aprobada",
        rejected:"Rechazada", cancelled:"Cancelada"};
    let rows = [];
    let sequence = 0;
    const isAdmin = () => window.AltoidssAuth?.getSession()?.role === "admin";
    const node = (tag, className, text) => {
        const element = document.createElement(tag);
        element.className = className;
        if (text !== undefined) element.textContent = String(text);
        return element;
    };
    const render = () => {
        list.replaceChildren();
        if (!isAdmin()) { rows = []; return; }
        if (!rows.length) { list.append(node("p", "review-empty", "No hay solicitudes de títulos externos.")); return; }
        for (const row of rows) {
            const item = row.candidate || {};
            const card = node("article", "review-card");
            card.dataset.catalogRequest = row.id;
            const header = node("header", "review-card-head");
            const heading = node("div", "");
            heading.append(node("h3", "", item.title || "Sin título"),
                node("p", "", [row.requestedBy, item.source, item.type].filter(Boolean).join(" · ")));
            header.append(heading, node("span", "review-status", labels[row.status] || row.status));
            card.append(header, node("p", "", String(item.description || "").slice(0, 600)),
                node("p", "", (item.genre || "") + " · " + (item.year || item.emissionYear || "Año no informado")));
            if (["pending", "approving"].includes(row.status)) {
                const actions = node("div", "review-actions");
                for (const [decision, label, className] of [
                    ["approve", "Aprobar incorporación", "btn btn-primary"],
                    ["reject", "Rechazar solicitud", "btn btn-outline-danger"]]) {
                    const button = node("button", className, label);
                    button.type = "button";
                    button.dataset.catalogDecision = decision;
                    actions.append(button);
                }
                card.append(actions);
            }
            list.append(card);
        }
    };
    const refresh = async () => {
        const current = ++sequence;
        if (!isAdmin()) { rows = []; render(); return; }
        try {
            const response = await AltoidssApi.get("/catalog/requests");
            if (current !== sequence || !isAdmin()) return;
            rows = response;
            render();
        } catch (error) {
            if (current === sequence) { rows = []; render(); feedback.textContent = error.message; }
        }
    };
    refreshButton.addEventListener("click", refresh);
    list.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-catalog-decision]");
        if (!button || !isAdmin()) return;
        const card = button.closest("[data-catalog-request]");
        const row = rows.find((item) => item.id === card?.dataset.catalogRequest);
        if (!row) return;
        const decision = button.dataset.catalogDecision;
        const question = (decision === "approve" ? "¿Incorporar al catálogo compartido: " : "¿Rechazar la solicitud: ")
            + (row.candidate?.title || "este título") + "?";
        if (!window.confirm(question)) return;
        card.querySelectorAll("button").forEach((item) => { item.disabled = true; });
        feedback.textContent = "Procesando solicitud…";
        try {
            await AltoidssApi.post("/catalog/requests/" + encodeURIComponent(row.id), {decision});
            feedback.textContent = decision === "approve" ? "Título aprobado e incorporado al catálogo." : "Solicitud rechazada.";
            await AltoidssStore.reload();
            window.dispatchEvent(new CustomEvent("altoidss-catalog-requests-updated"));
            await refresh();
        } catch (error) {
            feedback.textContent = error.message || "No se pudo completar la decisión.";
            await refresh();
        } finally {
            card.querySelectorAll("button").forEach((item) => { item.disabled = false; });
        }
    });
    window.addEventListener("altoidss-auth-change", refresh);
    window.addEventListener("altoidss-store-ready", refresh);
    window.addEventListener("pageshow", refresh);
    refresh();
})();

