import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { api, asList } from '../api/client';
import { useStudentId } from '../auth/AuthContext';
import { Async, Empty, PageHead } from '../components/ui';
import { useAct, useGet } from '../lib/hooks';

export default function Chat() {
  const sid = useStudentId();
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState<string | null>(null);
  const [hist, setHist] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const sessions = useGet('/api/chat/sessions', { student_id: sid, limit: 50 });
  const msgs = useGet(sessionId ? `/api/chat/sessions/${sessionId}/messages` : null, { limit: 500, offset: 0 });
  const send = useAct(
    (message: string) => api('/api/chat', { method: 'POST', timeoutMs: 120_000, body: { student_id: sid, session_id: sessionId ?? undefined, message } }),
    { invalidate: ['/api/chat'], onSuccess: (r: any) => { setPending(null); if (r?.session_id) setSessionId(r.session_id); } },
  );
  const del = useAct((id: number) => api(`/api/chat/sessions/${id}`, { method: 'DELETE' }), {
    ok: 'Conversation deleted.', invalidate: ['/api/chat'], onSuccess: () => setSessionId(null),
  });
  const list = useMemo(() => [...asList(msgs.data)].sort((a, b) => +new Date(a.created_at) - +new Date(b.created_at)), [msgs.data]);
  useEffect(() => { end.current?.scrollIntoView({ block: 'end' }); }, [list.length, pending]);

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const m = draft.trim();
    if (!m || send.isPending) return;
    setDraft(''); setPending(m);
    send.mutate(m, { onError: () => { setPending(null); setDraft(m); } });
  };
  return (
    <div className="chatpage">
      <PageHead title="Tutor" sub="Ask anything about your courses. Conversations are saved."
        actions={<button className="btn small histbtn" onClick={() => setHist(!hist)}>{hist ? 'Hide history' : 'History'}</button>} />
      <div className="chatwrap">
        <aside className={`sessions card ${hist ? 'show' : ''}`}>
          <button className="btn primary" onClick={() => { setSessionId(null); setHist(false); }}>New chat</button>
          <Async q={sessions} empty="No conversations yet.">
            {(d) => <div className="stack">{asList(d).map((s: any) => (
              <div key={s.id} className={`sess ${sessionId === s.id ? 'on' : ''}`}>
                <button onClick={() => { setSessionId(s.id); setHist(false); }}>{s.title}</button>
                <button className="x" aria-label="Delete conversation" onClick={() => window.confirm('Delete this conversation?') && del.mutate(s.id)}>×</button>
              </div>
            ))}</div>}
          </Async>
        </aside>
        <section className="chat card">
          <div className="log" role="log" aria-live="polite">
            {!sessionId && !pending && <Empty>Start a conversation below.</Empty>}
            {sessionId && msgs.isLoading && <p className="muted">Loading messages…</p>}
            {msgs.error && <p className="errnote">{msgs.error.message}</p>}
            {list.map((m: any) => (
              <div key={m.id} className={`bubble ${m.role === 'user' ? 'user' : 'bot'}`}>
                <p>{m.content}</p>
                {m.role !== 'user' && (m.agent_name || m.tool_name) && <small className="muted">via {[m.agent_name, m.tool_name].filter(Boolean).join(' · ')}</small>}
              </div>
            ))}
            {pending && <div className="bubble user"><p>{pending}</p></div>}
            {send.isPending && <div className="bubble bot"><p className="muted">Thinking…</p></div>}
            <div ref={end} />
          </div>
          <form className="composer" onSubmit={submit}>
            <label className="sr-only" htmlFor="ask">Ask Jarvis</label>
            <textarea id="ask" rows={1} value={draft} placeholder="Ask Jarvis…" enterKeyHint="send" onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && window.matchMedia('(hover: hover)').matches) { e.preventDefault(); submit(); } }} />
            <button className="btn primary" disabled={send.isPending || !draft.trim()}>Send</button>
          </form>
        </section>
      </div>
    </div>
  );
}
