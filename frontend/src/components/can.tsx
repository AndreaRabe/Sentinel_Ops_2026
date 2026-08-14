/**
 * Masquage d'un element d'interface selon les permissions (cahier des charges
 * section 10).
 *
 * ATTENTION : ceci n'est PAS un controle de securite. Les permissions du JWT
 * ne servent qu'a eviter d'afficher une action que le serveur refuserait de
 * toute facon. La seule autorite reste `require_permission` cote backend.
 */
import type { ReactNode } from "react";
import { usePermission } from "@/lib/permissions";

export function Can({
  permission,
  children,
  fallback = null,
}: {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  return usePermission(permission) ? <>{children}</> : <>{fallback}</>;
}
