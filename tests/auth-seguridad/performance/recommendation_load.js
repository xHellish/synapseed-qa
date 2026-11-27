// =============================================
// PERF-02 Recomendaciones simultaneas (RNF-04, RNF-03)
// ---------------------------------------------
// 10 usuarios virtuales piden 2 recomendaciones cada uno y consultan el estado
// cada 2 s hasta COMPLETED o FAILED. Umbrales declarados en docs/plan-calidad.md.

// =============================================
// Imports
// ---------------------------------------------
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import { BASE_URL, auth_headers, login, register_user } from "./common.js";

// =============================================
// Constantes
// ---------------------------------------------
const VIRTUAL_USERS = 10;
const REQUESTS_PER_USER = 2;
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
    concurrent_recommendations: {
      executor: "per-vu-iterations",
      vus: VIRTUAL_USERS,
      iterations: REQUESTS_PER_USER,
      maxDuration: "25m",
    },
  },
  thresholds: {
    "http_req_duration{endpoint:request}": ["p(95)<1000"],
    recommendation_total_ms: ["p(95)<=50000"],
    recommendation_completed: ["rate==1"],
  },
};

// =============================================
// Ciclo de vida
// ---------------------------------------------
// Crea un usuario sintetico con sesion por cada usuario virtual
export function setup() {
  const tokens = [];
  for (let index = 0; index < VIRTUAL_USERS; index++) {
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
    recommendation_completed.add(false);
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
  recommendation_total_ms.add(Date.now() - started_at);
  recommendation_completed.add(final_status === "completed");
  check(final_status, { "recommendation completed": (status) => status === "completed" });
}
