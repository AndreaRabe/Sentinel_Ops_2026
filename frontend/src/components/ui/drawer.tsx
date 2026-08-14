/**
 * Panneau lateral (creation/edition de tache, detail d'incident) et boite de
 * confirmation. Le drawer est le pattern valide en maquette pour la creation
 * de tache (cahier des charges section 11).
 *
 * Accessibilite : fermeture au clavier (Echap), focus deplace dans le panneau
 * a l'ouverture, defilement de la page bloque tant qu'il est ouvert.
 */
import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Button } from "./button";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  footer?: ReactNode;
  children: ReactNode;
  width?: "md" | "lg";
}

export function Drawer({
  open,
  onClose,
  title,
  description,
  footer,
  children,
  width = "md",
}: DrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panelRef.current?.focus();

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <button
        type="button"
        aria-label="Fermer le panneau"
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={cn(
          "relative flex h-full w-full flex-col border-l border-border bg-bg shadow-xl outline-none",
          width === "lg" ? "max-w-2xl" : "max-w-lg"
        )}
      >
        <header className="border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-textPrimary">{title}</h2>
          {description && <p className="mt-1 text-sm text-textSecondary">{description}</p>}
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>

        {footer && (
          <footer className="flex justify-end gap-2 border-t border-border px-6 py-4">
            {footer}
          </footer>
        )}
      </div>
    </div>
  );
}

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  destructive?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirmer",
  destructive = false,
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Annuler"
        className="absolute inset-0 bg-black/50"
        onClick={onCancel}
      />
      <div
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        className="relative w-full max-w-md rounded border border-border bg-surface p-6"
      >
        <h2 className="text-base font-semibold text-textPrimary">{title}</h2>
        <p className="mt-2 text-sm text-textSecondary">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            Annuler
          </Button>
          <Button
            variant={destructive ? "danger" : "primary"}
            loading={loading}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
