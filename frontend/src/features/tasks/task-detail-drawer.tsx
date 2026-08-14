/**
 * Detail d'une tache : transitions de statut, checklist, commentaires,
 * pieces jointes et historique.
 *
 * Les transitions proposees sont derivees de la machine a etats du backend.
 * Cette liste est un confort d'interface : le serveur reste seul juge et
 * refusera toute transition illegale (core/task_state.py).
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Drawer } from "@/components/ui/drawer";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import { SectionTitle } from "@/components/ui/data-display";
import { PriorityBadge, TASK_STATUS_LABELS, TaskStatusBadge } from "@/components/ui/badge";
import { Can } from "@/components/can";
import {
  addTaskComment,
  addTaskDependency,
  changeTaskStatus,
  deleteTask,
  deleteTaskAttachment,
  listTaskAttachments,
  listTaskComments,
  listTaskDependencies,
  listTaskHistory,
  listTasks,
  removeTaskDependency,
  taskAttachmentUrl,
  toggleChecklistItem,
  uploadTaskAttachment,
  type Task,
} from "@/features/tasks/api";
import { apiErrorMessage, type TaskStatus } from "@/lib/api-types";
import { formatDateTime, fromDateTimeLocal } from "@/lib/format";

/** Miroir de ALLOWED_TRANSITIONS (backend), hors transitions systeme (LATE). */
const NEXT_STATUSES: Record<TaskStatus, TaskStatus[]> = {
  DRAFT: ["CANCELLED"],
  ASSIGNED: ["IN_PROGRESS", "POSTPONED", "CANCELLED"],
  IN_PROGRESS: ["COMPLETED", "POSTPONED", "CANCELLED"],
  POSTPONED: ["ASSIGNED", "IN_PROGRESS", "CANCELLED"],
  LATE: ["IN_PROGRESS", "COMPLETED", "POSTPONED", "CANCELLED"],
  COMPLETED: [],
  CANCELLED: [],
};

export function TaskDetailDrawer({
  task,
  open,
  onClose,
  onEdit,
}: {
  task: Task | null;
  open: boolean;
  onClose: () => void;
  onEdit: () => void;
}) {
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [postponedUntil, setPostponedUntil] = useState("");
  const [newDependency, setNewDependency] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const taskId = task?.id ?? "";
  const enabled = open && Boolean(task);

  const comments = useQuery({
    queryKey: ["task", taskId, "comments"],
    queryFn: () => listTaskComments(taskId),
    enabled,
  });
  const history = useQuery({
    queryKey: ["task", taskId, "history"],
    queryFn: () => listTaskHistory(taskId),
    enabled,
  });
  const attachments = useQuery({
    queryKey: ["task", taskId, "attachments"],
    queryFn: () => listTaskAttachments(taskId),
    enabled,
  });

  const invalidateTask = () => {
    queryClient.invalidateQueries({ queryKey: ["tasks"] });
    queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const statusMutation = useMutation({
    mutationFn: (status: TaskStatus) =>
      changeTaskStatus(taskId, {
        status,
        postponed_until:
          status === "POSTPONED" ? fromDateTimeLocal(postponedUntil) : undefined,
      }),
    onSuccess: () => {
      invalidateTask();
      toast.success("Statut mis a jour.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Transition refusee.")),
  });

  const checklistMutation = useMutation({
    mutationFn: ({ itemId, isDone }: { itemId: string; isDone: boolean }) =>
      toggleChecklistItem(taskId, itemId, isDone),
    onSuccess: invalidateTask,
    onError: (error) => toast.error(apiErrorMessage(error, "Mise a jour impossible.")),
  });

  const commentMutation = useMutation({
    mutationFn: () => addTaskComment(taskId, comment),
    onSuccess: () => {
      setComment("");
      comments.refetch();
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Commentaire refuse.")),
  });

  const dependencies = useQuery({
    queryKey: ["task", taskId, "dependencies"],
    queryFn: () => listTaskDependencies(taskId),
    enabled,
  });

  // Candidats a la dependance : les autres taches du meme site. Le backend
  // refusera de toute facon un cycle ou une tache hors perimetre.
  const candidates = useQuery({
    queryKey: ["tasks", "dependency-candidates", task?.site_id],
    queryFn: () => listTasks({ site_id: task?.site_id, page_size: 200 }),
    enabled: enabled && Boolean(task?.site_id),
  });

  const addDependencyMutation = useMutation({
    mutationFn: (dependsOnId: string) => addTaskDependency(taskId, dependsOnId),
    onSuccess: () => {
      setNewDependency("");
      dependencies.refetch();
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Dependance refusee.")),
  });

  const removeDependencyMutation = useMutation({
    mutationFn: (dependsOnId: string) => removeTaskDependency(taskId, dependsOnId),
    onSuccess: () => dependencies.refetch(),
    onError: (error) => toast.error(apiErrorMessage(error, "Suppression impossible.")),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteTask(taskId),
    onSuccess: () => {
      invalidateTask();
      setConfirmDelete(false);
      onClose();
      toast.success("Tache supprimee.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Suppression refusee.")),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadTaskAttachment(taskId, file),
    onSuccess: () => {
      attachments.refetch();
      toast.success("Piece jointe ajoutee.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Envoi refuse.")),
  });

  const deleteAttachmentMutation = useMutation({
    mutationFn: (attachmentId: string) => deleteTaskAttachment(taskId, attachmentId),
    onSuccess: () => attachments.refetch(),
    onError: (error) => toast.error(apiErrorMessage(error, "Suppression impossible.")),
  });

  if (!task) return null;

  const nextStatuses = NEXT_STATUSES[task.status] ?? [];

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={task.title}
      width="lg"
      footer={
        <>
          <Can permission="task:delete">
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>
              Supprimer
            </Button>
          </Can>
          <Button variant="secondary" onClick={onClose}>
            Fermer
          </Button>
          <Can permission="task:update">
            <Button variant="secondary" onClick={onEdit}>
              Modifier
            </Button>
          </Can>
        </>
      }
    >
      <div className="space-y-8">
        <section className="flex flex-wrap items-center gap-2">
          <TaskStatusBadge status={task.status} />
          <PriorityBadge priority={task.priority} />
          {task.is_overdue && (
            <span className="font-mono text-[11px] uppercase tracking-wide text-danger">
              Echeance depassee
            </span>
          )}
        </section>

        {task.description && (
          <p className="whitespace-pre-wrap text-sm text-textSecondary">{task.description}</p>
        )}

        <section className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-textTertiary">Echeance</span>
          <span className="font-mono">{formatDateTime(task.due_at)}</span>
          <span className="text-textTertiary">Demarree</span>
          <span className="font-mono">{formatDateTime(task.started_at)}</span>
          <span className="text-textTertiary">Terminee</span>
          <span className="font-mono">{formatDateTime(task.completed_at)}</span>
          <span className="text-textTertiary">Agents assignes</span>
          <span className="font-mono">{task.assignee_ids.length}</span>
        </section>

        {nextStatuses.length > 0 && (
          <section>
            <SectionTitle>Faire evoluer</SectionTitle>
            <div className="flex flex-wrap gap-2">
              {nextStatuses.map((status) => (
                <Button
                  key={status}
                  size="sm"
                  variant={status === "CANCELLED" ? "danger" : "secondary"}
                  loading={statusMutation.isPending && statusMutation.variables === status}
                  onClick={() => statusMutation.mutate(status)}
                >
                  {TASK_STATUS_LABELS[status]}
                </Button>
              ))}
            </div>
            {nextStatuses.includes("POSTPONED") && (
              <div className="mt-3 max-w-xs">
                <Field label="Reporter au" htmlFor="postponed_until">
                  <Input
                    id="postponed_until"
                    type="datetime-local"
                    value={postponedUntil}
                    onChange={(event) => setPostponedUntil(event.target.value)}
                  />
                </Field>
              </div>
            )}
          </section>
        )}

        {task.checklist.length > 0 && (
          <section>
            <SectionTitle>Checklist</SectionTitle>
            <ul className="space-y-1">
              {task.checklist.map((item) => (
                <li key={item.id}>
                  <label className="flex items-start gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="mt-0.5"
                      checked={item.is_done}
                      onChange={(event) =>
                        checklistMutation.mutate({
                          itemId: item.id,
                          isDone: event.target.checked,
                        })
                      }
                    />
                    <span className={item.is_done ? "text-textTertiary line-through" : ""}>
                      {item.label}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section>
          <SectionTitle>Taches prealables</SectionTitle>
          <p className="mb-2 text-xs text-textTertiary">
            Cette tache ne pourra pas demarrer tant que celles-ci ne sont pas terminees ou
            annulees.
          </p>
          <ul className="mb-3 space-y-1 text-sm">
            {dependencies.data?.length === 0 && (
              <li className="text-textTertiary">Aucune dependance.</li>
            )}
            {dependencies.data?.map((dependencyId) => {
              const dependency = candidates.data?.items.find((item) => item.id === dependencyId);
              return (
                <li key={dependencyId} className="flex items-center justify-between gap-3">
                  <span className="truncate text-textPrimary">
                    {dependency ? dependency.title : dependencyId.slice(0, 8)}
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    {dependency && <TaskStatusBadge status={dependency.status} />}
                    <Can permission="task:update">
                      <button
                        type="button"
                        className="font-mono text-[11px] uppercase text-textTertiary hover:text-danger"
                        onClick={() => removeDependencyMutation.mutate(dependencyId)}
                      >
                        Retirer
                      </button>
                    </Can>
                  </span>
                </li>
              );
            })}
          </ul>
          <Can permission="task:update">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <Field label="Ajouter une tache prealable" htmlFor="new-dependency">
                  <Select
                    id="new-dependency"
                    value={newDependency}
                    onChange={(event) => setNewDependency(event.target.value)}
                  >
                    <option value="">— Selectionner —</option>
                    {candidates.data?.items
                      .filter(
                        (candidate) =>
                          candidate.id !== task.id &&
                          !dependencies.data?.includes(candidate.id)
                      )
                      .map((candidate) => (
                        <option key={candidate.id} value={candidate.id}>
                          {candidate.title}
                        </option>
                      ))}
                  </Select>
                </Field>
              </div>
              <Button
                size="sm"
                disabled={!newDependency}
                loading={addDependencyMutation.isPending}
                onClick={() => addDependencyMutation.mutate(newDependency)}
              >
                Ajouter
              </Button>
            </div>
          </Can>
        </section>

        <section>
          <SectionTitle>Pieces jointes</SectionTitle>
          <ul className="mb-3 space-y-1 text-sm">
            {attachments.data?.length === 0 && (
              <li className="text-textTertiary">Aucune piece jointe.</li>
            )}
            {attachments.data?.map((attachment) => (
              <li key={attachment.id} className="flex items-center justify-between gap-3">
                <a
                  href={taskAttachmentUrl(task.id, attachment.id)}
                  className="truncate text-info hover:underline"
                >
                  {attachment.filename}
                </a>
                <Can permission="task:update">
                  <button
                    type="button"
                    className="font-mono text-[11px] uppercase text-textTertiary hover:text-danger"
                    onClick={() => deleteAttachmentMutation.mutate(attachment.id)}
                  >
                    Retirer
                  </button>
                </Can>
              </li>
            ))}
          </ul>
          <input
            type="file"
            className="block text-sm text-textSecondary"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) uploadMutation.mutate(file);
              event.target.value = "";
            }}
          />
        </section>

        <section>
          <SectionTitle>Commentaires</SectionTitle>
          <ul className="mb-3 space-y-3">
            {comments.data?.length === 0 && (
              <li className="text-sm text-textTertiary">Aucun commentaire.</li>
            )}
            {comments.data?.map((item) => (
              <li key={item.id} className="border-b border-border pb-2">
                <p className="whitespace-pre-wrap text-sm text-textPrimary">{item.body}</p>
                <p className="mt-1 font-mono text-[11px] text-textTertiary">
                  {formatDateTime(item.created_at)}
                </p>
              </li>
            ))}
          </ul>
          <Can permission="task:comment">
            <div className="space-y-2">
              <Textarea
                rows={3}
                value={comment}
                placeholder="Ajouter un commentaire…"
                onChange={(event) => setComment(event.target.value)}
              />
              <Button
                size="sm"
                disabled={!comment.trim()}
                loading={commentMutation.isPending}
                onClick={() => commentMutation.mutate()}
              >
                Publier
              </Button>
            </div>
          </Can>
        </section>

        <section>
          <SectionTitle>Historique</SectionTitle>
          <ul className="space-y-1 text-sm">
            {history.data?.map((entry) => (
              <li key={entry.id} className="flex justify-between gap-3">
                <span className="text-textSecondary">
                  {entry.from_status
                    ? `${TASK_STATUS_LABELS[entry.from_status]} → ${TASK_STATUS_LABELS[entry.to_status]}`
                    : `Creation (${TASK_STATUS_LABELS[entry.to_status]})`}
                  {entry.changed_by_id === null && " · systeme"}
                </span>
                <span className="shrink-0 font-mono text-[11px] text-textTertiary">
                  {formatDateTime(entry.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Supprimer la tache"
        message={`« ${task.title} » sera archivee (suppression douce) et disparaitra des listes. L'operation reste tracee dans le journal d'audit.`}
        confirmLabel="Supprimer"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
        onCancel={() => setConfirmDelete(false)}
      />
    </Drawer>
  );
}
