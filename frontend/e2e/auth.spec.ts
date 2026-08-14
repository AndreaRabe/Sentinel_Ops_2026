/**
 * Parcours critique : authentification et cloisonnement de l'interface.
 */
import { expect, test } from "@playwright/test";
import { login, requireCredentials } from "./helpers";

test.describe("authentification", () => {
  test("refuse des identifiants invalides sans divulguer la cause", async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill("inconnu@sentinel-ops.local");
    await page.getByLabel("Mot de passe").fill("MauvaisMotDePasse!2026");
    await page.getByRole("button", { name: "Se connecter" }).click();

    // Le message ne doit jamais distinguer "compte inexistant" de "mot de
    // passe faux" : ce serait un oracle d'enumeration de comptes.
    await expect(page.getByText(/identifiants invalides/i)).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });

  test("connecte un compte valide et affiche le dashboard", async ({ page }) => {
    const credentials = requireCredentials();
    await login(page, credentials);

    await expect(page.getByRole("heading", { name: "Poste de commandement" })).toBeVisible();
  });

  test("redirige vers /login toute route protegee sans session", async ({ page }) => {
    await page.goto("/taches");
    await expect(page).toHaveURL(/\/login/);
  });

  test("ferme la session et interdit le retour arriere", async ({ page }) => {
    await login(page, requireCredentials());
    await page.getByRole("button", { name: "Deconnexion" }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
  });
});
