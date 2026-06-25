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

export type BottomDockTab = "progress" | "output";

export interface Settings {
  serverUrl: string;
  apiToken?: string | null;
  bottomDockDefault?: BottomDockTab;
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