-- Production-grade extension: track basic AI usage for dashboard + quotas.
-- Run in Supabase SQL editor after schema.sql (or as new migration).

alter table public.profiles
  add column if not exists ai_calls_count integer not null default 0,
  add column if not exists usage_updated_at timestamptz;

-- Optional future: create usage_events table for audit/history
-- create table if not exists public.usage_events (
--   id uuid primary key default gen_random_uuid(),
--   user_id uuid not null references public.profiles (id) on delete cascade,
--   event_type text not null, -- e.g. 'chat_completion'
--   amount integer not null default 1,
--   metadata jsonb,
--   created_at timestamptz not null default now()
-- );
-- create index if not exists usage_events_user_idx on public.usage_events (user_id, created_at desc);

comment on column public.profiles.ai_calls_count is 'Simple rolling counter of AI/chat interactions (reset strategy implemented in app or via billing webhooks)';
comment on column public.profiles.usage_updated_at is 'Last time usage counters were touched';

-- No additional RLS needed: service role only for increments.
