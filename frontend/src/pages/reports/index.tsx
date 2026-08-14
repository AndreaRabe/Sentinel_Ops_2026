import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Can } from "@/components/can";
import { Button } from "@/components/ui/button";
import {
  CountUp,
  DataTable,
  ErrorState,
  PageHeader,
  SectionTitle,
} from "@/components/ui/data-display";
import { ProgressRing, ScanLoader } from "@/components/ui/loaders";
import {
  INCIDENT_STATUS_LABELS,
  SEVERITY_LABELS,
  TASK_STATUS_LABELS,
} from "@/components/ui/badge";
import {
  downloadActivityExport,
  getActivityReport,
  type ReportPeriod,
} from "@/features/reports/api";
import { apiErrorMessage } from "@/lib/api-types";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/cn";

const PERIOD_LABELS: Record<ReportPeriod, string> = {
  day: "Jour",
  week: "Semaine",
  month: "Mois",
};

const SUMMARY_LABELS: Record<string, string> = {
  tasks_total: "Taches sur la periode",
  tasks_completed: "Taches terminees",
  tasks_late: "Taches en retard",
  tasks_cancelled: "Taches annulees",
  completion_rate: "Taux d'achevement (%)",
  incidents_total: "Incidents",
  incidents_resolved: "Incidents resolus",
};

export function ReportsPage() {
  const [period, setPeriod] = useState<ReportPeriod>("week");

  const report = useQuery({
    queryKey: ["report", period],
    queryFn: () => getActivityReport(period),
  });

  const exportMutation = useMutation({
    mutationFn: (format: "xlsx" | "pdf") => downloadActivityExport(period, format),
    onError: (error) => toast.error(apiErrorMessage(error, "Export impossible.")),
  });

  return (
    <>
      <PageHeader
        title="Rapports"
        subtitle="Activite consolidee, filtrable par jour, semaine ou mois."
        actions={
          <Can permission="report:export">
            <>
              <Button
                variant="secondary"
                size="sm"
                disabled={exportMutation.isPending}
                onClick={() => exportMutation.mutate("xlsx")}
              >
                Export Excel
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={exportMutation.isPending}
                onClick={() => exportMutation.mutate("pdf")}
              >
                Export PDF
              </Button>
            </>
          </Can>
        }
      />

      <div className="mb-5 flex items-center gap-4">
        <div className="flex rounded border border-border">
          {(Object.keys(PERIOD_LABELS) as ReportPeriod[]).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setPeriod(value)}
              className={cn(
                "px-4 py-1.5 font-mono text-[11px] uppercase tracking-widest",
                period === value ? "bg-surface text-textPrimary" : "text-textTertiary"
              )}
            >
              {PERIOD_LABELS[value]}
            </button>
          ))}
        </div>
        {exportMutation.isPending && <ProgressRing label="Generation de l'export…" />}
      </div>

      {report.isLoading && <ScanLoader label="Calcul du rapport" rows={4} />}
      {report.isError && <ErrorState />}

      {report.data && (
        <div className="space-y-10">
          <p className="font-mono text-[11px] uppercase tracking-widest text-textTertiary">
            {report.data.start} → {report.data.end} · {report.data.scope} · genere le{" "}
            {formatDateTime(report.data.generated_at)}
          </p>

          <section>
            <SectionTitle>Synthese</SectionTitle>
            <ul className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
              {Object.entries(report.data.summary).map(([key, value]) => (
                <li
                  key={key}
                  className="flex items-baseline justify-between border-b border-border py-2"
                >
                  <span className="text-sm text-textSecondary">{SUMMARY_LABELS[key] ?? key}</span>
                  <CountUp value={value} className="text-lg text-textPrimary" />
                </li>
              ))}
            </ul>
          </section>

          <div className="grid gap-10 lg:grid-cols-2">
            <section>
              <SectionTitle>Taches par statut</SectionTitle>
              <ul>
                {Object.entries(report.data.tasks_by_status).map(([status, count]) => (
                  <li
                    key={status}
                    className="flex justify-between border-b border-border py-2 text-sm"
                  >
                    <span className="text-textSecondary">
                      {TASK_STATUS_LABELS[status] ?? status}
                    </span>
                    <span className="font-mono tabular-nums">{count}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <SectionTitle>Incidents par gravite</SectionTitle>
              <ul>
                {Object.entries(report.data.incidents_by_severity).map(([severity, count]) => (
                  <li
                    key={severity}
                    className="flex justify-between border-b border-border py-2 text-sm"
                  >
                    <span className="text-textSecondary">
                      {SEVERITY_LABELS[severity] ?? severity}
                    </span>
                    <span className="font-mono tabular-nums">{count}</span>
                  </li>
                ))}
              </ul>
            </section>
          </div>

          <section>
            <SectionTitle>Detail des incidents</SectionTitle>
            {report.data.incidents.length === 0 ? (
              <p className="text-sm text-textTertiary">
                Aucun incident declare sur la periode.
              </p>
            ) : (
              <DataTable
                caption="Incidents de la periode"
                headers={["Reference", "Titre", "Site", "Gravite", "Statut", "Survenu le"]}
              >
                {report.data.incidents.map((incident, index) => (
                  <tr key={index} className="border-b border-border">
                    <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                      {incident.reference}
                    </td>
                    <td className="px-3 py-2 text-textPrimary">{incident.title}</td>
                    <td className="px-3 py-2 text-textSecondary">{incident.site}</td>
                    <td className="px-3 py-2 text-textSecondary">
                      {SEVERITY_LABELS[String(incident.severity)] ?? incident.severity}
                    </td>
                    <td className="px-3 py-2 text-textSecondary">
                      {INCIDENT_STATUS_LABELS[String(incident.status)] ?? incident.status}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                      {formatDateTime(incident.occurred_at)}
                    </td>
                  </tr>
                ))}
              </DataTable>
            )}
          </section>

          <section>
            <SectionTitle>Detail des taches</SectionTitle>
            <DataTable
              caption="Taches de la periode"
              headers={["Titre", "Site", "Statut", "Priorite", "Echeance"]}
            >
              {report.data.tasks.map((task, index) => (
                <tr key={index} className="border-b border-border">
                  <td className="px-3 py-2 text-textPrimary">{task.title}</td>
                  <td className="px-3 py-2 text-textSecondary">{task.site}</td>
                  <td className="px-3 py-2 text-textSecondary">
                    {TASK_STATUS_LABELS[String(task.status)] ?? task.status}
                  </td>
                  <td className="px-3 py-2 text-textSecondary">{task.priority}</td>
                  <td className="px-3 py-2 font-mono text-xs text-textSecondary">
                    {formatDateTime(task.due_at)}
                  </td>
                </tr>
              ))}
            </DataTable>
          </section>
        </div>
      )}
    </>
  );
}
