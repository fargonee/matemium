export interface ProjectSummary {
  id: string;
  name: string;
  description: string;
  scene_class: string;
  updated_at: string;
  preview_video?: string | null;
}

export interface ProjectOpen {
  id: string;
  name: string;
  description: string;
  scene_class: string;
  orientation: string;
  files: Record<string, string>;
  tapes: Record<string, string>;
  project_json: unknown;
  renders_dir: string;
}

export interface ProjectMediaEntry {
  name: string;
  path: string;
  bytes: number;
}

export interface LintDiagnostic {
  line: number;
  col: number;
  message: string;
  severity: "error" | "warning" | string;
}

export interface LintResult {
  ok: boolean;
  diagnostics: LintDiagnostic[];
  workspace: string;
}

export interface CheckResult {
  ok: boolean;
  errors: string[];
  warnings: string[];
  scene?: string;
  timeline_length?: number;
  title?: string;
}

export interface ListScenesResult {
  scenes: string[];
  workspace: string;
}

export type VideoOrientation = "portrait" | "landscape";

export interface RenderResult {
  video: string;
  /** User-chosen export path when it differs from ``video`` (project renders). */
  export_video?: string;
  orientation?: VideoOrientation;
  aspect_ratio?: string;
  pixel_width?: number;
  pixel_height?: number;
  workspace: string;
  scene: string;
  duration_estimate?: number;
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
  references?: string[];
}

export interface CodeEdit {
  description: string;
  search?: string | null;
  replace?: string | null;
  full_file?: string | null;
}

export interface ChatCompletionResponse {
  id: string;
  message: ChatMessage;
  code_edit?: CodeEdit | null;
  model: string;
  stub?: boolean;
  agent_runtime_version?: string | null;
  provider?: string | null;
  billing_mode?: "byo_external" | "local" | null;
  request_id?: string | null;
  agent_trace?: AgentTraceEntry[];
}

export interface AgentTraceEntry {
  type: string;
  summary?: string;
  details?: Record<string, unknown>;
  sequence?: number;
  timestamp_ms?: number;
}

// Extended for LLM-agnostic features (local OpenRouter keys + local models)
export interface LLMConfig {
  llm_provider?: string | null;
  has_own_llm_key?: boolean;
  tts_provider?: string | null;
  has_own_tts_key?: boolean;
  llm_credits?: number;
}

export interface ChatCompletionRequest {
  messages: ChatMessage[];
  project_id?: string;
  scenes_excerpt?: string;
  // Provider/model selection. Desktop resolves locally stored provider keys.
  llm_provider?: string;
  use_personal_llm?: boolean;
}

export type AgentRunStatus =
  | "received"
  | "understanding"
  | "planning"
  | "executing"
  | "verifying"
  | "recovering"
  | "completed"
  | "blocked"
  | "failed"
  | "cancelled";

export interface AgentRunState {
  run_id: string;
  runtime_version: string;
  project_id: string;
  objective: string;
  status: AgentRunStatus;
  sequence: number;
  plan: Array<{ id: string; text: string; status: string }>;
  acceptance_criteria: string[];
  terminal_reason?: string | null;
  completion_manifest?: Record<string, unknown> | null;
  budgets: Record<string, number>;
  usage: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export interface AgentStreamEvent {
  event_id: string;
  run_id: string;
  sequence: number;
  schema_version: number;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AudioSpeechRequest {
  text: string;
  voice?: string;
  model?: string;
  tts_provider?: string;
  use_personal_llm?: boolean;
}

export type BottomDockTab = "progress" | "output" | "preview";

export interface AssetStatus {
  id: string;
  display_name?: string | null;
  asset_type?: string | null;
  downloaded: boolean;
  verified: boolean;
  path?: string | null;
  size?: number | null;
  progress?: number | null;
  error?: string | null;
  paused?: boolean | null;
  source_url?: string | null;
  expected_sha256?: string | null;
  install_path?: string | null;
  extract?: boolean | null;
  extract_format?: string | null;
}

export interface LocalModelCatalogEntry {
  repoId: string;
  displayName: string;
  family: string;
  fileName: string;
  downloadUrl: string;
  sizeBytes: number;
  expectedSha256?: string | null;
  contextLength?: number | null;
  parameterSize?: string | null;
  quantization?: string | null;
  license?: string | null;
  tags: string[];
  assetId: string;
  installPath: string;
  sourceRepoUrl: string;
  installed: boolean;
}

export interface Settings {
  serverUrl: string;
  apiToken?: string | null;
  bottomDockDefault?: BottomDockTab;
  // LLM preferences - user chooses connected provider keys or local models.
  usePersonalLlm?: boolean;
  llmProvider?: string;
  openrouterApiKey?: string | null;
  openrouterUserId?: string | null;
  openrouterConnectedAt?: string | null;
  openrouterFreeDisabledUntil?: string | null;
  openaiApiKey?: string | null;
  openaiConnectedAt?: string | null;
  groqApiKey?: string | null;
  groqConnectedAt?: string | null;
  xaiApiKey?: string | null;
  xaiConnectedAt?: string | null;
  cerebrasApiKey?: string | null;
  cerebrasConnectedAt?: string | null;
  githubApiKey?: string | null;
  githubConnectedAt?: string | null;
  mistralApiKey?: string | null;
  mistralConnectedAt?: string | null;
  geminiApiKey?: string | null;
  geminiConnectedAt?: string | null;
  useLocalLlm?: boolean;
  localLlmModel?: string;
  externalLlmModel?: string;
  providerModels?: Record<string, ProviderModelSettings>;
  reasoningLevel?: string;
  useAutonomousAgent?: boolean;
  agentRuntimeVersion?: string;
}

export interface ProviderModelSettings {
  pinned?: string[];
  catalog?: ProviderModel[];
  fetchedAt?: string | null;
}

export interface ProviderModel {
  id: string;
  name: string;
  provider: string;
  contextLength?: number | null;
  pricingLabel?: string | null;
  badges?: string[];
}

export interface TokenResponse {
  accessToken: string;
}

export interface OpenRouterConnectionStatus {
  connected: boolean;
  userId?: string | null;
  connectedAt?: string | null;
}

export interface OpenRouterConnectStart {
  authUrl: string;
  callbackUrl: string;
}

export interface SidecarEventPayload {
  event: string;
  data: Record<string, unknown>;
}

export interface SectionItem {
  title: string;
  line: number;
}

export type OutputKind =
  | "preview"
  | "video"
  | "partial"
  | "tex"
  | "text"
  | "image"
  | "other";

export type CacheKind =
  | "partials"
  | "tex"
  | "texts"
  | "images"
  | "previews"
  | "videos"
  | "all";

export interface OutputEntry {
  path: string;
  relativePath: string;
  name: string;
  kind: OutputKind | string;
  sizeBytes: number;
  modifiedAt: string;
  resolution?: string | null;
}

export interface OutputKindSummary {
  kind: string;
  count: number;
  sizeBytes: number;
}

export interface OutputListResult {
  entries: OutputEntry[];
  totalBytes: number;
  rendersDir: string;
  byKind: OutputKindSummary[];
}

export interface ClearCacheResult {
  freedBytes: number;
}

export interface MediaPreviewResult {
  dataBase64: string;
  mimeType: string;
}

export interface MediaFileInfo {
  path: string;
  playbackPath: string;
  sizeBytes: number;
  mimeType: string;
}

export interface PreviewElement {
  id: string;
  type: string;
  content: string;
  spec?: any;                 // full spec for custom types (QuadraticPlot etc)
  raw_content?: any;
  x: number;
  y: number;
  z?: number;
  canvas_position?: [number, number, number];
  width: number;
  height: number;
  layout?: {
    width: number; height: number; wrap?: boolean; align?: string;
    margin_top?: number; margin_bottom?: number; margin_left?: number; margin_right?: number;
  };
  margin_top?: number;
  margin_bottom?: number;
  align?: string;
  is_math?: boolean;
  is_3d?: boolean;
  pitch?: number | null;
  yaw?: number | null;
  static_phi?: number | null;
  static_theta?: number | null;
  static_scale?: number;
  static_opacity?: number;
  auto_focus?: boolean;
  flex_group?: string | null;
  runs?: Array<{ text: string; style?: Record<string, any> }>;
  entry_animation?: { type: string; run_time: number; kwargs?: Record<string, any> };
  state_behavior?: { type: string; params?: Record<string, any> };
}

export interface TimelineAction extends PreviewElement {
  kind: string; // "element" | "CameraMove" | "TransformElement" | "CameraFocus" | ...
  target_position?: [number, number, number];
  run_time?: number;
  rate_func?: string;
  // other fields from special actions (element_id, etc.)
  [key: string]: any;
}

export interface PreviewData {
  elements: PreviewElement[];
  timeline?: TimelineAction[];   // full ordered script for manim-web replay (preferred for 1-1)
  frame_width: number;
  frame_height: number;
  title?: string;
  orientation?: string;
  background_color?: string;
  // Phase 1/7: 3D world model
  coordinate_system?: string;
  world_transform?: { position: [number,number,number]; rotation?: [number,number,number]; scale?: number } | null;
  // Phase 5/7: object graph + observations for full 3D preview
  root_objects?: any[];
  root_tape?: any;
  observations?: any[];  // list of camera keyframes/observations for replay
}

export interface AssetManifestEntry {
  id: string;
  name: string;
  url: string;
  sha256: string;
  size: number;
  extract: boolean;
  extract_format: "tar.gz" | "zip" | "none" | string;
  install_path: string;
  platforms: string[];
}

export interface AssetManifest {
  version: string;
  assets: AssetManifestEntry[];
  notes?: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  messages: ChatMessage[];
}
