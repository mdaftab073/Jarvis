import { FormEvent, ReactNode, useEffect, useState } from 'react';
import { api, ApiError, asList } from '../api/client';
import { useSubject } from '../auth/SubjectContext';
import { useAct, useGet } from '../lib/hooks';
import { toIso } from '../lib/format';

export const Spinner = ({ label = 'Loading…' }: { label?: string }) => (
  <div className="spinner" role="status"><i />{label}</div>
);
export const Empty = ({ children }: { children: ReactNode }) => <p className="empty">{children}</p>;
export const ErrorNote = ({ error, retry }: { error: ApiError | Error; retry?: () => void }) => (
  <div className="errnote" role="alert">
    <span>{error.message}</span>
    {retry && <button className="btn small" onClick={retry}>Retry</button>}
  </div>
);
export const Chip = ({ children, tone = '' }: { children: ReactNode; tone?: string }) => <span className={`chip ${tone}`}>{children}</span>;
export const Bar = ({ value }: { value: number | null }) => (
  <div className="bar" role="progressbar" aria-valuenow={value ?? 0} aria-valuemin={0} aria-valuemax={100}><i style={{ width: `${Math.max(0, Math.min(100, value ?? 0))}%` }} /></div>
);
export const Stat = ({ label, value }: { label: string; value: ReactNode }) => (
  <div className="stat"><span className="muted">{label}</span><b>{value}</b></div>
);
export function Trend({ values }: { values: number[] }) {
  if (values.length < 2) return <p className="muted">Not enough data for a trend yet.</p>;
  const max = Math.max(...values, 1), min = Math.min(...values, 0), r = max - min || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * 100},${28 - ((v - min) / r) * 26}`).join(' ');
  return <svg className="trend" viewBox="0 0 100 30" preserveAspectRatio="none" role="img" aria-label={`Trend over ${values.length} points, latest ${values[values.length - 1]}`}><polyline points={pts} fill="none" stroke="currentColor" strokeWidth="1.5" vectorEffect="non-scaling-stroke" /></svg>;
}

export function Card({ title, actions, children, className = '' }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && <header className="card-h">{title && <h2>{title}</h2>}<div className="row">{actions}</div></header>}
      {children}
    </section>
  );
}
export function PageHead({ title, sub, actions }: { title: string; sub?: string; actions?: ReactNode }) {
  return <div className="pagehead"><div><h1>{title}</h1>{sub && <p className="muted">{sub}</p>}</div><div className="row">{actions}</div></div>;
}

export function Async<T>({ q, empty, children }: { q: { isLoading: boolean; error: any; data: T | undefined; refetch: () => any }; empty?: string; children: (d: T) => ReactNode }) {
  if (q.isLoading) return <Spinner />;
  if (q.error) return <ErrorNote error={q.error} retry={() => q.refetch()} />;
  const d = q.data;
  const isEmpty = d == null || (Array.isArray(d) && !d.length) || (typeof d === 'object' && !Array.isArray(d) && !Object.keys(d as object).length);
  if (isEmpty) return <Empty>{empty ?? 'Nothing here yet.'}</Empty>;
  return <>{children(d as T)}</>;
}

export function Tabs({ tabs, value, onChange }: { tabs: [string, string][]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map(([k, label]) => (
        <button key={k} role="tab" aria-selected={value === k} className={value === k ? 'on' : ''} onClick={() => onChange(k)}>{label}</button>
      ))}
    </div>
  );
}

const human = (k: string) => k.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
const isoRe = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/;
function scalar(v: any): string {
  if (v === null || v === undefined || v === '') return '—';
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  if (typeof v === 'string' && isoRe.test(v)) { const d = new Date(v); if (!isNaN(+d)) return d.toLocaleString(); }
  return String(v);
}
/** Safe fallback renderer for payloads that aren't worth a bespoke layout. React escapes all text. */
export function DataView({ data, depth = 0 }: { data: any; depth?: number }) {
  if (data === null || data === undefined || typeof data !== 'object') return <span>{scalar(data)}</span>;
  if (Array.isArray(data)) {
    if (!data.length) return <span className="muted">None</span>;
    if (data.every((x) => x === null || typeof x !== 'object')) return <ul className="plain">{data.map((x, i) => <li key={i}>{scalar(x)}</li>)}</ul>;
    return <div className="stack">{data.map((x, i) => <div className="item" key={i}><DataView data={x} depth={depth + 1} /></div>)}</div>;
  }
  if (depth > 3) return <code>{JSON.stringify(data)}</code>;
  return <dl className="kv">{Object.entries(data).map(([k, v]) => <div key={k}><dt>{human(k)}</dt><dd><DataView data={v} depth={depth + 1} /></dd></div>)}</dl>;
}

// ---------- forms ----------
export interface FieldDef {
  name: string; label: string;
  type?: 'text' | 'number' | 'date' | 'datetime-local' | 'textarea' | 'select' | 'subject' | 'subjects';
  options?: string[]; required?: boolean; placeholder?: string; default?: string; min?: number; max?: number;
}

function SubjectSelect({ value, onChange, required }: { value: string; onChange: (v: string) => void; required?: boolean }) {
  const { subjectId } = useSubject();
  const q = useGet('/api/subjects');
  useEffect(() => { if (!value && subjectId) onChange(String(subjectId)); /* default to the selected subject */ // eslint-disable-next-line
  }, [subjectId]);
  return (
    <select value={value} required={required} onChange={(e) => onChange(e.target.value)}>
      <option value="">{q.isLoading ? 'Loading…' : 'Select a subject'}</option>
      {asList(q.data).map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
    </select>
  );
}
function SubjectChecks({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const q = useGet('/api/subjects');
  const on = new Set(value.split(',').filter(Boolean));
  const toggle = (id: string) => { on.has(id) ? on.delete(id) : on.add(id); onChange([...on].join(',')); };
  const list = asList(q.data);
  if (!list.length) return <span className="muted">No subjects yet.</span>;
  return <div className="checks">{list.map((s: any) => (
    <label key={s.id} className="check"><input type="checkbox" checked={on.has(String(s.id))} onChange={() => toggle(String(s.id))} />{s.name}</label>
  ))}</div>;
}

export function FormFields({ fields, values, set }: { fields: FieldDef[]; values: Record<string, string>; set: (n: string, v: string) => void }) {
  return (
    <>
      {fields.map((f) => (
        <label className="field" key={f.name}>
          <span>{f.label}{f.required ? ' *' : ''}</span>
          {f.type === 'textarea' ? (
            <textarea rows={3} value={values[f.name] ?? ''} required={f.required} placeholder={f.placeholder} onChange={(e) => set(f.name, e.target.value)} />
          ) : f.type === 'select' ? (
            <select value={values[f.name] ?? ''} required={f.required} onChange={(e) => set(f.name, e.target.value)}>
              <option value="">{f.required ? 'Select…' : 'Not set'}</option>
              {f.options!.map((o) => <option key={o}>{o}</option>)}
            </select>
          ) : f.type === 'subject' ? (
            <SubjectSelect value={values[f.name] ?? ''} required={f.required} onChange={(v) => set(f.name, v)} />
          ) : f.type === 'subjects' ? (
            <SubjectChecks value={values[f.name] ?? ''} onChange={(v) => set(f.name, v)} />
          ) : (
            <input type={f.type ?? 'text'} inputMode={f.type === 'number' ? 'decimal' : undefined} step={f.type === 'number' ? 'any' : undefined} min={f.min} max={f.max}
              value={values[f.name] ?? ''} required={f.required} placeholder={f.placeholder} onChange={(e) => set(f.name, e.target.value)} />
          )}
        </label>
      ))}
    </>
  );
}

/** Build a request body: numbers coerced, local datetimes → ISO, blanks omitted. */
export function bodyFrom(fields: FieldDef[], v: Record<string, string>, extra: Record<string, unknown> = {}) {
  const b: Record<string, unknown> = { ...extra };
  for (const f of fields) {
    const raw = v[f.name];
    if (raw === undefined || raw === '') continue;
    b[f.name] = f.type === 'number' || f.type === 'subject' ? Number(raw)
      : f.type === 'subjects' ? raw.split(',').filter(Boolean).map(Number)
      : f.type === 'datetime-local' ? toIso(raw) : raw;
  }
  return b;
}

const defaultsOf = (fields: FieldDef[]) => Object.fromEntries(fields.filter((f) => f.default !== undefined).map((f) => [f.name, f.default!]));

export function CreateForm(p: {
  path: string; method?: string; fields: FieldDef[]; extra?: Record<string, unknown>; shape?: (b: any) => any;
  invalidate?: string[]; ok?: string; submit?: string; onDone?: (r: any) => void; timeoutMs?: number;
}) {
  const [vals, setVals] = useState<Record<string, string>>(() => defaultsOf(p.fields));
  const m = useAct(() => {
    let b: any = bodyFrom(p.fields, vals, p.extra);
    if (p.shape) b = p.shape(b);
    return api(p.path, { method: p.method ?? 'POST', body: b, timeoutMs: p.timeoutMs });
  }, {
    ok: p.ok ?? 'Saved.',
    invalidate: [...(p.invalidate ?? []), '/api/dashboard', '/api/analytics'],
    onSuccess: (r) => { setVals(defaultsOf(p.fields)); p.onDone?.(r); },
  });
  return (
    <form className="stack" onSubmit={(e: FormEvent) => { e.preventDefault(); m.mutate(undefined as any); }}>
      <FormFields fields={p.fields} values={vals} set={(n, v) => setVals((s) => ({ ...s, [n]: v }))} />
      <button className="btn primary" disabled={m.isPending}>{m.isPending ? 'Working…' : p.submit ?? 'Save'}</button>
    </form>
  );
}

/** Edit a record loaded from `path` and save it back with PUT. */
export function EditForm({ path, fields, title }: { path: string; fields: FieldDef[]; title: string }) {
  const q = useGet(path);
  const [vals, setVals] = useState<Record<string, string>>({});
  useEffect(() => {
    if (q.data && typeof q.data === 'object') setVals(Object.fromEntries(fields.map((f) => [f.name, q.data[f.name] == null ? '' : String(q.data[f.name])])));
    // eslint-disable-next-line
  }, [q.data]);
  const save = useAct(() => api(path, { method: 'PUT', body: bodyFrom(fields, vals) }), { ok: 'Saved.', invalidate: [path.split('/').slice(0, 3).join('/'), '/api/dashboard', '/api/profile'] });
  return (
    <Card title={title}>
      {q.isLoading ? <Spinner /> : q.error ? <ErrorNote error={q.error} retry={() => q.refetch()} /> : (
        <form className="stack" onSubmit={(e) => { e.preventDefault(); save.mutate(undefined as any); }}>
          <FormFields fields={fields} values={vals} set={(n, v) => setVals((s) => ({ ...s, [n]: v }))} />
          <button className="btn primary" disabled={save.isPending}>{save.isPending ? 'Saving…' : 'Save changes'}</button>
        </form>
      )}
    </Card>
  );
}

export interface RowAction {
  label: string; method: string; path: (item: any) => string;
  body?: unknown | ((item: any, input?: string) => unknown);
  prompt?: string; confirm?: string; hide?: (item: any) => boolean;
}

/** List + optional create form + per-row actions. */
export function ResourcePanel(p: {
  title: string; listPath: string; query?: Record<string, unknown>;
  createPath?: string; fields?: FieldDef[]; createExtra?: Record<string, unknown>; createLabel?: string; shape?: (b: any) => any;
  actions?: RowAction[]; empty?: string; createdOk?: string;
  items?: (d: any) => any[]; render?: (item: any) => ReactNode;
}) {
  const prefix = p.listPath.split('/').slice(0, 3).join('/');
  const q = useGet(p.listPath, p.query);
  const act = useAct(
    (a: { act: RowAction; item: any; input?: string }) => {
      const body = typeof a.act.body === 'function' ? (a.act.body as any)(a.item, a.input) : a.act.body;
      return api(a.act.path(a.item), { method: a.act.method, body });
    },
    { ok: 'Done.', invalidate: [prefix, '/api/dashboard', '/api/analytics'] },
  );
  const run = (a: RowAction, item: any) => {
    if (a.confirm && !window.confirm(a.confirm)) return;
    let input: string | undefined;
    if (a.prompt) { const r = window.prompt(a.prompt); if (r === null || r.trim() === '') return; input = r; }
    act.mutate({ act: a, item, input });
  };
  return (
    <div className="grid2">
      <Card title={p.title}>
        <Async q={q} empty={p.empty}>
          {(d) => {
            const list = (p.items ?? asList)(d);
            if (!list.length) return <Empty>{p.empty ?? 'Nothing here yet.'}</Empty>;
            return (
              <div className="stack">
                {list.map((item: any, i: number) => (
                  <div className="item" key={item.id ?? item.record?.id ?? i}>
                    {p.render ? p.render(item) : <DataView data={item} />}
                    {p.actions && (
                      <div className="row">
                        {p.actions.filter((a) => !a.hide?.(item)).map((a) => (
                          <button key={a.label} className={`btn small ${a.method === 'DELETE' ? 'danger' : ''}`} disabled={act.isPending} onClick={() => run(a, item)}>{a.label}</button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            );
          }}
        </Async>
      </Card>
      {p.createPath && p.fields && (
        <Card title={p.createLabel ?? 'Add new'}>
          <CreateForm path={p.createPath} fields={p.fields} extra={p.createExtra} shape={p.shape} invalidate={[prefix]} ok={p.createdOk} />
        </Card>
      )}
    </div>
  );
}

export function Fetched({ title, path, query, empty, render }: { title: string; path: string | null; query?: Record<string, unknown>; empty?: string; render?: (d: any) => ReactNode }) {
  const q = useGet(path, query);
  return <Card title={title}>{path ? <Async q={q} empty={empty}>{(d) => (render ? render(d) : <DataView data={d} />)}</Async> : <Empty>Choose a subject first.</Empty>}</Card>;
}
