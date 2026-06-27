-- LLM Management System: our provider accounts, detailed usage/cost tracking, autonomous pricing support

-- Our platform LLM provider accounts (we buy the tokens here)
create table if not exists public.llm_providers (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,                    -- e.g. 'openai', 'groq', 'xai'
  display_name text,
  api_base text not null,
  api_key text,                                 -- store encrypted in real prod (pgsodium / vault)
  is_active boolean not null default true,
  priority integer default 100,                 -- lower = preferred
  monthly_budget_usd numeric(12,2),
  auto_replenish boolean default false,
  replenish_threshold_usd numeric(12,2),
  last_replenish_at timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists llm_providers_active_idx on public.llm_providers (is_active, priority);

-- Detailed cost tracking for every platform LLM call (our spend)
create table if not exists public.llm_usages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  provider_name text not null,
  model text not null,
  call_type text not null default 'chat',       -- 'chat' | 'audio' | 'other'
  prompt_tokens integer,
  completion_tokens integer,
  total_tokens integer,
  cost_usd numeric(12,6),
  charged_credits integer,                      -- how many of the user's platform credits we consumed for this
  margin_applied numeric(5,2),
  request_id text,
  metadata jsonb,                               -- extra (voice for audio etc)
  created_at timestamptz default now()
);

create index if not exists llm_usages_user_idx on public.llm_usages (user_id, created_at desc);
create index if not exists llm_usages_provider_model_idx on public.llm_usages (provider_name, model, created_at desc);
create index if not exists llm_usages_created_idx on public.llm_usages (created_at);

-- Simple system settings (margin, global config)
create table if not exists public.system_settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz default now()
);

-- Default margin (40%)
insert into public.system_settings (key, value)
values ('llm_profit_margin', '0.40')
on conflict (key) do nothing;

-- Per-model base cost configuration (our purchase price). Can be updated by admin.
-- Values are USD per 1M tokens (input / output). Used to calculate real cost + auto price.
create table if not exists public.llm_model_pricing (
  id uuid primary key default gen_random_uuid(),
  provider_name text not null,
  model text not null,
  input_price_per_million numeric(12,6) not null,
  output_price_per_million numeric(12,6) not null,
  is_active boolean default true,
  notes text,
  unique (provider_name, model)
);

-- Seed some common prices (approximate as of 2026; admin can update)
insert into public.llm_model_pricing (provider_name, model, input_price_per_million, output_price_per_million) values
('openai', 'gpt-4o-mini', 0.15, 0.60),
('openai', 'gpt-4o', 2.50, 10.00),
('groq', 'llama-3.1-70b', 0.59, 0.79),
('xai', 'grok-2', 2.00, 10.00)
on conflict (provider_name, model) do nothing;

-- Add updated_at trigger for llm_providers
create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists llm_providers_updated on public.llm_providers;
create trigger llm_providers_updated
  before update on public.llm_providers
  for each row execute function public.set_updated_at();

-- RLS: only service role + admins should touch these (we'll rely on service role from server)
alter table public.llm_providers enable row level security;
alter table public.llm_usages enable row level security;
alter table public.system_settings enable row level security;
alter table public.llm_model_pricing enable row level security;

-- Basic policies (service role bypasses). You can tighten later.
-- For admin UI we'll use server endpoints with require_admin.