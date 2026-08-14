import { apiClient } from "@/lib/api-client";
import type { Page, PageParams } from "@/lib/api-types";

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  resource_type: string | null;
  resource_id: string | null;
  read_at: string | null;
  created_at: string;
}

export async function listNotifications(
  params: PageParams & { unread_only?: boolean } = {}
): Promise<Page<Notification>> {
  const { data } = await apiClient.get<Page<Notification>>("/notifications", { params });
  return data;
}

export async function unreadCount(): Promise<{ unread: number }> {
  const { data } = await apiClient.get<{ unread: number }>("/notifications/unread-count");
  return data;
}

/** `ids` absent = tout marquer comme lu. */
export async function markNotificationsRead(ids?: string[]): Promise<{ unread: number }> {
  const { data } = await apiClient.post<{ unread: number }>("/notifications/mark-read", {
    notification_ids: ids ?? null,
  });
  return data;
}
