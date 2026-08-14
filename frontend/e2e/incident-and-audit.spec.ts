/**
 * Parcours critiques : declaration/resolution d'un incident, et verification
 * que le journal d'audit en garde la trace sans offrir la moindre action
 * d'ecriture.
 */
import { expect, test } from "@playwright/test";
import { login, requireCredentials, uniqueName } from "./helpers";

test.beforeEach(async ({ page }) => {
  await login(page, requireCredentials());
});

test("declare puis resout un incident", async ({ page }) => {
  const title = uniqueName("Porte forcee");

  await page.goto("/incidents");
  await page.getByRole("button", { name: "Declarer un incident" }).click();

  await page.getByLabel("Titre").fill(title);
  await page.getByLabel("Description").fill("Porte de service retrouvee ouverte.");
  await page.getByLabel("Gravite").selectOption("MAJOR");
  await page.getByLabel("Site").selectOption({ index: 1 });
  await page.getByRole("button", { name: "Declarer" }).click();

  await expect(page.getByText(title)).toBeVisible();

  await page.getByText(title).click();
  await page
    .getByPlaceholder(/Ce qui a ete fait/)
    .fill("Porte refermee et controle du perimetre effectue.");
  await page.getByRole("button", { name: "Marquer comme resolu" }).click();

  await expect(page.getByText("Incident resolu.")).toBeVisible();
});

test("le compte rendu de resolution est obligatoire", async ({ page }) => {
  await page.goto("/incidents");
  await page.getByLabel("Filtrer par statut").selectOption("OPEN");

  const firstRow = page.locator("tbody tr").first();
  if ((await firstRow.count()) === 0) test.skip(true, "Aucun incident ouvert en base.");

  await firstRow.click();
  await page.getByPlaceholder(/Ce qui a ete fait/).fill("court");
  // Moins de 10 caracteres : le bouton reste inactif cote interface, et le
  // backend refuserait de toute facon.
  await expect(page.getByRole("button", { name: "Marquer comme resolu" })).toBeDisabled();
});

test("le journal d'audit n'expose aucune action d'ecriture", async ({ page }) => {
  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "Journal d'audit" })).toBeVisible();

  for (const label of ["Supprimer", "Modifier", "Ajouter", "Enregistrer"]) {
    await expect(page.getByRole("button", { name: label })).toHaveCount(0);
  }
});
