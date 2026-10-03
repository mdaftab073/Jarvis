# Backend API Inventory

Generated from the registered FastAPI OpenAPI schema by `backend/scripts/generate_api_inventory.py`.

- Registered paths: 133
- Registered operations: 159
- Success response format: `{ "success": true, "data": ... }`.
- Error response format: `{ "success": false, "error": { "code": ..., "message": ... } }`.
- All API routes require a bearer access token except public health, Google login, and refresh routes. `GET /api/metrics/summary` also requires `X-Admin-Token`.
- The browser-origin allowlist is configured through comma-separated `ALLOWED_ORIGINS`; credentials are enabled and wildcard origins are rejected.

| Method | Route | Authentication | Request parameters/body | Success response schema |
|---|---|---|---|---|
| DELETE | `/api/calendar/events/{event_id}` | Bearer access token | event_id (path) | 200: SuccessResponse_Any_ |
| DELETE | `/api/chat/sessions/{session_id}` | Bearer access token | session_id (path) | 200: SuccessResponse_Any_ |
| DELETE | `/api/goals/{goal_id}` | Bearer access token | goal_id (path) | 200: SuccessResponse_Any_ |
| DELETE | `/api/habits/{habit_id}` | Bearer access token | habit_id (path) | 200: SuccessResponse_Any_ |
| DELETE | `/api/reminders/{reminder_id}` | Bearer access token | reminder_id (path) | 200: SuccessResponse_Any_ |
| DELETE | `/api/students/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/api/academic-profiles/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/academic-profiles/{student_id}/preferences` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/academic-profiles/{student_id}/summary` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/agent/debug-plan` | Bearer access token | student_id (query), goal (query) | 200: SuccessResponse_AcademicAgentDebugResponse_ |
| GET | `/api/analytics/dashboard/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_AnalyticsDashboard_ |
| GET | `/api/analytics/readiness/{student_id}/{subject_id}` | Bearer access token | student_id (path), subject_id (path) | 200: SuccessResponse_ReadinessResponse_ |
| GET | `/api/analytics/recommendations/{student_id}/{subject_id}` | Bearer access token | student_id (path), subject_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/analytics/strong-topics/{student_id}/{subject_id}` | Bearer access token | student_id (path), subject_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/analytics/weak-topics/{student_id}/{subject_id}` | Bearer access token | student_id (path), subject_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/attendance/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/auth/me` | Bearer access token | None | 200: SuccessResponse_Any_ |
| GET | `/api/calendar/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/calendar/{student_id}/today` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/calendar/{student_id}/tomorrow` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/calendar/{student_id}/week` | Bearer access token | student_id (path), start_date (query) | 200: SuccessResponse_Any_ |
| GET | `/api/chat/sessions` | Bearer access token | student_id (query), limit (query) | 200: SuccessResponse_list_ChatSessionResponse__ |
| GET | `/api/chat/sessions/{session_id}` | Bearer access token | session_id (path) | 200: SuccessResponse_ChatSessionResponse_ |
| GET | `/api/chat/sessions/{session_id}/messages` | Bearer access token | session_id (path), limit (query), offset (query) | 200: SuccessResponse_list_ChatMessageResponse__ |
| GET | `/api/connectors/{connector_id}/history` | Bearer access token | connector_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/connectors/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/courses` | Bearer access token | None | 200: SuccessResponse_list_CourseResponse__ |
| GET | `/api/courses/{course_id}` | Bearer access token | course_id (path) | 200: SuccessResponse_CourseResponse_ |
| GET | `/api/courses/{course_id}/subjects` | Bearer access token | course_id (path) | 200: SuccessResponse_CourseWithSubjects_ |
| GET | `/api/dashboard/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/db-health` | Bearer access token | None | 200: SuccessResponse_Any_ |
| GET | `/api/deadlines/{student_id}` | Bearer access token | student_id (path), include_completed (query) | 200: SuccessResponse_Any_ |
| GET | `/api/deadlines/{student_id}/overdue` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/deadlines/{student_id}/upcoming` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/debug/chroma` | Bearer access token | None | 200: SuccessResponse_Any_ |
| GET | `/api/debug/search` | Bearer access token | query (query), subject_id (query) | 200: SuccessResponse_Any_ |
| GET | `/api/director/debug-plan` | Bearer access token | student_id (query), goal (query), subject_id (query) | 200: SuccessResponse_DirectorDebugResponse_ |
| GET | `/api/flashcards/decks` | Bearer access token | subject_id (query), skip (query), limit (query) | 200: SuccessResponse_List_FlashcardDeck__ |
| GET | `/api/flashcards/decks/{deck_id}` | Bearer access token | deck_id (path) | 200: SuccessResponse_FlashcardDeck_ |
| GET | `/api/flashcards/topic/{topic_id}` | Bearer access token | topic_id (path), skip (query), limit (query) | 200: SuccessResponse_List_Flashcard__ |
| GET | `/api/goals/{student_id}` | Bearer access token | student_id (path), include_completed (query) | 200: SuccessResponse_Any_ |
| GET | `/api/grades/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/grades/{student_id}/analytics` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/habits/{habit_id}/logs` | Bearer access token | habit_id (path), start (query), end (query) | 200: SuccessResponse_Any_ |
| GET | `/api/habits/{student_id}` | Bearer access token | student_id (path), active_only (query) | 200: SuccessResponse_Any_ |
| GET | `/api/health` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/api/health/dependencies` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/api/health/live` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/api/health/ready` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/api/jobs/{job_id}` | Bearer access token | job_id (path), student_id (query) | 200: SuccessResponse_JobExecutionResponse_ |
| GET | `/api/learning/history/{student_id}` | Bearer access token | student_id (path), skip (query), limit (query) | 200: SuccessResponse_List_LearningSessionResponse__ |
| GET | `/api/learning/insights/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_LearningInsightsResponse_ |
| GET | `/api/mastery/student/{student_id}` | Bearer access token | student_id (path), skip (query), limit (query) | 200: SuccessResponse_List_MasteryWithTopic__ |
| GET | `/api/mastery/subject/{subject_id}` | Bearer access token | subject_id (path), student_id (query) | 200: SuccessResponse_List_MasteryWithTopic__ |
| GET | `/api/mastery/weak/{student_id}` | Bearer access token | student_id (path), threshold (query), limit (query) | 200: SuccessResponse_List_MasteryWithTopic__ |
| GET | `/api/materials` | Bearer access token | student_id (query) | 200: SuccessResponse_list_StudyMaterialResponse__ |
| GET | `/api/materials/{material_id}` | Bearer access token | material_id (path) | 200: SuccessResponse_StudyMaterialResponse_ |
| GET | `/api/materials/{material_id}/chunks` | Bearer access token | material_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/materials/{material_id}/extract-text` | Bearer access token | material_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/metrics/summary` | Bearer access token + X-Admin-Token | x-admin-token (header) | 200: SuccessResponse_Any_ |
| GET | `/api/milestones/{goal_id}` | Bearer access token | goal_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/notifications/{student_id}` | Bearer access token | student_id (path), unread_only (query) | 200: SuccessResponse_Any_ |
| GET | `/api/profile/debug/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/profile/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_ProfileResponse_ |
| GET | `/api/profile/{student_id}/memories` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/profile/{student_id}/readiness-history` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/profile/{student_id}/summary` | Bearer access token | student_id (path) | 200: SuccessResponse_ProfileSummaryResponse_ |
| GET | `/api/progress/{goal_id}` | Bearer access token | goal_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/pyq/debug/questions/{material_id}` | Bearer access token | material_id (path) | 200: SuccessResponse_ExtractedQuestionsResponse_ |
| GET | `/api/pyq/important-topics/{subject_id}` | Bearer access token | subject_id (path) | 200: SuccessResponse_list_ImportantTopic__ |
| GET | `/api/pyq/revision-plan/{subject_id}` | Bearer access token | subject_id (path) | 200: SuccessResponse_RevisionPlanResponse_ |
| GET | `/api/pyq/topics/{subject_id}` | Bearer access token | subject_id (path) | 200: SuccessResponse_TopicDashboardResponse_ |
| GET | `/api/pyq/trends/{subject_id}` | Bearer access token | subject_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/quizzes/history/{student_id}` | Bearer access token | student_id (path), skip (query), limit (query) | 200: SuccessResponse_List_QuizSession__ |
| GET | `/api/quizzes/session/{session_id}` | Bearer access token | session_id (path) | 200: SuccessResponse_QuizSessionWithQuestions_ |
| GET | `/api/rag/debug-search` | Bearer access token | query (query), subject_id (query) | 200: SuccessResponse_Any_ |
| GET | `/api/reminders/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/schedule/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/semester/{semester_id}` | Bearer access token | semester_id (path) | 200: SuccessResponse_SemesterResponse_ |
| GET | `/api/semester/{semester_id}/copilot` | Bearer access token | semester_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/semester/{semester_id}/health` | Bearer access token | semester_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/semester/{semester_id}/review` | Bearer access token | semester_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/semester/{semester_id}/risks` | Bearer access token | semester_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/students` | Bearer access token | None | 200: SuccessResponse_list_StudentResponse__ |
| GET | `/api/students/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_StudentResponse_ |
| GET | `/api/students/{student_id}/courses` | Bearer access token | student_id (path) | 200: SuccessResponse_StudentWithCourses_ |
| GET | `/api/study-plans/{plan_id}` | Bearer access token | plan_id (path) | 200: SuccessResponse_StudyPlanResponse_ |
| GET | `/api/study-plans/{plan_id}/progress` | Bearer access token | plan_id (path) | 200: SuccessResponse_PlanProgress_ |
| GET | `/api/subjects` | Bearer access token | None | 200: SuccessResponse_list_SubjectResponse__ |
| GET | `/api/subjects/{subject_id}` | Bearer access token | subject_id (path) | 200: SuccessResponse_SubjectResponse_ |
| GET | `/api/subjects/{subject_id}/materials` | Bearer access token | subject_id (path) | 200: SuccessResponse_list_StudyMaterialResponse__ |
| GET | `/api/subjects/{subject_id}/topics` | Bearer access token | subject_id (path), skip (query), limit (query) | 200: SuccessResponse_List_Topic__ |
| GET | `/api/sync-jobs/{student_id}` | Bearer access token | student_id (path) | 200: SuccessResponse_Any_ |
| GET | `/api/system/metrics` | Bearer access token | None | 200: SuccessResponse_Any_ |
| GET | `/api/topics` | Bearer access token | skip (query), limit (query) | 200: SuccessResponse_List_Topic__ |
| GET | `/api/topics/{topic_id}` | Bearer access token | topic_id (path) | 200: SuccessResponse_Topic_ |
| GET | `/health` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/health/dependencies` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/health/live` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/health/ready` | Public | None | 200: SuccessResponse_Any_ |
| GET | `/system/health` | Public | None | 200: SuccessResponse_Any_ |
| PATCH | `/api/deadlines/{deadline_id}/complete` | Bearer access token | deadline_id (path), application/json: DeadlineCompletionInput | 200: SuccessResponse_Any_ |
| PATCH | `/api/goals/{goal_id}` | Bearer access token | goal_id (path), application/json: GoalUpdateInput | 200: SuccessResponse_Any_ |
| PATCH | `/api/habits/{habit_id}` | Bearer access token | habit_id (path), application/json: HabitUpdateInput | 200: SuccessResponse_Any_ |
| PATCH | `/api/milestones/{milestone_id}/complete` | Bearer access token | milestone_id (path), completed (query) | 200: SuccessResponse_Any_ |
| PATCH | `/api/notifications/{notification_id}/read` | Bearer access token | notification_id (path) | 200: SuccessResponse_Any_ |
| PATCH | `/api/reminders/{reminder_id}` | Bearer access token | reminder_id (path), application/json: ReminderUpdate | 200: SuccessResponse_Any_ |
| PATCH | `/api/semester/{semester_id}/milestone/{milestone_id}` | Bearer access token | semester_id (path), milestone_id (path), application/json: SemesterMilestoneUpdateRequest | 200: SuccessResponse_Any_ |
| PATCH | `/api/semester/{semester_id}/status` | Bearer access token | semester_id (path), application/json: SemesterStatusUpdateRequest | 200: SuccessResponse_SemesterResponse_ |
| PATCH | `/api/study-plans/tasks/{task_id}/complete` | Bearer access token | task_id (path) | 200: SuccessResponse_StudyPlanResponse_ |
| POST | `/api/agent/academic` | Bearer access token | application/json: AcademicAgentRequest | 200: SuccessResponse_AcademicAgentResponse_ |
| POST | `/api/attendance/{student_id}` | Bearer access token | student_id (path), application/json: AttendanceInput | 200: SuccessResponse_Any_ |
| POST | `/api/auth/google` | Public | application/json: GoogleLoginRequest | 200: SuccessResponse_Any_ |
| POST | `/api/auth/logout` | Bearer access token | application/json: RefreshRequest | 200: SuccessResponse_Any_ |
| POST | `/api/auth/refresh` | Public | application/json: RefreshRequest | 200: SuccessResponse_Any_ |
| POST | `/api/calendar/{student_id}` | Bearer access token | student_id (path), application/json: CalendarEventInput | 200: SuccessResponse_Any_ |
| POST | `/api/chat` | Bearer access token | application/json: ChatRequest | 200: SuccessResponse_ChatResponse_ |
| POST | `/api/chat/sessions` | Bearer access token | application/json: CreateSessionRequest | 200: SuccessResponse_ChatSessionResponse_ |
| POST | `/api/connectors/{connector_id}/sync` | Bearer access token | connector_id (path) | 200: SuccessResponse_Any_ |
| POST | `/api/connectors/{student_id}` | Bearer access token | student_id (path), application/json: ConnectorCreateInput | 200: SuccessResponse_Any_ |
| POST | `/api/courses` | Bearer access token | application/json: CourseCreate | 200: SuccessResponse_CourseResponse_ |
| POST | `/api/deadlines/{student_id}` | Bearer access token | student_id (path), application/json: DeadlineInput | 200: SuccessResponse_Any_ |
| POST | `/api/director/academic` | Bearer access token | application/json: DirectorAcademicRequest | 200: SuccessResponse_DirectorAcademicResponse_ |
| POST | `/api/flashcards/generate` | Bearer access token | application/json: FlashcardGenerateRequest | 200: SuccessResponse_FlashcardGenerateResponse_ |
| POST | `/api/goals/{student_id}` | Bearer access token | student_id (path), application/json: GoalCreateInput | 200: SuccessResponse_Any_ |
| POST | `/api/grades/{student_id}` | Bearer access token | student_id (path), application/json: GradeInput | 200: SuccessResponse_Any_ |
| POST | `/api/habits/{habit_id}/logs` | Bearer access token | habit_id (path), application/json: HabitLogInput | 200: SuccessResponse_Any_ |
| POST | `/api/habits/{student_id}` | Bearer access token | student_id (path), application/json: HabitCreateInput | 200: SuccessResponse_Any_ |
| POST | `/api/learning/session` | Bearer access token | application/json: LearningSessionCreate | 200: SuccessResponse_LearningSessionResponse_ |
| POST | `/api/materials` | Bearer access token | application/json: StudyMaterialCreate | 200: SuccessResponse_StudyMaterialResponse_ |
| POST | `/api/materials/upload` | Bearer access token | multipart/form-data: Body__upload_material_background_api_materials_upload_post | 202: SuccessResponse_StudyMaterialResponse_ |
| POST | `/api/materials/{material_id}/embed` | Bearer access token | material_id (path) | 202: SuccessResponse_JobExecutionResponse_ |
| POST | `/api/milestones/{goal_id}` | Bearer access token | goal_id (path), application/json: MilestoneInput | 200: SuccessResponse_Any_ |
| POST | `/api/notifications/{student_id}` | Bearer access token | student_id (path), application/json: NotificationInput | 200: SuccessResponse_Any_ |
| POST | `/api/notifications/{student_id}/generate-alerts` | Bearer access token | student_id (path) | 202: SuccessResponse_JobExecutionResponse_ |
| POST | `/api/practice/start` | Bearer access token | application/json: PracticeStartRequest | 200: SuccessResponse_PracticeStartResponse_ |
| POST | `/api/practice/submit` | Bearer access token | application/json: PracticeSubmitRequest | 200: SuccessResponse_PracticeSubmitResponse_ |
| POST | `/api/progress/{goal_id}` | Bearer access token | goal_id (path), application/json: ProgressInput | 200: SuccessResponse_Any_ |
| POST | `/api/pyq/generate-practice` | Bearer access token | application/json: PracticeQuestionRequest | 200: SuccessResponse_PracticeQuestionResponse_ |
| POST | `/api/quizzes/generate` | Bearer access token | application/json: QuizGenerateRequest | 200: SuccessResponse_QuizSessionWithQuestions_ |
| POST | `/api/quizzes/submit` | Bearer access token | application/json: QuizSubmitRequest | 200: SuccessResponse_QuizSubmitResponse_ |
| POST | `/api/rag/ask` | Bearer access token | application/json: AskRequest | 200: SuccessResponse_AskResponse_ |
| POST | `/api/reminders/{student_id}` | Bearer access token | student_id (path), application/json: ReminderInput | 200: SuccessResponse_Any_ |
| POST | `/api/schedule/{student_id}/blocks` | Bearer access token | student_id (path), application/json: StudyBlockInput | 200: SuccessResponse_Any_ |
| POST | `/api/schedule/{student_id}/generate` | Bearer access token | student_id (path), application/json: ScheduleInput | 200: SuccessResponse_Any_ |
| POST | `/api/schedule/{student_id}/intelligent` | Bearer access token | student_id (path), application/json: IntelligentScheduleInput | 200: SuccessResponse_Any_ |
| POST | `/api/semester` | Bearer access token | application/json: SemesterCreateRequest | 201: SuccessResponse_SemesterResponse_ |
| POST | `/api/semester/{semester_id}/milestone` | Bearer access token | semester_id (path), application/json: SemesterMilestoneCreateRequest | 201: SuccessResponse_Any_ |
| POST | `/api/students` | Bearer access token | application/json: StudentCreate | 200: SuccessResponse_StudentResponse_ |
| POST | `/api/study-plans/generate` | Bearer access token | application/json: StudyPlanGenerateRequest | 200: SuccessResponse_StudyPlanResponse_ |
| POST | `/api/study-plans/{plan_id}/recalculate` | Bearer access token | plan_id (path) | 200: SuccessResponse_RecalculateResponse_ |
| POST | `/api/subjects` | Bearer access token | application/json: SubjectCreate | 200: SuccessResponse_SubjectResponse_ |
| POST | `/api/topics/extract/{material_id}` | Bearer access token | material_id (path), subject_id (query) | 200: SuccessResponse_List_Topic__ |
| PUT | `/api/academic-profiles/{student_id}` | Bearer access token | student_id (path), application/json: ProfileInput | 200: SuccessResponse_Any_ |
| PUT | `/api/academic-profiles/{student_id}/preferences` | Bearer access token | student_id (path), application/json: PreferenceInput | 200: SuccessResponse_Any_ |
| PUT | `/api/calendar/events/{event_id}` | Bearer access token | event_id (path), application/json: CalendarEventInput | 200: SuccessResponse_Any_ |
| PUT | `/api/connectors/{connector_id}/credentials` | Bearer access token | connector_id (path), application/json: ConnectorCredentialsInput | 200: SuccessResponse_Any_ |
| PUT | `/api/students/{student_id}` | Bearer access token | student_id (path), application/json: StudentUpdate | 200: SuccessResponse_StudentResponse_ |
