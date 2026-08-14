import { z } from "zod";

export const taskFormSchema = z.object({
  title: z.string().min(3, "Le titre doit contenir au moins 3 caracteres."),
  description: z.string().optional(),
  site_id: z.string().uuid("Selectionnez un site."),
  priority: z.enum(["LOW", "NORMAL", "HIGH", "CRITICAL"]),
  due_at: z.string().optional(),
  estimated_minutes: z
    .string()
    .optional()
    .refine((value) => !value || Number(value) >= 0, "Duree invalide."),
  assignee_ids: z.array(z.string().uuid()),
  // Saisie libre : une ligne = un element de checklist.
  checklist_text: z.string().optional(),
});

export type TaskFormValues = z.infer<typeof taskFormSchema>;

export function parseChecklist(text: string | undefined): string[] {
  return (text ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export const templateFormSchema = z.object({
  name: z.string().min(3, "Le nom doit contenir au moins 3 caracteres."),
  description: z.string().optional(),
  site_id: z.string().uuid("Selectionnez un site."),
  default_priority: z.enum(["LOW", "NORMAL", "HIGH", "CRITICAL"]),
  rrule: z.string().optional(),
  checklist_text: z.string().optional(),
  default_assignee_ids: z.array(z.string().uuid()),
});

export type TemplateFormValues = z.infer<typeof templateFormSchema>;
