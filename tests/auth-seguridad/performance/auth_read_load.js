// =============================================
// PERF-01 Autenticacion y lectura (RNF-04)
// ---------------------------------------------
// Rampa hasta 20 usuarios virtuales: cada iteracion inicia sesion y lee perfil,
// catalogo de cultivos y zonas. Umbrales declarados en docs/plan-calidad.md.

// =============================================
// Imports
// ---------------------------------------------
import http from "k6/http";
import { check, sleep } from "k6";
import { BASE_URL, auth_headers, login, register_user } from "./common.js";

// =============================================
// Constantes
// ---------------------------------------------
const VIRTUAL_USERS = 20;
const THINK_TIME_SECONDS = 1;

// =============================================
// Configuracion del escenario
// ---------------------------------------------
export const options = {
  stages: [
    { duration: "30s", target: VIRTUAL_USERS },
    { duration: "1m", target: VIRTUAL_USERS },
    { duration: "15s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{endpoint:login}": ["p(95)<1000"],
    "http_req_duration{kind:read}": ["p(95)<500"],
    checks: ["rate>0.99"],
  },
};

// =============================================
// Ciclo de vida
// ---------------------------------------------
// Crea un usuario sintetico por cada usuario virtual
export function setup() {
  const users = [];
  for (let index = 0; index < VIRTUAL_USERS; index++) {
    users.push(register_user());
  }
  return { users: users };
}

// Una iteracion: login y tres lecturas con el token recibido
export default function (data) {
  // Cada usuario virtual usa siempre la misma cuenta
  const credentials = data.users[(__VU - 1) % data.users.length];

  // Login con cedula
  const login_response = login(credentials, { endpoint: "login" });
  const logged_in = check(login_response, {
    "login 200": (response) => response.status === 200,
    "login returns token": (response) => response.json("access_token") !== undefined,
  });
  if (!logged_in) {
    sleep(THINK_TIME_SECONDS);
    return;
  }
  const headers = auth_headers(login_response.json("access_token"));

  // Lecturas autenticadas
  const profile = http.get(BASE_URL + "/users/me", {
    headers: headers,
    tags: { endpoint: "users_me", kind: "read" },
  });
  check(profile, {
    "profile 200": (response) => response.status === 200,
    "profile is own": (response) => response.json("identification") === credentials.identification,
  });

  const crops = http.get(BASE_URL + "/catalogs/crops", {
    headers: headers,
    tags: { endpoint: "catalog_crops", kind: "read" },
  });
  check(crops, {
    "crops 200": (response) => response.status === 200,
    "crops not empty": (response) => response.body.length > 2,
  });

  const zones = http.get(BASE_URL + "/zones", {
    headers: headers,
    tags: { endpoint: "zones", kind: "read" },
  });
  check(zones, { "zones 200": (response) => response.status === 200 });

  sleep(THINK_TIME_SECONDS);
}
