import { useState } from 'react';
import { api } from '../api/client';
import { useStudentId } from '../auth/AuthContext';
import { useSubjectNames } from '../auth/SubjectContext';
import { Async, Bar, Card, Chip, CreateForm, DataView, Empty, Fetched, PageHead, ResourcePanel, Tabs, Trend } from '../components/ui';
import { useGet } from '../lib/hooks';
import { useStored } from '../lib/store';
import { dd, dt, num } from '../lib/format';

const topicRows = (key: 'mastery' | 'confidence_score') => (d: any[]) => (
  <ul className="rows">{d.map((t, i) => <li key={i}><div className="grow"><div className="between"><b>{t.topic}</b><span className="muted">{Math.round(t[key === 'mastery' ? 'mastery' : 'mastery'])}%</span></div><Bar value={t.mastery} /></div></li>)}</ul>
);

function Overview() {
  const sid = useStudentId();
  const q = useGet(`/api/analytics/dashboard/${sid}`);
  const ins = useGet(`/api/learning/insights/${sid}`);
  return (
    <div className="stack">
      <Card title="Readiness">
        <Async q={q} empty="No analytics yet — practice or log a study session.">
          {(a: any) => (
            <div className="stack">
              <div className="stats">
                <div className="stat"><span className="muted">Overall readiness</span><b>{a.readiness_score}%</b></div>
                <div className="stat"><span className="muted">Status</span><b>{a.status}</b></div>
                <div className="stat"><span className="muted">Plan completion</span><b>{a.plan_completion}%</b></div>
              </div>
              {a.subjects?.length > 0 && <ul className="rows">{a.subjects.map((s: any) => <li key={s.subject_id}><div className="grow"><div className="between"><b>{s.subject_name}</b><span className="muted">{s.readiness_score}% · {s.status}</span></div><Bar value={s.readiness_score} /></div></li>)}</ul>}
              <h3>Practice score trend</h3>
              <Trend values={(a.practice_score_trend ?? []).map((p: any) => p.score)} />
              {a.recommendations?.length > 0 && <><h3>Recommendations</h3><ul className="plain">{a.recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul></>}
              <div className="grid2">
                <div><h3>Weak topics</h3>{a.weak_topics?.length ? topicRows('mastery')(a.weak_topics) : <p className="muted">None.</p>}</div>
                <div><h3>Strong topics</h3>{a.strong_topics?.length ? topicRows('mastery')(a.strong_topics) : <p className="muted">None yet.</p>}</div>
              </div>
            </div>
          )}
        </Async>
      </Card>
      <Card title="Learning insights">
        <Async q={ins} empty="No insights yet.">
          {(i: any) => <div className="stack"><div className="stats"><div className="stat"><span className="muted">Sessions</span><b>{i.total_sessions}</b></div><div className="stat"><span className="muted">Minutes studied</span><b>{num(i.total_time_minutes, 0)}</b></div><div className="stat"><span className="muted">Avg. mastery</span><b>{num(i.average_mastery, 0)}%</b></div></div>
            <p>{i.overall_readiness}</p>{i.recommended_actions?.length > 0 && <ul className="plain">{i.recommended_actions.map((r: string, k: number) => <li key={k}>{r}</li>)}</ul>}</div>}
        </Async>
      </Card>
    </div>
  );
}

function Learning() {
  const sid = useStudentId();
  const names = useSubjectNames();
  return (
    <ResourcePanel title="Study log" listPath={`/api/learning/history/${sid}`} empty="No sessions logged yet." createPath="/api/learning/session" createExtra={{ student_id: sid }} createLabel="Log a study session"
      render={(s) => <div className="between"><div><b>{s.activity_type.replace('_', ' ')}</b><div className="muted">{names(s.subject_id)} · {dt(s.created_at)}</div></div><Chip>{s.duration_minutes != null ? `${s.duration_minutes} min` : '—'}{s.score != null ? ` · ${s.score}%` : ''}</Chip></div>}
      fields={[
        { name: 'subject_id', label: 'Subject', type: 'subject', required: true },
        { name: 'activity_type', label: 'Activity', type: 'select', required: true, options: ['study_session', 'revision', 'quiz', 'flashcard_review', 'rag_question'] },
        { name: 'duration_minutes', label: 'Minutes', type: 'number', min: 0 },
        { name: 'score', label: 'Score % (optional)', type: 'number', min: 0, max: 100 },
      ]} />
  );
}

function Semester() {
  const sid = useStudentId();
  const [id, setId] = useStored('semester');
  const [view, setView] = useState('copilot');
  return (
    <>
      <Card title="Start a semester">
        <CreateForm path="/api/semester" extra={{ student_id: sid }} ok="Semester created." invalidate={['/api/semester']}
          shape={(b) => ({ ...b, subjects: (b.subjects ?? []).map((s: number) => ({ subject_id: s })) })} onDone={(r) => r?.id && setId(String(r.id))}
          fields={[
            { name: 'semester_number', label: 'Semester number', type: 'number', required: true, min: 1 },
            { name: 'start_date', label: 'Starts', type: 'date', required: true },
            { name: 'end_date', label: 'Ends', type: 'date', required: true },
            { name: 'target_cgpa', label: 'Target CGPA (optional)', type: 'number' },
            { name: 'subjects', label: 'Subjects', type: 'subjects' },
          ]} />
      </Card>
      {!id ? <Empty>Create a semester to see its health, risks and review.</Empty> : (
        <>
          <p className="hint">Showing semester #{id}. <button className="linkbtn" onClick={() => setId(null)}>Forget it</button></p>
          <Tabs tabs={[['copilot', 'Copilot'], ['health', 'Health'], ['risks', 'Risks'], ['review', 'Review']]} value={view} onChange={setView} />
          <Fetched title={view[0].toUpperCase() + view.slice(1)} path={`/api/semester/${id}/${view}`} empty="Nothing to show yet." />
          <ResourcePanel title="Milestones" listPath={`/api/semester/${id}`} items={(d) => d.milestones ?? []} empty="No milestones yet." createPath={`/api/semester/${id}/milestone`} createLabel="Add a milestone"
            render={(m) => <div className="between"><div><b>{m.title}</b><div className="muted">Due {dd(m.due_date)}</div></div>{m.completed && <Chip tone="ok">done</Chip>}</div>}
            actions={[{ label: 'Mark done', method: 'PATCH', path: (m) => `/api/semester/${id}/milestone/${m.id}`, body: { completed: true }, hide: (m) => m.completed }]}
            fields={[{ name: 'title', label: 'Title', required: true }, { name: 'due_date', label: 'Due', type: 'date', required: true }, { name: 'description', label: 'Notes', type: 'textarea' }]} />
        </>
      )}
    </>
  );
}

export default function Progress() {
  const sid = useStudentId();
  const names = useSubjectNames();
  const [tab, setTab] = useState('overview');
  const ga = useGet(tab === 'grades' ? `/api/grades/${sid}/analytics` : null);
  return (
    <>
      <PageHead title="Progress" sub="Analytics, grades, attendance, goals, habits, deadlines and reminders." />
      <Tabs value={tab} onChange={setTab} tabs={[['overview', 'Overview'], ['learning', 'Study log'], ['grades', 'Grades'], ['attendance', 'Attendance'], ['goals', 'Goals'], ['habits', 'Habits'], ['deadlines', 'Deadlines'], ['reminders', 'Reminders'], ['semester', 'Semester']]} />
      {tab === 'overview' && <Overview />}
      {tab === 'learning' && <Learning />}
      {tab === 'grades' && (
        <>
          <Card title="Grade analytics">
            <Async q={ga} empty="Add grades to see CPI/SPI.">
              {(g: any) => <div className="stack"><div className="stats"><div className="stat"><span className="muted">CPI</span><b>{num(g.cpi, 2)}</b></div><div className="stat"><span className="muted">Current SPI</span><b>{num(g.current_spi, 2)}</b></div><div className="stat"><span className="muted">Records</span><b>{g.record_count}</b></div></div>
                {g.spi_by_semester && <ul className="rows">{Object.entries(g.spi_by_semester).map(([s, v]) => <li key={s}><span>Semester {s}</span><b>{num(v, 2)}</b></li>)}</ul>}</div>}
            </Async>
          </Card>
          <ResourcePanel title="Grades" listPath={`/api/grades/${sid}`} empty="No grades recorded." createPath={`/api/grades/${sid}`} createLabel="Add a grade"
            render={(g) => <div className="between"><div><b>{names(g.subject_id)}</b><div className="muted">{g.grade_type === 'FINAL' ? `Final · sem ${g.semester ?? '?'}` : g.component_type}{g.grade ? ` · ${g.grade}` : ''}</div></div><Chip>{g.obtained_marks ?? '—'}/{g.max_marks}</Chip></div>}
            fields={[
              { name: 'subject_id', label: 'Subject', type: 'subject', required: true },
              { name: 'grade_type', label: 'Type', type: 'select', options: ['COMPONENT', 'FINAL'], default: 'COMPONENT' },
              { name: 'component_type', label: 'Component', type: 'select', options: ['CT1', 'CT2', 'CT3', 'ASSIGNMENT', 'LAB', 'END_SEM', 'MID_SEM', 'VIVA', 'PROJECT', 'OTHER'], default: 'OTHER' },
              { name: 'obtained_marks', label: 'Marks obtained', type: 'number', min: 0 },
              { name: 'max_marks', label: 'Out of', type: 'number', default: '100' },
              { name: 'semester', label: 'Semester (required for FINAL)', type: 'number', min: 1 },
              { name: 'credits', label: 'Credits (required for FINAL)', type: 'number', min: 0 },
              { name: 'grade_points', label: 'Grade points 0–10 (required for FINAL)', type: 'number', min: 0, max: 10 },
              { name: 'grade', label: 'Grade letter', placeholder: 'AA' },
            ]} />
        </>
      )}
      {tab === 'attendance' && (
        <ResourcePanel title="Attendance" listPath={`/api/attendance/${sid}`} empty="No attendance recorded." createPath={`/api/attendance/${sid}`} createLabel="Record attendance" createdOk="Attendance saved."
          items={(d) => (Array.isArray(d) ? d : [])}
          render={(a) => <div className="between"><div><b>{names(a.record.subject_id)}</b><div className="muted">{a.record.attended_classes}/{a.record.total_classes} classes{a.classes_to_recover ? ` · attend ${a.classes_to_recover} more to recover` : ''}</div></div><Chip tone={a.risk === 'CRITICAL' ? 'bad' : a.risk === 'WARNING' ? 'warn' : a.risk === 'SAFE' ? 'ok' : ''}>{a.record.attendance_percentage != null ? `${Math.round(a.record.attendance_percentage)}%` : a.risk.toLowerCase()}</Chip></div>}
          fields={[{ name: 'subject_id', label: 'Subject', type: 'subject', required: true }, { name: 'attended_classes', label: 'Classes attended', type: 'number', required: true, min: 0 }, { name: 'total_classes', label: 'Total classes held', type: 'number', required: true, min: 0 }]} />
      )}
      {tab === 'goals' && (
        <ResourcePanel title="Goals" listPath={`/api/goals/${sid}`} empty="No goals yet. Set one to track progress." createPath={`/api/goals/${sid}`} createLabel="New goal"
          render={(g) => <div className="stack"><div className="between"><b>{g.title}</b><Chip tone={g.completed ? 'ok' : ''}>{g.completed ? 'done' : g.goal_type.replace('_', ' ').toLowerCase()}</Chip></div>
            <Bar value={g.completed ? 100 : g.progress_percent} /><div className="muted">{g.current_value}{g.target_value != null ? ` / ${g.target_value}` : ''} {g.target_unit ?? ''}{g.target_date ? ` · by ${dd(g.target_date)}` : ''}</div></div>}
          fields={[
            { name: 'title', label: 'Goal', required: true }, { name: 'goal_type', label: 'Type', type: 'select', required: true, options: ['SEMESTER', 'CPI', 'ATTENDANCE', 'PLACEMENT', 'STUDY_HOURS'] },
            { name: 'target_value', label: 'Target value', type: 'number', min: 0 }, { name: 'target_unit', label: 'Unit', placeholder: 'hours, %, CPI…' }, { name: 'target_date', label: 'Target date', type: 'date' },
          ]}
          actions={[
            { label: 'Log progress', method: 'POST', prompt: 'Current progress value?', path: (g) => `/api/progress/${g.id}`, body: (_g: any, v?: string) => ({ progress_value: Number(v) }), hide: (g) => g.completed },
            { label: 'Mark done', method: 'PATCH', path: (g) => `/api/goals/${g.id}`, body: { completed: true }, hide: (g) => g.completed },
            { label: 'Delete', method: 'DELETE', confirm: 'Delete this goal?', path: (g) => `/api/goals/${g.id}` },
          ]} />
      )}
      {tab === 'habits' && (
        <ResourcePanel title="Habits" listPath={`/api/habits/${sid}`} empty="No habits yet." createPath={`/api/habits/${sid}`} createLabel="New habit"
          render={(h) => <div className="between"><div><b>{h.habit_name}</b><div className="muted">{h.category.replace('_', ' ').toLowerCase()} · {h.target_per_week}×/week</div></div></div>}
          fields={[{ name: 'habit_name', label: 'Habit', required: true }, { name: 'category', label: 'Category', type: 'select', required: true, options: ['DAILY_STUDY', 'REVISION', 'PYQ_PRACTICE', 'ATTENDANCE_CHECK', 'ASSIGNMENT_COMPLETION'] }, { name: 'target_per_week', label: 'Times per week (1–7)', type: 'number', min: 1, max: 7, default: '7' }]}
          actions={[
            { label: 'Log today', method: 'POST', path: (h) => `/api/habits/${h.id}/logs`, body: { completed: true } },
            { label: 'Delete', method: 'DELETE', confirm: 'Delete this habit?', path: (h) => `/api/habits/${h.id}` },
          ]} />
      )}
      {tab === 'deadlines' && (
        <ResourcePanel title="Deadlines" listPath={`/api/deadlines/${sid}`} empty="No open deadlines." createPath={`/api/deadlines/${sid}`} createLabel="New deadline"
          render={(d) => <div className="between"><div><b>{d.title}</b><div className="muted">Due {dt(d.due_date)} · {d.type.replace('_', ' ').toLowerCase()}</div></div><Chip tone={['HIGH', 'CRITICAL'].includes(d.priority) ? 'bad' : ''}>{d.priority.toLowerCase()}</Chip></div>}
          fields={[
            { name: 'title', label: 'Title', required: true }, { name: 'due_date', label: 'Due', type: 'datetime-local', required: true },
            { name: 'type', label: 'Type', type: 'select', options: ['EXAM', 'ASSIGNMENT', 'PROJECT', 'LAB_SUBMISSION', 'QUIZ', 'PRESENTATION', 'OTHER'], default: 'OTHER' },
            { name: 'priority', label: 'Priority', type: 'select', options: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'], default: 'MEDIUM' },
            { name: 'subject_id', label: 'Subject (optional)', type: 'subject' }, { name: 'description', label: 'Notes', type: 'textarea' },
          ]}
          actions={[{ label: 'Mark complete', method: 'PATCH', path: (d) => `/api/deadlines/${d.id}/complete`, body: { completed: true } }]} />
      )}
      {tab === 'reminders' && (
        <ResourcePanel title="Reminders" listPath={`/api/reminders/${sid}`} empty="No reminders." createPath={`/api/reminders/${sid}`} createLabel="New reminder"
          render={(r) => <div className="between"><div><b>{r.title}</b><div className="muted">{dt(r.trigger_time)}</div></div>{r.completed && <Chip tone="ok">done</Chip>}</div>}
          fields={[{ name: 'title', label: 'Reminder', required: true }, { name: 'trigger_time', label: 'When', type: 'datetime-local', required: true }]}
          actions={[
            { label: 'Mark done', method: 'PATCH', path: (r) => `/api/reminders/${r.id}`, body: { completed: true }, hide: (r) => r.completed },
            { label: 'Delete', method: 'DELETE', confirm: 'Delete this reminder?', path: (r) => `/api/reminders/${r.id}` },
          ]} />
      )}
      {tab === 'semester' && <Semester />}
    </>
  );
}
