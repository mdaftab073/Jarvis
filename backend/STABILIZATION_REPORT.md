# Jarvis Backend Stabilization

## Canonical Ownership

`student_id` is the canonical owner for student-owned records. It is non-null for academic profiles, attendance, grades, deadlines, study activity, digital-twin snapshots, notifications, calendar events, study blocks, reminders, goals, preferences, and habits. `academic_profile_id` remains a required relationship key on the five digital-twin-owned record types that historically used it.

The `before_flush` ownership hook fills a missing `student_id` from an attached academic profile and rejects an owner/profile mismatch. `student_owned_query` is the common read path for records that must remain visible through profile ownership during compatibility transitions. The stabilization migration backfills legacy records before making canonical ownership non-null.

## Grades and Deadlines

Grade records are classified as `COMPONENT` or `FINAL`. The migration classifies historical rows as `FINAL` only when semester, credits, and grade points are present; other historical assessment rows remain `COMPONENT`. Grade letters now use one physical `grade_letter` column, exposed as canonical ORM `grade` with a legacy `grade_letter` synonym. SPI/CPI use only valid final-grade rows, deduplicate by subject, weight by credits, and update profile aggregates after grade create/update/delete.

`AcademicDeadline` is the canonical mapped class on the existing `deadline_items` table. `DeadlineItem` remains a Python compatibility alias. Canonical `type` and `completed` map to legacy physical columns `item_type` and `is_completed`; the deadline service owns serialization and CRUD semantics.

## Dashboard and Scheduling

Dashboard readiness is calculated from current attendance and mastery inputs, not the latest snapshot. The latest snapshot is returned separately with its capture time. Live grade records and shared SPI/CPI analytics are included. Missing profiles or snapshots are represented safely while independent mastery, notification, and calendar information remains available.

Calendar and schedule datetimes are normalized to UTC-naive values to match the existing database columns. Conflict detection rejects reversed intervals and detects overlaps with both study blocks and calendar events. Touching intervals are allowed. Reminder generation clamps near-term triggers to the current time so it does not create already-expired reminders.

## Reminder API

- `GET /api/reminders/{student_id}`
- `POST /api/reminders/{student_id}`
- `PATCH /api/reminders/{reminder_id}`
- `DELETE /api/reminders/{reminder_id}`

## Authorization Preparation and Remaining Exposure

`app.api.student_scope` provides two hooks: student-ID validation with optional `request.state.student_id` principal matching, and record-owner matching. The hooks are wired into Phase A routes and legacy profile/analytics/learning/mastery/student/quiz/plan/director/semester/course/subject routes. No login, JWT, principal middleware, role model, or authentication enforcement has been added. When no principal is present, these hooks check existence and allow the requested owner; they are preparation interfaces, not access control.

Before deploying a multi-student authenticated API, extend scope enforcement to remaining resource-ID surfaces, including study-material/topic/flashcard endpoints and PYQ subject endpoints. Collection endpoints such as `/api/students`, `/api/courses`, and `/api/subjects` require an explicit authorization policy. Student deletion and administrative operations need role checks rather than simple self-ownership.

## Migration and Validation

The single Alembic head is `d14e6f2a9b31`. The migration was tested with historical profile-only records, canonical/legacy grade values, upgrade, downgrade to `c82d4e6f1a30`, and re-upgrade using disposable SQLite. It was not applied to the configured developer database.

Run from `backend/`:

```powershell
.\.venv\Scripts\python.exe -W ignore scripts/validate_stabilization.py
```

The validator checks historical migration backfills, schema contracts, grade behavior, deadline naming, reminder operations, dashboard presence, scheduler-related tests, agent registry, director routing, and runs the full unittest suite.

Final local evidence: one Alembic head (`d14e6f2a9b31`), 97 registered `/api` paths, and 126 backend tests passing. The migration lifecycle was verified against seeded historical rows in a disposable SQLite database; the configured developer database was not migrated.

## Unresolved Technical Debt

- Existing non-Phase-A APIs still expose unscoped resource IDs and collection reads; use the authorization inventory above before enabling authenticated multi-tenant access.
- Ownership equality between `student_id` and `academic_profile_id` is enforced by ORM flush handling, not a composite database foreign key. Direct SQL writers must preserve the same invariant.
- Datetimes are stored naive after UTC normalization for compatibility. A future timezone-aware schema migration requires a data conversion plan.
- `StudentGoal` and `StudentHabit` remain persistence-only entities; no new workflows were introduced in this stabilization pass.
