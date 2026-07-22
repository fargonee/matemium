from __future__ import annotations

import asyncio
from typing import Dict, List

from matemium.agent.react_runner import ReActAgentRunner, parse_llm_response


def test_parse_llm_response():
    # Full response with thought and tool call
    text1 = """
Some raw thought here.
<thought>
I need to inspect scenes.py first.
</thought>
And some other text.
<tool_call name="read_file_slice">
{
  "file_path": "scenes.py",
  "start_line": 1,
  "end_line": 10
}
</tool_call>
    """
    thought, tool_name, tool_args = parse_llm_response(text1)
    assert thought == "I need to inspect scenes.py first."
    assert tool_name == "read_file_slice"
    assert tool_args is not None
    assert tool_args["file_path"] == "scenes.py"
    assert tool_args["start_line"] == 1
    assert tool_args["end_line"] == 10

    # Markdown JSON block self-healing
    text2 = """
<thought>Analyzing...</thought>
<tool_call name="grep_search">
```json
{"pattern": "add_heading"}
```
</tool_call>
    """
    thought, tool_name, tool_args = parse_llm_response(text2)
    assert thought == "Analyzing..."
    assert tool_name == "grep_search"
    assert tool_args is not None
    assert tool_args["pattern"] == "add_heading"

    # Thought only, no tool call
    text3 = """
<thought>Task completed successfully!</thought>
I have fixed all lines.
    """
    thought, tool_name, tool_args = parse_llm_response(text3)
    assert thought == "Task completed successfully!"
    assert tool_name is None
    assert tool_args is None

    # Small local models often omit the XML closing tag or leave a markdown fence.
    malformed = '<tool_call name="apply_diff_patch"> {"file_path":"graphs.py","search":"A","replace":"B","project_dir":null} ```'
    _, tool_name, tool_args = parse_llm_response(malformed)
    assert tool_name == "apply_diff_patch"
    assert tool_args == {"file_path": "graphs.py", "search": "A", "replace": "B", "project_dir": None}


def test_react_agent_runner_loop():
    runner = ReActAgentRunner(max_turns=5)
    
    events: List[Dict] = []
    
    def progress_callback(event: Dict):
        events.append(event)

    # The first turn deliberately attempts a tool call. The runner must record
    # the plan but defer that action until the next model turn.
    llm_calls = 0
    def mock_generate_fn(history: List[Dict[str, str]]) -> str:
        nonlocal llm_calls
        llm_calls += 1
        
        if llm_calls == 1:
            return """
<thought>I should establish the workspace shape before deciding whether any change is needed.</thought>
<tool_call name="run_compiler">{}</tool_call>
            """
        elif llm_calls == 2:
            assert "Planning phase complete" in history[-1]["content"]
            return """
<thought>The smallest useful action is listing the workspace.</thought>
<tool_call name="list_directory">{}</tool_call>
            """
        elif llm_calls == 3:
            assert len(history) == 6
            assert "scenes.py" in history[-1]["content"]
            return """
<thought>I found scenes.py. No further action needed.</thought>
I have completed my investigation.
            """
        else:
            return "Should not reach here"

    # Running loop in a clean mock project sandbox
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy scenes.py in sandbox
        import pathlib
        p = pathlib.Path(tmpdir)
        (p / "scenes.py").write_text("print('scenes')", encoding="utf-8")
        
        messages = runner.run_loop(
            user_prompt="Inspect the folder and report what you see",
            generate_fn=mock_generate_fn,
            project_dir=tmpdir,
            callback=progress_callback,
        )

    # Ensure total LLM invocations matches the scenario
    assert llm_calls == 3
    
    # Check messages array structure
    assert len(messages) == 7
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Planning phase complete" in messages[3]["content"]
    assert messages[-1]["role"] == "assistant"

    # Check progress callbacks captured the events cleanly
    status_events = [e for e in events if e["type"] == "status"]
    thought_events = [e for e in events if e["type"] == "thought"]
    tool_call_events = [e for e in events if e["type"] == "tool_call"]
    tool_output_events = [e for e in events if e["type"] == "tool_output"]

    assert len(status_events) >= 2
    assert len(thought_events) == 3
    assert thought_events[0]["content"].startswith("I should establish")
    assert thought_events[-1]["content"] == "I found scenes.py. No further action needed."

    assert len(tool_call_events) == 1
    assert tool_call_events[0]["name"] == "list_directory"

    assert len(tool_output_events) == 1
    assert "scenes.py" in tool_output_events[0]["output"]


def test_preflight_workspace_reads_scenes_file(tmp_path):
    (tmp_path / "scenes.py").write_text(
        "class Existing:\n    pass\n",
        encoding="utf-8",
    )
    runner = ReActAgentRunner(max_turns=2)
    events: List[Dict] = []
    captured_histories: List[List[Dict[str, str]]] = []

    def mock_generate_fn(history: List[Dict[str, str]]) -> str:
        captured_histories.append([dict(message) for message in history])
        if len(captured_histories) == 1:
            return "<thought>I will inspect the workspace before drawing conclusions.</thought>"
        return "I inspected the workspace."

    runner.run_loop(
        user_prompt="Inspect the folder",
        generate_fn=mock_generate_fn,
        project_dir=str(tmp_path),
        callback=events.append,
        preflight_workspace=True,
    )

    assert any(event.get("name") == "list_directory" for event in events)
    assert any(event.get("name") == "read_file_slice" for event in events)
    assert not any("class Existing" in message["content"] for message in captured_histories[0])
    assert any("class Existing" in message["content"] for message in captured_histories[1])
    first_thought = next(i for i, event in enumerate(events) if event.get("type") == "thought")
    first_tool = next(i for i, event in enumerate(events) if event.get("type") == "tool_call")
    assert first_thought < first_tool


def test_async_runner_defers_first_turn_tool_call(tmp_path):
    runner = ReActAgentRunner(max_turns=2)
    events: List[Dict] = []
    calls = 0

    async def mock_generate_fn(_history: List[Dict[str, str]]) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            return """
<thought>I need a plan before touching the workspace.</thought>
<tool_call name="apply_diff_patch">
{"file_path":"scenes.py","search":"old","replace":"new"}
</tool_call>
            """
        return "No workspace action is needed."

    asyncio.run(
        runner.run_loop_async(
            user_prompt="Assess the requested change",
            generate_fn=mock_generate_fn,
            project_dir=str(tmp_path),
            callback=events.append,
        )
    )

    assert calls == 2
    assert not any(event.get("type") == "tool_call" for event in events)
    assert not (tmp_path / "scenes.py").exists()
