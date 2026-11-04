import { useEffect, useState } from "react";
import { Brain, Check, Edit3, Plus, Archive, Trash2, UserRound, Save, X, RefreshCw, History } from "lucide-react";
import type { Memory, Profile } from "../types";
import { api } from "../services/api";

interface Props { notify:(s:string)=>void; }
export default function MemoryPage({notify}:Props) {
  const [memories,setMemories]=useState<Memory[]>([]);
  const [profile,setProfile]=useState<Profile>({});
  const [tab,setTab]=useState<"pending"|"active"|"archived"|"profile">("pending");
  const [editing,setEditing]=useState<number|null>(null);
  const [editText,setEditText]=useState("");
  const [newText,setNewText]=useState("");
  const [showAdd,setShowAdd]=useState(false);
  const [loading,setLoading]=useState(false);
  const [historyOpen,setHistoryOpen]=useState<number|null>(null);
  const [historyItems,setHistoryItems]=useState<Record<number,Array<{id:number;action:string;old_content:string|null;new_content:string|null;created_at:string}>>>({});
  async function load() {
    setLoading(true);
    try { const [m,p]=await Promise.all([api.memories(),api.profile()]); setMemories(m);setProfile(p.profile); }
    catch(e){notify(e instanceof Error?e.message:"Could not load memory")}
    finally{setLoading(false)}
  }
  useEffect(()=>{void load()},[]);
  async function act(fn:()=>Promise<unknown>, message:string){try{await fn();notify(message);await load()}catch(e){notify(e instanceof Error?e.message:"Action failed")}}
  const visible=memories.filter(m=>m.status===tab);
  return <div className="flex-1 overflow-y-auto bg-[#FCFCFD]">
    <div className="mx-auto max-w-[1000px] px-8 py-9">
      <div className="flex items-start justify-between">
        <div><div className="eyebrow">PERSONALIZATION</div><h1 className="page-title">Memory & profile</h1><p className="mt-2 text-sm text-muted">Review what your assistant remembers. Only approved memories are used in chat context.</p></div>
        <div className="flex gap-2"><button onClick={()=>void load()} className="secondary-button"><RefreshCw size={14}/> Refresh</button><button onClick={()=>setShowAdd(true)} className="primary-button"><Plus size={15}/> Add memory</button></div>
      </div>
      <div className="mt-7 flex flex-wrap gap-2 border-b border-line pb-3">
        {(["pending","active","archived","profile"] as const).map(t=><button key={t} onClick={()=>setTab(t)} className={`tab-button ${tab===t?"tab-active":""}`}>{t==="pending"?"Pending review":t==="active"?"Approved memories":t==="archived"?"Archived":"User profile"}{t==="pending"&&<span className="ml-2 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px]">{memories.filter(m=>m.status==="pending").length}</span>}</button>)}
      </div>
      {tab==="profile" ? <section className="mt-6 rounded-2xl border border-line bg-white p-6">
        <div className="mb-5 flex items-center gap-2"><UserRound size={18} className="text-accent"/><h2 className="section-title">User profile</h2></div>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Profession" value={String(profile.profession||"")} onChange={v=>setProfile({...profile,profession:v})}/>
          <Field label="Additional context" value={String(profile.additional_context||"")} onChange={v=>setProfile({...profile,additional_context:v})}/>
          <ListField label="Interests" values={profile.interests||[]} onChange={v=>setProfile({...profile,interests:v})}/>
          <ListField label="Goals" values={profile.goals||[]} onChange={v=>setProfile({...profile,goals:v})}/>
          <ListField label="Response preferences" values={profile.response_preferences||[]} onChange={v=>setProfile({...profile,response_preferences:v})}/>
        </div>
        <button onClick={()=>void act(()=>api.updateProfile(profile),"Profile saved")} className="primary-button mt-5"><Save size={15}/> Save profile</button>
      </section> : <div className="mt-6 space-y-3">
        {loading&&<p className="text-sm text-muted">Loading…</p>}
        {!loading&&!visible.length&&<div className="rounded-2xl border border-dashed border-[#D9DEE7] bg-white px-6 py-12 text-center"><Brain className="mx-auto text-[#9AA5B5]" size={25}/><p className="mt-3 text-sm font-semibold text-ink">{tab==="pending"?"No memories awaiting review":tab==="active"?"No approved memories yet":"No archived memories"}</p><p className="mt-1 text-xs text-muted">Memories extracted from conversations will appear here for review.</p></div>}
        {visible.map(m=><div key={m.id} className="rounded-xl border border-line bg-white p-4 shadow-[0_2px_8px_rgba(20,30,50,.02)]">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#EDF1F7] text-[#587096]"><Brain size={16}/></div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2"><span className="text-[11px] font-bold uppercase tracking-wide text-[#687487]">{m.memory_type}</span><span className="text-[#B1B8C3]">·</span><span className="text-[11px] text-muted">{m.category}</span>{m.conflict_with&&<span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">Possible conflict with #{m.conflict_with}</span>}</div>
              {editing===m.id?<textarea value={editText} onChange={e=>setEditText(e.target.value)} className="mt-2 w-full rounded-lg border border-line p-2 text-sm outline-none focus:border-accent"/>:<p className="mt-2 text-sm leading-6 text-[#394352]">{m.content}</p>}
              <div className="mt-3 flex flex-wrap items-center gap-3 text-[10px] text-[#929AA6]"><span>Confidence {(m.confidence*100).toFixed(0)}%</span><span>Importance {(m.importance*100).toFixed(0)}%</span><span>{m.user_approved?"User approved":"Awaiting approval"}</span><span>{new Date(m.updated_at).toLocaleDateString()}</span>{m.source_message_id&&<span>Source message #{m.source_message_id}</span>}{m.source_conversation_id&&<span>Conversation {m.source_conversation_id.slice(0,8)}</span>}</div>
              {historyOpen===m.id&&<div className="mt-3 rounded-lg bg-[#F6F8FA] p-3 text-xs">{(historyItems[m.id]||[]).length?(historyItems[m.id]||[]).map(h=><div key={h.id} className="border-b border-[#E6EAF0] py-2 last:border-0"><span className="font-semibold text-[#4C5C73]">{h.action}</span><span className="ml-2 text-muted">{new Date(h.created_at).toLocaleString()}</span>{h.old_content&&<p className="mt-1 text-muted">Before: {h.old_content}</p>}{h.new_content&&h.new_content!==h.old_content&&<p className="mt-1 text-[#394352]">After: {h.new_content}</p>}</div>):<span className="text-muted">No history records.</span>}</div>}
            </div>
            <div className="flex shrink-0 items-center gap-1">
              {editing===m.id ? <>
                <button title="Save edit" className="icon-button text-emerald-700" onClick={()=>void act(()=>api.updateMemory(m.id,{content:editText}),"Memory updated").then(()=>setEditing(null))}><Save size={15}/></button>
                <button title="Cancel" className="icon-button" onClick={()=>setEditing(null)}><X size={15}/></button>
              </>:<>
                <button title="View history" className="icon-button" onClick={async()=>{if(historyOpen===m.id){setHistoryOpen(null);return}try{const h=await api.memoryHistory(m.id);setHistoryItems({...historyItems,[m.id]:h});setHistoryOpen(m.id)}catch(e){notify(e instanceof Error?e.message:"Could not load memory history")}}}><History size={15}/></button>
                <button title="Edit memory" className="icon-button" onClick={()=>{setEditing(m.id);setEditText(m.content)}}><Edit3 size={15}/></button>
                {m.status==="pending"&&<button title={m.conflict_with?"Approve; ask whether to replace conflicting memory":"Approve"} className="icon-button text-emerald-700" onClick={()=>{const replace=!!m.conflict_with&&window.confirm(`This may conflict with memory #${m.conflict_with}. Replace and archive the older memory? Choose Cancel to keep both.`);void act(()=>fetch(`/api/memories/${m.id}/approve`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({replace_conflict:replace})}).then(async r=>{if(!r.ok)throw new Error((await r.json()).detail||"Approval failed");return r.json()}),"Memory approved")}}><Check size={16}/></button>}
                {m.status==="archived"&&<button title="Restore memory" className="icon-button text-emerald-700" onClick={()=>void act(()=>api.approveMemory(m.id),"Memory restored")}><Check size={16}/></button>}
                {m.status!=="archived"&&<button title="Archive" className="icon-button" onClick={()=>void act(()=>api.archiveMemory(m.id),"Memory archived")}><Archive size={15}/></button>}
                <button title="Delete" className="icon-button text-red-500" onClick={()=>void act(()=>api.deleteMemory(m.id),"Memory deleted")}><Trash2 size={15}/></button>
              </>}
            </div>
          </div>
        </div>)}
      </div>}
      {showAdd&&<div className="fixed inset-0 z-50 grid place-items-center bg-[#172033]/35 p-4">
        <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl">
          <div className="flex items-center justify-between"><h2 className="section-title">Add a memory</h2><button className="icon-button" onClick={()=>setShowAdd(false)}><X size={17}/></button></div>
          <label className="form-label mt-5">Memory text</label><textarea value={newText} onChange={e=>setNewText(e.target.value)} rows={3} className="form-input"/>
          <button disabled={!newText.trim()} className="primary-button mt-4" onClick={()=>void act(()=>api.createMemory({memory_type:"semantic",category:"general",content:newText,importance:.7,confidence:1}),"Memory added").then(()=>{setNewText("");setShowAdd(false);setTab("active")})}><Plus size={15}/> Save approved memory</button>
        </div>
      </div>}
    </div>
  </div>;
}
function Field({label,value,onChange}:{label:string;value:string;onChange:(v:string)=>void}){return <label className="block"><span className="form-label">{label}</span><input className="form-input" value={value} onChange={e=>onChange(e.target.value)}/></label>}
function ListField({label,values,onChange}:{label:string;values:string[];onChange:(v:string[])=>void}){return <label className="block"><span className="form-label">{label} <span className="font-normal text-muted">(comma separated)</span></span><input className="form-input" value={values.join(", ")} onChange={e=>onChange(e.target.value.split(",").map(x=>x.trim()).filter(Boolean))}/></label>}
