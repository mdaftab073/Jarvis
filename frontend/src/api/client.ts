// Single HTTP client: base URL, bearer auth, envelope unwrapping, typed errors,
// single-flight refresh-token rotation. Never logs tokens.
export const API_BASE = ((import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in?: number;
}

// Session-storage choice: access token lives in memory only; the refresh token is kept in
// sessionStorage so a page reload restores the session (cleared when the tab closes).
// Trade-off: a browser-readable refresh token is exposed to XSS. No tokens are ever logged.
const RK = 'jarvis.refresh';
let access: string | null = null;
let refresh: string | null = safeGet();
let onAuthLost: (() => void) | null = null;

function safeGet() {
  try { return sessionStorage.getItem(RK); } catch { return null; }
}
export function setAuthLostHandler(fn: (() => void) | null) { onAuthLost = fn; }
export function setTokens(t: Tokens | null) {
  access = t?.access_token ?? null;
  refresh = t?.refresh_token ?? null;
  try {
    if (refresh) sessionStorage.setItem(RK, refresh); else sessionStorage.removeItem(RK);
  } catch { /* storage unavailable */ }
}
export const hasRefreshToken = () => !!refresh;
export const getRefreshToken = () => refresh;

const FALLBACK = 'Something went wrong. Check your connection and try again.';

async function parse(res: Response): Promise<any> {
  if (res.status === 204) return null;
  let json: any = null;
  try { json = await res.json(); } catch { /* non-JSON */ }
  if (!res.ok || json?.success === false) {
    const e = json?.error;
    let message: string = e?.message || '';
    if (!message && Array.isArray(json?.detail)) {
      message = json.detail.map((d: any) => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ');
    }
    throw new ApiError(res.status, e?.code || `http_${res.status}`, message || statusMessage(res.status));
  }
  return json && typeof json === 'object' && 'data' in json ? json.data : json;
}

function statusMessage(s: number) {
  switch (s) {
    case 401: return 'Your session has expired. Sign in again.';
    case 403: return "You don't have access to this.";
    case 404: return 'We couldn’t find that.';
    case 409: return 'That conflicts with existing data.';
    case 413: return 'The file is too large.';
    case 422: return 'Some fields are invalid. Check them and try again.';
    case 429: return 'Too many requests. Wait a moment and try again.';
    case 503: return 'A backend service is unavailable. Try again shortly.';
    default: return FALLBACK;
  }
}

let refreshing: Promise<any> | null = null;
/** Single-flight refresh: concurrent callers share one request (the token is single-use). */
export function refreshSession(): Promise<any> {
  if (!refresh) return Promise.reject(new ApiError(401, 'no_refresh_token', statusMessage(401)));
  if (!refreshing) {
    refreshing = fetch(API_BASE + '/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
      .then(parse)
      .then((data) => { setTokens(data.tokens); return data; })
      .catch((err) => { setTokens(null); throw err instanceof ApiError ? err : new ApiError(0, 'network_error', FALLBACK); })
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

export interface Opts {
  method?: string;
  body?: unknown;
  form?: FormData;
  query?: Record<string, unknown>;
  signal?: AbortSignal;
  auth?: boolean;
  timeoutMs?: number;
}

function qs(q?: Record<string, unknown>) {
  if (!q) return '';
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : '';
}

async function send(path: string, o: Opts): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), o.timeoutMs ?? 60_000);
  o.signal?.addEventListener('abort', () => ctrl.abort());
  const headers: Record<string, string> = {};
  if (o.auth !== false && access) headers.Authorization = `Bearer ${access}`;
  let body: BodyInit | undefined;
  if (o.form) body = o.form; // browser sets multipart boundary
  else if (o.body !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(o.body); }
  try {
    return await fetch(API_BASE + path + qs(o.query), { method: o.method || 'GET', headers, body, signal: ctrl.signal });
  } catch (e: any) {
    if (e?.name === 'AbortError' && o.signal?.aborted) throw e;
    throw new ApiError(0, 'network_error', e?.name === 'AbortError' ? 'The request timed out. Try again.' : FALLBACK);
  } finally {
    clearTimeout(timer);
  }
}

export async function api<T = any>(path: string, o: Opts = {}): Promise<T> {
  let res = await send(path, o);
  if (res.status === 401 && o.auth !== false && refresh) {
    try {
      await refreshSession();
    } catch (e) {
      onAuthLost?.();
      throw e;
    }
    res = await send(path, o); // retry once
    if (res.status === 401) { setTokens(null); onAuthLost?.(); }
  }
  return parse(res);
}

/** Find the list inside a response whose inner shape isn't frozen. */
export function asList(d: any): any[] {
  if (Array.isArray(d)) return d;
  if (d && typeof d === 'object') {
    for (const k of ['items', 'results', 'records', 'sessions', 'messages', 'notifications', 'tasks', 'events', 'decks', 'cards', 'materials', 'subjects', 'courses', 'topics', 'questions', 'data']) {
      if (Array.isArray(d[k])) return d[k];
    }
    for (const v of Object.values(d)) if (Array.isArray(v)) return v;
  }
  return [];
}

export const idOf = (o: any): number | string | undefined =>
  o?.id ?? o?.session_id ?? o?.plan_id ?? o?.quiz_id ?? o?.deck_id;
