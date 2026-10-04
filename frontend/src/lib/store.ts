import { useState } from 'react';
import { useStudentId } from '../auth/AuthContext';

/** localStorage value scoped to the signed-in student (several people can share one browser). */
export function useStored(key: string) {
  const sid = useStudentId();
  const k = `jarvis.${sid}.${key}`;
  const [v, setV] = useState<string | null>(() => localStorage.getItem(k));
  const set = (x: string | null) => {
    setV(x);
    if (x) localStorage.setItem(k, x); else localStorage.removeItem(k);
  };
  return [v, set] as const;
}
