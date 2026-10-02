from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class JobDefinition:
    name: str
    handler: Callable[[dict[str, Any]], Any]
    description: str = ""