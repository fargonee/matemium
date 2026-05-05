# Full Spec: Matemium `SolutionTape`

## Reusable Manim Tool for Tape-Like Mathematical Demonstration

## 0. Context

`SolutionTape` is a reusable Manim system for Matemium videos.

Matemium’s goal is not just to solve math problems, but to reveal the hidden thinking process behind a solution: what is happening, why each step matters, and how one idea connects to another. The project’s strongest identity is “we show the invisible logic behind the solution.”

`SolutionTape` should become one of Matemium’s core visual tools for doing exactly that.

It is not just a scrollable notebook.

It is a **stateful visual reasoning field**.

---

# 1. Core Idea

`SolutionTape` creates a long vertical mathematical “tape” inside a fixed video viewport.

The tape behaves like a scrollable reasoning surface:

```text
┌─────────────────────────┐
│                         │
│   earlier observation   │
│                         │
│   previous equation     │
│                         │
│ → current active step   │
│                         │
│   next idea appears     │
│                         │
└─────────────────────────┘
```

As the solution develops:

- new rows are added
- the tape scrolls smoothly
- earlier rows can be revisited
- important steps can be highlighted
- sections can be magnified
- states can be frozen
- the full solution can become a shareable summary image

The viewer should feel like they are watching a thought process unfold.

---

# 2. Main Purpose

`SolutionTape` should help Matemium creators produce short, clear, engaging Manim videos where mathematical reasoning is visible, memorable, and reusable.

The system should support:

1. **Step-by-step solution writing**
2. **Smooth scrolling through a long solution**
3. **Visual callbacks to earlier ideas**
4. **Highlighting and magnification**
5. **Difficulty-level styling**
6. **Replay / reanimation**
7. **Frozen static states**
8. **Full-tape export**
9. **Reusable visual language across videos**

---

# 3. Design Philosophy

The tape should not be a dumping ground for equations.

Every row should answer at least one of these:

- What are we noticing?
- What do we know?
- What are we trying?
- Why is this legal?
- What changed?
- Why does this help?
- What should we remember?
- What did we prove?

The tool should support Matemium’s teaching style:

- visual clarity
- thinking-first explanation
- friendly depth
- short-form pacing
- non-boring mathematical storytelling

---

# 4. Recommended Name

Implementation name:

```python
SolutionTape
```

Brand-facing concept:

```text
Matemium Reasoning Tape
```

Reason:

- `SolutionTape` is clear for code.
- `ReasoningTape` is stronger as a visual identity.

---

# 5. High-Level Usage Example

Target usage should feel simple:

```python
class FactoringExample(Scene):
    def construct(self):
        tape = SolutionTape(
            scene=self,
            difficulty="easy",
            theme="matemium_dark",
            viewport="reel"
        )

        tape.add_problem(
            r"Solve: x^2 - 5x + 6 = 0",
            tag="Algebra"
        )

        tape.add_observation(
            "This expression has a hidden product form."
        )

        tape.add_math(
            r"x^2 - 5x + 6",
            anchor="original_expression"
        )

        tape.add_note(
            "We need two numbers that multiply to 6 and add to -5.",
            tone="hint"
        )

        tape.add_math(
            r"x^2 - 5x + 6 = (x-2)(x-3)",
            anchor="factored_form"
        )

        tape.callback_to(
            "original_expression",
            message="Same expression, new form."
        )

        tape.add_math(r"(x-2)(x-3)=0")

        tape.add_concept(
            "Zero-product idea",
            "If a product is zero, at least one factor must be zero.",
            formula=r"ab=0 \Rightarrow a=0 \text{ or } b=0"
        )

        tape.add_math(r"x-2=0 \quad \text{or} \quad x-3=0")

        tape.add_conclusion(
            "So the solutions are",
            math=r"x=2 \quad \text{or} \quad x=3"
        )

        tape.reveal_full_tape()
```

The creator writes a reasoning script. The tape handles layout, scrolling, state, and visual behavior.

---

# 6. Core Architecture

The tool should use a **model-view-playback architecture**.

```text
SolutionTape
│
├── TapeModel
│   ├── rows
│   ├── anchors
│   ├── states
│   ├── events
│   └── metadata
│
├── TapeView
│   ├── viewport
│   ├── tape background
│   ├── grid
│   ├── content layer
│   ├── highlight layer
│   └── overlay layer
│
└── TapePlayback
    ├── row animations
    ├── scroll animations
    ├── callback animations
    ├── replay
    ├── freezing
    └── export
```

This is important.

The tape should know what it **is**, not only what it is currently animating.

---

# 7. Main Class: `SolutionTape`

## 7.1 Constructor

```python
SolutionTape(
    scene,
    width=7.0,
    viewport_height=12.5,
    tape_height=None,
    difficulty="easy",
    theme="matemium_dark",
    viewport="reel",
    row_gap=0.55,
    padding=0.45,
    active_y=-1.4,
    show_grid=True,
    show_frame=True,
    keep_last_n_rows_visible=2,
    animate_by_default=True,
)
```

## 7.2 Parameters

| Parameter                  | Meaning                                  |
| -------------------------- | ---------------------------------------- |
| `scene`                    | Current Manim scene                      |
| `width`                    | Width of the tape                        |
| `viewport_height`          | Visible height                           |
| `tape_height`              | Optional virtual tape height             |
| `difficulty`               | `easy`, `medium`, or `hard`              |
| `theme`                    | Visual preset                            |
| `viewport`                 | `reel`, `square`, `landscape`, or custom |
| `row_gap`                  | Space between rows                       |
| `padding`                  | Inner tape margin                        |
| `active_y`                 | Preferred y-position for active row      |
| `show_grid`                | Whether to display subtle grid           |
| `show_frame`               | Whether to display border/frame          |
| `keep_last_n_rows_visible` | How much recent context stays visible    |
| `animate_by_default`       | Whether rows animate immediately         |

---

# 8. Internal State

`SolutionTape` should maintain clear internal state.

```python
self.scene

self.model
self.view
self.playback

self.rows = []
self.anchors = {}
self.states = {}
self.events = []

self.current_row_index = -1
self.current_y = 0
self.scroll_offset = 0
self.current_view_center_y = 0

self.theme
self.difficulty
self.config
```

The class should never rely only on visible Manim positions. It should always store semantic and layout data.

---

# 9. Tape Layers

The visual tape should be built from layers.

```text
Viewport / Scene
│
├── background layer
│   ├── base rectangle
│   ├── subtle grid
│   └── difficulty tint
│
├── frame layer
│   ├── border
│   └── corner marker
│
├── content layer
│   ├── problem card
│   ├── rows
│   ├── notes
│   └── diagrams
│
├── highlight layer
│   ├── boxes
│   ├── glows
│   ├── underlines
│   └── side markers
│
└── overlay layer
    ├── focus cards
    ├── magnified copies
    └── temporary captions
```

This keeps the system predictable.

---

# 10. `TapeRow`

Every visible content item should become a registered row.

```python
TapeRow(
    id,
    mobject,
    row_type,
    y_position,
    height,
    anchor_name=None,
    visible=False,
    metadata={}
)
```

## Row types

```python
"problem"
"observation"
"text"
"math"
"step"
"note"
"concept"
"warning"
"check"
"conclusion"
"diagram"
"custom"
```

Different row types should have different default styles and animations.

---

# 11. Content API

## 11.1 Add problem

```python
tape.add_problem(
    text,
    subtitle=None,
    tag=None,
    difficulty_label=True,
    anchor="problem",
    animate=None
)
```

Use for the initial problem card.

Behavior:

- appears near top of tape
- gets automatic anchor
- may show topic tag
- may show difficulty marker

---

## 11.2 Add observation

```python
tape.add_observation(
    text,
    anchor=None,
    animate=None
)
```

Use for “what we notice first.”

Example:

```python
tape.add_observation(
    "The expression looks messy, but the exponents follow a pattern."
)
```

This supports Matemium’s thinking-first approach.

---

## 11.3 Add text

```python
tape.add_text(
    text,
    label=None,
    anchor=None,
    animate=None
)
```

General explanatory text row.

---

## 11.4 Add math

```python
tape.add_math(
    latex,
    label=None,
    reason=None,
    anchor=None,
    animate=None,
    transform_from=None
)
```

Example:

```python
tape.add_math(
    r"x^2 - 5x + 6 = (x-2)(x-3)",
    reason="because -2 and -3 multiply to 6 and add to -5",
    anchor="factored_form"
)
```

Optional `reason` can appear as a side note or small explanation under the equation.

Optional `transform_from` may use `TransformMatchingTex`.

---

## 11.5 Add step

```python
tape.add_step(
    title,
    content=None,
    math=None,
    anchor=None,
    animate=None
)
```

Use for bigger conceptual moves.

Example:

```python
tape.add_step(
    "Rewrite as a product",
    "This lets us use the zero-product idea.",
    math=r"(x-2)(x-3)=0"
)
```

---

## 11.6 Add note

```python
tape.add_note(
    text,
    tone="neutral",
    anchor=None,
    animate=None
)
```

Possible tones:

```python
"neutral"
"hint"
"warning"
"insight"
"shortcut"
"memory"
```

---

## 11.7 Add concept card

```python
tape.add_concept(
    title,
    explanation,
    formula=None,
    anchor=None,
    animate=None
)
```

Use for quick reminders.

Example:

```python
tape.add_concept(
    "Zero-product idea",
    "If a product is zero, one factor must be zero.",
    formula=r"ab=0 \Rightarrow a=0 \text{ or } b=0"
)
```

Concept cards should be short. They should support the solution, not interrupt it.

---

## 11.8 Add check

```python
tape.add_check(
    text=None,
    math=None,
    anchor=None,
    animate=None
)
```

Use to verify answers.

---

## 11.9 Add conclusion

```python
tape.add_conclusion(
    text,
    math=None,
    emphasize=True,
    anchor="answer",
    animate=None
)
```

The conclusion should have a satisfying final animation.

---

## 11.10 Add custom object

```python
tape.add_mobject(
    mobject,
    row_type="custom",
    anchor=None,
    animate=None
)
```

Use for diagrams, graphs, custom visuals, icons, or special layouts.

---

# 12. Anchors

Anchors let the tape remember important rows or objects.

## 12.1 Add anchor

```python
tape.add_anchor(name, target="latest")
```

Targets may be:

- latest row
- row id
- another anchor
- specific mobject
- group of rows

## 12.2 Anchor examples

```python
tape.add_anchor("given")
tape.add_anchor("goal")
tape.add_anchor("key_fact")
tape.add_anchor("substitution")
tape.add_anchor("answer")
```

## 12.3 Anchor operations

```python
tape.get_anchor(name)
tape.scroll_to(name)
tape.highlight(name)
tape.callback_to(name)
tape.freeze_rows(["given", "key_fact", "answer"])
```

Anchors are essential for callbacks, reanimation, freezing, and export.

---

# 13. Layout Rules

## 13.1 Vertical stacking

Rows are stacked top to bottom.

Each row stores:

```python
top_y
center_y
bottom_y
height
```

The tape should calculate height dynamically.

Important: math expressions, notes, diagrams, and concept cards may have different heights.

---

## 13.2 Safe margins

Recommended defaults:

```python
top_safe_margin = 0.6
bottom_safe_margin = 0.8
left_safe_margin = 0.35
right_safe_margin = 0.35
```

Text and math should never touch the tape edge.

---

## 13.3 Active row zone

Default active row position:

```python
active_y = -1.4
```

For vertical reels, the active row should usually sit slightly below center. This leaves visible context above.

---

## 13.4 Context preservation

When a new row appears, the previous one or two rows should often remain visible.

Default:

```python
keep_last_n_rows_visible = 2
```

This avoids a disconnected “one-line-at-a-time” feeling.

---

# 14. Scrolling

## 14.1 Required methods

```python
tape.scroll_to(target, align="center", run_time=None)
tape.scroll_by(amount, run_time=None)
tape.scroll_to_current(run_time=None)
tape.return_to_current(run_time=None)
```

## 14.2 Scroll styles

```python
"smooth"
"snap"
"elastic"
"cinematic"
```

Default:

```python
scroll_style="smooth"
```

## 14.3 Scroll behavior

When adding a new row:

1. row is created
2. row is positioned below previous content
3. system checks whether active row zone is exceeded
4. tape scrolls if needed
5. row animates into view

The creator should not manually position the camera for ordinary rows.

---

# 15. Highlighting

## 15.1 Required methods

```python
tape.highlight(target, label=None, style="soft")
tape.flash(target)
tape.box(target)
tape.underline(target)
tape.dim_except(target)
tape.clear_highlights()
```

## 15.2 Highlight styles

| Style         | Use                |
| ------------- | ------------------ |
| `soft`        | normal emphasis    |
| `glow`        | key insight        |
| `underline`   | algebraic focus    |
| `box`         | important equation |
| `side_marker` | important row      |
| `dim_except`  | focus attention    |

Example:

```python
tape.highlight(
    "factored_form",
    label="This new form is easier to use.",
    style="glow"
)
```

---

# 16. Callback System

A callback is when the solution revisits an earlier idea.

This is one of the most important Matemium-specific features.

## 16.1 Method

```python
tape.callback_to(
    target,
    message=None,
    return_after=True,
    highlight_style="glow",
    run_time=None
)
```

## 16.2 Callback sequence

1. current row pauses
2. tape scrolls to earlier anchor
3. target row is highlighted
4. optional message appears
5. optional connector appears
6. tape returns to current row
7. solution continues

Example:

```python
tape.callback_to(
    "factor_pattern",
    message="This earlier pattern is the key now.",
    return_after=True
)
```

Callbacks visually teach that math uses memory, structure, and reuse.

---

# 17. Zoom and Magnification

## 17.1 Required methods

```python
tape.zoom_to(target)
tape.magnify(target)
tape.restore_zoom()
tape.focus_card(target, caption=None)
```

## 17.2 Recommended MVP approach

For reliability, the first version should use **focus cards**, not true camera zoom.

A focus card:

- duplicates the target row
- enlarges it
- places it in the viewport
- dims the background
- optionally shows a caption
- then disappears

Example:

```python
tape.focus_card(
    "important_equation",
    caption="This is the hidden structure."
)
```

This is safer than manipulating the entire camera early in development.

---

# 18. Difficulty-Level Styling

The tape should support visual difficulty levels.

```python
difficulty="easy"
difficulty="medium"
difficulty="hard"
```

Difficulty should be visible but subtle.

## Suggested styling

| Level  | Mood                  | Visual treatment                                  |
| ------ | --------------------- | ------------------------------------------------- |
| Easy   | calm, clear           | soft blue/green accents, sparse grid              |
| Medium | connected, thoughtful | amber/violet accents, denser grid                 |
| Hard   | intense, elegant      | deep purple/red-orange accents, stronger contrast |

Difficulty may affect:

- border color
- grid tint
- background glow
- highlight color
- corner marker
- intro pulse
- final answer frame

Avoid loud labels. Difficulty should be felt through atmosphere.

---

# 19. Themes

The tape should support theme presets.

```python
theme="matemium_dark"
theme="matemium_light"
theme="paper_light"
theme="technical_dark"
```

A theme should define:

```python
TapeTheme(
    background_color,
    grid_color,
    frame_color,
    text_color,
    math_color,
    accent_color,
    muted_color,
    note_colors,
    font,
    math_font,
    stroke_widths,
    animation_defaults
)
```

---

# 20. Animation Events

Every meaningful action should be recorded as a `TapeEvent`.

```python
TapeEvent(
    id,
    type,
    target,
    animation,
    start_state=None,
    end_state=None,
    run_time=None,
    metadata={}
)
```

Example:

```python
TapeEvent(
    type="add_math",
    target_row=4,
    animation="write",
    run_time=0.8,
    metadata={
        "latex": r"x^2 - 5x + 6 = (x-2)(x-3)"
    }
)
```

Events enable:

- replay
- partial replay
- debugging
- timeline export
- alternate video pacing

---

# 21. Tape State

A `TapeState` represents the tape at a specific moment.

```python
TapeState(
    name,
    visible_rows,
    hidden_rows,
    highlighted_targets,
    scroll_offset,
    active_row_index,
    scale,
    viewport_center_y,
    metadata={}
)
```

## State methods

```python
tape.capture_state(name)
tape.restore_state(name)
tape.list_states()
```

Example:

```python
tape.capture_state("after_factoring")
tape.restore_state("after_factoring")
```

This is needed for reanimation and frozen snapshots.

---

# 22. Reanimation

The tape should support replaying content.

## 22.1 Required methods

```python
tape.replay()
tape.replay_from(state_name)
tape.replay_range(start_event, end_event)
tape.reanimate_row(row_or_anchor)
tape.reanimate_highlight(target)
```

## 22.2 Prebuild then replay

The creator should be able to create the full tape without animation:

```python
tape.add_problem("Solve...", animate=False)
tape.add_observation("Notice the structure.", animate=False)
tape.add_math(r"x^2 - 5x + 6", animate=False)
tape.add_math(r"(x-2)(x-3)", animate=False)

tape.replay()
```

This allows deterministic layout before playback.

## 22.3 Why this matters

One solution can become:

- a full reel
- a fast recap
- a slow explainer
- a thumbnail scene
- a static summary
- a later callback in another video

---

# 23. Freezing and Snapshots

The tape should support freezing any meaningful state into a static Manim object.

Important distinction:

```text
Freeze = returns a Manim VGroup
Export = writes an external file
```

---

## 23.1 Freeze current view

```python
frozen = tape.freeze_current_view()
```

Returns a static `VGroup` representing what the viewer currently sees.

Use case:

```python
mini_memory = tape.freeze_current_view()
self.play(mini_memory.animate.scale(0.35).to_corner(UL))
```

---

## 23.2 Freeze full tape

```python
full = tape.freeze_full_tape()
```

Returns the complete solution tape as a static `VGroup`.

Use case:

```python
full = tape.freeze_full_tape()
self.play(full.animate.scale(0.45).move_to(ORIGIN))
```

---

## 23.3 Freeze selected rows

```python
key_steps = tape.freeze_rows(["given", "factored_form", "answer"])
```

Returns a static group of selected rows.

Useful for compressed recap scenes.

---

## 23.4 Freeze named state

```python
snapshot = tape.freeze_state("after_zero_product_rule")
```

Returns the tape exactly as it looked when that state was captured.

---

## 23.5 Snapshot types

| Type                 | Meaning                           |
| -------------------- | --------------------------------- |
| `viewport_snapshot`  | Only what is visible in the frame |
| `full_tape_snapshot` | Entire written tape               |
| `rows_snapshot`      | Selected rows                     |
| `state_snapshot`     | Tape at a named captured state    |

---

# 24. Export

The tool should eventually support external export.

## Required export methods

```python
tape.export_current_view(path)
tape.export_full_tape(path)
tape.export_state(path, state_name)
```

Possible formats:

```python
"png"
"svg"
"pdf"
```

MVP should prioritize PNG.

## Full-tape export use case

At the end of a video:

1. final answer appears
2. tape zooms out
3. whole reasoning path is revealed
4. full tape is exported as vertical image
5. image can be shared as a post, story, or recap card

---

# 25. Whole-Tape Reveal

## Method

```python
tape.reveal_full_tape(
    emphasize_anchors=None,
    fade_helper_notes=True,
    run_time=None
)
```

## Behavior

1. pause after conclusion
2. clear temporary highlights
3. zoom or scale tape to fit
4. show full solution path
5. emphasize key anchors
6. final answer receives strong frame
7. optional share-card version appears

This should feel like a satisfying final “look what we built” moment.

---

# 26. Animation Rules

## 26.1 Default row animations

| Row type      | Default animation             |
| ------------- | ----------------------------- |
| `problem`     | fade + slight scale           |
| `observation` | write text + soft marker      |
| `math`        | Write or TransformMatchingTex |
| `note`        | slide/fade from side          |
| `concept`     | card pop-in                   |
| `check`       | checkmark + write             |
| `conclusion`  | frame + glow + pause          |

---

## 26.2 Timing presets

```python
pace="fast"
pace="normal"
pace="slow"
```

Default for short reels:

```python
pace="normal_fast"
```

Individual methods should still accept:

```python
run_time=...
```

---

## 26.3 Motion principles

- smooth but not slow
- no unexpected jumps
- callbacks should feel intentional
- final reveal should be satisfying
- highlights should guide attention, not decorate
- animation should never make the math harder to read

---

# 27. Static vs Animated Object Behavior

Every row should be able to exist in two modes:

```python
static
animated
```

A row created with `animate=False` should still be:

- positioned
- registered
- anchorable
- freezable
- replayable later

A row created with `animate=True` should do all of the above plus play its entrance animation.

This is central to reliable production.

---

# 28. MVP Scope

The first version should be intentionally focused.

## MVP should include

```python
SolutionTape(...)
add_problem(...)
add_text(...)
add_math(...)
add_note(...)
add_observation(...)
add_conclusion(...)

add_anchor(...)
scroll_to(...)
scroll_to_current(...)
return_to_current(...)

highlight(...)
clear_highlights(...)
callback_to(...)

capture_state(...)
restore_state(...)
freeze_current_view(...)
freeze_full_tape(...)

replay()
```

## MVP can postpone

```python
advanced export
SVG/PDF export
true camera zoom
advanced TransformMatchingTex
diagram layout engine
multi-column layout
timeline editor
voiceover synchronization
automatic subtitle timing
complex clipping masks
```

The MVP should prove:

1. we can write a solution line by line
2. the tape scrolls naturally
3. previous ideas can be revisited
4. rows can be highlighted
5. states can be captured
6. frozen static tape objects can be created
7. the full tape can be revealed at the end

---

# 29. Reliability Requirements

The system should be robust enough for repeated content production.

## Requirements

- no manual y-positioning for ordinary rows
- deterministic layout
- rows stored in data model
- anchors stored by name
- events recorded
- states capturable
- scroll offset tracked
- freeze functions return independent copies
- repeated replay should not corrupt layout
- hidden/visible state should be restorable
- final full tape should not depend on current viewport only

---

# 30. Implementation Strategy

Recommended first implementation strategy:

## Use a fixed viewport

The scene frame stays fixed.

## Move the tape group

The tape content moves up and down behind the viewport.

This is more reliable than moving the camera at first.

```text
Fixed camera
│
└── moving tape VGroup
```

## Avoid true clipping in MVP

Manim clipping can become complicated. For MVP, we can use:

- background panel
- frame overlay
- careful positioning
- optional masking later

True viewport clipping can be added later.

## Use focus cards for magnification

Instead of zooming the whole camera:

```python
tape.focus_card(target)
```

This duplicates a target row and enlarges it temporarily.

---

# 31. Suggested File Structure

```text
matemium/
│
├── tape/
│   ├── __init__.py
│   ├── solution_tape.py
│   ├── tape_model.py
│   ├── tape_row.py
│   ├── tape_state.py
│   ├── tape_event.py
│   ├── tape_theme.py
│   ├── tape_view.py
│   └── tape_playback.py
│
├── themes/
│   ├── matemium_dark.py
│   ├── matemium_light.py
│   └── difficulty.py
│
└── examples/
    ├── factoring_example.py
    ├── callback_example.py
    └── freeze_state_example.py
```

---

# 32. Example: State and Freezing Workflow

```python
class TapeStateExample(Scene):
    def construct(self):
        tape = SolutionTape(self, difficulty="medium")

        tape.add_problem(r"Solve: 2x + 3 = 11")
        tape.capture_state("problem_shown")

        tape.add_math(r"2x + 3 = 11", anchor="given")
        tape.add_math(r"2x = 8", reason="subtract 3 from both sides")
        tape.capture_state("after_subtracting")

        tape.add_math(r"x = 4", reason="divide both sides by 2")
        tape.add_conclusion("The answer is", math=r"x=4")

        frozen = tape.freeze_state("after_subtracting")
        self.play(
            frozen.animate.scale(0.4).to_corner(UR)
        )

        tape.reveal_full_tape()
```

This kind of behavior should be supported by design, not added later as a hack.

---

# 33. Example: Prebuild and Replay

```python
class ReplayExample(Scene):
    def construct(self):
        tape = SolutionTape(self, animate_by_default=False)

        tape.add_problem(r"Solve: x^2 - 5x + 6 = 0")
        tape.add_observation("Look for two numbers with product 6 and sum -5.")
        tape.add_math(r"x^2 - 5x + 6 = (x-2)(x-3)", anchor="factored")
        tape.add_math(r"(x-2)(x-3)=0")
        tape.add_math(r"x=2 \quad \text{or} \quad x=3")
        tape.add_conclusion("So the solutions are", math=r"x=2,3")

        tape.replay()
```

This is especially useful for producing multiple video versions from the same solution script.

---

# 34. Open Design Decisions

Before implementation, we should decide:

1. Should the default tape be dark or light?
2. Should we use `MathTex` only, or support mixed `Text + MathTex` rows?
3. Should row labels appear always or only for some row types?
4. Should the MVP use true masking/clipping?
5. Should full-tape export happen inside the same scene or through a separate export scene?
6. Should difficulty be visual-only, or also affect pacing?
7. Should the tape support horizontal branches later?
8. Should we treat every row as immutable after creation, or allow editing rows?

My recommendation:

- Dark theme first.
- Support `Text`, `MathTex`, and mixed rows.
- Row labels optional.
- Skip true clipping in MVP.
- Export later through a separate export scene.
- Difficulty should affect both visuals and pacing slightly.
- Start vertical only.
- Allow row replacement later, but not in MVP.

---

# 35. Final Definition

`SolutionTape` is a reusable Manim system that treats a mathematical solution as a **navigable memory of thought**.

It should allow a creator to:

- build a reasoning path
- animate it step by step
- scroll through it
- revisit earlier ideas
- highlight key insights
- freeze any state
- replay the animation
- reveal the whole solution
- export the final reasoning artifact

The central principle:

> A Matemium solution is not a sequence of equations.
> It is a visible trail of thinking.
