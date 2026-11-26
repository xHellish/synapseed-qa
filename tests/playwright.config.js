// =============================================
// Imports
// ---------------------------------------------
import { defineConfig, devices } from "@playwright/test";

// =============================================
// Constantes
// ---------------------------------------------
// URL del frontend bajo prueba, configurable con QA_WEB_URL
const WEB_URL = process.env.QA_WEB_URL || "http://localhost:5173";

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
