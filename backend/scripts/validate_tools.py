from app.tools.registry import get_tool_registry


REQUIRED_TOOLS = {
    "academic_profile",
    "grades",
    "attendance_summary",
    "rag_search",
    "study_materials",
    "study_plan",
    "topic_mastery",
    "flashcards",
    "quizzes",
    "goals",
    "habits",
    "productivity_analytics",
    "calendar_events",
    "study_schedule",
    "deadlines",
    "reminders",
    "mis_profile",
    "mis_attendance",
    "mis_results",
    "mis_sync_profile",
    "mis_get_attendance",
    "mis_get_results",
    "mis_get_timetable",
}


def main():
    tools = get_tool_registry().list_tools()
    names = {tool["name"] for tool in tools}
    missing = REQUIRED_TOOLS - names
    if missing:
        raise SystemExit(f"Missing required tools: {', '.join(sorted(missing))}")
    if len(names) != len(tools):
        raise SystemExit("Tool registry contains duplicate names")
    print(f"Tool registry validated: {len(tools)} tools discovered")


if __name__ == "__main__":
    main()