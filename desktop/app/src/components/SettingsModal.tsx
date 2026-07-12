import { useState } from "react";

import * as api from "../api/tauri";
import config from "../config.json";
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

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 480 }}>
        <h2 style={{ marginBottom: 14 }}>Settings</h2>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: '0.78rem', color: '#9aa0a6', display: 'block', marginBottom: 3 }}>Server URL</label>
          <input id="server-url" value={settings.serverUrl} onChange={(e) => onChange({ ...settings, serverUrl: e.target.value })} />
          <div style={{ fontSize: '0.7rem', color: '#7c8595', marginTop: 2 }}>Live server: {config.serverUrl}</div>
        </div>

        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: '0.78rem', color: '#9aa0a6', display: 'block', marginBottom: 3 }}>API Token</label>
          <input id="api-token" type="password" value={settings.apiToken ?? ''} onChange={(e) => onChange({ ...settings, apiToken: e.target.value || null })} placeholder="Paste token from web or dev" />
        </div>

        {!settings.apiToken && (
          <div style={{ background: '#1a1f2a', padding: '10px 12px', borderRadius: 8, marginBottom: 14, fontSize: '0.82rem' }}>
            <div style={{ color: '#f5c542', marginBottom: 6 }}>Quick sign in</div>
            <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
              <input value={email} onChange={e=>setEmail(e.target.value)} placeholder="email" style={{ flex: 1 }} />
              <input value={password} type="password" onChange={e=>setPassword(e.target.value)} placeholder="pass" style={{ flex: 1 }} />
            </div>
            <button type="button" className="btn" disabled={busy || authBusy} onClick={() => void handleGetToken()} style={{ width: '100%', marginBottom: 6 }}>Get dev token</button>

            <div style={{ fontSize: '0.7rem', color: '#9aa0a6' }}>Live server (sign in on web with Google first):</div>
            <button type="button" className="btn" disabled={busy || authBusy} onClick={() => {
              const t = prompt('Paste your Supabase access_token (from web after login)');
              if (t) void handleSessionLogin(t);
            }} style={{ width: '100%' }}>Exchange Supabase token (for live)</button>
            {authError && <p style={{ color: '#ff8a8a', fontSize: '0.7rem', marginTop: 4 }}>{authError}</p>}
          </div>
        )}

        {/* LLM section - beautiful and central to experience */}
        <div style={{ background: '#1a1f2a', padding: '10px 12px', borderRadius: 8, marginBottom: 14 }}>
          <div style={{ fontWeight: 600, marginBottom: 6, fontSize: '0.85rem' }}>🤖 LLM Mode</div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.85rem', marginBottom: 6 }}>
            <input type="checkbox" checked={!!settings.usePersonalLlm} onChange={e => onChange({ ...settings, usePersonalLlm: e.target.checked })} />
            Use my personal keys (BYO)
          </label>
          <select value={settings.llmProvider || 'openai'} onChange={e => onChange({ ...settings, llmProvider: e.target.value })} style={{ width: '100%', marginBottom: 6 }}>
            <option value="openai">OpenAI / Compatible</option>
            <option value="groq">Groq</option>
            <option value="xai">xAI</option>
            <option value="openrouter">OpenRouter</option>
          </select>
          <div style={{ fontSize: '0.7rem', color: '#9aa0a6' }}>
            Manage keys &amp; buy credits in the web dashboard. Desktop just picks the mode.
          </div>
          <button type="button" className="btn" style={{ marginTop: 6, fontSize: '0.75rem' }} onClick={() => window.open(`${config.serverUrl}/dashboard`, '_blank')}>
            Open web dashboard →
          </button>
        </div>

        <div style={{ marginBottom: 10 }}>
          <label style={{ fontSize: '0.78rem', color: '#9aa0a6', display: 'block', marginBottom: 3 }}>Bottom panel</label>
          <select value={settings.bottomDockDefault ?? 'progress'} onChange={e => onChange({ ...settings, bottomDockDefault: e.target.value === 'output' ? 'output' : 'progress' })}>
            <option value="progress">Progress</option>
            <option value="output">Terminal</option>
          </select>
        </div>

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button type="button" className="btn btn-primary" disabled={busy || authBusy} onClick={() => void onSave(settings)}>
            Save &amp; Connect
          </button>
        </div>
      </div>
    </div>
  );
}