# Specification: Rich, Transparent AI Chat Progress Canvas

This specification outlines the requirements, architectural design, user experience (UX) layout, and step-by-step implementation plan to upgrade the Matemium Desktop AI Assistant panel from a passive chat interface to an active, transparent, and high-fidelity **orchestration canvas** (similar to modern platforms like Roo Code, Claude Code, and Cursor).

---

## 1. Objectives & Philosophy

1. **Establish a "Chain of Trust"**: Build deep developer trust by making the AI's internal cognitive loop visible. Never hide background work behind a generic loading spinner.
2. **Action Transparency**: Make every context retrieval (RAG), LLM inference call, file-modification search-and-replace, and validation step fully traceable.
3. **Prevent "Black Box" Anxiety**: Allow users to inspect *why* changes are being suggested and *what* specific lines are being updated before committing changes to their editors.

---

## 2. Key Features

### A. Collapsible Reasoning Layer (`🧠 Cognitive Reasoning`)
*   **The Problem**: LLMs generate internal chain-of-thought tokens or high-level explanations that clutter the main conversation if displayed as raw text, but are highly valuable for understanding complex code generation.
*   **The Solution**: Support wrapping reasoning tokens in `<thought>` or `<reasoning>` tags (emitted by reasoning models or structured prompts).
*   **UI/UX Component**:
    *   Render a custom, collapsible `<details>` panel in the `ChatPanel` chat bubble.
    *   Styled with a subtle golden/amber left-border, a brain icon, and monospace typography.
    *   Keep it collapsed by default to prevent visual noise, with an active summary label like: `🧠 Cognitive Reasoning (Expand to inspect)`.

### B. Context & Discovery Audit (`🔍 Context Reference Log`)
*   **The Problem**: Developers don't know if the AI is hallucinating or referencing actual relevant codebase structures.
*   **The Solution**: Display a persistent context audit card during context assembly.
*   **UI/UX Component**:
    *   Show an expandable panel outlining what resources were fed into the prompt:
        *   `📄 Scenes Excerpt (Editor Buffer)`
        *   `📂 Local Embeddings Database (RAG Search Results)`
        *   `🔗 Related schemas / templates`
    *   Under the RAG results, list the top files and matching chunks with score attributes (e.g., `scenes.py - match score: 94%`).

### C. Visual, Interactive Inline Diff (`✏️ Search & Replace Preview`)
*   **The Problem**: The current `pendingEdit` box is a basic text description with a blind "Apply to editor" button. Users have no line-by-line visibility of the changes.
*   **The Solution**: An elegant, native Git-like inline diff preview.
*   **UI/UX Component**:
    *   Parse the `CodeEdit`'s `search` (old string) and `replace` (new string) fields.
    *   Display a side-by-side or stacked block highlighting deleted and added lines:
        *   **Red (`-`) background**: Lines present in `search` but modified/removed.
        *   **Green (`+`) background**: Lines present in `replace` to be inserted.
    *   Include line numbers (if trackable) or simple side indicators so the user knows exactly where and what the patch does before applying.

### D. Multi-Step Execution Stepper (`⚙️ Live Action Ledger`)
*   **The Problem**: During long-running calls, the app just says "Working..." with a disabled send button, making it look frozen.
*   **The Solution**: A real-time operations checklist placed inside the chat history stream while a request is active.
*   **Lifecycle Steps**:
    1.  **Context Preparation**: `Preparing local scene workspace files...`
    2.  **RAG Analysis**: `Querying PyInstaller sidecar for vector similarity...`
    3.  **LLM Generation**: `Streaming response from Claude/Gemini model...`
    4.  **Edit Extraction**: `Synthesizing structural code search-and-replace blocks...`
    5.  **Provider Sync**: `Refreshing provider usage metadata...`
*   **Visual Indicators**:
    *   🟢 **Green Check**: Step successfully completed.
    *   ⏳ **Pulsing Spinner/Amber**: Currently active step.
    *   ⚪ **Muted Grey**: Pending step.

---

## 3. UI/UX Visual Layout

```
+-------------------------------------------------------------+
| AI Assistant                      (OpenRouter: connected)   |
+-------------------------------------------------------------+
|                                                             |
|  [User] Can you refactor my scene to use a continuous       |
|         SolutionTape instead of a raw 3D plane?             |
|                                                             |
|  [AI Assistant]                                             |
|  +-------------------------------------------------------+  |
|  | 🧠 Cognitive Reasoning (Click to expand)             v |  |
|  +-------------------------------------------------------+  |
|  I will introduce a SolutionTape object, position it at      |
|  world coordinate (0, -2, 0), and bind the camera focus     |
|  mechanisms to track its local progression.                 |
|                                                             |
|  +-------------------------------------------------------+  |
|  | 🔍 Context Reference Audit                           ^ |  |
|  |   - scenes.py (Editor Buffer, lines 1-120)            |  |
|  |   - RAG Match: canvas/measurement/manim_backend.py (88%)| |
|  |   - RAG Match: canvas/dsl.py (74%)                    |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | Proposed Code Change:                                 |  |
|  | -   plane = ThreeDPlane(size=8)                        |  |
|  | +   tape = SolutionTape(width=6, direction="down")     |  |
|  | +   self.add(tape)                                     |  |
|  |                                                       |  |
|  | [ Apply Edit to Editor ]                              |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  | ⚙️ Operation Progress Ledger                          |  |
|  |   ✅ 1. Assembled local codebase workspace             |  |
|  |   ✅ 2. Executed sidecar vector retrieval (RAG)        |  |
|  |   ⏳ 3. Formulating response from AI models...         |  |
|  |   ⚪ 4. Synthesizing structural search/replace blocks  |  |
|  +-------------------------------------------------------+  |
|                                                             |
+-------------------------------------------------------------+
| [ Describe changes or ask for help...                     ] |
|                                             [ Send ] [ 🔊 ] |
+-------------------------------------------------------------+
```

---

## 4. State & Communication Architecture

To support this rich flow, we will manage intermediate states within our React frontend and communicate steps progressively:

### A. Extended Progress State (`App.tsx`)
We will track the active step, logs, and reasoning text:
```typescript
interface ExecutionProgress {
  step: "idle" | "preparing" | "retrieving" | "thinking" | "processing" | "refreshing";
  logs: string[];
  ragMatches?: Array<{ file: string; score: number }>;
}
```

### B. Reasoning & Thought Extraction (`ChatPanel.tsx`)
When the AI assistant returns text, we will parse out thought tags:
```typescript
function parseThoughtBlocks(content: string): { thought: string | null; cleanContent: string } {
  const thoughtRegex = /<(?:thought|reasoning)>([\s\S]*?)<\/(?:thought|reasoning)>/i;
  const match = content.match(thoughtRegex);
  if (match) {
    const cleanContent = content.replace(thoughtRegex, "").trim();
    return { thought: match[1].trim(), cleanContent };
  }
  return { thought: null, cleanContent: content };
}
```

### C. Inline Diff Generation
When a `pendingEdit` is active:
```typescript
interface DiffLine {
  type: "added" | "removed" | "unchanged";
  text: string;
}

function computeEditDiff(search: string, replace: string): DiffLine[] {
  const searchLines = search.split("\n");
  const replaceLines = replace.split("\n");
  
  // High-fidelity line mapping for side-by-side or stacked inline display
  const diff: DiffLine[] = [];
  searchLines.forEach(line => diff.push({ type: "removed", text: line }));
  replaceLines.forEach(line => diff.push({ type: "added", text: line }));
  return diff;
}
```

---

## 5. Styling Guidelines (`App.css`)

We will introduce modern dark-theme styles optimized for the Obsidian aesthetics:
- **Steppers**: Thin vertical lines with pulsing nodes matching `--accent` and `--text-secondary`.
- **Reasoning Box**: `--bg-elevated` background with a golden/amber border (`border-left: 3px solid #d4af37`), distinct typography, and subtle shadows.
- **Diff Box**:
  - Code wrapping in `code` blocks with monospace font sizes.
  - Added lines: light-green tint background (`rgba(46, 160, 67, 0.15)`) with deep green inline borders.
  - Removed lines: light-red tint background (`rgba(248, 81, 73, 0.15)`) with deep red inline borders.
- **Micro-Animations**: Smooth opacity changes (`transition: all 0.25s ease-in-out`) and pulsing dots for active operations.

---

## 6. Implementation Milestones

1. **Phase 1: Progress Ledger & States**: Setup React states in `App.tsx` and integrate live operation steps into `ChatPanel.tsx` using a beautifully styled UI stepper.
2. **Phase 2: Reasoning Parser**: Write regex-based parsing to extract `<thought>` blocks from chat streams or mock test messages and render them in expandable blocks.
3. **Phase 3: Context References**: Capture RAG results inside the sidecar retrieval handler and display the resulting database references inside the chat stream.
4. **Phase 4: Stacked Inline Diff**: Implement line-level diff calculations for `pendingEdit` search/replace strings and present it as an inline, color-coded block in the `ChatPanel` with clear "Apply" action buttons.
5. **Phase 5: Self-Correction Validation**: Pipe linter errors and verification feedback directly back to the chat progress panel when an AI suggestion fails, illustrating the self-correction cycle.
