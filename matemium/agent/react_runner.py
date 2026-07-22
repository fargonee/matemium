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
    tool_call_match = re.search(
        r'<tool_call\s+name=["\']([^"\']+)["\']\s*>([\s\S]*?)(?:</tool_call>|$)',
        text,
        re.I,
    )
    if tool_call_match:
        tool_name = tool_call_match.group(1).strip()
        args_text = tool_call_match.group(2).strip().removesuffix("```").strip()
        try:
            # Self-healing: if arguments are wrapped in ```json ... ```, strip it
            if args_text.startswith("```"):
                lines = args_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                args_text = "\n".join(lines).strip()
            # raw_decode accepts a valid leading JSON object while ignoring a
            # model's accidental prose or markdown after it.
            tool_args, _ = json.JSONDecoder().raw_decode(args_text)
        except Exception as e:
            tool_args = {"error": f"JSON parsing failed: {e}", "raw": args_text}

    return thought, tool_name, tool_args


class ReActAgentRunner:
    """Manages the conversation state and executes the autonomous ReAct tool loop."""

    def __init__(
        self,
        tools: List[BaseTool] | None = None,
        max_turns: int = 10,
        deliberation_turns: int = 1,
    ):
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
        self.deliberation_turns = max(0, deliberation_turns)

    def run_loop(
        self,
        user_prompt: str,
        generate_fn: Callable[[List[Dict[str, str]]], str],
        system_prompt: Optional[str] = None,
        project_dir: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        preflight_workspace: bool = False,
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
        for message in conversation_history or []:
            if message.get("role") in {"user", "assistant"} and message.get("content"):
                messages.append({"role": message["role"], "content": message["content"]})
        if not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != user_prompt:
            messages.append({"role": "user", "content": user_prompt})
        preflight_pending = bool(
            preflight_workspace and project_dir and "list_directory" in self.tool_by_name
        )

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

            if turn <= self.deliberation_turns:
                feedback = (
                    "<policy_feedback>\n"
                    "Planning phase complete. No tool action was executed on this turn. "
                    "Now use the plan to choose the single most useful next action, or answer "
                    "directly if no action is necessary. Do not call a tool merely because one "
                    "is available.\n"
                    "</policy_feedback>"
                )
                messages.append({"role": "user", "content": feedback})
                if callback:
                    callback({"type": "status", "status": "Plan formed; selecting the next action."})

                # Legacy workspace hydration remains opt-in, but it cannot run
                # before the model has formed an initial plan.
                if preflight_pending:
                    if callback:
                        callback({
                            "type": "tool_call",
                            "name": "list_directory",
                            "args": {"dir_path": "."},
                        })
                    observation = self.tool_by_name["list_directory"].execute(
                        dir_path=".", project_dir=project_dir
                    )
                    messages.append({"role": "user", "content": f"<tool_output>\n{observation}\n</tool_output>"})
                    if callback:
                        callback({
                            "type": "tool_output",
                            "name": "list_directory",
                            "output": observation,
                        })
                    if "read_file_slice" in self.tool_by_name:
                        read_args = {"file_path": "scenes.py", "start_line": 1, "end_line": 240}
                        if callback:
                            callback({
                                "type": "tool_call",
                                "name": "read_file_slice",
                                "args": read_args,
                            })
                        read_observation = self.tool_by_name["read_file_slice"].execute(
                            **read_args, project_dir=project_dir
                        )
                        messages.append({
                            "role": "user",
                            "content": f"<tool_output>\n{read_observation}\n</tool_output>",
                        })
                        if callback:
                            callback({
                                "type": "tool_output",
                                "name": "read_file_slice",
                                "output": read_observation,
                            })
                    preflight_pending = False
                continue

            if callback and tool_name:
                callback({"type": "tool_call", "name": tool_name, "args": tool_args})

            if tool_name:
                if tool_name in self.tool_by_name:
                    tool = self.tool_by_name[tool_name]
                    
                    actual_args = dict(tool_args or {})
                    if project_dir:
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
            elif "<tool_call" in response_text or "tool_call" in response_text:
                observation = "Error: The model emitted malformed tool-call protocol. Emit one valid tool call with a JSON object and no markdown fence."
                messages.append({"role": "user", "content": f"<tool_output>\n{observation}\n</tool_output>"})
                if callback:
                    callback({"type": "tool_output", "name": "protocol_validation", "output": observation})
            else:
                if callback:
                    callback({"type": "status", "status": "Task complete."})
                break
        else:
            if callback:
                callback({"type": "status", "status": f"Reached maximum allowed turns ({self.max_turns}). halting."})
            messages.append({
                "role": "assistant",
                "content": f"The agent reached its {self.max_turns}-turn limit before producing a verified final result. No completion claim was accepted.",
            })

        return messages

    async def run_loop_async(
        self,
        user_prompt: str,
        generate_fn: Callable[[List[Dict[str, str]]], Coroutine[Any, Any, str]],
        system_prompt: Optional[str] = None,
        project_dir: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], Coroutine[Any, Any, None] | None]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        preflight_workspace: bool = False,
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
        for message in conversation_history or []:
            if message.get("role") in {"user", "assistant"} and message.get("content"):
                messages.append({"role": message["role"], "content": message["content"]})
        if not messages or messages[-1].get("role") != "user" or messages[-1].get("content") != user_prompt:
            messages.append({"role": "user", "content": user_prompt})
        preflight_pending = bool(
            preflight_workspace and project_dir and "list_directory" in self.tool_by_name
        )

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

            if turn <= self.deliberation_turns:
                messages.append({
                    "role": "user",
                    "content": (
                        "<policy_feedback>\n"
                        "Planning phase complete. No tool action was executed on this turn. "
                        "Now use the plan to choose the single most useful next action, or answer "
                        "directly if no action is necessary. Do not call a tool merely because one "
                        "is available.\n"
                        "</policy_feedback>"
                    ),
                })
                if callback:
                    res = callback({"type": "status", "status": "Plan formed; selecting the next action."})
                    if hasattr(res, "__await__"):
                        await res

                if preflight_pending:
                    if callback:
                        res = callback({"type": "tool_call", "name": "list_directory", "args": {"dir_path": "."}})
                        if hasattr(res, "__await__"):
                            await res
                    observation = self.tool_by_name["list_directory"].execute(
                        dir_path=".", project_dir=project_dir
                    )
                    messages.append({"role": "user", "content": f"<tool_output>\n{observation}\n</tool_output>"})
                    if callback:
                        res = callback({"type": "tool_output", "name": "list_directory", "output": observation})
                        if hasattr(res, "__await__"):
                            await res
                    if "read_file_slice" in self.tool_by_name:
                        read_args = {"file_path": "scenes.py", "start_line": 1, "end_line": 240}
                        if callback:
                            res = callback({"type": "tool_call", "name": "read_file_slice", "args": read_args})
                            if hasattr(res, "__await__"):
                                await res
                        read_observation = self.tool_by_name["read_file_slice"].execute(
                            **read_args, project_dir=project_dir
                        )
                        messages.append({
                            "role": "user",
                            "content": f"<tool_output>\n{read_observation}\n</tool_output>",
                        })
                        if callback:
                            res = callback({
                                "type": "tool_output",
                                "name": "read_file_slice",
                                "output": read_observation,
                            })
                            if hasattr(res, "__await__"):
                                await res
                    preflight_pending = False
                continue

            if callback and tool_name:
                res = callback({"type": "tool_call", "name": tool_name, "args": tool_args})
                if hasattr(res, "__await__"):
                    await res

            if tool_name:
                if tool_name in self.tool_by_name:
                    tool = self.tool_by_name[tool_name]
                    
                    actual_args = dict(tool_args or {})
                    if project_dir:
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
            elif "<tool_call" in response_text or "tool_call" in response_text:
                observation = "Error: The model emitted malformed tool-call protocol. Emit one valid tool call with a JSON object and no markdown fence."
                messages.append({"role": "user", "content": f"<tool_output>\n{observation}\n</tool_output>"})
                if callback:
                    res = callback({"type": "tool_output", "name": "protocol_validation", "output": observation})
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
            messages.append({
                "role": "assistant",
                "content": f"The agent reached its {self.max_turns}-turn limit before producing a verified final result. No completion claim was accepted.",
            })

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

        manager_policy = ""
        try:
            from ..paths import ROOT

            manager_policy = (ROOT / "shared" / "prompts" / "project-manager-system.txt").read_text(
                encoding="utf-8"
            ).strip()
        except Exception:
            pass

        return f"""{manager_policy}

You are an autonomous AI engineering agent for the Matemium platform.
You operate in a deliberate loop of Plan, Action, Observation, and Reassessment.

### Rules of Engagement:
1. You must search and read files before making edits. Do not assume file layout or symbol names.
2. After making any change, you MUST run the compiler tool to verify it. Do not announce success until the compiler passes.
3. Keep your SEARCH/REPLACE blocks as small and precise as possible.
4. The project workspace normally contains scenes.py, helpers.py, and brief/. Use approved workspace-relative paths after evidence shows them; do not invent src/ or placeholder paths.
5. For edit requests, you are not done until an edit tool succeeds and compiler verification succeeds.
6. Tools are for obtaining missing evidence or changing/verifying the workspace. Do not call a tool when the current evidence is already sufficient.
7. Before each action, assess the latest evidence and choose the smallest action that can materially advance the task. Avoid repeated, speculative, or broad tool calls.

### Available Tools:
{tools_str}

### Response Format:
On the first turn, respond with only a concise planning block and no tool call. State the intended outcome, known constraints, missing evidence, and the smallest likely action sequence:
<thought>
[Concise decision plan. Do not reveal private chain-of-thought.]
</thought>

On later turns, reassess the latest observation. If an action is necessary, use:
<thought>
[Brief decision rationale based on observed evidence.]
</thought>
<tool_call name="[tool_name]">
{{
  "[arg_name]": "[arg_value]"
}}
</tool_call>

If no action is necessary, answer directly without a <tool_call> tag. If you changed files, do this only after compiler validation succeeds.
"""
