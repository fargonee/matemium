import type { VideoOrientation } from "../api/types";
import type { SidebarView } from "../components/ProjectSidebar";

const STORAGE_KEY = "matemium-workspace-prefs";

export type ProjectFile =
  | "scenes"
  | "helpers"
  | "passport"
  | "description"
  | "tape"
  | "roadmap"
  | "narration";

export interface GlobalWorkspacePrefs {
  sidebarView: SidebarView;
  activeFile: ProjectFile;
}

export interface ProjectRenderPrefs {
  scene: string;
  quality: string;
  orientation: VideoOrientation;
  /** Custom output folder; null uses the project default renders directory. */
  outputDir: string | null;
}

interface WorkspacePrefsStore {
  global: GlobalWorkspacePrefs;
  projects: Record<string, ProjectRenderPrefs>;
}

const DEFAULT_GLOBAL: GlobalWorkspacePrefs = {
  sidebarView: "project",
  activeFile: "scenes",
};

const DEFAULT_RENDER: ProjectRenderPrefs = {
  scene: "",
  quality: "low",
  orientation: "portrait",
  outputDir: null,
};

function isSidebarView(value: string): value is SidebarView {
  return value === "project";
}

function isProjectFile(value: string): value is ProjectFile {
  return ["scenes", "helpers", "passport", "description", "tape", "roadmap", "narration"].includes(value);
}

function isVideoOrientation(value: string): value is VideoOrientation {
  return value === "portrait" || value === "landscape";
}

function loadStore(): WorkspacePrefsStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { global: DEFAULT_GLOBAL, projects: {} };
    }

    const parsed = JSON.parse(raw) as Partial<WorkspacePrefsStore> & {
      global?: Partial<GlobalWorkspacePrefs>;
      projects?: Record<string, Partial<ProjectRenderPrefs>>;
    };

    const global: GlobalWorkspacePrefs = {
      sidebarView: isSidebarView(parsed.global?.sidebarView ?? "")
        ? parsed.global!.sidebarView!
        : DEFAULT_GLOBAL.sidebarView,
      activeFile: isProjectFile(parsed.global?.activeFile ?? "")
        ? parsed.global!.activeFile!
        : DEFAULT_GLOBAL.activeFile,
    };

    const projects: Record<string, ProjectRenderPrefs> = {};
    for (const [projectId, prefs] of Object.entries(parsed.projects ?? {})) {
      projects[projectId] = {
        scene: typeof prefs.scene === "string" ? prefs.scene : DEFAULT_RENDER.scene,
        quality: typeof prefs.quality === "string" ? prefs.quality : DEFAULT_RENDER.quality,
        orientation: isVideoOrientation(prefs.orientation ?? "")
          ? prefs.orientation!
          : DEFAULT_RENDER.orientation,
        outputDir:
          prefs.outputDir === null || typeof prefs.outputDir === "string"
            ? prefs.outputDir ?? null
            : null,
      };
    }

    return { global, projects };
  } catch {
    return { global: DEFAULT_GLOBAL, projects: {} };
  }
}

function saveStore(store: WorkspacePrefsStore): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

let cachedStore: WorkspacePrefsStore | null = null;

function getStore(): WorkspacePrefsStore {
  if (!cachedStore) {
    cachedStore = loadStore();
  }
  return cachedStore;
}

function commit(mutator: (store: WorkspacePrefsStore) => void): void {
  const store = getStore();
  mutator(store);
  saveStore(store);
}

export function loadGlobalPrefs(): GlobalWorkspacePrefs {
  return { ...getStore().global };
}

export function saveGlobalPrefs(partial: Partial<GlobalWorkspacePrefs>): void {
  commit((store) => {
    store.global = { ...store.global, ...partial };
  });
}

export function loadProjectRenderPrefs(projectId: string): ProjectRenderPrefs {
  const stored = getStore().projects[projectId];
  return stored ? { ...stored } : { ...DEFAULT_RENDER };
}

export function saveProjectRenderPrefs(
  projectId: string,
  partial: Partial<ProjectRenderPrefs>,
): void {
  commit((store) => {
    const current = store.projects[projectId] ?? { ...DEFAULT_RENDER };
    store.projects[projectId] = { ...current, ...partial };
  });
}
