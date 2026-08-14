import { apiClient } from "@/lib/api-client";
import type { Page, PageParams } from "@/lib/api-types";

export interface SiteSummary {
  id: string;
  name: string;
  is_active: boolean;
}

export interface Site extends SiteSummary {
  created_at: string;
  user_count: number;
}

export interface User {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  role: string;
  is_active: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  sites: SiteSummary[];
}

export interface CurrentUser extends User {
  permissions: string[];
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  permissions: string[];
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const { data } = await apiClient.get<CurrentUser>("/users/me");
  return data;
}

export interface UserFilters extends PageParams {
  role?: string;
  q?: string;
  include_inactive?: boolean;
}

export async function listUsers(filters: UserFilters = {}): Promise<Page<User>> {
  const { data } = await apiClient.get<Page<User>>("/users", { params: filters });
  return data;
}

export async function createUser(payload: {
  first_name: string;
  last_name: string;
  email: string;
  role: string;
  site_ids: string[];
}): Promise<{ temporary_password: string }> {
  const { data } = await apiClient.post<{ temporary_password: string }>("/users", payload);
  return data;
}

export async function updateUser(
  userId: string,
  payload: Partial<{
    first_name: string;
    last_name: string;
    email: string;
    role: string;
    site_ids: string[];
  }>
): Promise<User> {
  const { data } = await apiClient.patch<User>(`/users/${userId}`, payload);
  return data;
}

export async function setUserActivation(userId: string, isActive: boolean): Promise<User> {
  const { data } = await apiClient.put<User>(`/users/${userId}/activation`, {
    is_active: isActive,
  });
  return data;
}

export async function resetUserPassword(userId: string): Promise<{ temporary_password: string }> {
  const { data } = await apiClient.post<{ temporary_password: string }>(
    `/users/${userId}/reset-password`
  );
  return data;
}

export async function listSites(includeInactive = false): Promise<Site[]> {
  const { data } = await apiClient.get<Site[]>("/sites", {
    params: { include_inactive: includeInactive },
  });
  return data;
}

export async function createSite(name: string): Promise<Site> {
  const { data } = await apiClient.post<Site>("/sites", { name });
  return data;
}

export async function updateSite(
  siteId: string,
  payload: { name?: string; is_active?: boolean }
): Promise<Site> {
  const { data } = await apiClient.patch<Site>(`/sites/${siteId}`, payload);
  return data;
}

export async function deleteSite(siteId: string): Promise<void> {
  await apiClient.delete(`/sites/${siteId}`);
}

export async function listRoles(): Promise<Role[]> {
  const { data } = await apiClient.get<Role[]>("/roles");
  return data;
}

export interface SystemSetting {
  key: string;
  value: Record<string, unknown>;
  description: string | null;
}

export async function listSettings(): Promise<SystemSetting[]> {
  const { data } = await apiClient.get<SystemSetting[]>("/settings");
  return data;
}

export async function upsertSetting(
  key: string,
  value: Record<string, unknown>,
  description?: string | null
): Promise<SystemSetting> {
  const { data } = await apiClient.put<SystemSetting>(`/settings/${key}`, { value, description });
  return data;
}
