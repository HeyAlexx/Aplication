// Controla el cambio animado entre el formulario de login y el formulario de registro.
const authCard = document.querySelector("#authCard");
const authButtons = document.querySelectorAll("[data-auth-view]");
const socialLoginButtons = document.querySelectorAll("[data-provider]");
const loginForm = document.querySelector("#loginForm");
const registerForm = document.querySelector("#registerForm");
const loginFeedback = document.querySelector("#loginFeedback");
const registerFeedback = document.querySelector("#registerFeedback");

const showFeedback = (target, result) => {
    target.textContent = result.message;
    target.classList.toggle("is-success", result.ok);
    target.classList.toggle("is-error", !result.ok);
};

const goToDashboard = () => {
    window.location.href = "dashboard.html";
};

authButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const showRegister = button.dataset.authView === "register";

        authCard.classList.toggle("show-register", showRegister);

        authButtons.forEach((item) => {
            item.classList.toggle("is-active", item === button);
        });
    });
});

// Preparación para autenticación social futura.
// Cuando exista backend y base de datos, aquí se conectarán Google y GitHub.
socialLoginButtons.forEach((button) => {
    button.addEventListener("click", () => {
        if (button.disabled) {
            return;
        }

        const provider = button.dataset.provider;
        console.log(`Autenticación pendiente con ${provider}`);
    });
});

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const result = await AltoidssAuth.login(
        document.querySelector("#login-email").value,
        document.querySelector("#login-password").value,
    );

    showFeedback(loginFeedback, result);

    if (result.ok) {
        setTimeout(goToDashboard, 450);
    }
});

registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const result = await AltoidssAuth.register({
        name: document.querySelector("#register-name").value,
        email: document.querySelector("#register-email").value,
        password: document.querySelector("#register-password").value,
    });

    showFeedback(registerFeedback, result);

    if (result.ok) {
        setTimeout(goToDashboard, 450);
    }
});
