-- Migration: Stripe → Lemon Squeezy column names (run if you already applied the old schema)

alter table public.profiles
  rename column stripe_customer_id to lemon_customer_id;

alter table public.subscriptions
  rename column stripe_subscription_id to lemon_subscription_id;

alter table public.subscriptions
  rename column stripe_price_id to lemon_variant_id;