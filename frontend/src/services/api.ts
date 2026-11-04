import type { Conversation, Memory, Message, Profile } from "../types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{status:string;ollama:string;pending_background_jobs:number}>("/health"),
  conversations: (search = "") => request<Conversation[]>(`/api/conversations${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  createConversation: () => request<Conversation>("/api/conversations", { method: "POST", body: JSON.stringify({ title: "New chat" }) }),
  deleteConversation: (id: string) => request(`/api/conversations/${id}`, { method: "DELETE" }),
  messages: (id: string) => request<Message[]>(`/api/conversations/${id}/messages`),
  memories: (status?: string) => request<Memory[]>(`/api/memories${status ? `?status=${status}` : ""}`),
  memoryHistory: (id: number) => request<Array<{id:number;action:string;old_content:string|null;new_content:string|null;created_at:string}>>(`/api/memories/${id}/history`),
  approveMemory: (id: number) => request(`/api/memories/${id}/approve`, { method: "POST" }),
  archiveMemory: (id: number) => request(`/api/memories/${id}/archive`, { method: "POST" }),
  deleteMemory: (id: number) => request(`/api/memories/${id}`, { method: "DELETE" }),
  updateMemory: (id: number, data: Partial<Memory>) => request(`/api/memories/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  createMemory: (data: Partial<Memory>) => request("/api/memories", { method: "POST", body: JSON.stringify(data) }),
  profile: () => request<{profile:Profile;updated_at:string}>("/api/profile"),
  updateProfile: (profile: Profile) => request("/api/profile", { method: "PATCH", body: JSON.stringify(profile) }),
  settings: () => request<Record<string, unknown>>("/api/settings"),
  updateSettings: (values: Record<string, unknown>) => request("/api/settings", { method: "PATCH", body: JSON.stringify({ values }) })
};

export async function streamChat(
  conversationId: string,
  message: string,
  onToken: (token: string) => void
): Promise<void> {
  const response = await fetch("/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message })
  });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Could not start response stream");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const event of events) {
      const line = event.split("\n").find((part) => part.startsWith("data: "));
      if (!line) continue;
      const payload = JSON.parse(line.slice(6));
      if (payload.token) onToken(payload.token);
      if (payload.error) throw new Error(payload.error);
    }
  }
}
