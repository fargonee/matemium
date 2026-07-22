import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "./api/tauri";
import config from "./config.json";
import type {
  ChatMessage,
  CodeEdit,
  Conversation,
  LintDiagnostic,
  LLMConfig,
  ProjectOpen,
  ProjectSummary,
  Settings,
  SidecarEventPayload,
  VideoOrientation,
  ChatCompletionResponse,
  AgentTraceEntry,
} from "./api/types";
import "./App.css";
import { ChatPanel } from "./components/ChatPanel";
import { CodeEditor, type CodeEditorHandle } from "./components/Editor";
import { ProjectsLanding } from "./components/ProjectsLanding";
import { CommunityGallery } from "./components/CommunityGallery";
import { ObsidianLoadingScreen } from "./components/ObsidianLoadingScreen";
import { ProjectSidebar, type WorkspaceItem } from "./components/ProjectSidebar";
import { BriefJsonEditor, STRUCTURED_BRIEF_FILES } from "./components/BriefJsonEditor";
import { OutputsExplorer } from "./components/OutputsExplorer";
import { ProjectMediaLibrary } from "./components/ProjectMediaLibrary";
import { MediaPreviewModal } from "./components/MediaPreviewModal";
import { RenderModal } from "./components/RenderModal";
import { SettingsScreen } from "./components/SettingsScreen";
import { BottomDock } from "./components/BottomDock";
import { ResizeHandle } from "./components/ResizeHandle";
import { resolveBottomDockDefault, useBottomDockTab } from "./hooks/useBottomDockTab";
import { usePanelLayout } from "./hooks/usePanelLayout";
import { useSidecarEvents } from "./hooks/useSidecarEvents";
import { pinnedModelOptions } from "./modelCatalog";
import { applyCodeEdit } from "./utils/codeEdit";
import { formatError, tailLines } from "./utils/errors";
import { parseSections } from "./utils/sections";
import {
  applySidecarEvent,
  beginRenderJob,
  cancelRenderJob,
  failPipeline,
  INITIAL_PIPELINE_STATE,
  isRenderActive,
  type RenderPipelineState,
} from "./utils/renderPipeline";
import {
  mediaPreviewItemFromPath,
  type MediaPreviewItem,
} from "./utils/mediaPreview";
import {
  loadGlobalPrefs,
  loadProjectRenderPrefs,
  saveGlobalPrefs,
  saveProjectRenderPrefs,
  type ProjectFile,
} from "./utils/workspacePrefs";
type StatusKind = "idle" | "ok" | "error" | "busy";

const PROJECT_FILES: ProjectFile[] = ["scenes", "helpers", "passport", "description", "tape", "roadmap", "narration"];
const EMPTY_CONTENTS: Record<ProjectFile, string> = {
  scenes: "", helpers: "", passport: "", description: "", tape: "", roadmap: "", narration: "",
};
const EMPTY_DIRTY: Record<ProjectFile, boolean> = {
  scenes: false, helpers: false, passport: false, description: false, tape: false, roadmap: false, narration: false,
};
const FILE_LABELS: Record<ProjectFile, string> = {
  scenes: "scenes.py", helpers: "helpers.py", passport: "Passport", description: "Description",
  tape: "Tape", roadmap: "Roadmap", narration: "Narration",
};

function projectFiles(opened: ProjectOpen): Record<ProjectFile, string> {
  return Object.fromEntries(PROJECT_FILES.map((file) => [file, opened.files[file] ?? ""])) as Record<ProjectFile, string>;
}

function briefValidationErrors(files: Record<ProjectFile, string>): Partial<Record<ProjectFile, string>> {
  const errors: Partial<Record<ProjectFile, string>> = {};
  for (const file of ["passport", "roadmap"] as const) {
    try {
      JSON.parse(files[file]);
    } catch {
      errors[file] = "Invalid JSON";
    }
  }
  return errors;
}

export default function App() {
  const inTauri = api.runningInTauri();
  const editorRef = useRef<CodeEditorHandle>(null);
  const appBodyRef = useRef<HTMLDivElement>(null);
  const editorBottomRef = useRef<HTMLDivElement>(null);
  const renderCancelledRef = useRef(false);
  const activeChatRequestRef = useRef(0);
  const chatCancelRequestedRef = useRef(false);

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<ProjectOpen | null>(null);
  const [fileContents, setFileContents] = useState<Record<ProjectFile, string>>(EMPTY_CONTENTS);
  const [dirtyFiles, setDirtyFiles] = useState(EMPTY_DIRTY);
  const [activeFile, setActiveFile] = useState<ProjectFile>(
    () => loadGlobalPrefs().activeFile,
  );
  const [activeWorkspaceItem, setActiveWorkspaceItem] = useState<WorkspaceItem>(
    () => loadGlobalPrefs().activeFile,
  );
  const [newName, setNewName] = useState("");
  const [scenes, setScenes] = useState<string[]>([]);
  const [selectedScene, setSelectedScene] = useState("");
  const [quality, setQuality] = useState("low");
  const [orientation, setOrientation] = useState<VideoOrientation>("portrait");
  const [outputDir, setOutputDir] = useState<string | null>(null);
  const [diagnostics, setDiagnostics] = useState<LintDiagnostic[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [status, setStatus] = useState("Ready");
  const [statusKind, setStatusKind] = useState<StatusKind>("idle");
  const [busy, setBusy] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [linting, setLinting] = useState(false);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [chatInput, setChatInput] = useState("");
  const [pendingEdit, setPendingEdit] = useState<CodeEdit | null>(null);
  const [, setChatProgressStep] = useState<
    "idle" | "preparing" | "retrieving" | "thinking" | "processing" | "refreshing"
  >("idle");
  const [chatContextMatches, setChatContextMatches] = useState<Array<{ file: string; score?: number }>>([]);
  const [appliedEditErrors, setAppliedEditErrors] = useState<LintDiagnostic[]>([]);
  const [uploadedReferences, setUploadedReferences] = useState<string[]>([]);
  const [lastChatResponse, setLastChatResponse] = useState<ChatCompletionResponse | null>(null);
  const [liveAgentTrace, setLiveAgentTrace] = useState<AgentTraceEntry[]>([]);
  const liveAgentTraceKeysRef = useRef<Set<string>>(new Set());

  const [settings, setSettings] = useState<Settings>({
    serverUrl: config.serverUrl,
    apiToken: null,
    bottomDockDefault: "progress",
    usePersonalLlm: true,
    llmProvider: "openrouter",
    useAutonomousAgent: true,
  });
  const [llmProfile, setLlmProfile] = useState<LLMConfig | null>(null);
  const [pipeline, setPipeline] = useState<RenderPipelineState>(INITIAL_PIPELINE_STATE);
  const { tab: bottomDockTab, selectTab: selectBottomDockTab, focusProgress } =
    useBottomDockTab(resolveBottomDockDefault(settings));
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsInitialSection, setSettingsInitialSection] = useState<"general" | "models">("general");
  const [renderOpen, setRenderOpen] = useState(false);
  const [outputsRefreshToken, setOutputsRefreshToken] = useState(0);
  const [mediaPreview, setMediaPreview] = useState<MediaPreviewItem | null>(null);
  const [readiness, setReadiness] = useState<api.Readiness | null>(null);
  const [localModelReady, setLocalModelReady] = useState(true);
  const [localModelStatusMsg, setLocalModelStatusMsg] = useState("");
  const [downloadedModels, setDownloadedModels] = useState<Record<string, boolean>>({
    "llm-qwen-coder-3b-q4": false,
    "llm-qwen-coder-7b-q4": false,
    "llm-llama-8b-q4": false,
  });
  const [showGallery, setShowGallery] = useState(false);
  const {
    layout,
    setBottomPanelOpen,
    setSidebarOpen,
    setContainerWidth,
    setEditorRegionHeight,
    setChatWidthFromPointer,
    setSidebarWidthFromPointer,
    resizeBottom,
    maximizeBottom,
    setEditorOpen,
  } = usePanelLayout();

  useEffect(() => {
    const element = appBodyRef.current;
    if (!element) return;

    const syncWidth = () => setContainerWidth(element.getBoundingClientRect().width);
    syncWidth();

    const observer = new ResizeObserver(syncWidth);
    observer.observe(element);
    window.addEventListener("resize", syncWidth);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", syncWidth);
    };
  }, [setContainerWidth, project]);

  // Track editor-bottom-region height to allow bottom dock to resize up to full available space
  useEffect(() => {
    const syncHeight = () => {
      const el = editorBottomRef.current;
      if (el) {
        setEditorRegionHeight(el.getBoundingClientRect().height);
      }
    };

    syncHeight();

    const ro = new ResizeObserver(syncHeight);
    const observeIfPresent = () => {
      const el = editorBottomRef.current;
      if (el) ro.observe(el);
    };
    observeIfPresent();

    window.addEventListener("resize", syncHeight);

    // Catch ref attachment on first project mount
    const t1 = setTimeout(syncHeight, 0);
    const t2 = setTimeout(syncHeight, 80);
    const t3 = setTimeout(observeIfPresent, 0);

    return () => {
      window.removeEventListener("resize", syncHeight);
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      ro.disconnect();
    };
  }, [setEditorRegionHeight, project?.id]);

  const resizeSidebarFromPointer = useCallback(
    (clientX: number) => {
      const body = appBodyRef.current;
      if (!body) return;
      setSidebarWidthFromPointer(clientX, body.getBoundingClientRect().left);
    },
    [setSidebarWidthFromPointer],
  );

  const resizeChatFromPointer = useCallback(
    (clientX: number) => {
      const body = appBodyRef.current;
      if (!body) return;
      setChatWidthFromPointer(clientX, body.getBoundingClientRect().right);
    },
    [setChatWidthFromPointer],
  );

  const handleBottomResize = useCallback(
    (delta: number) => {
      resizeBottom(delta);
    },
    [resizeBottom],
  );

  const handleMaximizeBottom = useCallback(() => {
    const el = editorBottomRef.current;
    if (el) {
      setEditorRegionHeight(el.getBoundingClientRect().height);
    }
    maximizeBottom();
  }, [maximizeBottom, setEditorRegionHeight]);

  const appendLog = useCallback((line: string) => {
    setLog((prev) => [...prev.slice(-199), line]);
  }, []);

  const setStatusMessage = (message: string, kind: StatusKind = "idle") => {
    setStatus(message);
    setStatusKind(kind);
  };

  const refreshProjects = useCallback(async () => {
    const list = await api.projectList();
    setProjects(list);
  }, []);

  const loadScenes = useCallback(async (projectId: string, fallback?: string) => {
    const result = await api.sidecarListScenes(projectId);
    setScenes(result.scenes);
    const next =
      result.scenes.find((scene) => scene === fallback) ??
      result.scenes[0] ??
      "";
    setSelectedScene(next);
    return next;
  }, []);

  const applyProjectRenderPrefs = useCallback((projectId: string, sceneFallback?: string) => {
    const prefs = loadProjectRenderPrefs(projectId);
    setQuality(prefs.quality);
    setOrientation(prefs.orientation);
    setOutputDir(prefs.outputDir);
    return prefs.scene || sceneFallback || "";
  }, []);

  const updateActiveFile = useCallback((file: ProjectFile) => {
    setActiveFile(file);
    setActiveWorkspaceItem(file);
    saveGlobalPrefs({ activeFile: file });
  }, []);

  const updateSelectedScene = useCallback(
    (scene: string) => {
      setSelectedScene(scene);
      if (project?.id) {
        saveProjectRenderPrefs(project.id, { scene });
      }
    },
    [project?.id],
  );

  const updateQuality = useCallback(
    (nextQuality: string) => {
      setQuality(nextQuality);
      if (project?.id) {
        saveProjectRenderPrefs(project.id, { quality: nextQuality });
      }
    },
    [project?.id],
  );

  const updateOrientation = useCallback(
    (nextOrientation: VideoOrientation) => {
      setOrientation(nextOrientation);
      if (project?.id) {
        saveProjectRenderPrefs(project.id, { orientation: nextOrientation });
      }
    },
    [project?.id],
  );

  const updateOutputDir = useCallback(
    (nextOutputDir: string | null) => {
      setOutputDir(nextOutputDir);
      if (project?.id) {
        saveProjectRenderPrefs(project.id, { outputDir: nextOutputDir });
      }
    },
    [project?.id],
  );

  const handleSidecarEvent = useCallback(
    (payload: SidecarEventPayload) => {
      const detail =
        payload.data.message ??
        payload.data.code ??
        JSON.stringify(payload.data);
      appendLog(`[${payload.event}] ${String(detail)}`);
      if (payload.event === "agent_event") {
        const entry = {
          type: String(payload.data.event_type ?? "progress"),
          summary: typeof payload.data.summary === "string" ? payload.data.summary : undefined,
          details: payload.data.details && typeof payload.data.details === "object" ? payload.data.details as Record<string, unknown> : undefined,
          sequence: typeof payload.data.sequence === "number" ? payload.data.sequence : undefined,
          timestamp_ms: typeof payload.data.timestamp_ms === "number" ? payload.data.timestamp_ms : Date.now(),
        };
        const key = `${entry.sequence ?? "no-seq"}:${entry.type}:${entry.summary ?? ""}`;
        if (!liveAgentTraceKeysRef.current.has(key)) {
          liveAgentTraceKeysRef.current.add(key);
          setLiveAgentTrace((previous) => [...previous.slice(-99), entry]);
        }
      }
      setPipeline((prev) => applySidecarEvent(prev, payload));
      if (
        payload.event === "render_started" ||
        payload.event === "render_progress"
      ) {
        focusProgress();
      }
      if (payload.event === "render_complete") {
        setOutputsRefreshToken((n) => n + 1);
        setActiveWorkspaceItem("renders");
        const video =
          typeof payload.data.video === "string" ? payload.data.video : null;
        if (video) {
          const item = mediaPreviewItemFromPath(video);
          if (item) setMediaPreview(item);
        }
      }
    },
    [appendLog, focusProgress],
  );

  useSidecarEvents(handleSidecarEvent);

  const refreshReadiness = useCallback(async () => {
    try {
      const r = await api.getReadiness();
      setReadiness(r);

      // Query statuses of all 3 local models to know which ones are ready/downloaded
      const qwen3b = await api.getAssetStatus("llm-qwen-coder-3b-q4");
      const qwen7b = await api.getAssetStatus("llm-qwen-coder-7b-q4");
      const llama8b = await api.getAssetStatus("llm-llama-8b-q4");

      const nextDownloaded = {
        "llm-qwen-coder-3b-q4": !!(qwen3b?.[0]?.downloaded && qwen3b?.[0]?.verified),
        "llm-qwen-coder-7b-q4": !!(qwen7b?.[0]?.downloaded && qwen7b?.[0]?.verified),
        "llm-llama-8b-q4": !!(llama8b?.[0]?.downloaded && llama8b?.[0]?.verified),
      };
      setDownloadedModels(nextDownloaded);

      const currentModelId = settings.localLlmModel || "llm-qwen-coder-3b-q4";
      const currentStatus = currentModelId === "llm-qwen-coder-3b-q4" ? qwen3b?.[0] :
                            currentModelId === "llm-qwen-coder-7b-q4" ? qwen7b?.[0] :
                            llama8b?.[0];

      if (settings.useLocalLlm) {
        if (currentStatus) {
          const isModelReady = !!(currentStatus.downloaded && currentStatus.verified);
          setLocalModelReady(isModelReady);
          if (!isModelReady) {
            const pct = typeof currentStatus.progress === "number" ? ` (${currentStatus.progress.toFixed(1)}%)` : "";
            setLocalModelStatusMsg(`Downloading offline model${pct}...`);
          } else {
            setLocalModelStatusMsg("");
          }
        } else {
          setLocalModelReady(false);
          setLocalModelStatusMsg("Offline model not downloaded yet.");
        }
      } else {
        setLocalModelReady(true);
        setLocalModelStatusMsg("");
      }
    } catch (e) {
      // ignore, default not ready
    }
  }, [settings.useLocalLlm, settings.localLlmModel]);

  const refreshLlmProfile = useCallback(async () => {
    if (!inTauri) return;
    try {
      const profile = await api.cloudGetProfile();
      setLlmProfile(profile);
    } catch (e) {
      // ignore profile fetch errors (e.g. no token)
    }
  }, [inTauri]);

  useEffect(() => {
    // initial check
    void refreshReadiness();
    const id = setInterval(() => { void refreshReadiness(); }, 2000);
    return () => clearInterval(id);
  }, [refreshReadiness]);

  // Listen to asset progress and loading to refresh readiness faster
  useEffect(() => {
    // we can also listen for asset-progress
    let unlistenAsset: (() => void) | undefined;
    let unlistenSidecar: (() => void) | undefined;
    void import("@tauri-apps/api/event").then(({ listen }) => {
      listen("asset-progress", () => { void refreshReadiness(); }).then(fn => { unlistenAsset = fn; });
      listen("sidecar-event", (e: any) => {
        if (e.payload?.event === "loading_phase" || e.payload?.event === "status_update") {
          void refreshReadiness();
        }
      }).then(fn => { unlistenSidecar = fn; });
    });
    return () => {
      unlistenAsset?.();
      unlistenSidecar?.();
    };
  }, [refreshReadiness]);

  const coreReady = Boolean(
    readiness?.fullyReady
      || readiness?.phase === "ready"
      || (readiness?.assetsReady && readiness?.engineReady),
  );
  // A downloaded GGUF is required only when Aider uses the local model
  // transport. Cloud-backed Aider still executes beside the workspace.
  const isReady = coreReady && (!settings.useLocalLlm || localModelReady);
  const readinessMessage = settings.useLocalLlm && !localModelReady
    ? (localModelStatusMsg || "Waiting for offline model...") 
    : (readiness?.message || "Checking readiness...");

  // Auto trigger asset download on start if not ready (demo for phase 4)
  useEffect(() => {
    if (readiness && !readiness.assetsReady) {
      // fire and forget; UI will show via polling
      void api.startAssetDownload("tinytex-linux").catch(() => {});
    }
  }, [readiness?.assetsReady]);

  // Auto-trigger intelligence/RAG load in background once engine is ready
  // (retrieve handler calls ensure_intelligence_loaded; keyword fallback if no vector deps)
  useEffect(() => {
    if (readiness?.engineReady && !readiness?.intelligenceReady && projects.length > 0) {
      const firstId = projects[0].id;
      // dummy query to kick off the lazy load
      void api.sidecarRetrieve(firstId, "__preload__", 1).catch(() => {});
    }
  }, [readiness?.engineReady, readiness?.intelligenceReady, projects]);

  const saveFile = useCallback(
    async (file: ProjectFile, projectId = project?.id) => {
      if (!projectId || !dirtyFiles[file]) return;
      if (!isReady) {
        setStatusMessage("App not ready — " + readinessMessage, "idle");
        return;
      }
      setSaving(true);
      try {
        if (file === "scenes") await api.projectSave(projectId, fileContents.scenes);
        else await api.projectSaveFile(projectId, file, fileContents[file]);
        setDirtyFiles((prev) => ({ ...prev, [file]: false }));
      } finally {
        setSaving(false);
      }
    },
    [dirtyFiles, fileContents, project?.id, isReady, readinessMessage],
  );

  const flushDirtyFiles = useCallback(
    async (projectId = project?.id) => {
      if (!projectId) return;
      const pending = (Object.keys(dirtyFiles) as ProjectFile[]).filter(
        (file) => dirtyFiles[file],
      );
      for (const file of pending) {
        setSaving(true);
        try {
          if (file === "scenes") await api.projectSave(projectId, fileContents.scenes);
          else await api.projectSaveFile(projectId, file, fileContents[file]);
          setDirtyFiles((prev) => ({ ...prev, [file]: false }));
        } finally {
          setSaving(false);
        }
      }
    },
    [dirtyFiles, fileContents, project?.id],
  );

  const runLint = useCallback(
    async (options?: { silent?: boolean }) => {
      if (!project) return;
      if (!isReady && !options?.silent) {
        setStatusMessage("App not ready — " + readinessMessage, "idle");
        return;
      }
      setLinting(true);
      try {
        const result = await api.sidecarLint(project.id);
        setDiagnostics(result.diagnostics ?? []);
        const errors = result.diagnostics.filter((d) => d.severity === "error").length;
        if (!options?.silent) {
          if (errors > 0) {
            setStatusMessage(`Lint: ${errors} error(s)`, "error");
          } else {
            setStatusMessage("Lint passed", "ok");
          }
          appendLog(`[lint] ${result.diagnostics.length} diagnostic(s)`);
        } else if (errors > 0) {
          setStatusMessage(`Lint: ${errors} error(s)`, "error");
        }
      } catch (error) {
        if (!options?.silent) {
          appendLog(`[error] ${formatError(error)}`);
        }
      } finally {
        setLinting(false);
      }
    },
    [appendLog, project],
  );

  const loadProjectReferences = useCallback(async (projectId: string) => {
    try {
      const res = await api.sidecarListReferences(projectId);
      if (res.status === "success" && res.references) {
        setUploadedReferences(res.references);
      }
    } catch (e) {
      console.error("Failed to load project references:", e);
    }
  }, []);

  const openProjectById = useCallback(
    async (projectId: string) => {
      if (!isReady) {
        setStatusMessage("App not ready — " + readinessMessage, "idle");
        return;
      }
      if (project) {
        await flushDirtyFiles(project.id);
      }

      const opened = await api.projectOpen(projectId);
      setProject(opened);
      setFileContents(projectFiles(opened));
      setDirtyFiles(EMPTY_DIRTY);
      setDiagnostics([]);
      setPendingEdit(null);

      // Load conversations for the opened project
      try {
        const convList = await api.listConversations(opened.id);
        setConversations(convList);
        if (convList.length > 0) {
          const activeId = convList[0].id;
          setActiveConversationId(activeId);
          setChatMessages(convList[0].messages);
        } else {
          const newConv: Conversation = {
            id: Date.now().toString(),
            title: "New Conversation",
            created_at: new Date().toISOString(),
            messages: [],
          };
          await api.saveConversation(opened.id, newConv);
          setConversations([newConv]);
          setActiveConversationId(newConv.id);
          setChatMessages([]);
        }
      } catch (e) {
        console.error("Failed to load conversations:", e);
        setChatMessages([]);
      }
      setPipeline(INITIAL_PIPELINE_STATE);
      const sceneFallback = applyProjectRenderPrefs(opened.id, opened.scene_class);
      const scene = await loadScenes(opened.id, sceneFallback);
      saveProjectRenderPrefs(opened.id, { scene });
      setStatusMessage(`Opened ${opened.name}`, "ok");
      void loadProjectReferences(opened.id);
    },
    [applyProjectRenderPrefs, flushDirtyFiles, loadScenes, project, isReady, readinessMessage, loadProjectReferences],
  );

  const closeProject = useCallback(async () => {
    if (project) {
      await flushDirtyFiles(project.id);
    }
    await refreshProjects();
    setProject(null);
    setFileContents(EMPTY_CONTENTS);
    setDirtyFiles(EMPTY_DIRTY);
    setScenes([]);
    setSelectedScene("");
    setDiagnostics([]);
    setStatusMessage("Ready", "idle");
  }, [flushDirtyFiles, project, refreshProjects]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't run shortcuts if no project is active
      if (!project) return;

      const isMac = /Mac|iPod|iPhone|iPad/.test(navigator.userAgent);
      const isMod = isMac ? e.metaKey : e.ctrlKey;

      if (isMod) {
        const key = e.key.toLowerCase();

        // 1. Toggle Sidebar: Ctrl+B / Cmd+B
        if (key === "b" && !e.shiftKey && !e.altKey) {
          e.preventDefault();
          setSidebarOpen(layout.sidebarOpen !== false ? false : true);
        }

        // 2. Toggle Bottom Panel: Ctrl+J / Cmd+J or Ctrl+` / Cmd+`
        if (key === "j" || e.key === "`") {
          e.preventDefault();
          setBottomPanelOpen(!layout.bottomPanelOpen);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [project, layout, setSidebarOpen, setBottomPanelOpen]);

  useEffect(() => {
    if (!inTauri) return;

    void (async () => {
      try {
        setBusy(true);
        await refreshProjects();
        const loadedSettings = await api.settingsGet();
        setSettings(loadedSettings);
        if (loadedSettings.apiToken) {
          void refreshLlmProfile();
        }
        const ping = await api.sidecarPing();
        appendLog(`[ping] ${JSON.stringify(ping)}`);
        if (
          typeof ping.render_pipeline === "string" &&
          ping.render_pipeline !== "portrait-pixels-v2"
        ) {
          appendLog(
            "[warn] sidecar render pipeline is stale — run ./desktop/scripts/build-sidecar.sh and restart",
          );
        }
        setStatusMessage("Engine connected", "ok");
      } catch (error) {
        setStatusMessage(formatError(error), "error");
        appendLog(`[error] ${formatError(error)}`);
      } finally {
        setBusy(false);
      }
    })();
  }, [appendLog, inTauri, refreshProjects]);

  useEffect(() => {
    if (!project) return;
    const hasDirty = Object.values(dirtyFiles).some(Boolean);
    if (!hasDirty) return;

    const timer = window.setTimeout(() => {
      void (async () => {
        if (dirtyFiles.scenes) {
          await saveFile("scenes");
          await runLint({ silent: true });
        }
        for (const file of PROJECT_FILES.filter((candidate) => candidate !== "scenes" && dirtyFiles[candidate])) {
          await saveFile(file);
        }
      })();
    }, 800);

    return () => window.clearTimeout(timer);
  }, [dirtyFiles, fileContents, project, runLint, saveFile]);

  useEffect(() => {
    if (!project) return;
    void runLint({ silent: true });
  }, [project?.id, runLint]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    if (!isReady) {
      setStatusMessage("App not ready yet — waiting for assets and engine", "idle");
      return;
    }
    try {
      setBusy(true);
      const created = await api.projectCreate(newName.trim());
      setNewName("");
      await refreshProjects();
      await openProjectById(created.id);
    } catch (error) {
      setStatusMessage(formatError(error), "error");
      appendLog(`[error] ${formatError(error)}`);
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (projectId: string) => {
    if (!window.confirm("Delete this project and all renders?")) return;
    try {
      setBusy(true);
      await api.projectDelete(projectId);
      if (project?.id === projectId) {
        setProject(null);
        setFileContents(EMPTY_CONTENTS);
        setDirtyFiles(EMPTY_DIRTY);
        setScenes([]);
        setSelectedScene("");
      }
      await refreshProjects();
      setStatusMessage("Project deleted", "ok");
    } catch (error) {
      setStatusMessage(formatError(error), "error");
    } finally {
      setBusy(false);
    }
  };

  const prepareForValidation = useCallback(async () => {
    await flushDirtyFiles();
  }, [flushDirtyFiles]);

  const handleCancelRender = useCallback(async () => {
    renderCancelledRef.current = true;
    try {
      await api.sidecarCancel();
      setPipeline((prev) => cancelRenderJob(prev));
      setStatusMessage("Render cancelled", "idle");
      appendLog("[render] cancelled by user");
    } catch (error) {
      appendLog(`[render-cancel-error] ${formatError(error)}`);
    } finally {
      setBusy(false);
    }
  }, [appendLog]);

  const handleRender = async () => {
    if (!project) return;
    renderCancelledRef.current = false;
    setRenderOpen(false);
    try {
      setBusy(true);
      await flushDirtyFiles();
      setPipeline(
        beginRenderJob({
          scene: selectedScene || project.scene_class,
          quality,
          orientation,
        }),
      );
      appendLog(`[render] starting (${quality}, ${orientation})`);
      const result = await api.sidecarRender(
        project.id,
        selectedScene || undefined,
        quality,
        orientation,
        outputDir,
      );
      setOutputsRefreshToken((n) => n + 1);
      setActiveWorkspaceItem("renders");
      await refreshProjects();
      const aspect = result.aspect_ratio ?? (orientation === "landscape" ? "16:9" : "9:16");
      const dims =
        result.pixel_width && result.pixel_height
          ? `${result.pixel_width}×${result.pixel_height}`
          : null;
      setStatusMessage(
        dims ? `Render complete (${aspect}, ${dims})` : `Render complete (${aspect})`,
        "ok",
      );
      appendLog(
        `[render] video=${result.video} (${aspect}${dims ? `, ${dims}` : ""})`,
      );
      if (result.export_video && result.export_video !== result.video) {
        appendLog(`[render] export=${result.export_video}`);
      }
    } catch (error) {
      if (renderCancelledRef.current) {
        return;
      }
      const message = formatError(error);
      setStatusMessage(message, "error");
      setPipeline((prev) => failPipeline(prev, message));
      appendLog(tailLines(`[render-error]\n${message}`));
      if (resolveBottomDockDefault(settings) === "progress") {
        focusProgress();
      }
    } finally {
      if (!renderCancelledRef.current) {
        setBusy(false);
      }
    }
  };

  const handleGenerateAudio = async () => {
    const text = chatInput.trim() || chatMessages[chatMessages.length - 1]?.content || "";
    if (!text) {
      setStatusMessage("Enter text or have a chat message for audio", "error");
      return;
    }
    try {
      setBusy(true);
      const llmConfig = { tts_provider: settings.llmProvider || "openrouter", use_personal_llm: true };
      const res = await api.cloudGenerateAudio(text, "alloy", llmConfig);
      if (res.audioBase64) {
        appendLog(`[audio] generated ${text.length} chars`);
        setStatusMessage("Audio generated (base64 in log for now - integrate with media preview)", "ok");
        // For live preview parallel safety, just log; future can save via project
      } else {
        setStatusMessage("Audio generation failed", "error");
      }
    } catch (error) {
      setStatusMessage(formatError(error), "error");
    } finally {
      setBusy(false);
    }
  };

  const handleUpdateSettingsField = useCallback(async (updates: Partial<Settings>) => {
    const nextSettings = { ...settings, ...updates };
    try {
      await api.settingsSet(nextSettings);
      setSettings(nextSettings);
      // Automatically refresh readiness to reflect changes like local model paths
      void refreshReadiness();
    } catch (e) {
      console.error("Failed to update settings field", e);
    }
  }, [settings, refreshReadiness]);

  const handleSelectConversation = useCallback(async (convId: string) => {
    if (!project) return;
    try {
      const convList = await api.listConversations(project.id);
      setConversations(convList);
      const conv = convList.find((c) => c.id === convId);
      if (conv) {
        setActiveConversationId(convId);
        setChatMessages(conv.messages);
      }
    } catch (e) {
      console.error("Failed to switch conversation:", e);
    }
  }, [project]);

  const handleNewConversation = useCallback(async () => {
    if (!project) return;
    try {
      const newConv: Conversation = {
        id: Date.now().toString(),
        title: `Conversation ${conversations.length + 1}`,
        created_at: new Date().toISOString(),
        messages: [],
      };
      await api.saveConversation(project.id, newConv);
      setConversations((prev) => [newConv, ...prev]);
      setActiveConversationId(newConv.id);
      setChatMessages([]);
      setChatInput("");
      setPendingEdit(null);
      setAppliedEditErrors([]);
      setChatContextMatches([]);
      setLastChatResponse(null);
      setLiveAgentTrace([]);
      setStatusMessage("Started new conversation", "ok");
    } catch (e) {
      console.error("Failed to start new conversation:", e);
      setStatusMessage(formatError(e), "error");
    }
  }, [project, conversations.length]);

  const handleDeleteConversation = useCallback(async (convId: string) => {
    if (!project) return;
    try {
      await api.deleteConversation(project.id, convId);
      const nextConversations = conversations.filter((c) => c.id !== convId);
      setConversations(nextConversations);
      
      // If the active conversation was deleted, select another one or create a new one
      if (activeConversationId === convId) {
        if (nextConversations.length > 0) {
          setActiveConversationId(nextConversations[0].id);
          setChatMessages(nextConversations[0].messages);
        } else {
          const newConv: Conversation = {
            id: Date.now().toString(),
            title: "New Conversation",
            created_at: new Date().toISOString(),
            messages: [],
          };
          await api.saveConversation(project.id, newConv);
          setConversations([newConv]);
          setActiveConversationId(newConv.id);
          setChatMessages([]);
        }
      }
    } catch (e) {
      console.error("Failed to delete conversation:", e);
    }
  }, [project, conversations, activeConversationId]);

  useEffect(() => {
    if (!project || !activeConversationId) return;
    
    // Find active conversation in state list
    const activeConv = conversations.find((c) => c.id === activeConversationId);
    if (!activeConv) return;
    
    // Check if messages have actually changed to prevent infinite write loops
    const hasChanged = JSON.stringify(activeConv.messages) !== JSON.stringify(chatMessages);
    if (!hasChanged) return;
    
    // If user's first prompt has been sent, auto-rename the conversation based on the prompt!
    let updatedTitle = activeConv.title;
    if (activeConv.messages.length === 0 && chatMessages.length > 0) {
      const firstUserMsg = chatMessages.find(m => m.role === "user");
      if (firstUserMsg && firstUserMsg.content) {
        const cleanContent = firstUserMsg.content.replace(/^### Active Reference Attachments:[\s\S]*### User Question:/i, "").trim();
        updatedTitle = cleanContent.slice(0, 24).trim() || "New Conversation";
        if (cleanContent.length > 24) updatedTitle += "...";
      }
    }

    const updatedConv: Conversation = {
      ...activeConv,
      title: updatedTitle,
      messages: chatMessages,
    };
    
    // Update local state list
    setConversations((prev) => prev.map((c) => (c.id === activeConversationId ? updatedConv : c)));
    
    // Persist to disk
    void api.saveConversation(project.id, updatedConv);
  }, [chatMessages, activeConversationId, project?.id]);

  const getLlmConfigForCall = () => {
    const activeModel = settings.useLocalLlm ? settings.localLlmModel : settings.externalLlmModel;
    if (!settings.useLocalLlm) {
      return {
        llm_provider: settings.llmProvider || "openrouter",
        use_personal_llm: true,
        model: activeModel,
        use_autonomous_agent: !!settings.useAutonomousAgent,
        agent_runtime_version: "aider-v1",
      };
    }
    return {
      model: activeModel,
      use_autonomous_agent: !!settings.useAutonomousAgent,
      agent_runtime_version: "aider-v1",
    };
  };

  const handleCancelChat = useCallback(async () => {
    if (!chatBusy) return;

    chatCancelRequestedRef.current = true;
    activeChatRequestRef.current += 1;
    setChatBusy(false);
    setBusy(false);
    setChatProgressStep("idle");
    setStatusMessage("Chat cancelled", "idle");
    appendLog("[chat] cancelled by user");
    setLiveAgentTrace((previous) => [
      ...previous.slice(-99),
      {
        type: "terminal",
        summary: "Chat task cancelled by user.",
        details: { outcome: "cancelled" },
        sequence: previous.length + 1,
      },
    ]);
    setChatMessages((previous) => [
      ...previous,
      { role: "assistant", content: "Cancelled by user." },
    ]);

    try {
      await api.sidecarCancel();
    } catch (error) {
      appendLog(`[chat-cancel-error] ${formatError(error)}`);
    }
  }, [appendLog, chatBusy, setStatusMessage]);

  const handleChatSend = async (promptOverride?: string) => {
    const inputContent = promptOverride !== undefined ? promptOverride : chatInput;
    if (!inputContent.trim()) return;
    if (!isReady) {
      setStatusMessage("App not ready — " + readinessMessage, "idle");
      return;
    }
    const requestId = activeChatRequestRef.current + 1;
    activeChatRequestRef.current = requestId;
    chatCancelRequestedRef.current = false;
    const isCurrentChatRequest = () =>
      activeChatRequestRef.current === requestId && !chatCancelRequestedRef.current;

    const activeReferences = [...uploadedReferences];
    const userMessage: ChatMessage = {
      role: "user",
      content: inputContent.trim(),
      references: activeReferences.length > 0 ? activeReferences : undefined,
    };
    const nextMessages = [...chatMessages, userMessage];
    setChatMessages(nextMessages);
    if (promptOverride === undefined) {
      setChatInput("");
    }
    setUploadedReferences([]); // Clear the visual selection chips immediately!
    setChatContextMatches([]);
    setAppliedEditErrors([]);
    liveAgentTraceKeysRef.current.clear();
    setLiveAgentTrace([]);

    try {
      setBusy(true);
      setChatBusy(true);
      setChatProgressStep("preparing");
      const llmConfig = getLlmConfigForCall();
      if (settings.useAutonomousAgent && project) {
        // Aider works against disk. Flush the editor first so its
        // precondition is the exact content the user currently sees.
        for (const file of PROJECT_FILES) {
          if (file === "scenes") await api.projectSave(project.id, fileContents.scenes);
          else await api.projectSaveFile(project.id, file, fileContents[file]);
          if (!isCurrentChatRequest()) return;
        }
        setDirtyFiles(EMPTY_DIRTY);
      }
      const scenesExcerpt = fileContents.scenes;
      let finalMessages = [...nextMessages];

      // Inject reasoning level system prompts if medium or high to guide model behavior
      if (settings.reasoningLevel === "medium") {
        finalMessages.push({
          role: "system",
          content: "System instruction override: Use step-by-step reasoning and careful logical planning before outputting any code modifications. Analyze coordinates and element positioning systematically."
        });
      } else if (settings.reasoningLevel === "high") {
        finalMessages.push({
          role: "system",
          content: "Perform rigorous mathematical verification, visual-overlap analysis, and careful planning. Return only concise conclusions, proposed actions, and evidence; do not expose private chain-of-thought."
        });
      }

      // Phase 6: use advanced RAG chunks if intelligence ready (reduces token use)
      if (isReady && project) {
        setChatProgressStep("retrieving");
        try {
          const searchFiles = [
            "scenes.py",
            "helpers.py",
            "brief/passport.json",
            "brief/description.md",
            "brief/tape.md",
            "brief/roadmap.json",
            "brief/narration.md",
            ...activeReferences.map((name) => `references/${name}`),
          ];
          const rag = await api.sidecarRetrieve(project.id, inputContent.trim(), 6, searchFiles);
          if (!isCurrentChatRequest()) return;
          if (rag.results && rag.results.length > 0) {
            const seen = new Set<string>();
            const matches: Array<{ file: string; score?: number }> = [];
            for (const r of rag.results) {
              if (!seen.has(r.file)) {
                seen.add(r.file);
                matches.push({
                  file: r.file,
                  score: r.score !== undefined ? r.score : 1.0,
                });
              }
            }
            setChatContextMatches(matches);

            // Separate codebase RAG chunks from reference chunks
            const codebaseChunks = rag.results.filter((r: any) => !r.file.startsWith("references/"));
            const referenceChunks = rag.results.filter((r: any) => r.file.startsWith("references/"));

            // Retrieval context is supplemental. Keep scenesExcerpt as the exact
            // current file so edit preconditions can be validated generically.
            const codebaseText = codebaseChunks.map((r: any) => `# File: ${r.file}\n${r.chunk}`).join("\n\n---\n\n") || "";
            if (codebaseText) {
              finalMessages.push({
                role: "system",
                content: `Retrieved workspace excerpts (untrusted reference context; current scenes.py is supplied separately):\n${codebaseText}`,
              });
            }

            // Reference context goes directly into finalMessages to guarantee the AI sees them clearly as prompt attachments
            if (referenceChunks.length > 0) {
              const referenceText = referenceChunks.map((r: any) => `[ATTACHMENT FILE: ${r.file}]\n${r.chunk}`).join("\n\n---\n\n");
              const enrichedUserContent = `### Active Reference Attachments:\n${referenceText}\n\n### User Question:\n${inputContent.trim()}`;
              
              let userIndex = finalMessages.length - 1;
              while (userIndex > 0 && finalMessages[userIndex].role !== "user") userIndex -= 1;
              finalMessages[userIndex] = {
                role: "user",
                content: enrichedUserContent,
              };
            }
          }
        } catch {}
      }

      setChatProgressStep("thinking");
      const response = await api.cloudChat(
        finalMessages,
        project?.id,
        activeConversationId,
        scenesExcerpt,
        llmConfig,
      );
      if (!isCurrentChatRequest()) return;
      setChatProgressStep("processing");
      setLastChatResponse(response);
      setChatMessages((prev) => [...prev, response.message]);
      if (response.code_edit) {
        setPendingEdit(response.code_edit);
      }
      if (settings.useAutonomousAgent && project) {
        const refreshed = await api.projectOpen(project.id);
        if (!isCurrentChatRequest()) return;
        setProject(refreshed);
        setFileContents(projectFiles(refreshed));
        setDirtyFiles(EMPTY_DIRTY);
        setPendingEdit(null);
        const sceneResult = await api.sidecarListScenes(project.id);
        if (!isCurrentChatRequest()) return;
        setScenes(sceneResult.scenes ?? []);
        if (selectedScene && !(sceneResult.scenes ?? []).includes(selectedScene)) {
          setSelectedScene(sceneResult.scenes?.[0] ?? "");
        }
      }
      appendLog(`[chat] model=${response.model} runtime=${response.agent_runtime_version ?? "single-turn"} source=${response.billing_mode ?? (settings.useLocalLlm ? "local" : "byo_external")} stub=${response.stub ?? false}`);
      // Consume and clear temporary reference files after successful message send
      if (project && activeReferences.length > 0) {
        for (const name of activeReferences) {
          try {
            await api.sidecarDeleteReference(project.id, name);
          } catch (e) {
            console.error(`Failed to delete reference file ${name} after sending chat:`, e);
          }
        }
      }

      // Refresh provider/profile metadata after external provider use.
      if (!settings.useLocalLlm && settings.apiToken) {
        setChatProgressStep("refreshing");
        void refreshLlmProfile();
      }
    } catch (error) {
      if (!isCurrentChatRequest() || chatCancelRequestedRef.current) {
        return;
      }
      const errMsg = formatError(error);
      setStatusMessage(errMsg, "error");
      appendLog(`[chat-error] ${errMsg}`);
      if (errMsg.toLowerCase().includes("openrouter free model quota")) {
        try {
          setSettings(await api.settingsGet());
        } catch {}
      }
      if (errMsg.includes("402") || errMsg.toLowerCase().includes("api key")) {
        setStatusMessage("Connect OpenRouter or add your provider API key in settings.", "error");
      }
    } finally {
      if (activeChatRequestRef.current === requestId) {
        setBusy(false);
        setChatBusy(false);
        setChatProgressStep("idle");
      }
    }
  };

  const handleApplyEdit = async () => {
    if (!pendingEdit || !project) return;
    try {
      const next = applyCodeEdit(fileContents.scenes, pendingEdit);
      setFileContents((prev) => ({ ...prev, scenes: next }));
      setDirtyFiles((prev) => ({ ...prev, scenes: false }));
      updateActiveFile("scenes");
      setPendingEdit(null);

      // Auto-save the applied edit
      setSaving(true);
      await api.projectSave(project.id, next);
      setSaving(false);

      // Auto-lint to verify correctness
      setLinting(true);
      const lintRes = await api.sidecarLint(project.id);
      setDiagnostics(lintRes.diagnostics ?? []);
      const errors = (lintRes.diagnostics ?? []).filter((d: any) => d.severity === "error");
      if (errors.length > 0) {
        setAppliedEditErrors(errors);
        setStatusMessage(`Edit applied with ${errors.length} lint error(s)`, "error");
      } else {
        setAppliedEditErrors([]);
        setStatusMessage("Applied AI edit successfully", "ok");
      }
      setLinting(false);
    } catch (error) {
      setStatusMessage(formatError(error), "error");
      setSaving(false);
      setLinting(false);
    }
  };

  const handleFixAppliedEditErrors = () => {
    if (appliedEditErrors.length === 0) return;
    const errorDesc = appliedEditErrors.map((e) => `Line ${e.line}: ${e.message}`).join("\n");
    const fixPrompt = `I applied the previous edit, but it introduced the following lint error(s):\n${errorDesc}\n\nPlease fix these errors.`;
    setAppliedEditErrors([]);
    void handleChatSend(fixPrompt);
  };

  const handleUploadReferenceFile = useCallback(
    async (file: File) => {
      if (!project?.id) return;
      setBusy(true);
      setStatusMessage(`Uploading reference document: ${file.name}...`, "busy");
      appendLog(`[Upload] Starting upload for reference file: ${file.name}`);

      try {
        const reader = new FileReader();
        reader.onload = async () => {
          try {
            const dataUrl = reader.result as string;
            // Get the base64 content from the data URL
            const base64Content = dataUrl.split(",")[1];
            
            const res = await api.sidecarUploadReference(project.id, file.name, base64Content, null);
            if (res.status === "success") {
              setStatusMessage(`Reference '${file.name}' successfully uploaded and indexed!`, "ok");
              appendLog(`[Upload] Uploaded reference successfully: ${res.path} (Indexed: ${res.indexed})`);
              void loadProjectReferences(project.id);
            } else {
              throw new Error("Upload response status not success");
            }
          } catch (e: any) {
            setStatusMessage(`Upload failed: ${String(e.message || e)}`, "error");
            appendLog(`[Upload Error] ${String(e.message || e)}`);
          } finally {
            setBusy(false);
          }
        };
        reader.onerror = () => {
          setStatusMessage("FileReader error during upload", "error");
          appendLog("[Upload Error] FileReader failed to read file binary data.");
          setBusy(false);
        };
        reader.readAsDataURL(file);
      } catch (err: any) {
        setStatusMessage(`Upload failed: ${String(err.message || err)}`, "error");
        appendLog(`[Upload Error] ${String(err.message || err)}`);
        setBusy(false);
      }
    },
    [project?.id, appendLog, setStatusMessage, loadProjectReferences]
  );

  const handleDeleteReferenceFile = useCallback(
    async (fileName: string) => {
      if (!project?.id) return;
      setBusy(true);
      setStatusMessage(`Removing reference file: ${fileName}...`, "busy");
      appendLog(`[Delete] Deleting reference file: ${fileName}`);

      try {
        const res = await api.sidecarDeleteReference(project.id, fileName);
        if (res.status === "success") {
          setStatusMessage(`Reference file '${fileName}' successfully removed.`, "ok");
          appendLog(`[Delete] Successfully deleted reference file from workspace.`);
          setUploadedReferences((prev) => prev.filter((r) => r !== fileName));
        } else {
          throw new Error("Delete failed");
        }
      } catch (err: any) {
        setStatusMessage(`Delete failed: ${String(err.message || err)}`, "error");
        appendLog(`[Delete Error] ${String(err.message || err)}`);
      } finally {
        setBusy(false);
      }
    },
    [project?.id, appendLog, setStatusMessage]
  );

  const handlePublish = async () => {
    if (!project || !publishTitle.trim()) return;
    setPublishing(true);
    try {
      const tags = publishTags ? publishTags.split(",").map(t => t.trim()).filter(Boolean) : [];
      const res = await api.publishAnimation(
        project.id,
        publishTitle.trim(),
        publishDesc.trim() || undefined,
        tags,
        selectedScene,
        undefined // duration from last render if available
      );
      setStatusMessage(`Published! ID: ${res.id} — ${res.message || 'Pending YT upload'}`, "ok");
      setPublishOpen(false);
      setPublishTitle("");
      setPublishDesc("");
      setPublishTags("");
      // Refresh gallery if open
      if (showGallery) {
        // trigger reload somehow
      }
    } catch (error) {
      setStatusMessage(formatError(error), "error");
    } finally {
      setPublishing(false);
    }
  };

  const handleSaveSettings = async (nextSettings: Settings = settings) => {
    try {
      await api.settingsSet(nextSettings);
      setSettings(nextSettings);
      setSettingsOpen(false);
      setStatusMessage("Settings saved", "ok");
      // Refresh provider profile when token or prefs are saved.
      if (nextSettings.apiToken) {
        void refreshLlmProfile();
      }
    } catch (error) {
      setStatusMessage(formatError(error), "error");
      throw error;
    }
  };

  const activeCode = fileContents[activeFile];
  const activeIsProjectFile = PROJECT_FILES.includes(activeWorkspaceItem as ProjectFile);
  const workspaceLabel = activeIsProjectFile
    ? FILE_LABELS[activeWorkspaceItem as ProjectFile]
    : activeWorkspaceItem === "renders"
      ? "Output history"
      : activeWorkspaceItem.replace("media-", "").replace(/^./, (letter) => letter.toUpperCase());
  const sections = parseSections(fileContents.scenes);
  const lintErrors = diagnostics.filter((d) => d.severity === "error").length;
  const lintWarnings = diagnostics.filter((d) => d.severity === "warning").length;
  const hasUnsaved = Object.values(dirtyFiles).some(Boolean);

  if (!inTauri) {
    return (
      <div className="empty-state">
        <div>
          <p>Matemium runs inside the Tauri desktop shell.</p>
          <p>Start with: <code>cd desktop &amp;&amp; cargo tauri dev</code></p>
        </div>
      </div>
    );
  }

  // Phase 5: Loading screen + gallery always accessible (header always shown)
  const isFullyReady = isReady;
  const loadingProgress = readiness?.engineReady ? 90 : readiness?.assetsReady ? 65 : readiness ? 30 : 5;
  const showLoadingScreen = !isFullyReady;

  // Phase 8: Publish flow
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishTitle, setPublishTitle] = useState("");
  const [publishDesc, setPublishDesc] = useState("");
  const [publishTags, setPublishTags] = useState("");
  const [publishing, setPublishing] = useState(false);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <h1>Matemium</h1>
          <span className="header-tag">Canvas</span>
        </div>
        {project ? (
          <>
            <button type="button" className="btn btn-ghost" onClick={() => void closeProject()}>
              Library
            </button>
            <span className="project-name">{project.name}</span>
          </>
        ) : null}

        {/* Professional LLM status */}
        {llmProfile && (
          <span 
            className="llm-status" 
            title="Click to refresh provider status. External AI uses your connected provider key."
            onClick={() => void refreshLlmProfile()}
          >
            {settings.useLocalLlm ? "Local" : "BYO provider"}
            {llmProfile.llm_provider && ` (${llmProfile.llm_provider})`}
          </span>
        )}

        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            setSettingsInitialSection("general");
            setSettingsOpen(true);
          }}
        >
          Settings
        </button>
        <span className={`status-pill ${statusKind}`}>{busy ? "Working…" : status}</span>
      </header>

      {showGallery ? (
        <CommunityGallery onClose={() => setShowGallery(false)} />
      ) : showLoadingScreen ? (
        <ObsidianLoadingScreen
          progress={loadingProgress}
          message={readinessMessage}
          phase={readiness?.phase}
          onBrowseGallery={() => setShowGallery(true)}
          onRetry={() => void refreshReadiness()}
        />
      ) : (
        <div
          ref={appBodyRef}
          className={`app-body ${project ? "app-body-project" : "app-body-landing"}`}
          style={
            project
              ? ({
                  "--sidebar-width": layout.sidebarOpen !== false ? `${layout.sidebarWidth}px` : "0px",
                  "--chat-width": `${layout.chatWidth}px`,
                  gridTemplateColumns: layout.sidebarOpen !== false
                    ? `var(--sidebar-width, 260px) 8px minmax(280px, 1fr) 8px var(--chat-width, 320px)`
                    : `minmax(280px, 1fr) 8px var(--chat-width, 320px)`,
                } as React.CSSProperties)
              : undefined
          }
        >
        {project ? (
          <>
            {layout.sidebarOpen !== false ? (
              <>
                <aside className="sidebar">
                  <ProjectSidebar
                    projectName={project.name}
                    activeItem={activeWorkspaceItem}
                    dirtyFiles={dirtyFiles}
                    validationErrors={briefValidationErrors(fileContents)}
                    sections={sections}
                    onSelect={(item) => {
                      if (PROJECT_FILES.includes(item as ProjectFile)) updateActiveFile(item as ProjectFile);
                      else setActiveWorkspaceItem(item);
                    }}
                    onJump={(line) => editorRef.current?.jumpToLine(line)}
                  />
                </aside>
                <ResizeHandle
                  orientation="vertical"
                  onDragPosition={resizeSidebarFromPointer}
                />
              </>
            ) : null}
          </>
        ) : null}

        <section className="main-column">
          {project ? (
            <>
              <div className="toolbar toolbar-editor">
                <div className="editor-file-tabs">
                  <span className="workspace-surface-title">{workspaceLabel}</span>
                  {activeIsProjectFile && dirtyFiles[activeWorkspaceItem as ProjectFile] ? <span className="file-dirty">Unsaved</span> : null}
                </div>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy || linting || saving}
                  onClick={() => {
                    if (!isReady) {
                      setStatusMessage("App not ready — " + readinessMessage, "idle");
                      return;
                    }
                    setRenderOpen(true);
                  }}
                >
                  Render
                </button>
                {project && (
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={!isReady || publishing}
                    onClick={() => setPublishOpen(true)}
                    title="Publish thin metadata to community gallery (YouTube)"
                  >
                    Publish to Community
                  </button>
                )}
                <span className="toolbar-meta">
                  {saving
                    ? "Saving…"
                    : hasUnsaved
                      ? "Unsaved changes"
                      : linting
                        ? "Linting…"
                        : lintErrors > 0
                          ? `${lintErrors} lint error${lintErrors === 1 ? "" : "s"}`
                          : lintWarnings > 0
                            ? `${lintWarnings} warning${lintWarnings === 1 ? "" : "s"}`
                            : selectedScene
                              ? `Scene: ${selectedScene}`
                              : null}
                </span>
              </div>

              <div className="editor-bottom-region" ref={editorBottomRef}>
                {layout.editorOpen ? (
                  <div className="editor-stage">
                    {activeWorkspaceItem === "renders" ? (
                      <div className="workspace-browser-surface">
                        <OutputsExplorer projectId={project.id} busy={busy} refreshToken={outputsRefreshToken} onStatus={(message, kind = "ok") => setStatusMessage(message, kind)} onPreviewMedia={setMediaPreview} />
                      </div>
                    ) : activeWorkspaceItem.startsWith("media-") ? (
                      <ProjectMediaLibrary
                        projectId={project.id}
                        category={activeWorkspaceItem.replace("media-", "") as "images" | "video" | "audio"}
                        onStatus={(message, kind = "ok") => setStatusMessage(message, kind)}
                        onPreview={setMediaPreview}
                      />
                    ) : STRUCTURED_BRIEF_FILES.includes(activeFile) ? (
                      <BriefJsonEditor file={activeFile as "passport" | "roadmap"} value={activeCode} readOnly={!isReady} onChange={(value) => {
                        setFileContents((prev) => ({ ...prev, [activeFile]: value }));
                        setDirtyFiles((prev) => ({ ...prev, [activeFile]: true }));
                      }} />
                    ) : (
                      <CodeEditor
                        ref={editorRef}
                        value={activeCode}
                        language={activeFile === "scenes" || activeFile === "helpers" ? "python" : "markdown"}
                        diagnostics={activeFile === "scenes" ? diagnostics : []}
                        onChange={(value) => {
                          setFileContents((prev) => ({ ...prev, [activeFile]: value }));
                          setDirtyFiles((prev) => ({ ...prev, [activeFile]: true }));
                        }}
                        readOnly={!isReady}
                      />
                    )}
                    {!isReady && (
                      <div className="editor-locked-overlay">
                        <div className="locked-message">
                          Editor locked until ready<br />
                          <span className="locked-detail">{readinessMessage}</span>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <button
                    type="button"
                    className="editor-bump"
                    title="Show code editor"
                    onClick={() => {
                      const el = editorBottomRef.current;
                      if (el) setEditorRegionHeight(el.getBoundingClientRect().height);
                      setEditorOpen(true);
                    }}
                  >
                    <span className="editor-bump-tab">
                      <span className="bottom-panel-bump-icon" aria-hidden>
                        ▼
                      </span>
                      Editor
                    </span>
                  </button>
                )}

                {layout.bottomPanelOpen ? (
                  <>
                    <div
                      className="bottom-dock-chrome"
                      onMouseDown={() => {
                        // Ensure we have a fresh measurement of available height for clamp/max on drag start
                        const el = editorBottomRef.current;
                        if (el) setEditorRegionHeight(el.getBoundingClientRect().height);
                      }}
                    >
                      <ResizeHandle
                        orientation="horizontal"
                        onDrag={handleBottomResize}
                        onDoubleClick={handleMaximizeBottom}
                      />
                    </div>
                    <div
                      className="bottom-panels"
                      style={
                        layout.editorOpen
                          ? { flex: `0 0 ${layout.bottomHeight}px` }
                          : { flex: '1 1 auto' }
                      }
                    >
                      <BottomDock
                        tab={bottomDockTab}
                        onTabChange={selectBottomDockTab}
                        log={log.join("\n")}
                        pipeline={pipeline}
                        renderActive={isRenderActive(pipeline)}
                        onCancelRender={() => void handleCancelRender()}
                        projectId={project?.id}
                        onMaximize={handleMaximizeBottom}
                      />
                    </div>
                  </>
                ) : (
                  <button
                    type="button"
                    className="bottom-panel-bump"
                    title="Show bottom panel"
                    onClick={() => {
                      const el = editorBottomRef.current;
                      if (el) setEditorRegionHeight(el.getBoundingClientRect().height);
                      setBottomPanelOpen(true);
                    }}
                  >
                    <span className="bottom-panel-bump-tab">
                      <span className="bottom-panel-bump-icon" aria-hidden>
                        ▲
                      </span>
                      Panel
                    </span>
                  </button>
                )}
              </div>
            </>
          ) : (
            <>
              {!isReady && (
                <div className="readiness-banner">
                  {readinessMessage} — workspace actions disabled
                </div>
              )}
              <ProjectsLanding
              projects={projects}
              newName={newName}
              busy={busy || !isReady}
              onNewNameChange={setNewName}
              onCreate={() => void handleCreate()}
              onOpen={(id) => void openProjectById(id)}
              onDelete={(id) => void handleDelete(id)}
              readinessMessage={!isReady ? readinessMessage : undefined}
            />
            </>
          )}
        </section>

        {project ? (
          <>
            <ResizeHandle
              orientation="vertical"
              onDragPosition={resizeChatFromPointer}
            />
            {!isReady && project && (
              <div className="readiness-banner" style={{ gridColumn: "1 / -1" }}>
                {readinessMessage} — creation/editing/rendering blocked
              </div>
            )}
            <aside className="chat-panel">
              <ChatPanel
                messages={chatMessages}
                pendingEdit={pendingEdit}
                input={chatInput}
                busy={busy}
                contextMatches={chatContextMatches}
                validationErrors={appliedEditErrors}
                onFixErrors={handleFixAppliedEditErrors}
                onInputChange={setChatInput}
                onSend={() => void handleChatSend()}
                onCancel={() => void handleCancelChat()}
                canCancel={chatBusy}
                onApplyEdit={handleApplyEdit}
                llmStatus={
                  llmProfile
                    ? settings.useLocalLlm
                      ? "Local"
                      : `BYO (${settings.llmProvider || llmProfile.llm_provider || "OpenRouter"})`
                    : undefined
                }
                onGenerateAudio={() => void handleGenerateAudio()}
                disabled={!isReady}
                onUploadFile={handleUploadReferenceFile}
                uploadedReferences={uploadedReferences}
                onDeleteReference={handleDeleteReferenceFile}
                useLocalLlm={!!settings.useLocalLlm}
                onToggleLocalLlm={(val) => void handleUpdateSettingsField({ useLocalLlm: val })}
                localLlmModel={settings.localLlmModel || "llm-qwen-coder-3b-q4"}
                onLocalLlmModelChange={(val) => void handleUpdateSettingsField({ localLlmModel: val })}
                externalLlmModel={settings.externalLlmModel || "openai/gpt-4o-mini"}
                externalModelOptions={pinnedModelOptions(settings, settings.llmProvider || "openrouter")}
                onManageExternalModels={() => {
                  setSettingsInitialSection("models");
                  setSettingsOpen(true);
                }}
                onExternalLlmModelChange={(val) => void handleUpdateSettingsField({
                  externalLlmModel: val,
                  ...(val === "openrouter/free" ? { llmProvider: "openrouter" } : {}),
                })}
                openRouterFreeDisabledUntil={settings.openrouterFreeDisabledUntil ?? null}
                reasoningLevel={settings.reasoningLevel || "low"}
                onReasoningLevelChange={(val) => void handleUpdateSettingsField({ reasoningLevel: val })}
                downloadedModels={downloadedModels}
                conversations={conversations}
                activeConversationId={activeConversationId}
                onSelectConversation={handleSelectConversation}
                onNewConversation={handleNewConversation}
                onDeleteConversation={handleDeleteConversation}
                autonomousEnabled={!!settings.useAutonomousAgent}
                onToggleAutonomous={(enabled) => void handleUpdateSettingsField({ useAutonomousAgent: enabled })}
                configuredRuntime="aider-v1"
                responseMetadata={lastChatResponse ? {
                  runtime: lastChatResponse.agent_runtime_version ?? "single-turn",
                  model: lastChatResponse.model,
                  provider: lastChatResponse.provider ?? (settings.useLocalLlm ? "local" : settings.llmProvider || "openrouter"),
                  billingMode: lastChatResponse.billing_mode ?? (settings.useLocalLlm ? "local" : "byo_external"),
                  requestId: lastChatResponse.request_id ?? lastChatResponse.id,
                  stub: !!lastChatResponse.stub,
                  trace: lastChatResponse.agent_trace ?? [],
                } : undefined}
                liveAgentTrace={liveAgentTrace}
              />
            </aside>
          </>
        ) : null}
      </div>
      )}

      {settingsOpen && (
        <SettingsScreen
          settings={settings}
          busy={busy}
          initialSection={settingsInitialSection}
          onChange={setSettings}
          onClose={() => setSettingsOpen(false)}
          onSave={handleSaveSettings}
        />
      )}

      <MediaPreviewModal
        item={mediaPreview}
        projectId={project?.id ?? null}
        onClose={() => setMediaPreview(null)}
        onStatus={(message, kind = "ok") => setStatusMessage(message, kind)}
      />

      {project ? (
        <RenderModal
          open={renderOpen}
          projectId={project.id}
          defaultOutputDir={project.renders_dir}
          scenes={scenes}
          scene={selectedScene}
          quality={quality}
          orientation={orientation}
          outputDir={outputDir}
          lintErrors={lintErrors}
          lintWarnings={lintWarnings}
          busy={busy}
          onSceneChange={updateSelectedScene}
          onQualityChange={updateQuality}
          onOrientationChange={updateOrientation}
          onOutputDirChange={updateOutputDir}
          onClose={() => setRenderOpen(false)}
          onPrepare={prepareForValidation}
          onRender={() => void handleRender()}
        />
      ) : null}

      {/* Thin Publish Modal */}
      {publishOpen && (
        <div className="modal" onClick={() => setPublishOpen(false)}>
          <div className="modal-content publish-modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Publish to Community</h3>
            <p className="modal-hint">Thin publish: only metadata sent. Video hosted on YouTube. Requires engine ready.</p>
            <input value={publishTitle} onChange={(e) => setPublishTitle(e.target.value)} placeholder="Title (required)" />
            <textarea value={publishDesc} onChange={(e) => setPublishDesc(e.target.value)} placeholder="Description (optional)" rows={3} />
            <input value={publishTags} onChange={(e) => setPublishTags(e.target.value)} placeholder="Tags (comma separated)" />
            <div className="modal-actions">
              <button className="btn btn-ghost" onClick={() => setPublishOpen(false)}>Cancel</button>
              <button className="btn btn-primary" disabled={!publishTitle.trim() || publishing} onClick={() => void handlePublish()}>
                {publishing ? 'Publishing…' : 'Publish'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
