import { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import { useGet } from '../lib/hooks';
import { asList } from '../api/client';
import { useAuth } from './AuthContext';

interface Ctx { subjectId: number | null; setSubjectId: (id: number | null) => void }
const C = createContext<Ctx>({ subjectId: null, setSubjectId: () => {} });
export const useSubject = () => useContext(C);

/** Shared subject selection (per student). Feeds materials, practice, flashcards, analytics. */
export function SubjectProvider({ children }: { children: ReactNode }) {
  const { student } = useAuth();
  const key = `jarvis.${student?.id ?? 'anon'}.subject`;
  const [subjectId, setId] = useState<number | null>(null);
  useEffect(() => {
    const v = localStorage.getItem(key);
    setId(v ? Number(v) : null);
  }, [key]);
  const setSubjectId = (id: number | null) => {
    setId(id);
    if (id) localStorage.setItem(key, String(id)); else localStorage.removeItem(key);
  };
  return <C.Provider value={{ subjectId, setSubjectId }}>{children}</C.Provider>;
}

/** id → subject name lookup from /api/subjects. */
export function useSubjectNames() {
  const q = useGet('/api/subjects');
  return useMemo(() => {
    const m = new Map<number, string>();
    asList(q.data).forEach((s: any) => m.set(s.id, s.name));
    return (id: any) => m.get(Number(id)) ?? (id ? `Subject ${id}` : '—');
  }, [q.data]);
}

export function SubjectPicker() {
  const { subjectId, setSubjectId } = useSubject();
  const q = useGet('/api/subjects');
  const subjects = asList(q.data);
  return (
    <label className="picker">
      <span className="sr-only">Subject</span>
      <select value={subjectId ?? ''} onChange={(e) => setSubjectId(e.target.value ? Number(e.target.value) : null)}>
        <option value="">{q.isLoading ? 'Loading subjects…' : subjects.length ? 'Choose a subject' : 'No subjects yet — add one in Courses'}</option>
        {subjects.map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
    </label>
  );
}
