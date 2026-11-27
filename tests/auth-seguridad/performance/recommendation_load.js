// =============================================
// PERF-02 Recomendaciones simultaneas (RNF-04, RNF-03)
// ---------------------------------------------
// Carga creciente en escalones de 2, 5 y 10 usuarios virtuales: cada uno pide una
// recomendacion, consulta el estado cada 2 s hasta COMPLETED o FAILED y vuelve a pedir.
// Umbrales declarados en docs/plan-calidad.md; se reportan tambien por escalon.

// =============================================
// Imports
// ---------------------------------------------
import http from "k6/http";
import { check, sleep } from "k6";
import exec from "k6/execution";
import { Rate, Trend } from "k6/metrics";
import { BASE_URL, auth_headers, login, register_user } from "./common.js";

// =============================================
// Constantes
// ---------------------------------------------
// Escalones de carga: cada nivel se sostiene 1 min despues de subir
const LOAD_LEVELS = [2, 5, 10];
const MAX_VIRTUAL_USERS = 10;
const POLL_INTERVAL_SECONDS = 2;
const POLL_LIMIT_SECONDS = 600;
const FINAL_STATUSES = ["completed", "failed"];
const RECOMMENDATION_REQUEST = {
  crop: "Tomate",
  crop_stage: "Floración",
  problem_to_solve: "Plagas",
  soil_type: "Franco",
  humidity: "Media",
  temperature: 24,
  water_quality: "Buena",
  max_budget_per_liter: 15000,
};

// =============================================
// Metricas propias
// ---------------------------------------------
const recommendation_total_ms = new Trend("recommendation_total_ms", true);
const recommendation_completed = new Rate("recommendation_completed");

// =============================================
// Configuracion del escenario
// ---------------------------------------------
export const options = {
  scenarios: {
    increasing_recommendations: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: [
        { duration: "30s", target: 2 },
        { duration: "1m", target: 2 },
        { duration: "15s", target: 5 },
        { duration: "1m", target: 5 },
        { duration: "15s", target: 10 },
        { duration: "1m", target: 10 },
        { duration: "15s", target: 0 },
      ],
      // Las recomendaciones en curso terminan aunque la carga ya este bajando
      gracefulRampDown: "10m",
      gracefulStop: "10m",
    },
  },
  thresholds: {
    "http_req_duration{endpoint:request}": ["p(95)<1000"],
    recommendation_total_ms: ["p(95)<=50000"],
    "recommendation_total_ms{load:2}": ["p(95)<=50000"],
    "recommendation_total_ms{load:5}": ["p(95)<=50000"],
    "recommendation_total_ms{load:10}": ["p(95)<=50000"],
    recommendation_completed: ["rate==1"],
  },
};

// =============================================
// Funciones
// ---------------------------------------------
// Devuelve el escalon de carga (2, 5 o 10) al que pertenecen los usuarios activos ahora
function current_load_level() {
  const active_users = exec.instance.vusActive;
  for (const level of LOAD_LEVELS) {
    if (active_users <= level) {
      return String(level);
    }
  }
  return String(LOAD_LEVELS[LOAD_LEVELS.length - 1]);
}

// =============================================
// Ciclo de vida
// ---------------------------------------------
// Crea un usuario sintetico con sesion por cada usuario virtual
export function setup() {
  const tokens = [];
  for (let index = 0; index < MAX_VIRTUAL_USERS; index++) {
    const credentials = register_user();
    const response = login(credentials, { endpoint: "login" });
    if (response.status !== 200) {
      throw new Error("Could not log in load user: " + response.status);
    }
    tokens.push(response.json("access_token"));
  }
  return { tokens: tokens };
}

// Una iteracion: pide una recomendacion y espera su estado final
export default function (data) {
  const headers = auth_headers(data.tokens[(__VU - 1) % data.tokens.length]);
  const started_at = Date.now();
  // El escalon se fija al pedir, que es cuando la carga influye en la espera
  const load_tags = { load: current_load_level() };

  // Solicitud: debe responder sin esperar al pipeline
  const request = http.post(BASE_URL + "/recommendations/request", JSON.stringify(RECOMMENDATION_REQUEST), {
    headers: headers,
    tags: { endpoint: "request" },
  });
  const accepted = check(request, {
    "request 202": (response) => response.status === 202,
    "request returns id": (response) => response.json("recommendation_id") !== undefined,
  });
  if (!accepted) {
    recommendation_completed.add(false, load_tags);
    return;
  }
  const detail_url = BASE_URL + "/recommendations/" + request.json("recommendation_id");

  // Consulta del estado hasta que termine o se agote el limite
  let final_status = "timeout";
  while ((Date.now() - started_at) / 1000 < POLL_LIMIT_SECONDS) {
    sleep(POLL_INTERVAL_SECONDS);
    const detail = http.get(detail_url, { headers: headers, tags: { endpoint: "detail" } });
    if (detail.status !== 200) {
      continue;
    }
    const status = String(detail.json("status")).toLowerCase();
    if (FINAL_STATUSES.includes(status)) {
      final_status = status;
      break;
    }
  }

  // Registro del resultado de esta recomendacion
  recommendation_total_ms.add(Date.now() - started_at, load_tags);
  recommendation_completed.add(final_status === "completed", load_tags);
  check(final_status, { "recommendation completed": (status) => status === "completed" });
}
