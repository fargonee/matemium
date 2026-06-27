import { useState } from "react";
import { useSelector } from "react-redux";

import { useGetMeQuery, useUpdateLLMSettingsMutation } from "@/api/matemiumApi";
import { Card } from "@/components/ui/card";
import { ErrorAlert } from "@/components/ui/error-alert";
import { Spinner } from "@/components/ui/spinner";
import { SignOutButton } from "@/components/sign-out-button";
import type { RootState } from "@/store";

export function DashboardAccountPage() {
  const user = useSelector((state: RootState) => state.auth.user);
  const { data: account, isLoading, error, refetch } = useGetMeQuery(undefined, { skip: !user });

  const profile = account?.profile;
  const email = user?.email ?? profile?.email ?? "";
  const credits = profile?.llm_credits ?? 0;
  const hasLlmKey = !!profile?.has_own_llm_key;
  const hasTtsKey = !!profile?.has_own_tts_key;

  const [updateSettings, { isLoading: saving }] = useUpdateLLMSettingsMutation();

  const [llmKey, setLlmKey] = useState("");
  const [ttsKey, setTtsKey] = useState("");
  const [llmProv, setLlmProv] = useState(profile?.llm_provider || "openai");
  const [ttsProv, setTtsProv] = useState(profile?.tts_provider || "openai");
  const [msg, setMsg] = useState<string | null>(null);

  async function saveLLMKeys() {
    setMsg(null);
    try {
      await updateSettings({
        lLMSettingsUpdate: {
          llm_provider: llmProv,
          llm_api_key: llmKey || undefined,
          tts_provider: ttsProv,
          tts_api_key: ttsKey || undefined,
        },
      }).unwrap();
      setMsg("Settings saved. Your keys are used for BYO when provided.");
      setLlmKey("");
      setTtsKey("");
      void refetch();
    } catch (e: any) {
      setMsg("Failed to save: " + (e?.data?.detail || e.message));
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <Spinner /> Loading account…
      </div>
    );
  }

  if (error) {
    return <ErrorAlert onRetry={() => void refetch()}>Could not load account details.</ErrorAlert>;
  }

  return (
    <div className="max-w-2xl space-y-6">
      <Card>
        <h2 className="text-lg font-semibold">Profile</h2>
        <dl className="mt-4 space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-text-subtle">Email</dt>
            <dd className="font-medium">{email}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">Plan</dt>
            <dd className="capitalize">{profile?.plan ?? "free"}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-text-subtle">Platform LLM Credits</dt>
            <dd className="font-bold tabular-nums">{credits}</dd>
          </div>
        </dl>
      </Card>

      {/* LLM Agnostic Integrations */}
      <Card>
        <h2 className="text-lg font-semibold">LLM &amp; Audio Integrations</h2>
        <p className="text-sm text-text-muted mt-1">
          Configure your own LLM/TTS API keys (stored server-side, never exposed in client requests). 
          Choose to use <strong>Personal keys (BYO)</strong> for providers you pay for directly, or <strong>Platform credits</strong> (we manage the keys, you buy credits priced with margin).
        </p>

        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium mb-1">Code Gen Provider {hasLlmKey && <span className="text-success text-xs">(key saved)</span>}</label>
            <input
              value={llmProv}
              onChange={(e) => setLlmProv(e.target.value)}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm"
              placeholder="openai, groq, xai, openrouter..."
            />
            <label className="block text-sm font-medium mt-3 mb-1">LLM API Key (BYO — stored on server)</label>
            <input
              type="password"
              value={llmKey}
              onChange={(e) => setLlmKey(e.target.value)}
              placeholder={hasLlmKey ? "•••••••• (enter to update)" : "sk-... (leave empty to use only Platform)"}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm font-mono"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">TTS Provider {hasTtsKey && <span className="text-success text-xs">(key saved)</span>}</label>
            <input
              value={ttsProv}
              onChange={(e) => setTtsProv(e.target.value)}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm"
              placeholder="openai, elevenlabs..."
            />
            <label className="block text-sm font-medium mt-3 mb-1">TTS API Key (BYO)</label>
            <input
              type="password"
              value={ttsKey}
              onChange={(e) => setTtsKey(e.target.value)}
              placeholder={hasTtsKey ? "•••••••• (enter to update)" : ""}
              className="w-full rounded border border-border bg-bg px-3 py-2 text-sm font-mono"
            />
          </div>
        </div>

        <button
          onClick={saveLLMKeys}
          disabled={saving}
          className="mt-4 rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {saving ? "Saving..." : "Save My Keys (BYO)"}
        </button>

        {msg && <p className="mt-2 text-sm text-success">{msg}</p>}

        <div className="mt-4 text-xs text-text-subtle">
          Your keys are never shown back to you after save. When a key is present we use it instead of platform models (no credit spend).
        </div>
      </Card>

      <div className="flex gap-3">
        <a
          href="/pricing"
          className="inline-flex rounded-full border border-accent px-4 py-2 text-sm font-medium hover:bg-accent/10"
        >
          Buy more platform tokens →
        </a>
        <SignOutButton />
      </div>
    </div>
  );
}
