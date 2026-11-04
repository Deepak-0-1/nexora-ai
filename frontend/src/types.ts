export type Role = "user" | "assistant";
export interface Conversation {
  id: string; title: string; created_at: string; updated_at: string;
}
export interface Message {
  id: number; role: Role; content: string; created_at: string;
}
export interface Memory {
  id: number;
  memory_type: "semantic" | "procedural" | "episodic";
  category: string;
  content: string;
  importance: number;
  confidence: number;
  status: "pending" | "active" | "archived" | "deleted";
  source_conversation_id?: string | null;
  source_message_id?: number | null;
  user_approved: number;
  created_at: string;
  updated_at: string;
  conflict_with?: number | null;
}
export interface Profile {
  profession?: string;
  interests?: string[];
  goals?: string[];
  response_preferences?: string[];
  additional_context?: string;
  [key: string]: unknown;
}
