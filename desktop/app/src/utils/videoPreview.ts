import { convertFileSrc } from "@tauri-apps/api/core";

import * as api from "../api/tauri";

let activeBlobUrl: string | null = null;

function revokeActiveBlobUrl(): void {
  if (activeBlobUrl) {
    URL.revokeObjectURL(activeBlobUrl);
    activeBlobUrl = null;
  }
}

export async function resolveVideoPreviewSrc(path: string): Promise<string> {
  revokeActiveBlobUrl();

  try {
    const bytes = await api.readVideoPreview(path);
    const blob = new Blob([Uint8Array.from(bytes)], { type: "video/mp4" });
    activeBlobUrl = URL.createObjectURL(blob);
    return activeBlobUrl;
  } catch {
    return convertFileSrc(path);
  }
}

export function clearVideoPreviewSrc(): void {
  revokeActiveBlobUrl();
}