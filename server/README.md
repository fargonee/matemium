# Matemium Cloud Server

Thin middleware for the desktop app. **No rendering, no Manim, no DSL compilation.**

## Responsibilities

| In scope | Out of scope |
|----------|--------------|
| User authentication (JWT / API keys) | Video encoding |
| User profile/provider preference sync | Scene import or lint |
| Abuse/rate protection for Matemium endpoints | Storing rendered media |
| BYO chat LLM proxy helpers (OpenAI-compatible) | Returning Sheet DSL JSON as primary output |
| OpenRouter OAuth callback/key exchange support | Selling subscriptions, AI tokens, or pooled provider keys |

The server returns **natural language + optional code edit blocks** (v1 chat) or **tool-call messages** (v2 agent) for `scenes.py` / `assets.py` — not compiled animations. Agent orchestration spec: [`ai-agent-architecture.md`](../ai-agent-architecture.md).

## Layout

```
server/
├── pyproject.toml
├── .env.example
├── src/matemium_server/
│   ├── app.py              FastAPI application
│   ├── config.py           Environment settings
│   ├── routes/             HTTP endpoints
│   └── services/           LLM proxy (stub + real)
└── tests/
```

## Development

```bash
cd server
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
python -m matemium_server
# → http://127.0.0.1:8080/health
```

Or: `uvicorn matemium_server.app:app --reload --port 8080`

## API (v1)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | — | Liveness |
| `POST` | `/v1/auth/token` | — | Dev desktop stub (`MATEMIUM_AUTH_STUB=true`) |
| `POST` | `/v1/auth/session` | — | Exchange Supabase access token (Google sign-in) |
| `GET` | `/v1/auth/verify` | Bearer | Validate current token |
| `GET` | `/v1/me` | Bearer | Profile + provider preferences (website/dashboard) |
| `POST` | `/v1/billing/checkout` | Bearer | Historical/disabled unless paid offerings return |
| `POST` | `/v1/billing/portal` | Bearer | Historical/disabled unless paid offerings return |
| `POST` | `/v1/webhooks/lemonsqueezy` | X-Signature | Historical billing sync endpoint; not part of current product policy |
| `GET` | `/v1/admin/stats` | Admin | User counts and operational stats |
| `GET` | `/v1/admin/users` | Admin | User list |
| `GET` | `/v1/admin/subscriptions` | Admin | Subscription list |
| `POST` | `/v1/chat/completions` | Bearer | Chat LLM proxy for desktop |
| `POST` | `/v1/agent/turn` | Bearer | (planned) Agent tool loop |

**Auth:** Website and desktop send `Authorization: Bearer <supabase_access_token>`. The server verifies via Supabase Auth and reads profile/provider settings from Postgres. Desktop dev can use stub tokens when `MATEMIUM_AUTH_STUB=true`.

**Website SPA:** The marketing/dashboard site is a Vite React app at `http://localhost:5173`. It calls this server from the browser; set `MATEMIUM_SITE_URL` and `MATEMIUM_CORS_ORIGINS` accordingly. OpenAPI at `/openapi.json` includes `BearerAuth` on website routes — regenerate the RTK Query client with `cd website && npm run codegen` (server must be running).

**v1 chat:** desktop calls `/v1/chat/completions` with project context; user applies edits locally.

Production-grade additions:
- Abuse/rate protection on Matemium endpoints with `X-RateLimit-*` headers; limits must not imply paid tiers unless the product policy changes.
- Structured request logging + `X-Request-ID`.
- Global error responses + startup validation (stubs disabled in prod).
- Basic AI usage counters surfaced in `/me` (used by dashboard Usage view).
- Pagination + search on admin lists.

**v2 agent:** desktop sends a **context bundle** (files, selection, last compile errors), receives tool calls (`view_file`, `edit_file`, `compile_manim`), executes them locally, and posts tool results until compile succeeds. See [`ai-agent-architecture.md`](../ai-agent-architecture.md) §10.

## Configuration

See [`.env.example`](.env.example). Production requires:
- Supabase service role key
- OpenRouter OAuth callback configuration if using the one-click connection flow
- No Matemium-owned LLM API key is required for production BYO mode
- Lemon Squeezy keys only if historical billing endpoints are deliberately re-enabled

**Lemon Squeezy billing**: The root [`../LEMON_SQUEEZY_SETUP.md`](../LEMON_SQUEEZY_SETUP.md) is historical. Matemium currently does not charge users or sell subscriptions.

## Deployment

Designed for near-zero ops: single stateless container, no render queue, no object storage for v1.

### Fly.io

```bash
# Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
fly auth login
cd server
fly launch --no-deploy --name matemium-server --region ord

# Set secrets (production)
fly secrets set JWT_SECRET="$(openssl rand -hex 32)"
fly secrets set OPENROUTER_OAUTH_CALLBACK_URL="https://your-app.example.com/openrouter/callback"
fly secrets set LLM_STUB="false"

fly deploy
curl -s https://matemium-server.fly.dev/health | jq .
```

Use the deployed base URL in the desktop app **Settings → Server base URL** (e.g. `https://matemium-server.fly.dev`).

### Railway

```bash
npm i -g @railway/cli
railway login
cd server
railway init
railway up
```

In the Railway dashboard, set environment variables:

| Variable | Example |
|----------|---------|
| `JWT_SECRET` | random 32+ byte secret |
| `OPENROUTER_OAUTH_CALLBACK_URL` | `https://your-app.example.com/openrouter/callback` |
| `LLM_STUB` | `false` |

Verify: `curl -s https://<your-app>.up.railway.app/health`

### Northflank (PaaS)

Northflank works great with the included Dockerfile.

**Important:** The server publish is completely isolated from the engine/website/desktop.

1. In Northflank:
   - Create a new **Service** → **Deployment** → choose **Docker**
   - Connect your GitHub repo
   - **Dockerfile path**: `server/Dockerfile`
   - **Build context**: the `server` directory  (recommended) or use "context path" = `server`
   - This + `server/.dockerignore` guarantees the image contains *only* server code (no canvas, no desktop node_modules, no Rust target, no render outputs).

See also the root [STRUCTURE.md](../STRUCTURE.md) for publish boundaries.
2. Add the required environment variables (under Service → Environment):
   | Variable                               | Value (example)                                      | Notes |
   |----------------------------------------|------------------------------------------------------|-------|
   | `MATEMIUM_ENV`                         | `production`                                         |       |
   | `MATEMIUM_SUPABASE_URL`                | `https://xxx.supabase.co`                            | Same project as website |
   | `MATEMIUM_SUPABASE_ANON_KEY`           | `sb_publishable_...`                                 |       |
   | `MATEMIUM_SUPABASE_SERVICE_ROLE_KEY`   | `sb_secret_...` (keep private)                       | Needed for DB + admin ops |
   | `MATEMIUM_CORS_ORIGINS`                | `https://your-project.pages.dev,https://*.pages.dev,https://*.northflank.app` | Add Cloudflare Pages + server origins |
   | `MATEMIUM_SITE_URL`                    | `https://your-project.pages.dev`                     | Used for site redirects |
   | `MATEMIUM_LLM_STUB`                    | `false`                                              | Set false for real LLM |
   | `MATEMIUM_OPENROUTER_OAUTH_CALLBACK_URL` | `https://.../openrouter/callback`                  | For one-click OpenRouter connection |
   | `MATEMIUM_LEMON_SQUEEZY_*`             | ...                                                  | Historical only; current product does not charge users |
   | `MATEMIUM_ADMIN_EMAILS`                | `you@...`                                            |       |

3. Northflank will expose a public URL like `https://matemium-server-abc123.northflank.app`.
   - Use this as `VITE_API_URL` when building the **website**.
   - Use this in the desktop Tauri app Server settings when connecting to cloud.

Health check endpoint: `GET /health` (already configured).

Response includes `status`, `version`, and `commit` (populated with `COMMIT_SHA` when the GHA deploy passes it).

Recommended Northflank settings (critical for zero-downtime):
- Health check path: `/health` (readiness + startup probe recommended)
- Instances: 2+ (enables rolling updates with no downtime)
- Port: leave default or match the exposed `PORT`

The GitHub deploy workflow now:
- Waits for build
- Deploys the specific build
- Verifies the live `/health`
- Automatically rolls back to the previous successful build if verification fails, then marks the job failed.

### Local stub (development)

```bash
cd server && source .venv/bin/activate && python -m matemium_server
# Desktop default: http://127.0.0.1:8080
# Settings → Get dev token (email/password any value for stub)
```

## Boundary

- **No imports from `canvas/` or `matemium/`** — server is a separate Python package.
- Shared contracts live in [`shared/`](../shared/).

## Launch / Production Checklist (Webapp)

1. Run all Supabase migrations in order:
   - schema.sql
   - 002_lemon_squeezy.sql (historical billing only; skip for current free product unless schema compatibility is needed)
   - 003_usage_counters.sql
   - 004_user_llm_and_credits.sql
   - 005_llm_management.sql

2. Set production env vars (never commit secrets):
   - `MATEMIUM_ENV=production`
   - `MATEMIUM_AUTH_STUB=false`
   - `MATEMIUM_LLM_STUB=false`
   - `MATEMIUM_OPENROUTER_OAUTH_CALLBACK_URL=...` if OpenRouter OAuth is enabled
   - Do not configure a Matemium platform LLM key for user traffic; users bring their own keys
   - Do not configure Lemon Squeezy variables unless paid offerings are intentionally reintroduced
   - Supabase service role, admin emails, CORS with your real domains.

3. For LLM management:
   - Treat provider records as user-owned BYO configuration, not Matemium-owned accounts or budgets.
   - Do not calculate profit margins or deduct Matemium credits for BYO calls.
   - Record provider/model/usage metadata only for user visibility, debugging, and abuse protection.

4. Website build: set `VITE_API_URL` and `VITE_SITE_URL` to production values before `npm run build`.

5. Deploy order:
   - Supabase (DB + auth)
   - Server (Northflank/Fly/etc.) → verify /health and /v1/me
   - Website (Cloudflare Pages)
   - Update desktop (later) to point to prod server.

6. Post-launch:
   - Monitor endpoint health and provider failures without treating usage as Matemium spend.
   - Encourage users to rotate their own provider keys regularly.
   - Encrypt user `*_api_key` columns in production if keys are stored server-side at all (pgsodium recommended).
