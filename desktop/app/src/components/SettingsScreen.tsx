import { useEffect, useMemo, useState } from "react";

import * as api from "../api/tauri";
import config from "../config.json";
import type { AssetStatus, LocalModelCatalogEntry, ProviderModel, Settings } from "../api/types";
import {
  DEFAULT_PINNED_MODELS,
  formatModelMeta,
  modelDisplayName,
  pinnedModelIds,
  providerModelState,
} from "../modelCatalog";
import { formatBytes } from "../utils/formatBytes";
import { formatError } from "../utils/errors";

interface SettingsScreenProps {
  settings: Settings;
  busy: boolean;
  initialSection?: SettingsSection;
  onChange: (settings: Settings) => void;
  onClose: () => void;
  onSave: (settings: Settings) => Promise<void>;
}

type SettingsSection = "general" | "account" | "providers" | "models" | "ai";

const NAV_ITEMS: Array<{ id: SettingsSection; label: string; desc?: string }> = [
  { id: "general", label: "General", desc: "App behavior & connections" },
  { id: "account", label: "Account", desc: "Authentication & tokens" },
  { id: "providers", label: "AI Providers", desc: "External model keys" },
  { id: "models", label: "Model Picker", desc: "Pinned cloud models" },
  { id: "ai", label: "Offline AI", desc: "Local models & agent runtime" },
];

const PROVIDERS = [
  {
    id: "openrouter",
    name: "OpenRouter",
    status: "Supported",
    description: "Default external provider. OAuth and manual keys are supported.",
  },
  {
    id: "openai",
    name: "OpenAI Compatible",
    status: "Manual key",
    description: "Direct OpenAI-compatible requests from this computer.",
  },
  {
    id: "groq",
    name: "Groq",
    status: "Manual key",
    description: "Direct Groq requests from this computer.",
  },
  {
    id: "xai",
    name: "xAI",
    status: "Manual key",
    description: "Direct xAI requests from this computer.",
  },
  {
    id: "cerebras",
    name: "Cerebras Cloud",
    status: "Manual key",
    description: "Direct Cerebras Cloud requests from this computer.",
  },
  {
    id: "github",
    name: "GitHub Models",
    status: "Manual key",
    description: "Direct GitHub Models requests using a GitHub token with Models access.",
  },
  {
    id: "mistral",
    name: "Mistral",
    status: "Manual key",
    description: "Direct Mistral API requests from this computer.",
  },
  {
    id: "gemini",
    name: "Google AI Studio",
    status: "Manual key",
    description: "Direct Gemini API requests using a Google AI Studio key.",
  },
];

type LocalSystemProfile = {
  cores: number | null;
  memoryGB: number | null;
  platform: string;
};

type ModelRecommendation = {
  recommended: boolean;
  label?: string;
  reason: string;
};

type LocalModelCatalogCache = {
  query: string;
  entries: LocalModelCatalogEntry[];
};

const LOCAL_MODEL_CATALOG_CACHE_KEY = "matemium-local-model-catalog";

const BUILTIN_LOCAL_MODELS = [
  {
    id: "llm-qwen-coder-3b-q4",
    name: "Lite Tier: Qwen-2.5-Coder-3B-Instruct",
    meta: "1.9 GB · Q4_K_M",
    description: "Optimized for low RAM (4GB+) and CPU-only devices. Ultra-fast generation.",
  },
  {
    id: "llm-qwen-coder-7b-q4",
    name: "Balanced Tier: Qwen-2.5-Coder-7B-Instruct",
    meta: "4.7 GB · Q4_K_M",
    description: "Perfect math layouts and coding correctness. Recommended for dedicated GPUs and M1/M2/M3 Macs.",
  },
  {
    id: "llm-llama-8b-q4",
    name: "Elite Tier: Llama-3-8B-Instruct",
    meta: "4.9 GB · Q4_K_M",
    description: "Exceptional pedagogy and scripting style. Best for top-tier workstations.",
  },
];

function readLocalSystemProfile(): LocalSystemProfile {
  const nav = navigator as Navigator & { deviceMemory?: number };
  return {
    cores: typeof nav.hardwareConcurrency === "number" ? nav.hardwareConcurrency : null,
    memoryGB: typeof nav.deviceMemory === "number" ? nav.deviceMemory : null,
    platform: nav.platform || nav.userAgent || "unknown",
  };
}

function formatSystemProfile(profile: LocalSystemProfile): string {
  const parts: string[] = [];
  parts.push(profile.cores ? `${profile.cores} cores` : "cores unknown");
  parts.push(profile.memoryGB ? `${profile.memoryGB} GB RAM` : "RAM unknown");
  const platform = (() => {
    const raw = profile.platform.toLowerCase();
    if (raw.includes("mac")) return "macOS";
    if (raw.includes("win")) return "Windows";
    if (raw.includes("linux")) return "Linux";
    return "this device";
  })();
  parts.push(platform);
  return parts.join(" · ");
}

function recommendLocalModel(modelId: string, profile: LocalSystemProfile): ModelRecommendation {
  const memory = profile.memoryGB;
  const cores = profile.cores ?? 0;

  const lowSpec = memory === null || memory < 8 || cores <= 4;
  const midSpec = (memory ?? 0) >= 8 && (memory ?? 0) < 16 && cores >= 4;
  const highSpec = (memory ?? 0) >= 16 && cores >= 6;

  if (modelId === "llm-qwen-coder-3b-q4") {
    return {
      recommended: lowSpec,
      label: lowSpec ? "Recommended" : undefined,
      reason: lowSpec
        ? "Best fit for lighter systems and CPU-only use."
        : "Safe fallback if you want the smallest local footprint.",
    };
  }

  if (modelId === "llm-qwen-coder-7b-q4") {
    return {
      recommended: midSpec,
      label: midSpec ? "Recommended" : undefined,
      reason: midSpec
        ? "Balanced fit for this system's reported RAM and CPU class."
        : "Usually better on mid-range systems with more headroom.",
    };
  }

  if (modelId === "llm-llama-8b-q4") {
    return {
      recommended: highSpec,
      label: highSpec ? "Recommended" : undefined,
      reason: highSpec
        ? "Best fit for higher-memory systems with more CPU headroom."
        : "Best reserved for stronger machines with more RAM.",
    };
  }

  return {
    recommended: false,
    reason: "No local recommendation available.",
  };
}

function loadLocalModelCatalogCache(): LocalModelCatalogCache | null {
  try {
    const raw = localStorage.getItem(LOCAL_MODEL_CATALOG_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<LocalModelCatalogCache>;
    if (!Array.isArray(parsed.entries)) return null;
    return {
      query: typeof parsed.query === "string" ? parsed.query : "",
      entries: parsed.entries,
    };
  } catch {
    return null;
  }
}

function saveLocalModelCatalogCache(cache: LocalModelCatalogCache): void {
  localStorage.setItem(LOCAL_MODEL_CATALOG_CACHE_KEY, JSON.stringify(cache));
}

function recommendBrowseModel(entry: LocalModelCatalogEntry, profile: LocalSystemProfile): ModelRecommendation {
  const sizeGB = entry.sizeBytes / (1024 ** 3);
  const memory = profile.memoryGB;
  if (sizeGB <= 2.5) {
    return {
      recommended: memory === null || memory >= 4,
      label: memory === null || memory >= 4 ? "Recommended" : undefined,
      reason: "Small enough for most systems and the safest local entry to start with.",
    };
  }
  if (sizeGB <= 5.2) {
    return {
      recommended: memory === null || memory >= 8,
      label: memory === null || memory >= 8 ? "Recommended" : undefined,
      reason: "Balanced size for mid-range machines with more headroom.",
    };
  }
  return {
    recommended: memory !== null && memory >= 16,
    label: memory !== null && memory >= 16 ? "Recommended" : undefined,
    reason: "Large local model that fits best on higher-memory systems.",
  };
}

function isLocalModelReady(status?: AssetStatus): boolean {
  return !!(status?.downloaded && status?.verified);
}

export function SettingsScreen({
  settings,
  busy,
  initialSection = "general",
  onChange,
  onClose,
  onSave,
}: SettingsScreenProps) {
  const cachedLocalModelCatalog = useMemo(loadLocalModelCatalogCache, []);
  const [activeSection, setActiveSection] = useState<SettingsSection>(initialSection);
  const [email, setEmail] = useState("dev@matemium.app");
  const [password, setPassword] = useState("test");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [openRouterBusy, setOpenRouterBusy] = useState(false);
  const [openRouterError, setOpenRouterError] = useState<string | null>(null);
  const [openRouterPendingUrl, setOpenRouterPendingUrl] = useState<string | null>(null);
  const [openRouterCallbackUrl, setOpenRouterCallbackUrl] = useState<string | null>(null);
  const [manualProviderKeys, setManualProviderKeys] = useState<Record<string, string>>({});
  const [selectedProvider, setSelectedProvider] = useState("openrouter");
  const [selectedModelProvider, setSelectedModelProvider] = useState("openrouter");
  const [copiedAuthUrl, setCopiedAuthUrl] = useState(false);
  const [copiedProviderKey, setCopiedProviderKey] = useState<string | null>(null);
  const [modelSearch, setModelSearch] = useState("");
  const [modelBusyProvider, setModelBusyProvider] = useState<string | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  const [localModelCatalog, setLocalModelCatalog] = useState<LocalModelCatalogEntry[]>(
    () => cachedLocalModelCatalog?.entries ?? [],
  );
  const [localModelCatalogQuery, setLocalModelCatalogQuery] = useState(
    () => cachedLocalModelCatalog?.query ?? "",
  );
  const [localModelCatalogLoading, setLocalModelCatalogLoading] = useState(false);
  const [localModelCatalogLoaded, setLocalModelCatalogLoaded] = useState(
    () => !!cachedLocalModelCatalog,
  );
  const [localModelCatalogError, setLocalModelCatalogError] = useState<string | null>(null);
  const [localModelBusyId, setLocalModelBusyId] = useState<string | null>(null);

  const [assetStatuses, setAssetStatuses] = useState<Record<string, AssetStatus>>({});
  const systemProfile = useMemo(readLocalSystemProfile, []);
  const localModelRecommendations = useMemo(() => ({
    "llm-qwen-coder-3b-q4": recommendLocalModel("llm-qwen-coder-3b-q4", systemProfile),
    "llm-qwen-coder-7b-q4": recommendLocalModel("llm-qwen-coder-7b-q4", systemProfile),
    "llm-llama-8b-q4": recommendLocalModel("llm-llama-8b-q4", systemProfile),
  }), [systemProfile]);

  useEffect(() => {
    setActiveSection(initialSection);
  }, [initialSection]);

  const refreshStatuses = async () => {
    try {
      const statuses = await api.getAssetStatus();
      const next: Record<string, AssetStatus> = {};
      statuses.forEach((status) => {
        next[status.id] = status;
      });
      setAssetStatuses(next);
    } catch (e) {
      console.error("Failed to fetch asset statuses", e);
    }
  };

  useEffect(() => {
    refreshStatuses();

    let unlisten: (() => void) | undefined;
    void import("@tauri-apps/api/event").then(({ listen }) => {
      listen("asset-progress", (event: any) => {
        const payload = event.payload as { id: string; pct: number; message: string };
        setAssetStatuses(prev => ({
          ...prev,
          [payload.id]: {
            id: payload.id,
            display_name: prev[payload.id]?.display_name,
            asset_type: prev[payload.id]?.asset_type,
            downloaded: payload.pct === 100 && payload.message === "complete",
            verified: payload.pct === 100 && payload.message === "complete",
            path: prev[payload.id]?.path,
            size: prev[payload.id]?.size,
            progress: payload.pct,
            error: payload.message.startsWith("failed") ? payload.message : undefined,
            paused: payload.message === "paused",
            source_url: prev[payload.id]?.source_url,
            expected_sha256: prev[payload.id]?.expected_sha256,
            install_path: prev[payload.id]?.install_path,
            extract: prev[payload.id]?.extract,
            extract_format: prev[payload.id]?.extract_format,
          }
        }));
      }).then(fn => { unlisten = fn; });
    });

    return () => { unlisten?.(); };
  }, []);

  useEffect(() => {
    if (activeSection === "ai" && !localModelCatalogLoaded && localModelCatalog.length === 0) {
      void handleRefreshLocalModelCatalog(localModelCatalogQuery);
    }
  }, [activeSection, localModelCatalog.length, localModelCatalogLoaded, localModelCatalogQuery]);

  const handleStartDownload = async (modelId: string) => {
    try {
      setAssetStatuses(prev => ({
        ...prev,
        [modelId]: { ...prev[modelId], progress: prev[modelId]?.progress || 0, error: undefined, downloaded: false, verified: false, paused: false }
      }));
      await api.startAssetDownload(modelId);
      await refreshStatuses();
    } catch (err) {
      console.error("Failed to start download", err);
    }
  };

  const handlePauseDownload = async (modelId: string) => {
    try {
      await api.pauseAssetDownload(modelId);
      await refreshStatuses();
    } catch (err) {
      console.error("Failed to pause download", err);
    }
  };

  const handleCancelDownload = async (modelId: string) => {
    try {
      await api.cancelAssetDownload(modelId);
      await refreshStatuses();
    } catch (err) {
      console.error("Failed to cancel download", err);
    }
  };

  const renderModelStatus = (modelId: string) => {
    const status = assetStatuses[modelId];
    if (!status) {
      return (
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 4 }}>
          <button type="button" className="btn btn-sm" onClick={() => void handleStartDownload(modelId)}>
            Check Status
          </button>
        </div>
      );
    }

    if (status.verified || status.downloaded) {
      return (
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--success-color, #10b981)", fontWeight: 600, marginTop: 4 }}>
          <span style={{ fontSize: 14 }}>✓</span> Model is local &amp; fully ready
        </div>
      );
    }

    if (status.error && !status.paused) {
      return (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
          <div style={{ fontSize: 11, color: "var(--fg-dim)", maxWidth: "70%" }}>
            <span className="text-danger" style={{ color: "var(--error-color, #ef4444)" }}>Error: {status.error}</span>
          </div>
          <button type="button" className="btn btn-sm btn-primary" onClick={() => void handleStartDownload(modelId)}>
            Retry Download
          </button>
        </div>
      );
    }

    if (typeof status.progress === "number" && status.progress >= 0 && status.progress < 100) {
      const isPaused = !!status.paused;
      return (
        <div style={{ marginTop: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
            <span style={{ color: "var(--fg-dim)", fontStyle: isPaused ? "italic" : "normal" }}>
              {isPaused ? "Download paused" : "Downloading model assets..."}
            </span>
            <span style={{ fontWeight: 600, color: isPaused ? "var(--fg-dim)" : "var(--accent-color, #06b6d4)" }}>
              {status.progress.toFixed(1)}%
            </span>
          </div>
          <div style={{ height: 4, background: "var(--border-color)", borderRadius: 2, overflow: "hidden", position: "relative" }}>
            <div style={{
              width: `${status.progress}%`,
              height: "100%",
              background: isPaused ? "var(--border-color-dark, #4b5563)" : "var(--accent-color, #06b6d4)",
              transition: "width 0.1s linear"
            }} />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 6 }}>
            {isPaused ? (
              <button type="button" className="btn btn-sm btn-primary" onClick={() => void handleStartDownload(modelId)}>
                Resume
              </button>
            ) : (
              <button type="button" className="btn btn-sm" onClick={() => void handlePauseDownload(modelId)}>
                Pause
              </button>
            )}
            <button type="button" className="btn btn-sm btn-danger" onClick={() => void handleCancelDownload(modelId)}>
              Cancel
            </button>
          </div>
        </div>
      );
    }

    return (
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
        <div style={{ fontSize: 11, color: "var(--fg-dim)" }}>
          Not downloaded yet.
        </div>
        <button type="button" className="btn btn-sm btn-primary" onClick={() => void handleStartDownload(modelId)}>
          Download (Local Use)
        </button>
      </div>
    );
  };

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const handleGetToken = async () => {
    setAuthError(null);
    setAuthBusy(true);
    try {
      const result = await api.authLogin(email, password);
      const next = { ...settings, apiToken: result.accessToken };
      onChange(next);
      await onSave(next);
    } catch (error) {
      setAuthError(formatError(error));
    } finally {
      setAuthBusy(false);
    }
  };

  const handleSessionLogin = async (supabaseToken: string) => {
    if (!supabaseToken) return;
    setAuthError(null);
    setAuthBusy(true);
    try {
      const result = await api.authSession(supabaseToken);
      const next = { ...settings, apiToken: result.accessToken };
      onChange(next);
      await onSave(next);
    } catch (error) {
      setAuthError(formatError(error));
    } finally {
      setAuthBusy(false);
    }
  };

  const handleConnectOpenRouter = async () => {
    setOpenRouterError(null);
    setOpenRouterBusy(true);
    setOpenRouterPendingUrl(null);
    setOpenRouterCallbackUrl(null);
    setCopiedAuthUrl(false);
    try {
      const started = await api.openrouterPrepareConnect();
      setOpenRouterPendingUrl(started.authUrl);
      setOpenRouterCallbackUrl(started.callbackUrl);
      await api.openrouterCompleteConnect();
      onChange(await api.settingsGet());
    } catch (error) {
      const message = formatError(error);
      if (!message.toLowerCase().includes("cancelled")) {
        setOpenRouterError(message);
      }
    } finally {
      setOpenRouterBusy(false);
      setOpenRouterPendingUrl(null);
      setOpenRouterCallbackUrl(null);
    }
  };

  const handleCancelOpenRouter = async () => {
    try {
      await api.openrouterCancelConnect();
    } catch (error) {
      setOpenRouterError(formatError(error));
    } finally {
      setOpenRouterBusy(false);
      setOpenRouterPendingUrl(null);
      setOpenRouterCallbackUrl(null);
    }
  };

  const handleDisconnectOpenRouter = async () => {
    setOpenRouterError(null);
    setOpenRouterBusy(true);
    try {
      await api.openrouterDisconnect();
      onChange(await api.settingsGet());
    } catch (error) {
      setOpenRouterError(formatError(error));
    } finally {
      setOpenRouterBusy(false);
    }
  };

  const providerApiKey = (providerId: string) => {
    switch (providerId) {
      case "openrouter":
        return settings.openrouterApiKey ?? null;
      case "openai":
        return settings.openaiApiKey ?? null;
      case "groq":
        return settings.groqApiKey ?? null;
      case "xai":
        return settings.xaiApiKey ?? null;
      case "cerebras":
        return settings.cerebrasApiKey ?? null;
      case "github":
        return settings.githubApiKey ?? null;
      case "mistral":
        return settings.mistralApiKey ?? null;
      case "gemini":
        return settings.geminiApiKey ?? null;
      default:
        return null;
    }
  };

  const providerConnectedAt = (providerId: string) => {
    switch (providerId) {
      case "openrouter":
        return settings.openrouterConnectedAt ?? null;
      case "openai":
        return settings.openaiConnectedAt ?? null;
      case "groq":
        return settings.groqConnectedAt ?? null;
      case "xai":
        return settings.xaiConnectedAt ?? null;
      case "cerebras":
        return settings.cerebrasConnectedAt ?? null;
      case "github":
        return settings.githubConnectedAt ?? null;
      case "mistral":
        return settings.mistralConnectedAt ?? null;
      case "gemini":
        return settings.geminiConnectedAt ?? null;
      default:
        return null;
    }
  };

  const settingsWithProviderKey = (providerId: string, key: string | null): Settings => {
    const connectedAt = key ? new Date().toISOString() : null;
    const next: Settings = {
      ...settings,
      llmProvider: key ? providerId : settings.llmProvider,
      usePersonalLlm: true,
    };
    if (providerId === "openrouter") {
      next.openrouterApiKey = key;
      next.openrouterUserId = key ? settings.openrouterUserId ?? null : null;
      next.openrouterConnectedAt = connectedAt;
    } else if (providerId === "openai") {
      next.openaiApiKey = key;
      next.openaiConnectedAt = connectedAt;
    } else if (providerId === "groq") {
      next.groqApiKey = key;
      next.groqConnectedAt = connectedAt;
    } else if (providerId === "xai") {
      next.xaiApiKey = key;
      next.xaiConnectedAt = connectedAt;
    } else if (providerId === "cerebras") {
      next.cerebrasApiKey = key;
      next.cerebrasConnectedAt = connectedAt;
    } else if (providerId === "github") {
      next.githubApiKey = key;
      next.githubConnectedAt = connectedAt;
    } else if (providerId === "mistral") {
      next.mistralApiKey = key;
      next.mistralConnectedAt = connectedAt;
    } else if (providerId === "gemini") {
      next.geminiApiKey = key;
      next.geminiConnectedAt = connectedAt;
    }
    return next;
  };

  const handleSaveManualProviderKey = async (providerId: string) => {
    const key = (manualProviderKeys[providerId] ?? "").trim();
    if (!key) {
      setOpenRouterError(`Enter a ${PROVIDERS.find((item) => item.id === providerId)?.name ?? "provider"} API key first.`);
      return;
    }
    setOpenRouterError(null);
    setOpenRouterBusy(true);
    try {
      await api.settingsSet(settingsWithProviderKey(providerId, key));
      onChange(await api.settingsGet());
      setManualProviderKeys((prev) => ({ ...prev, [providerId]: "" }));
    } catch (error) {
      setOpenRouterError(formatError(error));
    } finally {
      setOpenRouterBusy(false);
    }
  };

  const handleCopyAuthUrl = async () => {
    if (!openRouterPendingUrl) return;
    try {
      await navigator.clipboard.writeText(openRouterPendingUrl);
      setCopiedAuthUrl(true);
      window.setTimeout(() => setCopiedAuthUrl(false), 1500);
    } catch {
      setOpenRouterError("Could not copy the URL. Select and copy it manually.");
    }
  };

  const maskedKey = (key: string | null | undefined) => {
    const trimmed = (key ?? "").trim();
    if (!trimmed) return "Not saved";
    const ending = trimmed.slice(-8);
    return `•••• •••• •••• ${ending}`;
  };

  const handleCopyProviderKey = async (providerId: string) => {
    const key = providerApiKey(providerId)?.trim();
    if (!key) return;
    try {
      await navigator.clipboard.writeText(key);
      setCopiedProviderKey(providerId);
      window.setTimeout(() => setCopiedProviderKey(null), 1500);
    } catch {
      setOpenRouterError("Could not copy the key.");
    }
  };

  const handleDisconnectProvider = async (providerId: string) => {
    if (providerId === "openrouter") {
      await handleDisconnectOpenRouter();
      return;
    }
    setOpenRouterError(null);
    setOpenRouterBusy(true);
    try {
      await api.settingsSet(settingsWithProviderKey(providerId, null));
      onChange(await api.settingsGet());
    } catch (error) {
      setOpenRouterError(formatError(error));
    } finally {
      setOpenRouterBusy(false);
    }
  };

  const handleUseProvider = async (providerId: string) => {
    setOpenRouterError(null);
    setOpenRouterBusy(true);
    try {
      await api.settingsSet({ ...settings, llmProvider: providerId, usePersonalLlm: true });
      onChange(await api.settingsGet());
    } catch (error) {
      setOpenRouterError(formatError(error));
    } finally {
      setOpenRouterBusy(false);
    }
  };

  const handleRefreshProviderModels = async (providerId: string) => {
    setModelError(null);
    setModelBusyProvider(providerId);
    try {
      await api.providerModelsList(providerId, true);
      onChange(await api.settingsGet());
    } catch (error) {
      setModelError(formatError(error));
    } finally {
      setModelBusyProvider(null);
    }
  };

  const handleRefreshConnectedProviderModels = async () => {
    const connected = PROVIDERS.filter((item) => !!providerApiKey(item.id));
    if (!connected.length) {
      setModelError("Connect at least one provider before refreshing model catalogs.");
      return;
    }
    setModelError(null);
    setModelBusyProvider("all");
    const failures: string[] = [];
    try {
      for (const provider of connected) {
        try {
          await api.providerModelsList(provider.id, true);
        } catch (error) {
          failures.push(`${provider.name}: ${formatError(error)}`);
        }
      }
      onChange(await api.settingsGet());
      if (failures.length) {
        setModelError(failures.join("  "));
      }
    } finally {
      setModelBusyProvider(null);
    }
  };

  const handleRefreshLocalModelCatalog = async (query = localModelCatalogQuery) => {
    setLocalModelCatalogLoading(true);
    setLocalModelCatalogError(null);
    try {
      const entries = await api.localModelCatalogList(query.trim() || undefined);
      setLocalModelCatalog(entries);
      setLocalModelCatalogQuery(query);
      saveLocalModelCatalogCache({ query, entries });
    } catch (error) {
      setLocalModelCatalogError(formatError(error));
    } finally {
      setLocalModelCatalogLoaded(true);
      setLocalModelCatalogLoading(false);
    }
  };

  const handleInstallLocalModel = async (entry: LocalModelCatalogEntry) => {
    if (isLocalModelReady(assetStatuses[entry.assetId]) || entry.installed) {
      return;
    }
    setModelError(null);
    setLocalModelBusyId(entry.assetId);
    try {
      await api.localModelInstall(entry);
      await refreshStatuses();
      await handleRefreshLocalModelCatalog();
    } catch (error) {
      setLocalModelCatalogError(formatError(error));
    } finally {
      setLocalModelBusyId(null);
    }
  };

  const updateProviderPinnedModels = async (providerId: string, pinned: string[]) => {
    const currentProviderModels = settings.providerModels ?? {};
    const currentState = currentProviderModels[providerId] ?? {};
    const next: Settings = {
      ...settings,
      providerModels: {
        ...currentProviderModels,
        [providerId]: {
          ...currentState,
          pinned: Array.from(new Set(pinned)),
        },
      },
    };
    onChange(next);
    await api.settingsSet(next);
    onChange(await api.settingsGet());
  };

  const handlePinProviderModel = async (providerId: string, modelId: string) => {
    await updateProviderPinnedModels(providerId, [...pinnedModelIds(settings, providerId), modelId]);
  };

  const handleUnpinProviderModel = async (providerId: string, modelId: string) => {
    await updateProviderPinnedModels(
      providerId,
      pinnedModelIds(settings, providerId).filter((id) => id !== modelId),
    );
  };

  const displayedProviderModels = (providerId: string, catalog: ProviderModel[]) => {
    const defaults = DEFAULT_PINNED_MODELS[providerId] ?? [];
    const pinnedMissingFromCatalog = pinnedModelIds(settings, providerId)
      .filter((id) => !catalog.some((model) => model.id === id))
      .map((id) => defaults.find((model) => model.id === id) ?? {
        id,
        name: modelDisplayName(id),
        provider: providerId,
        badges: ["Pinned"],
      });
    const source = catalog.length ? [...pinnedMissingFromCatalog, ...catalog] : defaults;
    const merged = source.filter(
      (model, index, list) => list.findIndex((candidate) => candidate.id === model.id) === index,
    );
    const query = modelSearch.trim().toLowerCase();
    if (!query) return merged.slice(0, 80);
    return merged
      .filter((model) => {
        const haystack = `${model.id} ${model.name} ${(model.badges ?? []).join(" ")}`.toLowerCase();
        return haystack.includes(query);
      })
      .slice(0, 80);
  };

  const handleSave = async () => {
    await onSave(settings);
  };

  const update = (patch: Partial<Settings>) => {
    onChange({ ...settings, ...patch });
  };

  const renderSection = () => {
    switch (activeSection) {
      case "general":
        return (
          <div className="settings-section">
            <div className="settings-section-header">
              <h3>General</h3>
              <p className="settings-section-desc">Connection and interface preferences.</p>
            </div>

            <div className="settings-field">
              <label className="settings-label">Server URL</label>
              <input
                className="settings-input"
                value={settings.serverUrl}
                onChange={(e) => update({ serverUrl: e.target.value })}
                placeholder="https://..."
              />
              <div className="settings-hint">
                Live server: {config.serverUrl}
              </div>
            </div>

            <div className="settings-field">
              <label className="settings-label">Default bottom panel</label>
              <select
                className="settings-select"
                value={settings.bottomDockDefault ?? "progress"}
                onChange={(e) =>
                  update({
                    bottomDockDefault: e.target.value === "output" ? "output" : "progress",
                  })
                }
              >
                <option value="progress">Progress</option>
                <option value="output">Terminal output</option>
              </select>
              <div className="settings-hint">
                Which panel opens by default after you start a render.
              </div>
            </div>
          </div>
        );

      case "account":
        return (
          <div className="settings-section">
            <div className="settings-section-header">
              <h3>Account</h3>
              <p className="settings-section-desc">
                API access for Matemium Cloud account features.
              </p>
            </div>

            <div className="settings-field">
              <label className="settings-label">API Token</label>
              <input
                className="settings-input"
                type="password"
                value={settings.apiToken ?? ""}
                onChange={(e) => update({ apiToken: e.target.value || null })}
                placeholder="Paste your access token here"
              />
              <div className="settings-hint">
                Required for account features such as profile and gallery access. Provider keys stay in the Providers tab.
              </div>
            </div>

            {!settings.apiToken && (
              <div className="settings-card">
                <div className="settings-card-title">Quick sign-in</div>

                <div className="settings-auth-row">
                  <input
                    className="settings-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="email"
                  />
                  <input
                    className="settings-input"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="password"
                  />
                </div>

                <button
                  type="button"
                  className="btn btn-primary settings-btn-block"
                  disabled={busy || authBusy}
                  onClick={() => void handleGetToken()}
                >
                  Get dev token
                </button>

                <div className="settings-auth-secondary">
                  <div className="settings-hint">
                    Live server: sign in on web with Google first, then paste Supabase token.
                  </div>
                  <button
                    type="button"
                    className="btn settings-btn-block"
                    disabled={busy || authBusy}
                    onClick={() => {
                      const t = prompt(
                        "Paste your Supabase access_token (from web after login)"
                      );
                      if (t) void handleSessionLogin(t);
                    }}
                  >
                    Exchange Supabase token (for live)
                  </button>
                </div>

                {authError && <p className="settings-error">{authError}</p>}
              </div>
            )}

            {settings.apiToken && (
              <div className="settings-card settings-card-success">
                <div className="settings-success-text">
                  ✓ You are authenticated. Token is saved locally.
                </div>
                <button
                  type="button"
                  className="btn"
                  onClick={() => update({ apiToken: null })}
                >
                  Clear token
                </button>
              </div>
            )}
          </div>
        );

      case "providers": {
        const provider = PROVIDERS.find((item) => item.id === selectedProvider) ?? PROVIDERS[0];
        const isOpenRouter = provider.id === "openrouter";
        const selectedProviderKey = providerApiKey(provider.id);
        const providerConnected = !!selectedProviderKey;
        const connectedAt = providerConnectedAt(provider.id);
        const manualKey = manualProviderKeys[provider.id] ?? "";

        return (
          <div className="settings-section settings-section-wide">
            <div className="settings-section-header">
              <h3>Providers</h3>
              <p className="settings-section-desc">
                Manage external AI providers on this computer. Provider keys are stored locally and requests go directly from your device to the provider.
              </p>
            </div>

            <div className="settings-provider-grid">
              <div className="settings-provider-column">
                <div className="settings-column-title">Available providers</div>
                <div className="settings-provider-list">
                  {PROVIDERS.map((item) => {
                    const active = selectedProvider === item.id;
                    const connected = !!providerApiKey(item.id);
                    return (
                      <button
                        key={item.id}
                        type="button"
                        className={`settings-provider-item ${active ? "active" : ""}`}
                        onClick={() => setSelectedProvider(item.id)}
                      >
                        <div className="settings-provider-item-main">
                          <span>{item.name}</span>
                          {connected && <span className="settings-provider-dot" />}
                        </div>
                        <div className="settings-provider-item-meta">{connected ? "Connected" : item.status}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="settings-provider-column">
                <div className="settings-column-title">Provider</div>
                <div className="settings-provider-summary">
                  <div className="settings-provider-name">{provider.name}</div>
                  <div className="settings-provider-description">{provider.description}</div>
                  {isOpenRouter ? (
                    <div className={`settings-provider-state ${providerConnected ? "connected" : ""}`}>
                      {providerConnected ? "Connected locally" : "Not connected"}
                    </div>
                  ) : (
                    <div className={`settings-provider-state ${providerConnected ? "connected" : ""}`}>
                      {providerConnected ? "Connected locally" : "Not connected"}
                    </div>
                  )}
                  {connectedAt && (
                    <div className="settings-hint">
                      Connected {new Date(connectedAt).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>

              <div className="settings-provider-column settings-provider-detail">
                <div className="settings-column-title">Connection</div>
                <>
                    {providerConnected ? (
                      <div className="settings-connected-provider">
                        <div className="settings-provider-name">{provider.name} is connected</div>
                        <div className="settings-hint">
                          To replace this key or start OAuth again, disconnect first.
                        </div>
                        <div className={`settings-provider-state ${settings.llmProvider === provider.id ? "connected" : ""}`}>
                          {settings.llmProvider === provider.id ? "Active for external AI" : "Connected but not active"}
                        </div>
                        <div className="settings-key-row">
                          <div>
                            <div className="settings-key-label">Saved key</div>
                            <div className="settings-key-value">{maskedKey(selectedProviderKey)}</div>
                          </div>
                          <button type="button" className="btn" onClick={() => void handleCopyProviderKey(provider.id)}>
                            {copiedProviderKey === provider.id ? "Copied" : "Copy"}
                          </button>
                        </div>
                        {settings.llmProvider !== provider.id && (
                          <button
                            type="button"
                            className="btn btn-primary settings-btn-block"
                            disabled={openRouterBusy}
                            onClick={() => void handleUseProvider(provider.id)}
                          >
                            Use {provider.name} for external AI
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn settings-btn-block"
                          disabled={openRouterBusy}
                          onClick={() => void handleDisconnectProvider(provider.id)}
                        >
                          Disconnect {provider.name}
                        </button>
                      </div>
                    ) : (
                      <>
                        <label className="settings-label">Manual API key</label>
                        <input
                          className="settings-input"
                          type="password"
                          value={manualKey}
                          onChange={(e) => setManualProviderKeys((prev) => ({ ...prev, [provider.id]: e.target.value }))}
                          placeholder={isOpenRouter ? "sk-or-v1-..." : "Paste API key"}
                          autoComplete="off"
                        />
                        <div className="settings-hint">
                          Paste a {provider.name} key if you already have one. It is saved only in Matemium desktop settings on this computer.
                        </div>

                        <div className="settings-provider-actions">
                          <button
                            type="button"
                            className="btn"
                            disabled={openRouterBusy || !manualKey.trim()}
                            onClick={() => void handleSaveManualProviderKey(provider.id)}
                          >
                            Save manual key
                          </button>
                        </div>

                        {isOpenRouter && (
                          <>
                            <div className="settings-provider-divider" />

                            <div className="settings-provider-name">Automatic connection</div>
                            <div className="settings-hint">
                              Matemium opens OpenRouter in your browser. The key is labeled Matemium and the callback stays on this computer.
                            </div>
                            {!openRouterBusy ? (
                              <button
                                type="button"
                                className="btn btn-primary settings-btn-block"
                                onClick={() => void handleConnectOpenRouter()}
                              >
                                Connect OpenRouter Account
                              </button>
                            ) : (
                              <div className="settings-oauth-pending">
                                <div className="settings-provider-name">Browser opened</div>
                                <div className="settings-hint">
                                  Complete authorization in the browser, or copy this URL and open it using your preferred browser. OpenRouter may show the temporary local callback address because the desktop app receives the code on this computer.
                                </div>
                                <div className="settings-copy-row">
                                  <input
                                    className="settings-input"
                                    value={openRouterPendingUrl ?? ""}
                                    readOnly
                                    onFocus={(event) => event.currentTarget.select()}
                                  />
                                  <button type="button" className="btn" onClick={() => void handleCopyAuthUrl()}>
                                    {copiedAuthUrl ? "Copied" : "Copy"}
                                  </button>
                                </div>
                                {openRouterCallbackUrl && (
                                  <div className="settings-hint">
                                    Waiting for callback on {openRouterCallbackUrl}
                                  </div>
                                )}
                                <button
                                  type="button"
                                  className="btn settings-btn-block"
                                  onClick={() => void handleCancelOpenRouter()}
                                >
                                  Cancel connection
                                </button>
                              </div>
                            )}
                          </>
                        )}
                      </>
                    )}
                    {openRouterError && <p className="settings-error">{openRouterError}</p>}
                  </>
              </div>
            </div>
          </div>
        );
      }
      case "models": {
        const provider = PROVIDERS.find((item) => item.id === selectedModelProvider) ?? PROVIDERS[0];
        const providerConnected = !!providerApiKey(provider.id);
        const modelState = providerModelState(settings, provider.id);
        const pinnedIds = pinnedModelIds(settings, provider.id);
        const catalog = modelState.catalog ?? [];
        const fetchedAt = modelState.fetchedAt ? new Date(modelState.fetchedAt).toLocaleString() : null;
        const visibleModels = displayedProviderModels(provider.id, catalog);
        const refreshingModels = modelBusyProvider === provider.id;

        return (
          <div className="settings-section settings-section-wide">
            <div className="settings-section-header">
              <div>
                <h3>Model Browser</h3>
                <p className="settings-section-desc">
                  Fetch provider model catalogs, keep them cached locally, and pin the models that should appear in the chat picker across connected providers.
                </p>
              </div>
              <button
                type="button"
                className="btn"
                disabled={modelBusyProvider === "all"}
                onClick={() => void handleRefreshConnectedProviderModels()}
              >
                {modelBusyProvider === "all" ? "Refreshing catalogs..." : "Refresh connected catalogs"}
              </button>
            </div>

            <div className="settings-model-management-grid">
              <div className="settings-provider-column">
                <div className="settings-column-title">Provider catalogs</div>
                <div className="settings-provider-list">
                  {PROVIDERS.map((item) => {
                    const active = selectedModelProvider === item.id;
                    const connected = !!providerApiKey(item.id);
                    const count = pinnedModelIds(settings, item.id).length;
                    const catalogCount = providerModelState(settings, item.id).catalog?.length ?? 0;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        className={`settings-provider-item ${active ? "active" : ""}`}
                        onClick={() => setSelectedModelProvider(item.id)}
                      >
                        <div className="settings-provider-item-main">
                          <span>{item.name}</span>
                          {connected && <span className="settings-provider-dot" />}
                        </div>
                        <div className="settings-provider-item-meta">
                          {connected ? `${count} pinned · ${catalogCount} cached` : "Connect provider first"}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="settings-provider-column settings-model-picker-detail">
                <div className="settings-model-browser">
                  <div className="settings-model-browser-header">
                    <div>
                      <div className="settings-provider-name">{provider.name}</div>
                      <div className="settings-hint">
                        Pinned models from every connected provider appear in the chat dropdown.
                      </div>
                    </div>
                    {providerConnected ? (
                      <button
                        type="button"
                        className="btn"
                        disabled={refreshingModels || modelBusyProvider === "all"}
                        onClick={() => void handleRefreshProviderModels(provider.id)}
                      >
                        {refreshingModels ? "Refreshing..." : catalog.length ? "Refresh catalog" : "Browse catalog"}
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => {
                          setSelectedProvider(provider.id);
                          setActiveSection("providers");
                        }}
                      >
                        Connect provider
                      </button>
                    )}
                  </div>

                  <div className={`settings-provider-state ${providerConnected ? "connected" : ""}`}>
                    {providerConnected ? "Catalog available with local provider key" : "Provider not connected"}
                  </div>

                  <div className="settings-column-title">Pinned in chat picker</div>
                  <div className="settings-model-pinned">
                    {pinnedIds.map((id) => {
                      const model = visibleModels.find((item) => item.id === id)
                        ?? catalog.find((item) => item.id === id)
                        ?? (DEFAULT_PINNED_MODELS[provider.id] ?? []).find((item) => item.id === id)
                        ?? { id, name: modelDisplayName(id), provider: provider.id };
                      return (
                        <button
                          key={id}
                          type="button"
                          className="settings-model-chip"
                          onClick={() => void handleUnpinProviderModel(provider.id, id)}
                          title="Remove from chat picker"
                        >
                          {model.name}
                          <span>Remove</span>
                        </button>
                      );
                    })}
                  </div>

                  <div className="settings-model-toolbar">
                    <input
                      className="settings-input"
                      value={modelSearch}
                      onChange={(event) => setModelSearch(event.target.value)}
                      placeholder="Search provider models"
                      disabled={!providerConnected}
                    />
                    {fetchedAt && <div className="settings-hint">Refreshed {fetchedAt}</div>}
                  </div>
                  {modelError && <p className="settings-error">{modelError}</p>}

                  <div className="settings-model-catalog settings-model-catalog-large">
                    {providerConnected && visibleModels.map((model) => {
                      const pinned = pinnedIds.includes(model.id);
                      return (
                        <div key={model.id} className="settings-model-catalog-row">
                          <div className="settings-model-catalog-main">
                            <div className="settings-model-name">{model.name}</div>
                            <div className="settings-model-id">{model.id}</div>
                            <div className="settings-model-meta">{formatModelMeta(model)}</div>
                            {!!model.badges?.length && (
                              <div className="settings-model-badges">
                                {model.badges.slice(0, 4).map((badge) => (
                                  <span key={badge} className="settings-model-badge">{badge}</span>
                                ))}
                              </div>
                            )}
                          </div>
                          <button
                            type="button"
                            className="btn"
                            onClick={() => pinned
                              ? void handleUnpinProviderModel(provider.id, model.id)
                              : void handlePinProviderModel(provider.id, model.id)}
                          >
                            {pinned ? "Pinned" : "Add"}
                          </button>
                        </div>
                      );
                    })}
                    {providerConnected && !visibleModels.length && (
                      <div className="settings-empty-models">
                        Refresh the catalog, then search the models this provider returns.
                      </div>
                    )}
                    {!providerConnected && (
                      <div className="settings-empty-models">
                        Connect {provider.name} in AI Providers before browsing its model catalog.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      }
      case "ai":
        return (
          <div className="settings-section settings-section-wide settings-offline-ai-section" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="settings-section-header">
              <h3>AI &amp; LLM</h3>
              <p className="settings-section-desc">
                Choose how the AI assistant and generation features work.
              </p>
              <div className="settings-hint">
                Detected device: {formatSystemProfile(systemProfile)}. Recommendations stay conservative and only change labels here.
              </div>
            </div>

            <div className="settings-card settings-offline-ai-card">
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                    Local model downloads <span style={{
                      borderRadius: 4,
                      padding: "2px 6px",
                      fontSize: 10,
                      background: "var(--accent-dim, rgba(6, 182, 212, 0.15))",
                      color: "var(--accent-color, #06b6d4)",
                      fontWeight: 700,
                      textTransform: "uppercase"
                    }}>Offline Assets</span>
                  </div>
                  <div className="settings-hint" style={{ marginTop: 2 }}>
                    Built-in local assets and official Hugging Face GGUF models are shown together.
                  </div>
                </div>
                <button
                  type="button"
                  className="btn"
                  disabled={localModelCatalogLoading}
                  onClick={() => void handleRefreshLocalModelCatalog()}
                >
                  {localModelCatalogLoading ? "Loading..." : "Refresh catalog"}
                </button>
              </div>

              <div className="settings-model-toolbar" style={{ marginTop: 12 }}>
                <input
                  className="settings-input"
                  value={localModelCatalogQuery}
                  onChange={(event) => setLocalModelCatalogQuery(event.target.value)}
                  placeholder="Search local models"
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void handleRefreshLocalModelCatalog();
                    }
                  }}
                />
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={localModelCatalogLoading}
                  onClick={() => void handleRefreshLocalModelCatalog()}
                >
                  Search
                </button>
              </div>

              {localModelCatalogError && <p className="settings-error">{localModelCatalogError}</p>}

              <div className="settings-model-catalog settings-model-catalog-large" style={{ marginTop: 12 }}>
                {BUILTIN_LOCAL_MODELS.map((model) => {
                  const recommendation = localModelRecommendations[model.id as keyof typeof localModelRecommendations];
                  return (
                    <div key={model.id} className="settings-model-catalog-row settings-local-model-row">
                      <div className="settings-model-catalog-main">
                        <div className="settings-model-name">{model.name}</div>
                        <div className="settings-model-meta">{model.meta}</div>
                        <div className="settings-hint" style={{ fontSize: 11 }}>{model.description}</div>
                        {recommendation?.recommended ? (
                          <div className="settings-model-badges">
                            <span className="settings-model-badge settings-model-badge-recommended" title={recommendation.reason}>
                              {recommendation.label ?? "Recommended"}
                            </span>
                          </div>
                        ) : null}
                      </div>
                      <div>{renderModelStatus(model.id)}</div>
                    </div>
                  );
                })}
                {Object.values(assetStatuses)
                  .filter((status) => status.asset_type === "local_model")
                  .filter((status) => !BUILTIN_LOCAL_MODELS.some((model) => model.id === status.id))
                  .filter((status) => !localModelCatalog.some((entry) => entry.assetId === status.id))
                  .map((status) => (
                    <div key={status.id} className="settings-model-catalog-row settings-local-model-row">
                      <div className="settings-model-catalog-main">
                        <div className="settings-model-name">{status.display_name ?? modelDisplayName(status.id)}</div>
                        <div className="settings-model-id">{status.id}</div>
                        <div className="settings-model-meta">
                          {typeof status.size === "number" ? formatBytes(status.size) : "Local model"}
                        </div>
                        {isLocalModelReady(status) ? (
                          <div className="settings-model-badges">
                            <span className="settings-model-badge">Installed</span>
                          </div>
                        ) : null}
                      </div>
                      <div>{renderModelStatus(status.id)}</div>
                    </div>
                  ))}
                {localModelCatalog.map((entry) => {
                  const status = assetStatuses[entry.assetId];
                  const recommended = recommendBrowseModel(entry, systemProfile);
                  const ready = isLocalModelReady(status) || entry.installed;
                  const installing = localModelBusyId === entry.assetId || (typeof status?.progress === "number" && !ready);
                  return (
                    <div key={entry.assetId} className="settings-model-catalog-row settings-local-model-row">
                      <div className="settings-model-catalog-main">
                        <div className="settings-model-name">{entry.displayName}</div>
                        <div className="settings-model-id">{entry.repoId} · {entry.fileName}</div>
                        <div className="settings-model-meta">
                          {formatBytes(entry.sizeBytes)}{entry.quantization ? ` · ${entry.quantization}` : ""}
                          {entry.contextLength ? ` · ${Math.round(entry.contextLength / 1000)}k ctx` : ""}
                          {entry.parameterSize ? ` · ${entry.parameterSize}` : ""}
                        </div>
                        <div className="settings-model-badges">
                          {recommended.recommended ? (
                            <span className="settings-model-badge settings-model-badge-recommended" title={recommended.reason}>
                              Recommended
                            </span>
                          ) : null}
                          {ready ? <span className="settings-model-badge">Installed</span> : null}
                          {entry.license ? <span className="settings-model-badge">{entry.license}</span> : null}
                        </div>
                      </div>
                      <div style={{ display: "grid", gap: 8, justifyItems: "end" }}>
                        {status ? (
                          renderModelStatus(entry.assetId)
                        ) : (
                          <button
                            type="button"
                            className="btn btn-primary"
                            disabled={ready || installing}
                            onClick={() => void handleInstallLocalModel(entry)}
                          >
                            {ready ? "Installed" : installing ? "Installing..." : "Install"}
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn"
                          onClick={() => window.open(entry.sourceRepoUrl, "_blank", "noreferrer")}
                        >
                          Open repo
                        </button>
                      </div>
                    </div>
                  );
                })}
                {localModelCatalogLoading && !localModelCatalog.length ? (
                  <div className="settings-empty-models">Loading local model catalog...</div>
                ) : null}
                {!localModelCatalogLoading && !localModelCatalog.length ? (
                  <div className="settings-empty-models">
                    Search the catalog to browse more local GGUF models.
                  </div>
                ) : null}
              </div>
            </div>

            {/* Autonomous Aider runtime */}
            <div className="settings-card" style={{ border: settings.useAutonomousAgent ? "1px solid #eab308" : "1px solid var(--border-color)" }}>
              <label className="settings-checkbox-row">
                <input
                  type="checkbox"
                  checked={!!settings.useAutonomousAgent}
                  onChange={(e) => {
                    update({
                      useAutonomousAgent: e.target.checked,
                    });
                  }}
                />
                <div>
                  <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                    Enable autonomous agent mode <span style={{
                      borderRadius: 4,
                      padding: "2px 6px",
                      fontSize: 10,
                      background: "rgba(234, 179, 8, 0.15)",
                      color: "#eab308",
                      fontWeight: 700,
                      textTransform: "uppercase"
                    }}>Aider</span>
                  </div>
                  <div className="settings-hint" style={{ marginTop: 2 }}>
                    Uses Aider as the coding-agent runtime for local and external models. Agent actions may modify project files; review the activity ledger and resulting changes.
                  </div>
                </div>
              </label>
            </div>

            <div className="settings-hint">
              AI mode is controlled from the chat header. Settings only manages provider keys and local model downloads.
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="settings-screen">
      <div className="settings-header">
        <div>
          <div className="settings-title">Settings</div>
          <div className="settings-subtitle">Configure Matemium desktop</div>
        </div>
        <button
          type="button"
          className="settings-close"
          onClick={onClose}
          aria-label="Close settings"
        >
          ×
        </button>
      </div>

      <div className="settings-body">
        <nav className="settings-nav">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`settings-nav-item ${activeSection === item.id ? "active" : ""}`}
              onClick={() => setActiveSection(item.id)}
            >
              <div className="settings-nav-label">{item.label}</div>
              {item.desc && <div className="settings-nav-desc">{item.desc}</div>}
            </button>
          ))}
        </nav>

        <div className="settings-content">{renderSection()}</div>
      </div>

      <div className="settings-footer">
        <div className="settings-footer-left">
          <span className="settings-hint">Changes are applied live. Click Save to persist.</span>
        </div>
        <div className="settings-footer-actions">
          <button type="button" className="btn" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy || authBusy}
            onClick={() => void handleSave()}
          >
            Save &amp; Apply
          </button>
        </div>
      </div>
    </div>
  );
}
