import { useCallback, useEffect, useMemo, useState } from "react";

import * as api from "../api/tauri";
import type { CacheKind, OutputEntry, OutputKind, OutputListResult } from "../api/types";
import { formatBytes } from "../utils/formatBytes";
import { formatError } from "../utils/errors";
import {
  isPreviewableOutput,
  mediaPreviewItemFromPath,
  type MediaPreviewItem,
} from "../utils/mediaPreview";

const KIND_LABELS: Record<string, string> = {
  preview: "Previews",
  video: "Videos",
  partial: "Partial movies",
  tex: "LaTeX cache",
  text: "Text cache",
  image: "Images",
  document: "Documents",
  other: "Other",
};

const KIND_ORDER = ["preview", "video", "image", "document", "partial", "tex", "text", "other"];

const CLEAR_OPTIONS: { kind: CacheKind; label: string }[] = [
  { kind: "partials", label: "Partial movies" },
  { kind: "tex", label: "LaTeX cache" },
  { kind: "texts", label: "Text cache" },
  { kind: "images", label: "Images" },
  { kind: "previews", label: "Preview MP4s" },
  { kind: "videos", label: "All videos" },
  { kind: "all", label: "Everything" },
];

interface OutputsExplorerProps {
  projectId: string;
  busy: boolean;
  refreshToken: number;
  embedded?: boolean;
  onStatus: (message: string, kind?: "ok" | "error") => void;
  onPreviewMedia?: (item: MediaPreviewItem) => void;
}

function groupEntries(entries: OutputEntry[]): Map<string, OutputEntry[]> {
  const groups = new Map<string, OutputEntry[]>();
  for (const entry of entries) {
    const kind = entry.kind || "other";
    const bucket = groups.get(kind) ?? [];
    bucket.push(entry);
    groups.set(kind, bucket);
  }
  return groups;
}

export function OutputsExplorer({
  projectId,
  busy,
  refreshToken,
  embedded = false,
  onStatus,
  onPreviewMedia,
}: OutputsExplorerProps) {
  const [data, setData] = useState<OutputListResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<OutputKind | "all">("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set(KIND_ORDER));

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.projectListOutputs(projectId);
      setData(result);
    } catch (error) {
      onStatus(formatError(error), "error");
    } finally {
      setLoading(false);
    }
  }, [onStatus, projectId]);

  useEffect(() => {
    void refresh();
  }, [projectId, refresh, refreshToken]);

  const filteredEntries = useMemo(() => {
    if (!data) return [];
    if (filter === "all") return data.entries;
    return data.entries.filter((entry) => entry.kind === filter);
  }, [data, filter]);

  const grouped = useMemo(() => groupEntries(filteredEntries), [filteredEntries]);

  const toggleGroup = (kind: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) {
        next.delete(kind);
      } else {
        next.add(kind);
      }
      return next;
    });
  };

  const handleOpen = async (path: string) => {
    try {
      await api.projectOpenOutput(projectId, path);
    } catch (error) {
      onStatus(formatError(error), "error");
    }
  };

  const handlePreview = (entry: OutputEntry) => {
    const item = mediaPreviewItemFromPath(entry.path, entry.name);
    if (item) onPreviewMedia?.(item);
  };

  const handleReveal = async (path?: string) => {
    try {
      await api.projectRevealOutput(projectId, path);
    } catch (error) {
      onStatus(formatError(error), "error");
    }
  };

  const handleDelete = async (entry: OutputEntry) => {
    const label = KIND_LABELS[entry.kind] ?? entry.kind;
    if (!window.confirm(`Delete ${entry.relativePath} from ${label}?`)) return;
    try {
      await api.projectDeleteOutput(projectId, entry.path);
      onStatus(`Deleted ${entry.name}`, "ok");
      await refresh();
    } catch (error) {
      onStatus(formatError(error), "error");
    }
  };

  const handleClear = async (kind: CacheKind) => {
    const label = CLEAR_OPTIONS.find((opt) => opt.kind === kind)?.label ?? kind;
    if (!window.confirm(`Clear ${label}? This cannot be undone.`)) return;
    try {
      const result = await api.projectClearRenderCache(projectId, kind);
      onStatus(`Cleared ${label} — freed ${formatBytes(result.freedBytes)}`, "ok");
      await refresh();
    } catch (error) {
      onStatus(formatError(error), "error");
    }
  };

  return (
    <div className={`outputs-explorer ${embedded ? "outputs-explorer-embedded" : ""}`}>
      <div className="outputs-toolbar">
        <div className="outputs-summary">
          <span>{data ? `${data.entries.length} files` : "—"}</span>
          <span className="outputs-size">
            {data ? formatBytes(data.totalBytes) : ""}
          </span>
        </div>
        <select
          className="outputs-filter"
          value={filter}
          onChange={(e) => setFilter(e.target.value as OutputKind | "all")}
        >
          <option value="all">All types</option>
          {KIND_ORDER.map((kind) => (
            <option key={kind} value={kind}>
              {KIND_LABELS[kind]}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={busy || loading}
          onClick={() => void refresh()}
        >
          Refresh
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={busy}
          onClick={() => void handleReveal()}
          title={data?.rendersDir}
        >
          Show folder
        </button>
        <select
          className="outputs-clear"
          defaultValue=""
          disabled={busy}
          onChange={(e) => {
            const kind = e.target.value as CacheKind;
            if (!kind) return;
            e.target.value = "";
            void handleClear(kind);
          }}
        >
          <option value="">Clear cache…</option>
          {CLEAR_OPTIONS.map((opt) => (
            <option key={opt.kind} value={opt.kind}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="outputs-list">
        {loading && !data ? (
          <p className="outputs-empty">Loading outputs…</p>
        ) : filteredEntries.length === 0 ? (
          <p className="outputs-empty">No outputs yet — render a scene or export a tape</p>
        ) : (
          KIND_ORDER.filter((kind) => grouped.has(kind)).map((kind) => {
            const entries = grouped.get(kind) ?? [];
            const kindSize = entries.reduce((sum, e) => sum + e.sizeBytes, 0);
            const isOpen = expanded.has(kind);
            return (
              <section key={kind} className="outputs-group">
                <button
                  type="button"
                  className="outputs-group-header"
                  onClick={() => toggleGroup(kind)}
                >
                  <span className="outputs-group-chevron">{isOpen ? "▾" : "▸"}</span>
                  <span className="outputs-group-title">{KIND_LABELS[kind]}</span>
                  <span className="outputs-group-meta">
                    {entries.length} · {formatBytes(kindSize)}
                  </span>
                </button>
                {isOpen ? (
                  <ul className="outputs-entries">
                    {entries.map((entry) => {
                      const previewable = isPreviewableOutput(entry);
                      return (
                        <li
                          key={entry.path}
                          className={`outputs-entry ${previewable ? "outputs-entry-previewable" : ""}`}
                        >
                          {previewable ? (
                            <button
                              type="button"
                              className="outputs-entry-main outputs-entry-open"
                              disabled={busy}
                              onClick={() => handlePreview(entry)}
                              title={`Preview ${entry.name}`}
                            >
                              <span className="outputs-entry-name">{entry.name}</span>
                              {entry.resolution ? (
                                <span className="outputs-entry-res">{entry.resolution}</span>
                              ) : null}
                              <span className="outputs-entry-size">
                                {formatBytes(entry.sizeBytes)}
                              </span>
                            </button>
                          ) : (
                            <div className="outputs-entry-main">
                              <span className="outputs-entry-name" title={entry.relativePath}>
                                {entry.name}
                              </span>
                              {entry.resolution ? (
                                <span className="outputs-entry-res">{entry.resolution}</span>
                              ) : null}
                              <span className="outputs-entry-size">
                                {formatBytes(entry.sizeBytes)}
                              </span>
                            </div>
                          )}
                          <div className="outputs-entry-actions">
                            {!previewable ? (
                              <button
                                type="button"
                                className="btn btn-ghost"
                                disabled={busy}
                                onClick={() => void handleOpen(entry.path)}
                              >
                                Open
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className="btn btn-ghost"
                              disabled={busy}
                              onClick={() => void handleReveal(entry.path)}
                            >
                              Reveal
                            </button>
                            <button
                              type="button"
                              className="btn btn-ghost btn-danger"
                              disabled={busy}
                              onClick={() => void handleDelete(entry)}
                            >
                              ×
                            </button>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                ) : null}
              </section>
            );
          })
        )}
      </div>
    </div>
  );
}
