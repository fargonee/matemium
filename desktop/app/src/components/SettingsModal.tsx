import { useState } from "react";

import * as api from "../api/tauri";
import type { Settings } from "../api/types";
import { formatError } from "../utils/errors";

interface SettingsModalProps {
  settings: Settings;
  open: boolean;
  busy: boolean;
  onChange: (settings: Settings) => void;
  onClose: () => void;
  onSave: (settings: Settings) => Promise<void>;
}

export function SettingsModal({
  settings,
  open,
  busy,
  onChange,
  onClose,
  onSave,
}: SettingsModalProps) {
  const [email, setEmail] = useState("dev@matemium.app");
  const [password, setPassword] = useState("test");
  const [authBusy, setAuthBusy] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  if (!open) return null;

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

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Settings</h2>
        <label htmlFor="server-url">Server base URL</label>
        <input
          id="server-url"
          value={settings.serverUrl}
          onChange={(e) => onChange({ ...settings, serverUrl: e.target.value })}
        />
        <label htmlFor="bottom-dock-default">Default bottom panel</label>
        <select
          id="bottom-dock-default"
          value={settings.bottomDockDefault ?? "progress"}
          onChange={(e) =>
            onChange({
              ...settings,
              bottomDockDefault: e.target.value === "output" ? "output" : "progress",
            })
          }
        >
          <option value="progress">Progress indicators</option>
          <option value="output">Terminal output</option>
        </select>
        <label htmlFor="api-token">API token</label>
        <input
          id="api-token"
          type="password"
          value={settings.apiToken ?? ""}
          onChange={(e) =>
            onChange({
              ...settings,
              apiToken: e.target.value || null,
            })
          }
        />
        {!settings.apiToken ? (
          <>
            <label htmlFor="auth-email">Dev login email</label>
            <input
              id="auth-email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <label htmlFor="auth-password">Dev login password</label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button
              type="button"
              className="btn"
              disabled={busy || authBusy}
              onClick={() => void handleGetToken()}
            >
              Get dev token
            </button>
            {authError ? (
              <p style={{ color: "#ff8a8a", fontSize: "0.78rem" }}>{authError}</p>
            ) : null}
          </>
        ) : null}
        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy || authBusy}
            onClick={() => void onSave(settings)}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}