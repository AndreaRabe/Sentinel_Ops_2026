/**
 * Dashboard editorial : bandeau de KPI en gros chiffres tabulaires animes,
 * puis repartitions et charge de travail separees par des hairlines - pas de
 * cartes empilees (cahier des charges section 11).
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getDashboard } from "@/features/reports/api";
import {
  CountUp,
  EmptyState,
  ErrorState,
  KpiTile,
  PageHeader,
  SectionTitle,
} from "@/components/ui/data-display";
import { ScanLoader } from "@/components/ui/loaders";
import { SEVERITY_LABELS, TASK_STATUS_LABELS } from "@/components/ui/badge";
import { formatDateTime } from "@/lib/format";

export function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["dashboard"],
    queryFn: getDashboard,
    refetchInterval: 120_000,
  });

  if (isLoading) return <ScanLoader label="Chargement du dashboard" rows={4} />;
  if (isError || !data) return <ErrorState />;

  const maxWorkload = Math.max(1, ...data.workload.map((entry) => entry.open_tasks));

  return (
    <>
      <PageHeader
        title="Poste de commandement"
        subtitle={`Situation au ${formatDateTime(data.generated_at)}`}
      />

      <div className="mb-10 flex flex-wrap gap-y-6">
        <KpiTile label="Aujourd'hui" value={data.kpis.tasks_today} />
        <KpiTile label="En retard" value={data.kpis.tasks_late} tone="danger" />
        <KpiTile label="Urgentes" value={data.kpis.tasks_urgent} tone="warning" />
        <KpiTile label="Taches ouvertes" value={data.kpis.tasks_open} />
        <KpiTile label="Incidents ouverts" value={data.kpis.incidents_open} tone="warning" />
      </div>

      <div className="grid gap-10 lg:grid-cols-2">
        <section>
          <SectionTitle>Taches par statut</SectionTitle>
          {Object.keys(data.tasks_by_status).length === 0 ? (
            <EmptyState title="Aucune tache enregistree." />
          ) : (
            <ul>
              {Object.entries(data.tasks_by_status).map(([status, count]) => (
                <li
                  key={status}
                  className="flex items-baseline justify-between border-b border-border py-2"
                >
                  <span className="text-sm text-textSecondary">
                    {TASK_STATUS_LABELS[status] ?? status}
                  </span>
                  <CountUp value={count} className="text-lg text-textPrimary" />
                </li>
              ))}
            </ul>
          )}
          <Link
            to="/taches"
            className="mt-3 inline-block font-mono text-[11px] uppercase tracking-widest text-info"
          >
            Ouvrir les taches →
          </Link>
        </section>

        <section>
          <SectionTitle>Incidents ouverts par gravite</SectionTitle>
          {Object.keys(data.incidents_by_severity).length === 0 ? (
            <EmptyState title="Aucun incident ouvert." />
          ) : (
            <ul>
              {Object.entries(data.incidents_by_severity).map(([severity, count]) => (
                <li
                  key={severity}
                  className="flex items-baseline justify-between border-b border-border py-2"
                >
                  <span className="text-sm text-textSecondary">
                    {SEVERITY_LABELS[severity] ?? severity}
                  </span>
                  <CountUp value={count} className="text-lg text-textPrimary" />
                </li>
              ))}
            </ul>
          )}
          <Link
            to="/incidents"
            className="mt-3 inline-block font-mono text-[11px] uppercase tracking-widest text-info"
          >
            Ouvrir les incidents →
          </Link>
        </section>

        <section className="lg:col-span-2">
          <SectionTitle>Charge de travail</SectionTitle>
          {data.workload.length === 0 ? (
            <EmptyState title="Aucune tache assignee." />
          ) : (
            <ul className="space-y-2">
              {data.workload.map((entry) => (
                <li key={entry.user_id} className="flex items-center gap-3">
                  <span className="w-48 shrink-0 truncate text-sm text-textSecondary">
                    {entry.first_name} {entry.last_name}
                  </span>
                  <span className="h-2 flex-1 bg-surface">
                    <span
                      className="block h-2 bg-primary"
                      style={{ width: `${(entry.open_tasks / maxWorkload) * 100}%` }}
                    />
                  </span>
                  <span className="w-10 text-right font-mono text-sm tabular-nums text-textPrimary">
                    {entry.open_tasks}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </>
  );
}
