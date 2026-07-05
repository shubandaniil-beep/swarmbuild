# SwarmBuild AI Internal System Context

Internal document. Do not expose this file in the public UI, generated project
artifacts, client downloads, marketing pages, or support answers.

## Product Role

SwarmBuild AI is an agentic project factory. A user registers, describes a
project, chooses a budget/tariff, and the backend runs a controlled multi-phase
AI workflow. The user receives a downloadable project package: code or document
deliverables, install notes, limitations, cost report, and next-step upsells.

The public promise is simple: "describe what you need, get a usable project
package." The internal system is more complex: budget planning, model routing,
provider key rotation, phase orchestration, artifact filtering, credit charging,
and founder-only observability.

## Runtime Map

```text
frontend Next.js
  landing / login / register / project form / project status / artifacts
  admin-login / admin console / provider keys / models / logs / billing

backend FastAPI
  auth, billing, project API, admin API
  SQLite locally, PostgreSQL-ready through DATABASE_URL
  filesystem workspaces under backend/data/projects/{project_id}

project worker
  daemon thread per project in MVP
  resumable through project status and phase rows
  replaceable later with Redis/RQ/Celery without changing the API contract

AI providers
  OpenAI-compatible adapter: OpenAI, Gemini-compatible endpoint, DeepSeek,
  Qwen, OpenRouter, custom OpenAI-compatible providers
  Anthropic adapter
  Mock adapter for development only, not production routing
```

## Key Request Flow

1. User opens landing page and registers or logs in.
2. Frontend sends `/api/projects` with title, brief, outputs, project type, mode,
   technical level, personality mode, and budget.
3. Backend checks auth, anti-abuse fingerprint/IP limits, and credit eligibility.
4. `project_intake.create_project()` creates:
   - `projects` row
   - `project_phases` rows
   - `brief.md`
   - `budget_state.json`
   - `phase_plan.json`
   - `swarm_state.json`
   - workspace folders: `spec`, `architecture`, `repo`, `reviews`, `artifacts`,
     `logs`
5. User starts the project through `/api/projects/{id}/start`.
6. `project_worker.enqueue()` starts a background thread.
7. `phase_orchestrator.run_project()` loads or repairs phase rows, selects a
   model pool, builds a role rotation plan, and runs each phase.
8. Each agent call goes through `agent_runner.run_agent()`.
9. Provider result is sanitized, persisted as a phase output, logged, and counted
   toward internal estimated cost.
10. Phase completion charges credits unless the project is admin-owned or a demo
    run.
11. Packaging creates public artifacts and `project.zip`.

## Main Statuses

`accepted`: project was created but not started.

`queued`: frontend/API asked to start; worker should pick it up.

`running`: worker is executing phases.

`packaging`: final artifact packaging is running.

`ready`: release policy allowed a full package.

`partial_ready`: package exists, but there are limitations or warnings.

`needs_topup`: user ran out of credits between phases.

`needs_provider`: AI provider or key pool is blocked. Typical causes: no usable
keys, 401/403 auth failure, 429 rate limit, quota exhaustion, upstream capacity
errors.

`failed`: real internal execution error not explained by provider capacity or
billing.

`cancelled`: user/admin stopped the project.

## Phase Plan

Small/demo projects use the short pipeline:

```text
intake -> spec_war -> build_sprint -> review_stop -> packaging
```

Larger projects can use:

```text
intake -> swarm_understanding -> spec_war -> architecture_battle
-> build_sprint -> review_stop -> repair_sprint -> final_audit -> packaging
```

Phase rows are the source of resumability. `run_project()` repairs missing phase
rows from `phase_plan.json`, skips completed phases, and marks failed phases
honestly instead of leaving the project stuck as `running`.

## Model Routing

Public wording should say:

```text
SwarmBuild uses a proprietary model-routing system that assigns different AI
models and roles to each project phase.
```

Do not publish detailed routing rules, provider priority, prompt structure, or
failover order outside internal docs/admin surfaces.

Current internal routing behavior:

1. `model_pool.available_cards()` loads enabled model registry rows joined to
   enabled providers.
2. Real providers are considered usable only when real calls are enabled and the
   provider has at least one enabled, non-error API key.
3. Default provider/model admin pins narrow the pool only when they point to
   real configured routes.
4. Cards are sorted by provider status, priority, and display name.
5. `select_pool()` cycles available cards to match the requested swarm size.
   If only two real models exist and swarm size is six, virtual copies are
   created as distinct agent slots while still pointing to the same provider
   route.
6. `role_rotation.build_rotation_plan()` assigns roles per phase.
7. `agent_runner` uses the selected card and rotates API keys least-recently-used
   through `key_pool.ordered_key_records()`.
8. On model/provider failure, the runner tries same-cost real alternatives
   before considering mock fallback. Mock fallback should stay disabled in
   production.
9. Key-scoped failures mark a key as error: invalid key, unauthorized,
   forbidden, quota, insufficient credits, rate limit.
10. Upstream model capacity failures should not automatically kill the key; they
    should trigger model failover.

## Role Rotation

Roles are internal job contracts, not marketing claims.

`lead`: turns brief into direction and main plan.

`critic`: challenges assumptions and catches weak spots.

`builder`: creates implementation or main deliverable.

`reviewer`: checks output quality and creates issues.

`repairer`: fixes issues from review phases.

`judge`: makes release/audit calls.

`packager`: prepares final delivery.

Important constraints:

- a model should not be `lead` more than two phases in a row;
- `judge` must differ from the phase `lead` when the pool has enough models;
- roles rotate each phase, even if one model is usually "better" for a role.

## Provider Calls And Observability

Each agent call logs:

- project id
- phase key
- mandate
- provider type
- model name
- masked key
- status
- estimated input/output tokens
- estimated USD cost
- safe error message

Events include:

- `project_accepted`
- `swarm_selected`
- `phase_started`
- `agent_call_started`
- `agent_output`
- `phase_finished`
- `credits_charged`
- `provider_blocked`
- `runtime_not_configured`
- `release_decision`
- `packaged`

The admin console should use those events to explain whether work is actually
running, blocked on keys, blocked on credits, or finished with limitations.

## Budget And Credits

Current visible economy:

```text
100 credits = $1 user-facing value
```

Credits are not the same as raw provider tokens. Credits are a product-level
unit that covers:

- provider token cost;
- retries and failovers;
- routing overhead;
- platform margin;
- support cost for packaging, logging, redaction, and security scanning.

Admin should see:

- actual estimated provider cost;
- credits charged;
- implied USD value of credits;
- platform margin.

User should see:

- available credits;
- estimate before start;
- credits charged by phase;
- reason when top-up is needed.

## Artifact Boundary

Internal material must never enter generated client packages:

- system prompts;
- routing details;
- provider priority;
- admin logs;
- raw provider errors with secrets;
- API key plaintext;
- internal docs under `docs/internal`.

`artifact_packager` zips only selected public workspace folders and skips logs,
reviews, specs, architecture internals, prompt files, and implementation logs.
Generated text is passed through the output filter and secret scanner before
download.

## Current Known Weak Points

- Background jobs are process-local threads. Production should move to a durable
  queue: Redis/RQ, Celery, Dramatiq, or a managed job system.
- SQLite is fine locally; production should use PostgreSQL.
- Password hashing currently uses PBKDF2-HMAC-SHA256 with per-password salt.
  Production target should be Argon2id or bcrypt with migration support.
- Sessions are signed stateless tokens in HttpOnly cookies. Production should
  add stricter device/session management, rotation, and optional admin MFA.
- Browser fingerprint limits are useful for abuse reduction, not strong identity
  proof.
- Free OpenRouter models are unstable and rate-limited. Production needs paid
  routes or a mixed provider pool.
- Sandbox is subprocess allowlist with timeouts, not a hardened container
  sandbox.

## Recommended Next Engineering Moves

1. Add paid, stable provider routes before launch.
2. Add durable worker queue and job heartbeat.
3. Add `needs_provider` UI state with clear admin action: add key, reset key,
   switch provider, or lower workload.
4. Add admin MFA and session/device management.
5. Move password hashing to Argon2id with backward-compatible PBKDF2 verify.
6. Add production deployment profile: PostgreSQL, HTTPS, secure cookies,
   backup/restore, logging retention.
7. Add honeypot admin route only as a defensive telemetry system, not as a
   credential collector.
