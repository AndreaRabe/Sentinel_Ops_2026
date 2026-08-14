/**
 * Animations de chargement contextuelles (cahier des charges section 11) :
 * - ScanLoader   : chargement d'une liste ou d'une page (effet "scan")
 * - PulseDots    : action inline (bouton en cours de soumission)
 * - ProgressRing : operation longue (export PDF/Excel)
 *
 * Les trois respectent `prefers-reduced-motion` : l'animation est neutralisee
 * et remplacee par un etat statique lisible.
 */
import { cn } from "@/lib/cn";

export function ScanLoader({ label = "Chargement", rows = 5 }: { label?: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3 py-2">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="relative h-10 overflow-hidden rounded border border-border bg-surface"
        >
          <div
            className="absolute inset-y-0 -left-1/3 w-1/3 animate-scan bg-gradient-to-r
                       from-transparent via-surfaceHover to-transparent
                       motion-reduce:hidden"
          />
        </div>
      ))}
    </div>
  );
}

export function PulseDots({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1", className)} aria-hidden="true">
      {[0, 1, 2].map((index) => (
        <span
          key={index}
          className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-current
                     motion-reduce:animate-none"
          style={{ animationDelay: `${index * 120}ms` }}
        />
      ))}
    </span>
  );
}

export function ProgressRing({ label = "Traitement en cours" }: { label?: string }) {
  return (
    <span role="status" aria-live="polite" className="inline-flex items-center gap-2">
      <svg viewBox="0 0 24 24" className="h-4 w-4 animate-spin motion-reduce:animate-none">
        <circle
          cx="12"
          cy="12"
          r="9"
          fill="none"
          stroke="currentColor"
          strokeOpacity="0.2"
          strokeWidth="3"
        />
        <path
          d="M21 12a9 9 0 0 0-9-9"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
      <span className="text-sm text-textSecondary">{label}</span>
    </span>
  );
}
