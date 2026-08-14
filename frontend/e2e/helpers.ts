import { expect, type Page } from "@playwright/test";

export interface Credentials {
  email: string;
  password: string;
}

/**
 * Les identifiants ne sont JAMAIS ecrits en dur : ces tests tournent contre
 * une vraie base, et un mot de passe committe serait un mot de passe fuite.
 */
export function requireCredentials(): Credentials {
  const email = process.env.E2E_ADMIN_EMAIL;
  const password = process.env.E2E_ADMIN_PASSWORD;
  if (!email || !password) {
    throw new Error(
      "E2E_ADMIN_EMAIL et E2E_ADMIN_PASSWORD doivent etre definis (voir README, section Tests)."
    );
  }
  return { email, password };
}

export async function login(page: Page, { email, password }: Credentials): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mot de passe").fill(password);
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

/** Nom unique : les parcours ecrivent en base et sont rejoues. */
export function uniqueName(prefix: string): string {
  return `${prefix} ${Date.now().toString(36)}`;
}
