import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, asList } from '../api/client';
import { useStudentId } from '../auth/AuthContext';
import { useSubject } from '../auth/SubjectContext';
import { Async, Bar, Card, Chip, CreateForm, DataView, Empty, Fetched, PageHead, Tabs } from '../components/ui';
import { useAct, useGet } from '../lib/hooks';
import { dt, num } from '../lib/format';

// ---- AI practice: server generates questions, grades free-text answers ----
function AiPractice() {
  const sid = useStudentId();
  const { subjectId } = useSubject();
  const [count, setCount] = useState('5');
  const [sess, setSess] = useState<any>(null);
  const [ans, setAns] = useState<Record<number, { a: string; c: number }>>({});
  const start = useAct(() => api('/api/practice/start', { method: 'POST', timeoutMs: 120_000, body: { student_id: sid, subject_id: subjectId, count: Number(count) } }),
    { onSuccess: (r) => { setSess(r); setAns({}); submit.reset(); } });
  const submit = useAct(() => api('/api/practice/submit', {
    method: 'POST', timeoutMs: 120_000,
    body: { session_id: sess.session_id, answers: sess.questions.map((q: any) => ({ attempt_id: q.attempt_id, student_answer: ans[q.attempt_id]?.a ?? '', confidence_score: ans[q.attempt_id]?.c ?? 50 })) },
  }), { ok: 'Practice graded.', invalidate: ['/api/mastery', '/api/analytics', '/api/learning', '/api/dashboard'] });
  const res: any = submit.data;
  const byId = (id: number) => res?.results?.find((r: any) => r.attempt_id === id);
  return (
    <Card title={sess ? 'Practice set' : 'Start practice'}>
      {!sess ? (
        <form className="stack" onSubmit={(e) => { e.preventDefault(); start.mutate(); }}>
          <p className="muted">Jarvis writes questions from your subject’s materials and grades your answers.</p>
          <label className="field"><span>Questions (1–30)</span><input type="number" inputMode="numeric" min={1} max={30} value={count} onChange={(e) => setCount(e.target.value)} /></label>
          <button className="btn primary" disabled={!subjectId || start.isPending}>{start.isPending ? 'Preparing questions…' : 'Start'}</button>
          {!subjectId && <Empty>Choose a subject first.</Empty>}
        </form>
      ) : (
        <div className="stack">
          {sess.questions.map((q: any, i: number) => {
            const r = byId(q.attempt_id);
            return (
              <fieldset key={q.attempt_id} className="q" disabled={!!res}>
                <legend>{i + 1}. {q.question}</legend>
                <div className="row"><Chip>{q.topic}</Chip><Chip>{q.difficulty}</Chip>{q.marks != null && <Chip>{q.marks} marks</Chip>}</div>
                <textarea rows={3} value={ans[q.attempt_id]?.a ?? ''} placeholder="Your answer" onChange={(e) => setAns((s) => ({ ...s, [q.attempt_id]: { a: e.target.value, c: s[q.attempt_id]?.c ?? 50 } }))} />
                <label className="field"><span>Confidence: {ans[q.attempt_id]?.c ?? 50}%</span>
                  <input type="range" min={0} max={100} step={10} value={ans[q.attempt_id]?.c ?? 50} onChange={(e) => setAns((s) => ({ ...s, [q.attempt_id]: { a: s[q.attempt_id]?.a ?? '', c: Number(e.target.value) } }))} /></label>
                {r && <div className={`fb ${r.is_correct ? 'ok' : 'bad'}`}><b>{r.is_correct ? 'Correct' : 'Not quite'} · {num(r.score)}</b><p>{r.feedback}</p></div>}
              </fieldset>
            );
          })}
          {!res ? (
            <button className="btn primary" disabled={submit.isPending} onClick={() => submit.mutate()}>{submit.isPending ? 'Grading…' : 'Submit answers'}</button>
          ) : (
            <div className="answer">
              <h3>Result: {res.correct_answers}/{res.total_questions} correct</h3>
              <Bar value={Math.round(res.accuracy <= 1 ? res.accuracy * 100 : res.accuracy)} />
              <p className="muted">Topics: {res.topic_coverage?.join(', ')}</p>
              <button className="btn" onClick={() => setSess(null)}>New practice set</button>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

// ---- Quiz lab: you write the questions (the API takes client-supplied questions) ----
interface Draft { question: string; question_type: string; correct_answer: string; topic_id?: number }
// The API returns correct_answer before submit; keep it out of UI state until results.
const strip = (q: any) => { const { correct_answer, ...rest } = q; return rest; };

function QuizLab() {
  const sid = useStudentId();
  const { subjectId } = useSubject();
  const topics = useGet(subjectId ? `/api/subjects/${subjectId}/topics` : null, { limit: 500 });
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [d, setD] = useState<Draft>({ question: '', question_type: 'short_answer', correct_answer: '' });
  const [quiz, setQuiz] = useState<{ id: number; questions: any[] } | null>(null);
  const [picked, setPicked] = useState<Record<number, string>>({});
  const gen = useAct(() => api('/api/quizzes/generate', { method: 'POST', body: { student_id: sid, subject_id: subjectId, questions: drafts } }),
    { onSuccess: (r: any) => { setQuiz({ id: r.session.id, questions: r.questions.map(strip) }); setPicked({}); submit.reset(); }, invalidate: ['/api/quizzes'] });
  const submit = useAct(() => api('/api/quizzes/submit', { method: 'POST', body: { session_id: quiz!.id, update_mastery: true, answers: quiz!.questions.map((q) => ({ question_id: q.id, student_answer: picked[q.id] ?? '' })) } }),
    { ok: 'Quiz scored.', invalidate: ['/api/quizzes', '/api/mastery', '/api/analytics'] });
  const history = useGet(`/api/quizzes/history/${sid}`, { limit: 50 });
  const res: any = submit.data;
  const add = () => { if (!d.question.trim() || !d.correct_answer.trim()) return; setDrafts([...drafts, d]); setD({ ...d, question: '', correct_answer: '' }); };
  return (
    <div className="grid2">
      <Card title={quiz ? 'Your quiz' : 'Build a quiz'}>
        {!quiz ? (
          <div className="stack">
            <p className="muted">Write your own questions and answers, then test yourself (or a friend). Answers stay hidden while you play.</p>
            <label className="field"><span>Question</span><textarea rows={2} value={d.question} onChange={(e) => setD({ ...d, question: e.target.value })} /></label>
            <label className="field"><span>Type</span><select value={d.question_type} onChange={(e) => setD({ ...d, question_type: e.target.value, correct_answer: '' })}><option value="short_answer">Short answer</option><option value="true_false">True / false</option><option value="MCQ">MCQ (put options in the question)</option></select></label>
            <label className="field"><span>Correct answer</span>
              {d.question_type === 'true_false'
                ? <select value={d.correct_answer} onChange={(e) => setD({ ...d, correct_answer: e.target.value })}><option value="">Select…</option><option value="true">true</option><option value="false">false</option></select>
                : <input value={d.correct_answer} onChange={(e) => setD({ ...d, correct_answer: e.target.value })} />}</label>
            <label className="field"><span>Topic (optional)</span><select value={d.topic_id ?? ''} onChange={(e) => setD({ ...d, topic_id: e.target.value ? Number(e.target.value) : undefined })}><option value="">None</option>{asList(topics.data).map((t: any) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></label>
            <button className="btn" onClick={add}>Add question</button>
            {drafts.length > 0 && <ol className="plain">{drafts.map((x, i) => <li key={i}>{x.question} <button className="linkbtn" onClick={() => setDrafts(drafts.filter((_, j) => j !== i))}>remove</button></li>)}</ol>}
            <button className="btn primary" disabled={!subjectId || !drafts.length || gen.isPending} onClick={() => gen.mutate()}>{gen.isPending ? 'Creating…' : `Start quiz (${drafts.length})`}</button>
            {!subjectId && <Empty>Choose a subject first.</Empty>}
          </div>
        ) : (
          <div className="stack">
            {quiz.questions.map((q, i) => {
              const r = res?.results?.find((x: any) => x.question_id === q.id);
              return (
                <fieldset key={q.id} className="q" disabled={!!res}>
                  <legend>{i + 1}. {q.question}</legend>
                  {q.question_type === 'true_false'
                    ? ['true', 'false'].map((o) => <label key={o} className="opt"><input type="radio" name={`q${q.id}`} checked={picked[q.id] === o} onChange={() => setPicked((p) => ({ ...p, [q.id]: o }))} /><span>{o}</span></label>)
                    : <input value={picked[q.id] ?? ''} placeholder="Your answer" onChange={(e) => setPicked((p) => ({ ...p, [q.id]: e.target.value }))} />}
                  {r && <div className={`fb ${r.is_correct ? 'ok' : 'bad'}`}><b>{r.is_correct ? 'Correct' : 'Incorrect'}</b>{!r.is_correct && <p>Answer: {r.correct_answer}</p>}</div>}
                </fieldset>
              );
            })}
            {!res ? <button className="btn primary" disabled={submit.isPending} onClick={() => submit.mutate()}>{submit.isPending ? 'Scoring…' : 'Submit answers'}</button>
              : <div className="answer"><h3>Score: {res.score}/{res.total_questions}</h3><button className="btn" onClick={() => { setQuiz(null); setDrafts([]); }}>New quiz</button></div>}
          </div>
        )}
      </Card>
      <Card title="Quiz history">
        <Async q={history} empty="No quizzes taken yet.">
          {(h) => <ul className="rows">{asList(h).map((s: any) => <li key={s.id}><div><b>Quiz #{s.id}</b><div className="muted">{dt(s.started_at)}</div></div><Chip>{s.score != null ? `${s.score}/${s.total_questions}` : 'unfinished'}</Chip></li>)}</ul>}
        </Async>
      </Card>
    </div>
  );
}

// ---- Flashcards ----
function Flip({ c }: { c: any }) {
  const [back, setBack] = useState(false);
  return <button className={`flash ${back ? 'back' : ''}`} onClick={() => setBack(!back)} aria-label="Flip card">{back ? c.answer : c.question}</button>;
}
function Flashcards() {
  const { subjectId } = useSubject();
  const [deck, setDeck] = useState<number | null>(null);
  const [fresh, setFresh] = useState<any[] | null>(null);
  const [picked, setPicked] = useState('');
  const decks = useGet('/api/flashcards/decks', { subject_id: subjectId ?? undefined, limit: 100 }, { enabled: !!subjectId });
  const topics = useGet(subjectId ? `/api/subjects/${subjectId}/topics` : null, { limit: 500 });
  const topicList = asList(topics.data);
  // The API has no "cards of a deck" route: fetch cards per topic and keep this deck's.
  const cards = useQuery({
    queryKey: ['deckcards', deck, subjectId, topicList.length], enabled: !!deck && topicList.length > 0,
    queryFn: async ({ signal }) => (await Promise.all(topicList.map((t: any) => api(`/api/flashcards/topic/${t.id}`, { query: { limit: 500 }, signal })))).flatMap(asList).filter((c: any) => c.deck_id === deck),
  });
  if (!subjectId) return <Card><Empty>Choose a subject first.</Empty></Card>;
  const shown = fresh ?? (cards.data as any[] | undefined);
  return (
    <div className="grid2">
      <div className="stack">
        <Card title="Decks">
          <Async q={decks} empty="No decks yet. Generate one below.">
            {(d) => <div className="stack">{asList(d).map((x: any) => <button key={x.id} className={`pick ${deck === x.id ? 'on' : ''}`} onClick={() => { setDeck(x.id); setFresh(null); }}>{x.name}</button>)}</div>}
          </Async>
        </Card>
        <Card title="Generate a deck">
          {!topicList.length ? <Empty>This subject has no topics yet. Upload a material and extract topics first.</Empty> : (
            <CreateForm path="/api/flashcards/generate" extra={{ subject_id: subjectId }} timeoutMs={120_000} invalidate={['/api/flashcards']} ok="Deck created." submit="Generate"
              shape={(b) => ({ ...b, topics: String(picked || '').split('|').filter(Boolean) })}
              onDone={(r) => { setDeck(r.deck.id); setFresh(r.flashcards); }}
              fields={[{ name: 'deck_name', label: 'Deck name', required: true }, { name: 'cards_per_topic', label: 'Cards per topic (1–20)', type: 'number', default: '5' }]} />
          )}
          {topicList.length > 0 && (
            <div className="checks"><span className="muted">Topics</span>{topicList.map((t: any) => {
              const sel = new Set(picked.split('|').filter(Boolean));
              return <label key={t.id} className="check"><input type="checkbox" checked={sel.has(t.name)} onChange={() => { sel.has(t.name) ? sel.delete(t.name) : sel.add(t.name); setPicked([...sel].join('|')); }} />{t.name}</label>;
            })}</div>
          )}
        </Card>
      </div>
      <Card title="Cards">
        {!deck ? <Empty>Open a deck. Tap a card to flip it.</Empty> : cards.isLoading && !fresh ? <p className="muted">Loading cards…</p> :
          shown?.length ? <div className="flashgrid">{shown.map((c: any) => <Flip key={c.id} c={c} />)}</div> : <Empty>No cards found for this deck’s topics.</Empty>}
      </Card>
    </div>
  );
}

// ---- Past papers ----
function Pyq() {
  const { subjectId } = useSubject();
  const [tab, setTab] = useState('important');
  const [pr, setPr] = useState<any>(null);
  const paths: Record<string, string> = { important: 'important-topics', trends: 'trends', topics: 'topics', revision: 'revision-plan' };
  const prac = useAct(() => api('/api/pyq/generate-practice', { method: 'POST', timeoutMs: 120_000, body: { subject_id: subjectId, count: 10 } }), { ok: 'Practice set ready.', onSuccess: setPr });
  return (
    <>
      <Tabs tabs={[['important', 'Important topics'], ['trends', 'Trends'], ['topics', 'Frequency'], ['revision', 'Revision plan']]} value={tab} onChange={setTab} />
      <Fetched title="Past-paper analysis" path={subjectId ? `/api/pyq/${paths[tab]}/${subjectId}` : null} empty="No past-paper data yet. Upload previous year papers (type PYQ)." />
      <Card title="Practice from past papers" actions={<button className="btn small primary" disabled={!subjectId || prac.isPending} onClick={() => prac.mutate()}>{prac.isPending ? 'Generating…' : 'Generate 10'}</button>}>
        {pr?.questions?.length ? <ol className="plain">{pr.questions.map((q: any, i: number) => <li key={i}><b>{q.question}</b><div className="muted">{q.topic} · {q.difficulty}{q.marks != null ? ` · ${q.marks} marks` : ''}</div></li>)}</ol> : <Empty>Generate practice questions modelled on previous exams.</Empty>}
      </Card>
    </>
  );
}

const mastery = (d: any) => <ul className="rows">{asList(d).map((m: any) => (
  <li key={m.id}><div className="grow"><div className="between"><b>{m.topic_name}</b><span className="muted">{Math.round(m.mastery_score)}% · {m.attempt_count} tries</span></div><Bar value={m.mastery_score} /></div></li>
))}</ul>;

function Mastery() {
  const sid = useStudentId();
  const { subjectId } = useSubject();
  return (
    <div className="grid2">
      <Fetched title="Needs work" path={`/api/mastery/weak/${sid}`} empty="No weak topics detected yet." render={mastery} />
      <Fetched title="Mastery in this subject" path={subjectId ? `/api/mastery/subject/${subjectId}` : null} query={{ student_id: sid }} empty="Practice to build mastery data." render={mastery} />
    </div>
  );
}

export default function Practice() {
  const [tab, setTab] = useState('practice');
  return (
    <>
      <PageHead title="Practice" sub="Practice, quizzes, flashcards and past-paper revision for your selected subject." />
      <Tabs tabs={[['practice', 'Practice'], ['quiz', 'Quiz lab'], ['cards', 'Flashcards'], ['pyq', 'Past papers'], ['mastery', 'Mastery']]} value={tab} onChange={setTab} />
      {tab === 'practice' && <AiPractice />}
      {tab === 'quiz' && <QuizLab />}
      {tab === 'cards' && <Flashcards />}
      {tab === 'pyq' && <Pyq />}
      {tab === 'mastery' && <Mastery />}
    </>
  );
}
