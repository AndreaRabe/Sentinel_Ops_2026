/**
 * Primitives d'affichage du theme "Command Center" : hairlines et grandes
 * valeurs tabulaires, pas de cartes empilees (cahier des charges section 11).
 */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/cn";

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-border pb-4">
      <div>
        <h1 className="text-xl font-semibold text-textPrimary">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-textSecondary">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="mb-3 border-b border-border pb-2 font-mono text-[11px] uppercase tracking-widest text-textTertiary">
      {children}
    </h2>
  );
}

export function EmptyState({ title, message }: { title: string; message?: string }) {
  return (
    <div className="border border-dashed border-border px-6 py-12 text-center">
      <p className="text-sm font-medium text-textPrimary">{title}</p>
      {message && <p className="mt-1 text-sm text-textSecondary">{message}</p>}
    </div>
  );
}

export function ErrorState({ message = "Impossible de charger ces donnees." }: { message?: string }) {
  return (
    <div role="alert" className="border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">
      {message}
    </div>
  );
}

/**
 * Compteur anime : la valeur monte jusqu'au chiffre cible.
 * Sous `prefers-reduced-motion`, la valeur finale est affichee directement.
 */
export function CountUp({ value, className }: { value: number; className?: string }) {
  const [displayed, setDisplayed] = useState(value);
  const frameRef = useRef<number>();

  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setDisplayed(value);
      return;
    }

    const from = displayed;
    const start = performance.now();
    const duration = 500;

    const step = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      setDisplayed(Math.round(from + (value - from) * progress));
      if (progress < 1) frameRef.current = requestAnimationFrame(step);
    };
    frameRef.current = requestAnimationFrame(step);

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
    // `displayed` est volontairement hors dependances : le relire relancerait
    // l'animation a chaque image.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return <span className={cn("font-mono tabular-nums", className)}>{displayed}</span>;
}

export function KpiTile({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: number;
  tone?: "default" | "warning" | "danger";
}) {
  const toneClass =
    tone === "danger" ? "text-danger" : tone === "warning" ? "text-warning" : "text-textPrimary";

  return (
    <div className="border-l border-border px-5 py-1 first:border-l-0 first:pl-0">
      <div className="font-mono text-[11px] uppercase tracking-widest text-textTertiary">
        {label}
      </div>
      <CountUp value={value} className={cn("mt-1 block text-3xl font-semibold", toneClass)} />
    </div>
  );
}

export function DataTable({
  headers,
  children,
  caption,
}: {
  headers: string[];
  children: ReactNode;
  caption?: string;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr>
            {headers.map((header) => (
              <th
                key={header}
                scope="col"
                className="border-b border-border px-3 py-2 text-left font-mono text-[11px]
                           uppercase tracking-widest text-textTertiary"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

export function Pagination({
  page,
  pages,
  total,
  onChange,
}: {
  page: number;
  pages: number;
  total: number;
  onChange: (page: number) => void;
}) {
  if (pages <= 1) {
    return <p className="mt-3 text-xs text-textTertiary">{total} resultat(s)</p>;
  }

  return (
    <nav className="mt-4 flex items-center justify-between text-sm" aria-label="Pagination">
      <span className="font-mono text-xs text-textTertiary">
        {total} resultat(s) — page {page}/{pages}
      </span>
      <div className="flex gap-2">
        <button
          type="button"
          className="rounded border border-border px-3 py-1 disabled:opacity-40"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          Precedent
        </button>
        <button
          type="button"
          className="rounded border border-border px-3 py-1 disabled:opacity-40"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
        >
          Suivant
        </button>
      </div>
    </nav>
  );
}
