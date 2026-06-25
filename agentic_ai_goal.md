## 1. System Vision & Objective

Matemium’s AI subsystem is not a passive code autocomplete tool. It is an **Autonomous Elite Director & Mathematical Animator**. It transforms weak, incomplete user ideas into high-fidelity, visually stunning, educational motion art.

The agent operates across two distinct user tiers (Token-Based Core and Multi-Modal Loop Premium) to maximize revenue, manage compute efficiency, and consistently deliver production-grade 9:16 and 16:9 animations.

---

## 2. Multi-Agent Lifecycle Architecture

```
 ┌────────────────────────────────────────────────────────┐
 │ 1. THE DIRECTOR AGENT (Creative Brainstorming & DSL)   │
 └───────────────────────────┬────────────────────────────┘
                             │ Finalized Script & Mode Config
                             ▼
               { User Selected Mode? }
              /                       \
      (Audio Mode)                 (Mute Mode)
            /                           \
 ┌─────────▼───────────────┐     ┌───────▼────────────────┐
 │ 2A. NARRATION PIPELINE  │     │ 2B. BEAT-CADENCE MAP   │
 │ Renders audio first;    │     │ Assigns standard pacing│
 │ extracts word-level     │     │ delays to narrative block│
 │ timestamps (Whisper JSON│     │ segments mathematically│
 └─────────┬───────────────┘     └───────┬────────────────┘
           \                             /
            └──────────────┬────────────┘
                           │ Precise Timing Blueprint
 ┌─────────────────────────▼──────────────────────────────┐
 │ 3. THE ENGINEER AGENT (Surgical Code Generation)       │
 └─────────────────────────┬──────────────────────────────┘
                           │ Python `scenes.py` + `assets.py`
 ┌─────────────────────────▼──────────────────────────────┐
 │ 4. THE CRITIC LOOP (Visual Self-Correction - Premium)  │◄──┐
 └─────────────────────────┬──────────────────────────────┘   │ Iterative
                           │ Rendered Video Frames          │ Refinement
                           ▼                                │ Loop
                     { Passes Visual QC? } ─────────────────┘
                           │ Yes
 ┌─────────────────────────▼──────────────────────────────┐
 │ 5. THE POST-PRODUCTION AGENT (Sound & Render Mix)     │
 └────────────────────────────────────────────────────────┘

```

### Phase 1: The Director Agent (Creative & Pedagogy)

* **Role:** Acts as an elite math educator, Disney-grade scriptwriter, and seasoned content creator.
* **Behavior:** If a user provides a weak prompt (e.g., *"Explain quadratic formula"*), the Director **rejects mediocrity**. It proactively suggests narrative hooks, visual metaphors (e.g., morphing a physical square area into algebraic variables), and pacing options.
* **User Collaboration:** It loops with the user to lock in the script, tone, chapter layout boundaries (`# ---DIV: ...`), and configuration switches (Audio Mode vs. Mute Mode).

### Phase 2: Timing Blueprint Instantiation (Decoupled Generation)

Before a single line of animation code is structured, the absolute timeline must be mapped to ensure frame-perfect synchronization.

* **Path A: Audio Mode (Audio-First Execution)**
1. The script text is dispatched to high-fidelity TTS systems to compile the raw voiceover track.
2. The resulting audio is processed via word-level timestamp extractors (e.g., Whisper JSON parsing) to isolate exact millisecond coordinates for every spoken keyphrase.
3. Kinetic subtitle payloads are auto-baked into the design parameters.


* **Path B: Mute Mode (Beat-Cadence Execution)**
1. Audio generation is skipped completely to protect user token allocations or fulfill layout requirements.
2. The engine switches to mathematical reading-cadence estimations (e.g., word-count-to-duration ratios scaled by mathematical reading complexities) to generate a static, predictable temporal layout map for the animation timeline.



### Phase 3: The Engineer Agent (Surgical Implementation)

* **Role:** A highly disciplined Manim/Matemium compiler specialist (inspired by Claude Code & Cursor).
* **Behavior:** Translates the locked script and its precise Timing Blueprint into **strictly decoupled** Python infrastructure:
* `scenes.py`: Clean, readable timeline narrative using `CanvasBuilder` and structural flex layout dicts (`style={}`). **Crucial:** It explicitly anchors animation reveal delays and camera moves to the calculated durations passed down by Phase 2 via explicit `builder.wait(duration)` markers.
* `assets.py`: Heavy lifting, pure mathematics, LaTeX strings, coordinate generation matrices, and mesh definitions.


* **Execution Strategy:** Uses targeted Search/Replace diff patches rather than rewriting entire files, protecting local compute resources.

### Phase 4: The Critic & Self-Correction Loop (Premium Multi-Modal)

* **Role:** Quality Assurance inspector using multi-modal capabilities.
* **Behavior:**
1. Triggers local execution via the sidecar pipeline (`compile_manim`).
2. If standard compilation fails, it parses `stderr`, runs absolute self-correction patches, and retries (capped at 3 attempts).
3. **Visual Verification:** On successful build, it inspects keyframe image screenshots or mini-clip renders via multi-modal vision inputs. It checks for clipping text, overlapping math objects, or poor contrast, adjusting `style={}` layouts automatically until visual balance is achieved.



### Phase 5: The Post-Production Mixer (Final Assembly)

* **Role:** Sound engineer.
* **Behavior:**
* *In Audio Mode:* Uses `ffmpeg` sidecar tasks to map background audio tracks (Suno/Udio hooks) tightly against the generated narrative voiceover track, combining them directly into `ReelCutter` splits.
* *In Mute Mode:* Skips voice tracks entirely; optional option to attach smooth, low-fidelity ambient backing tracks or deliver pure silent canvas exports.



---

## 3. Business & Monetization Matrix

To optimize API costs while giving users freedom, Matemium uses a hybrid **Dynamic Token Wallet + Add-On Features** model.

### Token Economy

* **The Unit:** Users purchase a generic pool of "Matemium Tokens".
* **Model Scaling:** Token deduction scales directly based on the engine model driving the session:
* *Standard Tasks (GPT-4o mini / Claude Haiku):* 1x Token multiplier.
* *Elite Reasoning Tasks (Claude 3.5 Sonnet / GPT-4o):* 5x Token multiplier.
* *Deep Thinking/Heavy Engine (Claude 3 Opus / o1/o3):* 12x Token multiplier.


* **Onboarding:** New users receive a complimentary bucket of one-time non-refreshing tokens to demo standard operations.

### Feature Access Levels

| Feature | Basic Plan / Token Only | Premium Plan (Subscription + Tokens) |
| --- | --- | --- |
| **Code Generation** | Standard text diff patches | Multi-modal visual feedback loop |
| **Audio Sync / Timing** | Beat-Cadence (Mute Mode Only) | Full Audio-First Timestamp Extraction Engine |
| **Watermarking** | Permanent `"matemium"` logo overlay | Removable via subscription or flat per-project token fee |
| **Reel Cutting** | Standard multi-file splitting | Batch export directly optimized for platform metadata |

---

## 4. Agent Operational Guardrails & Directives

When modifying or generating content within a workspace, the agent must stringently follow these internal laws:

* **Guardrail 1: Radical Decoupling.** Under no circumstances should raw math coordinate computations, complex LaTeX string arrays, or raw procedural loops live inside `scenes.py`. Keep layouts clean; map logic to `assets.py`.
* **Guardrail 2: Absolute Temporal Dependency.** Never guess wait/delay timings inside `scenes.py`. All structural durations MUST trace directly back to the calculated metrics delivered from the Phase 2 Timing Blueprint.
* **Guardrail 3: Do Not Settle for Basic Logic.** If an animation is static or uninspiring, inject dynamic transforms, smooth camera zooms (`camera.py`), or subtle orthographic tilts to emphasize 3D transitions.
* **Guardrail 4: Strict Error Capping.** The self-correction compile loop must drop a detailed trace log file (`.matemium_debug.json`) and halt for human confirmation if an issue cannot be resolved within 3 compile iterations. This prevents infinite token bleeding.
* **Guardrail 5: Fail-Safe Defaults.** If an explicit styling variable is omitted by the user, fallback to the strict 9:16 vertical design aesthetic (dark mode, high-contrast mathematical colors like neon cyan, gold, and clean white).