import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { changePassword } from "@/features/auth/api";
import { changePasswordSchema, type ChangePasswordFormValues } from "@/features/auth/schemas";
import { useAuthStore } from "@/store/auth-store";

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const accessToken = useAuthStore((s) => s.accessToken);
  const setSession = useAuthStore((s) => s.setSession);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ChangePasswordFormValues>({ resolver: zodResolver(changePasswordSchema) });

  const mutation = useMutation({
    mutationFn: changePassword,
    onSuccess: () => {
      if (accessToken) setSession(accessToken, false);
      toast.success("Mot de passe mis a jour.");
      navigate("/", { replace: true });
    },
    onError: () => {
      toast.error("Mot de passe actuel incorrect ou nouveau mot de passe trop faible.");
    },
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg text-textPrimary">
      <form
        onSubmit={handleSubmit((values) =>
          mutation.mutate({
            current_password: values.currentPassword,
            new_password: values.newPassword,
          })
        )}
        className="w-full max-w-sm space-y-4"
        noValidate
      >
        <h1 className="text-2xl font-semibold">Changement de mot de passe obligatoire</h1>
        <p className="text-sm text-textSecondary">
          Premiere connexion : choisissez un nouveau mot de passe avant de continuer.
        </p>

        <div>
          <label htmlFor="currentPassword" className="mb-1 block text-sm text-textSecondary">
            Mot de passe temporaire
          </label>
          <input
            id="currentPassword"
            type="password"
            autoComplete="current-password"
            className="w-full rounded border border-border bg-surface px-3 py-2 text-textPrimary"
            {...register("currentPassword")}
          />
          {errors.currentPassword && (
            <p className="mt-1 text-sm text-danger">{errors.currentPassword.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="newPassword" className="mb-1 block text-sm text-textSecondary">
            Nouveau mot de passe
          </label>
          <input
            id="newPassword"
            type="password"
            autoComplete="new-password"
            className="w-full rounded border border-border bg-surface px-3 py-2 text-textPrimary"
            {...register("newPassword")}
          />
          {errors.newPassword && (
            <p className="mt-1 text-sm text-danger">{errors.newPassword.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="confirmPassword" className="mb-1 block text-sm text-textSecondary">
            Confirmer le nouveau mot de passe
          </label>
          <input
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            className="w-full rounded border border-border bg-surface px-3 py-2 text-textPrimary"
            {...register("confirmPassword")}
          />
          {errors.confirmPassword && (
            <p className="mt-1 text-sm text-danger">{errors.confirmPassword.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full rounded bg-primary py-2 font-medium text-white disabled:opacity-60"
        >
          {mutation.isPending ? "Enregistrement..." : "Valider"}
        </button>
      </form>
    </div>
  );
}
