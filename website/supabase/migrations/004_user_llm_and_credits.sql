-- Support for LLM-agnostic usage + BYO keys + platform token system
-- Users can:
--   1. Provide their own API keys for code gen + audio (BYO, no platform credit spend)
--   2. Use platform LLMs by spending purchased platform credits/tokens

alter table public.profiles
  add column if not exists llm_credits integer not null default 0,
  add column if not exists llm_provider text default 'openai',
  add column if not exists llm_api_key text,          -- WARNING: encrypt at rest in production (Supabase Vault / server KMS)
  add column if not exists llm_model text,
  add column if not exists tts_provider text default 'openai',
  add column if not exists tts_api_key text,
  add column if not exists tts_voice text default 'alloy';

comment on column public.profiles.llm_credits is 'Consumable platform credits/tokens for using Matemium-hosted LLMs (code + audio). BYO keys do not consume these.';
comment on column public.profiles.llm_api_key is 'User provided key for their own LLM (never returned in API responses).';
comment on column public.profiles.tts_api_key is 'User provided key for their own TTS provider.';

-- For production, consider using Supabase Vault or pgsodium for encryption of *_api_key columns.
-- Example (if using pgsodium):
--   alter table ... alter column llm_api_key set data type bytea using llm_api_key::bytea; etc.
-- Or store only last4 + use external secret store.

-- Backfill existing users with some starter credits on free/pro if desired (manual or trigger later).
