from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from app.tools.exceptions import ToolOwnershipError, ToolValidationError
from app.tools.schemas import ToolRequest


class BaseTool(ABC):
    name: ClassVar[str] = "base"
    description: ClassVar[str] = ""
    input_model: ClassVar[type[BaseModel]] = ToolRequest

    @abstractmethod
    async def execute(self, payload: ToolRequest) -> object:
        raise NotImplementedError

    @staticmethod
    def require_student(payload: ToolRequest):
        db = getattr(payload, "db", None)
        student_id = getattr(payload, "student_id", None)
        if db is None or student_id is None:
            raise ToolValidationError("", "A database session and student_id are required")
        principal_id = getattr(payload, "principal_id", None)
        if principal_id is not None and principal_id != student_id:
            raise ToolOwnershipError()
        return db, student_id