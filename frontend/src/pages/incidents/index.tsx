import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Can } from "@/components/can";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { Field, Input, Select, Textarea } from "@/components/ui/field";
import {
  DataTable,
  EmptyState,
  ErrorState,
  PageHeader,
  Pagination,
  SectionTitle,
} from "@/components/ui/data-display";
import { ScanLoader } from "@/components/ui/loaders";
import {
  INCIDENT_STATUS_LABELS,
  IncidentStatusBadge,
  SEVERITY_LABELS,
  SeverityBadge,
} from "@/components/ui/badge";
import { listSites, listUsers } from "@/features/admin/api";
import {
  addIncidentAction,
  closeIncident,
  createIncident,
  updateIncident,
  incidentAttachmentUrl,
  listIncidentActions,
  listIncidentAttachments,
  listIncidents,
  resolveIncident,
  uploadIncidentAttachment,
  type Incident,
} from "@/features/incidents/api";
import { apiErrorMessage, type IncidentSeverity, type IncidentStatus } from "@/lib/api-types";
import { formatDateTime, fromDateTimeLocal } from "@/lib/format";

const incidentSchema = z.object({
  title: z.string().min(3, "Le titre doit contenir au moins 3 caracteres."),
  description: z.string().min(1, "Decrivez l'incident."),
  severity: z.enum(["MINOR", "MODERATE", "MAJOR", "CRITICAL"]),
  site_id: z.string().uuid("Selectionnez un site."),
  occurred_at: z.string().optional(),
});

type IncidentFormValues = z.infer<typeof incidentSchema>;

export function IncidentsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<IncidentStatus | "">("");
  const [severityFilter, setSeverityFilter] = useState<IncidentSeverity | "">("");
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [detail, setDetail] = useState<Incident | null>(null);

  const sites = useQuery({ queryKey: ["sites"], queryFn: () => listSites() });

  const filters = {
    page,
    page_size: 25,
    status: statusFilter ? [statusFilter] : undefined,
    severity: severityFilter ? [severityFilter] : undefined,
    q: search || undefined,
  };

  const incidentsQuery = useQuery({
    queryKey: ["incidents", filters],
    queryFn: () => listIncidents(filters),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<IncidentFormValues>({
    resolver: zodResolver(incidentSchema),
    defaultValues: { severity: "MINOR", title: "", description: "", site_id: "" },
  });

  const createMutation = useMutation({
    mutationFn: (values: IncidentFormValues) =>
      createIncident({
        ...values,
        occurred_at: values.occurred_at ? fromDateTimeLocal(values.occurred_at) : null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Incident declare.");
      reset();
      setCreateOpen(false);
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Declaration impossible.")),
  });

  const siteName = (siteId: string) =>
    sites.data?.find((site) => site.id === siteId)?.name ?? "—";

  return (
    <>
      <PageHeader
        title="Incidents"
        subtitle="Declaration, suivi et cloture des incidents de vos sites."
        actions={
          <Can permission="incident:create">
            <Button onClick={() => setCreateOpen(true)}>Declarer un incident</Button>
          </Can>
        }
      />

      <div className="mb-5 flex flex-wrap gap-3">
        <Input
          className="w-56"
          placeholder="Rechercher (titre, reference)…"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
        />
        <Select
          className="w-44"
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value as IncidentStatus | "");
            setPage(1);
          }}
        >
          <option value="">Tous les statuts</option>
          {Object.entries(INCIDENT_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select
          className="w-44"
          value={severityFilter}
          onChange={(event) => {
            setSeverityFilter(event.target.value as IncidentSeverity | "");
            setPage(1);
          }}
        >
          <option value="">Toutes gravites</option>
          {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
      </div>

      {incidentsQuery.isLoading && <ScanLoader label="Chargement des incidents" />}
      {incidentsQuery.isError && <ErrorState />}
      {incidentsQuery.data?.items.length === 0 && (
        <EmptyState title="Aucun incident ne correspond a ces filtres." />
      )}

      {incidentsQuery.data && incidentsQuery.data.items.length > 0 && (
        <>
          <DataTable
            caption="Liste des incidents"
            headers={["Reference", "Titre", "Gravite", "Statut", "Site", "Survenu le"]}
          >
            {incidentsQuery.data.items.map((incident) => (
              <tr
                key={incident.id}
                className="cursor-pointer border-b border-border hover:bg-surfaceHover"
                onClick={() => setDetail(incident)}
              >
                <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                  {incident.reference}
                </td>
                <td className="px-3 py-2 text-textPrimary">{incident.title}</td>
                <td className="px-3 py-2">
                  <SeverityBadge severity={incident.severity} />
                </td>
                <td className="px-3 py-2">
                  <IncidentStatusBadge status={incident.status} />
                </td>
                <td className="px-3 py-2 text-textSecondary">{siteName(incident.site_id)}</td>
                <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                  {formatDateTime(incident.occurred_at)}
                </td>
              </tr>
            ))}
          </DataTable>
          <Pagination
            page={incidentsQuery.data.page}
            pages={incidentsQuery.data.pages}
            total={incidentsQuery.data.total}
            onChange={setPage}
          />
        </>
      )}

      <Drawer
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="Declarer un incident"
        footer={
          <>
            <Button variant="secondary" onClick={() => setCreateOpen(false)}>
              Annuler
            </Button>
            <Button
              loading={createMutation.isPending}
              onClick={handleSubmit((values) => createMutation.mutate(values))}
            >
              Declarer
            </Button>
          </>
        }
      >
        <form className="space-y-4" noValidate>
          <Field label="Titre" htmlFor="inc-title" error={errors.title?.message} required>
            <Input id="inc-title" {...register("title")} />
          </Field>
          <Field
            label="Description"
            htmlFor="inc-description"
            error={errors.description?.message}
            required
          >
            <Textarea id="inc-description" rows={5} {...register("description")} />
          </Field>
          <Field label="Gravite" htmlFor="inc-severity">
            <Select id="inc-severity" {...register("severity")}>
              {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Site" htmlFor="inc-site" error={errors.site_id?.message} required>
            <Select id="inc-site" {...register("site_id")}>
              <option value="">— Selectionner —</option>
              {sites.data?.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label="Survenu le"
            htmlFor="inc-occurred"
            hint="Laisser vide pour horodater maintenant."
          >
            <Input id="inc-occurred" type="datetime-local" {...register("occurred_at")} />
          </Field>
        </form>
      </Drawer>

      <IncidentDetailDrawer incident={detail} onClose={() => setDetail(null)} />
    </>
  );
}

function IncidentDetailDrawer({
  incident,
  onClose,
}: {
  incident: Incident | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState("");
  const [assignee, setAssignee] = useState("");
  const [severity, setSeverity] = useState<IncidentSeverity | "">("");

  const incidentId = incident?.id ?? "";
  const enabled = Boolean(incident);

  const actions = useQuery({
    queryKey: ["incident", incidentId, "actions"],
    queryFn: () => listIncidentActions(incidentId),
    enabled,
  });
  const attachments = useQuery({
    queryKey: ["incident", incidentId, "attachments"],
    queryFn: () => listIncidentAttachments(incidentId),
    enabled,
  });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["incidents"] });
    queryClient.invalidateQueries({ queryKey: ["incident", incidentId] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const noteMutation = useMutation({
    mutationFn: () => addIncidentAction(incidentId, note),
    onSuccess: () => {
      setNote("");
      actions.refetch();
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Action refusee.")),
  });

  const resolveMutation = useMutation({
    mutationFn: () => resolveIncident(incidentId, resolution),
    onSuccess: () => {
      setResolution("");
      refresh();
      onClose();
      toast.success("Incident resolu.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Resolution refusee.")),
  });

  const closeMutation = useMutation({
    mutationFn: () => closeIncident(incidentId),
    onSuccess: () => {
      refresh();
      onClose();
      toast.success("Incident cloture.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Cloture refusee.")),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadIncidentAttachment(incidentId, file),
    onSuccess: () => attachments.refetch(),
    onError: (error) => toast.error(apiErrorMessage(error, "Envoi refuse.")),
  });

  const users = useQuery({
    queryKey: ["users", "incident-assignees"],
    queryFn: () => listUsers({ page_size: 200, include_inactive: false }),
    enabled,
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateIncident>[1]) =>
      updateIncident(incidentId, payload),
    onSuccess: () => {
      refresh();
      actions.refetch();
      toast.success("Incident mis a jour.");
    },
    onError: (error) => toast.error(apiErrorMessage(error, "Modification refusee.")),
  });

  if (!incident) return null;

  const isEditable = incident.status !== "CLOSED";

  return (
    <Drawer
      open
      onClose={onClose}
      title={`${incident.reference} — ${incident.title}`}
      width="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Fermer
          </Button>
          {incident.status === "RESOLVED" && (
            <Can permission="incident:resolve">
              <Button loading={closeMutation.isPending} onClick={() => closeMutation.mutate()}>
                Cloturer
              </Button>
            </Can>
          )}
        </>
      }
    >
      <div className="space-y-8">
        <div className="flex flex-wrap gap-2">
          <SeverityBadge severity={incident.severity} />
          <IncidentStatusBadge status={incident.status} />
        </div>

        <p className="whitespace-pre-wrap text-sm text-textSecondary">{incident.description}</p>

        <section className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-textTertiary">Survenu le</span>
          <span className="font-mono">{formatDateTime(incident.occurred_at)}</span>
          <span className="text-textTertiary">Resolu le</span>
          <span className="font-mono">{formatDateTime(incident.resolved_at)}</span>
        </section>

        {incident.resolution_summary && (
          <section>
            <SectionTitle>Compte rendu de resolution</SectionTitle>
            <p className="whitespace-pre-wrap text-sm text-textSecondary">
              {incident.resolution_summary}
            </p>
          </section>
        )}

        {isEditable && (
          <Can permission="incident:update">
            <section>
              <SectionTitle>Prise en charge</SectionTitle>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Responsable" htmlFor="inc-assignee">
                  <Select
                    id="inc-assignee"
                    value={assignee || incident.assigned_to_id || ""}
                    onChange={(event) => {
                      setAssignee(event.target.value);
                      if (event.target.value) {
                        updateMutation.mutate({ assigned_to_id: event.target.value });
                      }
                    }}
                  >
                    <option value="">— Non assigne —</option>
                    {users.data?.items.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.first_name} {user.last_name}
                      </option>
                    ))}
                  </Select>
                </Field>

                <Field label="Gravite" htmlFor="inc-severity-edit">
                  <Select
                    id="inc-severity-edit"
                    value={severity || incident.severity}
                    onChange={(event) => {
                      const value = event.target.value as IncidentSeverity;
                      setSeverity(value);
                      updateMutation.mutate({ severity: value });
                    }}
                  >
                    {Object.entries(SEVERITY_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
              {incident.status === "OPEN" && (
                <Button
                  size="sm"
                  variant="secondary"
                  className="mt-3"
                  loading={updateMutation.isPending}
                  onClick={() => updateMutation.mutate({ status: "IN_PROGRESS" })}
                >
                  Passer en traitement
                </Button>
              )}
            </section>
          </Can>
        )}

        {(incident.status === "OPEN" || incident.status === "IN_PROGRESS") && (
          <Can permission="incident:resolve">
            <section>
              <SectionTitle>Resoudre</SectionTitle>
              <Textarea
                rows={3}
                value={resolution}
                placeholder="Ce qui a ete fait (10 caracteres minimum)…"
                onChange={(event) => setResolution(event.target.value)}
              />
              <Button
                size="sm"
                className="mt-2"
                disabled={resolution.trim().length < 10}
                loading={resolveMutation.isPending}
                onClick={() => resolveMutation.mutate()}
              >
                Marquer comme resolu
              </Button>
            </section>
          </Can>
        )}

        <section>
          <SectionTitle>Pieces jointes</SectionTitle>
          <ul className="mb-3 space-y-1 text-sm">
            {attachments.data?.length === 0 && (
              <li className="text-textTertiary">Aucune piece jointe.</li>
            )}
            {attachments.data?.map((attachment) => (
              <li key={attachment.id}>
                <a
                  href={incidentAttachmentUrl(incident.id, attachment.id)}
                  className="text-info hover:underline"
                >
                  {attachment.filename}
                </a>
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
          <SectionTitle>Journal des actions</SectionTitle>
          <ul className="mb-3 space-y-3">
            {actions.data?.map((action) => (
              <li key={action.id} className="border-b border-border pb-2">
                <p className="whitespace-pre-wrap text-sm text-textPrimary">{action.body}</p>
                <p className="mt-1 font-mono text-[11px] text-textTertiary">
                  {action.action_type} · {formatDateTime(action.created_at)}
                </p>
              </li>
            ))}
          </ul>
          <Can permission="incident:update">
            <div className="space-y-2">
              <Textarea
                rows={3}
                value={note}
                placeholder="Consigner une action…"
                onChange={(event) => setNote(event.target.value)}
              />
              <Button
                size="sm"
                disabled={!note.trim()}
                loading={noteMutation.isPending}
                onClick={() => noteMutation.mutate()}
              >
                Ajouter
              </Button>
            </div>
          </Can>
        </section>
      </div>
    </Drawer>
  );
}
