# Matemium Cloud Server

Thin middleware for the desktop app. **No rendering, no Manim, no DSL compilation.**

## Responsibilities

| In scope | Out of scope |
|----------|--------------|
| User authentication (JWT / API keys) | Video encoding |
| Subscription & credit entitlements | Scene import or lint |
| Rate limiting per plan | Storing rendered media |
| Chat LLM proxy (OpenAI-compatible) | Returning Sheet DSL JSON as primary output |

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
| `GET` | `/v1/me` | Bearer | Profile + subscription (website dashboard) |
| `POST` | `/v1/billing/checkout` | Bearer | Lemon Squeezy checkout URL |
| `POST` | `/v1/billing/portal` | Bearer | Lemon Squeezy customer portal URL |
| `POST` | `/v1/webhooks/lemonsqueezy` | X-Signature | Full subscription + order (incl. refunds) sync → Supabase (register in Lemon Squeezy) |
| `GET` | `/v1/admin/stats` | Admin | User/subscription counts |
| `GET` | `/v1/admin/users` | Admin | User list |
| `GET` | `/v1/admin/subscriptions` | Admin | Subscription list |
| `POST` | `/v1/chat/completions` | Bearer | Chat LLM proxy for desktop |
| `POST` | `/v1/agent/turn` | Bearer | (planned) Agent tool loop |

**Auth:** Website and desktop send `Authorization: Bearer <supabase_access_token>`. The server verifies via Supabase Auth and reads entitlements from Postgres. Desktop dev can use stub tokens when `MATEMIUM_AUTH_STUB=true`.

**Website SPA:** The marketing/dashboard site is a Vite React app at `http://localhost:5173`. It calls this server from the browser; set `MATEMIUM_SITE_URL` and `MATEMIUM_CORS_ORIGINS` accordingly. OpenAPI at `/openapi.json` includes `BearerAuth` on website routes — regenerate the RTK Query client with `cd website && npm run codegen` (server must be running).

**v1 chat:** desktop calls `/v1/chat/completions` with project context; user applies edits locally.

Production-grade additions:
- Per-plan rate limiting (free vs pro) on chat with `X-RateLimit-*` headers.
- Structured request logging + `X-Request-ID`.
- Global error responses + startup validation (stubs disabled in prod).
- Basic AI usage counters surfaced in `/me` (used by dashboard Usage view).
- Pagination + search on admin lists.

**v2 agent:** desktop sends a **context bundle** (files, selection, last compile errors), receives tool calls (`view_file`, `edit_file`, `compile_manim`), executes them locally, and posts tool results until compile succeeds. See [`ai-agent-architecture.md`](../ai-agent-architecture.md) §10.

## Configuration

See [`.env.example`](.env.example). Production requires:
- Supabase service role key
- LLM API key (unless using stubs)
- Lemon Squeezy keys (if billing enabled)

**Lemon Squeezy billing**: Full setup instructions (products, webhooks, env vars, testing) are in the root [`../LEMON_SQUEEZY_SETUP.md`](../LEMON_SQUEEZY_SETUP.md).

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
fly secrets set LLM_API_KEY="sk-..."
fly secrets set LLM_API_BASE="https://api.openai.com/v1"
fly secrets set LLM_MODEL="gpt-4o-mini"
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
| `LLM_API_KEY` | OpenAI-compatible key |
| `LLM_API_BASE` | `https://api.openai.com/v1` |
| `LLM_MODEL` | `gpt-4o-mini` |
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
   | `MATEMIUM_SITE_URL`                    | `https://your-project.pages.dev`                     | Used for billing redirects |
   | `MATEMIUM_LLM_STUB`                    | `false`                                              | Set false for real LLM |
   | `MATEMIUM_LLM_API_KEY`                 | `sk-...`                                             |       |
   | `MATEMIUM_LEMON_SQUEEZY_*`             | ...                                                  | If using billing |
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