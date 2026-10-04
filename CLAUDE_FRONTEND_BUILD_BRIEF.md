# Jarvis Frontend Build Brief

**Purpose:** Give a frontend engineer or coding agent (including Claude) the product, API, security, and acceptance context needed to build a working Jarvis web application against the frozen backend.

**Contract snapshot:** 2026-10-03  
**Backend:** FastAPI; OpenAPI 3.1.0; 133 paths; 159 operations.

> Give the implementer this document together with [`docs/FRONTEND_API_REFERENCE.md`](./docs/FRONTEND_API_REFERENCE.md) and [`docs/openapi.json`](./docs/openapi.json). The Markdown reference is the exhaustive, operation-by-operation index; the JSON artifact contains the field-level OpenAPI schemas. Use live `GET /openapi.json` (or `/docs`) to check that artifact against the running backend. This brief explains what to build and how the parts fit together; it does not override the frozen API contract.

## 1. Instructions for the frontend implementer

Build the frontend in the existing `frontend/` directory. At the time of this handoff, no frontend source or package manifest was present there. Inspect the repository first; if it is still empty, choose a maintainable TypeScript web stack and create the application scaffold there. Do not change backend business logic or invent endpoints, request fields, response fields, or product capabilities.

Implement a responsive, accessible student-facing application with real API integration—not static mock screens. Keep API calls in a typed client/service layer, keep authentication state centralized, provide loading/empty/error states, and add tests for critical workflows. Use the API reference and OpenAPI schema for exact fields. A number of operations return `Any` for the inner `data` payload; do not make up a supposedly stable type for those responses. Inspect runtime examples/source where needed, model only what is confirmed, and handle absent/extra fields safely.

### Product in one paragraph

Jarvis is an authenticated academic assistant for students. It brings together courses and subjects, uploaded study materials and retrieval-based Q&A, academic chat/agents, study planning, quizzes/practice/flashcards, calendar and deadlines, goals/habits/reminders, semester tracking, attendance/grades, and learning/mastery analytics. Its backend uses PostgreSQL for application records and ChromaDB for retrieval. Google OAuth is the sign-in provider. The former SVNIT MIS integration has been removed; do not show MIS sign-in, MIS sync, or MIS-specific features.

## 2. Contract and environment

- Local API origin: `http://localhost:8000`. Use a configurable environment variable such as `VITE_API_BASE_URL`; do not hardcode the origin throughout the app.
- API paths in the reference are complete paths. For example, concatenate `http://localhost:8000` and `/api/courses`; do not add a second `/api` prefix.
- In production, the frontend origin must exactly match an origin configured in backend `ALLOWED_ORIGINS`. Browser CORS is not fixed by frontend code.
- Interactive docs: `{API_ORIGIN}/docs`. Machine-readable OpenAPI: `{API_ORIGIN}/openapi.json`.
- All application JSON success bodies use `{ "success": true, "data": ... }`. All application failures use `{ "success": false, "error": { "code": "...", "message": "..." } }`. Read the payload from `data`; present `error.message` to the user with a safe, nontechnical fallback for malformed/network failures.
- HTTP status remains meaningful. In particular, do not treat every 2xx as the same: material upload and embedding, and alert generation return `202` and require background-job UX.
- OpenAPI currently does **not** declare a bearer `securityScheme` or per-operation `security`, even though authentication middleware enforces bearer tokens. The generated API reference records the known public exceptions. Do not infer public access from missing OpenAPI security metadata.
- Route parameters such as `student_id`, `subject_id`, and `session_id` are identifiers, not authorization credentials. The backend validates ownership. In the UI, use the signed-in student's ID and never let a user switch to or enumerate another student's records.

## 3. Authentication and identity

### Sign-in

1. Use Google Identity Services in the browser and obtain a Google **ID token**. Configure the frontend Google OAuth client ID to match the backend's configured `GOOGLE_CLIENT_ID`.
2. Send `POST /api/auth/google` with JSON `{ "id_token": "<Google ID token>" }`.
3. On success, the response `data` is shaped as:

   ```json
   {
     "student": {
       "id": 1,
       "email": "student@example.edu",
       "full_name": "Student Name",
       "profile_picture": "https://...",
       "is_verified": true
     },
     "tokens": {
       "access_token": "...",
       "refresh_token": "...",
       "token_type": "bearer",
       "expires_in": 900
     }
   }
   ```

   `expires_in` is seconds (15 minutes with current backend settings); do not assume the sample ID or expiry if deployment configuration differs.
4. Store the authenticated student and tokens in the centralized auth layer. Send `Authorization: Bearer <access_token>` for protected `/api/*` calls.
5. Use `GET /api/auth/me` to verify an authenticated session when restoring it. Its `data` has `student` and a `tokens` object with `token_type` and `expires_at`; it does not return a new access token.

For protected API requests, the standard HTTP authorization header must use the Bearer scheme and the current access token as its credential.

### Refresh and logout

- `POST /api/auth/refresh` is public at middleware level and accepts `{ "refresh_token": "..." }`. On success it returns the same `student` + `tokens` shape as Google sign-in.
- Refresh tokens rotate: a successful refresh revokes the submitted refresh token and issues a new access/refresh pair. Replace **both** tokens atomically; never reuse the old refresh token.
- Use a single-flight refresh mechanism so concurrent `401` responses do not race the one-time refresh token. Retry the failed request at most once after refresh; if refresh fails, clear local auth and route to sign-in.
- `POST /api/auth/logout` requires the access bearer token and body `{ "refresh_token": "..." }`. Clear frontend auth whether logout succeeds or the network is unavailable; communicate any server-side failure appropriately.
- The API returns tokens in JSON; it does not establish HttpOnly cookies. Do not put secrets or provider keys in frontend code. Prefer keeping the access token in memory; if persistence is necessary, make an explicit, documented session-storage choice and account for the XSS exposure of browser-readable refresh tokens. Never log tokens or include them in analytics/error reports.
- Handle `401` as an authentication/refresh event; handle `403` as an authorization/ownership failure, not as permission to retry using a different student ID.

## 4. Recommended application navigation and workflow

Build the core product around the authenticated student, with a responsive navigation rail/sidebar and mobile navigation. Suggested routes/screens:

1. **Sign in** — Google sign-in, auth-loading and provider failure states.
2. **Home/dashboard** — student overview, current courses/subjects, upcoming work, progress/readiness, and notifications. Prefer the dashboard/analytics APIs; render confirmed fields only.
3. **Courses and subjects** — browse the student's courses and their subjects/topics; show materials and topic-level learning views.
4. **Study materials** — list materials, upload a PDF, show processing status, and open extracted text/chunks or resulting topics/questions when useful.
5. **Tutor/chat** — create or resume a persisted chat session, send messages, show assistant attribution, paginate history, and delete sessions. Chat is a normal request/response API, not a streaming/WebSocket contract.
6. **Study plan and schedule** — generate or view a plan, mark tasks complete, recalculate, create/view study blocks, and show calendar events.
7. **Practice and review** — generate PYQ practice, quizzes, or flashcards; answer/submit; show scored results, quiz history, mastery, important topics, and revision plans.
8. **Academic progress** — attendance, grades, learning history/insights, analytics, topic mastery, strong/weak topics, goals/milestones/progress, habits/logs, deadlines, reminders, and semester milestones/status.
9. **Profile and notifications** — read profile/summary/memories/readiness history; display and mark notifications read. Do not imply an unsupported profile-edit endpoint where none exists.

Use a shared course/subject/student context so the same selected subject feeds material, topic, retrieval, quiz, flashcard, and analytics screens. Prefer user-facing workflows over raw endpoint-by-endpoint screens.

## 5. Complete endpoint capability map

This map names every backend domain and its intended frontend use. The exact endpoint list is grouped by API surface; all methods and route paths are specified here or in the exhaustive generated table linked above. The operation-level reference is authoritative for required/optional parameters, exact body model names, success data schemas, and status codes. Routes under `debug`, health/metrics, and sync-job inspection are operational/developer surfaces and should not be exposed in ordinary student navigation.

| Domain / frontend use | Endpoints |
|---|---|
| **Root and service status** — minimal service check; use readiness only for connection/deployment diagnostics, not the signed-in student's dashboard. | `GET /`; `GET /health`; `GET /health/live`; `GET /health/ready`; `GET /health/dependencies`; `GET /system/health`; `GET /api/health`; `GET /api/health/live`; `GET /api/health/ready`; `GET /api/health/dependencies`; `GET /api/db-health` |
| **Authentication** — Google sign-in, current identity, refresh, logout. | `POST /api/auth/google`; `GET /api/auth/me`; `POST /api/auth/refresh`; `POST /api/auth/logout` |
| **Student and profile** — student identity/records, courses belonging to a student, profile summary and memory views. The Google login flow provisions/links the account; avoid redundant student creation on normal onboarding. | `GET /api/students`; `POST /api/students`; `GET /api/students/{student_id}`; `PUT /api/students/{student_id}`; `DELETE /api/students/{student_id}`; `GET /api/students/{student_id}/courses`; `GET /api/profile/{student_id}`; `GET /api/profile/{student_id}/summary`; `GET /api/profile/{student_id}/memories`; `GET /api/profile/{student_id}/readiness-history`; `GET /api/academic-profiles/{student_id}`; `PUT /api/academic-profiles/{student_id}`; `GET /api/academic-profiles/{student_id}/preferences`; `PUT /api/academic-profiles/{student_id}/preferences`; `GET /api/academic-profiles/{student_id}/summary` |
| **Courses, subjects, topics** — course/subject selection, subject material/topic drill-down, topic extraction from material. | `GET /api/courses`; `POST /api/courses`; `GET /api/courses/{course_id}`; `GET /api/courses/{course_id}/subjects`; `GET /api/subjects`; `POST /api/subjects`; `GET /api/subjects/{subject_id}`; `GET /api/subjects/{subject_id}/materials`; `GET /api/subjects/{subject_id}/topics`; `GET /api/topics`; `GET /api/topics/{topic_id}`; `POST /api/topics/extract/{material_id}` |
| **Materials and retrieval** — add a metadata record, upload PDF, embed/monitor it, inspect extracted content, and ask grounded subject-aware questions. `202` operations are asynchronous. | `GET /api/materials`; `POST /api/materials`; `POST /api/materials/upload`; `GET /api/materials/{material_id}`; `GET /api/materials/{material_id}/chunks`; `GET /api/materials/{material_id}/extract-text`; `POST /api/materials/{material_id}/embed`; `POST /api/rag/ask` |
| **Academic chat and agents** — conversational tutoring, persisted sessions/messages, academic agent task and director orchestration. | `POST /api/chat`; `GET /api/chat/sessions`; `POST /api/chat/sessions`; `GET /api/chat/sessions/{session_id}`; `GET /api/chat/sessions/{session_id}/messages`; `DELETE /api/chat/sessions/{session_id}`; `POST /api/agent/academic`; `POST /api/director/academic` |
| **Study plan and schedule** — generate plan, view progress, complete/recalculate, generate a schedule and add study blocks. | `POST /api/study-plans/generate`; `GET /api/study-plans/{plan_id}`; `GET /api/study-plans/{plan_id}/progress`; `PATCH /api/study-plans/tasks/{task_id}/complete`; `POST /api/study-plans/{plan_id}/recalculate`; `GET /api/schedule/{student_id}`; `POST /api/schedule/{student_id}/generate`; `POST /api/schedule/{student_id}/intelligent`; `POST /api/schedule/{student_id}/blocks` |
| **Calendar and deadlines** — agenda views, create/edit/delete events, list upcoming/overdue deadlines and mark complete. | `GET /api/calendar/{student_id}`; `GET /api/calendar/{student_id}/today`; `GET /api/calendar/{student_id}/tomorrow`; `GET /api/calendar/{student_id}/week`; `POST /api/calendar/{student_id}`; `PUT /api/calendar/events/{event_id}`; `DELETE /api/calendar/events/{event_id}`; `GET /api/deadlines/{student_id}`; `GET /api/deadlines/{student_id}/upcoming`; `GET /api/deadlines/{student_id}/overdue`; `POST /api/deadlines/{student_id}`; `PATCH /api/deadlines/{deadline_id}/complete` |
| **Quizzes, practice, flashcards, PYQ** — practice generation and attempts, scoring, flashcard review, historic quizzes, PYQ trend/topic/revision views. | `POST /api/quizzes/generate`; `POST /api/quizzes/submit`; `GET /api/quizzes/history/{student_id}`; `GET /api/quizzes/session/{session_id}`; `POST /api/practice/start`; `POST /api/practice/submit`; `POST /api/pyq/generate-practice`; `GET /api/pyq/topics/{subject_id}`; `GET /api/pyq/important-topics/{subject_id}`; `GET /api/pyq/trends/{subject_id}`; `GET /api/pyq/revision-plan/{subject_id}`; `POST /api/flashcards/generate`; `GET /api/flashcards/decks`; `GET /api/flashcards/decks/{deck_id}`; `GET /api/flashcards/topic/{topic_id}` |
| **Learning and mastery** — create learning-session records, review history/insights and current/topic/subject mastery. | `POST /api/learning/session`; `GET /api/learning/history/{student_id}`; `GET /api/learning/insights/{student_id}`; `GET /api/mastery/student/{student_id}`; `GET /api/mastery/subject/{subject_id}`; `GET /api/mastery/weak/{student_id}` |
| **Analytics dashboard/readiness** — student dashboard, subject readiness/recommendations and strong/weak topics. | `GET /api/dashboard/{student_id}`; `GET /api/analytics/dashboard/{student_id}`; `GET /api/analytics/readiness/{student_id}/{subject_id}`; `GET /api/analytics/recommendations/{student_id}/{subject_id}`; `GET /api/analytics/strong-topics/{student_id}/{subject_id}`; `GET /api/analytics/weak-topics/{student_id}/{subject_id}` |
| **Grades and attendance** — record and display student-entered records and grade analytics. | `GET /api/grades/{student_id}`; `POST /api/grades/{student_id}`; `GET /api/grades/{student_id}/analytics`; `GET /api/attendance/{student_id}`; `POST /api/attendance/{student_id}` |
| **Goals, progress, milestones, habits** — set goals, update progress, manage milestones, record habit logs. | `GET /api/goals/{student_id}`; `POST /api/goals/{student_id}`; `PATCH /api/goals/{goal_id}`; `DELETE /api/goals/{goal_id}`; `GET /api/progress/{goal_id}`; `POST /api/progress/{goal_id}`; `GET /api/milestones/{goal_id}`; `POST /api/milestones/{goal_id}`; `PATCH /api/milestones/{milestone_id}/complete`; `GET /api/habits/{student_id}`; `POST /api/habits/{student_id}`; `PATCH /api/habits/{habit_id}`; `DELETE /api/habits/{habit_id}`; `GET /api/habits/{habit_id}/logs`; `POST /api/habits/{habit_id}/logs` |
| **Reminders and notifications** — create/update/delete reminders, generate alerts asynchronously, list notifications and mark read. | `GET /api/reminders/{student_id}`; `POST /api/reminders/{student_id}`; `PATCH /api/reminders/{reminder_id}`; `DELETE /api/reminders/{reminder_id}`; `GET /api/notifications/{student_id}`; `POST /api/notifications/{student_id}`; `POST /api/notifications/{student_id}/generate-alerts`; `PATCH /api/notifications/{notification_id}/read` |
| **Semester copilot** — create semester, view health/review/risks/copilot summary, maintain milestones/status. | `POST /api/semester`; `GET /api/semester/{semester_id}`; `GET /api/semester/{semester_id}/copilot`; `GET /api/semester/{semester_id}/health`; `GET /api/semester/{semester_id}/review`; `GET /api/semester/{semester_id}/risks`; `POST /api/semester/{semester_id}/milestone`; `PATCH /api/semester/{semester_id}/milestone/{milestone_id}`; `PATCH /api/semester/{semester_id}/status` |
| **Connectors and background jobs** — connector setup/credentials/history/sync and job polling. SVNIT MIS is not supported. Only expose connector types that are actually configured by the backend; never display or persist raw credentials in logs. | `GET /api/connectors/{student_id}`; `POST /api/connectors/{student_id}`; `PUT /api/connectors/{connector_id}/credentials`; `GET /api/connectors/{connector_id}/history`; `POST /api/connectors/{connector_id}/sync`; `GET /api/jobs/{job_id}`; `GET /api/sync-jobs/{student_id}` |
| **Operational/developer only** — debug search and diagnostics; do not put in the student navigation. `GET /api/metrics/summary` is admin-only in addition to normal auth. | `GET /api/agent/debug-plan`; `GET /api/director/debug-plan`; `GET /api/debug/chroma`; `GET /api/debug/search`; `GET /api/rag/debug-search`; `GET /api/pyq/debug/questions/{material_id}`; `GET /api/profile/debug/{student_id}`; `GET /api/system/metrics`; `GET /api/metrics/summary` |

The operation table also includes `GET /` as a public root/status response. The complete contract artifact covers any operation not obvious from the capability descriptions above. Do not turn developer diagnostics into user-facing features merely because they appear in OpenAPI.

## 6. Important workflow details

### Initial app load

1. Load auth state, validate an available access token with `GET /api/auth/me`, and refresh on an expired access token if a refresh token exists.
2. Fetch the signed-in student's core data using the `student.id` returned from auth. Load courses/subjects and then request dashboard/calendar/notification data as needed.
3. Treat a `403` or owner-scoped `404` as a real access/data condition; do not silently retry against another student ID.
4. Design for empty states: a new student may have no courses, materials, plans, quiz history, analytics, or reminders.

### Study materials and background work

- The upload route is `POST /api/materials/upload`, consumes `multipart/form-data`, and returns `202 Accepted` with a material response. Read the exact multipart property names/metadata in OpenAPI; do not hand-set a JSON content type or manually set the multipart boundary.
- Show queued/processing/succeeded/failed states using `processing_job_id` / `processing_status` where present and `GET /api/jobs/{job_id}` with the required `student_id`. Poll with a bounded interval/backoff and stop when terminal; expose retry/error details safely.
- `POST /api/materials/{material_id}/embed` also returns `202` and a job response. Do not claim the material is searchable until the job has completed successfully.
- Upload constraints currently include PDF MIME type and a maximum size of 25 MiB. Validate for usability in the UI, but the server remains authoritative. Handle `413`, `422`, and provider/dependency `503`.

### Chat

- Create/list sessions, read a session's messages using `limit`/`offset`, and send a `POST /api/chat` request. Chat response includes the session ID, stored user/assistant message IDs, answer, agent/tool attribution, and creation time.
- For a new conversation, the chat request can include `student_id`; for an existing session pass `session_id`. Use the signed-in student's ID and never let client-side session selection bypass ownership checks.
- Render errors and assistant responses as ordinary request/response data; do not implement SSE, WebSockets, or token streaming because those are not part of this contract.

### Quiz and practice

- Quizzes are generated by sending questions to `POST /api/quizzes/generate`, then submitted to `POST /api/quizzes/submit`. The server scores submitted answers and may update topic mastery (the request has an `update_mastery` option).
- Never reveal `correct_answer` while the user is taking the quiz. It may be present in generated quiz payloads because the API response includes question records; keep it server-side/in protected state and only render it after submission. This is a critical UI/data-flow rule.
- Practice endpoints are separate from quiz session endpoints; inspect their exact request/response schema and build their screen only around returned fields.

### Subject context and retrieval

- Provide a clear subject selector where an operation is subject-specific. Use course/subject/topic/material identifiers from API responses; do not guess IDs from labels.
- `POST /api/rag/ask` is the grounded-answer workflow. Display any citations/source material fields only if the actual response includes them; never fabricate citations.
- PYQ, flashcard, mastery, and readiness endpoints are subject/topic dependent. Show useful empty/error states when a subject has no material or indexed content.

## 7. API implementation rules

- Create one HTTP client that sets the base URL, JSON headers, bearer auth, request timeout/abort handling, envelope parsing, and typed errors. For multipart upload, allow the browser to set the multipart content type/boundary.
- Define TypeScript DTOs only from the OpenAPI component schemas and verified runtime contracts. The OpenAPI wrapper response model name may look like `SuccessResponse_...`; unwrap exactly one `data` property at the client boundary.
- Preserve error `code`, `message`, and HTTP status in an application error object. Map `401`, `403`, `404`, `409`, `413`, `422`, `429`, and `503` to appropriate flows; validation messages should identify fields where available.
- Use abortable requests and avoid stale response races when a user changes the selected subject/student or navigates away.
- Follow pagination parameters exactly (`skip`/`limit`, `offset`/`limit` depending on endpoint). Do not assume all list operations use one common pagination convention.
- Use ISO timestamps returned by the API; format for display in the user's locale/time zone without changing values sent back. Send date values in the exact format declared by the operation schema.
- Avoid optimistic updates for destructive or stateful operations until the response contract is understood. Confirm destructive actions, then refresh or reconcile relevant query data.
- Be mindful of rate limits (notably auth, chat, uploads, connector sync, and alert generation). Disable duplicate submits and explain `429` with a retry delay if the response provides one.
- Do not expose admin-only metrics or diagnostic routes to student users. Never collect or show tokens, raw connector credentials, JWT secrets, API keys, database URLs, or internal stack traces.

## 8. Contract limitations and non-features

- 92 operations have unconstrained `Any` success `data` according to the backend freeze audit. Their envelope is stable, but their inner data is not machine-frozen. Validate each such response before building detailed UI logic; if the shape is unclear, use a guarded/fallback presentation and record the uncertainty instead of inventing an interface.
- OpenAPI lacks bearer-auth metadata even though the API enforces auth. Use the auth labels in the generated API reference and the middleware's public-route exceptions.
- No frontend app, route system, design system, or package manifest was present in `frontend/` at handoff. Preserve existing repository conventions if files have since been added.
- No MIS/SVNIT MIS login, MIS-derived account sync, or MIS-backed data should be built.
- No contract is documented for real-time chat streaming, push notifications, WebSockets, or external OAuth callback cookies.
- The endpoint reference includes debug/health/admin APIs for backend operations; their presence is not a requirement to expose them as student features.

## 9. Suggested implementation sequence

1. Inspect repository and create/confirm the frontend app scaffold; add a local `.env.example` with a placeholder API origin only (no secrets).
2. Build the shared API client, envelope/error handling, Google sign-in, auth state, refresh rotation, logout, and protected-route handling.
3. Implement app shell, profile/student context, core dashboard, course/subject selection, and empty/loading/error states.
4. Implement materials upload/processing and subject-aware tutor/chat. Verify background polling and ownership-safe behavior.
5. Implement study plan/calendar/deadlines, then practice/quiz/flashcards and learning/analytics.
6. Add remaining student capabilities (goals/habits/reminders/notifications/semester/attendance/grades) using the endpoint capability map and contract.
7. Add responsive/accessibility passes, tests, production build, and a real browser-to-staging API smoke test from an allowed CORS origin.

## 10. Definition of done

- Google sign-in succeeds against configured staging credentials; refresh rotates token pairs correctly; logout clears client auth; expired/invalid credentials return the user to sign-in without request loops.
- Every implemented user workflow consumes real API data and uses the standard envelope; no core screen depends on hardcoded mock records.
- A student can navigate courses/subjects, upload a PDF and see processing status, use chat/history, create/view/complete a study plan, interact with supported practice/review workflows, and review calendar/deadline/progress data where the backend has records.
- All state-changing actions display success/error feedback; forms handle server validation; destructive actions are confirmed.
- No user can access another student's data by editing URL/query/body identifiers; the frontend always binds to the authenticated student and backend ownership enforcement remains enabled.
- Loading, empty, offline/network, unauthorized, forbidden, not-found, conflict, validation, rate-limit, oversized upload, and dependency failure states are tested.
- No MIS feature, secret, debug console, raw error stack, or provider credential is exposed.
- App is usable on mobile and desktop, keyboard accessible, and has clear labels/focus/contrast.
- Unit/component tests and production build pass. Provide setup/run instructions, required frontend environment variables, and any backend contract uncertainties discovered.

## 11. Handoff files and source of truth

Provide the implementation agent these repository artifacts:

1. This document: [`CLAUDE_FRONTEND_BUILD_BRIEF.md`](./CLAUDE_FRONTEND_BUILD_BRIEF.md) — product workflows, backend integration behavior, endpoint purpose map, and build/acceptance requirements.
2. [`docs/FRONTEND_API_REFERENCE.md`](./docs/FRONTEND_API_REFERENCE.md) — complete operation inventory and exact parameter/body/response component references.
3. [`OPENAPI_AUDIT.md`](./OPENAPI_AUDIT.md) — schema coverage and known contract limitations.
4. [`docs/openapi.json`](./docs/openapi.json), then the live `{API_ORIGIN}/openapi.json` or `/docs` during implementation — field-level schemas for the contract snapshot and the running backend.

Supporting release/deployment context is in [`BACKEND_FREEZE_REPORT.md`](./BACKEND_FREEZE_REPORT.md), [`BACKEND_RELEASE_NOTES.md`](./BACKEND_RELEASE_NOTES.md), and [`SYSTEM_ARCHITECTURE.md`](./SYSTEM_ARCHITECTURE.md).
