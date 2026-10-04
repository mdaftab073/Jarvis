import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useStudentId } from '../auth/AuthContext';
import { useGet } from '../lib/hooks';
import { Spinner } from './ui';

const OK = ['completed', 'succeeded', 'success', 'done', 'finished'];
const BAD = ['failed', 'error', 'cancelled'];

/** Polls GET /api/jobs/{id} with bounded backoff until a terminal status (202 background work). */
export function JobStatus({ jobId, invalidate = [] }: { jobId: string | number; invalidate?: string[] }) {
  const sid = useStudentId();
  const qc = useQueryClient();
  const q = useGet(`/api/jobs/${jobId}`, { student_id: sid }, {
    refetchInterval: (query: any) => {
      const s = String(query.state.data?.status ?? '').toLowerCase();
      if (OK.includes(s) || BAD.includes(s) || query.state.status === 'error') return false;
      return Math.min(2000 * 1.4 ** query.state.dataUpdateCount, 15000);
    },
  });
  const s = String(q.data?.status ?? '').toLowerCase();
  useEffect(() => {
    if (OK.includes(s)) invalidate.forEach((p) => qc.invalidateQueries({ predicate: (x) => String(x.queryKey[0] ?? '').startsWith(p) }));
    // eslint-disable-next-line
  }, [s]);
  if (q.isLoading) return <Spinner label="Checking progress…" />;
  if (q.error) return <p className="errnote">{q.error.message}</p>;
  if (BAD.includes(s)) return <p className="errnote">Processing failed{q.data?.error_message ? `: ${q.data.error_message}` : '.'}</p>;
  if (OK.includes(s)) return <p className="okline">Ready for AI Analysis.</p>;
  return <Spinner label="Processing…" />;
}
