# Specification: Evolving Matemium into an Autonomous ReAct Agent

This specification outlines the architecture, principles, and implementation roadmap required to transition the Matemium AI assistant from a rigid, phase-based workflow into a dynamic, true ReAct (Reasoning + Acting) autonomous agent.

---

## 1. The Core Paradigm Shift

Currently, the Matemium local agent operates on a **hardcoded pipeline** (Director → Engineer → Critic). While effective for basic operations, it lacks the flexibility to handle ambiguous errors, perform deep codebase exploration, or course-correct gracefully.

The goal is to shift to an **Autonomous ReAct (Reasoning and Acting) loop**. In this model, the agent is given a top-level objective and a suite of tools. The agent autonomously decides:
1.  **What information it needs** (Thought).
2.  **How to get it or change it** (Action / Tool Call).
3.  **How to adapt based on the result** (Observation).

---

## 2. Architectural Pillars

To enable true autonomy while protecting context limits (the "Hero" of context management), the system must implement the following pillars:

### A. The ReAct Loop Engine
The core runner must support iterative, multi-turn executions triggered by a single user prompt.
*   **System Prompt:** The agent is instructed on its available tools, its objective, and the strict requirement to reason before acting.
*   **Tool Calling Schema:** We must implement standard OpenAI-compatible tool definitions (or generic JSON-schema definitions for local GGUF models) that the LLM can invoke.
*   **Execution Wrapper:** A robust `while` loop that captures the LLM's tool call, executes the local Python function, appends the tool output as a "user" or "tool" message, and re-queries the LLM until it emits a "Task Complete" signal or final response.

### B. Radical Context Minimization (Tool Design)
The agent must never be forced to process the entire codebase at once. Tools must be designed for surgical precision.
*   **`read_file(path, start_line, end_line)`:** Force the agent to read narrow slices of code.
*   **`search_codebase(regex_pattern, dir_path)`:** Allow the agent to grep for usages and symbols.
*   **`list_directory(path)`:** Allow the agent to navigate the project structure autonomously.
*   **`replace_in_file(path, search_string, replace_string)`:** The exact, surgical Aider-style block we already perfected, now wrapped as an explicit, targeted tool.

### C. Self-Healing & Validation (The "Critic" as an Action)
Currently, the Critic is a hardcoded fallback phase. In a ReAct agent, validation is just another tool output.
*   **`run_compiler()`:** A tool the agent can call to attempt a build. The observation returned is the `stderr` or compilation success.
*   If `run_compiler()` fails, the agent *autonomously* decides to read the problematic line, formulate a fix, apply it using `replace_in_file`, and call `run_compiler()` again.

### D. Sub-Agent Compression (Hierarchical Delegation)
For complex tasks (e.g., "Implement a new 3D tape scene"), the main "Orchestrator" agent should not bloat its context.
*   The Orchestrator can call a tool: `delegate_task(agent_role="Researcher", instruction="Find where the SolutionTape class is defined and summarize its API.")`
*   A fresh, isolated ReAct loop spawns, performs the task, and returns a dense summary. The Orchestrator's context remains clean and fast.

---

## 3. Implementation Roadmap

### Phase 1: Tool Infrastructure
1.  Define a standard interface for Tools (Name, Description, Input Schema, Execution Callable).
2.  Implement the core toolset:
    *   `read_file_slice`
    *   `grep_search`
    *   `list_files`
    *   `apply_diff_patch` (using our existing Aider logic)
    *   `run_matemium_compiler`

### Phase 2: The ReAct Engine Loop
1.  Build the `AgentRunner` class that handles the `while` loop.
2.  Integrate JSON-schema/Grammar parsing to reliably extract the LLM's thought and chosen tool.
3.  Implement safety boundaries (e.g., `max_iterations = 15` to prevent infinite loops).

### Phase 3: The Orchestrator System Prompt
Design the master system prompt:
> "You are an autonomous AI engineering agent for the Matemium platform. You operate in a continuous loop of Thought, Action, and Observation.
> You must never guess code structure; always use your search and read tools to verify assumptions before modifying files.
> Once you have modified a file, you must run the compiler tool to verify your changes. Do not report success until the compiler passes."

### Phase 4: UI/UX Transparency (The Desktop Client)
Integrate the ReAct loop logs into the desktop application's UI (building upon the `AI-CHAT-PROGRESS-SPEC.md`).
*   Show the user real-time stream of:
    *   🧠 *Thinking...*
    *   🛠️ *Agent called `grep_search("CanvasBuilder")`*
    *   👀 *Observation received (14 matches)*
    *   🧠 *Thinking...*
    *   ✏️ *Agent applied code patch to `scenes.py`*
    *   ✅ *Agent ran compiler (Success)*

---

## 4. Conclusion
By migrating from a rigid pipeline to a ReAct tool-calling architecture, Matemium's AI will evolve from a simple script-generator into a robust, context-aware co-programmer capable of independent debugging, surgical refactoring, and complex, multi-file orchestration.