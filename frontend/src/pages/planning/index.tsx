/**
 * Planning / calendrier : affichage seul, sans rotations ni gardes (celles-ci
 * sont explicitement en V2 - cahier des charges section 2).
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { addDays, format, startOfWeek } from "date-fns";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, PageHeader } from "@/components/ui/data-display";
import { ScanLoader } from "@/components/ui/loaders";
import { PriorityBadge, TaskStatusBadge } from "@/components/ui/badge";
import { getPlanning } from "@/features/reports/api";
import { formatDayLabel } from "@/lib/format";

export function PlanningPage() {
  const [weekStart, setWeekStart] = useState(() =>
    startOfWeek(new Date(), { weekStartsOn: 1 })
  );
  const [mineOnly, setMineOnly] = useState(false);

  const start = format(weekStart, "yyyy-MM-dd");
  const end = format(addDays(weekStart, 6), "yyyy-MM-dd");

  const planning = useQuery({
    queryKey: ["planning", start, end, mineOnly],
    queryFn: () => getPlanning({ start, end, mine: mineOnly }),
  });

  return (
    <>
      <PageHeader
        title="Planning"
        subtitle={`Semaine du ${formatDayLabel(weekStart)}`}
        actions={
          <>
            <label className="mr-3 flex items-center gap-2 text-sm text-textSecondary">
              <input
                type="checkbox"
                checked={mineOnly}
                onChange={(event) => setMineOnly(event.target.checked)}
              />
              Mes taches
            </label>
            <Button variant="secondary" size="sm" onClick={() => setWeekStart(addDays(weekStart, -7))}>
              Semaine precedente
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setWeekStart(startOfWeek(new Date(), { weekStartsOn: 1 }))}
            >
              Cette semaine
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setWeekStart(addDays(weekStart, 7))}>
              Semaine suivante
            </Button>
          </>
        }
      />

      {planning.isLoading && <ScanLoader label="Chargement du planning" rows={7} />}
      {planning.isError && <ErrorState />}

      {planning.data && (
        <div className="grid gap-4 md:grid-cols-7">
          {planning.data.days.map((day) => (
            <section key={day.day} className="min-w-0">
              <h2 className="mb-2 border-b border-border pb-2 font-mono text-[11px] uppercase tracking-widest text-textTertiary">
                {formatDayLabel(day.day)}
              </h2>
              {day.entries.length === 0 ? (
                <p className="text-xs text-textTertiary">—</p>
              ) : (
                <ul className="space-y-2">
                  {day.entries.map((entry) => (
                    <li key={entry.id} className="border border-border bg-surface p-2">
                      <span className="block text-sm text-textPrimary">{entry.title}</span>
                      <span className="mt-1 flex flex-wrap gap-1">
                        <TaskStatusBadge status={entry.status} />
                        <PriorityBadge priority={entry.priority} />
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}

      {planning.data && planning.data.days.every((day) => day.entries.length === 0) && (
        <div className="mt-6">
          <EmptyState
            title="Aucune tache planifiee cette semaine."
            message="Les taches sans echeance n'apparaissent pas au planning."
          />
        </div>
      )}
    </>
  );
}
