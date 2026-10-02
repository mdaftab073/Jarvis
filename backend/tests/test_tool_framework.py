import unittest

from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.tools.exceptions import ToolNotFoundError, ToolValidationError
from app.tools.registry import ToolRegistry, get_tool_registry, register_tool


class EchoInput(BaseModel):
    value: int = Field(gt=0)


@register_tool
class EchoTool(BaseTool):
    name = "echo"
    description = "Returns the validated value."
    input_model = EchoInput

    async def execute(self, payload: EchoInput) -> dict:
        return {"value": payload.value}


class ToolFrameworkTests(unittest.TestCase):
    def setUp(self):
        self.registry = ToolRegistry([EchoTool()])

    def test_sync_execution_validates_and_wraps_results(self):
        result = self.registry.execute_tool("echo", {"value": 4})
        self.assertTrue(result.success)
        self.assertEqual(result.tool, "echo")
        self.assertEqual(result.data, {"value": 4})

    def test_async_execution_and_discovery_metadata(self):
        import asyncio

        result = asyncio.run(self.registry.execute_tool_async("echo", {"value": 8}))
        self.assertEqual(result.data["value"], 8)
        metadata = self.registry.list_tools()[0]
        self.assertEqual(metadata["name"], "echo")
        self.assertIn("value", metadata["input_schema"]["properties"])

    def test_decorator_auto_registers_tool_for_default_registry(self):
        names = {item["name"] for item in get_tool_registry().list_tools()}
        self.assertIn("echo", names)
        schema = next(item["input_schema"] for item in get_tool_registry().list_tools() if item["name"] == "echo")
        self.assertNotIn("db", schema["properties"])
        self.assertNotIn("student_id", schema["properties"])

    def test_not_found_and_validation_errors_are_typed(self):
        with self.assertRaises(ToolNotFoundError):
            self.registry.execute_tool("missing", {})
        with self.assertRaises(ToolValidationError):
            self.registry.execute_tool("echo", {"value": 0})

    def test_sync_execution_rejects_running_event_loop(self):
        import asyncio

        async def call_sync():
            with self.assertRaisesRegex(Exception, "await execute_tool_async"):
                self.registry.execute_tool("echo", {"value": 1})

        asyncio.run(call_sync())


if __name__ == "__main__":
    unittest.main()