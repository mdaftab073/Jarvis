import { Link } from 'react-router-dom';
import { useAuth, useStudentId } from '../auth/AuthContext';
import { SubjectPicker, useSubject, useSubjectNames } from '../auth/SubjectContext';
import { Async, Bar, Card, Chip, Empty, PageHead, Stat } from '../components/ui';
import { useGet } from '../lib/hooks';
import { dt, dd, num, pctOf } from '../lib/format';

const tone = (r: string) => (r === 'CRITICAL' ? 'bad' : r === 'WARNING' ? 'warn' : r === 'SAFE' ? 'ok' : '');

export default function Home() {
  const sid = useStudentId();
  const { student } = useAuth();
  const { subjectId } = useSubject();
  const name = useSubjectNames();
  const dash = useGet(`/api/dashboard/${sid}`);
  const first = (student?.full_name || '').split(' ')[0];
  return (
    <>
      <PageHead title={first ? `Hi, ${first}` : 'Welcome back'} sub="Here’s what needs your attention." actions={<SubjectPicker />} />
      {!subjectId && <p className="hint">Choose a subject to unlock materials, practice and analytics. No subjects yet? Add a course in <Link to="/courses">Courses</Link>.</p>}
      <Async q={dash} empty="No activity yet. Add a course, upload a material or start a chat to get going.">
        {(d: any) => (
          <>
            <div className="stats">
              <Stat label="Readiness" value={d.readiness != null ? `${num(d.readiness, 0)}%` : '—'} />
              <Stat label="Study hours (7 days)" value={num(d.study_hours_7d)} />
              <Stat label="Plan completion" value={pctOf(d.completion_rate) != null ? `${pctOf(d.completion_rate)}%` : '—'} />
              <Stat label="Consistency" value={num(d.consistency_score, 0)} />
            </div>
            <div className="grid2">
              <Card title="Today" actions={<Link to="/plan">Plan</Link>}>
                {d.agenda_today?.items?.length ? (
                  <ul className="rows">{d.agenda_today.items.map((it: any, i: number) => (
                    <li key={i}><div><b>{it.title}</b><div className="muted">{dt(it.start_time)}</div></div><Chip>{String(it.kind).replace('_', ' ').toLowerCase()}</Chip></li>
                  ))}</ul>
                ) : <Empty>Nothing scheduled today.</Empty>}
              </Card>
              <Card title="Deadlines" actions={<Link to="/progress">All</Link>}>
                {d.deadlines?.filter((x: any) => !x.completed).length ? (
                  <ul className="rows">{d.deadlines.filter((x: any) => !x.completed).slice(0, 6).map((x: any) => (
                    <li key={x.id}><div><b>{x.title}</b><div className="muted">Due {dt(x.due_date)}</div></div><Chip tone={x.priority === 'CRITICAL' || x.priority === 'HIGH' ? 'bad' : ''}>{x.priority.toLowerCase()}</Chip></li>
                  ))}</ul>
                ) : <Empty>No open deadlines.</Empty>}
              </Card>
              <Card title="Goals">
                {d.goal_progress?.length ? (
                  <div className="stack">{d.goal_progress.map((g: any) => (
                    <div key={g.goal_id}><div className="between"><span>{g.title}</span><span className="muted">{g.completed ? 'Done' : g.progress_percent != null ? `${Math.round(g.progress_percent)}%` : '—'}</span></div><Bar value={g.completed ? 100 : g.progress_percent} /></div>
                  ))}</div>
                ) : <Empty>No goals yet. Set one under Progress.</Empty>}
              </Card>
              <Card title="Attendance">
                {d.attendance?.length ? (
                  <ul className="rows">{d.attendance.map((a: any) => (
                    <li key={a.record.id}><div><b>{name(a.record.subject_id)}</b><div className="muted">{a.record.attended_classes}/{a.record.total_classes} classes{a.classes_to_recover ? ` · attend ${a.classes_to_recover} more to recover` : ''}</div></div><Chip tone={tone(a.risk)}>{a.record.attendance_percentage != null ? `${Math.round(a.record.attendance_percentage)}%` : a.risk.toLowerCase()}</Chip></li>
                  ))}</ul>
                ) : <Empty>No attendance recorded.</Empty>}
              </Card>
              <Card title="Habit streaks">
                {d.habit_streaks?.length ? (
                  <ul className="rows">{d.habit_streaks.map((h: any) => (
                    <li key={h.habit_id}><div><b>{h.habit_name}</b><div className="muted">Best {h.longest_streak} days</div></div><Chip>{h.current_streak} day streak</Chip></li>
                  ))}</ul>
                ) : <Empty>No habits tracked.</Empty>}
              </Card>
              <Card title="Suggestions">
                {d.productivity?.suggestions?.length ? <ul className="plain">{d.productivity.suggestions.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul> : <Empty>No suggestions right now.</Empty>}
                {d.productivity?.procrastination_risks?.length ? <p className="muted">Risks: {d.productivity.procrastination_risks.map((r: any) => String(r.type).replace('_', ' ').toLowerCase()).join(', ')}</p> : null}
              </Card>
            </div>
            <p className="hint">Last updated {dd(new Date().toISOString())}.</p>
          </>
        )}
      </Async>
    </>
  );
}
