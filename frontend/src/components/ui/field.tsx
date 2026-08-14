/**
 * Champs de formulaire. Volontairement des composants non controles
 * compatibles avec le `register()` de react-hook-form (cahier des charges
 * section 10) : pas de wrapper Controller inutile.
 */
import {
  forwardRef,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { cn } from "@/lib/cn";

const CONTROL_CLASSES = cn(
  "w-full rounded border border-border bg-surface px-3 py-2 text-sm text-textPrimary",
  "placeholder:text-textTertiary focus:border-info focus:outline-none",
  "disabled:cursor-not-allowed disabled:opacity-60"
);

interface FieldProps {
  label: string;
  htmlFor?: string;
  error?: string;
  hint?: string;
  required?: boolean;
  children: ReactNode;
}

export function Field({ label, htmlFor, error, hint, required, children }: FieldProps) {
  return (
    <div className="space-y-1">
      <label htmlFor={htmlFor} className="block text-sm text-textSecondary">
        {label}
        {required && <span className="ml-1 text-danger">*</span>}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-textTertiary">{hint}</p>}
      {/* L'erreur est portee par le texte, jamais par la seule couleur. */}
      {error && (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(CONTROL_CLASSES, className)} {...props} />;
  }
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, rows = 4, ...props }, ref) {
    return (
      <textarea ref={ref} rows={rows} className={cn(CONTROL_CLASSES, className)} {...props} />
    );
  }
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <select ref={ref} className={cn(CONTROL_CLASSES, className)} {...props}>
        {children}
      </select>
    );
  }
);
