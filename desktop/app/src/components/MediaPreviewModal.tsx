import { useEffect, useRef, useState } from "react";

import * as api from "../api/tauri";
import type { MediaPreviewItem } from "../utils/mediaPreview";
import {
  clearMediaPreviewSrc,
  resolveMediaPreviewSrc,
  resolveVideoAssetFallback,
} from "../utils/mediaPreviewSrc";
import { formatError } from "../utils/errors";

interface MediaPreviewModalProps {
  item: MediaPreviewItem | null;
  projectId: string | null;
  onClose: () => void;
  onStatus?: (message: string, kind?: "ok" | "error") => void;
}

export function MediaPreviewModal({
  item,
  projectId,
  onClose,
  onStatus,
}: MediaPreviewModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [usedAssetFallback, setUsedAssetFallback] = useState(false);
  const [aspectRatio, setAspectRatio] = useState<number | null>(null);

  useEffect(() => {
    if (!item) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [item, onClose]);

  useEffect(() => {
    if (!item) {
      setSrc(null);
      setLoadError(null);
      setLoading(false);
      setUsedAssetFallback(false);
      setAspectRatio(null);
      clearMediaPreviewSrc();
      return;
    }

    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    setSrc(null);
    setUsedAssetFallback(false);
    setAspectRatio(null);

    void resolveMediaPreviewSrc(item.path, item.mediaType)
      .then((url) => {
        if (!cancelled) setSrc(url);
      })
      .catch((error) => {
        if (!cancelled) setLoadError(formatError(error));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      clearMediaPreviewSrc();
    };
  }, [item]);

  useEffect(() => {
    if (!item || item.mediaType !== "video" || !src) return;
    const video = videoRef.current;
    if (!video) return;
    void video.play().catch(() => undefined);
    return () => {
      video.pause();
      video.currentTime = 0;
    };
  }, [item, src]);

  const handleVideoError = () => {
    if (!item || item.mediaType !== "video" || usedAssetFallback) {
      setLoadError("This video could not be played in the preview.");
      return;
    }

    setUsedAssetFallback(true);
    setLoading(true);
    setLoadError(null);
    clearMediaPreviewSrc();

    void resolveVideoAssetFallback(item.path)
      .then((url) => {
        setSrc(url);
      })
      .catch((error) => {
        setLoadError(formatError(error));
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleVideoMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget;
    if (video.videoWidth && video.videoHeight) {
      setAspectRatio(video.videoWidth / video.videoHeight);
    }
  };

  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.currentTarget;
    if (img.naturalWidth && img.naturalHeight) {
      setAspectRatio(img.naturalWidth / img.naturalHeight);
    }
  };

  if (!item) return null;

  const handleReveal = async () => {
    if (!projectId) return;
    try {
      await api.projectRevealOutput(projectId, item.path);
    } catch (error) {
      onStatus?.(formatError(error), "error");
    }
  };

  return (
    <div className="modal-backdrop media-preview-backdrop" onClick={onClose}>
      <div
        className="modal media-preview-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Preview ${item.name}`}
        onClick={(event) => event.stopPropagation()}
        style={
          aspectRatio
            ? {
                width: `min(max(calc(min(72vh, 720px) * ${aspectRatio} + 32px), 320px), 920px, 96vw)`,
              }
            : undefined
        }
      >
        <div className="media-preview-header">
          <div className="media-preview-title-block">
            <h2 className="media-preview-title">{item.name}</h2>
            <p className="media-preview-subtitle">
              {item.mediaType === "video" ? "Video preview" : "Image preview"}
            </p>
          </div>
          <div className="media-preview-header-actions">
            {projectId ? (
              <button
                type="button"
                className="btn btn-ghost media-preview-btn"
                onClick={() => void handleReveal()}
              >
                Reveal
              </button>
            ) : null}
            <button type="button" className="btn btn-ghost media-preview-btn" onClick={onClose}>
              Close
            </button>
          </div>
        </div>

        <div className="media-preview-stage">
          {loading ? (
            <p className="media-preview-status">Loading preview…</p>
          ) : loadError ? (
            <p className="media-preview-status media-preview-status-error">{loadError}</p>
          ) : src && item.mediaType === "video" ? (
            <video
              key={src}
              ref={videoRef}
              className="media-preview-video"
              src={src}
              controls
              autoPlay
              playsInline
              onError={handleVideoError}
              onLoadedMetadata={handleVideoMetadata}
            />
          ) : src ? (
            <img
              className="media-preview-image"
              src={src}
              alt={item.name}
              onLoad={handleImageLoad}
            />
          ) : (
            <p className="media-preview-status">Preview unavailable</p>
          )}
        </div>

        <p className="media-preview-path" title={item.path}>
          {item.path}
        </p>
      </div>
    </div>
  );
}