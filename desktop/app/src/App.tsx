import { useCallback, useEffect, useRef, useState } from "react";

import * as api from "./api/tauri";
import config from "./config.json";
import type {
  ChatMessage,
  CodeEdit,
  LintDiagnostic,
  LLMConfig,
  ProjectOpen,
  ProjectSummary,
  Settings,
  SidecarEventPayload,
  VideoOrientation,
} from "./api/types";
import "./App.css";
import { ChatPanel } from "./components/ChatPanel";
import { CodeEditor, type CodeEditorHandle } from "./components/Editor";
import { ProjectsLanding } from "./components/ProjectsLanding";
import { CommunityGallery } from "./components/CommunityGallery";
import { ObsidianLoadingScreen } from "./components/ObsidianLoadingScreen";
import { ProjectSidebar, type SidebarView } from "./components/ProjectSidebar";
import { MediaPreviewModal } from "./components/MediaPreviewModal";
import { RenderModal } from "./components/RenderModal";
import { SettingsScreen } from "./components/SettingsScreen";
import { BottomDock } from "./components/BottomDock";
import { ResizeHandle } from "./components/ResizeHandle";
import { resolveBottomDockDefault, useBottomDockTab } from "./hooks/useBottomDockTab";
import { usePanelLayout } from "./hooks/usePanelLayout";
import { useSidecarEvents } from "./hooks/useSidecarEvents";
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

const EMPTY_DIRTY: Record<ProjectFile, boolean> = { scenes: false, assets: false };

export default function App() {
  const inTauri = api.runningInTauri();
  const editorRef = useRef<CodeEditorHandle>(null);
  const appBodyRef = useRef<HTMLDivElement>(null);
  const editorBottomRef = useRef<HTMLDivElement>(null);
  const renderCancelledRef = useRef(false);

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [project, setProject] = useState<ProjectOpen | null>(null);
  const [fileContents, setFileContents] = useState({ scenes: "", assets: "" });
  const [dirtyFiles, setDirtyFiles] = useState(EMPTY_DIRTY);
  const [activeFile, setActiveFile] = useState<ProjectFile>(
    () => loadGlobalPrefs().activeFile,
  );
  const [sidebarView, setSidebarView] = useState<SidebarView>(
    () => loadGlobalPrefs().sidebarView,
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
  const [saving, setSaving] = useState(false);
  const [linting, setLinting] = useState(false);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [pendingEdit, setPendingEdit] = useState<CodeEdit | null>(null);

  const [settings, setSettings] = useState<Settings>({
    serverUrl: config.serverUrl,
    apiToken: null,
    bottomDockDefault: "progress",
    usePersonalLlm: false,
    llmProvider: "openai",
  });
  const [llmProfile, setLlmProfile] = useState<LLMConfig | null>(null);
  const [pipeline, setPipeline] = useState<RenderPipelineState>(INITIAL_PIPELINE_STATE);
  const { tab: bottomDockTab, selectTab: selectBottomDockTab, focusProgress } =
    useBottomDockTab(resolveBottomDockDefault(settings));
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [renderOpen, setRenderOpen] = useState(false);
  const [outputsRefreshToken, setOutputsRefreshToken] = useState(0);
  const [mediaPreview, setMediaPreview] = useState<MediaPreviewItem | null>(null);
  const [readiness, setReadiness] = useState<api.Readiness | null>(null);
  const [showGallery, setShowGallery] = useState(false);
  const {
    layout,
    setBottomPanelOpen,
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

  const updateSidebarView = useCallback((view: SidebarView) => {
    setSidebarView(view);
    saveGlobalPrefs({ sidebarView: view });
  }, []);

  const updateActiveFile = useCallback((file: ProjectFile) => {
    setActiveFile(file);
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
      setPipeline((prev) => applySidecarEvent(prev, payload));
      if (
        payload.event === "render_started" ||
        payload.event === "render_progress"
      ) {
        focusProgress();
      }
      if (payload.event === "render_complete") {
        setOutputsRefreshToken((n) => n + 1);
        updateSidebarView("outputs");
        const video =
          typeof payload.data.video === "string" ? payload.data.video : null;
        if (video) {
          const item = mediaPreviewItemFromPath(video);
          if (item) setMediaPreview(item);
        }
      }
    },
    [appendLog, focusProgress, updateSidebarView],
  );

  useSidecarEvents(handleSidecarEvent);

  const refreshReadiness = useCallback(async () => {
    try {
      const r = await api.getReadiness();
      setReadiness(r);
    } catch (e) {
      // ignore, default not ready
    }
  }, []);

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
    void import("@tauri-apps/api/event").then(({ listen }) => {
      listen("asset-progress", () => { void refreshReadiness(); }).then(fn => { unlistenAsset = fn; });
      listen("sidecar-event", (e: any) => {
        if (e.payload?.event === "loading_phase" || e.payload?.event === "status_update") {
          void refreshReadiness();
        }
      }).then(() => {});
    });
    return () => { unlistenAsset?.(); };
  }, [refreshReadiness]);

  const isReady = readiness?.fullyReady || readiness?.phase === "ready" || (readiness?.assetsReady && readiness?.engineReady);
  const readinessMessage = readiness?.message || "Checking readiness...";

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
        if (file === "scenes") {
          await api.projectSave(projectId, fileContents.scenes);
        } else {
          await api.projectSaveAssets(projectId, fileContents.assets);
        }
        setDirtyFiles((prev) => ({ ...prev, [file]: false }));
      } finally {
        setSaving(false);
      }
    },
    [dirtyFiles, fileContents.assets, fileContents.scenes, project?.id, isReady, readinessMessage],
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
          if (file === "scenes") {
            await api.projectSave(projectId, fileContents.scenes);
          } else {
            await api.projectSaveAssets(projectId, fileContents.assets);
          }
          setDirtyFiles((prev) => ({ ...prev, [file]: false }));
        } finally {
          setSaving(false);
        }
      }
    },
    [dirtyFiles, fileContents.assets, fileContents.scenes, project?.id],
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
      setFileContents({
        scenes: opened.scenes_content,
        assets: opened.assets_content ?? "",
      });
      setDirtyFiles(EMPTY_DIRTY);
      setDiagnostics([]);
      setChatMessages([]);
      setPendingEdit(null);
      setPipeline(INITIAL_PIPELINE_STATE);
      const sceneFallback = applyProjectRenderPrefs(opened.id, opened.scene_class);
      const scene = await loadScenes(opened.id, sceneFallback);
      saveProjectRenderPrefs(opened.id, { scene });
      setStatusMessage(`Opened ${opened.name}`, "ok");
    },
    [applyProjectRenderPrefs, flushDirtyFiles, loadScenes, project, isReady, readinessMessage],
  );

  const closeProject = useCallback(async () => {
    if (project) {
      await flushDirtyFiles(project.id);
    }
    await refreshProjects();
    setProject(null);
    setFileContents({ scenes: "", assets: "" });
    setDirtyFiles(EMPTY_DIRTY);
    setScenes([]);
    setSelectedScene("");
    setDiagnostics([]);
    setStatusMessage("Ready", "idle");
  }, [flushDirtyFiles, project, refreshProjects]);

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
    const hasDirty = dirtyFiles.scenes || dirtyFiles.assets;
    if (!hasDirty) return;

    const timer = window.setTimeout(() => {
      void (async () => {
        if (dirtyFiles.scenes) {
          await saveFile("scenes");
          await runLint({ silent: true });
        }
        if (dirtyFiles.assets) {
          await saveFile("assets");
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
        setFileContents({ scenes: "", assets: "" });
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
      updateSidebarView("outputs");
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
      const llmConfig = settings.usePersonalLlm
        ? { tts_provider: settings.llmProvider, use_personal_llm: true }
        : undefined;
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

  const getLlmConfigForCall = () => {
    if (settings.usePersonalLlm && settings.llmProvider) {
      return {
        llm_provider: settings.llmProvider,
        use_personal_llm: true,
      };
    }
    return undefined;
  };

  const handleChatSend = async () => {
    if (!chatInput.trim()) return;
    if (!isReady) {
      setStatusMessage("App not ready — " + readinessMessage, "idle");
      return;
    }
    const userMessage: ChatMessage = { role: "user", content: chatInput.trim() };
    const nextMessages = [...chatMessages, userMessage];
    setChatMessages(nextMessages);
    setChatInput("");
    try {
      setBusy(true);
      const llmConfig = getLlmConfigForCall();
      let scenesExcerpt = fileContents.scenes;
      // Phase 6: use RAG chunks if intelligence ready (reduces token use)
      if (isReady && project) {
        try {
          const rag = await api.sidecarRetrieve(project.id, chatInput.trim() || userMessage.content, 6);
          const ragText = rag.results?.map((r: any) => `// ${r.file}\n${r.chunk}`).join("\n\n---\n\n") || "";
          if (ragText) {
            scenesExcerpt = ragText + "\n\n// --- full scenes below if needed ---\n" + fileContents.scenes.slice(0, 3000);
          }
        } catch {}
      }
      const response = await api.cloudChat(
        nextMessages,
        project?.id,
        scenesExcerpt,
        llmConfig,
      );
      setChatMessages((prev) => [...prev, response.message]);
      if (response.code_edit) {
        setPendingEdit(response.code_edit);
      }
      appendLog(`[chat] model=${response.model} stub=${response.stub ?? false} personal=${!!llmConfig}`);
      // Refresh credits/profile after platform use
      if (!llmConfig && settings.apiToken) {
        void refreshLlmProfile();
      }
    } catch (error) {
      const errMsg = formatError(error);
      setStatusMessage(errMsg, "error");
      appendLog(`[chat-error] ${errMsg}`);
      // Handle insufficient credits nicely (402 from server)
      if (errMsg.includes("402") || errMsg.toLowerCase().includes("credit")) {
        setStatusMessage("Insufficient platform credits. Buy more on the web dashboard.", "error");
      }
    } finally {
      setBusy(false);
    }
  };

  const handleApplyEdit = () => {
    if (!pendingEdit) return;
    try {
      const next = applyCodeEdit(fileContents.scenes, pendingEdit);
      setFileContents((prev) => ({ ...prev, scenes: next }));
      setDirtyFiles((prev) => ({ ...prev, scenes: true }));
      updateActiveFile("scenes");
      setPendingEdit(null);
      setStatusMessage("Applied AI edit", "ok");
    } catch (error) {
      setStatusMessage(formatError(error), "error");
    }
  };

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
      // Refresh LLM profile/credits when token or prefs saved
      if (nextSettings.apiToken) {
        void refreshLlmProfile();
      }
    } catch (error) {
      setStatusMessage(formatError(error), "error");
      throw error;
    }
  };

  const activeCode = fileContents[activeFile];
  const sections = parseSections(fileContents.scenes);
  const lintErrors = diagnostics.filter((d) => d.severity === "error").length;
  const lintWarnings = diagnostics.filter((d) => d.severity === "warning").length;
  const hasUnsaved = dirtyFiles.scenes || dirtyFiles.assets;

  if (!inTauri) {
    return (
      <div className="empty-state">
        <div>
          <p>Matemium Canvas runs inside the Tauri desktop shell.</p>
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
            title="Click to refresh credits. Platform uses our tokens (margin priced). Personal = your keys from web."
            onClick={() => void refreshLlmProfile()}
          >
            {settings.usePersonalLlm ? 'Personal' : `Platform • ${llmProfile.llm_credits ?? '—'} credits`}
            {llmProfile.llm_provider && ` (${llmProfile.llm_provider})`}
          </span>
        )}

        <button type="button" className="btn btn-ghost" onClick={() => setSettingsOpen(true)}>
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
                  "--sidebar-width": `${layout.sidebarWidth}px`,
                  "--chat-width": `${layout.chatWidth}px`,
                } as React.CSSProperties)
              : undefined
          }
        >
        {project ? (
          <>
            <aside className="sidebar">
              <ProjectSidebar
                view={sidebarView}
                onViewChange={updateSidebarView}
                sections={sections}
                projectId={project.id}
                busy={busy}
                outputsRefreshToken={outputsRefreshToken}
                onJump={(line) => editorRef.current?.jumpToLine(line)}
                onStatus={(message, kind = "ok") => setStatusMessage(message, kind)}
                onPreviewMedia={setMediaPreview}
              />
            </aside>
            <ResizeHandle
              orientation="vertical"
              onDragPosition={resizeSidebarFromPointer}
            />
          </>
        ) : null}

        <section className="main-column">
          {project ? (
            <>
              <div className="toolbar toolbar-editor">
                <div className="editor-file-tabs">
                  <button
                    type="button"
                    className={`editor-file-tab ${activeFile === "scenes" ? "active" : ""}`}
                    onClick={() => updateActiveFile("scenes")}
                  >
                    scenes.py
                    {dirtyFiles.scenes ? <span className="file-dirty">•</span> : null}
                  </button>
                  <button
                    type="button"
                    className={`editor-file-tab ${activeFile === "assets" ? "active" : ""}`}
                    onClick={() => updateActiveFile("assets")}
                  >
                    assets.py
                    {dirtyFiles.assets ? <span className="file-dirty">•</span> : null}
                  </button>
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
                    <CodeEditor
                      ref={editorRef}
                      value={activeCode}
                      diagnostics={activeFile === "scenes" ? diagnostics : []}
                      onChange={(value) => {
                        setFileContents((prev) => ({ ...prev, [activeFile]: value }));
                        setDirtyFiles((prev) => ({ ...prev, [activeFile]: true }));
                      }}
                      readOnly={!isReady}
                    />
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
                onInputChange={setChatInput}
                onSend={() => void handleChatSend()}
                onApplyEdit={handleApplyEdit}
                llmStatus={
                  llmProfile
                    ? settings.usePersonalLlm
                      ? `Personal (${settings.llmProvider || "BYO"})`
                      : `Platform (${llmProfile.llm_credits ?? "?"} credits)`
                    : undefined
                }
                onGenerateAudio={() => void handleGenerateAudio()}
                disabled={!isReady}
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