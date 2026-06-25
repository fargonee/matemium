import type { OutputEntry } from "../api/types";

export type MediaPreviewType = "video" | "image";

const VIDEO_EXTENSIONS = new Set([".mp4", ".webm", ".mov", ".m4v"]);
const IMAGE_EXTENSIONS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".webp",
  ".svg",
  ".bmp",
  ".avif",
]);

export interface MediaPreviewItem {
  path: string;
  name: string;
  mediaType: MediaPreviewType;
}

function fileExtension(path: string): string {
  const dot = path.lastIndexOf(".");
  if (dot < 0) return "";
  return path.slice(dot).toLowerCase();
}

export function mediaTypeFromPath(path: string): MediaPreviewType | null {
  const ext = fileExtension(path);
  if (VIDEO_EXTENSIONS.has(ext)) return "video";
  if (IMAGE_EXTENSIONS.has(ext)) return "image";
  return null;
}

export function mediaPreviewItemFromPath(
  path: string,
  name?: string,
): MediaPreviewItem | null {
  const mediaType = mediaTypeFromPath(path);
  if (!mediaType) return null;
  return {
    path,
    name: name ?? path.split(/[/\\]/).pop() ?? path,
    mediaType,
  };
}

export function isPreviewableOutput(entry: OutputEntry): boolean {
  return mediaTypeFromPath(entry.path) !== null;
}