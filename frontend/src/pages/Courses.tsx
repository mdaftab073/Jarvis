import { useState } from 'react';
import { asList } from '../api/client';
import { useStudentId } from '../auth/AuthContext';
import { useSubject } from '../auth/SubjectContext';
import { Async, Card, CreateForm, PageHead } from '../components/ui';
import { useGet } from '../lib/hooks';

export default function Courses() {
  const sid = useStudentId();
  const { subjectId, setSubjectId } = useSubject();
  const [courseId, setCourseId] = useState<number | null>(null);
  const courses = useGet('/api/courses');
  const subjects = useGet(courseId ? `/api/courses/${courseId}/subjects` : null);
  const topics = useGet(subjectId ? `/api/subjects/${subjectId}/topics` : null, { limit: 500 });
  return (
    <>
      <PageHead title="Courses" sub="Create a course, add subjects, then pick a subject — it follows you across the app." />
      <div className="grid3">
        <Card title="Your courses">
          <Async q={courses} empty="No courses yet. Add your first one below.">
            {(d) => <div className="stack">{asList(d).map((c: any) => (
              <button key={c.id} className={`pick ${courseId === c.id ? 'on' : ''}`} onClick={() => setCourseId(c.id)}>{c.name}</button>
            ))}</div>}
          </Async>
        </Card>
        <Card title="Subjects">
          {!courseId ? <p className="empty">Select a course.</p> : (
            <Async q={subjects} empty="This course has no subjects yet.">
              {(d: any) => <div className="stack">{asList(d.subjects ?? d).map((s: any) => (
                <button key={s.id} className={`pick ${subjectId === s.id ? 'on' : ''}`} onClick={() => setSubjectId(s.id)}>{s.name}</button>
              ))}</div>}
            </Async>
          )}
        </Card>
        <Card title="Topics">
          {!subjectId ? <p className="empty">Select a subject.</p> : (
            <Async q={topics} empty="No topics yet. Upload a material, then use “Extract topics”.">
              {(d) => <ul className="plain">{asList(d).map((t: any) => <li key={t.id}>{t.name}</li>)}</ul>}
            </Async>
          )}
        </Card>
      </div>
      <div className="grid2">
        <Card title="Add a course">
          <CreateForm path="/api/courses" extra={{ student_id: sid }} invalidate={['/api/courses', '/api/subjects']} ok="Course added."
            fields={[{ name: 'name', label: 'Course name', required: true, placeholder: 'e.g. B.Tech Computer Engineering' }, { name: 'description', label: 'Description', type: 'textarea' }]} />
        </Card>
        <Card title="Add a subject">
          {!courseId ? <p className="empty">Select a course first.</p> : (
            <CreateForm path="/api/subjects" extra={{ course_id: courseId }} invalidate={['/api/courses', '/api/subjects']} ok="Subject added."
              fields={[{ name: 'name', label: 'Subject name', required: true, placeholder: 'e.g. Operating Systems' }, { name: 'description', label: 'Description', type: 'textarea' }]} />
          )}
        </Card>
      </div>
    </>
  );
}
