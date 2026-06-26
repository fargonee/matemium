# Lemon Squeezy Billing Integration Guide

This project uses [Lemon Squeezy](https://www.lemonsqueezy.com) for payments and subscriptions (Pro plan).

Everything required to integrate is already prepared in the codebase:

- Supabase schema (`profiles` + `subscriptions` tables with `lemon_*` columns)
- Server endpoints: `/v1/billing/checkout`, `/v1/billing/portal`, `/v1/webhooks/lemonsqueezy`
- Webhook signature verification (HMAC SHA-256)
- Frontend pricing cards, billing dashboard, and "Manage billing" flow
- Plan syncing to profile + subscription records (used for entitlements)

## 1. Prerequisites

- A Supabase project (already used for auth)
- A Lemon Squeezy account
- Deployed (or locally running) Matemium Cloud server
- Deployed website (for success redirects and user experience)

## 2. Supabase Setup (one-time)

Run in Supabase SQL editor:

```sql
-- Full schema (recommended on a fresh project)
\i website/supabase/schema.sql
```

If you previously had Stripe columns:

```sql
\i website/supabase/migrations/002_lemon_squeezy.sql
```

After running, ensure these columns exist on `profiles`:

- `lemon_customer_id` (text, unique)
- `plan` (text: 'free' | 'pro' | 'teams')

And `subscriptions` table with:

- `lemon_subscription_id`
- `lemon_variant_id`
- `status`
- `plan`
- `current_period_end`

Promote yourself to admin later:

```sql
update public.profiles set role = 'admin' where email = 'you@example.com';
```

## 3. Create Your Product in Lemon Squeezy

1. Go to **Lemon Squeezy Dashboard → Products**.
2. Create a new **Subscription** product called "Matemium Pro".
3. Add a **Monthly** variant (you can add yearly later).
4. Configure pricing, trial (optional), etc.
5. Save.

**Configure store policies** (important for compliance and customer trust):
- Go to your Store settings in Lemon Squeezy.
- Set up **Refund Policy**, **Cancellation Policy**, and any **Terms of Service**.
- These appear on checkout and customer portal. Lemon Squeezy (as Merchant of Record) cares that you have clear policies and that your backend revokes access on refunds.

**Record these values** (they go into server env):

- **Store ID** (found in URL or Store settings)
- **Variant ID** for the Pro monthly plan (click the variant → look at the URL or copy ID)

## 4. Lemon Squeezy API Keys & Secrets

1. Dashboard → **Settings → API**.
2. Create an API key → copy it (this is `MATEMIUM_LEMON_SQUEEZY_API_KEY`).
3. Dashboard → **Settings → Webhooks**.
4. Add a new webhook endpoint:

   **URL**: `https://<your-deployed-server>/v1/webhooks/lemonsqueezy`

   Recommended events to subscribe to (select all for complete refund + lifecycle support):
   - `order_created`
   - `order_refunded`
   - `subscription_created`
   - `subscription_updated`
   - `subscription_cancelled`
   - `subscription_resumed`
   - `subscription_expired`
   - `subscription_paused`
   - `subscription_unpaused`
   - `subscription_plan_changed`
   - `subscription_payment_success`
   - `subscription_payment_failed`
   - `subscription_payment_recovered`
   - `subscription_payment_refunded`

5. After creating, copy the **Signing Secret** → `MATEMIUM_LEMON_SQUEEZY_WEBHOOK_SECRET`.

## 5. Environment Variables (Server)

Set these in your server deployment (Northflank, Railway, Fly, etc.) or local `.env`:

```bash
MATEMIUM_LEMON_SQUEEZY_API_KEY=ls_...
MATEMIUM_LEMON_SQUEEZY_WEBHOOK_SECRET=...
MATEMIUM_LEMON_SQUEEZY_STORE_ID=12345
MATEMIUM_LEMON_SQUEEZY_VARIANT_PRO_MONTHLY=123456
MATEMIUM_LEMON_SQUEEZY_TEST_MODE=true   # false in production
MATEMIUM_SITE_URL=https://your-website.pages.dev
```

See `server/.env.example` for the full list.

## 6. Environment Variables (Website)

```bash
VITE_API_URL=https://your-server.example.com
VITE_SITE_URL=https://your-website.pages.dev
```

The website does **not** need Lemon Squeezy keys directly.

## 7. Local Development Flow

1. Start the server with the env vars above.
2. Start the website: `cd website && npm run dev`
3. Sign in via Google on the website.
4. Go to `/pricing` → click "Upgrade to Pro".
5. You will be redirected to Lemon Squeezy hosted checkout.
6. Complete a **test** purchase (use Lemon Squeezy test card if in test mode).
7. After success you are sent back to `/dashboard/billing?checkout=success`.
8. Your profile `plan` should become `pro` (via webhook).

**Webhook testing locally**:

Use a tool like ngrok or Cloudflare Tunnel so Lemon Squeezy can reach your local server:

```bash
ngrok http 8080
# Use the https ngrok URL as your webhook endpoint temporarily
```

In the Lemon Squeezy dashboard (Test mode), after creating a test subscription, you can **Simulate** `order_refunded`, `subscription_payment_failed`, etc. directly from the subscription/order detail pages. This is the easiest way to test revocation logic without waiting for real time.

## 8. Production Checklist

- [ ] Set `MATEMIUM_LEMON_SQUEEZY_TEST_MODE=false`
- [ ] Use live API key + correct variant ID
- [ ] Webhook URL points to your public server (HTTPS)
- [ ] Webhook events selected in Lemon Squeezy dashboard
- [ ] `MATEMIUM_SITE_URL` is your production website
- [ ] CORS includes your website origin + desktop origins
- [ ] Test a real checkout end-to-end
- [ ] Verify admin pages show subscription data (`/admin/...`)
- [ ] (Optional) Add more variants (yearly, teams) and extend frontend + server code

## 9. How It Works (Data Flow)

```
User clicks "Upgrade"
  → Website calls POST /v1/billing/checkout (Bearer token)
  → Server creates Lemon checkout with custom_data.supabase_user_id
  → Lemon redirects user back on completion

Lemon sends webhook → POST /v1/webhooks/lemonsqueezy
  → Server verifies X-Signature
  → Server upserts subscription + updates profile.plan
  → Future /v1/me calls reflect the new plan

Refunds (`order_refunded`, `subscription_payment_refunded`) immediately revoke pro access (plan=free + status=refunded).

User clicks "Manage billing"
  → Website calls POST /v1/billing/portal
  → Server fetches customer portal URL from Lemon API
  → User redirected to Lemon-hosted billing portal (cancel, update card, etc.)
```

## 10. Troubleshooting

**"No Lemon Squeezy subscription for this user" on portal**

→ The user does not yet have a row in `subscriptions` with `lemon_subscription_id`.
→ Make sure a successful webhook fired after checkout.

**Plan not updating after purchase**

- Check server logs for webhook handling
- Verify the webhook was received (Lemon Dashboard → Webhooks)
- Ensure the `custom_data` contained `supabase_user_id` at checkout time
- Manually inspect `profiles` and `subscriptions` tables

**Refunds / Chargebacks**

Lemon Squeezy will send `order_refunded` (and `subscription_payment_refunded`).
Our handler immediately:
- Sets `profiles.plan = 'free'`
- Sets the latest subscription `status = 'refunded'`

This is required to avoid access after refund. Failing to handle this can lead to Lemon Squeezy reviewing or restricting your store. Always subscribe to `order_refunded`.

**Signature verification fails**

- Confirm you copied the correct signing secret for that webhook
- Ensure you are sending the raw body (FastAPI `request.body()` does this)

**Test mode vs Live**

- The same store/variant IDs are used
- Toggle `TEST_MODE` + use test cards when `test_mode=true`

**Teams plan**

Currently "Contact sales" only. Extend by adding another variant + handling in checkout.

## 11. Regenerating API Client (after server changes)

```bash
cd website
npm run codegen
# (requires server running on http://127.0.0.1:8080 or update openapi-config.mjs)
```

## 12. References

- Server billing logic: `server/matemium_server/services/billing.py`
- Routes: `server/matemium_server/routes/billing.py`, `webhooks.py`
- Schema: `website/supabase/schema.sql`
- Frontend: `website/src/components/pricing-cards.tsx`, `DashboardBillingPage.tsx`
- Config: `server/.env.example`

---

Once the steps above are completed, Lemon Squeezy billing is fully integrated.
