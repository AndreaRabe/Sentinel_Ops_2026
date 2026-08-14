import { apiClient } from "@/lib/api-client";
import type { Attachment } from "@/features/tasks/api";
import type { IncidentSeverity, IncidentStatus, Page, PageParams } from "@/lib/api-types";

export interface Incident {
  id: string;
  reference: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  site_id: string;
  reported_by_id: string | null;
  assigned_to_id: string | null;
  occurred_at: string;
  resolved_at: string | null;
  resolution_summary: string | null;
  created_at: string;
}

export interface IncidentAction {
  id: string;
  incident_id: string;
  author_id: string | null;
  action_type: "COMMENT" | "STATUS_CHANGE" | "ASSIGNMENT" | "RESOLUTION";
  body: string;
  created_at: string;
}

export interface IncidentFilters extends PageParams {
  status?: IncidentStatus[];
  severity?: IncidentSeverity[];
  site_id?: string;
  mine?: boolean;
  occurred_after?: string;
  occurred_before?: string;
  q?: string;
}

export async function listIncidents(filters: IncidentFilters): Promise<Page<Incident>> {
  const { data } = await apiClient.get<Page<Incident>>("/incidents", { params: filters });
  return data;
}

export async function getIncident(incidentId: string): Promise<Incident> {
  const { data } = await apiClient.get<Incident>(`/incidents/${incidentId}`);
  return data;
}

export async function createIncident(payload: {
  title: string;
  description: string;
  severity: IncidentSeverity;
  site_id: string;
  occurred_at?: string | null;
}): Promise<Incident> {
  const { data } = await apiClient.post<Incident>("/incidents", payload);
  return data;
}

export async function updateIncident(
  incidentId: string,
  payload: Partial<{
    title: string;
    description: string;
    severity: IncidentSeverity;
    status: IncidentStatus;
    assigned_to_id: string;
  }>
): Promise<Incident> {
  const { data } = await apiClient.patch<Incident>(`/incidents/${incidentId}`, payload);
  return data;
}

export async function resolveIncident(
  incidentId: string,
  resolutionSummary: string
): Promise<Incident> {
  const { data } = await apiClient.post<Incident>(`/incidents/${incidentId}/resolve`, {
    resolution_summary: resolutionSummary,
  });
  return data;
}

export async function closeIncident(incidentId: string): Promise<Incident> {
  const { data } = await apiClient.post<Incident>(`/incidents/${incidentId}/close`);
  return data;
}

export async function listIncidentActions(incidentId: string): Promise<IncidentAction[]> {
  const { data } = await apiClient.get<IncidentAction[]>(`/incidents/${incidentId}/actions`);
  return data;
}

export async function addIncidentAction(
  incidentId: string,
  body: string
): Promise<IncidentAction> {
  const { data } = await apiClient.post<IncidentAction>(`/incidents/${incidentId}/actions`, {
    body,
  });
  return data;
}

export async function listIncidentAttachments(incidentId: string): Promise<Attachment[]> {
  const { data } = await apiClient.get<Attachment[]>(`/incidents/${incidentId}/attachments`);
  return data;
}

export async function uploadIncidentAttachment(
  incidentId: string,
  file: File
): Promise<Attachment> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<Attachment>(
    `/incidents/${incidentId}/attachments`,
    form
  );
  return data;
}

export function incidentAttachmentUrl(incidentId: string, attachmentId: string): string {
  return `${import.meta.env.VITE_API_BASE_URL}/incidents/${incidentId}/attachments/${attachmentId}/download`;
}
