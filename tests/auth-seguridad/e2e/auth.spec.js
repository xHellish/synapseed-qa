// =============================================
// Pruebas E2E de registro e inicio de sesion (RF-01, RF-02)
// ---------------------------------------------
// Recorren la interfaz real del ambiente QA local como lo haria una persona agricultora.
// Cada prueba crea su propia cuenta sintetica; las cedulas empiezan en 4
// (pytest usa 8, k6 7 y Postman 6).
// Uso, desde tests/ con el ambiente QA arriba:
//   npx playwright test auth-seguridad

// =============================================
// Imports
// ---------------------------------------------
import { test, expect } from "@playwright/test";

// =============================================
// Constantes
// ---------------------------------------------
const API_PREFIX = "/api/v1";
const PHONE_DIGITS = "88880000";

// =============================================
// Funciones
// ---------------------------------------------
// Genera una cuenta sintetica con cedula de 9 digitos que empieza en 4
function new_account() {
  let identification = "4";
  for (let position = 0; position < 8; position++) {
    identification = identification + String(Math.floor(Math.random() * 10));
  }
  return {
    identification: identification,
    full_name: "Persona E2E " + identification,
    email: "qa.e2e." + identification + "@example.com",
    password: "QaE2e-" + identification,
  };
}

// Registra la cuenta directo por la API, para pruebas que solo ejercitan el login
async function register_by_api(request, account) {
  const response = await request.post(API_PREFIX + "/auth/register", {
    data: {
      identification: account.identification,
      full_name: account.full_name,
      email: account.email,
      phone: PHONE_DIGITS,
      password: account.password,
    },
  });
  expect(response.status(), "registro previo por la API").toBe(201);
}

// Llena y envia el formulario de inicio de sesion
async function submit_login(page, identification, password) {
  await page.getByLabel("Número de identificación:").fill(identification);
  await page.getByLabel("Contraseña:", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
}

// =============================================
// Pruebas
// ---------------------------------------------
test("CP-RF01-08 registro por la interfaz y redireccion al login", async ({ page, request }) => {
  const account = new_account();

  // Abre el formulario de registro desde el login, como lo haria la persona usuaria
  await page.goto("/login");
  await page.getByRole("link", { name: "Crear cuenta" }).click();
  await expect(page).toHaveURL(/\/register$/);

  // Llena el formulario; la interfaz da formato a la cedula y al telefono mientras se escribe
  await page.getByLabel("Número de identificación:").fill(account.identification);
  await page.getByLabel("Nombre completo:").fill(account.full_name);
  await page.getByLabel("Teléfono:").fill(PHONE_DIGITS);
  await page.getByLabel("Correo electrónico:").fill(account.email);
  await page.getByLabel("Contraseña:", { exact: true }).fill(account.password);
  await page.getByLabel("Confirmar contraseña:").fill(account.password);
  await expect(page.getByLabel("Número de identificación:")).toHaveValue(
    account.identification.slice(0, 1) + " " + account.identification.slice(1, 5) + " " + account.identification.slice(5),
  );
  await expect(page.getByLabel("Teléfono:")).toHaveValue("8888 - 0000");

  // Envia y espera la respuesta del backend y la redireccion al login.
  // No se valida el aviso "Cuenta creada": solo dura 350 ms antes de navegar y la prueba se vuelve inestable
  const register_response_promise = page.waitForResponse(function (response) {
    return response.url().endsWith(API_PREFIX + "/auth/register");
  });
  await page.getByRole("button", { name: "Crear cuenta" }).click();
  const register_response = await register_response_promise;
  expect(register_response.status()).toBe(201);
  await expect(page).toHaveURL(/\/login$/);

  // Confirma por la API que la cuenta quedo creada con la cedula sin espacios
  const login_response = await request.post(API_PREFIX + "/auth/login", {
    data: { identification: account.identification, password: account.password },
  });
  expect(login_response.status()).toBe(200);
  const login_body = await login_response.json();
  expect(login_body.user.identification).toBe(account.identification);
});

test("CP-RF02-06 login por la interfaz entra a la zona protegida", async ({ page, request }) => {
  const account = new_account();
  await register_by_api(request, account);

  // Inicia sesion con la cedula y la contrasena de la cuenta nueva
  await page.goto("/login");
  const login_response_promise = page.waitForResponse(function (response) {
    return response.url().endsWith(API_PREFIX + "/auth/login");
  });
  await submit_login(page, account.identification, account.password);

  // El backend acepta el login y la interfaz lleva a la gestion de zonas, que es una ruta protegida.
  // Igual que en el registro, el aviso de exito dura 300 ms y no se valida
  const login_response = await login_response_promise;
  expect(login_response.status()).toBe(200);
  await expect(page).toHaveURL(/\/zones$/);
  await expect(page.getByText("Gestión de zonas", { exact: true })).toBeVisible();

  // La sesion sobrevive a recargar la pagina
  await page.reload();
  await expect(page).toHaveURL(/\/zones$/);
});

test("CP-RF02-07 sin sesion o con contrasena incorrecta no se entra a rutas protegidas", async ({ page, request }) => {
  const account = new_account();
  await register_by_api(request, account);

  // Sin sesion, una ruta protegida redirige al login
  await page.goto("/zones");
  await expect(page).toHaveURL(/\/login$/);

  // Con contrasena incorrecta se muestra el mensaje generico y se sigue en el login
  await submit_login(page, account.identification, "Incorrecta-E2E-123");
  await expect(page.getByText("No se pudo iniciar sesión", { exact: true })).toBeVisible();
  await expect(page.getByText("Cédula o contraseña incorrectos", { exact: true })).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);

  // Intentar entrar por la URL despues del fallo tampoco da acceso
  await page.goto("/zones");
  await expect(page).toHaveURL(/\/login$/);
});
