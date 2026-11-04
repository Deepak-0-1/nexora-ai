import { useEffect, useState } from "react";
import { Save, SlidersHorizontal, Cpu, Database } from "lucide-react";
import { api } from "../services/api";

interface Props { notify:(s:string)=>void; }
export default function SettingsPage({notify}:Props) {
  const [temperature,setTemperature]=useState(0.4);
  const [recent,setRecent]=useState(12);
  const [memoryCount,setMemoryCount]=useState(8);
  const [contextChars,setContextChars]=useState(18000);
  const [personalization,setPersonalization]=useState(true);
  const [health,setHealth]=useState<{status:string;ollama:string;pending_background_jobs:number}|null>(null);
  useEffect(()=>{void Promise.all([api.settings(),api.health()]).then(([s,h])=>{setTemperature(Number(s.temperature??.4));setRecent(Number(s.max_recent_messages??12));setMemoryCount(Number(s.max_context_memories??8));setContextChars(Number(s.max_context_chars??18000));setPersonalization(Boolean(s.personalization_enabled??true));setHealth(h)}).catch(e=>notify(e instanceof Error?e.message:"Could not load settings"))},[]);
  async function save(){try{await api.updateSettings({temperature,max_recent_messages:recent,max_context_memories:memoryCount,max_context_chars:contextChars,personalization_enabled:personalization});notify("Settings saved. Changes apply to the next message.")}catch(e){notify(e instanceof Error?e.message:"Save failed")}}
  return <div className="flex-1 overflow-y-auto bg-[#FCFCFD]"><div className="mx-auto max-w-[900px] px-8 py-9">
    <div className="eyebrow">CONFIGURATION</div><h1 className="page-title">Settings</h1><p className="mt-2 text-sm text-muted">Tune response behavior and inspect local service status.</p>
    <section className="mt-7 rounded-2xl border border-line bg-white p-6">
      <div className="flex items-center gap-2"><Cpu size={18} className="text-accent"/><h2 className="section-title">Model configuration</h2></div>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div><div className="form-label">Chat model</div><div className="rounded-lg bg-[#F5F6F8] px-3 py-2.5 text-sm text-[#4B5666]">phi4-mini:3.8b</div></div>
        <div><div className="form-label">Embedding model</div><div className="rounded-lg bg-[#F5F6F8] px-3 py-2.5 text-sm text-[#4B5666]">nomic-embed-text</div></div>
        <label><span className="form-label">Temperature: {temperature.toFixed(2)}</span><input type="range" min="0" max="1" step=".05" value={temperature} onChange={e=>setTemperature(Number(e.target.value))} className="w-full accent-[#4969A5]"/></label>
      </div>
    </section>
    <section className="mt-4 rounded-2xl border border-line bg-white p-6">
      <div className="flex items-center gap-2"><SlidersHorizontal size={18} className="text-accent"/><h2 className="section-title">Context management</h2></div>
      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <NumberField label="Recent messages" value={recent} min={2} max={30} onChange={setRecent}/>
        <NumberField label="Maximum retrieved memories" value={memoryCount} min={1} max={30} onChange={setMemoryCount}/>
        <NumberField label="Maximum context characters" value={contextChars} min={4000} max={50000} step={1000} onChange={setContextChars}/>
      </div>
    </section>
    <section className="mt-4 rounded-2xl border border-line bg-white p-6">
      <div className="flex items-center justify-between gap-4">
        <div><h2 className="section-title">Personalization</h2><p className="mt-1 text-xs text-muted">When disabled, saved profile and memories are excluded from prompts. Memories remain stored.</p></div>
        <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-[#4B5666]"><input type="checkbox" checked={personalization} onChange={e=>setPersonalization(e.target.checked)} className="h-4 w-4 accent-[#4969A5]"/> Enabled</label>
      </div>
    </section>
    <section className="mt-4 rounded-2xl border border-line bg-white p-6">
      <div className="flex items-center gap-2"><Database size={18} className="text-accent"/><h2 className="section-title">Local services</h2></div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-[#F6F8FA] p-4"><div className="text-xs text-muted">Backend status</div><div className="mt-1 text-sm font-semibold text-ink">{health?.status??"Checking..."}</div></div>
        <div className="rounded-xl bg-[#F6F8FA] p-4"><div className="text-xs text-muted">Ollama</div><div className="mt-1 truncate text-sm font-semibold text-ink">{health?.ollama??"Checking..."}</div></div>
        <div className="rounded-xl bg-[#F6F8FA] p-4"><div className="text-xs text-muted">Queued background jobs</div><div className="mt-1 text-sm font-semibold text-ink">{health?.pending_background_jobs??"—"}</div></div>
        <div className="rounded-xl bg-[#F6F8FA] p-4"><div className="text-xs text-muted">Storage</div><div className="mt-1 text-sm font-semibold text-ink">Local SQLite</div></div>
      </div>
    </section>
    <div className="mt-5 flex justify-end"><button onClick={()=>void save()} className="primary-button"><Save size={15}/> Save settings</button></div>
  </div></div>;
}
function NumberField({label,value,min,max,step=1,onChange}:{label:string;value:number;min:number;max:number;step?:number;onChange:(n:number)=>void}){return <label><span className="form-label">{label}</span><input className="form-input" type="number" min={min} max={max} step={step} value={value} onChange={e=>onChange(Number(e.target.value))}/></label>}
