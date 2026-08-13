import { apiClient } from "@/lib/api-client";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  must_change_password: boolean;
}

export async function login(payload: { email: string; password: string }): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
  return data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  await apiClient.post("/auth/change-password", payload);
}
