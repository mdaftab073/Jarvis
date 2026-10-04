import { useState } from 'react';
import { api, asList } from '../api/client';
import { useStudentId } from '../auth/AuthContext';
import { SubjectPicker, useSubject, useSubjectNames } from '../auth/SubjectContext';
import { Async, Bar, Card, Chip, CreateForm, DataView, Empty, PageHead, ResourcePanel, Tabs } from '../components/ui';
import { useAct, useGet } from '../lib/hooks';
import { useStored } from '../lib/store';
import { dd, dt } from '../lib/format';

const isDone = (t: any) => ['completed', 'done', 'complete'].includes(String(t.status).toLowerCase());

function StudyPlan() {
  const sid = useStudentId();
  const { subjectId } = useSubject();
  const [planId, setPlanId] = useStored('plan');
  const plan = useGet(planId ? `/api/study-plans/${planId}` : null);
  const done = useAct((id: number) => api(`/api/study-plans/tasks/${id}/complete`, { method: 'PATCH' }), { ok: 'Task completed.', invalidate: ['/api/study-plans', '/api/analytics'] });
  const recalc = useAct(() => api(`/api/study-plans/${planId}/recalculate`, { method: 'POST' }), { ok: 'Plan recalculated.', invalidate: ['/api/study-plans'] });
  return (
    <div className="grid2">
      <Card title="Generate a plan">
        {!subjectId ? <Empty>Choose a subject first.</Empty> : (
          <CreateForm path="/api/study-plans/generate" extra={{ student_id: sid, subject_id: subjectId }} timeoutMs={120_000} ok="Study plan created." invalidate={['/api/study-plans']}
            onDone={(r) => r?.id && setPlanId(String(r.id))} submit="Generate plan"
            fields={[
              { name: 'exam_date', label: 'Exam date', type: 'date', required: true },
              { name: 'hours_per_day', label: 'Hours per day', type: 'number', required: true, min: 0.5, max: 24, default: '2' },
              { name: 'subject_difficulty', label: 'Difficulty (1 easy – 5 hard)', type: 'number', min: 1, max: 5, default: '3' },
            ]} />
        )}
        {planId && <p className="hint"><button className="linkbtn" onClick={() => setPlanId(null)}>Forget this plan</button></p>}
      </Card>
      <Card title={plan.data ? `${(plan.data as any).subject_name} plan` : 'Current plan'}
        actions={planId && <button className="btn small" disabled={recalc.isPending} onClick={() => recalc.mutate()}>Recalculate</button>}>
        {!planId ? <Empty>No plan yet. Generate one to see your daily tasks here.</Empty> : (
          <Async q={plan}>
            {(p: any) => (
              <div className="stack">
                <div><div className="between"><span>Exam {dd(p.exam_date)}</span><span className="muted">{p.progress?.tasks_done}/{(p.progress?.tasks_done ?? 0) + (p.progress?.tasks_remaining ?? 0)} done</span></div><Bar value={p.progress?.completion ?? 0} /></div>
                {p.daily_agenda?.map((day: any) => (
                  <div key={day.day_number} className="day">
                    <h3>Day {day.day_number} · {dd(day.date)}</h3>
                    {day.tasks.map((t: any) => (
                      <div key={t.id} className={`task ${isDone(t) ? 'done' : ''}`}>
                        <div><b>{t.topic}</b><div className="muted">{t.estimated_hours} h · priority {t.priority}</div></div>
                        {isDone(t) ? <Chip tone="ok">done</Chip> : <button className="btn small" disabled={done.isPending} onClick={() => done.mutate(t.id)}>Done</button>}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </Async>
        )}
      </Card>
    </div>
  );
}

const blockRow = (names: (id: any) => string) => (b: any) => (
  <div><div className="between"><b>{b.title || 'Study block'}</b><Chip>{String(b.block_type).replace('_', ' ').toLowerCase()}</Chip></div>
    <div className="muted">{dt(b.start_time)} → {dt(b.end_time)}{b.subject_id ? ` · ${names(b.subject_id)}` : ''}</div></div>
);

function Schedule() {
  const sid = useStudentId();
  const names = useSubjectNames();
  return (
    <>
      <ResourcePanel title="Study blocks" listPath={`/api/schedule/${sid}`} empty="No study blocks yet. Generate a schedule or add a block." render={blockRow(names)}
        createPath={`/api/schedule/${sid}/blocks`} createLabel="Add a study block"
        fields={[
          { name: 'title', label: 'Title' },
          { name: 'subject_id', label: 'Subject', type: 'subject' },
          { name: 'block_type', label: 'Type', type: 'select', options: ['STUDY', 'REVISION', 'ATTENDANCE_RECOVERY', 'DEADLINE_PREP', 'GOAL'], default: 'STUDY' },
          { name: 'start_time', label: 'Starts', type: 'datetime-local', required: true },
          { name: 'end_time', label: 'Ends', type: 'datetime-local', required: true },
        ]} />
      <div className="grid2">
        <Card title="Auto-schedule subjects">
          <CreateForm path={`/api/schedule/${sid}/generate`} invalidate={['/api/schedule', '/api/calendar']} ok="Schedule created." submit="Generate"
            fields={[
              { name: 'subject_ids', label: 'Subjects', type: 'subjects', required: true },
              { name: 'start_time', label: 'Start', type: 'datetime-local', required: true },
              { name: 'session_length', label: 'Session length (min)', type: 'number', default: '50' },
              { name: 'break_minutes', label: 'Break (min)', type: 'number', default: '10' },
            ]} />
        </Card>
        <Card title="Smart schedule">
          <CreateForm path={`/api/schedule/${sid}/intelligent`} invalidate={['/api/schedule', '/api/calendar']} ok="Smart schedule created." submit="Generate"
            fields={[
              { name: 'start_time', label: 'Start', type: 'datetime-local', required: true },
              { name: 'available_hours', label: 'Hours available per day (max 16)', type: 'number', required: true, default: '3' },
              { name: 'horizon_days', label: 'Days to plan (1–14)', type: 'number', default: '7' },
              { name: 'session_minutes', label: 'Session length (15–180 min)', type: 'number', default: '45' },
            ]} />
        </Card>
      </div>
    </>
  );
}

function Agenda({ a }: { a: any }) {
  if (!a?.items?.length) return <p className="muted">Nothing scheduled.</p>;
  return <ul className="rows">{a.items.map((it: any, i: number) => (
    <li key={i}><div><b>{it.title}</b><div className="muted">{dt(it.start_time)}{it.end_time ? ` → ${dt(it.end_time)}` : ''}</div></div><Chip>{String(it.kind).replace('_', ' ').toLowerCase()}</Chip></li>
  ))}</ul>;
}

function Calendar() {
  const sid = useStudentId();
  const [range, setRange] = useState('week');
  const isWeek = range === 'week';
  return (
    <>
      <Tabs tabs={[['today', 'Today'], ['tomorrow', 'Tomorrow'], ['week', 'This week'], ['events', 'My events']]} value={range} onChange={setRange} />
      {range === 'events' ? (
        <ResourcePanel title="Events" listPath={`/api/calendar/${sid}`} empty="No events yet." createPath={`/api/calendar/${sid}`} createLabel="New event"
          render={(e) => <div><b>{e.title}</b><div className="muted">{dt(e.start_time)} → {dt(e.end_time)}</div>{e.description && <p>{e.description}</p>}</div>}
          fields={[
            { name: 'title', label: 'Title', required: true },
            { name: 'description', label: 'Notes', type: 'textarea' },
            { name: 'start_time', label: 'Starts', type: 'datetime-local', required: true },
            { name: 'end_time', label: 'Ends (must be after start)', type: 'datetime-local', required: true },
            { name: 'event_type', label: 'Type', type: 'select', options: ['EXAM', 'CLASS', 'LAB', 'MEETING', 'OTHER'], default: 'OTHER' },
          ]}
          actions={[{ label: 'Delete', method: 'DELETE', confirm: 'Delete this event?', path: (e) => `/api/calendar/events/${e.id}` }]} />
      ) : (
        <AgendaView path={`/api/calendar/${sid}/${range}`} week={isWeek} />
      )}
    </>
  );
}
function AgendaView({ path, week }: { path: string; week: boolean }) {
  const q = useGet(path);
  return (
    <Card title={week ? 'Week agenda' : 'Agenda'}>
      <Async q={q} empty="Nothing scheduled.">
        {(d: any) => week
          ? <div className="stack">{d.days?.map((day: any) => <div key={day.date} className="day"><h3>{dd(day.date)}</h3><Agenda a={day} /></div>)}</div>
          : <Agenda a={d} />}
      </Async>
    </Card>
  );
}

function Coach() {
  const sid = useStudentId();
  const [goal, setGoal] = useState('');
  const go = useAct(() => api('/api/agent/academic', { method: 'POST', timeoutMs: 120_000, body: { student_id: sid, goal } }));
  const r: any = go.data;
  const list = (t: string, a?: string[]) => a?.length ? <><h3>{t}</h3><ul className="plain">{a.map((x, i) => <li key={i}>{x}</li>)}</ul></> : null;
  return (
    <Card title="Study coach">
      <form className="stack" onSubmit={(e) => { e.preventDefault(); if (goal.trim()) go.mutate(); }}>
        <label className="field"><span>What do you want to achieve?</span><textarea rows={3} maxLength={2000} value={goal} placeholder="e.g. Get ready for my DBMS mid-sem in two weeks" onChange={(e) => setGoal(e.target.value)} /></label>
        <button className="btn primary" disabled={go.isPending || !goal.trim()}>{go.isPending ? 'Thinking…' : 'Get a plan of action'}</button>
      </form>
      {r && <div className="answer"><p>{r.summary}</p>{list('Priority actions', r.priority_actions)}{list('Topics to focus on', r.recommended_topics)}{list('Next steps', r.next_steps)}</div>}
    </Card>
  );
}

export default function Plan() {
  const [tab, setTab] = useState('plan');
  return (
    <>
      <PageHead title="Plan" sub="Study plans, schedule, calendar and coaching." actions={<SubjectPicker />} />
      <Tabs tabs={[['plan', 'Study plan'], ['schedule', 'Schedule'], ['calendar', 'Calendar'], ['coach', 'Coach']]} value={tab} onChange={setTab} />
      {tab === 'plan' && <StudyPlan />}
      {tab === 'schedule' && <Schedule />}
      {tab === 'calendar' && <Calendar />}
      {tab === 'coach' && <Coach />}
    </>
  );
}
