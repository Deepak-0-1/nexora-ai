import { useState } from "react";
import { Brain, MessageSquare, Plus, Search, Settings, Trash2, X } from "lucide-react";
import type { Conversation } from "../types";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onSearch: (q: string) => void;
  page: string;
  setPage: (page: string) => void;
}
export default function Sidebar(p: Props) {
  const [query, setQuery] = useState("");
  return <aside className="flex h-full w-[278px] shrink-0 flex-col border-r border-line bg-[#F8F9FB]">
    <div className="flex h-[68px] items-center justify-between px-5">
      <div className="flex items-center gap-2.5">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-[#27364F] text-white"><Brain size={19}/></div>
        <div><div className="font-display text-[15px] font-bold text-ink">Personal AI</div><div className="text-[11px] text-muted">Local workspace</div></div>
      </div>
    </div>
    <div className="px-3 pb-3">
      <button onClick={p.onNew} className="flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-[#344C73] text-sm font-semibold text-white shadow-sm transition hover:bg-[#293E60]">
        <Plus size={16}/> New conversation
      </button>
    </div>
    <div className="px-3 pb-2">
      <div className="relative">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"/>
        <input value={query} onChange={(e)=>{setQuery(e.target.value);p.onSearch(e.target.value)}} placeholder="Search conversations" className="h-9 w-full rounded-lg border border-line bg-white pl-9 pr-8 text-xs outline-none focus:border-[#9BAECD]"/>
        {query && <button onClick={()=>{setQuery("");p.onSearch("")}} className="absolute right-2 top-2 text-muted"><X size={15}/></button>}
      </div>
    </div>
    <div className="px-4 pb-2 pt-3 text-[10px] font-bold uppercase tracking-[.13em] text-[#929AA8]">Recent conversations</div>
    <div className="min-h-0 flex-1 space-y-1 overflow-y-auto px-2">
      {p.conversations.map((c)=> <div key={c.id} className={`group flex items-center rounded-lg ${p.activeId===c.id?"bg-[#E9EDF4]":"hover:bg-[#EEF1F5]"}`}>
        <button onClick={()=>p.onSelect(c.id)} className="flex min-w-0 flex-1 items-center gap-2.5 px-3 py-2.5 text-left text-[12px] text-[#404958]">
          <MessageSquare size={14} className="shrink-0 text-[#8A94A3]"/>
          <span className="truncate">{c.title}</span>
        </button>
        <button onClick={()=>p.onDelete(c.id)} title="Delete conversation" className="mr-2 hidden rounded p-1 text-muted hover:bg-white hover:text-red-600 group-hover:block"><Trash2 size={13}/></button>
      </div>)}
      {!p.conversations.length && <p className="px-3 py-5 text-xs text-muted">No conversations found.</p>}
    </div>
    <div className="space-y-1 border-t border-line p-3">
      <button onClick={()=>p.setPage("memory")} className={`nav-button ${p.page==="memory"?"nav-active":""}`}><Brain size={16}/><span>Memory & personalization</span></button>
      <button onClick={()=>p.setPage("settings")} className={`nav-button ${p.page==="settings"?"nav-active":""}`}><Settings size={16}/><span>Settings</span></button>
      <div className="mt-3 flex items-center gap-2 rounded-xl bg-white px-3 py-2.5">
        <div className="grid h-8 w-8 place-items-center rounded-full bg-[#E6EBF3] text-xs font-bold text-[#405778]">U</div>
        <div><div className="text-xs font-semibold text-ink">Personal workspace</div><div className="text-[10px] text-muted">Local · Single user</div></div>
        <span className="ml-auto h-2 w-2 rounded-full bg-emerald-500"/>
      </div>
    </div>
  </aside>;
}
