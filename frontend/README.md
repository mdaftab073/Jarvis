# Jarvis frontend

React + TypeScript + Vite, TanStack Query, React Router. Built against `BACKEND_API_CONTRACT.md` / `openapi.json` (snapshot 2026-10-03).

## Run
```bash
cp .env.example .env     # VITE_API_BASE_URL, VITE_GOOGLE_CLIENT_ID
npm install
npm run dev              # http://localhost:5173  (add --host to test from your phone on the same Wi‑Fi)
npm test && npm run build
```
- `VITE_GOOGLE_CLIENT_ID` must equal the backend `GOOGLE_CLIENT_ID`; add your frontend origin to the Google client's authorized JavaScript origins **and** to backend `ALLOWED_ORIGINS`.
- Testing on an Android phone: use `npm run dev -- --host`, open `http://<your-pc-ip>:5173`, and add that exact origin to `ALLOWED_ORIGINS`. Google sign-in requires an origin Google accepts (localhost, or HTTPS on a real domain) — for phone testing use a deployed HTTPS URL or a tunnel.

## Layout
- `src/api/client.ts` — envelope unwrap, typed errors, bearer auth, single-flight refresh rotation, multipart-safe.
- `src/auth/` — auth, shared subject selection (per student).
- `src/components/ui.tsx` — Async states, forms (`CreateForm`, `EditForm`, `ResourcePanel`), `DataView` fallback.
- `src/pages/` — Home, Courses, Materials, Tutor, Plan, Practice, Progress, Inbox, Profile.

## Responsive / Android
Sidebar on desktop; bottom tab bar + "More" sheet below 900px. Safe-area insets, `100dvh` chat, 16px inputs (no zoom on Android Chrome), 44px touch targets, Enter-to-send only on hover devices (Enter inserts a newline on phones).

## Contract-driven decisions
- `/api/quizzes/generate` takes **client-written questions**, so "Quiz lab" lets you write them; the main practice flow uses `/api/practice/start|submit` (server-generated and graded). `correct_answer` is stripped from state until results.
- No endpoint lists a deck's cards: opening a deck fetches `/flashcards/topic/{id}` for each topic and keeps that deck's cards (cards without a topic won't appear). Just-generated decks show instantly.
- No list endpoints for study plans/semesters: IDs are remembered per student in localStorage.
- Datetime fields are sent as ISO-8601 UTC. If the backend expects naive local times, change `toIso` in `src/lib/format.ts`.
- Job polling (`202` upload/embed/alerts) uses `GET /api/jobs/{id}?student_id=`, backoff 2s→15s.
- Tokens: access in memory, refresh in `sessionStorage`; never logged.

## Not built
Student CRUD, connectors, director endpoint, milestones/progress history per goal (progress can be logged), calendar event editing (create/delete only), material deletion (no endpoint).

## Unverified
Enum values for calendar `event_type`, job `status` strings, and study-task `status` aren't in the contract; the UI accepts common values (`completed/done/succeeded…`). Not yet run against your live backend or a physical Android device.
