import { apiClient } from "@/lib/api-client";
import type { TaskPriority, TaskStatus } from "@/lib/api-types";

export interface DashboardKpis {
  tasks_today: number;
  tasks_late: number;
  tasks_urgent: number;
  tasks_open: number;
  incidents_open: number;
}

export interface WorkloadEntry {
  user_id: string;
  first_name: string;
  last_name: string;
  open_tasks: number;
}

export interface Dashboard {
  kpis: DashboardKpis;
  tasks_by_status: Record<string, number>;
  incidents_by_severity: Record<string, number>;
  workload: WorkloadEntry[];
  generated_at: string;
}

export async function getDashboard(): Promise<Dashboard> {
  const { data } = await apiClient.get<Dashboard>("/dashboard");
  return data;
}

export interface PlanningEntry {
  id: string;
  title: string;
  status: TaskStatus;
  priority: TaskPriority;
  site_id: string;
  due_at: string;
  assignee_ids: string[];
}

export interface Planning {
  start: string;
  end: string;
  days: { day: string; entries: PlanningEntry[] }[];
}

export async function getPlanning(params: {
  start: string;
  end: string;
  mine?: boolean;
}): Promise<Planning> {
  const { data } = await apiClient.get<Planning>("/planning", { params });
  return data;
}

export type ReportPeriod = "day" | "week" | "month";

export interface ActivityReport {
  start: string;
  end: string;
  generated_at: string;
  scope: string;
  summary: Record<string, number>;
  tasks_by_status: Record<string, number>;
  incidents_by_severity: Record<string, number>;
  tasks: Record<string, string | null>[];
  incidents: Record<string, string | null>[];
}

export async function getActivityReport(period: ReportPeriod): Promise<ActivityReport> {
  const { data } = await apiClient.get<ActivityReport>("/reports/activity", {
    params: { period },
  });
  return data;
}

/**
 * Telecharge l'export. Le fichier transite par une requete authentifiee (le
 * token n'est jamais mis dans une URL), puis est remis au navigateur via un
 * Blob temporaire.
 */
export async function downloadActivityExport(
  period: ReportPeriod,
  format: "xlsx" | "pdf"
): Promise<void> {
  const response = await apiClient.get("/reports/activity/export", {
    params: { period, format },
    responseType: "blob",
  });

  const url = URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `sentinel-ops_${period}.${format}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
