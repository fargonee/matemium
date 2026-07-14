"""Type-safe agent bridge emulating the PydanticAI design (zero-dependency fallback).

Allows Matemium to leverage the industry-standard PydanticAI framework when
available, while providing a lightweight, robust, and standalone Pydantic-based
validation engine as a zero-dependency fallback for the standalone sidecar.
"""

from __future__ import annotations

import json
from typing import Any, Generic, Type, TypeVar

from pydantic import BaseModel

from .local_runner import LocalInferenceRunner

# Define generic result type for type safety
T = TypeVar("T", bound=BaseModel)

class RunResult(Generic[T]):
    """Container matching the PydanticAI RunResult model structure."""

    def __init__(self, data: T, raw_content: str):
        self.data = data
        self.raw_content = raw_content


class PydanticAIAgent(Generic[T]):
    """Type-safe agent wrapper mimicking pydantic_ai.Agent.

    Delegates to the real pydantic_ai library if installed; otherwise, executes
    structured JSON-based generation locally with Pydantic schema validation.
    """

    def __init__(
        self,
        model_name: str,
        result_type: Type[T],
        system_prompt: str,
        tools: list[Any] | None = None,
    ):
        self.model_name = model_name
        self.result_type = result_type
        self.system_prompt = system_prompt
        self.tools = tools or []
        self._real_agent: Any = None

        # Attempt to load from real pydantic_ai if present
        try:
            from pydantic_ai import Agent
            # Translate local model names if needed
            self._real_agent = Agent(
                model_name,
                result_type=result_type,
                system_prompt=system_prompt,
            )
            # Register tools to real agent
            for tool in self.tools:
                self._real_agent.tool(tool)
            print("[PydanticAI Bridge] Successfully instantiated real PydanticAI Agent.")
        except ImportError:
            # Fallback to local Pydantic-based validation engine
            pass

    def run_sync(self, user_prompt: str) -> RunResult[T]:
        """Run the agent synchronously with type-safe structured output validation."""
        # 1. Real PydanticAI execution
        if self._real_agent is not None:
            res = self._real_agent.run_sync(user_prompt)
            return RunResult(data=res.data, raw_content=str(res.data))

        # 2. Standalone fallback validation execution
        runner = LocalInferenceRunner()

        # Build schema explanation to prompt the model to output conformant JSON
        schema_dict = self.result_type.model_json_schema() if hasattr(self.result_type, "model_json_schema") else self.result_type.schema()
        schema_str = json.dumps(schema_dict, indent=2)

        structured_sys_prompt = f"""{self.system_prompt}

You MUST return your response as a single, valid JSON object matching this exact Pydantic schema:
{schema_str}

Ensure your response is valid JSON. Do not include markdown wrappers (no ```json code blocks), only the raw JSON string."""

        from .grammars import SIMPLE_JSON_GBNF
        raw_output = runner.generate(structured_sys_prompt, user_prompt, grammar=SIMPLE_JSON_GBNF)

        # Self-healing parser for json blocks if the model wrapped it in markdown
        cleaned_output = raw_output.strip()
        if cleaned_output.startswith("```"):
            lines = cleaned_output.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned_output = "\n".join(lines).strip()

        try:
            parsed_json = json.loads(cleaned_output)
            # Support both Pydantic v1 (parse_obj) and v2 (model_validate)
            if hasattr(self.result_type, "model_validate"):
                validated_data = self.result_type.model_validate(parsed_json)
            else:
                validated_data = self.result_type.parse_obj(parsed_json)
            return RunResult(data=validated_data, raw_content=raw_output)
        except Exception as e:
            # Fallback parsing/healing or raising validation error
            raise ValueError(
                f"[PydanticAI Fallback Validation Failed] Model output did not match "
                f"the schema for {self.result_type.__name__}: {e}. Raw content: {raw_output}"
            )
