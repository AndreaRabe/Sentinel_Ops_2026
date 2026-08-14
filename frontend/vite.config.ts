/// <reference types="vitest" />
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: true,
    port: 5173,
  },
  test: {
    // Vitest ne prend QUE les tests unitaires de src/. Les specs de e2e/ sont
    // du ressort de Playwright (elles exigent une pile complete en marche) et
    // echoueraient ici faute de navigateur.
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
