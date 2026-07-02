import { useEffect, useState } from "react";

import * as api from "../api/tauri";
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
                Live server: https://p01--math--zjvwyx4fjqbn.code.run
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
          <div className="settings-section">
            <div className="settings-section-header">
              <h3>AI &amp; LLM</h3>
              <p className="settings-section-desc">
                Choose how the AI assistant and generation features work.
              </p>
            </div>

            <div className="settings-card">
              <label className="settings-checkbox-row">
                <input
                  type="checkbox"
                  checked={!!settings.usePersonalLlm}
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
                  onClick={() =>
                    window.open(
                      "https://p01--math--zjvwyx4fjqbn.code.run/dashboard",
                      "_blank"
                    )
                  }
                >
                  Manage keys &amp; credits in web dashboard →
                </button>
              </div>
            </div>

            <div className="settings-hint">
              The desktop app just selects the mode. Actual keys and billing live on the web.
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
