import { PropsWithChildren } from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth-store";

interface ProtectedRouteProps extends PropsWithChildren {
  requiredPermission?: string;
  /** Route accessible uniquement pendant le changement de mot de passe force. */
  allowMustChangePassword?: boolean;
}

export function ProtectedRoute({ children, allowMustChangePassword = false }: ProtectedRouteProps) {
  const accessToken = useAuthStore((s) => s.accessToken);
  const mustChangePassword = useAuthStore((s) => s.mustChangePassword);

  if (!accessToken) return <Navigate to="/login" replace />;
  if (mustChangePassword && !allowMustChangePassword) {
    return <Navigate to="/change-password" replace />;
  }
  if (!mustChangePassword && allowMustChangePassword) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
