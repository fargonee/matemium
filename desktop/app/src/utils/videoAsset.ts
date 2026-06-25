import { convertFileSrc } from "@tauri-apps/api/core";

export function videoAssetSrc(path: string): string {
  return convertFileSrc(path);
}