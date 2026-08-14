/**
 * Ecran Taches : deux vues (Liste/Backlog et Kanban) sur les MEMES donnees,
 * pas deux modeles distincts (cahier des charges section 2).
 */
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Can } from "@/components/can";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/field";
import {
  DataTable,
  EmptyState,
  ErrorState,
  PageHeader,
  Pagination,
} from "@/components/ui/data-display";
import { ScanLoader } from "@/components/ui/loaders";
import {
  PRIORITY_LABELS,
  PriorityBadge,
  TASK_STATUS_LABELS,
  TaskStatusBadge,
} from "@/components/ui/badge";
import { listSites } from "@/features/admin/api";
import { changeTaskStatus, listTasks, type Task } from "@/features/tasks/api";
import { TaskDetailDrawer } from "@/features/tasks/task-detail-drawer";
import { TaskFormDrawer } from "@/features/tasks/task-form-drawer";
import { TemplatePanel } from "@/features/tasks/template-panel";
import { apiErrorMessage, type TaskPriority, type TaskStatus } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/cn";

/** Colonnes du Kanban : les etats terminaux sont regroupes a droite. */
const KANBAN_COLUMNS: TaskStatus[] = [
  "DRAFT",
  "ASSIGNED",
  "IN_PROGRESS",
  "LATE",
  "POSTPONED",
  "COMPLETED",
];

type View = "list" | "kanban" | "templates";

const VIEW_LABELS: Record<View, string> = {
  list: "Liste",
  kanban: "Kanban",
  templates: "Modeles",
};

export function TasksPage() {
  const queryClient = useQueryClient();
  const [view, setView] = useState<View>("list");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "">("");
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | "">("");
  const [siteFilter, setSiteFilter] = useState("");
  const [mineOnly, setMineOnly] = useState(false);

  const [detailTask, setDetailTask] = useState<Task | null>(null);
  const [formTask, setFormTask] = useState<Task | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const sites = useQuery({ queryKey: ["sites"], queryFn: () => listSites() });

  const filters = useMemo(
    () => ({
      page,
      // Le Kanban a besoin de toutes les taches d'un coup pour repartir les
      // colonnes ; la liste reste paginee.
      page_size: view === "kanban" ? 200 : 25,
      q: search || undefined,
      status: statusFilter ? [statusFilter] : undefined,
      priority: priorityFilter ? [priorityFilter] : undefined,
      site_id: siteFilter || undefined,
      mine: mineOnly || undefined,
    }),
    [page, view, search, statusFilter, priorityFilter, siteFilter, mineOnly]
  );

  const tasksQuery = useQuery({
    queryKey: ["tasks", filters],
    queryFn: () => listTasks(filters),
    // Le panneau Modeles n'affiche aucune tache : inutile d'interroger l'API.
    enabled: view !== "templates",
  });

  const statusMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: TaskStatus }) =>
      changeTaskStatus(taskId, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Transition refusee.")),
  });

  const siteName = (siteId: string) =>
    sites.data?.find((site) => site.id === siteId)?.name ?? "—";

  const openCreate = () => {
    setFormTask(null);
    setFormOpen(true);
  };

  return (
    <>
      <PageHeader
        title="Taches"
        subtitle="Liste, backlog et Kanban partagent les memes donnees."
        actions={
          <Can permission="task:create">
            <Button onClick={openCreate}>Nouvelle tache</Button>
          </Can>
        }
      />

      <div className="mb-5 flex flex-wrap items-end gap-3">
        <div className="flex rounded border border-border">
          {(["list", "kanban", "templates"] as View[]).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => {
                setView(value);
                setPage(1);
              }}
              className={cn(
                "px-3 py-1.5 font-mono text-[11px] uppercase tracking-widest",
                view === value ? "bg-surface text-textPrimary" : "text-textTertiary"
              )}
            >
              {VIEW_LABELS[value]}
            </button>
          ))}
        </div>

        {/* Les filtres ne s'appliquent qu'aux taches, pas aux modeles. */}
        {view !== "templates" && (
          <>
            <Input
              className="w-56"
              placeholder="Rechercher…"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
            />

            <Select
              className="w-44"
              aria-label="Filtrer par statut"
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value as TaskStatus | "");
                setPage(1);
              }}
            >
              <option value="">Tous les statuts</option>
              {Object.entries(TASK_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>

            <Select
              className="w-44"
              aria-label="Filtrer par priorite"
              value={priorityFilter}
              onChange={(event) => {
                setPriorityFilter(event.target.value as TaskPriority | "");
                setPage(1);
              }}
            >
              <option value="">Toutes priorites</option>
              {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>

            <Select
              className="w-44"
              aria-label="Filtrer par site"
              value={siteFilter}
              onChange={(event) => {
                setSiteFilter(event.target.value);
                setPage(1);
              }}
            >
              <option value="">Tous les sites</option>
              {sites.data?.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name}
                </option>
              ))}
            </Select>

            <label className="flex items-center gap-2 text-sm text-textSecondary">
              <input
                type="checkbox"
                checked={mineOnly}
                onChange={(event) => {
                  setMineOnly(event.target.checked);
                  setPage(1);
                }}
              />
              Mes taches
            </label>
          </>
        )}
      </div>

      {view === "templates" && <TemplatePanel />}

      {tasksQuery.isLoading && <ScanLoader label="Chargement des taches" />}
      {tasksQuery.isError && <ErrorState />}

      {tasksQuery.data && tasksQuery.data.items.length === 0 && (
        <EmptyState
          title="Aucune tache ne correspond a ces filtres."
          message="Modifiez la recherche ou creez une nouvelle tache."
        />
      )}

      {tasksQuery.data && tasksQuery.data.items.length > 0 && view === "list" && (
        <>
          <DataTable
            caption="Liste des taches"
            headers={["Titre", "Statut", "Priorite", "Site", "Echeance", "Agents"]}
          >
            {tasksQuery.data.items.map((task) => (
              <tr
                key={task.id}
                className="cursor-pointer border-b border-border hover:bg-surfaceHover"
                onClick={() => setDetailTask(task)}
              >
                <td className="px-3 py-2">
                  <span className="text-textPrimary">{task.title}</span>
                </td>
                <td className="px-3 py-2">
                  <TaskStatusBadge status={task.status} />
                </td>
                <td className="px-3 py-2">
                  <PriorityBadge priority={task.priority} />
                </td>
                <td className="px-3 py-2 text-textSecondary">{siteName(task.site_id)}</td>
                <td
                  className={cn(
                    "px-3 py-2 font-mono text-xs",
                    task.is_overdue ? "text-danger" : "text-textSecondary"
                  )}
                >
                  {formatDateTime(task.due_at)}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                  {task.assignee_ids.length}
                </td>
              </tr>
            ))}
          </DataTable>
          <Pagination
            page={tasksQuery.data.page}
            pages={tasksQuery.data.pages}
            total={tasksQuery.data.total}
            onChange={setPage}
          />
        </>
      )}

      {tasksQuery.data && view === "kanban" && (
        <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          {KANBAN_COLUMNS.map((column) => {
            const columnTasks = tasksQuery.data.items.filter((task) => task.status === column);
            return (
              <section key={column}>
                <h2 className="mb-2 flex items-center justify-between border-b border-border pb-2">
                  <span className="font-mono text-[11px] uppercase tracking-widest text-textTertiary">
                    {TASK_STATUS_LABELS[column]}
                  </span>
                  <span className="font-mono text-xs tabular-nums text-textTertiary">
                    {columnTasks.length}
                  </span>
                </h2>
                <ul className="space-y-2">
                  {columnTasks.map((task) => (
                    <li
                      key={task.id}
                      className="border border-border bg-surface p-3 hover:bg-surfaceHover"
                    >
                      <button
                        type="button"
                        className="block w-full text-left"
                        onClick={() => setDetailTask(task)}
                      >
                        <span className="block text-sm text-textPrimary">{task.title}</span>
                        <span className="mt-1 block font-mono text-[11px] text-textTertiary">
                          {formatDateTime(task.due_at)}
                        </span>
                      </button>
                      {/* Changement de statut "live" depuis la carte. */}
                      {column === "ASSIGNED" && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="mt-2 px-0"
                          onClick={() =>
                            statusMutation.mutate({ taskId: task.id, status: "IN_PROGRESS" })
                          }
                        >
                          Demarrer →
                        </Button>
                      )}
                      {(column === "IN_PROGRESS" || column === "LATE") && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="mt-2 px-0"
                          onClick={() =>
                            statusMutation.mutate({ taskId: task.id, status: "COMPLETED" })
                          }
                        >
                          Cloturer →
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      )}

      <TaskDetailDrawer
        task={detailTask}
        open={Boolean(detailTask)}
        onClose={() => setDetailTask(null)}
        onEdit={() => {
          setFormTask(detailTask);
          setDetailTask(null);
          setFormOpen(true);
        }}
      />

      <TaskFormDrawer open={formOpen} task={formTask} onClose={() => setFormOpen(false)} />
    </>
  );
}
