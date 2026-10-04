import { useAuth, useStudentId } from '../auth/AuthContext';
import { useSubjectNames } from '../auth/SubjectContext';
import { Async, Card, EditForm, Fetched, PageHead, Trend } from '../components/ui';
import { useGet } from '../lib/hooks';

export default function Profile() {
  const sid = useStudentId();
  const { student, logout } = useAuth();
  const names = useSubjectNames();
  const prof = useGet(`/api/profile/${sid}`);
  const summary = useGet(`/api/profile/${sid}/summary`);
  const list = (t: string, a?: string[]) => (a?.length ? <div><h3>{t}</h3><ul className="plain">{a.map((x, i) => <li key={i}>{x}</li>)}</ul></div> : null);
  return (
    <>
      <PageHead title="Profile" actions={<button className="btn" onClick={logout}>Sign out</button>} />
      <Card title="Account">
        <div className="row">
          {student?.profile_picture && <img className="avatar" src={student.profile_picture} alt="" referrerPolicy="no-referrer" />}
          <div><strong>{student?.full_name}</strong><p className="muted">{student?.email}</p></div>
        </div>
      </Card>
      <Card title="How Jarvis sees you">
        <Async q={summary} empty="No summary yet — use the tutor and practice to build one.">{(s: any) => <p className="pre">{s.summary}</p>}</Async>
        <Async q={prof}>{(p: any) => <div className="grid2">{list('Strengths', p.strengths)}{list('Weaknesses', p.weaknesses)}{list('Study habits', p.study_habits)}{list('Preferred subjects', p.preferred_subjects)}
          {p.current_goal && <div><h3>Current goal</h3><p>{p.current_goal}</p></div>}{p.readiness_trend?.length > 1 && <div><h3>Readiness trend</h3><Trend values={p.readiness_trend} /></div>}</div>}</Async>
      </Card>
      <div className="grid2">
        <EditForm title="Academic profile" path={`/api/academic-profiles/${sid}`} fields={[
          { name: 'enrollment_number', label: 'Enrollment number' }, { name: 'branch', label: 'Branch' }, { name: 'department', label: 'Department' },
          { name: 'semester', label: 'Semester', type: 'number', min: 1 }, { name: 'section', label: 'Section' }, { name: 'batch_year', label: 'Batch year', type: 'number' },
          { name: 'current_cpi', label: 'Current CPI (0–10)', type: 'number', min: 0, max: 10 }, { name: 'current_spi', label: 'Current SPI (0–10)', type: 'number', min: 0, max: 10 },
          { name: 'earned_credits', label: 'Earned credits', type: 'number', min: 0 }, { name: 'total_credits', label: 'Total credits', type: 'number', min: 0 },
          { name: 'academic_status', label: 'Status', type: 'select', options: ['ACTIVE', 'PROBATION', 'GRADUATED', 'SUSPENDED', 'DROPOUT'] },
        ]} />
        <EditForm title="Study preferences" path={`/api/academic-profiles/${sid}/preferences`} fields={[
          { name: 'preferred_study_time', label: 'Preferred study time', placeholder: 'e.g. evening' },
          { name: 'preferred_session_length', label: 'Session length (minutes)', type: 'number', min: 1 },
          { name: 'study_style', label: 'Study style', placeholder: 'e.g. flashcards, past papers' },
        ]} />
        <Fetched title="What Jarvis remembers" path={`/api/profile/${sid}/memories`} empty="No memories yet."
          render={(d: any[]) => <ul className="rows">{d.map((m) => <li key={m.id}><div><b>{m.memory_key.replace(/_/g, ' ')}</b><div className="muted">{typeof m.memory_value === 'string' ? m.memory_value : JSON.stringify(m.memory_value)}</div></div></li>)}</ul>} />
        <Fetched title="Readiness history" path={`/api/profile/${sid}/readiness-history`} empty="No readiness history yet."
          render={(d: any[]) => <><Trend values={d.map((x) => x.readiness_score)} /><ul className="rows">{d.slice(-5).reverse().map((x) => <li key={x.id}><span>{x.subject_id ? names(x.subject_id) : 'Overall'}</span><b>{x.readiness_score}%</b></li>)}</ul></>} />
      </div>
    </>
  );
}
