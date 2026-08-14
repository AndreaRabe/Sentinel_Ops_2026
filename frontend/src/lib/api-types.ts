/** Types partages avec l'API (conventions du cahier des charges section 8). */

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface PageParams {
  page?: number;
  page_size?: number;
}

export type TaskStatus =
  | "DRAFT"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "POSTPONED"
  | "CANCELLED"
  | "LATE";

export type TaskPriority = "LOW" | "NORMAL" | "HIGH" | "CRITICAL";
export type IncidentSeverity = "MINOR" | "MODERATE" | "MAJOR" | "CRITICAL";
export type IncidentStatus = "OPEN" | "IN_PROGRESS" | "RESOLVED" | "CLOSED";

/** Message d'erreur normalise renvoye par le backend, si present. */
export function apiErrorMessage(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { error?: { message?: string } } } })?.response
    ?.data?.error?.message;
  return detail ?? fallback;
}
