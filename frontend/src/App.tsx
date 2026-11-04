import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import ChatPage from "./components/ChatPage";
import MemoryPage from "./components/MemoryPage";
import SettingsPage from "./components/SettingsPage";
import { api } from "./services/api";
import { useChatStore } from "./store";

export default function App() {
  const [page,setPage]=useState("chat");
  const [notice,setNotice]=useState("");
  const conversations=useChatStore(s=>s.conversations);
  const activeId=useChatStore(s=>s.activeId);
  const messages=useChatStore(s=>s.messages);
  const setConversations=useChatStore(s=>s.setConversations);
  const setActiveId=useChatStore(s=>s.setActiveId);
  const setMessages=useChatStore(s=>s.setMessages);
  const [loading,setLoading]=useState(true);
  const notify=(message:string)=>{setNotice(message);window.setTimeout(()=>setNotice(""),3500)};
  async function loadConversations(search="") {
    const items=await api.conversations(search);setConversations(items);
    if(!activeId&&items.length){setActiveId(items[0].id)}
  }
  async function loadMessages(id:string) { setMessages(await api.messages(id)); }
  useEffect(()=>{void (async()=>{
    try {
      const items=await api.conversations();
      if(items.length){setConversations(items);setActiveId(items[0].id);}
      else {
        const created=await api.createConversation();
        setConversations([created]);
        setActiveId(created.id);
      }
    } catch(e) {
      notify(e instanceof Error?e.message:"Backend unavailable");
    } finally { setLoading(false); }
  })()},[]);
  useEffect(()=>{if(activeId)void loadMessages(activeId).catch(e=>notify(e instanceof Error?e.message:"Could not load conversation"))},[activeId]);
  async function newChat(){try{const c=await api.createConversation();await loadConversations();setActiveId(c.id);setMessages([]);setPage("chat")}catch(e){notify(e instanceof Error?e.message:"Could not create conversation")}}
  async function deleteChat(id:string){if(!window.confirm("Delete this conversation and its messages?"))return;try{await api.deleteConversation(id);const items=await api.conversations();setConversations(items);if(activeId===id){if(items.length){setActiveId(items[0].id)}else{const created=await api.createConversation();setConversations([created]);setActiveId(created.id)}setMessages([])}}catch(e){notify(e instanceof Error?e.message:"Delete failed")}}
  async function search(q:string){try{setConversations(await api.conversations(q))}catch(e){notify(e instanceof Error?e.message:"Search failed")}}
  return <div className="flex h-screen overflow-hidden bg-white text-ink">
    <Sidebar conversations={conversations} activeId={activeId} onSelect={id=>{setActiveId(id);setPage("chat")}} onNew={()=>void newChat()} onDelete={id=>void deleteChat(id)} onSearch={q=>void search(q)} page={page} setPage={setPage}/>
    {loading?<div className="grid flex-1 place-items-center text-sm text-muted">Connecting to local assistant…</div>:
      page==="chat"?<ChatPage conversationId={activeId} messages={messages} onMessages={setMessages} onRefresh={()=>void loadConversations()}/>:
      page==="memory"?<MemoryPage notify={notify}/>:
      <SettingsPage notify={notify}/>}
    {notice&&<div className="fixed bottom-5 right-5 z-50 rounded-xl bg-[#202A3A] px-4 py-3 text-xs font-medium text-white shadow-xl">{notice}</div>}
  </div>;
}
