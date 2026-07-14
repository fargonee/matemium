from __future__ import annotations

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


def test_react_agent_runner_loop():
    runner = ReActAgentRunner(max_turns=5)
    
    events: List[Dict] = []
    
    def progress_callback(event: Dict):
        events.append(event)

    # Let's mock a multi-turn LLM generation sequence
    llm_calls = 0
    def mock_generate_fn(history: List[Dict[str, str]]) -> str:
        nonlocal llm_calls
        llm_calls += 1
        
        if llm_calls == 1:
            # First turn: decide to search the project
            return """
<thought>I need to list files to see if scenes.py is present.</thought>
<tool_call name="list_directory">{}</tool_call>
            """
        elif llm_calls == 2:
            # Check that history includes the previous user message, assistant turn, and tool output
            assert len(history) == 4
            assert "scenes.py" in history[-1]["content"] # Tool observation should be present
            
            # Second turn: declare completion
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
    assert llm_calls == 2
    
    # Check messages array structure
    # 1. System, 2. User, 3. Assistant (decide to search), 4. User (tool observation), 5. Assistant (completed)
    assert len(messages) == 5
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"
    assert messages[4]["role"] == "assistant"

    # Check progress callbacks captured the events cleanly
    status_events = [e for e in events if e["type"] == "status"]
    thought_events = [e for e in events if e["type"] == "thought"]
    tool_call_events = [e for e in events if e["type"] == "tool_call"]
    tool_output_events = [e for e in events if e["type"] == "tool_output"]

    assert len(status_events) >= 2
    assert len(thought_events) == 2
    assert thought_events[0]["content"] == "I need to list files to see if scenes.py is present."
    assert thought_events[1]["content"] == "I found scenes.py. No further action needed."

    assert len(tool_call_events) == 1
    assert tool_call_events[0]["name"] == "list_directory"

    assert len(tool_output_events) == 1
    assert "scenes.py" in tool_output_events[0]["output"]
