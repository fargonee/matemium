from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Type
from pydantic import BaseModel


class BaseTool(ABC):
    """Abstract base class for all Matemium ReAct agent tools."""

    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool logic and return the result as a string observation."""
        pass

    def get_schema(self) -> dict[str, Any]:
        """Return the JSON schema for this tool's input arguments."""
        schema_dict = (
            self.args_schema.model_json_schema()
            if hasattr(self.args_schema, "model_json_schema")
            else self.args_schema.schema()
        )
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema_dict,
        }
