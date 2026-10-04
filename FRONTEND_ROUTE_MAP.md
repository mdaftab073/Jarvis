# Jarvis Frontend Route Map

Frontend target: React + TypeScript + Vite. This map uses capabilities confirmed in the FastAPI routes. It is a UI proposal; it does not imply that the backend serves these browser routes.

## Browser routes

```text
/
├── login
├── dashboard
├── chat
│   ├── new
│   └── :sessionId
├── exam-prep
│   └── :subjectId
├── materials
│   └── :materialId
├── quizzes
│   ├── new
│   └── :sessionId
├── flashcards
│   ├── decks
│   └── decks/:deckId
├── mastery
│   └── :subjectId
├── analytics
├── planner
│   ├── calendar
│   └── plans/:planId
├── notifications
└── profile
```

`/` should resolve to `/dashboard` for an authenticated user and `/login` otherwise. `:sessionId`, `:subjectId`, `:materialId`, `:deckId`, and `:planId` are frontend path parameters; they correspond to the backend IDs below.

## Page-to-API map

Every protected request uses `Authorization: Bearer ${accessToken}`. Substitute the authenticated student's `id` from `GET /api/auth/me` for `{student_id}`.

| Browser route | Backend calls |
|---|---|
| `/login` | Google Identity Services obtains a Google ID token; send `{ id_token }` to `POST /api/auth/google`. No backend login page or OAuth redirect endpoint is registered. |
| `/dashboard` | `GET /api/auth/me`; `GET /api/analytics/dashboard/{student_id}`; optionally `GET /api/dashboard/{student_id}` for its aggregate OS data; `GET /api/notifications/{student_id}?unread_only=true`. |
| `/chat` | `GET /api/chat/sessions?student_id={student_id}&limit=50`. |
| `/chat/new` | Start a chat via `POST /api/chat` with `message` (no session ID), or explicitly create an empty thread using `POST /api/chat/sessions` with `{ student_id, title }`. |
| `/chat/:sessionId` | `GET /api/chat/sessions/{session_id}`; `GET /api/chat/sessions/{session_id}/messages?limit=100&offset=0`; send subsequent turns with `POST /api/chat` and `session_id`; delete with `DELETE /api/chat/sessions/{session_id}`. |
| `/exam-prep` | `GET /api/courses`, then `GET /api/courses/{course_id}/subjects`; select a subject and call the subject-specific endpoints below. |
| `/exam-prep/:subjectId` | `GET /api/analytics/readiness/{student_id}/{subject_id}`; `GET /api/analytics/weak-topics/{student_id}/{subject_id}`; `GET /api/analytics/strong-topics/{student_id}/{subject_id}`; `GET /api/analytics/recommendations/{student_id}/{subject_id}`; `GET /api/subjects/{subject_id}/topics`; `GET /api/subjects/{subject_id}/materials`; optionally `GET /api/flashcards/decks?subject_id={subject_id}` and `GET /api/mastery/subject/{subject_id}?student_id={student_id}`. Quiz generation requires the client to submit question records to `POST /api/quizzes/generate`; the backend does not expose a quiz-question generation endpoint. |
| `/materials` | `GET /api/courses` → `GET /api/courses/{course_id}/subjects` → `GET /api/subjects/{subject_id}/materials`. Upload by multipart POST to `/api/materials/upload`, then poll its `processing_job_id`. |
| `/materials/:materialId` | `GET /api/materials/{material_id}`; `GET /api/materials/{material_id}/extract-text`; `GET /api/materials/{material_id}/chunks`; enqueue/re-enqueue with `POST /api/materials/{material_id}/embed`; extract associated topics with `POST /api/topics/extract/{material_id}?subject_id={subject_id}`. There is no material-delete endpoint. |
| `/quizzes` | `GET /api/quizzes/history/{student_id}?skip=0&limit=50`. |
| `/quizzes/new` | `GET /api/subjects`, `GET /api/subjects/{subject_id}/topics`, and optionally `GET /api/subjects/{subject_id}/materials`; create a session with `POST /api/quizzes/generate`. Questions and `correct_answer` values must be supplied by the caller. |
| `/quizzes/:sessionId` | `GET /api/quizzes/session/{session_id}`; submit answer array to `POST /api/quizzes/submit`. |
| `/flashcards` and `/flashcards/decks` | `GET /api/courses`, `GET /api/courses/{course_id}/subjects`, and `GET /api/flashcards/decks?subject_id={subject_id}&skip=0&limit=100`. |
| `/flashcards/decks/:deckId` | `GET /api/flashcards/decks/{deck_id}`. Use `GET /api/flashcards/topic/{topic_id}?skip=0&limit=100` for topic-scoped card retrieval. Generate with `POST /api/flashcards/generate`. |
| `/mastery` | `GET /api/mastery/student/{student_id}?skip=0&limit=100` and `GET /api/mastery/weak/{student_id}?threshold=50&limit=20`. |
| `/mastery/:subjectId` | `GET /api/mastery/subject/{subject_id}?student_id={student_id}`; readiness and analytics are available through the exam-prep endpoints. |
| `/analytics` | `GET /api/analytics/dashboard/{student_id}`; `GET /api/grades/{student_id}/analytics`; `GET /api/profile/{student_id}/readiness-history`; optional attendance and grade details through `/api/attendance/{student_id}` and `/api/grades/{student_id}`. |
| `/planner` | Generate via `POST /api/study-plans/generate`; a generated plan response includes its ID and can then be loaded with `GET /api/study-plans/{plan_id}`. There is no study-plan list endpoint, so retain the returned plan ID in client state/URL if the UI needs to reopen it. List study blocks using `/api/schedule/{student_id}` and calendar agendas using `/api/calendar/{student_id}/today`, `/tomorrow`, `/week`. |
| `/planner/calendar` | `GET /api/calendar/{student_id}`; `GET /api/calendar/{student_id}/week?start_date=YYYY-MM-DD`; `GET /api/schedule/{student_id}`; `GET /api/deadlines/{student_id}/upcoming`; `GET /api/reminders/{student_id}`. Create/update/delete calendar events via `/api/calendar/{student_id}` POST, `/api/calendar/events/{event_id}` PUT/DELETE. |
| `/planner/plans/:planId` | `GET /api/study-plans/{plan_id}`; `GET /api/study-plans/{plan_id}/progress`; `PATCH /api/study-plans/tasks/{task_id}/complete`; `POST /api/study-plans/{plan_id}/recalculate`. |
| `/notifications` | `GET /api/notifications/{student_id}?unread_only=false`; mark a row read with `PATCH /api/notifications/{notification_id}/read`; request background alert generation with `POST /api/notifications/{student_id}/generate-alerts` and poll `/api/jobs/{job_id}?student_id={student_id}`. |
| `/profile` | `GET /api/auth/me`; `GET /api/profile/{student_id}`; `GET /api/profile/{student_id}/summary`; `GET /api/profile/{student_id}/readiness-history`; `GET /api/profile/{student_id}/memories`; academic fields/preferences via `/api/academic-profiles/{student_id}` and `/preferences`. |

## Other available student-operating-system endpoints

These backend capabilities can be linked from Dashboard or Planner without inventing new server routes:

- Goals: `GET/POST /api/goals/{student_id}`, `PATCH/DELETE /api/goals/{goal_id}`, `POST/GET /api/milestones/{goal_id}`, `PATCH /api/milestones/{milestone_id}/complete`, `POST/GET /api/progress/{goal_id}`.
- Habits: `GET/POST /api/habits/{student_id}`, `PATCH/DELETE /api/habits/{habit_id}`, `POST /api/habits/{habit_id}/logs`, `GET /api/habits/{habit_id}/logs`.
- Study blocks: `GET /api/schedule/{student_id}`, `POST /api/schedule/{student_id}/blocks`, `POST /api/schedule/{student_id}/generate`, `POST /api/schedule/{student_id}/intelligent`.
- Deadlines: `GET/POST /api/deadlines/{student_id}`, `GET /upcoming`, `GET /overdue`, `PATCH /api/deadlines/{deadline_id}/complete`.
- Semester overview: registered `/api/semester` and `/api/semester/...` endpoints are present in the API inventory; use their OpenAPI schemas in `docs/openapi.json` before adding a semester-specific UI.

## Navigation recommendation

### Left sidebar

1. Dashboard
2. New Chat
3. Chat History
4. Exam Preparation
5. Study Materials
6. Quizzes
7. Flashcards
8. Mastery
9. Analytics
10. Study Planner
11. Notifications
12. Profile

Use course/subject context from the Courses and Subjects APIs rather than assuming a fixed subject list.

### Top bar

- Current page title.
- Course/subject selector where the page needs a course or subject ID.
- Notifications entry with unread count from the notification list.
- Current-user menu populated from `/api/auth/me`, including sign out.

No generic full-text search endpoint exists in the registered API. Do not add a global-search behavior that implies backend support.

There is no study-plan list endpoint. Keep the ID returned by plan generation if the user needs to reopen that plan.

### Main page modules

- **Dashboard cards:** readiness score/status and plan completion (`/analytics/dashboard`); unread notifications (`/notifications`); due dates (`/deadlines/.../upcoming`); calendar agenda; productivity and habit streaks from `/dashboard/{student_id}`; attendance and grades where available.
- **Exam Preparation workspace:** selected subject context; readiness and topic mastery; weak/strong topics and recommendations; materials and PDF-derived topics; quizzes/practice; flashcard decks; study-plan generation and completion.
- **Chat:** persistent history sidebar; new chat action; synchronous assistant transcript; paginated message loading. Do not render a streaming indicator as if the backend streams.
- **Study Materials:** PDF-only upload, processing status, text/chunk inspection if useful, and RAG question answering scoped by subject.
- **Study Planner:** study plans and task completion; week/day agenda; calendar events, deadlines, and reminders. Conflict-aware study-block creation can return 409.
- **Analytics:** readiness, practice score trend, course/subject summaries, grade analytics, and profile readiness history.

### Mobile navigation

Use five primary tabs: **Home**, **Chat**, **Exam Prep**, **Planner**, and **Profile**. Keep Materials, Quizzes, Flashcards, Mastery, Analytics, and Notifications reachable from the Dashboard or a secondary menu; this is a frontend information-architecture recommendation, not an API constraint.

## Routing and data-loading constraints

- Resolve `/` only after checking the auth state; while `GET /api/auth/me` is pending, render a loading state rather than briefly showing protected content.
- Keep backend IDs in route state; after login, use the authenticated `student.id` for all student-scoped requests.
- Never infer route support from similarly named service functions: only registered API routes are callable.
- API contracts, payload schemas, envelope, and pagination limits are documented in [`BACKEND_API_CONTRACT.md`](./BACKEND_API_CONTRACT.md). Full machine-readable details are in [`docs/openapi.json`](./docs/openapi.json).
