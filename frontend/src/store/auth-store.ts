/**
 * Etat UI global de session (Zustand) - distinct de l'etat serveur
 * gere par React Query (voir cahier des charges section 10).
 */
import { create } from "zustand";
import { decodeAccessToken } from "@/lib/jwt";

interface AuthState {
  accessToken: string | null;
  role: string | null;
  permissions: string[];
  mustChangePassword: boolean;
  isInitialized: boolean;
  setSession: (token: string, mustChangePassword: boolean) => void;
  setInitialized: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  role: null,
  permissions: [],
  mustChangePassword: false,
  isInitialized: false,
  setSession: (token, mustChangePassword) => {
    const decoded = decodeAccessToken(token);
    set({
      accessToken: token,
      role: decoded.role,
      permissions: decoded.perms,
      mustChangePassword,
    });
  },
  setInitialized: () => set({ isInitialized: true }),
  logout: () =>
    set({ accessToken: null, role: null, permissions: [], mustChangePassword: false }),
}));
