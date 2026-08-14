/**
 * Le masquage par permission est un confort d'interface, pas une securite :
 * ces tests verifient qu'il ne se trompe pas dans le sens "affiche alors que
 * le serveur refusera", ce qui produirait des 403 sous les yeux de
 * l'utilisateur.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/store/auth-store";

function setPermissions(permissions: string[]) {
  useAuthStore.setState({ permissions });
}

/** Reprend la regle de usePermission, hors contexte React. */
function allows(permission: string): boolean {
  const permissions = useAuthStore.getState().permissions;
  return permissions.includes("*") || permissions.includes(permission);
}

describe("evaluation des permissions", () => {
  beforeEach(() => setPermissions([]));

  it("refuse tout quand aucune permission n'est chargee", () => {
    expect(allows("task:read")).toBe(false);
  });

  it("accorde une permission explicitement listee", () => {
    setPermissions(["task:read", "task:comment"]);
    expect(allows("task:read")).toBe(true);
  });

  it("refuse une permission absente de la liste", () => {
    setPermissions(["task:read"]);
    expect(allows("task:delete")).toBe(false);
  });

  it("accorde tout au joker du Super Admin", () => {
    setPermissions(["*"]);
    expect(allows("audit:read")).toBe(true);
    expect(allows("settings:update")).toBe(true);
  });

  it("ne confond pas un prefixe avec une permission complete", () => {
    setPermissions(["task:update_own_status"]);
    expect(allows("task:update")).toBe(false);
  });
});

describe("session", () => {
  it("vide les permissions a la deconnexion", () => {
    setPermissions(["*"]);
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.permissions).toEqual([]);
    expect(state.accessToken).toBeNull();
    expect(state.role).toBeNull();
  });
});
