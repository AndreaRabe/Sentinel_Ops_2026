/**
 * Configuration Playwright pour les parcours critiques (cahier des charges
 * section 12).
 *
 * Ces tests s'executent contre une pile REELLE (backend + PostgreSQL migre +
 * frontend), et non contre des mocks : c'est tout leur interet, ils verifient
 * ce que les tests unitaires ne peuvent pas voir. Ils ne sont donc pas lances
 * par `make test` ni par la CI actuelle. Voir README, section Tests.
 *
 * Prerequis :
 *   E2E_BASE_URL      URL du frontend servi (defaut http://localhost:5173)
 *   E2E_ADMIN_EMAIL   compte Super Admin dont le mot de passe est deja change
 *   E2E_ADMIN_PASSWORD
 */
import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  // Les parcours ecrivent en base (creation de site, de tache) : les paralleliser
  // rendrait les assertions de liste non deterministes.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 30_000,
  reporter: [["list"]],
  use: {
    baseURL,
    locale: "fr-FR",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
