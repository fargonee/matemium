from __future__ import annotations

import json
import re
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from .tools import (
    BaseTool,
    FSApplyDiffPatchTool,
    FSGrepSearchTool,
    FSListDirectoryTool,
    FSReadSliceTool,
    FSRunCompilerTool,
)


def parse_llm_response(text: str) -> Tuple[Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Parse the LLM response to extract:
    - Thought text (within <thought>...</thought> tags)
    - Tool name (from <tool_call name="...">)
    - Tool arguments (JSON block within <tool_call>...</tool_call> tags)
    """
    thought = None
    tool_name = None
    tool_args = None

    # Extract thought
    thought_match = re.search(r"<(?:thought|reasoning)>([\s\S]*?)</(?:thought|reasoning)>", text, re.I)
    if thought_match:
        thought = thought_match.group(1).strip()

    # Extract tool_call
    tool_call_match = re.search(r'<tool_call\s+name=["\']([^"\']+)["\']\s*>([\s\S]*?)</tool_call>', text, re.I)
    if tool_call_match:
        tool_name = tool_call_match.group(1).strip()
        args_text = tool_call_match.group(2).strip()
        try:
            # Self-healing: if arguments are wrapped in ```json ... ```, strip it
            if args_text.startswith("```"):
                lines = args_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                args_text = "\n".join(lines).strip()
            tool_args = json.loads(args_text)
        except Exception as e:
            tool_args = {"error": f"JSON parsing failed: {e}", "raw": args_text}

    return thought, tool_name, tool_args


class ReActAgentRunner:
    """Manages the conversation state and executes the autonomous ReAct tool loop."""

    def __init__(self, tools: List[BaseTool] | None = None, max_turns: int = 10):
        if tools is None:
            self.tools = [
                FSReadSliceTool(),
                FSGrepSearchTool(),
                FSListDirectoryTool(),
                FSApplyDiffPatchTool(),
                FSRunCompilerTool(),
            ]
        else:
            self.tools = tools
        self.tool_by_name = {t.name: t for t in self.tools}
        self.max_turns = max_turns

    def run_loop(
        self,
        user_prompt: str,
        generate_fn: Callable[[List[Dict[str, str]]], str],
        system_prompt: Optional[str] = None,
        project_dir: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, str]]:
        """
        Run the ReAct autonomous tool-calling loop.
        - user_prompt: the top-level goal.
        - generate_fn: standard completion handler.
        - system_prompt: custom override.
        - project_dir: active workspace passed to tools.
        - callback: live progress hook.
        """
        messages: List[Dict[str, str]] = []

        sys_prompt = system_prompt or self.get_default_system_prompt()
        messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_prompt})

        turn = 0
        while turn < self.max_turns:
            turn += 1

            if callback:
                callback({"type": "status", "status": f"Thinking (Turn {turn}/{self.max_turns})..."})

            # Query the model with full conversation history
            response_text = generate_fn(messages)

            thought, tool_name, tool_args = parse_llm_response(response_text)

            messages.append({"role": "assistant", "content": response_text})

            if callback:
                if thought:
                    callback({"type": "thought", "content": thought})
                if tool_name:
                    callback({"type": "tool_call", "name": tool_name, "args": tool_args})

            if tool_name:
                if tool_name in self.tool_by_name:
                    tool = self.tool_by_name[tool_name]
                    
                    actual_args = dict(tool_args or {})
                    if "project_dir" not in actual_args and project_dir:
                        actual_args["project_dir"] = project_dir

                    if callback:
                        callback({"type": "status", "status": f"Executing tool: {tool_name}"})

                    try:
                        observation = tool.execute(**actual_args)
                    except Exception as e:
                        observation = f"Error executing tool: {e}"
                else:
                    observation = f"Error: Tool '{tool_name}' is not recognized. Available tools: {', '.join(self.tool_by_name.keys())}"

                tool_msg = f"<tool_output>\n{observation}\n</tool_output>"
                messages.append({"role": "user", "content": tool_msg})

                if callback:
                    callback({"type": "tool_output", "name": tool_name, "output": observation})
            else:
                if callback:
                    callback({"type": "status", "status": "Task complete."})
                break
        else:
            if callback:
                callback({"type": "status", "status": f"Reached maximum allowed turns ({self.max_turns}). halting."})

        return messages

    async def run_loop_async(
        self,
        user_prompt: str,
        generate_fn: Callable[[List[Dict[str, str]]], Coroutine[Any, Any, str]],
        system_prompt: Optional[str] = None,
        project_dir: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None] | None]] = None,
    ) -> List[Dict[str, str]]:
        """
        Run the ReAct autonomous tool-calling loop asynchronously.
        - user_prompt: the top-level goal.
        - generate_fn: async completion handler.
        - system_prompt: custom override.
        - project_dir: active workspace passed to tools.
        - callback: async/sync live progress hook.
        """
        messages: List[Dict[str, str]] = []

        sys_prompt = system_prompt or self.get_default_system_prompt()
        messages.append({"role": "system", "content": sys_prompt})
        messages.append({"role": "user", "content": user_prompt})

        turn = 0
        while turn < self.max_turns:
            turn += 1

            if callback:
                res = callback({"type": "status", "status": f"Thinking (Turn {turn}/{self.max_turns})..."})
                if hasattr(res, "__await__"):
                    await res

            response_text = await generate_fn(messages)

            thought, tool_name, tool_args = parse_llm_response(response_text)

            messages.append({"role": "assistant", "content": response_text})

            if callback:
                if thought:
                    res = callback({"type": "thought", "content": thought})
                    if hasattr(res, "__await__"):
                        await res
                if tool_name:
                    res = callback({"type": "tool_call", "name": tool_name, "args": tool_args})
                    if hasattr(res, "__await__"):
                        await res

            if tool_name:
                if tool_name in self.tool_by_name:
                    tool = self.tool_by_name[tool_name]
                    
                    actual_args = dict(tool_args or {})
                    if "project_dir" not in actual_args and project_dir:
                        actual_args["project_dir"] = project_dir

                    if callback:
                        res = callback({"type": "status", "status": f"Executing tool: {tool_name}"})
                        if hasattr(res, "__await__"):
                            await res

                    try:
                        observation = tool.execute(**actual_args)
                    except Exception as e:
                        observation = f"Error executing tool: {e}"
                else:
                    observation = f"Error: Tool '{tool_name}' is not recognized. Available tools: {', '.join(self.tool_by_name.keys())}"

                tool_msg = f"<tool_output>\n{observation}\n</tool_output>"
                messages.append({"role": "user", "content": tool_msg})

                if callback:
                    res = callback({"type": "tool_output", "name": tool_name, "output": observation})
                    if hasattr(res, "__await__"):
                        await res
            else:
                if callback:
                    res = callback({"type": "status", "status": "Task complete."})
                    if hasattr(res, "__await__"):
                        await res
                break
        else:
            if callback:
                res = callback({"type": "status", "status": f"Reached maximum allowed turns ({self.max_turns}). halting."})
                if hasattr(res, "__await__"):
                    await res

        return messages

    def get_default_system_prompt(self) -> str:
        """Return the default system prompt describing available tools."""
        tool_desc = []
        for t in self.tools:
            schema = t.get_schema()
            tool_desc.append(
                f"- Name: {t.name}\n"
                f"  Description: {t.description}\n"
                f"  Arguments Schema: {json.dumps(schema['parameters'], indent=2)}"
            )
        tools_str = "\n\n".join(tool_desc)

        return f"""You are an autonomous AI engineering agent for the Matemium platform.
You operate in a continuous loop of Thought, Action, and Observation.

### Rules of Engagement:
1. You must search and read files before making edits. Do not assume file layout or symbol names.
2. After making any change, you MUST run the compiler tool to verify it. Do not announce success until the compiler passes.
3. Keep your SEARCH/REPLACE blocks as small and precise as possible.

### Available Tools:
{tools_str}

### Response Format:
For every step, you MUST respond in the following format:
<thought>
[Explain your reasoning, what you have observed, and what you need to do next.]
</thought>
<tool_call name="[tool_name]">
{{
  "[arg_name]": "[arg_value]"
}}
</tool_call>

If you are completely done and have validated your changes with the compiler, explain your final result without a <tool_call> tag.
"""
