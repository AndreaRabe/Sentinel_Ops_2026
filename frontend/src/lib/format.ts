/**
 * Formatage partage. Les donnees (dates, IDs, KPI) s'affichent en IBM Plex Mono
 * avec des chiffres tabulaires : c'est la regle typographique du theme
 * "Command Center" (cahier des charges section 11).
 */
import { format, formatDistanceToNowStrict, isValid, parseISO } from "date-fns";
import { fr } from "date-fns/locale";

export function toDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const date = typeof value === "string" ? parseISO(value) : value;
  return isValid(date) ? date : null;
}

export function formatDateTime(value: string | Date | null | undefined): string {
  const date = toDate(value);
  return date ? format(date, "dd/MM/yyyy HH:mm", { locale: fr }) : "—";
}

export function formatDate(value: string | Date | null | undefined): string {
  const date = toDate(value);
  return date ? format(date, "dd/MM/yyyy", { locale: fr }) : "—";
}

export function formatDayLabel(value: string | Date): string {
  const date = toDate(value);
  return date ? format(date, "EEEE d MMMM", { locale: fr }) : "—";
}

export function formatRelative(value: string | Date | null | undefined): string {
  const date = toDate(value);
  if (!date) return "—";
  return formatDistanceToNowStrict(date, { addSuffix: true, locale: fr });
}

/** Valeur d'un champ <input type="datetime-local"> a partir d'une date ISO. */
export function toDateTimeLocal(value: string | Date | null | undefined): string {
  const date = toDate(value);
  return date ? format(date, "yyyy-MM-dd'T'HH:mm") : "";
}

/** Inverse de toDateTimeLocal : renvoie une chaine ISO UTC, ou null si vide. */
export function fromDateTimeLocal(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return isValid(date) ? date.toISOString() : null;
}

export function initials(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
}

export function fullName(person: { first_name: string; last_name: string }): string {
  return `${person.first_name} ${person.last_name}`;
}
