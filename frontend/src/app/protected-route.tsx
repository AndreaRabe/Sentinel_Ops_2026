import { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth-store";

interface ProtectedRouteProps extends PropsWithChildren {
  /**
   * Permission exigee pour afficher la route. Confort d'interface uniquement :
   * chaque endpoint appele reverifie ses propres droits cote serveur.
   */
  requiredPermission?: string;
  /** Route accessible uniquement pendant le changement de mot de passe force. */
  allowMustChangePassword?: boolean;
}

export function ProtectedRoute({
  children,
  requiredPermission,
  allowMustChangePassword = false,
}: ProtectedRouteProps) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const mustChangePassword = useAuthStore((s) => s.mustChangePassword);
  const permissions = useAuthStore((s) => s.permissions);

  if (!accessToken) return <Navigate to="/login" replace />;
  if (mustChangePassword && !allowMustChangePassword) {
    return <Navigate to="/change-password" replace />;
  }
  if (!mustChangePassword && allowMustChangePassword) {
    return <Navigate to="/" replace />;
  }
  if (
    requiredPermission &&
    !permissions.includes("*") &&
    !permissions.includes(requiredPermission)
  ) {
    // Renvoi vers le dashboard plutot qu'une page 403 : l'entree de menu
    // correspondante est deja masquee, arriver ici signifie une URL saisie
    // a la main.
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
