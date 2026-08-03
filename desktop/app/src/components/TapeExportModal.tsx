import { useEffect, useMemo, useState } from "react";

import * as api from "../api/tauri";
import type {
  TapeExportFormat,
  TapeExportResult,
  TapeSummary,
} from "../api/types";
import { formatError } from "../utils/errors";

type ResolutionChoice = "native" | "2160" | "4096";

interface TapeExportModalProps {
  open: boolean;
  projectId: string;
  scenes: string[];
  scene: string;
  busy: boolean;
  onSceneChange: (scene: string) => void;
  onClose: () => void;
  onPrepare: () => Promise<void>;
  onExport: (options: {
    scene: string;
    tapeId: string;
    format: TapeExportFormat;
    highResHeight: number | null;
  }) => Promise<TapeExportResult>;
  onPreview: (path: string) => void;
  onStatus: (message: string, kind: "ok" | "error") => void;
}

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  const amount = value / 1024 ** index;
  return `${amount >= 10 || index === 0 ? amount.toFixed(0) : amount.toFixed(1)} ${units[index]}`;
}

function tapeSubtitle(tape: TapeSummary): string {
  const elements = `${tape.element_count} element${tape.element_count === 1 ? "" : "s"}`;
  const span = tape.content_span > 0 ? ` · ${tape.content_span.toFixed(1)} units long` : "";
  return `${elements}${span}`;
}

export function TapeExportModal({
  open,
  projectId,
  scenes,
  scene,
  busy,
  onSceneChange,
  onClose,
  onPrepare,
  onExport,
  onPreview,
  onStatus,
}: TapeExportModalProps) {
  const [localScenes, setLocalScenes] = useState<string[]>(scenes);
  const [activeScene, setActiveScene] = useState(scene);
  const [tapes, setTapes] = useState<TapeSummary[]>([]);
  const [selectedTapeId, setSelectedTapeId] = useState("");
  const [format, setFormat] = useState<TapeExportFormat>("png");
  const [resolution, setResolution] = useState<ResolutionChoice>("native");
  const [loadingScenes, setLoadingScenes] = useState(false);
  const [loadingTapes, setLoadingTapes] = useState(false);
  const [sceneReady, setSceneReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TapeExportResult | null>(null);

  useEffect(() => {
    if (!open || !projectId) return;
    let cancelled = false;
    setLoadingScenes(true);
    setSceneReady(false);
    setError(null);
    setResult(null);
    setFormat("png");
    setResolution("native");

    void (async () => {
      try {
        await onPrepare();
        const response = await api.sidecarListScenes(projectId);
        if (cancelled) return;
        const fresh = response.scenes ?? [];
        setLocalScenes(fresh);
        const nextScene = fresh.includes(scene) ? scene : fresh[0] ?? scene;
        setActiveScene(nextScene);
        setSceneReady(true);
        if (nextScene && nextScene !== scene) onSceneChange(nextScene);
      } catch (cause) {
        if (!cancelled) setError(formatError(cause));
      } finally {
        if (!cancelled) setLoadingScenes(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [open, projectId, scene, onPrepare, onSceneChange]);

  useEffect(() => {
    if (!open || !projectId || !activeScene || !sceneReady || loadingScenes) return;
    let cancelled = false;
    setLoadingTapes(true);
    setError(null);
    setResult(null);

    void api.sidecarListTapes(projectId, activeScene)
      .then((response) => {
        if (cancelled) return;
        const populated = (response.tapes ?? []).filter((tape) => tape.element_count > 0);
        setTapes(populated);
        const preferred =
          response.default_tape_id &&
          populated.some((tape) => tape.id === response.default_tape_id)
            ? response.default_tape_id
            : populated[0]?.id ?? "";
        setSelectedTapeId(preferred);
      })
      .catch((cause) => {
        if (!cancelled) {
          setTapes([]);
          setSelectedTapeId("");
          setError(formatError(cause));
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingTapes(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, projectId, activeScene, sceneReady, loadingScenes]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, busy, onClose]);

  const selectedTape = useMemo(
    () => tapes.find((tape) => tape.id === selectedTapeId) ?? null,
    [tapes, selectedTapeId],
  );
  const loading = loadingScenes || loadingTapes;
  const canExport = !busy && !loading && !error && Boolean(activeScene && selectedTapeId);

  if (!open) return null;

  const changeScene = (nextScene: string) => {
    setActiveScene(nextScene);
    setSelectedTapeId("");
    setTapes([]);
    setResult(null);
    setSceneReady(true);
    onSceneChange(nextScene);
  };

  const startExport = async () => {
    if (!canExport) return;
    setError(null);
    setResult(null);
    try {
      const exported = await onExport({
        scene: activeScene,
        tapeId: selectedTapeId,
        format,
        highResHeight: resolution === "native" ? null : Number(resolution),
      });
      setResult(exported);
    } catch (cause) {
      setError(formatError(cause));
    }
  };

  const revealResult = async () => {
    if (!result) return;
    try {
      await api.projectRevealOutput(projectId, result.path);
    } catch (cause) {
      onStatus(formatError(cause), "error");
    }
  };

  return (
    <div
      className="modal-backdrop tape-export-backdrop"
      onClick={() => {
        if (!busy) onClose();
      }}
    >
      <div
        className="modal tape-export-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="tape-export-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="tape-export-header">
          <div className="tape-export-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M7 3.5h10v4H7zM5 7.5h14v13H5z" />
              <path d="M8 11h8M8 14h6M8 17h7" />
            </svg>
          </div>
          <div>
            <div className="tape-export-eyebrow">Study document</div>
            <h2 id="tape-export-title">Export full tape</h2>
            <p>
              Create an upright, uncropped document independent of the video camera.
            </p>
          </div>
          <button
            type="button"
            className="tape-export-close"
            aria-label="Close tape export"
            disabled={busy}
            onClick={onClose}
          >
            ×
          </button>
        </header>

        {result ? (
          <section className="tape-export-success">
            <div className="tape-export-success-icon" aria-hidden="true">✓</div>
            <div className="tape-export-success-copy">
              <span>Export complete</span>
              <strong>{result.path.split(/[/\\]/).pop()}</strong>
              <small>
                {result.pixel_width && result.pixel_height
                  ? `${result.pixel_width} × ${result.pixel_height} · `
                  : ""}
                {formatBytes(result.size_bytes)} · {result.format.toUpperCase()}
              </small>
            </div>
            <div className="tape-export-success-actions">
              {result.format === "png" ? (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => onPreview(result.path)}
                >
                  Preview
                </button>
              ) : null}
              <button type="button" className="btn" onClick={() => void revealResult()}>
                Show in folder
              </button>
            </div>
          </section>
        ) : (
          <>
            <div className="tape-export-content">
              <section className="tape-export-section">
                <div className="tape-export-section-heading">
                  <span className="tape-export-step">1</span>
                  <div>
                    <h3>Choose content</h3>
                    <p>The selected scene is inspected directly from your saved code.</p>
                  </div>
                </div>

                <label htmlFor="tape-export-scene">Scene</label>
                <select
                  id="tape-export-scene"
                  value={activeScene}
                  disabled={loadingScenes || busy}
                  onChange={(event) => changeScene(event.target.value)}
                >
                  {localScenes.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>

                <div className="tape-export-label-row">
                  <span>Tape</span>
                  {!loadingTapes && tapes.length > 1 ? (
                    <small>{tapes.length} populated tapes found</small>
                  ) : null}
                </div>

                {loading ? (
                  <div className="tape-export-loading">
                    <span />
                    <div>
                      <b>Inspecting scene…</b>
                      <small>Finding authored tapes and document bounds</small>
                    </div>
                  </div>
                ) : tapes.length > 0 ? (
                  <div className={`tape-picker ${tapes.length === 1 ? "is-single" : ""}`}>
                    {tapes.map((tape) => (
                      <button
                        type="button"
                        key={tape.id}
                        className={`tape-picker-card ${selectedTapeId === tape.id ? "is-selected" : ""}`}
                        aria-pressed={selectedTapeId === tape.id}
                        onClick={() => {
                          setSelectedTapeId(tape.id);
                          setResult(null);
                        }}
                      >
                        <span className="tape-picker-radio" />
                        <span className="tape-picker-copy">
                          <strong>{tape.title}</strong>
                          <span>{tape.id}</span>
                          <small>{tapeSubtitle(tape)}</small>
                        </span>
                        {tape.is_root ? <em>Root</em> : null}
                      </button>
                    ))}
                  </div>
                ) : !error ? (
                  <div className="tape-export-empty">
                    No populated tapes were found in this scene.
                  </div>
                ) : null}
              </section>

              <section className="tape-export-section">
                <div className="tape-export-section-heading">
                  <span className="tape-export-step">2</span>
                  <div>
                    <h3>Export settings</h3>
                    <p>Natural tape proportions are always preserved.</p>
                  </div>
                </div>

                <div className="tape-export-options-grid">
                  <div>
                    <div className="tape-export-label-row"><span>File format</span></div>
                    <div className="tape-export-segments">
                      {(["png", "pdf"] as TapeExportFormat[]).map((item) => (
                        <button
                          type="button"
                          key={item}
                          className={format === item ? "is-active" : ""}
                          onClick={() => setFormat(item)}
                        >
                          <strong>{item.toUpperCase()}</strong>
                          <small>{item === "png" ? "Previewable image" : "Printable document"}</small>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="tape-export-label-row"><span>Resolution</span></div>
                    <select
                      value={resolution}
                      onChange={(event) => setResolution(event.target.value as ResolutionChoice)}
                    >
                      <option value="native">Native detail · recommended</option>
                      <option value="2160">Compact · 2160 px tall</option>
                      <option value="4096">High detail · 4096 px tall</option>
                    </select>
                    <p className="tape-export-option-hint">
                      Native detail keeps text equally sharp on short and long tapes.
                    </p>
                  </div>
                </div>

                {selectedTape ? (
                  <div className="tape-export-summary">
                    <span>Document</span>
                    <strong>{selectedTape.title}</strong>
                    <small>
                      Natural aspect · {format.toUpperCase()} ·{" "}
                      {resolution === "native" ? "native detail" : `${resolution}px tall`}
                    </small>
                  </div>
                ) : null}
              </section>
            </div>

            {error ? (
              <div className="tape-export-error" role="alert">
                <strong>Couldn’t prepare the export</strong>
                <span>{error}</span>
              </div>
            ) : null}
          </>
        )}

        <footer className="tape-export-footer">
          <div className="tape-export-destination">
            <span>Saved to</span>
            <strong>Project / Renders</strong>
          </div>
          <div className="tape-export-footer-actions">
            <button type="button" className="btn" disabled={busy} onClick={onClose}>
              {result ? "Done" : "Cancel"}
            </button>
            {!result ? (
              <button
                type="button"
                className="btn btn-primary tape-export-submit"
                disabled={!canExport}
                onClick={() => void startExport()}
              >
                {busy ? (
                  <>
                    <span className="tape-export-spinner" />
                    Exporting…
                  </>
                ) : (
                  "Export tape"
                )}
              </button>
            ) : null}
          </div>
        </footer>
      </div>
    </div>
  );
}
