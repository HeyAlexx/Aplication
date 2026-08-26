// Cliente único para comunicar todas las páginas de Altoidss con la API PHP.
window.AltoidssApi = (() => {
    let csrfToken = "";
    let backendAvailable = null;

    const request = async (route, options = {}) => {
        const method = options.method || "GET";
        const headers = { Accept: "application/json", ...(options.headers || {}) };

        if (options.body !== undefined) {
            headers["Content-Type"] = "application/json";
        }

        if (csrfToken && !["GET", "HEAD"].includes(method)) {
            headers["X-CSRF-Token"] = csrfToken;
        }

        const response = await fetch(`../api/index.php?route=${encodeURIComponent(route)}`, {
            method,
            headers,
            credentials: "same-origin",
            body: options.body === undefined ? undefined : JSON.stringify(options.body),
        });
        const contentType = response.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
            backendAvailable = false;
            throw new Error("La API PHP no está disponible en este servidor.");
        }

        const payload = await response.json();
        csrfToken = payload.meta?.csrfToken || csrfToken;
        backendAvailable = true;

        if (!response.ok || !payload.ok) {
            const error = new Error(payload.error?.message || "La solicitud no pudo completarse.");
            error.status = response.status;
            error.details = payload.error?.details || [];
            throw error;
        }

        return payload.data;
    };

    const check = async () => {
        try {
            await request("/health");
            return true;
        } catch (error) {
            return false;
        }
    };

    return {
        request,
        check,
        isAvailable: () => backendAvailable === true,
        get: (route) => request(route),
        post: (route, body = {}) => request(route, { method: "POST", body }),
        put: (route, body = {}) => request(route, { method: "PUT", body }),
        delete: (route) => request(route, { method: "DELETE" }),
    };
})();
