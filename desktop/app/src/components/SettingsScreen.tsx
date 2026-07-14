import { useEffect, useState } from "react";

import * as api from "../api/tauri";
import config from "../config.json";
import type { Settings } from "../api/types";
import { formatError } from "../utils/errors";

interface SettingsScreenProps {
  settings: Settings;
  busy: boolean;
  onChange: (settings: Settings) => void;
  onClose: () => void;
  onSave: (settings: Settings) => Promise<void>;
}

type SettingsSection = "general" | "account" | "ai";

const NAV_ITEMS: Array<{ id: SettingsSection; label: string; desc?: string }> = [
  { id: "general", label: "General", desc: "App behavior & connections" },
  { id: "account", label: "Account", desc: "Authentication & tokens" },
  { id: "ai", label: "AI & LLM", desc: "Model provider & keys" },
];

export function SettingsScreen({
  settings,
  busy,
  onChange,
  onClose,
  onSave,
}: SettingsScreenProps) {
  const [activeSection, setActiveSection] = useState<SettingsSection>("general");
  const [email, setEmail] = useState("dev@matemium.app");
  const [password, setPassword] = useState("test");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const [assetStatuses, setAssetStatuses] = useState<Record<string, { downloaded: boolean; verified: boolean; progress?: number; error?: string; paused?: boolean }>>({});

  const refreshStatuses = async () => {
    try {
      const qwen3b = await api.getAssetStatus("llm-qwen-coder-3b-q4");
      const qwen7b = await api.getAssetStatus("llm-qwen-coder-7b-q4");
      const llama8b = await api.getAssetStatus("llm-llama-8b-q4");

      const next: typeof assetStatuses = {};
      if (qwen3b?.[0]) next["llm-qwen-coder-3b-q4"] = qwen3b[0];
      if (qwen7b?.[0]) next["llm-qwen-coder-7b-q4"] = qwen7b[0];
      if (llama8b?.[0]) next["llm-llama-8b-q4"] = llama8b[0];

      setAssetStatuses(prev => ({ ...prev, ...next }));
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
        if (["llm-qwen-coder-3b-q4", "llm-qwen-coder-7b-q4", "llm-llama-8b-q4"].includes(payload.id)) {
          setAssetStatuses(prev => ({
            ...prev,
            [payload.id]: {
              downloaded: payload.pct === 100 && payload.message === "complete",
              verified: payload.pct === 100 && payload.message === "complete",
              progress: payload.pct,
              error: payload.message.startsWith("failed") ? payload.message : undefined,
              paused: payload.message === "paused",
            }
          }));
        }
      }).then(fn => { unlisten = fn; });
    });

    return () => { unlisten?.(); };
  }, []);

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
                API access for the Matemium platform and sidecar.
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
                Required for chat, rendering credits, and cloud features.
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

      case "ai":
        return (
          <div className="settings-section" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="settings-section-header">
              <h3>AI &amp; LLM</h3>
              <p className="settings-section-desc">
                Choose how the AI assistant and generation features work.
              </p>
            </div>

            {/* Local LLM Offline Engine (Offline-First) */}
            <div className="settings-card" style={{ border: settings.useLocalLlm ? "1px solid var(--accent-color, #06b6d4)" : "1px solid var(--border-color)" }}>
              <label className="settings-checkbox-row">
                <input
                  type="checkbox"
                  checked={!!settings.useLocalLlm}
                  onChange={(e) => {
                    update({
                      useLocalLlm: e.target.checked,
                      usePersonalLlm: e.target.checked ? false : settings.usePersonalLlm,
                    });
                  }}
                />
                <div>
                  <div style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
                    Enable Local LLM Engine <span style={{
                      borderRadius: 4,
                      padding: "2px 6px",
                      fontSize: 10,
                      background: "var(--accent-dim, rgba(6, 182, 212, 0.15))",
                      color: "var(--accent-color, #06b6d4)",
                      fontWeight: 700,
                      textTransform: "uppercase"
                    }}>Offline Mode</span>
                  </div>
                  <div className="settings-hint" style={{ marginTop: 2 }}>
                    Run state-of-the-art open mathematical assistant models entirely on your machine.
                  </div>
                </div>
              </label>

              {settings.useLocalLlm && (
                <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: "var(--fg-dim)" }}>
                    Select local model:
                  </div>

                  {/* Model 1: Qwen 3B */}
                  <div className="settings-model-row" style={{
                    border: "1px solid var(--border-color)",
                    borderRadius: 6,
                    padding: 12,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    background: settings.localLlmModel === "llm-qwen-coder-3b-q4" ? "rgba(6, 182, 212, 0.05)" : "transparent"
                  }}>
                    <label style={{ display: "flex", gap: 10, alignItems: "flex-start", cursor: "pointer" }}>
                      <input
                        type="radio"
                        name="local-llm-model"
                        checked={settings.localLlmModel === "llm-qwen-coder-3b-q4"}
                        onChange={() => update({ localLlmModel: "llm-qwen-coder-3b-q4" })}
                        style={{ marginTop: 3 }}
                      />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>Lite Tier: Qwen-2.5-Coder-3B-Instruct (1.9 GB)</div>
                        <div className="settings-hint" style={{ fontSize: 11 }}>
                          Optimized for low RAM (4GB+) and CPU-only devices. Ultra-fast generation.
                        </div>
                      </div>
                    </label>
                    {renderModelStatus("llm-qwen-coder-3b-q4")}
                  </div>

                  {/* Model 2: Qwen 7B */}
                  <div className="settings-model-row" style={{
                    border: "1px solid var(--border-color)",
                    borderRadius: 6,
                    padding: 12,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    background: settings.localLlmModel === "llm-qwen-coder-7b-q4" ? "rgba(6, 182, 212, 0.05)" : "transparent"
                  }}>
                    <label style={{ display: "flex", gap: 10, alignItems: "flex-start", cursor: "pointer" }}>
                      <input
                        type="radio"
                        name="local-llm-model"
                        checked={settings.localLlmModel === "llm-qwen-coder-7b-q4"}
                        onChange={() => update({ localLlmModel: "llm-qwen-coder-7b-q4" })}
                        style={{ marginTop: 3 }}
                      />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>Balanced Tier: Qwen-2.5-Coder-7B-Instruct (4.7 GB)</div>
                        <div className="settings-hint" style={{ fontSize: 11 }}>
                          Perfect math layouts and coding correctness. Recommended for dedicated GPUs and M1/M2/M3 Macs.
                        </div>
                      </div>
                    </label>
                    {renderModelStatus("llm-qwen-coder-7b-q4")}
                  </div>

                  {/* Model 3: Llama 8B */}
                  <div className="settings-model-row" style={{
                    border: "1px solid var(--border-color)",
                    borderRadius: 6,
                    padding: 12,
                    display: "flex",
                    flexDirection: "column",
                    gap: 8,
                    background: settings.localLlmModel === "llm-llama-8b-q4" ? "rgba(6, 182, 212, 0.05)" : "transparent"
                  }}>
                    <label style={{ display: "flex", gap: 10, alignItems: "flex-start", cursor: "pointer" }}>
                      <input
                        type="radio"
                        name="local-llm-model"
                        checked={settings.localLlmModel === "llm-llama-8b-q4"}
                        onChange={() => update({ localLlmModel: "llm-llama-8b-q4" })}
                        style={{ marginTop: 3 }}
                      />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>Elite Tier: Llama-3-8B-Instruct (4.9 GB)</div>
                        <div className="settings-hint" style={{ fontSize: 11 }}>
                          Exceptional pedagogy and scripting style. Best for top-tier workstations.
                        </div>
                      </div>
                    </label>
                    {renderModelStatus("llm-llama-8b-q4")}
                  </div>
                </div>
              )}
            </div>

            {/* Cloud Hosted LLM options */}
            <div className="settings-card" style={{
              opacity: settings.useLocalLlm ? 0.5 : 1,
              pointerEvents: settings.useLocalLlm ? "none" : "auto",
              transition: "opacity 0.2s ease"
            }}>
              <label className="settings-checkbox-row">
                <input
                  type="checkbox"
                  checked={!!settings.usePersonalLlm}
                  disabled={!!settings.useLocalLlm}
                  onChange={(e) => update({ usePersonalLlm: e.target.checked })}
                />
                <div>
                  <div style={{ fontWeight: 600 }}>Use my personal API keys (BYO)</div>
                  <div className="settings-hint" style={{ marginTop: 2 }}>
                    Bring your own keys for OpenAI, Groq, xAI, etc. Keys are managed in the web dashboard.
                  </div>
                </div>
              </label>

              <div className="settings-field settings-field-tight">
                <label className="settings-label">LLM Provider</label>
                <select
                  className="settings-select"
                  value={settings.llmProvider || "openai"}
                  disabled={!!settings.useLocalLlm}
                  onChange={(e) => update({ llmProvider: e.target.value })}
                >
                  <option value="openai">OpenAI / Compatible</option>
                  <option value="groq">Groq (fast)</option>
                  <option value="xai">xAI</option>
                  <option value="openrouter">OpenRouter</option>
                </select>
              </div>

              <div style={{ marginTop: 12 }}>
                <button
                  type="button"
                  className="btn settings-btn-block"
                  disabled={!!settings.useLocalLlm}
                  onClick={() =>
                    window.open(
                      `${config.serverUrl}/dashboard`,
                      "_blank"
                    )
                  }
                >
                  Manage keys &amp; credits in web dashboard →
                </button>
              </div>
            </div>

            {/* Autonomous ReAct Agent Mode Option */}
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
                    Enable Autonomous ReAct Agent Mode <span style={{
                      borderRadius: 4,
                      padding: "2px 6px",
                      fontSize: 10,
                      background: "rgba(234, 179, 8, 0.15)",
                      color: "#eab308",
                      fontWeight: 700,
                      textTransform: "uppercase"
                    }}>Experimental</span>
                  </div>
                  <div className="settings-hint" style={{ marginTop: 2 }}>
                    Allow the AI to autonomously reason, search files, read slices, apply patches, and compile/self-heal in a multi-turn ReAct loop.
                  </div>
                </div>
              </label>
            </div>

            <div className="settings-hint">
              {settings.useLocalLlm
                ? "Running with local model. Internet access is not required."
                : "The desktop app just selects the mode. Actual keys and billing live on the web."}
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
