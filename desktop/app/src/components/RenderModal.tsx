import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";

import * as api from "../api/tauri";
import type { CheckResult, VideoOrientation } from "../api/types";
import { formatError } from "../utils/errors";

interface RenderModalProps {
  open: boolean;
  projectId: string;
  defaultOutputDir: string;
  scenes: string[];
  scene: string;
  quality: string;
  orientation: VideoOrientation;
  outputDir: string | null;
  lintErrors: number;
  lintWarnings: number;
  busy: boolean;
  onSceneChange: (scene: string) => void;
  onQualityChange: (quality: string) => void;
  onOrientationChange: (orientation: VideoOrientation) => void;
  onOutputDirChange: (outputDir: string | null) => void;
  onClose: () => void;
  onPrepare: () => Promise<void>;
  onRender: () => void;
}

export function RenderModal({
  open: isOpen,
  projectId,
  defaultOutputDir,
  scenes,
  scene,
  quality,
  orientation,
  outputDir,
  lintErrors,
  lintWarnings,
  busy,
  onSceneChange,
  onQualityChange,
  onOrientationChange,
  onOutputDirChange,
  onClose,
  onPrepare,
  onRender,
}: RenderModalProps) {
  const [check, setCheck] = useState<CheckResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [pickingFolder, setPickingFolder] = useState(false);
  const [localScenes, setLocalScenes] = useState<string[]>(scenes);

  useEffect(() => {
    if (!isOpen || !projectId) return;

    let cancelled = false;
    setChecking(true);
    setCheckError(null);

    void (async () => {
      try {
        await onPrepare();
        // Always fetch fresh scenes list so stale "MyScene" from new project metadata doesn't cause issues after overwriting scenes.py
        const listRes = await api.sidecarListScenes(projectId);
        if (cancelled) return;

        const fresh = listRes.scenes || [];
        setLocalScenes(fresh);

        let activeScene = scene;
        if (fresh.length > 0 && !fresh.includes(scene)) {
          activeScene = fresh[0];
          onSceneChange(activeScene);
          // Stop here: the parent will re-render and trigger this effect again with the correct scene
          return;
        }

        const result = await api.sidecarCheck(projectId, activeScene || undefined);
        if (!cancelled) {
          setCheck(result);
        }
      } catch (error) {
        if (!cancelled) {
          setCheck(null);
          setCheckError(formatError(error));
        }
      } finally {
        if (!cancelled) {
          setChecking(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [onPrepare, isOpen, projectId, scene, onSceneChange]);

  if (!isOpen) return null;

  const checkOk = check?.ok === true;
  const canRender = !busy && !checking && lintErrors === 0 && checkOk;
  const effectiveOutputDir = outputDir ?? defaultOutputDir;
  const usingCustomOutput = outputDir != null;

  const handleBrowseOutput = async () => {
    setPickingFolder(true);
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        defaultPath: effectiveOutputDir,
        title: "Choose output folder",
      });
      if (typeof selected === "string" && selected.trim()) {
        onOutputDirChange(selected);
      }
    } catch (error) {
      setCheckError(formatError(error));
    } finally {
      setPickingFolder(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal render-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Render video</h2>
        <p className="modal-hint">
          Choose scene and export settings. The scene is validated automatically before rendering.
        </p>

        <label htmlFor="render-scene">Scene</label>
        <select
          id="render-scene"
          value={localScenes.includes(scene) ? scene : (localScenes[0] || scene)}
          onChange={(e) => onSceneChange(e.target.value)}
        >
          {localScenes.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>

        <label htmlFor="render-format">Format</label>
        <select
          id="render-format"
          value={orientation}
          onChange={(e) => onOrientationChange(e.target.value as VideoOrientation)}
        >
          <option value="portrait">9:16 portrait (Reels)</option>
          <option value="landscape">16:9 landscape (YouTube)</option>
        </select>

        <label htmlFor="render-quality">Quality</label>
        <select
          id="render-quality"
          value={quality}
          onChange={(e) => onQualityChange(e.target.value)}
        >
          <option value="fast_preview">Fast preview — quarter resolution, 10 fps</option>
          <option value="preview">Preview — fast, half resolution</option>
          <option value="low">Low — default</option>
          <option value="medium">Medium</option>
          <option value="high">High — 60 fps</option>
          <option value="final">Final — export quality</option>
        </select>

        <label htmlFor="render-output-dir">Output folder</label>
        <div className="render-output-dir-row">
          <input
            id="render-output-dir"
            type="text"
            readOnly
            value={effectiveOutputDir}
            title={effectiveOutputDir}
          />
          <button
            type="button"
            className="btn"
            disabled={pickingFolder}
            onClick={() => void handleBrowseOutput()}
          >
            {pickingFolder ? "…" : "Browse"}
          </button>
        </div>
        {usingCustomOutput ? (
          <>
            <p className="render-output-hint">
              Also copies to this folder. Preview and partial movies stay in the project workspace.
            </p>
            <button
              type="button"
              className="render-output-reset"
              onClick={() => onOutputDirChange(null)}
            >
              Use project default ({defaultOutputDir})
            </button>
          </>
        ) : (
          <p className="render-output-hint">
            Final video saves to the project renders folder. Manim cache stays in the project
            workspace.
          </p>
        )}

        <div className="render-validation">
          <div className="render-validation-row">
            <span className="render-validation-label">Lint</span>
            {lintErrors > 0 ? (
              <span className="render-validation-bad">
                {lintErrors} error{lintErrors === 1 ? "" : "s"}
                {lintWarnings > 0 ? `, ${lintWarnings} warning${lintWarnings === 1 ? "" : "s"}` : ""}
              </span>
            ) : lintWarnings > 0 ? (
              <span className="render-validation-warn">
                {lintWarnings} warning{lintWarnings === 1 ? "" : "s"}
              </span>
            ) : (
              <span className="render-validation-ok">No issues</span>
            )}
          </div>

          <div className="render-validation-row">
            <span className="render-validation-label">Scene check</span>
            {checking ? (
              <span className="render-validation-pending">Validating…</span>
            ) : checkError ? (
              <span className="render-validation-bad">{checkError}</span>
            ) : checkOk ? (
              <span className="render-validation-ok">
                {check?.scene ?? scene}
                {check?.timeline_length != null ? ` · ${check.timeline_length} steps` : ""}
                {check?.title ? ` · ${check.title}` : ""}
              </span>
            ) : (
              <span className="render-validation-bad">
                {(check?.errors ?? []).map((e: any) => (typeof e === "string" ? e : e?.message || JSON.stringify(e))).join("; ") || "Scene failed validation"}
              </span>
            )}
          </div>
        </div>

        {!checking && check && !check.ok && (check.errors?.length ?? 0) > 0 ? (
          <ul className="render-error-list">
            {(check?.errors ?? []).map((err: any, index: number) => {
              const msg = typeof err === "string" ? err : err?.message || JSON.stringify(err);
              const key = typeof err === "string" ? err : err?.message || index;
              return <li key={`${key}-${index}`}>{msg}</li>;
            })}
          </ul>
        ) : null}

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!canRender}
            onClick={onRender}
          >
            {checking ? "Validating…" : "Start render"}
          </button>
        </div>
      </div>
    </div>
  );
}
