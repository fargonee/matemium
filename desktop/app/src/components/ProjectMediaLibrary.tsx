import { open } from "@tauri-apps/plugin-dialog";
import { useCallback, useEffect, useState } from "react";

import * as api from "../api/tauri";
import type { ProjectMediaEntry } from "../api/types";
import { formatBytes } from "../utils/formatBytes";
import { mediaPreviewItemFromPath, type MediaPreviewItem } from "../utils/mediaPreview";
import { formatError } from "../utils/errors";

interface ProjectMediaLibraryProps {
  projectId: string;
  category: "images" | "video" | "audio";
  onStatus: (message: string, kind?: "ok" | "error") => void;
  onPreview: (item: MediaPreviewItem) => void;
}

const FILTERS = {
  images: { name: "Images", extensions: ["png", "jpg", "jpeg", "webp", "gif", "svg"] },
  video: { name: "Video", extensions: ["mp4", "mov", "webm", "mkv"] },
  audio: { name: "Audio", extensions: ["mp3", "wav", "ogg", "m4a", "flac"] },
};

export function ProjectMediaLibrary({ projectId, category, onStatus, onPreview }: ProjectMediaLibraryProps) {
  const [entries, setEntries] = useState<ProjectMediaEntry[]>([]);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setEntries(await api.projectListMedia(projectId, category));
    } catch (error) {
      onStatus(formatError(error), "error");
    }
  }, [category, onStatus, projectId]);

  useEffect(() => { void refresh(); }, [refresh]);

  const importFiles = async () => {
    const selected = await open({ multiple: true, directory: false, filters: [FILTERS[category]] });
    const paths = Array.isArray(selected) ? selected : selected ? [selected] : [];
    if (paths.length === 0) return;
    setBusy(true);
    try {
      for (const path of paths) await api.projectImportMedia(projectId, category, path);
      await refresh();
      onStatus(`Imported ${paths.length} asset${paths.length === 1 ? "" : "s"}`, "ok");
    } catch (error) {
      onStatus(formatError(error), "error");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (entry: ProjectMediaEntry) => {
    if (!window.confirm(`Remove ${entry.name} from this project's assets?`)) return;
    try {
      await api.projectDeleteMedia(projectId, category, entry.name);
      await refresh();
      onStatus(`Removed ${entry.name}`, "ok");
    } catch (error) {
      onStatus(formatError(error), "error");
    }
  };

  return <div className="project-media-library">
    <div className="project-media-toolbar">
      <div><strong>{FILTERS[category].name}</strong><span>{entries.length} file{entries.length === 1 ? "" : "s"}</span></div>
      <button type="button" className="btn btn-primary" disabled={busy} onClick={() => void importFiles()}>{busy ? "Importing..." : "Import"}</button>
    </div>
    {entries.length === 0 ? <div className="media-library-empty"><span className="media-library-kind">{FILTERS[category].name}</span><strong>No project assets yet</strong><p>Import source files here. They are copied into <code>assets/{category}/</code> and stay separate from generated render caches.</p></div> :
      <div className="project-media-list">{entries.map((entry) => <article key={entry.name} className="project-media-row">
        <span className="file-kind file-kind-media">{category === "images" ? "IMG" : category === "video" ? "VID" : "AUD"}</span>
        <div><strong title={entry.name}>{entry.name}</strong><span>{formatBytes(entry.bytes)}</span></div>
        <div className="project-media-actions">
          <button type="button" className="btn btn-ghost" onClick={() => { const item = mediaPreviewItemFromPath(entry.path, entry.name); if (item) onPreview(item); }}>Preview</button>
          <button type="button" className="btn btn-ghost danger" onClick={() => void remove(entry)}>Delete</button>
        </div>
      </article>)}</div>}
  </div>;
}
