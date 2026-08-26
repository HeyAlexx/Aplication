// Menú de cuenta compartido: conserva el acceso al login para visitantes y muestra la sesión activa.
(() => {
    const originalIcon = document.querySelector(".login-icon");

    if (!originalIcon || !window.AltoidssAuth) {
        return;
    }

    let accountTrigger = originalIcon;
    let accountMenu = null;
    let logoutButton = null;
    let isOpen = false;

    const initialsFrom = (name) => String(name || "AL")
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((part) => part.charAt(0))
        .join("")
        .toUpperCase() || "AL";

    const roleLabel = (role) => role === "admin" ? "Administrador" : "Usuario";

    const createAccountMenu = () => {
        const menu = document.createElement("section");
        menu.className = "account-menu";
        menu.id = "account-menu";
        menu.setAttribute("role", "dialog");
        menu.setAttribute("aria-label", "Perfil actual");
        menu.setAttribute("aria-hidden", "true");
        menu.innerHTML = `
            <div class="account-menu-profile">
                <span class="account-menu-avatar" data-account-avatar aria-hidden="true">AL</span>
                <div class="account-menu-identity">
                    <span class="account-menu-label">Perfil actual</span>
                    <strong data-account-name>Usuario</strong>
                    <span data-account-email></span>
                </div>
            </div>
            <span class="account-menu-role" data-account-role>Usuario</span>
            <div class="account-menu-actions">
                <a class="account-menu-link" href="dashboard.html?tab=profile">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
                        <path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6m2-3a2 2 0 1 1-4 0 2 2 0 0 1 4 0m4 8c0 1-1 1-1 1H3s-1 0-1-1 1-4 6-4 6 3 6 4m-1-.004c-.001-.246-.154-.986-.832-1.664C11.516 10.68 10.289 10 8 10s-3.516.68-4.168 1.332c-.678.678-.83 1.418-.832 1.664z"/>
                    </svg>
                    Abrir perfil
                </a>
                <button class="account-menu-logout" type="button" data-account-logout>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true">
                        <path fill-rule="evenodd" d="M10 12.5a.5.5 0 0 0 .5.5h2a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-2a.5.5 0 0 0 0 1H12v8h-1.5a.5.5 0 0 0-.5.5"/>
                        <path fill-rule="evenodd" d="M.146 8.354a.5.5 0 0 1 0-.708l3-3a.5.5 0 1 1 .708.708L1.707 7.5H10.5a.5.5 0 0 1 0 1H1.707l2.147 2.146a.5.5 0 0 1-.708.708z"/>
                    </svg>
                    Cerrar sesión
                </button>
            </div>
        `;
        document.body.append(menu);
        logoutButton = menu.querySelector("[data-account-logout]");

        logoutButton.addEventListener("click", async () => {
            logoutButton.disabled = true;
            logoutButton.classList.add("is-loading");
            logoutButton.lastChild.textContent = " Cerrando sesión...";
            await AltoidssAuth.logout();
            window.location.replace("index.html");
        });

        return menu;
    };

    const positionMenu = () => {
        if (!accountMenu || !isOpen) {
            return;
        }

        const triggerRect = accountTrigger.getBoundingClientRect();
        const menuWidth = Math.min(300, window.innerWidth - 24);
        const left = Math.min(
            Math.max(12, triggerRect.right - menuWidth),
            window.innerWidth - menuWidth - 12
        );

        accountMenu.style.width = `${menuWidth}px`;
        accountMenu.style.left = `${left}px`;
        accountMenu.style.top = `${triggerRect.bottom + 10}px`;
    };

    const setMenuOpen = (open) => {
        if (!accountMenu) {
            return;
        }

        isOpen = open;
        accountMenu.classList.toggle("is-open", open);
        accountMenu.setAttribute("aria-hidden", String(!open));
        accountTrigger.classList.toggle("is-menu-open", open);
        accountTrigger.setAttribute("aria-expanded", String(open));

        if (open) {
            positionMenu();
        }
    };

    const ensureButtonTrigger = () => {
        if (accountTrigger.tagName === "BUTTON") {
            return;
        }

        const button = document.createElement("button");
        button.type = "button";
        button.className = accountTrigger.className;
        button.innerHTML = accountTrigger.innerHTML;
        accountTrigger.replaceWith(button);
        accountTrigger = button;
        accountTrigger.addEventListener("click", () => setMenuOpen(!isOpen));
    };

    const syncAccount = (session) => {
        if (!session?.isAuthenticated) {
            setMenuOpen(false);
            return;
        }

        ensureButtonTrigger();
        accountMenu ||= createAccountMenu();
        accountTrigger.classList.add("has-session");
        accountTrigger.setAttribute("aria-label", `Abrir perfil de ${session.name}`);
        accountTrigger.setAttribute("title", `Perfil de ${session.name}`);
        accountTrigger.setAttribute("aria-haspopup", "dialog");
        accountTrigger.setAttribute("aria-controls", accountMenu.id);
        accountTrigger.setAttribute("aria-expanded", "false");

        accountMenu.querySelector("[data-account-avatar]").textContent = initialsFrom(session.name);
        accountMenu.querySelector("[data-account-name]").textContent = session.name || "Usuario";
        accountMenu.querySelector("[data-account-email]").textContent = session.email || "Sin correo registrado";
        accountMenu.querySelector("[data-account-role]").textContent = roleLabel(session.role);
    };

    document.addEventListener("click", (event) => {
        if (isOpen && !accountMenu?.contains(event.target) && !accountTrigger.contains(event.target)) {
            setMenuOpen(false);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && isOpen) {
            setMenuOpen(false);
            accountTrigger.focus();
        }
    });

    window.addEventListener("resize", positionMenu);
    window.addEventListener("scroll", positionMenu, { passive: true });
    window.addEventListener("altoidss-auth-change", (event) => syncAccount(event.detail));

    AltoidssAuth.initialize().then(syncAccount);
})();
