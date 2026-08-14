import { apiClient } from "@/lib/api-client";
import type { Page, PageParams } from "@/lib/api-types";

export interface AuditLogEntry {
  id: string;
  actor_user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface AuditFilters extends PageParams {
  actor_user_id?: string;
  action?: string;
  resource_type?: string;
  created_after?: string;
  created_before?: string;
}

export async function listAuditLogs(filters: AuditFilters): Promise<Page<AuditLogEntry>> {
  const { data } = await apiClient.get<Page<AuditLogEntry>>("/audit", { params: filters });
  return data;
}

export async function listAuditActions(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>("/audit/actions");
  return data;
}
