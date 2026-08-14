import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { AppProviders } from "./app/providers";
import { router } from "./app/router";
import { apiClient } from "@/lib/api-client";
import { ScanLoader } from "@/components/ui/loaders";
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

  // Tant que la session n'est pas resolue, on affiche le chargement "scan"
  // plutot qu'un ecran blanc ou un flash vers /login.
  if (!isInitialized) {
    return (
      <div className="min-h-screen bg-bg p-8">
        <ScanLoader label="Ouverture de la session" rows={3} />
      </div>
    );
  }

  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
