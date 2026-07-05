# Production Readiness Runbook

Internal launch checklist for SwarmBuild AI.

## Current Local State

The local app runs as:

```text
frontend: http://127.0.0.1:3000
backend:  http://127.0.0.1:8000
```

Backend health:

```bash
curl http://127.0.0.1:8000/api/health
```

Admin entry:

```text
/admin-login
```

Founder/admin password is either `ADMIN_PASSWORD` from env or the local
auto-generated password file. Do not commit that file.

## Minimum Deploy Environment

Required:

```env
ENCRYPTION_SECRET=long-random-production-secret
ADMIN_EMAIL=founder@example.com
ADMIN_PASSWORD=long-unique-admin-password
DATABASE_URL=postgresql://...
CORS_ALLOW_ORIGINS=https://your-domain.com
ENABLE_REAL_MODEL_CALLS=true
```

Recommended:

```env
TELEGRAM_PAYMENT_BOT_URL=https://t.me/your_payment_bot
TRUST_PROXY_HEADERS=true
ENABLE_API_DOCS=false
```

Do not deploy with a weak or missing `ENCRYPTION_SECRET`; it protects session
signing and provider API-key encryption.

## Provider Setup

1. Add at least two real provider routes before launch.
2. Prefer paid/stable routes for production. Free OpenRouter models are useful
   for smoke tests but too rate-limited for customers.
3. Keep OpenRouter free models as fallback only.
4. Test every key from `/admin/providers`.
5. Confirm `/admin/logs` shows:
   - `agent_call_started`;
   - `agent_output`;
   - masked key;
   - provider/model name;
   - safe errors when blocked.

Operational interpretation:

```text
needs_provider = add/replace/reset provider keys or switch models
needs_topup    = user must add credits
partial_ready  = package exists, but limitations are present
ready          = package created and release policy passed
failed         = internal execution error, inspect logs
```

## Worker Readiness

MVP uses in-process daemon threads. This is acceptable for local demos, not for
durable production.

Production target:

```text
FastAPI API process
Redis queue
worker process
PostgreSQL
object storage for artifacts
```

Worker requirements:

- heartbeat per active project;
- restart recovery;
- idempotent phase execution;
- max runtime per phase;
- max agent calls per project;
- provider timeout;
- explicit cancellation.

## Database

Local SQLite is acceptable only for development.

Production:

- PostgreSQL;
- daily backups;
- restore test before launch;
- migration mechanism instead of only additive startup migration;
- indexes on project id, user id, event created_at, provider key status.

## Security Launch Checklist

Before public traffic:

- `ADMIN_PASSWORD` set and strong;
- legacy dev admin disabled;
- `ENCRYPTION_SECRET` set and backed up securely;
- HTTPS enabled;
- secure cookies enabled by HTTPS;
- CORS allowlist set to production domain only;
- API docs disabled unless intentionally exposed;
- public admin routes protected by `require_admin`;
- provider keys visible only as masks;
- generated artifacts scanned and redacted;
- admin logs do not include raw prompts or keys;
- browser fingerprint and IP signup limits enabled;
- login rate limits enabled;
- admin MFA planned before paid launch.

## Payment/Credit Readiness

Current economy:

```text
100 credits = $1
```

Current behavior:

- free user gets 100 credits and one tiny demo generation;
- admin is not charged;
- trial runs burn the starter credits like any other project;
- non-demo phases burn fixed credits after phase completion;
- internal provider cost is tracked separately.

Payment foundation:

- top-up records exist;
- Telegram payment bot URL setting exists;
- admin can inspect top-ups;
- future payment webhook should create a verified top-up and credit the user.

Do not let client-side credit numbers be authoritative. The backend ledger must
be the source of truth.

## Customer-Facing Copy Rules

Say:

```text
Proprietary model routing selects the right AI role for each project phase.
```

Do not say:

```text
Exact prompt structure, role weights, provider order, fallback rules, or model
priority.
```

Say:

```text
Credits cover generation, quality checks, packaging, and provider costs.
```

Do not say:

```text
Credits are raw provider tokens.
```

## Release Smoke Test

Use a fresh user account:

1. Open landing page.
2. Register.
3. Confirm project panel is inaccessible before login.
4. Create a tiny project.
5. Start project.
6. Watch project status move through phases.
7. Confirm final status is `ready`, `partial_ready`, `needs_topup`, or
   `needs_provider`; it must not stay in `running`.
8. Download artifacts.
9. Confirm zip has no prompts, logs, provider keys, or internal docs.
10. Log in as admin and check provider/model/cost logs.

## Current Recommendation

The app is suitable for founder demos and internal testing after the latest
runner fixes.

It is not ready for paid public launch until:

- stable paid model routes are configured;
- durable worker queue is added;
- PostgreSQL deployment is tested;
- admin MFA/session controls are added;
- payment webhook path is implemented;
- production smoke test passes with real provider keys.
