import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { logout } from "@/features/auth/api";
import { getCurrentUser } from "@/features/admin/api";
import { ROLE_LABELS } from "@/components/ui/badge";
import { useAuthStore } from "@/store/auth-store";

export function UserMenu() {
  const navigate = useNavigate();
  const clearSession = useAuthStore((s) => s.logout);

  const me = useQuery({ queryKey: ["me"], queryFn: getCurrentUser, staleTime: 5 * 60_000 });

  const signOut = useMutation({
    mutationFn: logout,
    // Meme si l'appel echoue (reseau coupe), on nettoie l'etat local :
    // conserver un token en memoire apres une demande de deconnexion serait pire.
    onSettled: () => {
      clearSession();
      navigate("/login", { replace: true });
    },
  });

  return (
    <div className="flex items-center gap-3">
      <div className="hidden text-right sm:block">
        <div className="text-sm text-textPrimary">
          {me.data ? `${me.data.first_name} ${me.data.last_name}` : "…"}
        </div>
        <div className="font-mono text-[11px] uppercase tracking-widest text-textTertiary">
          {me.data ? (ROLE_LABELS[me.data.role] ?? me.data.role) : ""}
        </div>
      </div>
      <button
        type="button"
        onClick={() => signOut.mutate()}
        className="rounded border border-border px-3 py-1.5 text-sm text-textSecondary
                   hover:bg-surfaceHover hover:text-textPrimary"
      >
        Deconnexion
      </button>
    </div>
  );
}
