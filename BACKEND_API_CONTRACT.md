# Jarvis Backend API Contract

Contract snapshot: 2026-10-03
Source of truth: [`docs/openapi.json`](./docs/openapi.json), generated from the registered FastAPI application.
Implementation cross-check: `backend/app/api/routes/`, `backend/app/schemas/`, and `backend/app/services/`.

## Contract scope and caveats

- The generated OpenAPI document is OpenAPI 3.1.0 with 133 paths, 159 operations, and 160 component schemas.
- All success responses are wrapped in the success envelope below. An OpenAPI response named `SuccessResponse_Any_` has no specified inner `data` schema; consult the runtime notes below for the frontend-facing `Any` endpoints.
- OpenAPI does not declare bearer security schemes or per-operation security requirements. Authentication below is read from `StudentIdentityMiddleware` and the actual route guards.
- The generated inventory and complete request/status listing remain available in [`docs/API_INVENTORY.md`](./docs/API_INVENTORY.md) and [`docs/FRONTEND_API_REFERENCE.md`](./docs/FRONTEND_API_REFERENCE.md). The OpenAPI file is the complete machine-readable operation contract.
- Path parameters named `student_id` are scope-checked against the authenticated student; they do not let the client act as another student.

## Envelope

Every successful route is wrapped by `envelope_routes`:

```json
{
  "success": true,
  "data": {}
}
```

`success` is a boolean that defaults to `true`; `data` is the serialized route result. For a list response, `data` is an array; `204` is not the normal deletion contract—delete handlers return JSON data.

HTTP, validation, rate-limit, middleware, and unexpected errors use:

```json
{
  "success": false,
  "error": {
    "code": "unauthorized",
    "message": "Authentication required."
  }
}
```

`error.code` and `error.message` are strings. Standard status-to-code mappings are: 400 `bad_request`, 401 `unauthorized`, 403 `forbidden`, 404 `not_found`, 409 `conflict`, 413 `payload_too_large`, 422 `validation_error`, and 429 `rate_limited`; other HTTP errors use `http_<status>`. A request-validation failure uses the fixed message `Request validation failed.` and does not return Pydantic's field-error array. Unexpected errors use 500 / `internal_server_error` / `An unexpected error occurred.` Service-unavailable auth configuration can return 503 / `authentication_unavailable`.

## Authentication

### `POST /api/auth/google` — public

Request (`application/json`):

```json
{ "id_token": "GOOGLE_ISSUED_ID_TOKEN" }
```

`id_token` is a required non-empty string. The backend verifies Google's token signature, issuer, audience (`GOOGLE_CLIENT_ID`), expiry, subject, and verified email. Identity attributes must come from Google's token; do not submit a trusted student ID, email, name, or picture.

Success `data`:

```json
{
  "student": {
    "id": 17,
    "email": "student@example.edu",
    "full_name": "Student Name",
    "profile_picture": "https://example.invalid/avatar",
    "is_verified": true
  },
  "tokens": {
    "access_token": "JWT",
    "refresh_token": "JWT",
    "token_type": "bearer",
    "expires_in": 900
  }
}
```

`profile_picture` is nullable; the other student fields are present. `expires_in` is seconds (default 900).

### `POST /api/auth/refresh` — public; refresh token in JSON

Request:

```json
{ "refresh_token": "CURRENT_REFRESH_JWT" }
```

Success `data` has the same `student` shape and token pair as Google login. Refresh tokens are rotated: the submitted token is revoked and a new pair is issued. A reused, expired, revoked, wrong-purpose, or otherwise invalid refresh token returns 401.

### `POST /api/auth/logout` — access bearer required, refresh token in JSON

Request:

```json
{ "refresh_token": "CURRENT_REFRESH_JWT" }
```

Success `data`:

```json
{
  "student": {
    "id": 17,
    "email": "student@example.edu",
    "full_name": "Student Name",
    "profile_picture": null,
    "is_verified": true
  },
  "tokens": { "token_type": "bearer", "revoked": true }
}
```

Logout revokes that refresh token only. An already issued access token remains valid until expiry, so the client must discard both tokens immediately.

### `GET /api/auth/me` — access bearer required

No request body or query parameters.

Success `data`:

```json
{
  "student": {
    "id": 17,
    "email": "student@example.edu",
    "full_name": "Student Name",
    "profile_picture": null,
    "is_verified": true
  },
  "tokens": {
    "token_type": "bearer",
    "expires_at": "2026-10-03T12:00:00+00:00"
  }
}
```

### JWT and storage facts

- Default access-token lifetime: 15 minutes. Default refresh-token lifetime: 30 days. Values are configurable by `ACCESS_TOKEN_EXPIRE_MINUTES` and `REFRESH_TOKEN_EXPIRE_DAYS`.
- JWT claims include string `sub` (student ID), `typ` (`access` or `refresh`), `jti`, `iat`, and `exp`. The API uses `Authorization: Bearer ${accessToken}` for protected requests.
- Refresh-token JTIs are stored server-side, rotated on refresh, and revoked on logout.
- The backend sets no auth cookies. It expects the refresh token in a JSON request body and the access token in the Authorization header. Frontend storage is therefore a client decision, not a backend-provided cookie contract. Recommended frontend policy: keep the access token in memory and the refresh token in `sessionStorage` for the current tab only; clear both on logout and failed refresh. Do not put either token in URLs.
- Middleware permits public `/api/auth/google`, `/api/auth/refresh`, and health routes. Other `/api/*` requests require the access bearer in strict-auth mode. `/api/metrics/summary` additionally requires `X-Admin-Token` and is not a student-facing feature.

## Feature contracts

All paths below are prefixed with `/api`. Unless marked otherwise, require `Authorization: Bearer ${accessToken}`. Every JSON success payload listed is inside `data`.

### Dashboard and student academic data

| Method and path | Request | Runtime `data` |
|---|---|---|
| `GET /dashboard/{student_id}` | Path `student_id: integer` | `DashboardData` below. OpenAPI inner response is `Any`. |
| `GET /analytics/dashboard/{student_id}` | Path `student_id: integer` | `AnalyticsDashboard` below. |
| `GET /analytics/readiness/{student_id}/{subject_id}` | Both path IDs are integers | `ReadinessResponse` below. |
| `GET /analytics/weak-topics/{student_id}/{subject_id}` | Both path IDs are integers | Array of `{ topic: string, mastery: number, attempts: integer, pyq_frequency: integer }`. |
| `GET /analytics/strong-topics/{student_id}/{subject_id}` | Both path IDs are integers | Array of `{ topic: string, mastery: number, attempts: integer, confidence_score: number }`. |
| `GET /analytics/recommendations/{student_id}/{subject_id}` | Both path IDs are integers | Array of recommendation strings. |
| `GET /attendance/{student_id}` | Path ID | Array of `{ record: AttendanceRecord, risk: "UNKNOWN" \| "SAFE" \| "WARNING" \| "CRITICAL", classes_to_recover: integer }`. |
| `POST /attendance/{student_id}` | `AttendanceInput` below | Upserted `AttendanceRecord` |
| `GET /grades/{student_id}` | Path ID | Array of grade-record ORM rows. Fields are listed in `GradeRecord` below. |
| `POST /grades/{student_id}` | `GradeInput` below | Created `GradeRecord` |
| `GET /grades/{student_id}/analytics` | Path ID | `{ spi_by_semester: Record<string, number \| null>, cpi: number \| null, record_count: integer, current_spi: number \| null }`. |

`GET /dashboard/{student_id}` runtime `data` keys:

```ts
interface DashboardData {
  student_id: number;
  profile: AcademicProfileWithCurrentGrades | null;
  attendance: AttendanceSummary[];
  mastery: Array<{ topic_id: number; mastery_score: number }>;
  readiness: number | null;
  grades: GradeRecord[];
  grade_analytics: GradeAnalytics;
  deadlines: DeadlineItem[];
  notifications: StudentNotification[];
  calendar: CalendarEvent[];
  agenda_today: Agenda;
  agenda_week: WeekAgenda;
  goals: Goal[];
  goal_progress: Array<{
    goal_id: number;
    title: string;
    progress_percent: number | null;
    completed: boolean;
  }>;
  productivity: Productivity;
  productivity_score: number;
  consistency_score: number;
  study_hours_7d: number;
  completion_rate: number;
  habit_streaks: HabitStreakSummary[];
  readiness_snapshot: { score: number | null; captured_at: string } | null;
}
```

The profile contains the `StudentAcademicProfile` columns plus `current_cpi` and `current_spi` from grade analytics: `id`, `student_id`, `enrollment_number`, `branch`, `department`, `semester`, `section`, `batch_year`, `current_cpi`, `current_spi`, `total_credits`, `earned_credits`, `academic_status`, `created_at`, `updated_at`. Optional academic fields are nullable.

`AnalyticsDashboard` fields: `student_id: number`, `readiness_score: number`, `status: string`, `plan_completion: number`, `weak_topics: Array<{ subject_id: number; topic: string; mastery: number; attempts: number; pyq_frequency: number }>`, `strong_topics: Array<{ subject_id: number; topic: string; mastery: number; attempts: number; confidence_score: number }>`, `recommendations: string[]`, `subjects: SubjectAnalytics[]`, and `practice_score_trend: Array<{ date: string; subject_id: number; score: number }>`.

Each `SubjectAnalytics` has `subject_id`, `subject_name`, `readiness_score`, `status`, `plan_completion`, `pyq_coverage`, `weak_topics`, `strong_topics`, `recommendations`, and `topic_mastery`. `topic_mastery` elements have `topic`, `attempts`, `correct_answers`, `incorrect_answers`, `confidence_score`, `mastery_score`, and nullable `last_practiced_at`.

`ReadinessResponse` has `student_id`, `subject_id`, `readiness_score`, `status`, `topic_mastery` (same structure above), `plan_completion`, and `pyq_coverage`.

The `/dashboard/{student_id}` runtime nested field types are:

```ts
interface AcademicProfileWithCurrentGrades {
  id: number; student_id: number; enrollment_number: string | null;
  branch: string | null; department: string | null; semester: number | null;
  section: string | null; batch_year: number | null; current_cpi: number | null;
  current_spi: number | null; total_credits: number | null; earned_credits: number | null;
  academic_status: string; created_at: string; updated_at: string;
}
interface AttendanceRecord {
  id: number; student_id: number; academic_profile_id: number; subject_id: number;
  attended_classes: number; total_classes: number;
  attendance_percentage: number | null; last_updated: string;
}
interface AttendanceSummary {
  record: AttendanceRecord;
  risk: "UNKNOWN" | "SAFE" | "WARNING" | "CRITICAL";
  classes_to_recover: number;
}
interface GradeRecord {
  id: number; student_id: number; academic_profile_id: number; subject_id: number;
  component_type: string; obtained_marks: number | null; max_marks: number;
  grade: string | null; grade_type: "COMPONENT" | "FINAL";
  semester: number | null; credits: number | null; grade_points: number | null;
  recorded_at: string;
}
interface GradeAnalytics {
  spi_by_semester: Record<string, number | null>;
  cpi: number | null; record_count: number; current_spi: number | null;
}
interface Goal {
  id: number; student_id: number; title: string;
  goal_type: "SEMESTER" | "CPI" | "ATTENDANCE" | "PLACEMENT" | "STUDY_HOURS";
  target_value: number | null; target_unit: string | null; target_date: string | null;
  completed: boolean; current_value: number; progress_percent: number | null;
  milestones: GoalMilestone[]; created_at: string;
}
interface GoalMilestone {
  id: number; student_id: number; goal_id: number; title: string;
  target_value: number | null; target_date: string | null;
  completed: boolean; completed_at: string | null;
}
interface DeadlineItem {
  id: number; student_id: number; subject_id: number | null;
  title: string; description: string | null; type: string; due_date: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"; completed: boolean;
}
interface CalendarEvent {
  id: number; student_id: number; title: string; description: string | null;
  start_time: string; end_time: string; event_type: string;
}
interface Reminder {
  id: number; student_id: number; title: string; trigger_time: string; completed: boolean;
}
interface StudentNotification {
  id: number; student_id: number; title: string; message: string;
  notification_type: "INFO" | "SUCCESS" | "WARNING" | "CRITICAL" | "REMINDER";
  read: boolean; created_at: string;
}
interface HabitStreakSummary {
  habit_id: number; habit_name: string; current_streak: number;
  longest_streak: number; completion_rate: number;
}
interface Productivity {
  student_id: number; productivity_score: number; consistency_score: number;
  study_hours_7d: number; study_minutes_7d: number; completion_rate: number;
  habit_streaks: HabitStreakSummary[];
  procrastination_risks: Array<
    | { type: "OVERDUE_DEADLINE"; count: number }
    | { type: "MISSED_HABIT"; habits: string[] }
    | { type: "PROCRASTINATION"; completion_rate: number }
  >;
  suggestions: string[]; window_start: string; window_end: string;
}
interface Habit {
  id: number; student_id: number; habit_name: string; category: string;
  target_per_week: number; active: boolean; created_at: string;
}
interface HabitLog {
  id: number; student_id: number; habit_id: number; log_date: string;
  completed: boolean; duration_minutes: number | null; notes: string | null;
  created_at: string;
}
interface StudyBlock {
  id: number; student_id: number; subject_id: number | null;
  start_time: string; end_time: string; planned_duration: number;
  title: string | null;
  block_type: "STUDY" | "REVISION" | "ATTENDANCE_RECOVERY" | "DEADLINE_PREP" | "GOAL";
  completed: boolean;
}

```

### Chat

| Method and path | Request | Success `data` |
|---|---|---|
| `POST /chat` | `ChatRequest` below | `ChatResponse` below |
| `POST /chat/sessions` | `CreateSessionRequest` below | `ChatSession` |
| `GET /chat/sessions?student_id={id}&limit={limit}` | Required `student_id`; `limit` 1–200, default 50 | `ChatSession[]` |
| `GET /chat/sessions/{session_id}` | Path session ID | `ChatSession` |
| `GET /chat/sessions/{session_id}/messages?limit={limit}&offset={offset}` | `limit` 1–1000, default 100; `offset` >=0, default 0 | `ChatMessage[]` |
| `DELETE /chat/sessions/{session_id}` | Path session ID | `{ session_id: number }` |

```ts
interface ChatRequest {
  session_id?: number | null; // omitted/null starts a new session
  student_id?: number | null; // optional; authenticated identity is authoritative
  message: string; // 1–8000 characters
}
interface ChatResponse {
  session_id: number;
  user_message_id: number;
  assistant_message_id: number;
  answer: string;
  agent_used: string;
  tool_used: string | null;
  created_at: string;
}
interface CreateSessionRequest { student_id: number; title?: string | null; }
interface ChatSession {
  id: number; student_id: number; title: string;
  created_at: string; updated_at: string;
}
interface ChatMessage {
  id: number; session_id: number; role: string; content: string;
  agent_name: string | null; tool_name: string | null;
  metadata_json: Record<string, unknown>; created_at: string;
}
```

Chat is a synchronous JSON request/response. The route does not stream tokens, return Server-Sent Events, or use WebSockets. `POST /chat` with no `session_id` creates/uses a new session; with an existing session it appends to that session. Session ownership is enforced. Session list uses a limit but no offset/cursor; messages use limit/offset.

### Courses, subjects, topics

| Method and path | Request | Success `data` |
|---|---|---|
| `GET /courses` | None | `Course[]` for the authenticated student |
| `GET /courses/{course_id}` | Path ID | `Course` |
| `GET /courses/{course_id}/subjects` | Path ID | `CourseWithSubjects` |
| `POST /courses` | `CourseCreate` | `Course` |
| `GET /subjects` | None | `Subject[]` for the authenticated student |
| `GET /subjects/{subject_id}` | Path ID | `Subject` |
| `POST /subjects` | `SubjectCreate` | `Subject` |
| `GET /topics?skip={skip}&limit={limit}` | skip >=0 default 0; limit 1–500 default 100 | `Topic[]` |
| `GET /topics/{topic_id}` | Path ID | `Topic` |
| `GET /subjects/{subject_id}/topics?skip={skip}&limit={limit}` | IDs; same pagination | `Topic[]` |
| `POST /topics/extract/{material_id}?subject_id={subject_id}` | Material path ID; required subject query ID >=1 | `Topic[]`; persists extracted topics |

```ts
interface CourseCreate { name: string; description?: string | null; student_id: number; }
interface Course { id: number; name: string; description: string | null; student_id: number; }
interface CourseSubject { id: number; name: string; }
interface CourseWithSubjects {
  id: number; name: string; description: string | null; subjects: CourseSubject[];
}
interface SubjectCreate { name: string; description?: string | null; course_id: number; }
interface Subject { id: number; name: string; description: string | null; course_id: number; }
interface Topic { id: number; subject_id: number; name: string; description: string | null; }
```

### Study materials, PDF processing, and RAG

| Method and path | Request | Success `data` |
|---|---|---|
| `POST /materials/upload` | `multipart/form-data` fields below; HTTP 202 | `StudyMaterial` including processing job ID/status |
| `GET /materials?student_id={id}` | Required query student ID | `StudyMaterial[]`, newest upload first |
| `GET /materials/{material_id}` | Path ID | `StudyMaterial` |
| `GET /subjects/{subject_id}/materials` | Subject path ID | `StudyMaterial[]` |
| `POST /materials/{material_id}/embed` | Material path ID; HTTP 202 | `JobExecution` |
| `GET /jobs/{job_id}?student_id={id}` | Required query student ID | `JobExecution`; poll this endpoint for queued work |
| `GET /materials/{material_id}/extract-text` | Material path ID | `{ title: string; text: string }`; text is truncated to 5,000 characters |
| `GET /materials/{material_id}/chunks` | Material path ID | `{ total_chunks: number; first_chunk: string }` |
| `POST /topics/extract/{material_id}?subject_id={id}` | IDs | `Topic[]` |
| `POST /rag/ask` | `AskRequest` below | `AskResponse` below |

Upload multipart fields: `title` (required string), `subject_id` (required integer), `material_type` (optional, default `NOTES`; one of `NOTES`, `PYQ`, `SYLLABUS`, `REFERENCE`), `file` (required PDF upload), and `student_id` (optional integer; if supplied, must match the subject owner). Backend defaults: maximum 25 MiB (`MAX_UPLOAD_SIZE_BYTES = 25 * 1024 * 1024`), MIME type `application/pdf`, `.pdf` extension, and `%PDF-` file signature. Upload rate limit defaults to 10 requests/minute. Invalid type/signature/extension returns 400; oversized upload returns 413.

Upload immediately creates the material and enqueues `process_pdf_material`. Its 202 response includes `processing_job_id` and initial `processing_status`; poll `GET /jobs/{job_id}?student_id=...`. Job status fields are:

```ts
interface JobExecution {
  id: number; job_name: string; status: string; student_id: number | null;
  result_json: unknown; created_at: string; started_at: string | null;
  completed_at: string | null; queue_time_seconds: number | null;
  duration_seconds: number | null; retry_count: number;
  error_message: string | null;
}
```

`result_json` is declared as Pydantic `Any` and is job-specific; `unknown` is intentional in TypeScript. `StudyMaterial` fields: `id`, `title`, `file_path`, nullable `uploaded_at`, `subject_id`, `material_type`, nullable `processing_job_id`, nullable `processing_status`.

There is **no material DELETE endpoint** in the registered API. `POST /materials/{material_id}/embed` enqueues processing; do not call the unregistered helper function as an HTTP endpoint. `GET /rag/debug-search`, `/debug/chroma`, and `/debug/search` are diagnostic endpoints; they are not production frontend capabilities (`/rag/debug-search` and material debug handlers are disabled/hidden in production).

```ts
interface AskRequest { question: string; subject_id?: number | null; }
interface SourceItem { material_id: number; title: string; chunk_index: number; }
interface RetrievalDebug { chunks_used: number; subject_detected: string | null; }
interface AskResponse {
  answer: string; sources: SourceItem[]; debug: RetrievalDebug | null;
}
```

### Quiz system and exam preparation

| Method and path | Request | Success `data` |
|---|---|---|
| `POST /quizzes/generate` | `QuizGenerateRequest` | `QuizSessionWithQuestions` |
| `POST /quizzes/submit` | `QuizSubmitRequest` | `QuizSubmitResponse` |
| `GET /quizzes/history/{student_id}?skip={skip}&limit={limit}` | skip >=0 default 0; limit 1–200 default 50 | `QuizSession[]` |
| `GET /quizzes/session/{session_id}` | Path ID | `QuizSessionWithQuestions` |
| `POST /practice/start` | `PracticeStartRequest` | `PracticeStartResponse` |
| `POST /practice/submit` | `PracticeSubmitRequest` | `PracticeSubmitResponse` |

```ts
interface QuestionInput {
  topic_id?: number | null;
  question: string;
  question_type?: string; // default short_answer; documented values MCQ, true_false, short_answer
  correct_answer: string;
}
interface QuizGenerateRequest {
  student_id: number; subject_id: number; questions: QuestionInput[]; // minimum 1
}
interface QuizSession {
  id: number; student_id: number; subject_id: number; total_questions: number;
  score: number | null; started_at: string | null; completed_at: string | null;
}
interface QuizQuestion {
  id: number; session_id: number; topic_id: number | null;
  question: string; question_type: string; correct_answer: string;
}
interface QuizSessionWithQuestions { session: QuizSession; questions: QuizQuestion[]; }
interface AnswerSubmission { question_id: number; student_answer: string; }
interface QuizSubmitRequest {
  session_id: number; answers: AnswerSubmission[]; // minimum 1
  update_mastery?: boolean; // defaults true
}
interface AnswerResult {
  question_id: number; is_correct: boolean;
  correct_answer: string; student_answer: string;
}
interface QuizSubmitResponse {
  session_id: number; score: number; total_questions: number; results: AnswerResult[];
}
```

Important observed behavior: `POST /quizzes/generate` and `GET /quizzes/session/{id}` return `QuizQuestion.correct_answer` before submission. The API does not hide correct answers from the client. The quiz UI may choose not to render the field until after submit, but that is a UI-only concealment; it is not an API guarantee. Submission returns `correct_answer`, `student_answer`, and `is_correct` per result and updates topic mastery by default.

Practice request/result fields:

```ts
interface PracticeStartRequest { student_id: number; subject_id: number; count?: number; } // count default 10, range 1–30
interface PracticeQuestion { attempt_id: number; question: string; topic: string; difficulty: "Easy" | "Medium" | "Hard"; marks: number | null; }
interface PracticeStartResponse {
  session_id: number; student_id: number; subject_id: number;
  started_at: string; total_questions: number; questions: PracticeQuestion[];
}
interface PracticeAnswer { attempt_id: number; student_answer: string; confidence_score?: number; } // confidence default 50, 0–100
interface PracticeSubmitRequest { session_id: number; answers: PracticeAnswer[]; } // 1–30
interface GradedPracticeAnswer { attempt_id: number; topic: string; is_correct: boolean; score: number; feedback: string; }
interface PracticeSubmitResponse {
  session_id: number; score: number; total_questions: number;
  correct_answers: number; accuracy: number; duration_seconds: number;
  topic_coverage: string[]; results: GradedPracticeAnswer[];
}
```

### Flashcards and mastery

| Method and path | Request | Success `data` |
|---|---|---|
| `POST /flashcards/generate` | `FlashcardGenerateRequest` | `{ deck: FlashcardDeck; flashcards: Flashcard[] }` |
| `GET /flashcards/decks?subject_id={id}&skip={skip}&limit={limit}` | Required subject ID; skip >=0 default 0; limit 1–500 default 100 | `FlashcardDeck[]` |
| `GET /flashcards/decks/{deck_id}` | Path ID | `FlashcardDeck` |
| `GET /flashcards/topic/{topic_id}?skip={skip}&limit={limit}` | Path ID; same pagination | `Flashcard[]` |
| `GET /mastery/student/{student_id}?skip={skip}&limit={limit}` | skip >=0 default 0; limit 1–500 default 100 | `MasteryWithTopic[]` |
| `GET /mastery/subject/{subject_id}?student_id={id}` | Required student ID query | `MasteryWithTopic[]` |
| `GET /mastery/weak/{student_id}?threshold={n}&limit={n}` | threshold 0–100 default 50; limit 1–100 default 20 | `MasteryWithTopic[]`, ascending mastery score |

```ts
interface FlashcardGenerateRequest {
  subject_id: number; deck_name: string; topics: string[];
  cards_per_topic?: number; // default 5, range 1–20
}
interface FlashcardDeck { id: number; subject_id: number; name: string; created_at: string | null; }
interface Flashcard {
  id: number; deck_id: number; question: string; answer: string;
  difficulty: string; topic_id: number | null; created_at: string | null;
}
interface FlashcardGenerateResponse { deck: FlashcardDeck; flashcards: Flashcard[]; }
interface MasteryWithTopic {
  id: number; student_id: number; topic_id: number; topic_name: string;
  mastery_score: number; attempt_count: number;
}
```

### Study planner, calendar, reminders, deadlines, notifications

| Method and path | Request | Success `data` |
|---|---|---|
| `POST /study-plans/generate` | `StudyPlanGenerateRequest` | `StudyPlan` |
| `GET /study-plans/{plan_id}` | Path ID | `StudyPlan` |
| `GET /study-plans/{plan_id}/progress` | Path ID | `PlanProgress` |
| `PATCH /study-plans/tasks/{task_id}/complete` | Path ID; no body | Updated `StudyPlan` |
| `POST /study-plans/{plan_id}/recalculate` | Path ID; no body | `StudyPlan` plus `rescheduled_tasks` |
| `GET /schedule/{student_id}` | Path ID | `StudyBlock[]` ordered by start time |
| `POST /schedule/{student_id}/blocks` | `StudyBlockInput` | Created `StudyBlock`; overlapping events/blocks return 409 |
| `POST /schedule/{student_id}/generate` | `ScheduleInput` | Created `StudyBlock[]`; conflicts return 409 |
| `POST /schedule/{student_id}/intelligent` | `IntelligentScheduleInput` | Created `StudyBlock[]` |
| `GET /calendar/{student_id}` | Path ID | `CalendarEvent[]` |
| `POST /calendar/{student_id}` | `CalendarEventInput` | Created `CalendarEvent` |
| `PUT /calendar/events/{event_id}` | Path ID, `CalendarEventInput` | Updated `CalendarEvent` |
| `DELETE /calendar/events/{event_id}` | Path ID | `{ deleted: true }` |
| `GET /calendar/{student_id}/today` | Path ID | `Agenda` |
| `GET /calendar/{student_id}/tomorrow` | Path ID | `Agenda` |
| `GET /calendar/{student_id}/week?start_date={YYYY-MM-DD}` | Path ID; optional date | `WeekAgenda` (7 day records) |
| `GET /reminders/{student_id}` | Path ID | `Reminder[]`, includes completed and pending |
| `POST /reminders/{student_id}` | `ReminderInput` | Created `Reminder` |
| `PATCH /reminders/{reminder_id}` | Path ID, `ReminderUpdate` | Updated `Reminder` |
| `DELETE /reminders/{reminder_id}` | Path ID | `{ deleted: true }` |
| `GET /deadlines/{student_id}?include_completed={bool}` | Path ID; default false | `DeadlineItem[]` |
| `GET /deadlines/{student_id}/upcoming` | Path ID | Upcoming `DeadlineItem[]` |
| `GET /deadlines/{student_id}/overdue` | Path ID | Overdue `DeadlineItem[]` |
| `POST /deadlines/{student_id}` | `DeadlineInput` | Created `DeadlineItem` |
| `PATCH /deadlines/{deadline_id}/complete` | Path ID, `{ completed: boolean }` | Updated `DeadlineItem` |
| `GET /notifications/{student_id}?unread_only={bool}` | Path ID; default false | `StudentNotification[]` |
| `POST /notifications/{student_id}` | `NotificationInput` | Created `StudentNotification` |
| `PATCH /notifications/{notification_id}/read` | Path ID; no body | Updated `StudentNotification` |
| `POST /notifications/{student_id}/generate-alerts` | Path ID; HTTP 202 | `JobExecution`; poll `/jobs/{job_id}?student_id={id}` |

`StudyPlanGenerateRequest`: `{ student_id: number; subject_id: number; exam_date: string /* date */; hours_per_day: number /* >0 and <=24 */; subject_difficulty?: number /* default 3, 1–5 */ }`.

`StudyPlan`: `{ id, student_id, subject_id, subject_name, exam_date, start_date, hours_per_day, created_at, progress, daily_agenda }`. `progress` is `{ completion, tasks_done, tasks_remaining }`; each agenda item is `{ day_number, date, tasks }`; each task is `{ id, day_number, scheduled_date, topic, priority, estimated_hours, status }`. Dates are ISO date strings and timestamps are ISO date-time strings. Recalculate adds integer `rescheduled_tasks`.

`StudyBlockInput`: `{ subject_id?: number | null; title?: string | null; block_type?: "STUDY" | "REVISION" | "ATTENDANCE_RECOVERY" | "DEADLINE_PREP" | "GOAL"; start_time: string; end_time: string; planned_duration?: number | null }`. `planned_duration` must be >=0 when supplied. If omitted, service calculates the duration in minutes. `ScheduleInput`: `{ subject_ids: number[]; start_time: string; session_length?: number; break_minutes?: number }`; defaults are 50 minutes and 10 minutes. `IntelligentScheduleInput`: `{ start_time: string; available_hours: number; horizon_days?: number; session_minutes?: number }`; defaults are 7 days and 45 minutes.

`CalendarEventInput`: `{ title: string; description: string | null; start_time: string; end_time: string; event_type: string /* default OTHER */ }`. `CalendarEvent` adds `id` and `student_id`. End time must be after start time.

Agenda runtime shape:

```ts
interface Agenda {
  student_id: number; date: string; items: AgendaItem[];
}
interface AgendaItem {
  kind: "CALENDAR" | "STUDY_BLOCK" | "DEADLINE" | "REMINDER";
  title: string; start_time: string; end_time: string | null;
  event_type: string; id: number;
  subject_id?: number; completed?: boolean; priority?: string;
}
interface WeekAgenda { student_id: number; start_date: string; days: Agenda[]; }
```

`ReminderInput`: `{ title: string; trigger_time: string }`. `ReminderUpdate` accepts optional `title`, `trigger_time`, and `completed`; at least one is not enforced by the model. A `Reminder` has `id`, `student_id`, `title`, `trigger_time`, `completed`.

`NotificationInput`: `{ title: string; message: string; notification_type: "INFO" | "SUCCESS" | "WARNING" | "CRITICAL" | "REMINDER" }`, default type `INFO`. `StudentNotification` adds `id`, `student_id`, `read`, and `created_at`.

`DeadlineInput`: `{ title: string; description: string | null; type: "EXAM" | "ASSIGNMENT" | "PROJECT" | "LAB_SUBMISSION" | "QUIZ" | "PRESENTATION" | "OTHER"; due_date: string; priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"; subject_id: number | null }`, defaults type `OTHER`, priority `MEDIUM`. Runtime `DeadlineItem` is `{ id, student_id, subject_id, title, description, type, due_date, priority, completed }`.

### Student profile

| Method and path | Request | Success `data` |
|---|---|---|
| `GET /profile/{student_id}` | Path ID | `ProfileResponse` |
| `GET /profile/{student_id}/summary` | Path ID | `{ summary: string }` |
| `GET /profile/{student_id}/readiness-history` | Path ID | Array of `{ id, student_id, subject_id, readiness_score, captured_at }` |
| `GET /profile/{student_id}/memories` | Path ID | Array of `StudentMemory` |
| `GET /academic-profiles/{student_id}` | Path ID | Academic profile data |
| `PUT /academic-profiles/{student_id}` | Path ID, `ProfileInput` | Updated academic profile data |
| `GET /academic-profiles/{student_id}/summary` | Path ID | Academic profile summary data |
| `GET /academic-profiles/{student_id}/preferences` | Path ID | Preference data |
| `PUT /academic-profiles/{student_id}/preferences` | Path ID, `PreferenceInput` | Updated preference data |

`ProfileResponse` is `{ student_id: number; preferred_study_hours: number | null; preferred_subjects: string[]; current_goal: string | null; strengths: string[]; weaknesses: string[]; study_habits: string[]; readiness_trend: number[] }`.

`ProfileInput` accepts these optional nullable fields: `enrollment_number: string`, `branch: string`, `department: string`, `semester: integer >=1`, `section: string`, `batch_year: integer`, `current_cpi: number 0–10`, `current_spi: number 0–10`, `earned_credits: integer >=0`, `total_credits: integer >=0`, and `academic_status: "ACTIVE" | "PROBATION" | "GRADUATED" | "SUSPENDED" | "DROPOUT"`. The academic profile response is `{ id, student_id, enrollment_number, branch, department, semester, section, batch_year, current_cpi, current_spi, total_credits, earned_credits, academic_status, created_at, updated_at }`.

`GET /academic-profiles/{student_id}/summary` returns `{ profile: StudentAcademicProfile | null, attendance_count: number, grade_count: number, grade_analytics?: GradeAnalytics, pending_deadline_count: number }`. When the academic profile is absent, runtime returns only `{ profile: null, attendance_count: 0, grade_count: 0, pending_deadline_count: 0 }`; `grade_analytics` is therefore absent in that case.

`PreferenceInput` accepts optional nullable `preferred_study_time: string`, `preferred_session_length: integer >0`, and `study_style: string`. Preference GET/PUT returns the raw preference row fields `{ id, student_id, preferred_study_time, preferred_session_length, study_style }`; GET returns `{}` when no preference row exists.

Attendance creation/update uses `AttendanceInput`: `{ subject_id: integer; attended_classes: integer >=0; total_classes: integer >=0 }`; attended classes cannot exceed total classes. Its response `AttendanceRecord` has `id`, `student_id`, `academic_profile_id`, `subject_id`, `attended_classes`, `total_classes`, nullable `attendance_percentage`, and `last_updated`.

Grade creation uses `GradeInput`: required `subject_id`; optional nullable `semester` (>=1), `credits` (>=0), `grade`, `grade_points` (0–10), `obtained_marks` (>=0), and `grade_letter`; `grade_type` is `COMPONENT` or `FINAL` (default `COMPONENT`); `component_type` is `CT1`, `CT2`, `CT3`, `ASSIGNMENT`, `LAB`, `END_SEM`, `MID_SEM`, `VIVA`, `PROJECT`, or `OTHER` (default `OTHER`); `max_marks` defaults to 100 and must be >0. For `FINAL`, semester, positive credits, and grade_points are required. Runtime `GradeRecord` fields are listed above.

### Goals and habits

| Method and path | Request | Success `data` |
|---|---|---|
| `GET /goals/{student_id}?include_completed={bool}` | include_completed default true | `Goal[]` |
| `POST /goals/{student_id}` | `GoalCreateInput` | `Goal` |
| `PATCH /goals/{goal_id}` | Partial `GoalUpdateInput` | Updated `Goal` |
| `DELETE /goals/{goal_id}` | No body | `{ deleted: true }` |
| `POST /milestones/{goal_id}` | `MilestoneInput` | `GoalMilestone` |
| `GET /milestones/{goal_id}` | No body | `GoalMilestone[]` |
| `PATCH /milestones/{milestone_id}/complete?completed={bool}` | Required query boolean | Updated `GoalMilestone` |
| `POST /progress/{goal_id}` | `ProgressInput` | `GoalProgress` |
| `GET /progress/{goal_id}` | No body | `GoalProgress[]` |
| `GET /habits/{student_id}?active_only={bool}` | active_only default true | `Habit[]` |
| `POST /habits/{student_id}` | `HabitCreateInput` | `Habit` |
| `PATCH /habits/{habit_id}` | Partial `HabitUpdateInput` | Updated `Habit` |
| `DELETE /habits/{habit_id}` | No body | `{ deleted: true }` |
| `POST /habits/{habit_id}/logs` | `HabitLogInput` | `HabitLog` |
| `GET /habits/{habit_id}/logs?start={date}&end={date}` | Optional date bounds | `HabitLog[]`, newest first |

`GoalCreateInput`: `{ title: string; goal_type: "SEMESTER" | "CPI" | "ATTENDANCE" | "PLACEMENT" | "STUDY_HOURS"; target_value?: number | null; target_unit?: string | null; target_date?: string | null }`. `GoalUpdateInput` has the same fields optional and also `completed?: boolean`. `MilestoneInput`: `{ title: string; target_value?: number | null; target_date?: string | null }`. `ProgressInput`: `{ progress_value: number >=0; notes?: string | null }`.

`GoalProgress` fields: `id`, `student_id`, `goal_id`, `progress_value`, `recorded_at`, `notes`. `HabitCreateInput`: `{ habit_name: string; category: "DAILY_STUDY" | "REVISION" | "PYQ_PRACTICE" | "ATTENDANCE_CHECK" | "ASSIGNMENT_COMPLETION"; target_per_week?: integer 1–7 }`. `HabitUpdateInput` makes these fields optional and accepts `active?: boolean`. `HabitLogInput`: `{ log_date?: string; completed?: boolean; duration_minutes?: integer >=0 | null; notes?: string | null }`. See `Habit` and `HabitLog` interfaces above for returned row fields.

`StudentMemory` is `{ id: number; student_id: number; memory_type: string; memory_key: string; memory_value: unknown; created_at: string; updated_at: string }`. `memory_value` is decoded JSON and is intentionally typed `unknown`, not `any`.

## OpenAPI response gaps and runtime-traced shapes

The audit reports 92 of 159 operations whose success envelope has `data` typed as Pydantic `Any`. Each listed method/path below is one such operation; paths grouped in a cell have the same runtime shape, not one combined endpoint. This traces every `Any` success operation in the snapshot. Values noted as dynamic remain unconstrained at runtime and are deliberately represented as `unknown` in TypeScript. Typed response schemas and all operation parameters/status codes are in the generated API inventory and OpenAPI file.

| Endpoint | OpenAPI schema | Actual response `data` |
|---|---|---|
| `GET /api/health/live`; `GET /health/live` | `SuccessResponse[Any]` | `{ status: "alive" }`. |
| `GET /api/health/ready`; `GET /health/ready` | `SuccessResponse[Any]` | `{ status: "ready" \| "not_ready"; ready: boolean; database: string; chromadb: string; scheduler: string; tool_registry: string; migrations: string; metrics: string; audit_logging: string; authentication: string }`. Check strings typically use `"ok"`/`"error"`; migrations may also be `"pending"`. |
| `GET /api/health/dependencies`; `GET /api/health`; `GET /health/dependencies`; `GET /health` | `SuccessResponse[Any]` | `{ status: "healthy" \| "degraded"; database: string; chromadb: string; scheduler: string; tool_registry: string; migrations: string; metrics: string; audit_logging: string; authentication: string }`. |
| `POST /api/auth/google`; `POST /api/auth/refresh` | `SuccessResponse[Any]` | `{ student: StudentIdentity; tokens: { access_token: string; refresh_token: string; token_type: "bearer"; expires_in: integer } }`. These response bodies are detailed in Authentication above. |
| `GET /api/auth/me` | `SuccessResponse[Any]` | `{ student: StudentIdentity; tokens: { token_type: "bearer"; expires_at: string } }`. |
| `POST /api/auth/logout` | `SuccessResponse[Any]` | `{ student: StudentIdentity; tokens: { token_type: "bearer"; revoked: boolean } }`. |
| `DELETE /api/students/{student_id}` | `SuccessResponse[Any]` | `{ message: "Student deleted successfully" }` on success. |
| `GET /api/db-health` | `SuccessResponse[Any]` | `{ status: "Database connected" }` on success. |
| `GET /` | `SuccessResponse[Any]` | `{ message: "Jarvis API running" }`. |
| `GET /api/materials/{material_id}/extract-text` | `SuccessResponse[Any]` | `{ title: string; text: string }`; text is truncated to at most 5,000 characters. |
| `GET /api/materials/{material_id}/chunks` | `SuccessResponse[Any]` | `{ total_chunks: integer; first_chunk: string }`; `first_chunk` is `""` if no chunks exist. |
| `GET /api/debug/chroma` | `SuccessResponse[Any]` | `{ total_chunks: integer; sample_metadata: object[] }`; each metadata object's keys/values depend on stored Chroma metadata. This endpoint returns 404 in production. |
| `GET /api/debug/search` | `SuccessResponse[Any]` | Array of `{ id: string; document: string; metadata: object; distance: number; similarity: number }`; nested metadata is dynamic. |
| `GET /api/rag/debug-search` | `SuccessResponse[Any]` | `{ query: string; subject_id: integer \| null; retrieved_chunks: array; stats: RetrievalStats; vector_results: array; keyword_results: array; hybrid_results: array; fusion_stats: FusionStats }`. `RetrievalStats` is `{ chunks_retrieved: integer; chunks_after_filtering: integer; subject_detected: string \| null; materials_used: Array<{ material_id: integer \| null; title: string \| null }> }`. `FusionStats` contains integer hit/duplicate counts and `fusion_score_distribution: { min: number \| null; max: number \| null; mean: number \| null }`. Chunk variants/metadata depend on retrieval source. This endpoint returns 404 in production. |
| `GET /api/pyq/trends/{subject_id}` | `SuccessResponse[Any]` | `{ most_repeated_topics: Array<{ topic: string; frequency: integer }>; new_topics: string[]; declining_topics: Array<{ topic: string; previous_year_frequency: integer; latest_year_frequency: integer }>; yearly_frequencies: Record<string, Record<string, integer>>; topic_growth_trends: Array<{ topic: string; years: Array<{ year: integer; count: integer }> }> }`. |
| `GET /api/analytics/weak-topics/{student_id}/{subject_id}` | `SuccessResponse[Any]` | Array of `{ topic: string; mastery: integer; attempts: integer; pyq_frequency: integer }`. |
| `GET /api/analytics/strong-topics/{student_id}/{subject_id}` | `SuccessResponse[Any]` | Array of `{ topic: string; mastery: integer; attempts: integer; confidence_score: integer }`. |
| `GET /api/analytics/recommendations/{student_id}/{subject_id}` | `SuccessResponse[Any]` | `string[]`. |
| `GET /api/profile/{student_id}/readiness-history` | `SuccessResponse[Any]` | Array of `{ id: integer; student_id: integer; subject_id: integer \| null; readiness_score: integer; captured_at: string }`. |
| `GET /api/profile/{student_id}/memories` | `SuccessResponse[Any]` | Array of `{ id: integer; student_id: integer; memory_type: string; memory_key: string; memory_value: unknown; created_at: string; updated_at: string }`. `memory_value` may be a JSON scalar, null, array, or object; legacy non-JSON content is returned as a string. |
| `GET /api/profile/debug/{student_id}` | `SuccessResponse[Any]` | `{ stored_memories: StudentMemory[]; profile_state: ProfileResponse; readiness_snapshots: ReadinessSnapshot[] }`; `memory_value` is dynamic JSON as above. |
| `GET /api/semester/{semester_id}/health` | `SuccessResponse[Any]` | `{ semester_id: integer; health_score: integer; category: string; factors: { average_readiness: integer; plan_completion: integer; milestone_completion: integer; weak_topic_count: integer; weak_topic_score: integer }; subjects: Array<{ subject_id: integer; subject_name: string; readiness: integer; plan_completion: integer; weak_topic_count: integer }>; calculated_at: string }`. |
| `GET /api/semester/{semester_id}/review` | `SuccessResponse[Any]` | `{ summary: string; completed_goals: Array<{ title: string; completed_at: string }>; pending_goals: Array<{ title: string; due_date: string; overdue: boolean }>; recommended_actions: string[] }`. |
| `GET /api/semester/{semester_id}/risks` | `SuccessResponse[Any]` | Array of `{ risk: string; severity: "HIGH" \| "MEDIUM" }`. |
| `POST /api/semester/{semester_id}/milestone` (201); `PATCH /api/semester/{semester_id}/milestone/{milestone_id}` | `SuccessResponse[Any]` | `{ id: integer; semester_id: integer; title: string; description: string \| null; due_date: string; completed: boolean; completed_at: string \| null; created_at: string }`. |
| `GET /api/semester/{semester_id}/copilot` | `SuccessResponse[Any]` | `{ semester_id: integer; semester_health: integer; health_category: string; priority_subjects: Array<{ subject_id: integer; subject_name: string; readiness: integer; plan_completion: integer; weak_topic_count: integer; target_score: number \| null }>; risks: Array<{ risk: string; severity: "HIGH" \| "MEDIUM" }>; milestones: Array<{ id: integer; semester_id: integer; title: string; description: string \| null; due_date: string; completed: boolean; completed_at: string \| null; created_at: string }>; next_actions: string[]; profile_memory: { strengths: string[]; weaknesses: string[]; study_habits: string[]; current_goal: string \| null } }`. |
| `GET /system/health` | `SuccessResponse[Any]` | `{ database: string; chroma: string; groq: string; migrations: string; agents: string; version: string; overall: string; uptime_seconds: number }`. Status strings include values such as `"healthy"`, `"unhealthy"`, `"configured"`, `"missing"`, `"unknown"`, `"up_to_date"`, and `"pending"`. |
| `GET /api/system/metrics` | `SuccessResponse[Any]` | `total_requests`, `total_errors`, `director_agent_calls`, `rag_requests` are integers; `average_latency_ms`, `min_latency_ms`, `max_latency_ms`, `uptime_seconds` are numbers; `status_codes`, `agent_executions`, `endpoint_counts` are objects with dynamic string keys and integer values. |
| `GET /api/metrics/summary` | `SuccessResponse[Any]` | Integer counters `total_users`, `total_sessions`, `total_chat_messages`, `total_tool_executions`, `total_jobs`, `job_failures`, `rag_query_count`; `jobs: { total, successes, failures, active, pending: integer; success_rate, failure_rate, average_duration_seconds: number }`; `http` has the `/api/system/metrics` shape. Requires both access JWT and `X-Admin-Token`. |
| `GET /api/academic-profiles/{student_id}`; `PUT /api/academic-profiles/{student_id}` | `SuccessResponse[Any]` | Academic-profile row: integer/nullable `id`, `student_id`, `semester`, `batch_year`, `total_credits`, `earned_credits`; nullable string `enrollment_number`, `branch`, `department`, `section`; nullable number `current_cpi`, `current_spi`; string `academic_status`; string timestamps `created_at`, `updated_at`. |
| `GET /api/academic-profiles/{student_id}/summary` | `SuccessResponse[Any]` | `{ profile: AcademicProfile \| null; attendance_count: integer; grade_count: integer; pending_deadline_count: integer; grade_analytics?: GradeAnalytics }`. `grade_analytics` is present only when a profile exists. |
| `GET /api/academic-profiles/{student_id}/preferences`; `PUT /api/academic-profiles/{student_id}/preferences` | `SuccessResponse[Any]` | Preference row `{ id: integer; student_id: integer; preferred_study_time: string \| null; preferred_session_length: integer \| null; study_style: string \| null }`; GET returns `{}` if no row exists. |
| `GET /api/attendance/{student_id}` | `SuccessResponse[Any]` | Array `{ record: AttendanceRecord; risk: string; classes_to_recover: integer }`. |
| `POST /api/attendance/{student_id}` | `SuccessResponse[Any]` | `{ record: AttendanceRecord; risk: string }`. |
| `GET /api/grades/{student_id}` | `SuccessResponse[Any]` | `GradeRecord[]`. |
| `POST /api/grades/{student_id}` | `SuccessResponse[Any]` | One `GradeRecord`. |
| `GET /api/grades/{student_id}/analytics` | `SuccessResponse[Any]` | `{ spi_by_semester: Record<string, number \| null>; cpi: number \| null; record_count: integer; current_spi: number \| null }`. |
| `GET /api/deadlines/{student_id}`; `GET /api/deadlines/{student_id}/upcoming`; `GET /api/deadlines/{student_id}/overdue` | `SuccessResponse[Any]` | Arrays of `{ id: integer; student_id: integer; subject_id: integer \| null; title: string; description: string \| null; type: string; due_date: string; priority: string; completed: boolean }`. |
| `POST /api/deadlines/{student_id}`; `PATCH /api/deadlines/{deadline_id}/complete` | `SuccessResponse[Any]` | One serialized deadline object of the fields above. |
| `GET /api/notifications/{student_id}` | `SuccessResponse[Any]` | `StudentNotification[]` (`id`, `student_id`, `title`, `message`, `notification_type`, `read`, `created_at`). |
| `POST /api/notifications/{student_id}`; `PATCH /api/notifications/{notification_id}/read` | `SuccessResponse[Any]` | One `StudentNotification`. |
| `GET /api/calendar/{student_id}/today`; `GET /api/calendar/{student_id}/tomorrow` | `SuccessResponse[Any]` | `{ student_id: integer; date: string; items: AgendaItem[] }`; items are heterogeneous and discriminated by `kind` (`CALENDAR`, `STUDY_BLOCK`, `DEADLINE`, `REMINDER`). Deadline/reminder `end_time` is null; optional fields vary by kind. |
| `GET /api/calendar/{student_id}/week` | `SuccessResponse[Any]` | `{ student_id: integer; start_date: string; days: Agenda[] }`; `days` contains seven agenda objects. |
| `GET /api/calendar/{student_id}` | `SuccessResponse[Any]` | `CalendarEvent[]`. |
| `POST /api/calendar/{student_id}`; `PUT /api/calendar/events/{event_id}` | `SuccessResponse[Any]` | One `CalendarEvent`: integer `id`, `student_id`; string `title`, `event_type`, `start_time`, `end_time`; nullable string `description`. |
| `DELETE /api/calendar/events/{event_id}` | `SuccessResponse[Any]` | `{ deleted: true }`. |
| `GET /api/schedule/{student_id}`; `POST /api/schedule/{student_id}/generate`; `POST /api/schedule/{student_id}/intelligent` | `SuccessResponse[Any]` | `StudyBlock[]`. Fields: `id`, `student_id` integers; `subject_id` integer/null; `start_time`, `end_time` strings; `planned_duration` integer; `title` string/null; `block_type` string; `completed` boolean. |
| `POST /api/schedule/{student_id}/blocks` | `SuccessResponse[Any]` | One `StudyBlock` row with the fields above. |
| `GET /api/dashboard/{student_id}` | `SuccessResponse[Any]` | `DashboardData` as detailed above; top-level keys: student_id, profile, attendance, mastery, readiness, grades, grade_analytics, deadlines, notifications, calendar, agenda_today, agenda_week, goals, goal_progress, productivity, productivity_score, consistency_score, study_hours_7d, completion_rate, habit_streaks, readiness_snapshot. |
| `GET /api/reminders/{student_id}` | `SuccessResponse[Any]` | `Reminder[]`; row fields `id`, `student_id`, `title`, `trigger_time`, `completed`. |
| `POST /api/reminders/{student_id}`; `PATCH /api/reminders/{reminder_id}` | `SuccessResponse[Any]` | One `Reminder` row of those fields. |
| `DELETE /api/reminders/{reminder_id}` | `SuccessResponse[Any]` | `{ deleted: true }`. |
| `GET /api/goals/{student_id}` | `SuccessResponse[Any]` | Serialized `Goal[]`; each has `id`, `student_id`, `title`, `goal_type`, nullable `target_value`, `target_unit`, `target_date`, `completed`, `current_value`, nullable `progress_percent`, `milestones`, `created_at`. |
| `POST /api/goals/{student_id}`; `PATCH /api/goals/{goal_id}` | `SuccessResponse[Any]` | One serialized `Goal` of the fields above. |
| `DELETE /api/goals/{goal_id}` | `SuccessResponse[Any]` | `{ deleted: true }`. |
| `POST /api/milestones/{goal_id}`; `PATCH /api/milestones/{milestone_id}/complete` | `SuccessResponse[Any]` | One `GoalMilestone`: integer `id`, `student_id`, `goal_id`; string `title`; nullable number `target_value`; nullable date strings `target_date`, `completed_at`; boolean `completed`. |
| `GET /api/milestones/{goal_id}` | `SuccessResponse[Any]` | `GoalMilestone[]` with the fields above. |
| `POST /api/progress/{goal_id}` | `SuccessResponse[Any]` | One `GoalProgress`: integer `id`, `student_id`, `goal_id`; number `progress_value`; string `recorded_at`; nullable string `notes`. |
| `GET /api/progress/{goal_id}` | `SuccessResponse[Any]` | `GoalProgress[]` with the fields above. |
| `GET /api/habits/{student_id}` | `SuccessResponse[Any]` | `Habit[]`: integer `id`, `student_id`, `target_per_week`; string `habit_name`, `category`, `created_at`; boolean `active`. |
| `POST /api/habits/{student_id}`; `PATCH /api/habits/{habit_id}` | `SuccessResponse[Any]` | One `Habit` row with the fields above. |
| `DELETE /api/habits/{habit_id}` | `SuccessResponse[Any]` | `{ deleted: true }`. |
| `POST /api/habits/{habit_id}/logs` | `SuccessResponse[Any]` | One `HabitLog`: integer `id`, `student_id`, `habit_id`; string `log_date`, `created_at`; boolean `completed`; nullable integer `duration_minutes`; nullable string `notes`. |
| `GET /api/habits/{habit_id}/logs` | `SuccessResponse[Any]` | `HabitLog[]` with the fields above. |
| `POST /api/connectors/{student_id}`; `GET /api/connectors/{student_id}` | `SuccessResponse[Any]` | One connector projection / array of projections: `id`, `student_id`, `sync_interval_minutes` integer/null; `connector_type`, `status` strings; `enabled` boolean; `last_sync_at` string/null; `created_at` string. Credentials, endpoint URL, and configuration are not included. |
| `PUT /api/connectors/{connector_id}/credentials` | `SuccessResponse[Any]` | Connector projection as above; credentials are not returned. |
| `POST /api/connectors/{connector_id}/sync` | `SuccessResponse[Any]` | Sync-job projection plus `execution_job_id: integer` and `execution_status: string`. Projection fields: `id`, `student_id`, `connector_id` integers; `status` string; `scheduled_at` string; `started_at`, `finished_at` strings/null; `duration_seconds` number/null; `error` string/null. |
| `GET /api/connectors/{connector_id}/history` | `SuccessResponse[Any]` | SyncHistory row array: `id`, `student_id`, `connector_id`, `records_processed` integers; `status` string (`"SUCCEEDED" \| "FAILED"`); `started_at`, `finished_at` strings; `duration_seconds` number; `error` string/null; `summary` dynamic JSON/null. |
| `GET /api/sync-jobs/{student_id}` | `SuccessResponse[Any]` | SyncJob row array: `id`, `student_id`, `connector_id` integers; `status` string; `scheduled_at` string; `started_at`, `finished_at` strings/null; `duration_seconds` number/null; `error` string/null. `records_processed`, `execution_job_id`, and `execution_status` are not included. |
| `DELETE /api/chat/sessions/{session_id}` | `SuccessResponse[Any]` | `{ session_id: integer }`. |

Operations in this gap table use `Any` in OpenAPI despite the runtime structures above. Some exposed fields remain genuinely dynamic (Chroma metadata, retrieval chunks, memory values, sync summaries); their TypeScript representation must be `unknown`, not `any`. Diagnostic handlers marked production-hidden are not frontend capabilities; other debug endpoints noted above do not all have a production guard.
