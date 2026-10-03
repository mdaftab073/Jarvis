# Frontend API Reference

Generated from the registered FastAPI OpenAPI schema by `backend/scripts/generate_api_inventory.py`.

- OpenAPI version: 3.1.0
- Paths: 133
- Operations: 159
- Success envelope: `{ "success": true, "data": ... }`.
- Error envelope: `{ "success": false, "error": { "code": "...", "message": "..." } }`.
- Authentication is derived from backend middleware; the OpenAPI schema currently has no `securitySchemes` declaration.
- All `/api/*` operations require a bearer access token except the listed public authentication and health operations. `GET /api/metrics/summary` also requires `X-Admin-Token`.
- Browser clients must use an origin included in `ALLOWED_ORIGINS`.
- Follow request/response component names in `/openapi.json` for field-level schemas. An `Any` response leaves the inner `data` payload unspecified.

| Method | Route | Auth | Request body / parameters | Success response | Common error statuses |
|---|---|---|---|---|---|
| DELETE | `/api/calendar/events/{event_id}` | Bearer access token | event_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| DELETE | `/api/chat/sessions/{session_id}` | Bearer access token | session_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| DELETE | `/api/goals/{goal_id}` | Bearer access token | goal_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| DELETE | `/api/habits/{habit_id}` | Bearer access token | habit_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| DELETE | `/api/reminders/{reminder_id}` | Bearer access token | reminder_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| DELETE | `/api/students/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/academic-profiles/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/academic-profiles/{student_id}/preferences` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/academic-profiles/{student_id}/summary` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/agent/debug-plan` | Bearer access token | student_id (query, integer, required), goal (query, string, required) | 200: SuccessResponse_AcademicAgentDebugResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/analytics/dashboard/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_AnalyticsDashboard_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/analytics/readiness/{student_id}/{subject_id}` | Bearer access token | student_id (path, integer, required), subject_id (path, integer, required) | 200: SuccessResponse_ReadinessResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/analytics/recommendations/{student_id}/{subject_id}` | Bearer access token | student_id (path, integer, required), subject_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/analytics/strong-topics/{student_id}/{subject_id}` | Bearer access token | student_id (path, integer, required), subject_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/analytics/weak-topics/{student_id}/{subject_id}` | Bearer access token | student_id (path, integer, required), subject_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/attendance/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/auth/me` | Bearer access token | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/calendar/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/calendar/{student_id}/today` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/calendar/{student_id}/tomorrow` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/calendar/{student_id}/week` | Bearer access token | student_id (path, integer, required), start_date (query, inline schema, optional) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/chat/sessions` | Bearer access token | student_id (query, integer, required), limit (query, integer, optional, default=50) | 200: SuccessResponse_list_ChatSessionResponse__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/chat/sessions/{session_id}` | Bearer access token | session_id (path, integer, required) | 200: SuccessResponse_ChatSessionResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/chat/sessions/{session_id}/messages` | Bearer access token | session_id (path, integer, required), limit (query, integer, optional, default=100), offset (query, integer, optional, default=0) | 200: SuccessResponse_list_ChatMessageResponse__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/connectors/{connector_id}/history` | Bearer access token | connector_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/connectors/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/courses` | Bearer access token | None | 200: SuccessResponse_list_CourseResponse__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/courses/{course_id}` | Bearer access token | course_id (path, integer, required) | 200: SuccessResponse_CourseResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/courses/{course_id}/subjects` | Bearer access token | course_id (path, integer, required) | 200: SuccessResponse_CourseWithSubjects_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/dashboard/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/db-health` | Bearer access token | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/deadlines/{student_id}` | Bearer access token | student_id (path, integer, required), include_completed (query, boolean, optional, default=False) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/deadlines/{student_id}/overdue` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/deadlines/{student_id}/upcoming` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/debug/chroma` | Bearer access token | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/debug/search` | Bearer access token | query (query, string, required), subject_id (query, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/director/debug-plan` | Bearer access token | student_id (query, integer, required), goal (query, string, required), subject_id (query, inline schema, optional) | 200: SuccessResponse_DirectorDebugResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/flashcards/decks` | Bearer access token | subject_id (query, integer, required), skip (query, integer, optional, default=0), limit (query, integer, optional, default=100) | 200: SuccessResponse_List_FlashcardDeck__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/flashcards/decks/{deck_id}` | Bearer access token | deck_id (path, integer, required) | 200: SuccessResponse_FlashcardDeck_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/flashcards/topic/{topic_id}` | Bearer access token | topic_id (path, integer, required), skip (query, integer, optional, default=0), limit (query, integer, optional, default=100) | 200: SuccessResponse_List_Flashcard__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/goals/{student_id}` | Bearer access token | student_id (path, integer, required), include_completed (query, boolean, optional, default=True) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/grades/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/grades/{student_id}/analytics` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/habits/{habit_id}/logs` | Bearer access token | habit_id (path, integer, required), start (query, inline schema, optional), end (query, inline schema, optional) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/habits/{student_id}` | Bearer access token | student_id (path, integer, required), active_only (query, boolean, optional, default=True) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/health` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/health/dependencies` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/health/live` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/health/ready` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/jobs/{job_id}` | Bearer access token | job_id (path, integer, required), student_id (query, integer, required) | 200: SuccessResponse_JobExecutionResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/learning/history/{student_id}` | Bearer access token | student_id (path, integer, required), skip (query, integer, optional, default=0), limit (query, integer, optional, default=50) | 200: SuccessResponse_List_LearningSessionResponse__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/learning/insights/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_LearningInsightsResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/mastery/student/{student_id}` | Bearer access token | student_id (path, integer, required), skip (query, integer, optional, default=0), limit (query, integer, optional, default=100) | 200: SuccessResponse_List_MasteryWithTopic__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/mastery/subject/{subject_id}` | Bearer access token | subject_id (path, integer, required), student_id (query, integer, required) | 200: SuccessResponse_List_MasteryWithTopic__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/mastery/weak/{student_id}` | Bearer access token | student_id (path, integer, required), threshold (query, number, optional, default=50.0), limit (query, integer, optional, default=20) | 200: SuccessResponse_List_MasteryWithTopic__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/materials` | Bearer access token | student_id (query, integer, required) | 200: SuccessResponse_list_StudyMaterialResponse__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/materials/{material_id}` | Bearer access token | material_id (path, integer, required) | 200: SuccessResponse_StudyMaterialResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/materials/{material_id}/chunks` | Bearer access token | material_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/materials/{material_id}/extract-text` | Bearer access token | material_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/metrics/summary` | Bearer access token + `X-Admin-Token` | x-admin-token (header, inline schema, optional) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/milestones/{goal_id}` | Bearer access token | goal_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/notifications/{student_id}` | Bearer access token | student_id (path, integer, required), unread_only (query, boolean, optional, default=False) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/profile/debug/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/profile/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_ProfileResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/profile/{student_id}/memories` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/profile/{student_id}/readiness-history` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/profile/{student_id}/summary` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_ProfileSummaryResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/progress/{goal_id}` | Bearer access token | goal_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/pyq/debug/questions/{material_id}` | Bearer access token | material_id (path, integer, required) | 200: SuccessResponse_ExtractedQuestionsResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/pyq/important-topics/{subject_id}` | Bearer access token | subject_id (path, integer, required) | 200: SuccessResponse_list_ImportantTopic__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/pyq/revision-plan/{subject_id}` | Bearer access token | subject_id (path, integer, required) | 200: SuccessResponse_RevisionPlanResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/pyq/topics/{subject_id}` | Bearer access token | subject_id (path, integer, required) | 200: SuccessResponse_TopicDashboardResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/pyq/trends/{subject_id}` | Bearer access token | subject_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/quizzes/history/{student_id}` | Bearer access token | student_id (path, integer, required), skip (query, integer, optional, default=0), limit (query, integer, optional, default=50) | 200: SuccessResponse_List_QuizSession__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/quizzes/session/{session_id}` | Bearer access token | session_id (path, integer, required) | 200: SuccessResponse_QuizSessionWithQuestions_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/rag/debug-search` | Bearer access token | query (query, string, required), subject_id (query, inline schema, optional) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/reminders/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/schedule/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/semester/{semester_id}` | Bearer access token | semester_id (path, integer, required) | 200: SuccessResponse_SemesterResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/semester/{semester_id}/copilot` | Bearer access token | semester_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/semester/{semester_id}/health` | Bearer access token | semester_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/semester/{semester_id}/review` | Bearer access token | semester_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/semester/{semester_id}/risks` | Bearer access token | semester_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/students` | Bearer access token | None | 200: SuccessResponse_list_StudentResponse__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/students/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_StudentResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/students/{student_id}/courses` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_StudentWithCourses_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/study-plans/{plan_id}` | Bearer access token | plan_id (path, integer, required) | 200: SuccessResponse_StudyPlanResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/study-plans/{plan_id}/progress` | Bearer access token | plan_id (path, integer, required) | 200: SuccessResponse_PlanProgress_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/subjects` | Bearer access token | None | 200: SuccessResponse_list_SubjectResponse__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/subjects/{subject_id}` | Bearer access token | subject_id (path, integer, required) | 200: SuccessResponse_SubjectResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/subjects/{subject_id}/materials` | Bearer access token | subject_id (path, integer, required) | 200: SuccessResponse_list_StudyMaterialResponse__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/subjects/{subject_id}/topics` | Bearer access token | subject_id (path, integer, required), skip (query, integer, optional, default=0), limit (query, integer, optional, default=100) | 200: SuccessResponse_List_Topic__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/sync-jobs/{student_id}` | Bearer access token | student_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/system/metrics` | Bearer access token | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/topics` | Bearer access token | skip (query, integer, optional, default=0), limit (query, integer, optional, default=100) | 200: SuccessResponse_List_Topic__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/api/topics/{topic_id}` | Bearer access token | topic_id (path, integer, required) | 200: SuccessResponse_Topic_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/health` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/health/dependencies` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/health/live` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/health/ready` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| GET | `/system/health` | Public | None | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/deadlines/{deadline_id}/complete` | Bearer access token | deadline_id (path, integer, required), application/json (required): DeadlineCompletionInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/goals/{goal_id}` | Bearer access token | goal_id (path, integer, required), application/json (required): GoalUpdateInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/habits/{habit_id}` | Bearer access token | habit_id (path, integer, required), application/json (required): HabitUpdateInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/milestones/{milestone_id}/complete` | Bearer access token | milestone_id (path, integer, required), completed (query, boolean, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/notifications/{notification_id}/read` | Bearer access token | notification_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/reminders/{reminder_id}` | Bearer access token | reminder_id (path, integer, required), application/json (required): ReminderUpdate | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/semester/{semester_id}/milestone/{milestone_id}` | Bearer access token | semester_id (path, integer, required), milestone_id (path, integer, required), application/json (required): SemesterMilestoneUpdateRequest | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/semester/{semester_id}/status` | Bearer access token | semester_id (path, integer, required), application/json (required): SemesterStatusUpdateRequest | 200: SuccessResponse_SemesterResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PATCH | `/api/study-plans/tasks/{task_id}/complete` | Bearer access token | task_id (path, integer, required) | 200: SuccessResponse_StudyPlanResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/agent/academic` | Bearer access token | application/json (required): AcademicAgentRequest | 200: SuccessResponse_AcademicAgentResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/attendance/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): AttendanceInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/auth/google` | Public | application/json (required): GoogleLoginRequest | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/auth/logout` | Bearer access token | application/json (required): RefreshRequest | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/auth/refresh` | Public | application/json (required): RefreshRequest | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/calendar/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): CalendarEventInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/chat` | Bearer access token | application/json (required): ChatRequest | 200: SuccessResponse_ChatResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/chat/sessions` | Bearer access token | application/json (required): CreateSessionRequest | 200: SuccessResponse_ChatSessionResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/connectors/{connector_id}/sync` | Bearer access token | connector_id (path, integer, required) | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/connectors/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): ConnectorCreateInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/courses` | Bearer access token | application/json (required): CourseCreate | 200: SuccessResponse_CourseResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/deadlines/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): DeadlineInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/director/academic` | Bearer access token | application/json (required): DirectorAcademicRequest | 200: SuccessResponse_DirectorAcademicResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/flashcards/generate` | Bearer access token | application/json (required): FlashcardGenerateRequest | 200: SuccessResponse_FlashcardGenerateResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/goals/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): GoalCreateInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/grades/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): GradeInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/habits/{habit_id}/logs` | Bearer access token | habit_id (path, integer, required), application/json (required): HabitLogInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/habits/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): HabitCreateInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/learning/session` | Bearer access token | application/json (required): LearningSessionCreate | 200: SuccessResponse_LearningSessionResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/materials` | Bearer access token | application/json (required): StudyMaterialCreate | 200: SuccessResponse_StudyMaterialResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/materials/upload` | Bearer access token | multipart/form-data (required): Body__upload_material_background_api_materials_upload_post | 202: SuccessResponse_StudyMaterialResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/materials/{material_id}/embed` | Bearer access token | material_id (path, integer, required) | 202: SuccessResponse_JobExecutionResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/milestones/{goal_id}` | Bearer access token | goal_id (path, integer, required), application/json (required): MilestoneInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/notifications/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): NotificationInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/notifications/{student_id}/generate-alerts` | Bearer access token | student_id (path, integer, required) | 202: SuccessResponse_JobExecutionResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/practice/start` | Bearer access token | application/json (required): PracticeStartRequest | 200: SuccessResponse_PracticeStartResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/practice/submit` | Bearer access token | application/json (required): PracticeSubmitRequest | 200: SuccessResponse_PracticeSubmitResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/progress/{goal_id}` | Bearer access token | goal_id (path, integer, required), application/json (required): ProgressInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/pyq/generate-practice` | Bearer access token | application/json (required): PracticeQuestionRequest | 200: SuccessResponse_PracticeQuestionResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/quizzes/generate` | Bearer access token | application/json (required): QuizGenerateRequest | 200: SuccessResponse_QuizSessionWithQuestions_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/quizzes/submit` | Bearer access token | application/json (required): QuizSubmitRequest | 200: SuccessResponse_QuizSubmitResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/rag/ask` | Bearer access token | application/json (required): AskRequest | 200: SuccessResponse_AskResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/reminders/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): ReminderInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/schedule/{student_id}/blocks` | Bearer access token | student_id (path, integer, required), application/json (required): StudyBlockInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/schedule/{student_id}/generate` | Bearer access token | student_id (path, integer, required), application/json (required): ScheduleInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/schedule/{student_id}/intelligent` | Bearer access token | student_id (path, integer, required), application/json (required): IntelligentScheduleInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/semester` | Bearer access token | application/json (required): SemesterCreateRequest | 201: SuccessResponse_SemesterResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/semester/{semester_id}/milestone` | Bearer access token | semester_id (path, integer, required), application/json (required): SemesterMilestoneCreateRequest | 201: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/students` | Bearer access token | application/json (required): StudentCreate | 200: SuccessResponse_StudentResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/study-plans/generate` | Bearer access token | application/json (required): StudyPlanGenerateRequest | 200: SuccessResponse_StudyPlanResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/study-plans/{plan_id}/recalculate` | Bearer access token | plan_id (path, integer, required) | 200: SuccessResponse_RecalculateResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/subjects` | Bearer access token | application/json (required): SubjectCreate | 200: SuccessResponse_SubjectResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| POST | `/api/topics/extract/{material_id}` | Bearer access token | material_id (path, integer, required), subject_id (query, integer, required) | 200: SuccessResponse_List_Topic__ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PUT | `/api/academic-profiles/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): ProfileInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PUT | `/api/academic-profiles/{student_id}/preferences` | Bearer access token | student_id (path, integer, required), application/json (required): PreferenceInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PUT | `/api/calendar/events/{event_id}` | Bearer access token | event_id (path, integer, required), application/json (required): CalendarEventInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PUT | `/api/connectors/{connector_id}/credentials` | Bearer access token | connector_id (path, integer, required), application/json (required): ConnectorCredentialsInput | 200: SuccessResponse_Any_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
| PUT | `/api/students/{student_id}` | Bearer access token | student_id (path, integer, required), application/json (required): StudentUpdate | 200: SuccessResponse_StudentResponse_ | 400, 401, 403, 404, 409, 413, 422, 429, 500, 503 |
