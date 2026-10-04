import { createContext, useCallback, useContext, useState, ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '../api/client';

export function useGet<T = any>(path: string | null, query?: Record<string, unknown>, opts: { refetchInterval?: any; enabled?: boolean } = {}) {
  return useQuery<T, ApiError>({
    queryKey: [path, query],
    queryFn: ({ signal }) => api<T>(path!, { query, signal }),
    enabled: !!path && opts.enabled !== false,
    refetchInterval: opts.refetchInterval,
  });
}

// ---- toasts ----
type Toast = { id: number; kind: 'ok' | 'err'; text: string };
const ToastCtx = createContext<(kind: Toast['kind'], text: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [list, setList] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast['kind'], text: string) => {
    const id = Date.now() + Math.random();
    setList((l) => [...l, { id, kind, text }]);
    setTimeout(() => setList((l) => l.filter((t) => t.id !== id)), 5000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {list.map((t) => <div key={t.id} className={`toast ${t.kind}`}>{t.text}</div>)}
      </div>
    </ToastCtx.Provider>
  );
}

/** Mutation with success/error toasts. Invalidates all queries whose key path starts with any prefix. */
export function useAct<V = any, R = any>(
  fn: (v: V) => Promise<R>,
  o: { ok?: string; invalidate?: string[]; onSuccess?: (r: R) => void } = {},
) {
  const qc = useQueryClient();
  const toast = useToast();
  return useMutation<R, ApiError, V>({
    mutationFn: fn,
    onSuccess: (r) => {
      if (o.ok) toast('ok', o.ok);
      o.invalidate?.forEach((p) => qc.invalidateQueries({ predicate: (q) => String(q.queryKey[0] ?? '').startsWith(p) }));
      o.onSuccess?.(r);
    },
    onError: (e) => toast('err', e.message),
  });
}
