import { convertFileSrc, invoke } from "@tauri-apps/api/core";

import type { MediaFileInfo, MediaPreviewResult } from "../api/types";
import type { MediaPreviewType } from "./mediaPreview";
import { mediaTypeFromPath } from "./mediaPreview";

/** Full renders are streamed/remuxed; partial segments stay small enough for blob IPC. */
const VIDEO_BLOB_MAX_BYTES = 48 * 1024 * 1024;

let activeBlobUrl: string | null = null;

function revokeActiveBlobUrl(): void {
  if (activeBlobUrl) {
    URL.revokeObjectURL(activeBlobUrl);
    activeBlobUrl = null;
  }
}

function decodeBase64(encoded: string): Uint8Array {
  const binary = atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function blobUrlFromBytes(bytes: Uint8Array, mimeType: string): string {
  const blob = new Blob([Uint8Array.from(bytes)], { type: mimeType });
  const url = URL.createObjectURL(blob);
  activeBlobUrl = url;
  return url;
}

function blobUrlFromBase64(dataBase64: string, mimeType: string): string {
  return blobUrlFromBytes(decodeBase64(dataBase64), mimeType);
}

function normalizeBinaryPayload(payload: number[] | Uint8Array): Uint8Array {
  return payload instanceof Uint8Array ? payload : new Uint8Array(payload);
}

export async function mediaFileInfo(path: string): Promise<MediaFileInfo> {
  return invoke<MediaFileInfo>("media_file_info", { params: { path } });
}

async function fetchMediaPreviewBinary(path: string): Promise<Uint8Array> {
  const payload = await invoke<number[] | Uint8Array>("read_media_preview_binary", {
    params: { path },
  });
  return normalizeBinaryPayload(payload);
}

async function fetchMediaPreviewBase64(path: string): Promise<MediaPreviewResult> {
  return invoke<MediaPreviewResult>("read_media_preview", { params: { path } });
}

async function videoBlobUrl(info: MediaFileInfo): Promise<string> {
  try {
    const bytes = await fetchMediaPreviewBinary(info.playbackPath);
    return blobUrlFromBytes(bytes, info.mimeType);
  } catch {
    const { dataBase64, mimeType } = await fetchMediaPreviewBase64(info.playbackPath);
    return blobUrlFromBase64(dataBase64, mimeType);
  }
}

export function videoAssetUrl(path: string): string {
  return convertFileSrc(path);
}

async function resolveVideoPreviewSrc(path: string): Promise<string> {
  const info = await mediaFileInfo(path);

  if (info.sizeBytes <= VIDEO_BLOB_MAX_BYTES) {
    return videoBlobUrl(info);
  }

  return videoAssetUrl(info.playbackPath);
}

export async function resolveMediaPreviewSrc(
  path: string,
  mediaType?: MediaPreviewType,
): Promise<string> {
  revokeActiveBlobUrl();

  const kind = mediaType ?? mediaTypeFromPath(path);
  if (!kind) {
    throw new Error("Unsupported preview file type");
  }

  if (kind === "video") {
    return resolveVideoPreviewSrc(path);
  }

  const info = await mediaFileInfo(path);
  const { dataBase64, mimeType } = await fetchMediaPreviewBase64(info.playbackPath);
  return blobUrlFromBase64(dataBase64, mimeType);
}

/** Fallback when blob playback fails in the webview. */
export async function resolveVideoAssetFallback(path: string): Promise<string> {
  const info = await mediaFileInfo(path);
  return videoAssetUrl(info.playbackPath);
}

export function clearMediaPreviewSrc(): void {
  revokeActiveBlobUrl();
}