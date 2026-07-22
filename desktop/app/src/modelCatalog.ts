import type { ProviderModel, Settings } from "./api/types";

export const PROVIDER_NAMES: Record<string, string> = {
  openrouter: "OpenRouter",
  openai: "OpenAI",
  groq: "Groq",
  xai: "xAI",
};

export const DEFAULT_PINNED_MODELS: Record<string, ProviderModel[]> = {
  openrouter: [
    {
      id: "openrouter/free",
      name: "OpenRouter Free",
      provider: "openrouter",
      pricingLabel: "Free",
      badges: ["Free"],
    },
    {
      id: "openai/gpt-4o-mini",
      name: "GPT-4o mini",
      provider: "openrouter",
      badges: ["Popular"],
    },
    {
      id: "anthropic/claude-3.5-sonnet",
      name: "Claude 3.5 Sonnet",
      provider: "openrouter",
      badges: ["Popular"],
    },
    {
      id: "deepseek/deepseek-r1",
      name: "DeepSeek R1",
      provider: "openrouter",
      badges: ["Reasoning"],
    },
  ],
  openai: [
    { id: "gpt-4o-mini", name: "GPT-4o mini", provider: "openai", badges: ["Popular"] },
    { id: "gpt-4o", name: "GPT-4o", provider: "openai", badges: ["Popular"] },
    { id: "o4-mini", name: "o4-mini", provider: "openai", badges: ["Reasoning"] },
  ],
  groq: [
    {
      id: "llama-3.1-8b-instant",
      name: "Llama 3.1 8B Instant",
      provider: "groq",
      badges: ["Fast"],
    },
    {
      id: "llama-3.3-70b-versatile",
      name: "Llama 3.3 70B Versatile",
      provider: "groq",
      badges: ["Popular"],
    },
  ],
  xai: [
    { id: "grok-2-latest", name: "Grok 2", provider: "xai", badges: ["Popular"] },
    { id: "grok-3-mini", name: "Grok 3 mini", provider: "xai", badges: ["Reasoning"] },
  ],
};

export function providerModelState(settings: Settings, provider: string) {
  return settings.providerModels?.[provider] ?? {};
}

export function providerDefaultPinnedIds(provider: string): string[] {
  return (DEFAULT_PINNED_MODELS[provider] ?? []).map((model) => model.id);
}

export function pinnedModelIds(settings: Settings, provider: string): string[] {
  const stored = providerModelState(settings, provider).pinned;
  if (stored) {
    return unique(stored);
  }
  return providerDefaultPinnedIds(provider);
}

export function pinnedModelOptions(settings: Settings, provider: string): ProviderModel[] {
  const state = providerModelState(settings, provider);
  const catalog = state.catalog ?? [];
  const defaults = DEFAULT_PINNED_MODELS[provider] ?? [];
  return pinnedModelIds(settings, provider).map((id) => {
    return (
      catalog.find((model) => model.id === id) ??
      defaults.find((model) => model.id === id) ?? {
        id,
        name: modelDisplayName(id),
        provider,
        badges: [],
      }
    );
  });
}

export function modelDisplayName(id: string): string {
  return id
    .split("/")
    .pop()!
    .replaceAll("-", " ")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatModelMeta(model: ProviderModel): string {
  const parts = [
    PROVIDER_NAMES[model.provider] ?? model.provider,
    model.pricingLabel,
    model.contextLength ? `${Math.round(model.contextLength / 1000)}k ctx` : null,
  ].filter(Boolean);
  return parts.join(" · ");
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values.filter(Boolean)));
}
