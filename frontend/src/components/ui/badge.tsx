/**
 * Pastilles de statut / gravite / priorite.
 *
 * Regle d'accessibilite du theme (cahier des charges section 11) : une
 * information n'est JAMAIS portee par la seule couleur. Chaque badge affiche
 * donc toujours un libelle texte, la couleur ne fait que renforcer.
 */
import { cn } from "@/lib/cn";

export type Tone = "neutral" | "info" | "success" | "warning" | "danger" | "primary";

const TONES: Record<Tone, string> = {
  neutral: "border-border bg-surfaceElevated text-textSecondary",
  info: "border-info/40 bg-info/10 text-info",
  success: "border-success/40 bg-success/10 text-success",
  warning: "border-warning/40 bg-warning/10 text-warning",
  danger: "border-danger/40 bg-danger/10 text-danger",
  primary: "border-primary/40 bg-primary/10 text-primary",
};

export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: Tone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded border px-2 py-0.5",
        "font-mono text-[11px] uppercase tracking-wide",
        TONES[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

// ---------------------------------------------------------------- taches

export const TASK_STATUS_LABELS: Record<string, string> = {
  DRAFT: "Brouillon",
  ASSIGNED: "Assignee",
  IN_PROGRESS: "En cours",
  COMPLETED: "Terminee",
  POSTPONED: "Reportee",
  CANCELLED: "Annulee",
  LATE: "En retard",
};

const TASK_STATUS_TONES: Record<string, Tone> = {
  DRAFT: "neutral",
  ASSIGNED: "info",
  IN_PROGRESS: "primary",
  COMPLETED: "success",
  POSTPONED: "warning",
  CANCELLED: "neutral",
  LATE: "danger",
};

export function TaskStatusBadge({ status }: { status: string }) {
  return <Badge tone={TASK_STATUS_TONES[status] ?? "neutral"}>{TASK_STATUS_LABELS[status] ?? status}</Badge>;
}

export const PRIORITY_LABELS: Record<string, string> = {
  LOW: "Basse",
  NORMAL: "Normale",
  HIGH: "Haute",
  CRITICAL: "Critique",
};

const PRIORITY_TONES: Record<string, Tone> = {
  LOW: "neutral",
  NORMAL: "info",
  HIGH: "warning",
  CRITICAL: "danger",
};

export function PriorityBadge({ priority }: { priority: string }) {
  return <Badge tone={PRIORITY_TONES[priority] ?? "neutral"}>{PRIORITY_LABELS[priority] ?? priority}</Badge>;
}

// ------------------------------------------------------------- incidents

export const SEVERITY_LABELS: Record<string, string> = {
  MINOR: "Mineur",
  MODERATE: "Modere",
  MAJOR: "Majeur",
  CRITICAL: "Critique",
};

const SEVERITY_TONES: Record<string, Tone> = {
  MINOR: "neutral",
  MODERATE: "info",
  MAJOR: "warning",
  CRITICAL: "danger",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return <Badge tone={SEVERITY_TONES[severity] ?? "neutral"}>{SEVERITY_LABELS[severity] ?? severity}</Badge>;
}

export const INCIDENT_STATUS_LABELS: Record<string, string> = {
  OPEN: "Ouvert",
  IN_PROGRESS: "En traitement",
  RESOLVED: "Resolu",
  CLOSED: "Cloture",
};

const INCIDENT_STATUS_TONES: Record<string, Tone> = {
  OPEN: "danger",
  IN_PROGRESS: "warning",
  RESOLVED: "success",
  CLOSED: "neutral",
};

export function IncidentStatusBadge({ status }: { status: string }) {
  return (
    <Badge tone={INCIDENT_STATUS_TONES[status] ?? "neutral"}>
      {INCIDENT_STATUS_LABELS[status] ?? status}
    </Badge>
  );
}

export const ROLE_LABELS: Record<string, string> = {
  super_admin: "Super Admin",
  responsable: "Responsable",
  chef_equipe: "Chef d'equipe",
  agent: "Agent",
};
