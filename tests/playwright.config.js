// =============================================
// Imports
// ---------------------------------------------
import { defineConfig, devices } from "@playwright/test";

// =============================================
// Constantes
// ---------------------------------------------
// URL del frontend bajo prueba, configurable con QA_WEB_URL
// 127.0.0.1 y no localhost: en Windows localhost intenta IPv6 primero y agrega ~2 s por peticion
const WEB_URL = process.env.QA_WEB_URL || "http://127.0.0.1:5173";

// =============================================
// Configuracion
// ---------------------------------------------
// Busca los *.spec.js dentro de tests/<area>/e2e/ de las tres areas
export default defineConfig({
  testDir: ".",
  testMatch: "**/e2e/**/*.spec.js",
  testIgnore: "**/node_modules/**",
  outputDir: "../reports/e2e/test-results",
  reporter: [
    ["list"],
    ["html", { outputFolder: "../reports/e2e/html", open: "never" }],
  ],
  use: {
    baseURL: WEB_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
