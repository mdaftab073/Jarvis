import { useState } from 'react';
import { api } from '../api/client';
import { useStudentId } from '../auth/AuthContext';
import { JobStatus } from '../components/Job';
import { Chip, PageHead, ResourcePanel } from '../components/ui';
import { useAct } from '../lib/hooks';
import { dt } from '../lib/format';

export default function Inbox() {
  const sid = useStudentId();
  const [job, setJob] = useState<number | null>(null);
  // 202: alerts are generated in the background; poll the job, then refresh the list.
  const gen = useAct(() => api(`/api/notifications/${sid}/generate-alerts`, { method: 'POST' }), { ok: 'Checking for new alerts…', onSuccess: (r: any) => setJob(r?.id ?? null) });
  return (
    <>
      <PageHead title="Inbox" sub="Alerts about deadlines, plans and progress."
        actions={<button className="btn" disabled={gen.isPending} onClick={() => gen.mutate()}>{gen.isPending ? 'Working…' : 'Check for alerts'}</button>} />
      {job && <JobStatus jobId={job} invalidate={['/api/notifications']} />}
      <ResourcePanel title="Notifications" listPath={`/api/notifications/${sid}`} empty="You’re all caught up."
        render={(n) => <div className="stack"><div className="between"><b>{!n.read && <span className="unread" aria-label="unread" />}{n.title}</b><Chip tone={n.notification_type === 'CRITICAL' ? 'bad' : n.notification_type === 'WARNING' ? 'warn' : ''}>{n.notification_type.toLowerCase()}</Chip></div><p>{n.message}</p><span className="muted">{dt(n.created_at)}</span></div>}
        actions={[{ label: 'Mark read', method: 'PATCH', path: (n) => `/api/notifications/${n.id}/read`, hide: (n) => n.read }]} />
    </>
  );
}
