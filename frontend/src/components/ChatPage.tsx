import { useEffect, useRef, useState } from "react";
import { ArrowUp, Sparkles, Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";
import { streamChat } from "../services/api";

interface Props {
  conversationId: string | null;
  messages: Message[];
  onMessages: (items: Message[]) => void;
  onRefresh: () => void;
}
export default function ChatPage({conversationId,messages,onMessages,onRefresh}:Props) {
  const [input,setInput] = useState("");
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(()=>{endRef.current?.scrollIntoView({behavior:"smooth"})},[messages]);
  async function send(text=input) {
    const value=text.trim();
    if(!value || !conversationId || busy) return;
    setInput(""); setError(""); setBusy(true);
    const userMessage:Message={id:Date.now(),role:"user",content:value,created_at:new Date().toISOString()};
    const assistantMessage:Message={id:Date.now()+1,role:"assistant",content:"",created_at:new Date().toISOString()};
    onMessages([...messages,userMessage,assistantMessage]);
    let answer="";
    try {
      await streamChat(conversationId,value,(token)=>{
        answer+=token;
        onMessages([...messages,userMessage,{...assistantMessage,content:answer}]);
      });
      onRefresh();
    } catch(e) {
      setError(e instanceof Error?e.message:"Response failed");
      onMessages([...messages,userMessage]);
    } finally { setBusy(false); }
  }
  return <main className="relative flex min-w-0 flex-1 flex-col bg-[#FCFCFD]">
    <header className="flex h-[68px] shrink-0 items-center justify-between border-b border-line px-7">
      <div><div className="text-sm font-semibold text-ink">Assistant</div><div className="mt-0.5 text-[11px] text-muted">phi4-mini:3.8b · Local inference</div></div>
      <div className="flex items-center gap-2 rounded-full border border-[#DDE8E0] bg-[#F4FAF6] px-3 py-1.5 text-[10px] font-semibold text-[#47785A]"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500"/> Local model</div>
    </header>
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto max-w-[850px] px-6 pb-10 pt-8">
        {!messages.length ? <div className="flex min-h-[62vh] flex-col items-center justify-center">
          <div className="mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-[#E9EEF6] text-[#49658F]"><Sparkles size={25}/></div>
          <h1 className="font-display text-[30px] font-bold tracking-[-.04em] text-[#252D3A]">How can I help?</h1>
          <p className="mt-2 text-sm text-[#858D9A]">A private assistant that learns your preferences over time.</p>
          <div className="mt-9 grid w-full max-w-[650px] grid-cols-2 gap-3">
            {[
              ["Explain a technical concept","Explain vector databases with a practical example."],
              ["Help with a project","Help me plan a reliable local AI application."],
              ["Write or review code","Help me debug a Python implementation."],
              ["Explore an idea","Suggest practical ways to use AI in my workflow."]
            ].map(([title,prompt])=><button key={title} onClick={()=>send(prompt)} className="rounded-xl border border-line bg-white p-4 text-left shadow-[0_2px_8px_rgba(20,30,50,.025)] transition hover:-translate-y-0.5 hover:border-[#C9D4E4] hover:shadow-soft"><div className="text-[13px] font-semibold text-[#394454]">{title}</div><div className="mt-1 text-xs leading-5 text-muted">{prompt}</div></button>)}
          </div>
        </div> : <div className="space-y-8">
          {messages.map((m)=> <article key={m.id} className={`flex gap-3 ${m.role==="user"?"justify-end":""}`}>
            {m.role==="assistant" && <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#E9EEF6] text-[#4C668F]"><Bot size={17}/></div>}
            <div className={`${m.role==="user"?"max-w-[78%] rounded-2xl rounded-br-md bg-[#F0F2F6] px-4 py-3 text-[#303846]":"min-w-0 max-w-[88%] flex-1 pt-1 text-[#303846]"}`}>
              {m.role==="assistant" ? <div className="markdown-body"><ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || (busy?"Thinking…":"")}</ReactMarkdown></div> : <div className="whitespace-pre-wrap text-[14px] leading-7">{m.content}</div>}
            </div>
            {m.role==="user" && <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-[#EDEFF2] text-[#697486]"><User size={16}/></div>}
          </article>)}
          {busy && <div className="ml-11 flex items-center gap-2 text-xs text-muted"><span className="typing-dot"/> Generating response</div>}
          <div ref={endRef}/>
        </div>}
        {error && <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</div>}
      </div>
    </div>
    <div className="shrink-0 px-5 pb-5 pt-3">
      <div className="mx-auto max-w-[850px]">
        <div className="rounded-2xl border border-[#DDE2EA] bg-white p-3 shadow-[0_8px_30px_rgba(26,39,61,.06)] focus-within:border-[#AAB9D0]">
          <textarea value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send()}}} rows={2} placeholder="Message your assistant..." className="max-h-36 min-h-[48px] w-full resize-y bg-transparent px-1 py-1 text-sm leading-6 text-ink outline-none placeholder:text-[#A0A7B2]" />
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-1 text-[#929AA6]"><span className="text-[10px]">Local conversation</span></div>
            <button disabled={!input.trim()||busy||!conversationId} onClick={()=>send()} className="grid h-9 w-9 place-items-center rounded-xl bg-[#344C73] text-white transition hover:bg-[#293E60] disabled:cursor-not-allowed disabled:bg-[#C8CED8]"><ArrowUp size={18}/></button>
          </div>
        </div>
        <p className="mt-2 text-center text-[10px] text-[#A1A7B1]">AI can make mistakes. Verify important information.</p>
      </div>
    </div>
  </main>;
}
