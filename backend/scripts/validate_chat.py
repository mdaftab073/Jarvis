from app.db.database import Base
from app.main import app
from app.tools.registry import get_tool_registry


REQUIRED_PATHS = {
    "/api/chat",
    "/api/chat/sessions",
    "/api/chat/sessions/{session_id}",
    "/api/chat/sessions/{session_id}/messages",
}


def main():
    required_tables = {"chat_sessions", "chat_messages"}
    missing_tables = required_tables - Base.metadata.tables.keys()
    if missing_tables:
        raise SystemExit(f"Chat tables are not registered: {', '.join(sorted(missing_tables))}")
    missing_paths = REQUIRED_PATHS - app.openapi()["paths"].keys()
    if missing_paths:
        raise SystemExit(f"Chat routes are not registered: {', '.join(sorted(missing_paths))}")
    tool_names = {tool["name"] for tool in get_tool_registry().list_tools()}
    if not tool_names:
        raise SystemExit("Director tool registry is empty")
    print(f"Chat validation passed: {len(required_tables)} tables, {len(REQUIRED_PATHS)} paths, {len(tool_names)} tools")


if __name__ == "__main__":
    main()