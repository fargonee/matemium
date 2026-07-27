# How Feedback Stabilizes a System

## Project identity

- **Subject:** Engineering
- **Project slug:** `feedback_control`
- **Status:** Landscape flagship preview accepted; final master and independent controls sign-off pending
- **Central question:** How does a system detect a disturbance and correct itself?
- **Primary audience:** General engineering learners and introductory control-systems students
- **Target format:** 16:9 flagship master, approximately 45–60 seconds

## Purpose

Use cruise control as a concrete system to explain closed-loop feedback. The
accepted scene connects a physical disturbance, semantic block diagram, error
signal, PI action, and aligned deterministic time-series plots.

The story should show that useful automation is continuous measurement and correction, not a one-time command.

## Learning outcomes

The viewer should understand:

- the difference between target value and measured output;
- how error is computed;
- how a controller changes the actuator command;
- how an external disturbance propagates through a system;
- why excessive gain can cause overshoot or oscillation;
- how feedback differs from an open-loop command.

## Narrative arc

1. **Set the target:** A car reaches a chosen speed on level ground.
2. **Introduce disturbance:** The road slopes upward and speed begins to drop.
3. **Expose the loop:** Transform the physical scene into setpoint, comparator, controller, plant, sensor, and feedback blocks.
4. **Follow one cycle:** Trace the signal from measured speed to error to throttle correction.
5. **Watch recovery:** Synchronize car behavior, signal values, and speed-over-time plot.
6. **Compare control choices:** Show low gain, useful gain, and excessive gain in aligned plots.
7. **Open versus closed loop:** Briefly remove feedback and repeat the hill disturbance.
8. **Synthesis:** Reconnect the abstract loop to the physical car and broader engineered systems.

## Visual and motion direction

- Maintain fixed colors for setpoint, measured output, error, and control command.
- Animate signal flow directionally through the block diagram.
- Keep the car scene simplified and subordinate to the system explanation.
- Align comparison plots to the same axes and disturbance time.
- Show overshoot and settling with annotations rather than relying on visual inference.
- Use the camera to move between physical, diagrammatic, and quantitative views while preserving continuity.

## Matemium capabilities this project must demonstrate

- system and block diagrams;
- causal signal flow;
- sampled deterministic time-series plots;
- staged physical and abstract representations;
- parameter comparisons;
- animated disturbances and recovery;
- reusable components for blocks, connectors, scopes, and control signals.

## Required source and assets

- Use a documented simplified longitudinal car model.
- Generate response curves deterministically from explicit parameters.
- Keep controller gains and disturbance profiles configurable.
- Use procedural diagrams and vehicle silhouettes; no external media is required.

## Scope boundaries

- Do not claim the simplified model represents production automotive control.
- Do not introduce PID terms until proportional control and feedback are understood.
- Do not compare plots with different axes.
- Do not imply that faster response is always better.
- Avoid dense transfer-function algebra in the main narrative.

## Acceptance criteria

- Every signal in the block diagram has a clear meaning and direction.
- The physical motion and speed plot agree.
- Low, balanced, and excessive gains produce correctly characterized responses.
- The disturbance is introduced at the same time across comparisons.
- Source parameters can be changed without restructuring the scene.
- The project demonstrates Matemium’s ability to explain engineered systems across multiple representations.
