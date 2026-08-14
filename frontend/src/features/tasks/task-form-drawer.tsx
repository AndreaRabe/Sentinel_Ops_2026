/**
 * Drawer de creation / modification d'une tache (ecran valide en maquette).
 */
import { useEffect } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { PRIORITY_LABELS } from "@/components/ui/badge";
import { listSites, listUsers } from "@/features/admin/api";
import { createTask, setTaskAssignees, updateTask, type Task } from "@/features/tasks/api";
import { parseChecklist, taskFormSchema, type TaskFormValues } from "@/features/tasks/schemas";
import { apiErrorMessage } from "@/lib/api-types";
import { fromDateTimeLocal, toDateTimeLocal } from "@/lib/format";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Absent = creation. */
  task?: Task | null;
}

export function TaskFormDrawer({ open, onClose, task }: Props) {
  const queryClient = useQueryClient();
  const isEdit = Boolean(task);

  const sites = useQuery({ queryKey: ["sites"], queryFn: () => listSites(), enabled: open });
  const users = useQuery({
    queryKey: ["users", "assignable"],
    queryFn: () => listUsers({ page_size: 200, include_inactive: false }),
    enabled: open,
  });

  const {
    register,
    handleSubmit,
    reset,
    control,
    watch,
    formState: { errors },
  } = useForm<TaskFormValues>({
    resolver: zodResolver(taskFormSchema),
    defaultValues: {
      title: "",
      description: "",
      site_id: "",
      priority: "NORMAL",
      due_at: "",
      estimated_minutes: "",
      assignee_ids: [],
      checklist_text: "",
    },
  });

  useEffect(() => {
    if (!open) return;
    reset({
      title: task?.title ?? "",
      description: task?.description ?? "",
      site_id: task?.site_id ?? "",
      priority: task?.priority ?? "NORMAL",
      due_at: toDateTimeLocal(task?.due_at),
      estimated_minutes: task?.estimated_minutes ? String(task.estimated_minutes) : "",
      assignee_ids: task?.assignee_ids ?? [],
      checklist_text: (task?.checklist ?? []).map((item) => item.label).join("\n"),
    });
  }, [open, task, reset]);

  const selectedSite = watch("site_id");

  // Un agent ne peut porter une tache que sur un site qu'il couvre : on
  // n'affiche donc que les utilisateurs rattaches au site choisi (les roles a
  // portee globale n'ont pas de site et restent toujours proposes).
  const assignableUsers = (users.data?.items ?? []).filter(
    (user) =>
      user.sites.length === 0 || user.sites.some((site) => site.id === selectedSite)
  );

  const mutation = useMutation({
    mutationFn: async (values: TaskFormValues) => {
      const payload = {
        title: values.title,
        description: values.description || null,
        site_id: values.site_id,
        priority: values.priority,
        due_at: values.due_at ? fromDateTimeLocal(values.due_at) : null,
        estimated_minutes: values.estimated_minutes ? Number(values.estimated_minutes) : null,
        assignee_ids: values.assignee_ids,
        checklist_labels: parseChecklist(values.checklist_text),
      };
      if (!task) return createTask(payload);

      // PATCH /tasks/{id} ne porte PAS les assignations : cote backend elles
      // passent par une route dediee, gardee par la permission task:assign
      // (modifier le contenu d'une tache et changer son porteur sont deux
      // actes distincts). On enchaine donc les deux appels a l'edition.
      const updated = await updateTask(task.id, payload);
      const unchanged =
        values.assignee_ids.length === task.assignee_ids.length &&
        values.assignee_ids.every((id) => task.assignee_ids.includes(id));
      return unchanged ? updated : setTaskAssignees(task.id, values.assignee_ids);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(isEdit ? "Tache mise a jour." : "Tache creee.");
      onClose();
    },
    onError: (error) => {
      toast.error(apiErrorMessage(error, "Enregistrement impossible."));
    },
  });

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={isEdit ? "Modifier la tache" : "Nouvelle tache"}
      description={
        isEdit
          ? undefined
          : "Une tache creee avec au moins un agent assigne part directement en « Assignee »."
      }
      width="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button
            loading={mutation.isPending}
            onClick={handleSubmit((values) => mutation.mutate(values))}
          >
            {isEdit ? "Enregistrer" : "Creer la tache"}
          </Button>
        </>
      }
    >
      <form
        className="space-y-4"
        onSubmit={handleSubmit((values) => mutation.mutate(values))}
        noValidate
      >
        <Field label="Titre" htmlFor="title" error={errors.title?.message} required>
          <Input id="title" {...register("title")} />
        </Field>

        <Field label="Description" htmlFor="description">
          <Textarea id="description" {...register("description")} />
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Site" htmlFor="site_id" error={errors.site_id?.message} required>
            <Select id="site_id" {...register("site_id")} disabled={isEdit}>
              <option value="">— Selectionner —</option>
              {sites.data?.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Priorite" htmlFor="priority">
            <Select id="priority" {...register("priority")}>
              {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Echeance" htmlFor="due_at">
            <Input id="due_at" type="datetime-local" {...register("due_at")} />
          </Field>

          <Field
            label="Duree estimee (minutes)"
            htmlFor="estimated_minutes"
            error={errors.estimated_minutes?.message}
          >
            <Input id="estimated_minutes" type="number" min={0} {...register("estimated_minutes")} />
          </Field>
        </div>

        <Field
          label="Agents assignes"
          hint={
            selectedSite
              ? "Maintenez Ctrl/Cmd pour selectionner plusieurs agents."
              : "Choisissez d'abord un site."
          }
        >
          <Controller
            control={control}
            name="assignee_ids"
            render={({ field }) => (
              <Select
                multiple
                size={6}
                value={field.value}
                onChange={(event) =>
                  field.onChange(
                    Array.from(event.target.selectedOptions).map((option) => option.value)
                  )
                }
                disabled={!selectedSite}
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

        <Field label="Checklist" htmlFor="checklist_text" hint="Une ligne = un element.">
          <Textarea id="checklist_text" rows={5} {...register("checklist_text")} />
        </Field>
      </form>
    </Drawer>
  );
}
