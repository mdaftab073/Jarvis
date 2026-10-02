class ToolError(Exception):
    code = "tool_error"
    safe_message = "The requested tool could not be completed."


class ToolNotFoundError(ToolError):
    code = "tool_not_found"
    safe_message = "The requested tool is not available."

    def __init__(self, tool_name: str):
        super().__init__(tool_name)
        self.tool_name = tool_name


class ToolValidationError(ToolError):
    code = "tool_validation_error"
    safe_message = "The tool request is invalid."

    def __init__(self, tool_name: str, message: str):
        super().__init__(message)
        self.tool_name = tool_name


class ToolExecutionError(ToolError):
    code = "tool_execution_error"
    safe_message = "The tool failed while processing the request."

    def __init__(self, tool_name: str, message: str | None = None):
        super().__init__(message or self.safe_message)
        self.tool_name = tool_name


class ToolOwnershipError(ToolError):
    code = "tool_ownership_error"
    safe_message = "The requested record is outside the current student scope."

    def __init__(self, message: str | None = None):
        super().__init__(message or self.safe_message)