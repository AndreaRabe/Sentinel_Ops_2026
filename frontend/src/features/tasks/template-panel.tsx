/**
 * Modeles de taches et recurrences.
 *
 * La RRULE (RFC 5545) est incomprehensible pour un utilisateur non technique :
 * l'interface propose donc des cadences courantes, avec une saisie libre en
 * repli pour les cas particuliers. La regle reste validee par le backend a
 * l'enregistrement.
 */
import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { Can } from "@/components/can";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Drawer } from "@/components/ui/drawer";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { DataTable, EmptyState, ErrorState } from "@/components/ui/data-display";
import { ScanLoader } from "@/components/ui/loaders";
import { PRIORITY_LABELS, PriorityBadge } from "@/components/ui/badge";
import { listSites, listUsers } from "@/features/admin/api";
import {
  createTaskTemplate,
  deleteTaskTemplate,
  instantiateTemplate,
  listTaskTemplates,
  type TaskTemplate,
} from "@/features/tasks/api";
import { parseChecklist, templateFormSchema, type TemplateFormValues } from "./schemas";
import { apiErrorMessage } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";

/** Cadences proposees. La valeur vide = modele manuel, sans generation. */
const RRULE_PRESETS: { value: string; label: string }[] = [
  { value: "", label: "Aucune — modele instancie manuellement" },
  { value: "FREQ=DAILY", label: "Tous les jours" },
  { value: "FREQ=WEEKLY;BYDAY=MO", label: "Toutes les semaines, le lundi" },
  { value: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", label: "Du lundi au vendredi" },
  { value: "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO", label: "Une semaine sur deux, le lundi" },
  { value: "FREQ=MONTHLY;BYMONTHDAY=1", label: "Le 1er de chaque mois" },
];

function describeRrule(rrule: string | null): string {
  if (!rrule) return "Manuel";
  return RRULE_PRESETS.find((preset) => preset.value === rrule)?.label ?? rrule;
}

export function TemplatePanel() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TaskTemplate | null>(null);
  const [customRrule, setCustomRrule] = useState(false);

  const templates = useQuery({ queryKey: ["task-templates"], queryFn: listTaskTemplates });
  const sites = useQuery({ queryKey: ["sites"], queryFn: () => listSites() });
  const users = useQuery({
    queryKey: ["users", "assignable"],
    queryFn: () => listUsers({ page_size: 200, include_inactive: false }),
    enabled: createOpen,
  });

  const {
    register,
    handleSubmit,
    reset,
    control,
    watch,
    setValue,
    formState: { errors },
  } = useForm<TemplateFormValues>({
    resolver: zodResolver(templateFormSchema),
    defaultValues: {
      name: "",
      description: "",
      site_id: "",
      default_priority: "NORMAL",
      rrule: "",
      checklist_text: "",
      default_assignee_ids: [],
    },
  });

  const selectedSite = watch("site_id");
  const assignableUsers = (users.data?.items ?? []).filter(
    (user) => user.sites.length === 0 || user.sites.some((site) => site.id === selectedSite)
  );

  const createMutation = useMutation({
    mutationFn: (values: TemplateFormValues) =>
      createTaskTemplate({
        name: values.name,
        description: values.description || null,
        site_id: values.site_id,
        default_priority: values.default_priority,
        rrule: values.rrule || null,
        checklist_labels: parseChecklist(values.checklist_text),
        default_assignee_ids: values.default_assignee_ids,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-templates"] });
      toast.success("Modele enregistre.");
      reset();
      setCustomRrule(false);
      setCreateOpen(false);
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Enregistrement impossible.")),
  });

  const deleteMutation = useMutation({
    mutationFn: (templateId: string) => deleteTaskTemplate(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task-templates"] });
      setDeleteTarget(null);
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Suppression impossible.")),
  });

  const instantiateMutation = useMutation({
    mutationFn: (templateId: string) => instantiateTemplate(templateId, null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      toast.success("Tache creee a partir du modele.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Creation impossible.")),
  });

  const siteName = (siteId: string) =>
    sites.data?.find((site) => site.id === siteId)?.name ?? "—";

  return (
    <>
      <div className="mb-4 flex justify-end">
        <Can permission="task:template_manage">
          <Button onClick={() => setCreateOpen(true)}>Nouveau modele</Button>
        </Can>
      </div>

      {templates.isLoading && <ScanLoader label="Chargement des modeles" rows={3} />}
      {templates.isError && <ErrorState />}
      {templates.data?.length === 0 && (
        <EmptyState
          title="Aucun modele de tache."
          message="Un modele sert a recreer une tache identique, ponctuellement ou automatiquement."
        />
      )}

      {templates.data && templates.data.length > 0 && (
        <DataTable
          caption="Modeles de taches"
          headers={["Nom", "Site", "Priorite", "Recurrence", "Derniere generation", ""]}
        >
          {templates.data.map((template) => (
            <tr key={template.id} className="border-b border-border">
              <td className="px-3 py-2 text-textPrimary">{template.name}</td>
              <td className="px-3 py-2 text-textSecondary">{siteName(template.site_id)}</td>
              <td className="px-3 py-2">
                <PriorityBadge priority={template.default_priority} />
              </td>
              <td className="px-3 py-2 text-textSecondary">{describeRrule(template.rrule)}</td>
              <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                {template.rrule ? formatDateTime(template.last_generated_at) : "—"}
              </td>
              <td className="px-3 py-2 text-right">
                <div className="flex justify-end gap-3">
                  <Can permission="task:create">
                    <button
                      type="button"
                      className="font-mono text-[11px] uppercase text-textTertiary hover:text-textPrimary"
                      onClick={() => instantiateMutation.mutate(template.id)}
                    >
                      Creer une tache
                    </button>
                  </Can>
                  <Can permission="task:template_delete">
                    <button
                      type="button"
                      className="font-mono text-[11px] uppercase text-textTertiary hover:text-danger"
                      onClick={() => setDeleteTarget(template)}
                    >
                      Supprimer
                    </button>
                  </Can>
                </div>
              </td>
            </tr>
          ))}
        </DataTable>
      )}

      <Drawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Nouveau modele de tache"
        description="Avec une recurrence, les taches sont generees automatiquement chaque nuit sur un horizon de 14 jours."
        width="lg"
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>
              Annuler
            </Button>
            <Button
              loading={createMutation.isPending}
              onClick={handleSubmit((values) => createMutation.mutate(values))}
            >
              Enregistrer
            </Button>
          </>
        }
      >
        <form className="space-y-4" noValidate>
          <Field label="Nom" htmlFor="tpl-name" error={errors.name?.message} required>
            <Input id="tpl-name" {...register("name")} />
          </Field>

          <Field label="Description" htmlFor="tpl-description">
            <Textarea id="tpl-description" {...register("description")} />
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Site" htmlFor="tpl-site" error={errors.site_id?.message} required>
              <Select id="tpl-site" {...register("site_id")}>
                <option value="">— Selectionner —</option>
                {sites.data?.map((site) => (
                  <option key={site.id} value={site.id}>
                    {site.name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Priorite par defaut" htmlFor="tpl-priority">
              <Select id="tpl-priority" {...register("default_priority")}>
                {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field
            label="Recurrence"
            htmlFor="tpl-rrule"
            error={errors.rrule?.message}
            hint={customRrule ? "Regle RRULE (RFC 5545), ex : FREQ=WEEKLY;BYDAY=TU,TH" : undefined}
          >
            {customRrule ? (
              <Input id="tpl-rrule" placeholder="FREQ=..." {...register("rrule")} />
            ) : (
              <Select
                id="tpl-rrule"
                value={watch("rrule") ?? ""}
                onChange={(event) => setValue("rrule", event.target.value)}
              >
                {RRULE_PRESETS.map((preset) => (
                  <option key={preset.value} value={preset.value}>
                    {preset.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>

          <button
            type="button"
            className="font-mono text-[11px] uppercase tracking-widest text-info"
            onClick={() => {
              setCustomRrule((value) => !value);
              setValue("rrule", "");
            }}
          >
            {customRrule ? "← Revenir aux cadences proposees" : "Saisir une regle personnalisee →"}
          </button>

          <Field label="Agents assignes par defaut" hint="Facultatif.">
            <Controller
              control={control}
              name="default_assignee_ids"
              render={({ field }) => (
                <Select
                  multiple
                  size={5}
                  value={field.value}
                  disabled={!selectedSite}
                  onChange={(event) =>
                    field.onChange(
                      Array.from(event.target.selectedOptions).map((option) => option.value)
                    )
                  }
                >
                  {assignableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.first_name} {user.last_name}
                    </option>
                  ))}
                </Select>
              )}
            />
          </Field>

          <Field label="Checklist" htmlFor="tpl-checklist" hint="Une ligne = un element.">
            <Textarea id="tpl-checklist" rows={4} {...register("checklist_text")} />
          </Field>
        </form>
      </Drawer>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Supprimer le modele"
        message={
          deleteTarget
            ? `« ${deleteTarget.name} » sera archive et ne generera plus de taches. Les taches deja creees sont conservees.`
            : ""
        }
        confirmLabel="Supprimer"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />
    </>
  );
}

export { describeRrule, RRULE_PRESETS };
