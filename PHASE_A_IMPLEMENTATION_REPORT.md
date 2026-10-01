# Phase A: Student Operating System Core

## Architecture

Phase A extends Jarvis's existing digital-twin schema and services rather than replacing Phase 15 contracts. `StudentAcademicProfile`, `AttendanceRecord`, `GradeRecord`, and `DeadlineItem` retain their existing table names and legacy fields. The profile remains one-to-one with `Student`; attendance, grades, and deadlines remain owned through `academic_profile_id`, with nullable direct `student_id` references added and backfilled for student-scoped access. `AcademicDeadline` is exposed as a model alias over `DeadlineItem`, including `type` and `completed` synonyms.

The existing component-grade model is extended with `semester`, `credits`, `grade`, and `grade_points`. SPI and CPI use credit-weighted grade points. Attendance risk is `SAFE` at 75% or above, `WARNING` from 65% through 74.99%, and `CRITICAL` below 65%.

## Entity Relationships

- `Student` has one `StudentAcademicProfile`; profile owns attendance, grade, deadline, study activity, and digital-twin snapshot records.
- Attendance, grades, and deadlines reference their profile and optionally reference their student directly for backward compatibility; attendance and grades also reference `Subject`.
- `StudentNotification`, `CalendarEvent`, `StudyBlock`, `Reminder`, `StudentGoal`, `StudentPreference`, and `StudentHabit` reference `Student` with cascading deletion.
- `StudyBlock` optionally references `Subject`.
- Student preferences are unique per student; calendar events and study blocks enforce start-before-end constraints.

## APIs

All routes are registered under `/api`:

- `academic-profiles`: profile read/upsert, academic summary, and study preferences.
- `attendance`: student attendance retrieval and subject attendance upsert, including risk.
- `grades`: grade retrieval/creation and SPI/CPI analytics.
- `deadlines`: retrieval, upcoming/overdue listing, creation, and completion; payloads expose `type` and `completed`.
- `notifications`: retrieval, creation, alert generation, and read marking.
- `calendar`: event retrieval, creation, update, and deletion.
- `schedule`: study-block retrieval/creation and generated schedule creation with conflict checks against both study blocks and calendar events.
- `dashboard`: `GET /api/dashboard/{student_id}` aggregates profile, attendance, mastery, readiness, deadlines, unread notifications, and calendar events.

The current OpenAPI schema contains 95 `/api` paths.

## Agents

Registered specialists: `AcademicProfileAgent`, `AttendanceAgent`, `DeadlineAgent`, `NotificationAgent`, `CalendarAgent`, `SchedulerAgent`, and `ReminderAgent`. Director intent routing covers attendance, deadlines, calendar, schedule, profile, notifications, and reminders; legacy agent ordering for exam planning remains unchanged.

## Dashboard

The dashboard reads the latest digital-twin snapshot for readiness, current mastery records, subject attendance risks/recovery counts, upcoming deadlines, unread notifications, and calendar events. A missing academic profile returns a valid empty dashboard payload.

## Validation Evidence

- Alembic has one head: `c82d4e6f1a30`, directly following `b25c9e1f3a40`.
- Full migration upgrade, Phase A downgrade, and re-upgrade succeeded on a disposable SQLite database.
- OpenAPI imports successfully and includes every requested route family.
- `tests/test_phaseA_student_os.py` covers model relationships/constraints, attendance rules and recovery, SPI/CPI, deadline ordering, schedule conflicts, notifications, API/dashboard aggregation, agent execution, and director routing.
- `scripts/validate_phaseA.py` repeats isolated migration lifecycle checks, verifies registered tables/services/agents/routes, and runs the Phase A test module.

## Compatibility Notes and Remaining Risks

- `academic_deadlines` is not a separate physical table; Phase A uses the pre-existing `deadline_items` table and exposes `AcademicDeadline` as a compatible model alias to avoid splitting legacy deadline data.
- Semester grades and component grades share `grade_records`; existing component entries remain valid, while SPI/CPI includes records with semester, credits, and grade points.
- The dashboard readiness value is the latest stored digital-twin snapshot and remains `null` until a snapshot is generated.
- The project environment currently lacks `pytest`; the included tests and validation run with Python's built-in `unittest` runner.
