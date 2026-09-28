# API Summary

Base URL: `http://localhost:8000`. Most application APIs are under `/api`; `/system/health` and `/` are root-level.

## Platform and Data

| Methods | Routes | Purpose |
|---|---|---|
| GET | `/`, `/api/health`, `/api/db-health`, `/system/health` | Service and dependency health |
| GET, POST, PUT, DELETE | `/api/students`, `/api/students/{student_id}` | Student records |
| GET, POST | `/api/courses`, `/api/courses/{course_id}`, `/api/courses/{course_id}/subjects` | Courses |
| GET, POST | `/api/subjects`, `/api/subjects/{subject_id}`, `/api/subjects/{subject_id}/materials` | Subjects |
| GET, POST | `/api/materials`, `/api/materials/upload`, `/api/materials/{material_id}` | Material records and PDF uploads |
| POST | `/api/materials/{material_id}/embed` | Extract, chunk, index, and embed a PDF |
| GET | `/api/materials/{material_id}/chunks`, `/api/materials/{material_id}/extract-text` | Material diagnostics |

## Retrieval and PYQ

| Methods | Routes | Purpose |
|---|---|---|
| POST | `/api/rag/ask` | Subject-aware hybrid RAG answer |
| GET | `/api/rag/debug-search`, `/api/debug/search`, `/api/debug/chroma` | Retrieval/vector diagnostics |
| GET | `/api/pyq/topics/{subject_id}`, `/api/pyq/trends/{subject_id}` | PYQ frequency and trends |
| GET | `/api/pyq/revision-plan/{subject_id}`, `/api/pyq/important-topics/{subject_id}` | Revision priorities |
| POST | `/api/pyq/generate-practice` | Practice question generation |
| GET | `/api/pyq/debug/questions/{material_id}` | Extracted-question diagnostics |

## Analytics and Planning

| Methods | Routes | Purpose |
|---|---|---|
| GET | `/api/analytics/dashboard/{student_id}` | Student overview |
| GET | `/api/analytics/readiness/{student_id}/{subject_id}` | Readiness and mastery |
| GET | `/api/analytics/weak-topics/{student_id}/{subject_id}`, `/api/analytics/strong-topics/{student_id}/{subject_id}` | Topic mastery groups |
| GET | `/api/analytics/recommendations/{student_id}/{subject_id}` | Personalized recommendations |
| POST | `/api/study-plans/generate` | Generate a study plan |
| GET | `/api/study-plans/{plan_id}`, `/api/study-plans/{plan_id}/progress` | Plan and progress |
| PATCH, POST | `/api/study-plans/tasks/{task_id}/complete`, `/api/study-plans/{plan_id}/recalculate` | Update study tasks |
| POST | `/api/practice/start`, `/api/practice/submit` | Practice sessions |

## Profile, Semester, and Agents

| Methods | Routes | Purpose |
|---|---|---|
| GET | `/api/profile/{student_id}`, `/api/profile/{student_id}/summary`, `/api/profile/{student_id}/readiness-history`, `/api/profile/{student_id}/memories`, `/api/profile/debug/{student_id}` | Long-term student profile |
| POST | `/api/semester` | Create a semester with subject targets |
| GET | `/api/semester/{semester_id}`, `/api/semester/{semester_id}/health`, `/api/semester/{semester_id}/review`, `/api/semester/{semester_id}/risks`, `/api/semester/{semester_id}/copilot` | Semester status and guidance |
| POST, PATCH | `/api/semester/{semester_id}/milestone`, `/api/semester/{semester_id}/milestone/{milestone_id}`, `/api/semester/{semester_id}/status` | Milestone and semester state |
| POST | `/api/agent/academic` | Single academic workflow agent |
| GET | `/api/agent/debug-plan` | Workflow-agent diagnostics |
| POST | `/api/director/academic` | Multi-agent academic strategy |
| GET | `/api/director/debug-plan` | Director execution diagnostics |

Interactive OpenAPI documentation is served at `/docs`.