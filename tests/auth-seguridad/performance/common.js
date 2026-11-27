// =============================================
// Imports
// ---------------------------------------------
import http from "k6/http";

// =============================================
// Constantes
// ---------------------------------------------
// Dentro de la red del compose QA el backend se llama "backend"
export const BASE_URL = __ENV.BASE_URL || "http://backend:8000/api/v1";
export const JSON_HEADERS = { "Content-Type": "application/json" };
// Las cedulas de carga empiezan en 7 para no chocar con el seed (9...) ni con pytest (8...)
const LOAD_ID_PREFIX = "7";

// =============================================
// Funciones
// ---------------------------------------------
// Genera una cedula sintetica de 9 digitos
export function new_identification() {
  let digits = LOAD_ID_PREFIX;
  for (let position = 0; position < 8; position++) {
    digits = digits + String(Math.floor(Math.random() * 10));
  }
  return digits;
}

// Registra un usuario sintetico y devuelve sus credenciales; falla si la API lo rechaza
export function register_user() {
  const identification = new_identification();
  const user = {
    email: "qa.carga." + identification + "@example.com",
    full_name: "Persona Carga " + identification,
    identification: identification,
    phone: "88880000",
    password: "QaCarga-" + identification,
  };
  const response = http.post(BASE_URL + "/auth/register", JSON.stringify(user), {
    headers: JSON_HEADERS,
  });
  if (response.status !== 201) {
    throw new Error("Could not register load user: " + response.status + " " + response.body);
  }
  return { identification: identification, password: user.password };
}

// Inicia sesion y devuelve la respuesta completa, para medirla en el escenario
export function login(credentials, tags) {
  return http.post(BASE_URL + "/auth/login", JSON.stringify(credentials), {
    headers: JSON_HEADERS,
    tags: tags,
  });
}

// Encabezados con el token Bearer
export function auth_headers(token) {
  return { "Content-Type": "application/json", Authorization: "Bearer " + token };
}
