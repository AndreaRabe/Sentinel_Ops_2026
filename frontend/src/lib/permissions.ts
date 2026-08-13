import { useAuthStore } from "@/store/auth-store";

/**
 * Les permissions accordees viennent du claim "perms" du JWT (calcule cote
 * serveur depuis role_permissions) - pas de matrice dupliquee cote client.
 */
export function usePermission(permission: string): boolean {
  const permissions = useAuthStore((s) => s.permissions);
  return permissions.includes("*") || permissions.includes(permission);
}
