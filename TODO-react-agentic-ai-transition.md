# TODO Plan: Transitioning Matemium to an Autonomous ReAct Agent

This document outlines the step-by-step, actionable tasks to transition the Matemium AI assistant from the legacy rigid pipeline to the autonomous ReAct (Reasoning + Acting) loop.

---

## Phase 1: Tool Infrastructure (`matemium/agent/tools/`)

- [x] **1.1 Base Tool Definition**
  - [x] Create a standard base class/interface `BaseTool` in a new file `matemium/agent/tools/base.py`.
  - [x] Implement support for automatic JSON Schema generation from Pydantic models for each tool's argument definition.

- [x] **1.2 Core File-System Tools**
  - [x] Implement `read_file_slice(file_path, start_line, end_line)` with robust boundary checking to prevent bloating the context.
  - [x] Implement `grep_search(pattern, dir_path)` using Python's `re` module to locate functions, classes, and variable uses.
  - [x] Implement `list_directory(dir_path)` to allow the agent to inspect project directories.

- [x] **1.3 Modification & Compilation Tools**
  - [x] Implement `apply_diff_patch(file_path, search, replace)` using our existing Aider-style search/replace patch engine.
  - [x] Implement `run_compiler(project_id)` to execute the local Matemium compilation pipeline and return stdout/stderr.

- [x] **1.4 Safety & Unit Testing**
  - [x] Add guardrails to prevent path traversal (e.g., block tool calls attempting to read/write outside the active workspace directory).
  - [x] Write robust unit tests under `tests/test_react_tools.py` verifying each tool's behavior under success and error conditions.

---

## Phase 2: ReAct Engine Loop (`matemium/agent/react_runner.py`)

- [x] **2.1 Implement the Loop Class**
  - [x] Create `ReActAgentRunner` to manage the conversation state and execute the tool-calling loop.
  - [x] Design the conversation list structure: `[System, User, Thought/Tool Call, Tool Output, Thought, ...]`.

- [x] **2.2 Parser & Schema Extraction**
  - [x] Write a robust regex/JSON parser to extract the chosen `<thought>` and `<tool_call>` (with arguments) from the raw LLM string.
  - [x] Adapt the parser to support both standard OpenAI-compatible tool schemas (for cloud APIs) and GBNF grammars (for GGUF local LLMs).

- [x] **2.3 Loop Boundary Controls**
  - [x] Enforce a strict `max_turns = 10` limit to prevent expensive runaway infinite loops.
  - [x] Set up credit balance and token usage meters to track consumption during the loop execution.

- [x] **2.4 Integration Tests**
  - [x] Add mock-based integration tests under `tests/test_react_runner.py` simulating an entire thought -> search -> edit -> compile -> complete loop.

---

## Phase 3: Prompt Engineering & System Alignment

- [x] **3.1 Create Master ReAct Prompt**
  - [x] Create `shared/prompts/react-agent-system.txt` outlining the rules of reasoning:
    - Must search and read files before editing.
    - Must run the compiler tool after every edit.
    - Must never guess function signatures or variable names.
    - Must keep search/replace blocks as small and surgical as possible.

- [x] **3.2 Self-Healing Examples**
  - [x] Include clear few-shot examples in the prompt demonstrating how to process compile errors (stderr) and issue subsequent fixes.

---

## Phase 4: Full Stack Streaming & Desktop UI

- [x] **4.1 Streamable FastAPI Backend**
  - [x] Expose an event-driven endpoint (Websockets or Server-Sent Events) at `/v1/chat/stream` in `server/matemium_server/routes/chat.py`.
  - [x] Push progress updates synchronously as the agent executes tool calls:
    - `{"type": "thought", "content": "..."}`
    - `{"type": "tool_call", "name": "grep_search", "args": {...}}`
    - `{"type": "tool_output", "output": "..."}`

- [x] **4.2 React Frontend State Updates**
  - [x] Map the stream events directly to `App.tsx`'s active `ExecutionProgress` state.
  - [x] Populate the progress ledger stepper with detailed operations dynamically.

- [x] **4.3 UI Rendering Enhancements**
  - [x] Render the golden-bordered collapsible reasoning panel for `<thought>` blocks in `ChatPanel.tsx`.
  - [x] Render a live, line-by-line colored diff box as soon as a `replace_in_file` action is proposed, requesting user confirmation before execution.

---

## Phase 5: Production Validation & Deployment

- [x] **5.1 End-to-End Test Suite**
  - [x] Perform live, end-to-end integration tests using local test sheets (e.g., `projects/demo/`).
  - [x] Verify that credit tracking accurately logs platform costs for the entire multi-turn ReAct run.
- [x] **5.2 User Opt-In Control**
  - [x] Add an "Enable Autonomous Agent Mode" toggle in the desktop application's Settings panel, allowing users to switch between the classic pipeline and the new autonomous ReAct model.
