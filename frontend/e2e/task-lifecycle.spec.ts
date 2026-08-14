/**
 * Parcours critique : cycle de vie d'une tache, de la creation a la cloture.
 *
 * Verifie ce qu'aucun test unitaire ne peut voir : que la machine a etats du
 * backend, les permissions et l'interface se comportent de facon coherente
 * sur un enchainement reel.
 */
import { expect, test } from "@playwright/test";
import { login, requireCredentials, uniqueName } from "./helpers";

test.beforeEach(async ({ page }) => {
  await login(page, requireCredentials());
});

test("cree une tache, la demarre puis la cloture", async ({ page }) => {
  const title = uniqueName("Ronde de controle");

  await page.goto("/taches");
  await page.getByRole("button", { name: "Nouvelle tache" }).click();

  await page.getByLabel("Titre").fill(title);
  await page.getByLabel("Site").selectOption({ index: 1 });
  await page.getByLabel("Checklist").fill("Verifier les acces\nControler les cameras");
  await page.getByRole("button", { name: "Creer la tache" }).click();

  await expect(page.getByText(title)).toBeVisible();

  // Ouverture du detail, puis transitions successives.
  await page.getByText(title).click();
  await page.getByRole("button", { name: "Demarrer" }).click();
  await expect(page.getByText("En cours")).toBeVisible();

  await page.getByRole("button", { name: "Terminee" }).click();
  await expect(page.getByText("Terminee")).toBeVisible();
});

test("une tache terminee ne propose plus de transition", async ({ page }) => {
  await page.goto("/taches");
  await page.getByLabel("Filtrer par statut").selectOption("COMPLETED");

  const firstRow = page.locator("tbody tr").first();
  if ((await firstRow.count()) === 0) test.skip(true, "Aucune tache terminee en base.");

  await firstRow.click();
  await expect(page.getByRole("button", { name: "Demarrer" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Terminee" })).toHaveCount(0);
});

test("la checklist se coche et se conserve", async ({ page }) => {
  const title = uniqueName("Tache avec checklist");

  await page.goto("/taches");
  await page.getByRole("button", { name: "Nouvelle tache" }).click();
  await page.getByLabel("Titre").fill(title);
  await page.getByLabel("Site").selectOption({ index: 1 });
  await page.getByLabel("Checklist").fill("Point unique");
  await page.getByRole("button", { name: "Creer la tache" }).click();

  await page.getByText(title).click();
  const checkbox = page.getByRole("checkbox").first();
  await checkbox.check();

  await page.getByRole("button", { name: "Fermer" }).click();
  await page.getByText(title).click();
  await expect(page.getByRole("checkbox").first()).toBeChecked();
});
