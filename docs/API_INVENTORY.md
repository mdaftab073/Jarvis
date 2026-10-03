# Backend API Inventory

Generated from the registered FastAPI OpenAPI schema. Regenerate this inventory after route or schema changes.

- Registered paths: 133
- Registered operations: 159
- Authentication: all `/api/*` routes require a valid Bearer access token in production except public health routes and Google/refresh endpoints listed below. This enforcement is middleware-based and is not represented as OpenAPI `security` metadata.
- Non-`/api/*` root and health endpoints are public. `GET /api/metrics/summary` additionally requires `X-Admin-Token`.
- `Not declared` means the handler relies on FastAPI generic response handling rather than a declared Pydantic response model; consult the implementation for exact payloads.

| Method | Route | Authentication | Request parameters/body schema | Success response schema |
|---|---|---|---|---|
| GET | / | Public | None declared | 200: Not declared |
| GET | /api/academic-profiles/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| PUT | /api/academic-profiles/{student_id} | Bearer access token | student_id (path), application/json: ProfileInput | 200: Not declared |
| GET | /api/academic-profiles/{student_id}/preferences | Bearer access token | student_id (path) | 200: Not declared |
| PUT | /api/academic-profiles/{student_id}/preferences | Bearer access token | student_id (path), application/json: PreferenceInput | 200: Not declared |
| GET | /api/academic-profiles/{student_id}/summary | Bearer access token | student_id (path) | 200: Not declared |
| POST | /api/agent/academic | Bearer access token | application/json: AcademicAgentRequest | 200: AcademicAgentResponse |
| GET | /api/agent/debug-plan | Bearer access token | student_id (query), goal (query) | 200: AcademicAgentDebugResponse |
| GET | /api/analytics/dashboard/{student_id} | Bearer access token | student_id (path) | 200: AnalyticsDashboard |
| GET | /api/analytics/readiness/{student_id}/{subject_id} | Bearer access token | student_id (path), subject_id (path) | 200: ReadinessResponse |
| GET | /api/analytics/recommendations/{student_id}/{subject_id} | Bearer access token | student_id (path), subject_id (path) | 200: Not declared |
| GET | /api/analytics/strong-topics/{student_id}/{subject_id} | Bearer access token | student_id (path), subject_id (path) | 200: Not declared |
| GET | /api/analytics/weak-topics/{student_id}/{subject_id} | Bearer access token | student_id (path), subject_id (path) | 200: Not declared |
| GET | /api/attendance/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| POST | /api/attendance/{student_id} | Bearer access token | student_id (path), application/json: AttendanceInput | 200: Not declared |
| POST | /api/auth/google | Public | application/json: GoogleLoginRequest | 200: Not declared |
| POST | /api/auth/logout | Bearer access token | application/json: RefreshRequest | 200: Not declared |
| GET | /api/auth/me | Bearer access token | None declared | 200: Not declared |
| POST | /api/auth/refresh | Public | application/json: RefreshRequest | 200: Not declared |
| DELETE | /api/calendar/events/{event_id} | Bearer access token | event_id (path) | 200: Not declared |
| PUT | /api/calendar/events/{event_id} | Bearer access token | event_id (path), application/json: CalendarEventInput | 200: Not declared |
| GET | /api/calendar/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| POST | /api/calendar/{student_id} | Bearer access token | student_id (path), application/json: CalendarEventInput | 200: Not declared |
| GET | /api/calendar/{student_id}/today | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/calendar/{student_id}/tomorrow | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/calendar/{student_id}/week | Bearer access token | student_id (path), start_date (query) | 200: Not declared |
| POST | /api/chat | Bearer access token | application/json: ChatRequest | 200: ChatResponse |
| GET | /api/chat/sessions | Bearer access token | student_id (query), limit (query) | 200: array[ChatSessionResponse] |
| POST | /api/chat/sessions | Bearer access token | application/json: CreateSessionRequest | 200: ChatSessionResponse |
| DELETE | /api/chat/sessions/{session_id} | Bearer access token | session_id (path) | 200: Not declared |
| GET | /api/chat/sessions/{session_id} | Bearer access token | session_id (path) | 200: ChatSessionResponse |
| GET | /api/chat/sessions/{session_id}/messages | Bearer access token | session_id (path), limit (query), offset (query) | 200: array[ChatMessageResponse] |
| PUT | /api/connectors/{connector_id}/credentials | Bearer access token | connector_id (path), application/json: ConnectorCredentialsInput | 200: Not declared |
| GET | /api/connectors/{connector_id}/history | Bearer access token | connector_id (path) | 200: Not declared |
| POST | /api/connectors/{connector_id}/sync | Bearer access token | connector_id (path) | 200: Not declared |
| GET | /api/connectors/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| POST | /api/connectors/{student_id} | Bearer access token | student_id (path), application/json: ConnectorCreateInput | 200: Not declared |
| GET | /api/courses | Bearer access token | None declared | 200: array[CourseResponse] |
| POST | /api/courses | Bearer access token | application/json: CourseCreate | 200: CourseResponse |
| GET | /api/courses/{course_id} | Bearer access token | course_id (path) | 200: CourseResponse |
| GET | /api/courses/{course_id}/subjects | Bearer access token | course_id (path) | 200: CourseWithSubjects |
| GET | /api/dashboard/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/db-health | Bearer access token | None declared | 200: Not declared |
| PATCH | /api/deadlines/{deadline_id}/complete | Bearer access token | deadline_id (path), application/json: DeadlineCompletionInput | 200: Not declared |
| GET | /api/deadlines/{student_id} | Bearer access token | student_id (path), include_completed (query) | 200: Not declared |
| POST | /api/deadlines/{student_id} | Bearer access token | student_id (path), application/json: DeadlineInput | 200: Not declared |
| GET | /api/deadlines/{student_id}/overdue | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/deadlines/{student_id}/upcoming | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/debug/chroma | Bearer access token | None declared | 200: Not declared |
| GET | /api/debug/search | Bearer access token | query (query), subject_id (query) | 200: Not declared |
| POST | /api/director/academic | Bearer access token | application/json: DirectorAcademicRequest | 200: DirectorAcademicResponse |
| GET | /api/director/debug-plan | Bearer access token | student_id (query), goal (query), subject_id (query) | 200: DirectorDebugResponse |
| GET | /api/flashcards/decks | Bearer access token | subject_id (query), skip (query), limit (query) | 200: array[FlashcardDeck] |
| GET | /api/flashcards/decks/{deck_id} | Bearer access token | deck_id (path) | 200: FlashcardDeck |
| POST | /api/flashcards/generate | Bearer access token | application/json: FlashcardGenerateRequest | 200: FlashcardGenerateResponse |
| GET | /api/flashcards/topic/{topic_id} | Bearer access token | topic_id (path), skip (query), limit (query) | 200: array[Flashcard] |
| DELETE | /api/goals/{goal_id} | Bearer access token | goal_id (path) | 200: Not declared |
| PATCH | /api/goals/{goal_id} | Bearer access token | goal_id (path), application/json: GoalUpdateInput | 200: Not declared |
| GET | /api/goals/{student_id} | Bearer access token | student_id (path), include_completed (query) | 200: Not declared |
| POST | /api/goals/{student_id} | Bearer access token | student_id (path), application/json: GoalCreateInput | 200: Not declared |
| GET | /api/grades/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| POST | /api/grades/{student_id} | Bearer access token | student_id (path), application/json: GradeInput | 200: Not declared |
| GET | /api/grades/{student_id}/analytics | Bearer access token | student_id (path) | 200: Not declared |
| DELETE | /api/habits/{habit_id} | Bearer access token | habit_id (path) | 200: Not declared |
| PATCH | /api/habits/{habit_id} | Bearer access token | habit_id (path), application/json: HabitUpdateInput | 200: Not declared |
| GET | /api/habits/{habit_id}/logs | Bearer access token | habit_id (path), start (query), end (query) | 200: Not declared |
| POST | /api/habits/{habit_id}/logs | Bearer access token | habit_id (path), application/json: HabitLogInput | 200: Not declared |
| GET | /api/habits/{student_id} | Bearer access token | student_id (path), active_only (query) | 200: Not declared |
| POST | /api/habits/{student_id} | Bearer access token | student_id (path), application/json: HabitCreateInput | 200: Not declared |
| GET | /api/health | Public | None declared | 200: Not declared |
| GET | /api/health/dependencies | Public | None declared | 200: Not declared |
| GET | /api/health/live | Public | None declared | 200: Not declared |
| GET | /api/health/ready | Public | None declared | 200: Not declared |
| GET | /api/jobs/{job_id} | Bearer access token | job_id (path), student_id (query) | 200: JobExecutionResponse |
| GET | /api/learning/history/{student_id} | Bearer access token | student_id (path), skip (query), limit (query) | 200: array[LearningSessionResponse] |
| GET | /api/learning/insights/{student_id} | Bearer access token | student_id (path) | 200: LearningInsightsResponse |
| POST | /api/learning/session | Bearer access token | application/json: LearningSessionCreate | 200: LearningSessionResponse |
| GET | /api/mastery/student/{student_id} | Bearer access token | student_id (path), skip (query), limit (query) | 200: array[MasteryWithTopic] |
| GET | /api/mastery/subject/{subject_id} | Bearer access token | subject_id (path), student_id (query) | 200: array[MasteryWithTopic] |
| GET | /api/mastery/weak/{student_id} | Bearer access token | student_id (path), threshold (query), limit (query) | 200: array[MasteryWithTopic] |
| GET | /api/materials | Bearer access token | student_id (query) | 200: array[StudyMaterialResponse] |
| POST | /api/materials | Bearer access token | application/json: StudyMaterialCreate | 200: StudyMaterialResponse |
| POST | /api/materials/upload | Bearer access token | multipart/form-data: Body__upload_material_background_api_materials_upload_post | 202: StudyMaterialResponse |
| GET | /api/materials/{material_id} | Bearer access token | material_id (path) | 200: StudyMaterialResponse |
| GET | /api/materials/{material_id}/chunks | Bearer access token | material_id (path) | 200: Not declared |
| POST | /api/materials/{material_id}/embed | Bearer access token | material_id (path) | 202: JobExecutionResponse |
| GET | /api/materials/{material_id}/extract-text | Bearer access token | material_id (path) | 200: Not declared |
| GET | /api/metrics/summary | Bearer access token + X-Admin-Token | x-admin-token (header) | 200: Not declared |
| GET | /api/milestones/{goal_id} | Bearer access token | goal_id (path) | 200: Not declared |
| POST | /api/milestones/{goal_id} | Bearer access token | goal_id (path), application/json: MilestoneInput | 200: Not declared |
| PATCH | /api/milestones/{milestone_id}/complete | Bearer access token | milestone_id (path), completed (query) | 200: Not declared |
| PATCH | /api/notifications/{notification_id}/read | Bearer access token | notification_id (path) | 200: Not declared |
| GET | /api/notifications/{student_id} | Bearer access token | student_id (path), unread_only (query) | 200: Not declared |
| POST | /api/notifications/{student_id} | Bearer access token | student_id (path), application/json: NotificationInput | 200: Not declared |
| POST | /api/notifications/{student_id}/generate-alerts | Bearer access token | student_id (path) | 202: JobExecutionResponse |
| POST | /api/practice/start | Bearer access token | application/json: PracticeStartRequest | 200: PracticeStartResponse |
| POST | /api/practice/submit | Bearer access token | application/json: PracticeSubmitRequest | 200: PracticeSubmitResponse |
| GET | /api/profile/debug/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/profile/{student_id} | Bearer access token | student_id (path) | 200: ProfileResponse |
| GET | /api/profile/{student_id}/memories | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/profile/{student_id}/readiness-history | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/profile/{student_id}/summary | Bearer access token | student_id (path) | 200: ProfileSummaryResponse |
| GET | /api/progress/{goal_id} | Bearer access token | goal_id (path) | 200: Not declared |
| POST | /api/progress/{goal_id} | Bearer access token | goal_id (path), application/json: ProgressInput | 200: Not declared |
| GET | /api/pyq/debug/questions/{material_id} | Bearer access token | material_id (path) | 200: ExtractedQuestionsResponse |
| POST | /api/pyq/generate-practice | Bearer access token | application/json: PracticeQuestionRequest | 200: PracticeQuestionResponse |
| GET | /api/pyq/important-topics/{subject_id} | Bearer access token | subject_id (path) | 200: array[ImportantTopic] |
| GET | /api/pyq/revision-plan/{subject_id} | Bearer access token | subject_id (path) | 200: RevisionPlanResponse |
| GET | /api/pyq/topics/{subject_id} | Bearer access token | subject_id (path) | 200: TopicDashboardResponse |
| GET | /api/pyq/trends/{subject_id} | Bearer access token | subject_id (path) | 200: Not declared |
| POST | /api/quizzes/generate | Bearer access token | application/json: QuizGenerateRequest | 200: QuizSessionWithQuestions |
| GET | /api/quizzes/history/{student_id} | Bearer access token | student_id (path), skip (query), limit (query) | 200: array[QuizSession] |
| GET | /api/quizzes/session/{session_id} | Bearer access token | session_id (path) | 200: QuizSessionWithQuestions |
| POST | /api/quizzes/submit | Bearer access token | application/json: QuizSubmitRequest | 200: QuizSubmitResponse |
| POST | /api/rag/ask | Bearer access token | application/json: AskRequest | 200: AskResponse |
| GET | /api/rag/debug-search | Bearer access token | query (query), subject_id (query) | 200: Not declared |
| DELETE | /api/reminders/{reminder_id} | Bearer access token | reminder_id (path) | 200: Not declared |
| PATCH | /api/reminders/{reminder_id} | Bearer access token | reminder_id (path), application/json: ReminderUpdate | 200: Not declared |
| GET | /api/reminders/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| POST | /api/reminders/{student_id} | Bearer access token | student_id (path), application/json: ReminderInput | 200: Not declared |
| GET | /api/schedule/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| POST | /api/schedule/{student_id}/blocks | Bearer access token | student_id (path), application/json: StudyBlockInput | 200: Not declared |
| POST | /api/schedule/{student_id}/generate | Bearer access token | student_id (path), application/json: ScheduleInput | 200: Not declared |
| POST | /api/schedule/{student_id}/intelligent | Bearer access token | student_id (path), application/json: IntelligentScheduleInput | 200: Not declared |
| POST | /api/semester | Bearer access token | application/json: SemesterCreateRequest | 201: SemesterResponse |
| GET | /api/semester/{semester_id} | Bearer access token | semester_id (path) | 200: SemesterResponse |
| GET | /api/semester/{semester_id}/copilot | Bearer access token | semester_id (path) | 200: Not declared |
| GET | /api/semester/{semester_id}/health | Bearer access token | semester_id (path) | 200: Not declared |
| POST | /api/semester/{semester_id}/milestone | Bearer access token | semester_id (path), application/json: SemesterMilestoneCreateRequest | 201: Not declared |
| PATCH | /api/semester/{semester_id}/milestone/{milestone_id} | Bearer access token | semester_id (path), milestone_id (path), application/json: SemesterMilestoneUpdateRequest | 200: Not declared |
| GET | /api/semester/{semester_id}/review | Bearer access token | semester_id (path) | 200: Not declared |
| GET | /api/semester/{semester_id}/risks | Bearer access token | semester_id (path) | 200: Not declared |
| PATCH | /api/semester/{semester_id}/status | Bearer access token | semester_id (path), application/json: SemesterStatusUpdateRequest | 200: SemesterResponse |
| GET | /api/students | Bearer access token | None declared | 200: array[StudentResponse] |
| POST | /api/students | Bearer access token | application/json: StudentCreate | 200: StudentResponse |
| DELETE | /api/students/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/students/{student_id} | Bearer access token | student_id (path) | 200: StudentResponse |
| PUT | /api/students/{student_id} | Bearer access token | student_id (path), application/json: StudentUpdate | 200: StudentResponse |
| GET | /api/students/{student_id}/courses | Bearer access token | student_id (path) | 200: StudentWithCourses |
| POST | /api/study-plans/generate | Bearer access token | application/json: StudyPlanGenerateRequest | 200: StudyPlanResponse |
| PATCH | /api/study-plans/tasks/{task_id}/complete | Bearer access token | task_id (path) | 200: StudyPlanResponse |
| GET | /api/study-plans/{plan_id} | Bearer access token | plan_id (path) | 200: StudyPlanResponse |
| GET | /api/study-plans/{plan_id}/progress | Bearer access token | plan_id (path) | 200: PlanProgress |
| POST | /api/study-plans/{plan_id}/recalculate | Bearer access token | plan_id (path) | 200: RecalculateResponse |
| GET | /api/subjects | Bearer access token | None declared | 200: array[SubjectResponse] |
| POST | /api/subjects | Bearer access token | application/json: SubjectCreate | 200: SubjectResponse |
| GET | /api/subjects/{subject_id} | Bearer access token | subject_id (path) | 200: SubjectResponse |
| GET | /api/subjects/{subject_id}/materials | Bearer access token | subject_id (path) | 200: array[StudyMaterialResponse] |
| GET | /api/subjects/{subject_id}/topics | Bearer access token | subject_id (path), skip (query), limit (query) | 200: array[Topic] |
| GET | /api/sync-jobs/{student_id} | Bearer access token | student_id (path) | 200: Not declared |
| GET | /api/system/metrics | Bearer access token | None declared | 200: Not declared |
| GET | /api/topics | Bearer access token | skip (query), limit (query) | 200: array[Topic] |
| POST | /api/topics/extract/{material_id} | Bearer access token | material_id (path), subject_id (query) | 200: array[Topic] |
| GET | /api/topics/{topic_id} | Bearer access token | topic_id (path) | 200: Topic |
| GET | /health | Public | None declared | 200: Not declared |
| GET | /health/dependencies | Public | None declared | 200: Not declared |
| GET | /health/live | Public | None declared | 200: Not declared |
| GET | /health/ready | Public | None declared | 200: Not declared |
| GET | /system/health | Public | None declared | 200: Not declared |
