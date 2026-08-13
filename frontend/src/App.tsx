import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { AppProviders } from "./app/providers";
import { router } from "./app/router";
import { apiClient } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";

export default function App() {
  const isInitialized = useAuthStore((s) => s.isInitialized);
  const setSession = useAuthStore((s) => s.setSession);
  const setInitialized = useAuthStore((s) => s.setInitialized);

  useEffect(() => {
    apiClient
      .post("/auth/refresh")
      .then(({ data }) => setSession(data.access_token, data.must_change_password))
      .catch(() => {
        // Pas de session valide (pas de cookie de refresh ou expire) - reste deconnecte.
      })
      .finally(() => setInitialized());
  }, [setSession, setInitialized]);

  // TODO Phase 9 : ecran de chargement "scan" (voir cahier des charges section 11)
  if (!isInitialized) return null;

  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
