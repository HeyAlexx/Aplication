// Authentication requires the server; static previews never retain passwords or grant roles.
window.AltoidssAuth = (() => {
    const visitorSession = {id:"visitor", name:"Visitante", email:"", role:"visitante",
        profileMode:"visitor", isAuthenticated:false};
    let currentSession = {...visitorSession};
    let initializePromise = null;
    // Retire credential-bearing preview storage, preserving content and profile collections.
    try {
        localStorage.removeItem("altoidss_auth_users");
        localStorage.removeItem("altoidss_auth_session");
    } catch { /* Storage can be disabled; server authentication still applies. */ }
    const roleToProfileMode = (role) => role === "admin" ? "admin" : role === "visitante" ? "visitor" : "user";
    const setSession = (session) => {
        currentSession = {...visitorSession, ...session};
        window.dispatchEvent(new CustomEvent("altoidss-auth-change", {detail:currentSession}));
        return currentSession;
    };
    const initialize = async (force = false) => {
        if (initializePromise && !force) return initializePromise;
        initializePromise = (async () => {
            try { return setSession(await AltoidssApi.get("/auth/session")); }
            catch { return setSession(visitorSession); }
        })();
        return initializePromise;
    };
    const login = async (email,password) => {
        try {
            const session = setSession(await AltoidssApi.post("/auth/login",{email,password}));
            return {ok:true, message:"Sesión iniciada como " + session.name + ".", session};
        } catch (error) {
            return {ok:false,message:error.message || "El servidor de autenticación no está disponible."};
        }
    };
    const register = async ({name,email,password}) => {
        try {
            const session = setSession(await AltoidssApi.post("/auth/register",{name,email,password}));
            return {ok:true,message:"Cuenta creada e iniciada correctamente.",session};
        } catch (error) {
            return {ok:false,message:error.message || "El servidor de autenticación no está disponible."};
        }
    };
    const logout = async () => {
        try { await AltoidssApi.post("/auth/logout"); }
        finally { setSession(visitorSession); }
        return currentSession;
    };
    initialize();
    return {initialize,getSession:()=>currentSession,login,register,logout,roleToProfileMode};
})();
