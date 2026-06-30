import { useRef, useState } from "react";

import { sidecarGetPreviewData } from "../api/tauri";
import type { PreviewData, PreviewElement, TimelineAction } from "../api/types";

// =====================================================
// Phase 10 (canonical): manim-web Full 3D World + Special Tape Mode preview
// Renders object graph (root_objects + root_tape) in world space. Special handling for
// TapeObjects (local sheet logic projected onto the tape's world-transformed plane).
// Camera keyframes (ObjectAnchor / TapeScroll / WorldPoint) drive observations.
// =====================================================
import { ManimScene } from "manim-web/react";
import {
  Scene,
  Text,
  MathTex,
  Create,
  FadeIn,
  Write,
  VGroup,
  AnimationGroup,
  Axes,
  Dot,
  // 3D support for Phase 7 full 3D world preview
  Sphere,
  Cube,
  ThreeDAxes,
  Cylinder,
} from "manim-web";

interface LivePreviewProps {
  projectId?: string;
}

export function LiveMeasurementPreview({ projectId }: LivePreviewProps) {
  const [data, setData] = useState<PreviewData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentAction, setCurrentAction] = useState<string>("");
  const [sceneSize, setSceneSize] = useState({ width: 360, height: 640 });
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [is3DMode, setIs3DMode] = useState(false);

  const sceneRef = useRef<Scene | null>(null);
  const rootGroupRef = useRef<any | null>(null); // master container for camera simulation (y-shift)
  const revealedRef = useRef<Map<string, any>>(new Map()); // id -> mob for transforms / reuse

  const load = async () => {
    if (!projectId) {
      setError("No project open");
      return;
    }
    setBusy(true);
    setError(null);
    setCurrentAction("");
    try {
      const result = await sidecarGetPreviewData(projectId);
      setData(result);

      const is3D = result?.coordinate_system === "space" || !!result?.root_objects || !!result?.root_tape;
      setIs3DMode(is3D);

      if (result?.frame_width && result?.frame_height) {
        const fw = result.frame_width;
        const fh = result.frame_height;
        const targetH = is3D ? 480 : 640;  // slightly smaller for 3D visibility
        const targetW = Math.max(280, Math.round((fw / fh) * targetH));
        setSceneSize({ width: targetW, height: targetH });
      }

      // Auto-start replay when scene is ready
      if (sceneRef.current) {
        await playWebPreview(sceneRef.current, result);
      }
    } catch (e: any) {
      setError("Failed to load real preview: " + (e?.message || String(e)));
    } finally {
      setBusy(false);
    }
  };

  function clearAll() {
    const scene = sceneRef.current;
    if (!scene) return;
    try {
      const toRemove: any[] = [];
      revealedRef.current.forEach((m) => toRemove.push(m));
      if (rootGroupRef.current) toRemove.push(rootGroupRef.current);
      if (toRemove.length) scene.remove(...toRemove);
    } catch {}
    revealedRef.current.clear();
    rootGroupRef.current = null;
    setCurrentAction("");
  }

  // Build a manim-web mobject from the rich Python element spec.
  // Phase 10: full 3D world support + special tape mode.
  // Handles world_transform for 3D placement, and special logic for tapes.
  function createMobjectFromSpec(el: PreviewElement | TimelineAction, fw: number, fh: number): any {
    const type = el.type;
    const spec = (el as any).spec || (el as any).raw_content || el.content || {};
    const wt = (el as any).world_transform || (el as any).transform || null;

    // === 3D object types (Phase 7) ===
    if (type === "Solid3D" || type === "ThreeDGraph" || type === "Surface") {
      // Basic 3D primitives using manim-web 3D mobjects
      let mob3d: any;
      if (type === "Solid3D") {
        const shape = (spec.shape || "cube").toLowerCase();
        if (shape === "sphere") mob3d = new Sphere({ radius: 0.5 });
        else if (shape === "cylinder") mob3d = new Cylinder({ radius: 0.5, height: 1 });
        else mob3d = new Cube({ sideLength: 1 });
      } else {
        // Fallback for graphs/surfaces: use a plane or axes
        mob3d = new ThreeDAxes({ xRange: [-2,2], yRange: [-2,2], zRange: [-2,2] });
      }
      if (wt && wt.position) {
        mob3d.moveTo([wt.position[0] || 0, wt.position[1] || 0, wt.position[2] || 0]);
      }
      if (wt && wt.rotation) {
        const [rx, ry, rz] = wt.rotation;
        if (rx) (mob3d as any).rotate(rx * Math.PI / 180, [1,0,0]);
        if (ry) (mob3d as any).rotate(ry * Math.PI / 180, [0,1,0]);
        if (rz) (mob3d as any).rotate(rz * Math.PI / 180, [0,0,1]);
      }
      return mob3d;
    }

    // === Custom high-level types ===
    if (type === "QuadraticPlot" || type === "QuadraticPlotPair") {
      return makeQuadraticPlotFromSpec(spec, el);
    }

    // Future: add GridBoard, etc.

    const raw = typeof el.content === "string" ? el.content.trim() : "";
    const isMath = !!(el.is_math || type?.toLowerCase().includes("math") || raw.includes("\\") || raw.includes("frac") || raw.includes("^"));

    let mob: any;

    if (isMath || type === "MathTex") {
      const latex = raw.replace(/^\$+|\$+$/g, "").replace(/\\\\/g, "\\");
      mob = new MathTex({ latex, fontSize: 0.85, displayMode: true });
    } else if (el.runs && el.runs.length > 1) {
      // Sophisticated rich text
      const children: any[] = [];
      let xCursor = 0;
      for (const run of el.runs) {
        const style = run.style || {};
        const t = new Text({
          text: run.text || "",
          fontSize: 17,
          color: style.color || "#e8eaed",
          ...(style.bold ? { fontWeight: 700 } : {}),
        });
        t.moveTo([xCursor + (t.getWidth?.() || 0) / 2, 0, 0]);
        xCursor += (t.getWidth?.() || (run.text?.length || 0) * 0.18) + 0.06;
        children.push(t);
      }
      mob = new VGroup(...children);
    } else {
      // Generic fallback
      const s: any = (el as any).spec || (el as any).raw_content || {};
      const label = s.formula || s.label || raw || el.type || el.id || "element";
      const box = new Text({ text: label, fontSize: 15, color: "#ddd" } as any);

      if (s.a !== undefined || s.rows !== undefined || s.parts) {
        const hint = new Text({ text: `[${el.type}]`, fontSize: 11, color: "#888" } as any);
        const g = new VGroup(box, hint);
        try { (hint as any).moveTo([0, -0.35, 0]); } catch {}
        mob = g;
      } else {
        mob = box;
      }
    }

    // Phase 7: apply world_transform for 3D placement if present
    const pos = (el as any).canvas_position || [el.x || 0, el.y || 0, (el as any).z || 0];
    let targetPos = [pos[0], pos[1], pos[2] || 0];
    if (wt && wt.position) {
      targetPos = [wt.position[0] || pos[0], wt.position[1] || pos[1], wt.position[2] || pos[2] || 0];
    }
    mob.moveTo(targetPos);

    if (wt && wt.rotation) {
      const [rx, ry, rz] = wt.rotation;
      if (rx && typeof (mob as any).rotate === "function") (mob as any).rotate(rx * Math.PI / 180, [1,0,0]);
      if (ry && typeof (mob as any).rotate === "function") (mob as any).rotate(ry * Math.PI / 180, [0,1,0]);
      if (rz && typeof (mob as any).rotate === "function") (mob as any).rotate(rz * Math.PI / 180, [0,0,1]);
    }
    const s = (el as any).static_scale || (wt && wt.scale) || 1;
    if (s && s !== 1 && typeof (mob as any).scale === "function") {
      (mob as any).scale(s);
    }

    return mob;
  }

  // Re-implementation of Python's make_quadratic_plot using manim-web primitives.
  // This prevents the dict text box problem for QuadraticPlot elements.
  function makeQuadraticPlotFromSpec(spec: any, el: any): any {
    const a = Number(spec.a ?? 1);
    const b = Number(spec.b ?? 0);
    const c = Number(spec.c ?? 0);
    const xRange: [number, number] = Array.isArray(spec.x_range) ? spec.x_range : [-3, 3];
    const color = spec.color || "#5eb3ff";
    const xStart = Number(spec.x_start ?? 0);

    const plotW = Number(spec.plot_width ?? spec.width ?? 2.8);
    const plotH = Number(spec.plot_height ?? 2.0);

    // Approximate y range like the Python version
    const xs = Array.from({ length: 50 }, (_, i) => xRange[0] + (i / 49) * (xRange[1] - xRange[0]));
    const ys = xs.map((x) => a * x * x + b * x + c);
    let yMin = Math.min(...ys);
    let yMax = Math.max(...ys);
    const pad = Math.max(0.7, (yMax - yMin) * 0.22);
    yMin -= pad;
    yMax += pad;

    const axes = new Axes({
      xRange: [xRange[0], xRange[1], 1],
      yRange: [yMin, yMax, Math.max(1, Math.round((yMax - yMin) / 3))],
      xLength: plotW * 0.82,
      yLength: plotH * 0.62,
      axisConfig: { color: "#666666", strokeWidth: 2, includeTip: false },
    } as any);

    // Plot curve
    let curve: any = null;
    try {
      curve = (axes as any).plot((x: number) => a * x * x + b * x + c, { xRange, color, strokeWidth: 3 });
    } catch (e) {
      // crude polyline fallback
      const pts = xs.map((x) => (axes as any).c2p(x, a * x * x + b * x + c));
      // @ts-ignore
      curve = new (Axes as any).prototype.constructor || null; // avoid crash
    }

    // Trace dot
    const x0 = Math.max(xRange[0], Math.min(xRange[1], xStart));
    const y0 = a * x0 * x0 + b * x0 + c;
    const dot = new Dot({ radius: 0.07, color: "#ffdd66" } as any);
    try {
      (dot as any).moveTo((axes as any).c2p(x0, y0));
    } catch {}

    const formulaStr = (spec.formula || `y=${a}x^{2}+${b}x+${c}`).replace(/\s/g, "");
    const formula = new MathTex({ latex: formulaStr, fontSize: 0.36 });
    try { (formula as any).nextTo(axes, "DOWN", 0.18); } catch {}

    const group = new VGroup(axes, curve || dot, dot, formula);

    // Keep references so PlotTrace actions can animate the dot
    (group as any)._quad = { axes, dot, a, b, c, xRange };

    const pos = (el as any).canvas_position || [el.x || 0, el.y || 0, 0];
    group.moveTo(pos);

    if (el.static_scale && el.static_scale !== 1) (group as any).scale(el.static_scale);

    return group;
  }

  // Map Python entry animation names to manim-web equivalents
  function makeEntryAnim(mob: any, animSpec?: { type: string; run_time: number; kwargs?: any }) {
    const atype = (animSpec?.type || "write").toLowerCase();
    const rt = (animSpec?.run_time || 0.9) / playbackSpeed;

    if (atype.includes("write") || atype.includes("tex")) return new Write(mob, { runTime: rt });
    if (atype.includes("fade") || atype.includes("appear")) return new FadeIn(mob, { runTime: rt });
    if (atype.includes("grow") || atype.includes("create") || atype.includes("draw")) return new Create(mob, { runTime: rt });
    return new FadeIn(mob, { runTime: rt });
  }

  async function simulateCamera(scene: Scene, targetY: number, runTime: number) {
    // Phase 7: Best-effort 3D camera / sheet simulation.
    // Supports free 3D navigation and tape-specific local scroll.
    const rt = Math.max(0.2, runTime / playbackSpeed);

    const cam: any = (scene as any).camera;
    if (cam && typeof cam.moveTo === "function") {
      try {
        const current = cam.getPosition?.() || [0, 0, 10];
        // In 3D mode, move in world coords; for tape, local handled in play loop
        await Promise.resolve(cam.moveTo([current[0] || 0, targetY * 0.6, current[2] || 10]));
        return;
      } catch {}
    }

    // Fallback: shift master group (works for both 2D tape and 3D world)
    if (rootGroupRef.current && typeof rootGroupRef.current.shift === "function") {
      const delta = (rootGroupRef.current.getY?.() || 0) - targetY * 0.55;
      rootGroupRef.current.shift([0, -delta * 0.9, 0]);
      await new Promise((r) => setTimeout(r, rt * 1000));
    } else {
      await new Promise((r) => setTimeout(r, rt * 700));
    }
  }

  async function playWebPreview(scene: Scene, preview: PreviewData | null) {
    if (!preview) {
      // Demo 3D
      clearAll();
      const title = new Text({ text: "Matemium 3D", fontSize: 42, color: "#fff" });
      const eq = new MathTex({ latex: "e^{i\\pi} + 1 = 0", fontSize: 1.1 });
      scene.add(title); scene.add(eq);
      title.moveTo([0, 3, 0]); eq.moveTo([0, 0, 0]);
      await scene.play(new Write(title, { runTime: 1.2 / playbackSpeed }));
      await scene.play(new Create(eq, { runTime: 1.0 / playbackSpeed }));
      setCurrentAction("Demo complete");
      return;
    }

    clearAll();

    const fw = preview.frame_width ?? 9;
    const fh = preview.frame_height ?? 16;
    const is3D = preview.coordinate_system === "space" || !!preview.root_objects || !!preview.root_tape;
    const actions: TimelineAction[] = preview.timeline && preview.timeline.length > 0
      ? preview.timeline
      : (preview.elements || []).map(e => ({ ...e, kind: "element" } as any));

    // Phase 7: Full 3D world + special tape mode
    const root = new VGroup();
    rootGroupRef.current = root;
    scene.add(root);

    // Render root objects in world space (3D support)
    const rootObjs = preview.root_objects || [];
    for (const obj of rootObjs) {
      if (obj.element) {
        const mob = createMobjectFromSpec(obj.element, fw, fh);
        if (obj.transform && obj.transform.position) {
          mob.moveTo(obj.transform.position);
        }
        if (obj.transform && obj.transform.rotation) {
          const [rx, ry, rz] = obj.transform.rotation;
          if (rx) (mob as any).rotate?.(rx * Math.PI / 180, [1,0,0]);
          if (ry) (mob as any).rotate?.(ry * Math.PI / 180, [0,1,0]);
          if (rz) (mob as any).rotate?.(rz * Math.PI / 180, [0,0,1]);
        }
        root.add(mob);
        revealedRef.current.set(obj.id, mob);
      }
    }

    // Special tape handling: render tape content projected on its plane using local sheet logic
    const tape = preview.root_tape;
    if (tape) {
      const tapeGroup = new VGroup();
      const tapeContent = tape.local_elements || [];
      for (const localEl of tapeContent) {
        const mob = createMobjectFromSpec(localEl, fw, fh);
        // local positions on tape plane
        const lpos = localEl.canvas_position || [localEl.x || 0, localEl.y || 0, localEl.z || 0];
        mob.moveTo(lpos);
        tapeGroup.add(mob);
      }
      // Apply tape's world transform
      const tw = tape.world_transform;
      if (tw && tw.position) {
        tapeGroup.moveTo(tw.position);
      }
      if (tw && tw.rotation) {
        const [rx, ry, rz] = tw.rotation;
        if (rx) (tapeGroup as any).rotate?.(rx * Math.PI / 180, [1,0,0]);
        if (ry) (tapeGroup as any).rotate?.(ry * Math.PI / 180, [0,1,0]);
        if (rz) (tapeGroup as any).rotate?.(rz * Math.PI / 180, [0,0,1]);
      }
      root.add(tapeGroup);
      revealedRef.current.set(tape.id || "root_tape", tapeGroup);
    }

    setIsPlaying(true);

    if (is3D && (scene as any).camera) {
      try {
        (scene as any).camera.use_orthographic_projection = false;
      } catch {}
    }

    // Replay using observations if present (Phase 7), else fall back to sequential
    const observations = preview.observations || actions;

    let i = 0;
    while (i < observations.length) {
      const action = observations[i];
      const kind = action.kind || (action.type === "CanvasElement" ? "element" : action.type || "element");

      setCurrentAction(`${kind}: ${action.id || action.content?.slice(0, 28) || ""}`);

      if (kind === "element" || kind === "CanvasElement") {
        const el = action as PreviewElement;
        if (revealedRef.current.has(el.id)) { i++; continue; }
        const mob = createMobjectFromSpec(el, fw, fh);
        root.add(mob);
        revealedRef.current.set(el.id, mob);
        const animSpec = el.entry_animation;
        const anim = makeEntryAnim(mob, animSpec);
        try { await scene.play(anim); } catch { scene.add(mob); }
      } else if (kind === "flex_group" || action.flex_group) {
        // ... (keep previous flex logic, adapted for 3D if needed)
        const gid = action.flex_group;
        const groupEls: TimelineAction[] = [action];
        let j = i + 1;
        while (j < actions.length) {
          const nxt = actions[j];
          if (nxt.flex_group && nxt.flex_group === gid && !revealedRef.current.has(nxt.id)) {
            groupEls.push(nxt);
            j++;
          } else break;
        }
        const avgY = groupEls.reduce((s, e) => s + ((e.y ?? e.canvas_position?.[1] ?? 0)), 0) / Math.max(1, groupEls.length);
        await simulateCamera(scene, avgY, action.run_time || 0.9);
        for (const gel of groupEls) {
          if (revealedRef.current.has(gel.id)) continue;
          const m = createMobjectFromSpec(gel, fw, fh);
          root.add(m);
          revealedRef.current.set(gel.id, m);
          try { await scene.play(makeEntryAnim(m, gel.entry_animation)); } catch { scene.add(m); }
        }
        i = j - 1;
      } else if (kind === "CameraMove" || kind === "CameraKeyframe") {
        const targetY = (action.target_position?.[1] ?? action.y ?? (action.target && action.target.local_y) ?? 0);
        const rt = action.run_time || action.duration || 1.2;
        await simulateCamera(scene, targetY, rt);
        // For tape targets in 3D: special mode would pan local tape content + adjust outer camera
        if (action.target && action.target.kind === "tape_scroll" && tape) {
          const tapeMob = revealedRef.current.get(tape.id || "root_tape");
          if (tapeMob) {
            // Simulate local scroll on tape group (simplified)
            try { (tapeMob as any).shift?.([0, -targetY * 0.1, 0]); } catch {}
          }
        }
      } else if (kind === "CameraFocus" || kind === "CameraInspect") {
        const targetY = action.target_position?.[1] ?? 0;
        await simulateCamera(scene, targetY, action.run_time || 1.0);
      } else if (kind === "TransformElement" || kind === "SolidRotate" || kind === "SolidLift") {
        const targetMob = revealedRef.current.get(action.element_id || action.source_id || "");
        if (targetMob && typeof (targetMob as any).animate === "object") {
          const rt = (action.run_time || 0.8) / playbackSpeed;
          try {
            await scene.play((targetMob as any).animate?.scale(1.15)?.set_run_time(rt * 0.4));
            await scene.play((targetMob as any).animate?.scale(1 / 1.15)?.set_run_time(rt * 0.4));
          } catch {}
        }
      } else if (kind === "PlotTrace") {
        // ... keep previous, works in 3D too
        const targetGroup = revealedRef.current.get(action.element_id || "");
        const quad = targetGroup && (targetGroup as any)._quad;
        if (quad && quad.dot && quad.axes) {
          const { dot, axes, a, b, c, xRange } = quad;
          const xFrom = Number(action.x_from ?? -2);
          const xTo = Number(action.x_to ?? 2);
          const rt = (action.run_time || 2.5) / playbackSpeed;
          const steps = 28;
          const dx = (xTo - xFrom) / steps;
          for (let s = 0; s <= steps; s++) {
            const xv = xFrom + s * dx;
            const yv = a * xv * xv + b * xv + c;
            try { (dot as any).moveTo((axes as any).c2p(xv, yv)); } catch {}
            await new Promise(r => setTimeout(r, (rt * 1000) / steps));
          }
        } else {
          await new Promise(r => setTimeout(r, 220 / playbackSpeed));
        }
      } else {
        await new Promise(r => setTimeout(r, 120 / playbackSpeed));
      }

      i++;
      await new Promise(r => setTimeout(r, 60 / playbackSpeed));
    }

    setCurrentAction(is3D ? "3D World Preview complete (manim-web)" : "Preview complete (manim-web)");
    setIsPlaying(false);
  }

  const handleSceneReady = (scene: Scene) => {
    sceneRef.current = scene;
    if (data) {
      void playWebPreview(scene, data);
    } else {
      void playWebPreview(scene, null);
    }
  };

  const replay = () => {
    if (sceneRef.current) {
      void playWebPreview(sceneRef.current, data);
    }
  };

  const reset = () => {
    clearAll();
    setCurrentAction("");
    if (sceneRef.current && data) {
      // re-instantiate a clean scene by forcing remount + replay
      const freshData = { ...data };
      setData(freshData);
    } else if (sceneRef.current) {
      void playWebPreview(sceneRef.current, null);
    }
  };

  return (
    <div className="live-preview" style={{ padding: 8, display: "flex", flexDirection: "column", height: "100%", background: "#0b0d12" }}>
      <div style={{ display: "flex", gap: 6, marginBottom: 6, alignItems: "center", flexWrap: "wrap", fontSize: 12 }}>
        <button onClick={load} disabled={busy || !projectId}>
          {busy ? "Loading..." : "Load + Play from project"}
        </button>
        <button onClick={replay} disabled={busy || !sceneRef.current || isPlaying}>
          Replay
        </button>
        <button onClick={reset} disabled={busy || !sceneRef.current}>
          Reset
        </button>

        <label style={{ marginLeft: 12 }}>
          speed:
          <input
            type="range"
            min={0.5}
            max={3}
            step={0.25}
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
            style={{ width: 90, verticalAlign: "middle", marginLeft: 4 }}
          />
          {playbackSpeed.toFixed(2)}×
        </label>

        <span style={{ marginLeft: "auto", color: "#9aa0a6" }}>
          {is3DMode ? "manim-web Full 3D + Tape" : "manim-web Sheet"}
        </span>
        <button onClick={() => { setData(null); if (sceneRef.current) void playWebPreview(sceneRef.current, null); }}>
          {is3DMode ? "3D Demo" : "Demo"}
        </button>
      </div>

      {error && <div style={{ color: "#ff8a8a", fontSize: 11, marginBottom: 4 }}>{error}</div>}

      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", background: "#0a0a0f", border: "1px solid #232a38", borderRadius: 4, overflow: "hidden", minHeight: 220, position: "relative" }}>
        <ManimScene
          key={`mw-${data ? "script" : "demo"}-${sceneSize.width}x${sceneSize.height}-${is3DMode ? "3d" : "2d"}`}
          width={sceneSize.width}
          height={sceneSize.height}
          backgroundColor={data?.background_color || "#0a0a0f"}
          onSceneReady={handleSceneReady}
        />

        {currentAction && (
          <div style={{ position: "absolute", bottom: 6, left: 8, fontSize: 10, background: "rgba(0,0,0,0.6)", padding: "1px 6px", borderRadius: 3, color: "#aaa" }}>
            {currentAction}
          </div>
        )}
      </div>

      <div style={{ fontSize: 10, color: "#666", marginTop: 5, lineHeight: 1.3 }}>
        Phase 7: Full 3D world + special Tape mode in manim-web. Objects placed with world_transforms.
        Tape content rendered on transformed plane using local sheet logic. Camera observations replayed (3D orbit or tape scroll+reveal).
        Pure sheet projects still use high-fidelity 2D mode.
      </div>
    </div>
  );
}
