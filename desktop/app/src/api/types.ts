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
  scenes_path: string;
  scenes_content: string;
  assets_path: string;
  assets_content: string;
  project_json: unknown;
  renders_dir: string;
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
}

// Extended for new LLM-agnostic server features (BYO keys + platform credits)
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
  // Flags to select personal (BYO) or platform LLM (keys resolved server-side)
  llm_provider?: string;
  use_personal_llm?: boolean;
}

export interface AudioSpeechRequest {
  text: string;
  voice?: string;
  model?: string;
  tts_provider?: string;
  use_personal_llm?: boolean;
}

export type BottomDockTab = "progress" | "output" | "preview";

export interface Settings {
  serverUrl: string;
  apiToken?: string | null;
  bottomDockDefault?: BottomDockTab;
  // LLM preferences - user chooses personal keys (BYO via web dashboard) or platform credits
  usePersonalLlm?: boolean;
  llmProvider?: string;
}

export interface TokenResponse {
  accessToken: string;
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