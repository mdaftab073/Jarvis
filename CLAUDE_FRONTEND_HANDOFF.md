# Claude Frontend Handoff

Contract snapshot: 2026-10-03
Frontend target: React + TypeScript + Vite
Backend: FastAPI + PostgreSQL; JSON API with JWT bearer authentication.

Use this document together with [`BACKEND_API_CONTRACT.md`](./BACKEND_API_CONTRACT.md), [`FRONTEND_ROUTE_MAP.md`](./FRONTEND_ROUTE_MAP.md), and the machine-readable [`docs/openapi.json`](./docs/openapi.json). The OpenAPI file is the frozen operation source of truth. Do not derive endpoints from service names or add unregistered HTTP operations.

## 1. Auth flow

1. Render Google Identity Services and receive a Google-issued ID token in the browser.
2. `POST /api/auth/google` with `{ "id_token": "<Google ID token>" }`.
3. Store returned `student.id` for client route/data scoping; backend identity remains the bearer token principal.
4. Send `Authorization: Bearer ${accessToken}` on all protected `/api/*` calls.
5. Call `GET /api/auth/me` to restore/validate the authenticated student.
6. On a protected request's 401, make one serialized `POST /api/auth/refresh` call with `{ "refresh_token": "<current refresh token>" }`. Replace both tokens because the previous refresh token has been rotated. Retry the failed operation no more than once.
7. Sign out through `POST /api/auth/logout` with both the access bearer and `{ "refresh_token": "<current refresh token>" }`. Clear local tokens and student state even if logout reports a network error.

Google login and refresh are public routes. Logout and `/auth/me` require the access bearer. Google claims must be the identity source; never send client-provided email/name/student ID as proof of identity. Access defaults to 15 minutes; refresh defaults to 30 days. Refresh JWT IDs are server-stored and rotated. Logout revokes the refresh token; existing access tokens remain valid until expiry.

The backend does not issue or read auth cookies. Recommended client storage is access token in memory and refresh token in `sessionStorage`; do not put bearer tokens in URLs or persistent `localStorage`. This storage recommendation is a frontend security choice, not behavior enforced by FastAPI.

## 2. API contracts and TypeScript interfaces

Base URL is deployment configuration; paths below are backend paths under `/api`. Use JSON unless an endpoint explicitly takes multipart form data.

```ts
export interface SuccessEnvelope<T> {
  success: true;
  data: T;
}

export interface ErrorEnvelope {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export type ApiEnvelope<T> = SuccessEnvelope<T> | ErrorEnvelope;

export interface StudentIdentity {
  id: number;
  email: string;
  full_name: string;
  profile_picture: string | null;
  is_verified: boolean;
}

export interface GoogleLoginRequest { id_token: string; }
export interface RefreshRequest { refresh_token: string; }

export interface AuthTokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface GoogleLoginData {
  student: StudentIdentity;
  tokens: AuthTokenPair;
}

export interface CurrentUserData {
  student: StudentIdentity;
  tokens: { token_type: "bearer"; expires_at: string };
}

export interface LogoutData {
  student: StudentIdentity;
  tokens: { token_type: "bearer"; revoked: boolean };
}

export interface ChatRequest {
  session_id?: number | null;
  student_id?: number | null;
  message: string;
}

export interface ChatResponse {
  session_id: number;
  user_message_id: number;
  assistant_message_id: number;
  answer: string;
  agent_used: string;
  tool_used: string | null;
  created_at: string;
}

export interface ChatSession {
  id: number;
  student_id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface CreateSessionRequest {
  student_id: number;
  title?: string | null;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: string;
  content: string;
  agent_name: string | null;
  tool_name: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface Course {
  id: number;
  name: string;
  description: string | null;
  student_id: number;
}

export interface CourseCreate {
  name: string;
  description?: string | null;
  student_id: number;
}

export interface CourseSubject { id: number; name: string; }

export interface CourseWithSubjects {
  id: number; name: string; description: string | null; subjects: CourseSubject[];
}

export interface Subject {
  id: number;
  name: string;
  description: string | null;
  course_id: number;
}

export interface SubjectCreate {
  name: string;
  description?: string | null;
  course_id: number;
}

export interface Topic {
  id: number;
  subject_id: number;
  name: string;
  description: string | null;
}

export type MaterialType = "NOTES" | "PYQ" | "SYLLABUS" | "REFERENCE";

export interface StudyMaterial {
  id: number;
  title: string;
  file_path: string;
  uploaded_at: string | null;
  subject_id: number;
  material_type: MaterialType;
  processing_job_id: number | null;
  processing_status: string | null;
}

export interface StudyMaterialUploadForm {
  title: string;
  subject_id: number;
  material_type?: MaterialType;
  file: File;
  student_id?: number;
}

export interface JobExecution {
  id: number;
  job_name: string;
  status: string;
  student_id: number | null;
  result_json: unknown;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  queue_time_seconds: number | null;
  duration_seconds: number | null;
  retry_count: number;
  error_message: string | null;
}

export interface AskRequest {
  question: string;
  subject_id?: number | null;
}

export interface AskResponse {
  answer: string;
  sources: Array<{ material_id: number; title: string; chunk_index: number }>;
  debug: { chunks_used: number; subject_detected: string | null } | null;
}

export interface QuizQuestionInput {
  topic_id?: number | null;
  question: string;
  question_type?: string;
  correct_answer: string;
}

export interface QuizGenerateRequest {
  student_id: number;
  subject_id: number;
  questions: QuizQuestionInput[];
}

export interface QuizSubmitRequest {
  session_id: number;
  answers: Array<{ question_id: number; student_answer: string }>;
  update_mastery?: boolean;
}

export interface QuizSession {
  id: number;
  student_id: number;
  subject_id: number;
  total_questions: number;
  score: number | null;
  started_at: string | null;
  completed_at: string | null;
}

export interface QuizQuestion {
  id: number;
  session_id: number;
  topic_id: number | null;
  question: string;
  question_type: string;
  correct_answer: string;
}

export interface QuizSessionWithQuestions {
  session: QuizSession;
  questions: QuizQuestion[];
}

export interface QuizSubmitResponse {
  session_id: number;
  score: number;
  total_questions: number;
  results: Array<{
    question_id: number;
    is_correct: boolean;
    correct_answer: string;
    student_answer: string;
  }>;
}

export interface FlashcardDeck {
  id: number;
  subject_id: number;
  name: string;
  created_at: string | null;
}

export interface Flashcard {
  id: number;
  deck_id: number;
  question: string;
  answer: string;
  difficulty: string;
  topic_id: number | null;
  created_at: string | null;
}

export interface FlashcardGenerateRequest {
  subject_id: number;
  deck_name: string;
  topics: string[];
  cards_per_topic?: number;
}

export interface FlashcardGenerateResponse {
  deck: FlashcardDeck;
  flashcards: Flashcard[];
}

export interface MasteryWithTopic {
  id: number;
  student_id: number;
  topic_id: number;
  topic_name: string;
  mastery_score: number;
  attempt_count: number;
}

export interface TopicPerformance {
  topic: string;
  attempts: number;
  correct_answers: number;
  incorrect_answers: number;
  confidence_score: number;
  mastery_score: number;
  last_practiced_at: string | null;
}

export interface SubjectAnalytics {
  subject_id: number;
  subject_name: string;
  readiness_score: number;
  status: string;
  plan_completion: number;
  pyq_coverage: number;
  weak_topics: Array<{
    topic: string; mastery: number; attempts: number; pyq_frequency: number;
  }>;
  strong_topics: Array<{
    topic: string; mastery: number; attempts: number; confidence_score: number;
  }>;
  recommendations: string[];
  topic_mastery: TopicPerformance[];
}

export interface AnalyticsDashboard {
  student_id: number;
  readiness_score: number;
  status: string;
  plan_completion: number;
  weak_topics: Array<{
    subject_id: number; topic: string; mastery: number;
    attempts: number; pyq_frequency: number;
  }>;
  strong_topics: Array<{
    subject_id: number; topic: string; mastery: number;
    attempts: number; confidence_score: number;
  }>;
  recommendations: string[];
  subjects: SubjectAnalytics[];
  practice_score_trend: Array<{ date: string; subject_id: number; score: number }>;
}

export interface ReadinessResponse {
  student_id: number;
  subject_id: number;
  readiness_score: number;
  status: string;
  topic_mastery: TopicPerformance[];
  plan_completion: number;
  pyq_coverage: number;
}

export interface PracticeStartRequest {
  student_id: number; subject_id: number; count?: number;
}

export interface PracticeStartResponse {
  session_id: number; student_id: number; subject_id: number;
  started_at: string; total_questions: number;
  questions: Array<{
    attempt_id: number; question: string; topic: string;
    difficulty: "Easy" | "Medium" | "Hard"; marks: number | null;
  }>;
}

export interface PracticeSubmitRequest {
  session_id: number;
  answers: Array<{
    attempt_id: number; student_answer: string; confidence_score?: number;
  }>;
}

export interface PracticeSubmitResponse {
  session_id: number; score: number; total_questions: number;
  correct_answers: number; accuracy: number; duration_seconds: number;
  topic_coverage: string[];
  results: Array<{
    attempt_id: number; topic: string; is_correct: boolean;
    score: number; feedback: string;
  }>;
}

export interface StudyPlanTask {
  id: number;
  day_number: number;
  scheduled_date: string;
  topic: string;
  priority: number;
  estimated_hours: number;
  status: string;
}

export interface StudyPlan {
  id: number;
  student_id: number;
  subject_id: number;
  subject_name: string;
  exam_date: string;
  start_date: string;
  hours_per_day: number;
  created_at: string;
  progress: { completion: number; tasks_done: number; tasks_remaining: number };
  daily_agenda: Array<{
    day_number: number;
    date: string;
    tasks: StudyPlanTask[];
  }>;
}

export interface ProfileResponse {
  student_id: number;
  preferred_study_hours: number | null;
  preferred_subjects: string[];
  current_goal: string | null;
  strengths: string[];
  weaknesses: string[];
  study_habits: string[];
  readiness_trend: number[];
}

export interface StudentAcademicProfile {
  id: number; student_id: number; enrollment_number: string | null;
  branch: string | null; department: string | null; semester: number | null;
  section: string | null; batch_year: number | null; current_cpi: number | null;
  current_spi: number | null; total_credits: number | null; earned_credits: number | null;
  academic_status: string; created_at: string; updated_at: string;
}

export interface AttendanceRecord {
  id: number; student_id: number; academic_profile_id: number; subject_id: number;
  attended_classes: number; total_classes: number;
  attendance_percentage: number | null; last_updated: string;
}

export interface GradeRecord {
  id: number; student_id: number; academic_profile_id: number; subject_id: number;
  component_type: string; obtained_marks: number | null; max_marks: number;
  grade: string | null; grade_type: "COMPONENT" | "FINAL";
  semester: number | null; credits: number | null; grade_points: number | null;
  recorded_at: string;
}

export interface Goal {
  id: number; student_id: number; title: string;
  goal_type: "SEMESTER" | "CPI" | "ATTENDANCE" | "PLACEMENT" | "STUDY_HOURS";
  target_value: number | null; target_unit: string | null; target_date: string | null;
  completed: boolean; current_value: number; progress_percent: number | null;
  milestones: GoalMilestone[]; created_at: string;
}

export interface GoalMilestone {
  id: number; student_id: number; goal_id: number; title: string;
  target_value: number | null; target_date: string | null;
  completed: boolean; completed_at: string | null;
}

export interface DeadlineItem {
  id: number; student_id: number; subject_id: number | null;
  title: string; description: string | null; type: string; due_date: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"; completed: boolean;
}

export interface CalendarEvent {
  id: number; student_id: number; title: string; description: string | null;
  start_time: string; end_time: string; event_type: string;
}

export interface Reminder {
  id: number; student_id: number; title: string; trigger_time: string; completed: boolean;
}

export interface StudentNotification {
  id: number; student_id: number; title: string; message: string;
  notification_type: "INFO" | "SUCCESS" | "WARNING" | "CRITICAL" | "REMINDER";
  read: boolean; created_at: string;
}

export interface StudyBlock {
  id: number; student_id: number; subject_id: number | null;
  start_time: string; end_time: string; planned_duration: number;
  title: string | null;
  block_type: "STUDY" | "REVISION" | "ATTENDANCE_RECOVERY" | "DEADLINE_PREP" | "GOAL";
  completed: boolean;
}

export interface AgendaItem {
  kind: "CALENDAR" | "STUDY_BLOCK" | "DEADLINE" | "REMINDER";
  title: string; start_time: string; end_time: string | null;
  event_type: string; id: number; subject_id?: number;
  completed?: boolean; priority?: string;
}

export interface Agenda { student_id: number; date: string; items: AgendaItem[]; }
export interface WeekAgenda { student_id: number; start_date: string; days: Agenda[]; }

export interface GoalCreateInput {
  title: string;
  goal_type: "SEMESTER" | "CPI" | "ATTENDANCE" | "PLACEMENT" | "STUDY_HOURS";
  target_value?: number | null; target_unit?: string | null; target_date?: string | null;
}

export interface AttendanceInput {
  subject_id: number; attended_classes: number; total_classes: number;
}

export interface CalendarEventInput {
  title: string; description?: string | null;
  start_time: string; end_time: string; event_type?: string;
}

export interface ReminderInput { title: string; trigger_time: string; }

export interface NotificationInput {
  title: string; message: string;
  notification_type?: "INFO" | "SUCCESS" | "WARNING" | "CRITICAL" | "REMINDER";
}

export interface StudyPlanGenerateRequest {
  student_id: number; subject_id: number; exam_date: string;
  hours_per_day: number; subject_difficulty?: number;
}

export interface StudyBlockInput {
  subject_id?: number | null; title?: string | null;
  block_type?: "STUDY" | "REVISION" | "ATTENDANCE_RECOVERY" | "DEADLINE_PREP" | "GOAL";
  start_time: string; end_time: string; planned_duration?: number | null;
}

export interface ScheduleInput {
  subject_ids: number[]; start_time: string;
  session_length?: number; break_minutes?: number;
}

export interface IntelligentScheduleInput {
  start_time: string; available_hours: number;
  horizon_days?: number; session_minutes?: number;
}

export interface ProfileInput {
  enrollment_number?: string | null; branch?: string | null;
  department?: string | null; semester?: number | null; section?: string | null;
  batch_year?: number | null; current_cpi?: number | null; current_spi?: number | null;
  earned_credits?: number | null; total_credits?: number | null;
  academic_status?: "ACTIVE" | "PROBATION" | "GRADUATED" | "SUSPENDED" | "DROPOUT" | null;
}

export interface PreferenceInput {
  preferred_study_time?: string | null;
  preferred_session_length?: number | null;
  study_style?: string | null;
}

export interface GradeInput {
  subject_id: number;
  semester?: number | null;
  credits?: number | null;
  grade?: string | null;
  grade_points?: number | null;
  grade_type?: "COMPONENT" | "FINAL";
  component_type?: "CT1" | "CT2" | "CT3" | "ASSIGNMENT" | "LAB" | "END_SEM" | "MID_SEM" | "VIVA" | "PROJECT" | "OTHER";
  obtained_marks?: number | null;
  max_marks?: number;
  grade_letter?: string | null;
}

export interface DashboardData {
  student_id: number;
  profile: StudentAcademicProfile | null;
  attendance: Array<{
    record: AttendanceRecord;
    risk: "UNKNOWN" | "SAFE" | "WARNING" | "CRITICAL";
    classes_to_recover: number;
  }>;
  mastery: Array<{ topic_id: number; mastery_score: number }>;
  readiness: number | null;
  grades: GradeRecord[];
  grade_analytics: {
    spi_by_semester: Record<string, number | null>;
    cpi: number | null; record_count: number; current_spi: number | null;
  };
  deadlines: DeadlineItem[];
  notifications: StudentNotification[];
  calendar: CalendarEvent[];
  agenda_today: Agenda;
  agenda_week: WeekAgenda;
  goals: Goal[];
  goal_progress: Array<{
    goal_id: number; title: string; progress_percent: number | null; completed: boolean;
  }>;
  productivity: {
    student_id: number; productivity_score: number; consistency_score: number;
    study_hours_7d: number; study_minutes_7d: number; completion_rate: number;
    habit_streaks: Array<{
      habit_id: number; habit_name: string; current_streak: number;
      longest_streak: number; completion_rate: number;
    }>;
    procrastination_risks: Array<
      | { type: "OVERDUE_DEADLINE"; count: number }
      | { type: "MISSED_HABIT"; habits: string[] }
      | { type: "PROCRASTINATION"; completion_rate: number }
    >;
    suggestions: string[]; window_start: string; window_end: string;
  };
  productivity_score: number; consistency_score: number; study_hours_7d: number;
  completion_rate: number;
  habit_streaks: Array<{
    habit_id: number; habit_name: string; current_streak: number;
    longest_streak: number; completion_rate: number;
  }>;
  readiness_snapshot: { score: number | null; captured_at: string } | null;
}
```

The code block includes the traced `GET /api/dashboard/{student_id}` aggregate plus the core raw row types. Do not change unconstrained backend fields into TypeScript `any`; keep them `unknown` or use the exact traced interfaces in [`BACKEND_API_CONTRACT.md`](./BACKEND_API_CONTRACT.md). For other OpenAPI `Any` operations, the generated contract may not include a fully stable DTO.

## 3. Frontend route map

Implement the browser route structure and page mapping in [`FRONTEND_ROUTE_MAP.md`](./FRONTEND_ROUTE_MAP.md). Key routes are `/dashboard`, `/chat/new`, `/chat/:sessionId`, `/exam-prep/:subjectId`, `/materials/:materialId`, `/quizzes/:sessionId`, `/flashcards/decks/:deckId`, `/mastery/:subjectId`, `/analytics`, `/planner`, `/notifications`, and `/profile`.

## 4. State management requirements

- Keep auth state (student identity and tokens) in one auth provider/store. Do not make every page independently refresh credentials.
- Keep the selected course/subject and route resource IDs in URL/UI state; backend endpoints require numeric IDs.
- Use server-state caching for list/detail queries and invalidate affected queries after mutations (chat send, quiz submit, task completion, event changes, material upload, notification read).
- Keep form drafts and unsent chat text in local component state; do not persist bearer tokens with page state.
- Ensure refresh is single-flight: queue concurrent 401 requests behind one refresh request so the refresh token is not concurrently reused after rotation.
- Treat a 401 from `/auth/me` or failed refresh as signed out. Treat 403 as an ownership/permission denial, not a sign-in retry.

## 5. Token handling requirements

- Access token goes in the Authorization header as `Bearer <token>`, never as a query parameter.
- Refresh uses JSON `{ refresh_token }`; it does not use a cookie or Authorization refresh scheme.
- Replace access and refresh token together after refresh. Reuse of the old refresh token fails.
- On logout, call the protected logout endpoint with access bearer and refresh token body, then clear client state regardless of response outcome.
- Default access lifetime is 900 seconds; refresh lifetime is 30 days. Backend configuration may alter these defaults.

## 6. Error handling requirements

Parse the exact error envelope `{"success": false, "error": {"code": string, "message": string}}`. Preserve HTTP status alongside the envelope. Do not expect field-level validation details: 422 returns `validation_error` and `Request validation failed.`.

Handle at least:

- 401: missing/expired/invalid access token; attempt one refresh for protected requests.
- 403: authenticated identity does not own requested resource.
- 404: missing record, or production-hidden diagnostic route.
- 409: conflicting schedule/calendar action, completed/duplicate/invalid state.
- 413: upload exceeds limit.
- 422: invalid request payload or domain validation.
- 429: rate limit exceeded; respect a retry delay if supplied by infrastructure.
- 500/503: show recoverable service errors; do not silently show success-shaped data.

The backend's exception handler can return generic messages for some errors; show `error.message` and preserve status/code for logs and support.

## 7. Loading state requirements

- Show initial/refresh loading states for identity, dashboards, selected subject data, chat transcript, and history.
- Distinguish empty lists from request failures.
- Keep submitted state visible while chat or quiz submissions are pending; prevent accidental duplicate sends/submissions.
- For background material/alert jobs, show current `status`; poll the job endpoint using a bounded interval and stop when a terminal state is received or the page is abandoned. Do not assume a fixed processing duration.
- For asynchronous upload, distinguish "uploaded/queued" from "processed/embedded"; HTTP 202 does not mean processing has completed.

## 8. Pagination requirements

There is no universal pagination response wrapper, total count, cursor, or `next` field. Pagination parameters/results are endpoint-specific:

- Chat sessions: `limit` 1–200, default 50; no offset.
- Chat messages: `limit` 1–1000, default 100; `offset` >=0, default 0.
- Quiz history: `skip` >=0, default 0; `limit` 1–200, default 50.
- Topics, flashcard decks/cards, and mastery student list: `skip` >=0, default 0; `limit` endpoint max 500, generally default 100.
- Other listed collections do not accept pagination parameters. Do not invent response totals.

## 9. File upload flow

1. Select an existing subject from `/api/courses` and `/api/courses/{course_id}/subjects`.
2. Send `multipart/form-data` to `POST /api/materials/upload` with `title`, `subject_id`, `file`, optional `material_type` (defaults to `NOTES`), and optional `student_id`.
3. Use a PDF file with `.pdf` extension and MIME `application/pdf`; backend validates `%PDF-` signature and limits bytes to 25 MiB by default.
4. Read returned `data.processing_job_id` and `data.processing_status`.
5. Poll `GET /api/jobs/{job_id}?student_id={student_id}`; display terminal status and `error_message` where present.
6. Refresh the material list. Topic extraction is a separate `POST /api/topics/extract/{material_id}?subject_id={subject_id}` action. Embedding can be enqueued using `POST /api/materials/{material_id}/embed`.
7. No HTTP delete material route exists.

## 10. Chat flow

- Load sidebar sessions with `GET /api/chat/sessions?student_id={id}&limit=50`.
- Submit a new message via `POST /api/chat` with `message` and optional `session_id`; an absent ID starts a new session and the response returns its `session_id`.
- Load existing transcript with `GET /api/chat/sessions/{session_id}/messages?limit=100&offset=0`; fetch older messages by increasing offset.
- Response is a complete JSON answer. No streaming, SSE, or websocket API is registered.
- Keep separate loading/error states per conversation and never cross-populate messages between sessions.

## 11. Quiz flow

- Load subject and topic IDs; `POST /api/quizzes/generate` accepts a client-provided `questions` array. It does not generate questions from a subject by itself.
- Response includes session plus questions. The actual response exposes `correct_answer` before submit. Do not display it before the user answers, but do not claim the backend withholds it.
- Submit `{ session_id, answers: [{ question_id, student_answer }], update_mastery? }` to `/api/quizzes/submit`.
- Render score/results from the response; `update_mastery` defaults true and updates are persisted.
- Use `/api/quizzes/history/{student_id}` for history; use `/api/quizzes/session/{session_id}` to reload session/questions.

## 12. Analytics flow

- Dashboard: `GET /api/analytics/dashboard/{student_id}` for readiness, status, plan completion, subject summaries, topic categories, recommendations, and practice-score trend.
- Subject detail: `GET /api/analytics/readiness/{student_id}/{subject_id}` plus weak/strong topics and recommendations endpoints.
- Mastery page: `/api/mastery/student/{student_id}`, `/api/mastery/subject/{subject_id}?student_id=...`, and `/api/mastery/weak/{student_id}`.
- Profile trend: `GET /api/profile/{student_id}/readiness-history`.
- A separate legacy aggregate exists at `GET /api/dashboard/{student_id}`; its detailed runtime shape is in the API contract. Do not treat it as equivalent to `AnalyticsDashboard`.

## 13. Dashboard flow

1. Resolve identity with `/api/auth/me`.
2. Load `/api/courses` and `/api/analytics/dashboard/{student_id}`.
3. Load the combined student-OS aggregate `/api/dashboard/{student_id}` only if the page needs its attendance, grade, goal, deadline, calendar, productivity, and notification data.
4. Render empty states where returned collections are empty; readiness can be null in the aggregate dashboard or zero in the analytics dashboard when no subject analytics are available.
5. Refresh the appropriate data after user mutations; do not synthesize fields that the endpoint did not return.

## 14. Exam preparation and study planner flow

- Use the route map's selected subject ID for topics, materials, readiness, mastery, quiz, flashcard, and plan calls.
- Generate a plan with `{ student_id, subject_id, exam_date, hours_per_day, subject_difficulty? }` at `POST /api/study-plans/generate`.
- Load plan by ID; complete an individual task via `PATCH /api/study-plans/tasks/{task_id}/complete` with no body; query progress separately if needed; recalculate using POST with no body.
- Use calendar day/week endpoints for agenda. Calendar event payloads require title/start/end, and end must be later than start.
- Study-block generation is separate from study-plan generation. Study blocks can fail with 409 for conflicts.

## 15. Backend limitations the UI must preserve

- OpenAPI has no security declaration although middleware enforces bearer authentication.
- 92 operation success payloads use unconstrained `Any`; the endpoint-by-endpoint known runtime structures and remaining gaps are listed in the backend contract.
- No material delete, generic search, client OAuth redirect, streaming chat, or backend-generated quiz-question route is registered.
- No study-plan list endpoint is registered; retain a generated plan's returned ID to reopen it.
- CORS only permits configured exact origins; production rejects wildcard origins.
- Do not treat HTTP 202 as completed background work.
- No frontend has been assumed or edited by this handoff task.
