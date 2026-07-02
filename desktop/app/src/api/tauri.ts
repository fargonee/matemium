import { invoke, isTauri } from "@tauri-apps/api/core";

import type {
  CacheKind,
  ChatCompletionResponse,
  ChatMessage,
  CheckResult,
  ClearCacheResult,
  LintResult,
  ListScenesResult,
  MediaPreviewResult,
  OutputListResult,
  PreviewData,
  ProjectOpen,
  ProjectSummary,
  RenderResult,
  Settings,
  TokenResponse,
  VideoOrientation,
} from "./types";

export function runningInTauri(): boolean {
  return isTauri();
}

export async function projectList(): Promise<ProjectSummary[]> {
  return invoke<ProjectSummary[]>("project_list");
}

export async function projectCreate(name: string): Promise<ProjectOpen> {
  return invoke<ProjectOpen>("project_create", { params: { name } });
}

export async function projectOpen(projectId: string): Promise<ProjectOpen> {
  return invoke<ProjectOpen>("project_open", { params: { projectId } });
}

export async function projectSave(projectId: string, content: string): Promise<void> {
  return invoke("project_save", {
    params: { projectId, content },
  });
}

export async function projectSaveAssets(projectId: string, content: string): Promise<void> {
  return invoke("project_save_assets", {
    params: { projectId, content },
  });
}

export async function projectDelete(projectId: string): Promise<void> {
  return invoke("project_delete", { params: { projectId } });
}

export async function sidecarPing(): Promise<Record<string, unknown>> {
  return invoke("sidecar_ping");
}

export async function sidecarLint(projectId: string): Promise<LintResult> {
  return invoke<LintResult>("sidecar_lint", { params: { projectId } });
}

export async function sidecarCheck(
  projectId: string,
  scene?: string,
): Promise<CheckResult> {
  return invoke<CheckResult>("sidecar_check", {
    params: { projectId, scene: scene ?? null },
  });
}

export async function sidecarListScenes(projectId: string): Promise<ListScenesResult> {
  return invoke<ListScenesResult>("sidecar_list_scenes", {
    params: { projectId },
  });
}

export async function sidecarRender(
  projectId: string,
  scene?: string,
  quality = "preview",
  orientation: VideoOrientation = "portrait",
  outputDir?: string | null,
): Promise<RenderResult> {
  return invoke<RenderResult>("sidecar_render", {
    params: {
      projectId,
      scene: scene ?? null,
      quality,
      orientation,
      outputDir: outputDir ?? null,
    },
  });
}

export async function sidecarCancel(): Promise<void> {
  return invoke("sidecar_cancel");
}

export async function getAssetStatus(assetId?: string): Promise<any[]> {
  return invoke<any[]>("get_asset_status", { assetId: assetId ?? null });
}

export async function startAssetDownload(assetId: string): Promise<void> {
  return invoke("start_asset_download", { assetId });
}

export interface Readiness {
  phase: string;
  assetsReady: boolean;
  engineReady: boolean;
  intelligenceReady: boolean;
  fullyReady: boolean;
  message: string;
  enginePhase?: string;
}

export async function getReadiness(): Promise<Readiness> {
  return invoke<Readiness>("get_readiness");
}

export async function sidecarRetrieve(
  projectId: string,
  query: string,
  topK: number = 8
): Promise<{ query: string; results: any[] }> {
  return invoke<{ query: string; results: any[] }>("sidecar_retrieve", {
    project_id: projectId,
    query,
    top_k: topK,
  });
}

export interface PublishResponse {
  id: string;
  status: string;
  message?: string;
}

export async function publishAnimation(
  projectId: string,
  title: string,
  description?: string,
  tags?: string[],
  scene?: string,
  duration?: number
): Promise<PublishResponse> {
  return invoke<PublishResponse>("publish_animation", {
    project_id: projectId,
    title,
    description: description ?? null,
    tags: tags ?? null,
    scene: scene ?? null,
    duration: duration ?? null,
  });
}

export async function listGallery(search?: string): Promise<any> {
  return invoke("list_gallery", { search: search ?? null });
}

export async function cloudChat(
  messages: ChatMessage[],
  projectId?: string,
  scenesExcerpt?: string,
  llmConfig?: { llm_provider?: string; use_personal_llm?: boolean },
): Promise<ChatCompletionResponse> {
  return invoke<ChatCompletionResponse>("cloud_chat", {
    params: {
      messages,
      projectId: projectId ?? null,
      scenesExcerpt: scenesExcerpt ?? null,
      llm_provider: llmConfig?.llm_provider ?? null,
      use_personal_llm: llmConfig?.use_personal_llm ?? null,
    },
  });
}

export async function cloudGetProfile(): Promise<any> {
  // Fetches /v1/me for credits, LLM config status (has_own keys, etc.)
  return invoke("cloud_get_profile");
}

export async function cloudGenerateAudio(
  text: string,
  voice?: string,
  llmConfig?: { tts_provider?: string; use_personal_llm?: boolean },
): Promise<{ audioBase64?: string; error?: string }> {
  return invoke("cloud_generate_audio", {
    params: {
      text,
      voice: voice ?? null,
      tts_provider: llmConfig?.tts_provider ?? null,
      use_personal_llm: llmConfig?.use_personal_llm ?? null,
    },
  });
}

export async function authLogin(email: string, password: string): Promise<TokenResponse> {
  return invoke<TokenResponse>("auth_login", { params: { email, password } });
}

export async function authSession(accessToken: string): Promise<TokenResponse> {
  return invoke<TokenResponse>("auth_session", { params: { accessToken } });
}

export async function settingsGet(): Promise<Settings> {
  return invoke<Settings>("settings_get");
}

export async function settingsSet(settings: Settings): Promise<void> {
  return invoke("settings_set", { settings });
}

export async function readMediaPreview(path: string): Promise<MediaPreviewResult> {
  try {
    return await invoke<MediaPreviewResult>("read_media_preview", { params: { path } });
  } catch {
    const dataBase64 = await invoke<string>("read_video_preview", { params: { path } });
    return { dataBase64, mimeType: "video/mp4" };
  }
}

export async function readVideoPreview(path: string): Promise<Uint8Array> {
  const { dataBase64 } = await readMediaPreview(path);
  const binary = atob(dataBase64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export async function projectListOutputs(projectId: string): Promise<OutputListResult> {
  return invoke<OutputListResult>("project_list_outputs", {
    params: { projectId },
  });
}

export async function projectDeleteOutput(projectId: string, path: string): Promise<void> {
  return invoke("project_delete_output", {
    params: { projectId, path },
  });
}

export async function projectClearRenderCache(
  projectId: string,
  kind: CacheKind,
): Promise<ClearCacheResult> {
  return invoke<ClearCacheResult>("project_clear_render_cache", {
    params: { projectId, kind },
  });
}

export async function projectRevealOutput(
  projectId: string,
  path?: string,
): Promise<void> {
  return invoke("project_reveal_output", {
    params: { projectId, path: path ?? null },
  });
}

export async function projectOpenOutput(projectId: string, path: string): Promise<void> {
  return invoke("project_open_output", {
    params: { projectId, path },
  });
}

export async function sidecarGetPreviewData(projectId: string): Promise<PreviewData> {
  return invoke<PreviewData>("sidecar_get_preview_data", { params: { projectId } });
}