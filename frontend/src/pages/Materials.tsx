import { FormEvent, useState } from 'react';
import { api, asList } from '../api/client';
import { useStudentId } from '../auth/AuthContext';
import { SubjectPicker, useSubject, useSubjectNames } from '../auth/SubjectContext';
import { JobStatus } from '../components/Job';
import { Async, Card, Chip, Empty, PageHead } from '../components/ui';
import { useAct, useGet, useToast } from '../lib/hooks';

const MAX = 25 * 1024 * 1024;
const TYPES = ['NOTES', 'PYQ', 'SYLLABUS', 'REFERENCE'];

function MaterialRow({ m }: { m: any }) {
  const [view, setView] = useState<'' | 'text'>('');
  const [jobId, setJobId] = useState<number | null>(m.processing_job_id ?? null);
  const name = useSubjectNames();
  const embed = useAct(() => api(`/api/materials/${m.id}/embed`, { method: 'POST' }), { ok: 'Indexing started.', onSuccess: (r: any) => setJobId(r?.id ?? null) });
  const extract = useAct(() => api(`/api/topics/extract/${m.id}`, { method: 'POST', query: { subject_id: m.subject_id }, timeoutMs: 120_000 }),
    { ok: 'Topics extracted.', invalidate: ['/api/subjects', '/api/topics'] });
  const detail = useGet(view ? `/api/materials/${m.id}/extract-text` : null);
  const processingStatus = m.processing_status ?? m.embedding_status;
  const statusLabel = processingStatus === 'embedded'
    ? 'Ready for AI Analysis'
    : processingStatus === 'failed'
      ? 'Failed'
      : processingStatus
        ? 'Processing'
        : null;
  return (
    <div className="item">
      <div className="between"><strong>{m.title}</strong><Chip>{(m.material_type ?? 'NOTES').toLowerCase()}</Chip></div>
      <p className="muted">{name(m.subject_id)}{statusLabel ? ` · ${statusLabel}` : ''}</p>
      {jobId && <JobStatus jobId={jobId} invalidate={['/api/materials', '/api/subjects']} />}
      <div className="row">
        <button className="btn small" onClick={() => setView(view === 'text' ? '' : 'text')}>Extracted text</button>
        <button className="btn small" disabled={embed.isPending} onClick={() => embed.mutate()}>Make searchable</button>
        <button className="btn small" disabled={extract.isPending} onClick={() => extract.mutate()}>{extract.isPending ? 'Extracting…' : 'Extract topics'}</button>
      </div>
      {view && (
        <div className="scroll">
          <Async q={detail} empty="Nothing extracted yet.">
            {(d: any) => (
              <>
                <h3>{d.title}</h3>
                <p className="pre">{d.text}</p>
                {String(d.text ?? '').length >= 5000 && <p className="muted">Showing the first 5,000 characters.</p>}
              </>
            )}
          </Async>
        </div>
      )}
    </div>
  );
}

function Upload() {
  const sid = useStudentId();
  const { subjectId } = useSubject();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [type, setType] = useState('NOTES');
  const [jobId, setJobId] = useState<number | null>(null);
  const up = useAct((fd: FormData) => api('/api/materials/upload', { method: 'POST', form: fd, timeoutMs: 180_000 }), {
    ok: 'Upload accepted — processing in the background.', invalidate: ['/api/materials', '/api/subjects'],
    onSuccess: (r: any) => { setJobId(r?.processing_job_id ?? null); setFile(null); setTitle(''); },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    if (!/\.pdf$/i.test(file.name) || (file.type && file.type !== 'application/pdf')) return toast('err', 'Only PDF files are supported.');
    if (file.size > MAX) return toast('err', 'That file is over the 25 MB limit.');
    if (!subjectId) return toast('err', 'Choose a subject first.');
    const fd = new FormData();
    fd.append('title', title.trim() || file.name.replace(/\.pdf$/i, ''));
    fd.append('subject_id', String(subjectId));
    fd.append('material_type', type);
    fd.append('student_id', String(sid));
    fd.append('file', file);
    up.mutate(fd);
  };
  return (
    <Card title="Upload a PDF">
      <form className="stack" onSubmit={submit}>
        <label className="field"><span>PDF (up to 25 MB)</span><input type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
        <label className="field"><span>Title</span><input value={title} placeholder="Defaults to the file name" onChange={(e) => setTitle(e.target.value)} /></label>
        <label className="field"><span>Type</span><select value={type} onChange={(e) => setType(e.target.value)}>{TYPES.map((t) => <option key={t}>{t}</option>)}</select></label>
        <button className="btn primary" disabled={!file || up.isPending}>{up.isPending ? 'Uploading…' : 'Upload'}</button>
        {!subjectId && <Empty>Choose a subject above or from Courses first.</Empty>}
      </form>
      {jobId && <JobStatus jobId={jobId} invalidate={['/api/materials', '/api/subjects']} />}
    </Card>
  );
}

function Ask() {
  const { subjectId } = useSubject();
  const [question, setQ] = useState('');
  const ask = useAct(() => api('/api/rag/ask', { method: 'POST', body: { question, subject_id: subjectId }, timeoutMs: 120_000 }));
  const d: any = ask.data;
  return (
    <Card title="Ask your materials">
      <form className="stack" onSubmit={(e) => { e.preventDefault(); if (question.trim()) ask.mutate(); }}>
        <label className="field"><span>Question</span><input value={question} onChange={(e) => setQ(e.target.value)} placeholder="What does chapter 3 say about…" /></label>
        <button className="btn primary" disabled={ask.isPending || !subjectId}>{ask.isPending ? 'Searching…' : 'Ask'}</button>
        {!subjectId && <Empty>Choose a subject first.</Empty>}
      </form>
      {d && (
        <div className="answer">
          <p className="pre">{d.answer}</p>
          {d.sources?.length > 0 && <><h3>Sources</h3><ul className="plain">{d.sources.map((s: any, i: number) => <li key={i}>{s.title}</li>)}</ul></>}
        </div>
      )}
    </Card>
  );
}

export default function Materials() {
  const sid = useStudentId();
  const { subjectId } = useSubject();
  const list = useGet(subjectId ? `/api/subjects/${subjectId}/materials` : '/api/materials', subjectId ? undefined : { student_id: sid });
  return (
    <>
      <PageHead title="Study materials" sub="Upload notes and past papers, then search or study from them." actions={<SubjectPicker />} />
      <div className="grid2"><Upload /><Ask /></div>
      <Card title={subjectId ? 'Materials in this subject' : 'All your materials'}>
        <Async q={list} empty="No materials yet. Upload a PDF to begin.">
          {(d) => <div className="stack">{asList(d).map((m: any) => <MaterialRow key={m.id} m={m} />)}</div>}
        </Async>
      </Card>
    </>
  );
}
