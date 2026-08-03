import { useEffect, useRef, useState } from "react";

import * as api from "../api/tauri";
import type { MediaPreviewItem } from "../utils/mediaPreview";
import {
  clearMediaPreviewSrc,
  resolveMediaPreviewSrc,
  resolveVideoAssetFallback,
  resolveVideoBlobFallback,
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
  const fallbackAttemptedRef = useRef(false);
  const replacingVideoSourceRef = useRef(false);
  const pendingPlaybackRef = useRef<{ time: number; shouldPlay: boolean } | null>(null);
  const [src, setSrc] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [videoReady, setVideoReady] = useState(false);
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
      setVideoReady(false);
      setUsedAssetFallback(false);
      setAspectRatio(null);
      fallbackAttemptedRef.current = false;
      replacingVideoSourceRef.current = false;
      pendingPlaybackRef.current = null;
      clearMediaPreviewSrc();
      return;
    }

    let cancelled = false;
    fallbackAttemptedRef.current = false;
    replacingVideoSourceRef.current = false;
    pendingPlaybackRef.current = null;
    setLoading(true);
    setVideoReady(false);
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
      const video = videoRef.current;
      if (video) {
        video.pause();
        video.removeAttribute("src");
        video.load();
      }
      clearMediaPreviewSrc();
    };
  }, [item?.path, item?.mediaType]);

  const handleVideoError = () => {
    if (replacingVideoSourceRef.current) return;

    if (
      !item ||
      item.mediaType !== "video" ||
      fallbackAttemptedRef.current
    ) {
      setLoadError("This video could not be played in the preview.");
      return;
    }

    const video = videoRef.current;
    const failedSrc = video?.currentSrc || src || "";
    pendingPlaybackRef.current = {
      time: video && Number.isFinite(video.currentTime) ? video.currentTime : 0,
      shouldPlay: Boolean(video && !video.paused),
    };
    fallbackAttemptedRef.current = true;
    replacingVideoSourceRef.current = true;
    setUsedAssetFallback(true);
    setLoading(true);
    setVideoReady(false);
    setLoadError(null);
    setSrc(null);

    // Detach the element before revoking a blob URL. Revoking a URL that is
    // still attached can emit another error and start a duplicate fallback.
    if (video) {
      video.pause();
      video.removeAttribute("src");
      video.load();
    }
    clearMediaPreviewSrc();

    const resolveFallback = failedSrc.startsWith("blob:")
      ? resolveVideoAssetFallback
      : resolveVideoBlobFallback;

    void resolveFallback(item.path)
      .then((url) => {
        replacingVideoSourceRef.current = false;
        setSrc(url);
      })
      .catch((error) => {
        replacingVideoSourceRef.current = false;
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

    const pending = pendingPlaybackRef.current;
    if (pending && pending.time > 0 && Number.isFinite(video.duration)) {
      video.currentTime = Math.min(pending.time, Math.max(0, video.duration - 0.01));
    }
  };

  const handleVideoData = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget;
    const pending = pendingPlaybackRef.current;
    pendingPlaybackRef.current = null;
    setVideoReady(true);
    setLoading(false);

    // Begin only after the browser has decoded and presented the first frame.
    // This keeps autoplay from advancing past the opening while the stage is blank.
    requestAnimationFrame(() => {
      if (!video.isConnected) return;
      if (!pending || pending.shouldPlay) {
        void video.play().catch(() => undefined);
      }
    });
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
              {item.mediaType === "video"
                ? `Video preview${usedAssetFallback ? " · compatibility mode" : ""}`
                : "Image preview"}
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
          {loadError ? (
            <p className="media-preview-status media-preview-status-error">{loadError}</p>
          ) : src && item.mediaType === "video" ? (
            <>
              <video
                key={src}
                ref={videoRef}
                className={`media-preview-video${videoReady ? " is-ready" : ""}`}
                src={src}
                controls
                preload="auto"
                playsInline
                onError={handleVideoError}
                onLoadedMetadata={handleVideoMetadata}
                onLoadedData={handleVideoData}
              />
              {!videoReady ? (
                <p className="media-preview-status media-preview-video-loading">
                  Preparing video…
                </p>
              ) : null}
            </>
          ) : src ? (
            <img
              className="media-preview-image"
              src={src}
              alt={item.name}
              onLoad={handleImageLoad}
            />
          ) : loading ? (
            <p className="media-preview-status">Loading preview…</p>
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
