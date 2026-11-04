import { create } from "zustand";
import type { Conversation, Message } from "./types";

interface ChatState {
  conversations: Conversation[];
  activeId: string | null;
  messages: Message[];
  setConversations: (items: Conversation[]) => void;
  setActiveId: (id: string | null) => void;
  setMessages: (items: Message[]) => void;
  appendMessage: (item: Message) => void;
  updateLastAssistant: (content: string) => void;
}
export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  activeId: null,
  messages: [],
  setConversations: (conversations) => set({ conversations }),
  setActiveId: (activeId) => set({ activeId }),
  setMessages: (messages) => set({ messages }),
  appendMessage: (item) => set((state) => ({ messages: [...state.messages, item] })),
  updateLastAssistant: (content) => set((state) => {
    const messages = [...state.messages];
    const last = messages[messages.length - 1];
    if (last?.role === "assistant") messages[messages.length - 1] = { ...last, content };
    return { messages };
  })
}));
