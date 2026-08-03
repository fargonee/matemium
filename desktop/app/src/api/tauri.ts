import { invoke, isTauri } from "@tauri-apps/api/core";

import type {
  BundledExampleOpen,
  BundledExampleSummary,
  CacheKind,
  ChatCompletionResponse,
  ChatMessage,
  CheckResult,
  ClearCacheResult,
  AssetStatus,
  Conversation,
  LintResult,
  ListScenesResult,
  ListTapesResult,
  MediaPreviewResult,
  LocalModelCatalogEntry,
  OpenRouterConnectStart,
  OpenRouterConnectionStatus,
  OutputListResult,
  PreviewData,
  ProjectOpen,
  ProjectMediaEntry,
  ProviderModel,
  ProjectSummary,
  RenderResult,
  Settings,
  TapeExportFormat,
  TapeExportResult,
  TokenResponse,
  VideoOrientation,
  AgentRunState,
  AgentStreamEvent,
} from "./types";

export function runningInTauri(): boolean {
  return isTauri();
}

export async function projectList(): Promise<ProjectSummary[]> {
  return invoke<ProjectSummary[]>("project_list");
}

export async function exampleList(): Promise<BundledExampleSummary[]> {
  return invoke<BundledExampleSummary[]>("example_list");
}

export async function exampleOpenSource(exampleId: string): Promise<BundledExampleOpen> {
  return invoke<BundledExampleOpen>("example_open_source", { params: { exampleId } });
}

export async function exampleCreateCopy(exampleId: string): Promise<ProjectOpen> {
  return invoke<ProjectOpen>("example_create_copy", { params: { exampleId } });
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

export async function projectSaveFile(projectId: string, file: string, content: string): Promise<void> {
  return invoke("project_save_file", {
    params: { projectId, file, content },
  });
}

export async function projectCreateTape(projectId: string, slug: string, title: string): Promise<ProjectOpen> {
  return invoke<ProjectOpen>("project_create_tape", {
    params: { projectId, slug, title, content: null },
  });
}

export async function projectSaveTape(projectId: string, slug: string, content: string): Promise<void> {
  return invoke("project_save_tape", {
    params: { projectId, slug, title: null, content },
  });
}

export async function projectListMedia(projectId: string, category: string): Promise<ProjectMediaEntry[]> {
  return invoke<ProjectMediaEntry[]>("project_list_media", { params: { projectId, category } });
}

export async function projectImportMedia(projectId: string, category: string, source: string): Promise<ProjectMediaEntry> {
  return invoke<ProjectMediaEntry>("project_import_media", { params: { projectId, category, source } });
}

export async function projectDeleteMedia(projectId: string, category: string, name: string): Promise<void> {
  return invoke("project_delete_media", { params: { projectId, category, name } });
}

export async function projectDelete(projectId: string): Promise<void> {
  return invoke("project_delete", { params: { projectId } });
}

export async function projectExportArchive(projectId: string, destination: string): Promise<string> {
  return invoke<string>("project_export_archive", { params: { projectId, destination } });
}

export async function projectImportArchive(source: string): Promise<ProjectOpen> {
  return invoke<ProjectOpen>("project_import_archive", { params: { source } });
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

export async function sidecarListTapes(
  projectId: string,
  scene?: string,
): Promise<ListTapesResult> {
  return invoke<ListTapesResult>("sidecar_list_tapes", {
    params: { projectId, scene: scene ?? null },
  });
}

export async function sidecarExportTape(
  projectId: string,
  tapeId: string,
  scene?: string,
  format: TapeExportFormat = "png",
  highResHeight?: number | null,
): Promise<TapeExportResult> {
  return invoke<TapeExportResult>("sidecar_export_tape", {
    params: {
      projectId,
      scene: scene ?? null,
      tapeId,
      format,
      highResHeight: highResHeight ?? null,
    },
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

export async function agentRunList(): Promise<AgentRunState[]> {
  return invoke<AgentRunState[]>("agent_run_list");
}

export async function agentRunGet(runId: string): Promise<AgentRunState> {
  return invoke<AgentRunState>("agent_run_get", { params: { runId } });
}

export async function agentRunEvents(
  runId: string,
  afterSequence = 0,
  limit = 200,
): Promise<AgentStreamEvent[]> {
  return invoke<AgentStreamEvent[]>("agent_run_events", {
    params: { runId, afterSequence, limit },
  });
}

export async function agentRunCancel(runId: string, reason?: string): Promise<AgentRunState> {
  return invoke<AgentRunState>("agent_run_cancel", {
    params: { runId, reason: reason ?? null },
  });
}

export async function agentRunResume(runId: string): Promise<AgentRunState> {
  return invoke<AgentRunState>("agent_run_resume", { params: { runId } });
}

export async function agentRunApprove(
  runId: string,
  actionId: string,
  approved: boolean,
  note?: string,
): Promise<AgentStreamEvent> {
  return invoke<AgentStreamEvent>("agent_run_approve", {
    params: { runId, actionId, approved, note: note ?? null },
  });
}

export async function agentRunProvideInput(runId: string, content: string): Promise<AgentRunState> {
  return invoke<AgentRunState>("agent_run_provide_input", {
    params: { runId, content },
  });
}

export async function getAssetStatus(assetId?: string): Promise<AssetStatus[]> {
  return invoke<AssetStatus[]>("get_asset_status", { assetId: assetId ?? null });
}

export async function startAssetDownload(assetId: string): Promise<void> {
  return invoke("start_asset_download", { assetId });
}

export async function pauseAssetDownload(assetId: string): Promise<void> {
  return invoke("pause_asset_download", { assetId });
}

export async function cancelAssetDownload(assetId: string): Promise<void> {
  return invoke("cancel_asset_download", { assetId });
}

export async function localModelCatalogList(query?: string): Promise<LocalModelCatalogEntry[]> {
  return invoke<LocalModelCatalogEntry[]>("local_model_catalog_list", { query: query ?? null });
}

export async function localModelInstall(entry: LocalModelCatalogEntry): Promise<void> {
  return invoke("local_model_install", { entry });
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
  topK: number = 8,
  files?: string[] | null,
): Promise<{ query: string; results: any[] }> {
  return invoke<{ query: string; results: any[] }>("sidecar_retrieve", {
    projectId,
    query,
    topK,
    files: files ?? null,
  });
}

export async function sidecarUploadReference(
  projectId: string,
  fileName: string,
  fileContentBase64?: string | null,
  fileContentText?: string | null,
): Promise<{ status: string; file_name: string; path: string; indexed: boolean }> {
  return invoke<{ status: string; file_name: string; path: string; indexed: boolean }>(
    "sidecar_upload_reference",
    {
      projectId,
      fileName,
      fileContentBase64: fileContentBase64 ?? null,
      fileContentText: fileContentText ?? null,
    }
  );
}

export async function sidecarListReferences(
  projectId: string,
): Promise<{ status: string; references: string[] }> {
  return invoke<{ status: string; references: string[] }>("sidecar_list_references", {
    projectId,
  });
}

export async function sidecarDeleteReference(
  projectId: string,
  fileName: string,
): Promise<{ status: string; file_name: string; deleted: boolean }> {
  return invoke<{ status: string; file_name: string; deleted: boolean }>("sidecar_delete_reference", {
    projectId,
    fileName,
  });
}

export async function sidecarGetReferenceContent(
  projectId: string,
  fileName: string,
): Promise<{ status: string; file_name: string; content: string }> {
  return invoke<{ status: string; file_name: string; content: string }>("sidecar_get_reference_content", {
    projectId,
    fileName,
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
  conversationId?: string | null,
  scenesExcerpt?: string,
  llmConfig?: { llm_provider?: string; use_personal_llm?: boolean; model?: string; use_autonomous_agent?: boolean; agent_runtime_version?: string },
): Promise<ChatCompletionResponse> {
  return invoke<ChatCompletionResponse>("cloud_chat", {
    params: {
      messages,
      projectId: projectId ?? null,
      conversationId: conversationId ?? null,
      scenesExcerpt: scenesExcerpt ?? null,
      llmProvider: llmConfig?.llm_provider ?? null,
      usePersonalLlm: llmConfig?.use_personal_llm ?? null,
      model: llmConfig?.model ?? null,
      useAutonomousAgent: llmConfig?.use_autonomous_agent ?? null,
      agentRuntimeVersion: llmConfig?.agent_runtime_version ?? null,
    },
  });
}

export async function cloudGetProfile(): Promise<any> {
  // Fetches /v1/me for account/profile status. Provider keys stay local.
  return invoke("cloud_get_profile");
}

export async function providerModelsList(provider: string, refresh = false): Promise<ProviderModel[]> {
  return invoke<ProviderModel[]>("provider_models_list", {
    params: { provider, refresh },
  });
}

export async function cloudGenerateAudio(
  text: string,
  voice?: string,
  llmConfig?: { tts_provider?: string; use_personal_llm?: boolean },
  project?: { projectId: string; artifactKind: "tts" | "custom_audio" },
  delivery?: { model?: string; instructions?: string },
): Promise<{ audioBase64?: string; audioPath?: string | null; mimeType?: string; error?: string }> {
  return invoke("cloud_generate_audio", {
    params: {
      text,
      voice: voice ?? null,
      model: delivery?.model ?? null,
      instructions: delivery?.instructions ?? null,
      tts_provider: llmConfig?.tts_provider ?? null,
      use_personal_llm: llmConfig?.use_personal_llm ?? null,
      projectId: project?.projectId ?? null,
      artifactKind: project?.artifactKind ?? null,
    },
  });
}

export async function projectMuxAudio(
  projectId: string,
  videoPath?: string | null,
  audioPath?: string | null,
): Promise<{ video: string; audio: string; output: string; videoCodec: "copy"; audioCodec: string }> {
  return invoke("project_mux_audio", {
    params: { projectId, videoPath: videoPath ?? null, audioPath: audioPath ?? null },
  });
}

export async function projectTranscribeAudio(
  projectId: string,
  audioPath?: string | null,
  provider?: string | null,
): Promise<{ audio: string; transcript: string; segments: Array<{ start: number; end: number; text: string }>; transcriptPath: string; timestampsPath: string }> {
  return invoke("project_transcribe_audio", {
    params: { projectId, audioPath: audioPath ?? null, provider: provider ?? null },
  });
}

export async function projectApproveAudio(
  projectId: string,
  artifactKind: "tts" | "custom_audio",
): Promise<{ audio: string; artifactKind: string; validation: "approved" }> {
  return invoke("project_approve_audio", {
    params: { projectId, artifactKind },
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

export async function openrouterPrepareConnect(): Promise<OpenRouterConnectStart> {
  return invoke<OpenRouterConnectStart>("openrouter_prepare_connect");
}

export async function openrouterCompleteConnect(): Promise<OpenRouterConnectionStatus> {
  return invoke<OpenRouterConnectionStatus>("openrouter_complete_connect");
}

export async function openrouterCancelConnect(): Promise<void> {
  return invoke("openrouter_cancel_connect");
}

export async function openrouterDisconnect(): Promise<OpenRouterConnectionStatus> {
  return invoke<OpenRouterConnectionStatus>("openrouter_disconnect");
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

export async function listConversations(projectId: string): Promise<Conversation[]> {
  return invoke<Conversation[]>("conversation_list", { params: { projectId } });
}

export async function saveConversation(projectId: string, conversation: Conversation): Promise<void> {
  return invoke("conversation_save", { params: { projectId, conversation } });
}

export async function deleteConversation(projectId: string, conversationId: string): Promise<void> {
  return invoke("conversation_delete", { params: { projectId, conversationId } });
}
