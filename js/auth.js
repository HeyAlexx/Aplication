// Autenticación mediante PHP. El modo local permite registrar una cuenta si se abre sin servidor PHP.
window.AltoidssAuth = (() => {
    const sessionKey = "altoidss_auth_session";
    const usersKey = "altoidss_auth_users";
    const visitorSession = {
        id: "visitor",
        name: "Visitante",
        email: "",
        role: "visitante",
        profileMode: "visitor",
        isAuthenticated: false,
    };
    let currentSession = visitorSession;
    let initializePromise = null;

    const roleToProfileMode = (role) => role === "admin" ? "admin" : (role === "visitante" ? "visitor" : "user");

    const readLocalSession = () => {
        try {
            return JSON.parse(localStorage.getItem(sessionKey)) || visitorSession;
        } catch (error) {
            return visitorSession;
        }
    };

    const setSession = (session, persistLocally = false) => {
        currentSession = { ...visitorSession, ...session };

        if (persistLocally) {
            localStorage.setItem(sessionKey, JSON.stringify(currentSession));
        } else {
            localStorage.removeItem(sessionKey);
        }

        window.dispatchEvent(new CustomEvent("altoidss-auth-change", { detail: currentSession }));
        return currentSession;
    };

    const initialize = async (force = false) => {
        if (initializePromise && !force) {
            return initializePromise;
        }

        initializePromise = (async () => {
            try {
                return setSession(await AltoidssApi.get("/auth/session"));
            } catch (error) {
                console.info("Altoidss usa autenticación local de previsualización porque PHP no está disponible.");
                currentSession = readLocalSession();
                return currentSession;
            }
        })();

        return initializePromise;
    };

    const getSession = () => currentSession;

    const localUsers = () => {
        try {
            return JSON.parse(localStorage.getItem(usersKey)) || [];
        } catch (error) {
            return [];
        }
    };

    const login = async (email, password) => {
        try {
            const session = await AltoidssApi.post("/auth/login", { email, password });
            setSession(session);
            return { ok: true, message: `Sesión iniciada como ${session.name}.`, session };
        } catch (error) {
            if (AltoidssApi.isAvailable()) {
                return { ok: false, message: error.message };
            }

            const user = localUsers().find((item) => item.email.toLowerCase() === email.trim().toLowerCase() && item.password === password);
            if (!user) {
                return { ok: false, message: "Correo o contraseña incorrectos." };
            }
            const session = setSession({ ...user, isAuthenticated: true }, true);
            return { ok: true, message: `Sesión local iniciada como ${session.name}.`, session };
        }
    };

    const register = async ({ name, email, password }) => {
        try {
            const session = await AltoidssApi.post("/auth/register", { name, email, password });
            setSession(session);
            return { ok: true, message: "Cuenta creada e iniciada correctamente.", session };
        } catch (error) {
            if (AltoidssApi.isAvailable()) {
                return { ok: false, message: error.message };
            }

            const users = localUsers();
            if (users.some((item) => item.email.toLowerCase() === email.trim().toLowerCase())) {
                return { ok: false, message: "Ese correo ya existe en la previsualización local." };
            }
            const user = { id: crypto.randomUUID(), name: name.trim(), email: email.trim().toLowerCase(), password, role: "usuario", profileMode: "user" };
            users.push(user);
            localStorage.setItem(usersKey, JSON.stringify(users));
            const session = setSession({ ...user, isAuthenticated: true }, true);
            return { ok: true, message: "Cuenta local creada correctamente.", session };
        }
    };

    const logout = async () => {
        try {
            await AltoidssApi.post("/auth/logout");
        } catch (error) {
            // La sesión local también debe poder cerrarse durante la previsualización estática.
        }
        return setSession(visitorSession, false);
    };

    initialize();

    return { initialize, getSession, login, register, logout, roleToProfileMode };
})();
