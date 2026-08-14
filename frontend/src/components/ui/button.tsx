import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { PulseDots } from "./loaders";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  /** Affiche les "pulse dots" et neutralise le clic (animation inline du theme). */
  loading?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary: "bg-primary text-white hover:opacity-90",
  secondary: "border border-border bg-surface text-textPrimary hover:bg-surfaceHover",
  ghost: "text-textSecondary hover:bg-surfaceHover hover:text-textPrimary",
  danger: "border border-danger text-danger hover:bg-danger hover:text-white",
};

const SIZES: Record<Size, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading = false, disabled, className, children, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded font-medium transition-colors",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2",
        "focus-visible:outline-info disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className
      )}
      {...props}
    >
      {loading ? <PulseDots /> : children}
    </button>
  );
});
