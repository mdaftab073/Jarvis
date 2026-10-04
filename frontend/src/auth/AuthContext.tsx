import { createContext, useCallback, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, getRefreshToken, hasRefreshToken, refreshSession, setAuthLostHandler, setTokens } from '../api/client';

export interface Student { id: number; email: string; full_name?: string; profile_picture?: string; is_verified?: boolean }
type Status = 'loading' | 'authed' | 'anon';
interface Ctx { student: Student | null; status: Status; login: (idToken: string) => Promise<void>; logout: () => Promise<void> }

const AuthCtx = createContext<Ctx>(null as any);
export const useAuth = () => useContext(AuthCtx);
/** The signed-in student's ID. All student-scoped calls bind to this — never to user input. */
export const useStudentId = () => useAuth().student!.id;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [student, setStudent] = useState<Student | null>(null);
  const [status, setStatus] = useState<Status>('loading');
  const qc = useQueryClient();

  const clear = useCallback(() => {
    setTokens(null);
    setStudent(null);
    setStatus('anon');
    qc.clear();
  }, [qc]);

  useEffect(() => {
    setAuthLostHandler(clear);
    return () => setAuthLostHandler(null);
  }, [clear]);

  // Restore session: rotate the stored refresh token (single-flight, safe under StrictMode),
  // then verify with /api/auth/me.
  useEffect(() => {
    let live = true;
    (async () => {
      if (!hasRefreshToken()) { setStatus('anon'); return; }
      try {
        const data = await refreshSession();
        const me = await api('/api/auth/me');
        if (live) { setStudent(me?.student ?? data.student); setStatus('authed'); }
      } catch {
        if (live) clear();
      }
    })();
    return () => { live = false; };
  }, [clear]);

  const login = useCallback(async (idToken: string) => {
    const data = await api('/api/auth/google', { method: 'POST', body: { id_token: idToken }, auth: false });
    setTokens(data.tokens);
    setStudent(data.student);
    setStatus('authed');
  }, []);

  const logout = useCallback(async () => {
    const rt = getRefreshToken();
    try { await api('/api/auth/logout', { method: 'POST', body: { refresh_token: rt } }); } catch { /* clear regardless */ }
    clear();
  }, [clear]);

  const value = useMemo(() => ({ student, status, login, logout }), [student, status, login, logout]);
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
