import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { login } from "@/features/auth/api";
import { loginSchema, type LoginFormValues } from "@/features/auth/schemas";
import { useAuthStore } from "@/store/auth-store";

export function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((s) => s.setSession);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: (data) => {
      setSession(data.access_token, data.must_change_password);
      navigate("/", { replace: true });
    },
    onError: () => {
      toast.error("Identifiants invalides ou compte temporairement verrouille.");
    },
  });

  return (
    <div className="grid min-h-screen grid-cols-1 bg-bg text-textPrimary md:grid-cols-2">
      <div className="hidden items-center justify-center border-r border-border bg-surface md:flex">
        <span className="font-mono text-sm tracking-widest text-textSecondary">
          SENTINEL OPS / COMMAND CENTER
        </span>
      </div>
      <div className="flex items-center justify-center p-8">
        <form
          onSubmit={handleSubmit((values) => mutation.mutate(values))}
          className="w-full max-w-sm space-y-4"
          noValidate
        >
          <h1 className="text-2xl font-semibold">Connexion</h1>

          <div>
            <label htmlFor="email" className="mb-1 block text-sm text-textSecondary">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              className="w-full rounded border border-border bg-surface px-3 py-2 text-textPrimary"
              {...register("email")}
            />
            {errors.email && <p className="mt-1 text-sm text-danger">{errors.email.message}</p>}
          </div>

          <div>
            <label htmlFor="password" className="mb-1 block text-sm text-textSecondary">
              Mot de passe
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                className="w-full rounded border border-border bg-surface px-3 py-2 pr-16 text-textPrimary"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-sm text-textSecondary"
              >
                {showPassword ? "Masquer" : "Afficher"}
              </button>
            </div>
            {errors.password && (
              <p className="mt-1 text-sm text-danger">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className="w-full rounded bg-primary py-2 font-medium text-white disabled:opacity-60"
          >
            {mutation.isPending ? "Connexion..." : "Se connecter"}
          </button>
        </form>
      </div>
    </div>
  );
}
