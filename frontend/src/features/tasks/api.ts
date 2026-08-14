import { apiClient } from "@/lib/api-client";
import type { Page, PageParams, TaskPriority, TaskStatus } from "@/lib/api-types";

export interface ChecklistItem {
  id: string;
  label: string;
  position: number;
  is_done: boolean;
  done_by_id: string | null;
  done_at: string | null;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  site_id: string;
  template_id: string | null;
  created_by_id: string | null;
  due_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  postponed_until: string | null;
  estimated_minutes: number | null;
  created_at: string;
  assignee_ids: string[];
  checklist: ChecklistItem[];
  is_overdue: boolean;
}

export interface TaskFilters extends PageParams {
  status?: TaskStatus[];
  priority?: TaskPriority[];
  assignee_id?: string;
  mine?: boolean;
  site_id?: string;
  due_before?: string;
  due_after?: string;
  q?: string;
}

export interface TaskComment {
  id: string;
  task_id: string;
  author_id: string | null;
  body: string;
  created_at: string;
}

export interface TaskHistoryEntry {
  id: string;
  from_status: TaskStatus | null;
  to_status: TaskStatus;
  changed_by_id: string | null;
  comment: string | null;
  created_at: string;
}

export interface Attachment {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_by_id: string | null;
  created_at: string;
}

export async function listTasks(filters: TaskFilters): Promise<Page<Task>> {
  const { data } = await apiClient.get<Page<Task>>("/tasks", { params: filters });
  return data;
}

export async function getTask(taskId: string): Promise<Task> {
  const { data } = await apiClient.get<Task>(`/tasks/${taskId}`);
  return data;
}

export interface TaskCreatePayload {
  title: string;
  description?: string | null;
  site_id: string;
  priority: TaskPriority;
  due_at?: string | null;
  estimated_minutes?: number | null;
  assignee_ids: string[];
  checklist_labels: string[];
}

export async function createTask(payload: TaskCreatePayload): Promise<Task> {
  const { data } = await apiClient.post<Task>("/tasks", payload);
  return data;
}

export async function updateTask(
  taskId: string,
  payload: Partial<TaskCreatePayload> & { checklist_labels?: string[] }
): Promise<Task> {
  const { data } = await apiClient.patch<Task>(`/tasks/${taskId}`, payload);
  return data;
}

export async function changeTaskStatus(
  taskId: string,
  payload: { status: TaskStatus; comment?: string | null; postponed_until?: string | null }
): Promise<Task> {
  const { data } = await apiClient.put<Task>(`/tasks/${taskId}/status`, payload);
  return data;
}

export async function setTaskAssignees(taskId: string, assigneeIds: string[]): Promise<Task> {
  const { data } = await apiClient.put<Task>(`/tasks/${taskId}/assignees`, {
    assignee_ids: assigneeIds,
  });
  return data;
}

export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete(`/tasks/${taskId}`);
}

export async function listTaskComments(taskId: string): Promise<TaskComment[]> {
  const { data } = await apiClient.get<TaskComment[]>(`/tasks/${taskId}/comments`);
  return data;
}

export async function addTaskComment(taskId: string, body: string): Promise<TaskComment> {
  const { data } = await apiClient.post<TaskComment>(`/tasks/${taskId}/comments`, { body });
  return data;
}

export async function toggleChecklistItem(
  taskId: string,
  itemId: string,
  isDone: boolean
): Promise<Task> {
  const { data } = await apiClient.put<Task>(`/tasks/${taskId}/checklist/${itemId}`, {
    is_done: isDone,
  });
  return data;
}

export async function listTaskHistory(taskId: string): Promise<TaskHistoryEntry[]> {
  const { data } = await apiClient.get<TaskHistoryEntry[]>(`/tasks/${taskId}/history`);
  return data;
}

export async function listTaskDependencies(taskId: string): Promise<string[]> {
  const { data } = await apiClient.get<string[]>(`/tasks/${taskId}/dependencies`);
  return data;
}

export async function addTaskDependency(taskId: string, dependsOnTaskId: string): Promise<void> {
  await apiClient.post(`/tasks/${taskId}/dependencies`, { depends_on_task_id: dependsOnTaskId });
}

export async function removeTaskDependency(
  taskId: string,
  dependsOnTaskId: string
): Promise<void> {
  await apiClient.delete(`/tasks/${taskId}/dependencies/${dependsOnTaskId}`);
}

export async function listTaskAttachments(taskId: string): Promise<Attachment[]> {
  const { data } = await apiClient.get<Attachment[]>(`/tasks/${taskId}/attachments`);
  return data;
}

export async function uploadTaskAttachment(taskId: string, file: File): Promise<Attachment> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await apiClient.post<Attachment>(`/tasks/${taskId}/attachments`, form);
  return data;
}

export async function deleteTaskAttachment(taskId: string, attachmentId: string): Promise<void> {
  await apiClient.delete(`/tasks/${taskId}/attachments/${attachmentId}`);
}

export function taskAttachmentUrl(taskId: string, attachmentId: string): string {
  return `${import.meta.env.VITE_API_BASE_URL}/tasks/${taskId}/attachments/${attachmentId}/download`;
}

// -------------------------------------------------------------- modeles

export interface TaskTemplate {
  id: string;
  name: string;
  description: string | null;
  default_priority: TaskPriority;
  site_id: string;
  rrule: string | null;
  estimated_minutes: number | null;
  checklist_labels: string[] | null;
  default_assignee_ids: string[] | null;
  is_active: boolean;
  last_generated_at: string | null;
  created_at: string;
}

export async function listTaskTemplates(): Promise<TaskTemplate[]> {
  const { data } = await apiClient.get<TaskTemplate[]>("/task-templates");
  return data;
}

export async function createTaskTemplate(payload: {
  name: string;
  description?: string | null;
  site_id: string;
  default_priority: TaskPriority;
  rrule?: string | null;
  estimated_minutes?: number | null;
  checklist_labels: string[];
  default_assignee_ids: string[];
}): Promise<TaskTemplate> {
  const { data } = await apiClient.post<TaskTemplate>("/task-templates", payload);
  return data;
}

export async function deleteTaskTemplate(templateId: string): Promise<void> {
  await apiClient.delete(`/task-templates/${templateId}`);
}

export async function instantiateTemplate(
  templateId: string,
  dueAt: string | null
): Promise<Task> {
  const { data } = await apiClient.post<Task>(
    `/task-templates/${templateId}/instantiate`,
    null,
    { params: dueAt ? { due_at: dueAt } : {} }
  );
  return data;
}
