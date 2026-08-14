/**
 * Consultation du journal d'audit.
 *
 * Ecran strictement en lecture : aucune action de modification ou de
 * suppression n'y est proposee, et l'API n'en expose aucune. La table est
 * append-only avec une retention de 3 ans (exigence contractuelle client).
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  DataTable,
  EmptyState,
  ErrorState,
  PageHeader,
  Pagination,
} from "@/components/ui/data-display";
import { ScanLoader } from "@/components/ui/loaders";
import { Input, Select } from "@/components/ui/field";
import { listAuditActions, listAuditLogs } from "@/features/audit/api";
import { listUsers } from "@/features/admin/api";
import { formatDateTime } from "@/lib/format";

export function AuditPage() {
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [actorId, setActorId] = useState("");
  const [createdAfter, setCreatedAfter] = useState("");

  const actions = useQuery({ queryKey: ["audit", "actions"], queryFn: listAuditActions });
  const users = useQuery({
    queryKey: ["users", "audit-filter"],
    queryFn: () => listUsers({ page_size: 200 }),
  });

  const filters = {
    page,
    page_size: 50,
    action: action || undefined,
    actor_user_id: actorId || undefined,
    created_after: createdAfter ? new Date(createdAfter).toISOString() : undefined,
  };

  const logs = useQuery({
    queryKey: ["audit", filters],
    queryFn: () => listAuditLogs(filters),
  });

  const actorName = (id: string | null) => {
    if (!id) return "Systeme";
    const user = users.data?.items.find((item) => item.id === id);
    return user ? `${user.first_name} ${user.last_name}` : id.slice(0, 8);
  };

  return (
    <>
      <PageHeader
        title="Journal d'audit"
        subtitle="Lecture seule — les entrees ne peuvent etre ni modifiees ni supprimees (retention 3 ans)."
      />

      <div className="mb-5 flex flex-wrap gap-3">
        <Select
          className="w-56"
          value={action}
          onChange={(event) => {
            setAction(event.target.value);
            setPage(1);
          }}
        >
          <option value="">Toutes les actions</option>
          {actions.data?.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </Select>

        <Select
          className="w-56"
          value={actorId}
          onChange={(event) => {
            setActorId(event.target.value);
            setPage(1);
          }}
        >
          <option value="">Tous les acteurs</option>
          {users.data?.items.map((user) => (
            <option key={user.id} value={user.id}>
              {user.first_name} {user.last_name}
            </option>
          ))}
        </Select>

        <Input
          className="w-52"
          type="date"
          value={createdAfter}
          onChange={(event) => {
            setCreatedAfter(event.target.value);
            setPage(1);
          }}
        />
      </div>

      {logs.isLoading && <ScanLoader label="Chargement du journal" rows={8} />}
      {logs.isError && <ErrorState />}
      {logs.data?.items.length === 0 && <EmptyState title="Aucune entree pour ces filtres." />}

      {logs.data && logs.data.items.length > 0 && (
        <>
          <DataTable
            caption="Journal d'audit"
            headers={["Horodatage", "Acteur", "Action", "Ressource", "IP", "Details"]}
          >
            {logs.data.items.map((entry) => (
              <tr key={entry.id} className="border-b border-border align-top">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-textSecondary">
                  {formatDateTime(entry.created_at)}
                </td>
                <td className="px-3 py-2 text-textSecondary">{actorName(entry.actor_user_id)}</td>
                <td className="px-3 py-2 font-mono text-xs text-textPrimary">{entry.action}</td>
                <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                  {entry.resource_type}
                  {entry.resource_id ? ` · ${entry.resource_id.slice(0, 8)}` : ""}
                </td>
                <td className="px-3 py-2 font-mono text-xs text-textTertiary">
                  {entry.ip_address ?? "—"}
                </td>
                <td className="max-w-xs px-3 py-2 font-mono text-[11px] text-textTertiary">
                  {entry.details ? JSON.stringify(entry.details) : "—"}
                </td>
              </tr>
            ))}
          </DataTable>
          <Pagination
            page={logs.data.page}
            pages={logs.data.pages}
            total={logs.data.total}
            onChange={setPage}
          />
        </>
      )}
    </>
  );
}
