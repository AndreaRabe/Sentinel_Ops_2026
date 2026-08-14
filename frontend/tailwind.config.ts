import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        surfaceElevated: "var(--surface-elevated)",
        surfaceHover: "var(--surface-hover)",
        border: "var(--border)",
        textPrimary: "var(--text-primary)",
        textSecondary: "var(--text-secondary)",
        textTertiary: "var(--text-tertiary)",
        primary: "var(--primary)",
        success: "var(--success)",
        warning: "var(--warning)",
        danger: "var(--danger)",
        info: "var(--info)",
      },
      fontFamily: {
        sans: ["Manrope", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      keyframes: {
        // Effet "scan" des chargements de liste/page.
        scan: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(400%)" },
        },
        // "Pulse dots" des actions inline.
        pulseDot: {
          "0%, 80%, 100%": { opacity: "0.25", transform: "scale(0.8)" },
          "40%": { opacity: "1", transform: "scale(1)" },
        },
        // Compteurs du dashboard : apparition des gros chiffres tabulaires.
        countUp: {
          "0%": { opacity: "0", transform: "translateY(0.25em)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        scan: "scan 1.4s ease-in-out infinite",
        pulseDot: "pulseDot 1.1s ease-in-out infinite",
        countUp: "countUp 400ms ease-out both",
      },
    },
  },
  plugins: [],
} satisfies Config;
