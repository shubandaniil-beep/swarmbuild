# Архитектура SwarmBuild

## Общий pipeline

```text
User Input → Project Intake → Budget Engine → Model Pool → Role Rotation
   → Phase Orchestrator → Agent Runner → Blackboard (workspace)
   → Sandbox / Review / Repair / Audit → Artifact Packager → Download
```

## Backend-сервисы (`backend/app/services/`)

| Сервис | Ответственность |
|---|---|
| `project_intake` | создаёт проект, workspace, `budget_state.json`, `phase_plan.json` |
| `budget_engine` | делит бюджет (fee/model/compute/reserve), размер роя, saving mode при 85%, exhausted при 100% |
| `model_pool` | реестр моделей в БД; выбор пула по бюджету и saving mode |
| `key_pool` | пул API-ключей провайдера: LRU-ротация, cooldown при rate-limit, отключение при перманентных ошибках |
| `role_rotation` | назначение мандатов на фазу; инварианты: lead ≤ 2 фаз подряд, judge ≠ lead, роли меняются каждую фазу |
| `access_control` | временные права агента на фазу (read/write scope) |
| `phase_orchestrator` | прогон фаз: контекст → роли → вызовы → outputs → exit criteria; review stop создаёт issues, repair sprint их закрывает |
| `agent_runner` | сборка промпта, вызов провайдера, лестница failover (retry → ключи → same-cost модель → mock), учёт стоимости, журнал вызовов |
| `sandbox_runner` | команды только внутри workspace, allowlist бинарей, timeout |
| `release_policy` | финальное решение release / partial_release / blocked |
| `artifact_packager` | README, INSTALL, business-plan, limitations, cost-report, project.zip |
| `token_ledger`, `credit_pricing` | кредитная экономика: оценка, авторизация, списание по фазам |
| `prompt_guard`, `secret_scanner`, `security_report` | скан брифа на injection, redaction секретов в артефактах |

## Workspace проекта (`STORAGE_PATH/{project_id}/`)

```text
brief.md  budget_state.json  phase_plan.json  swarm_state.json
spec/  architecture/  repo/  reviews/  artifacts/
logs/   # events.jsonl, agent-calls.jsonl, command-runs.jsonl, calls/
```

Агенты не переписываются диалогами — они пишут структурированные артефакты
на «доску» (blackboard). Это делает фазы воспроизводимыми и отлаживаемыми.

## Провайдеры (`backend/app/providers/`)

- `MockProvider` — детерминированный офлайн-рой для dev/тестов;
- `OpenAICompatibleProvider` — OpenAI, DeepSeek, Qwen, Gemini, Groq, OpenRouter
  (единый chat-completions протокол);
- `AnthropicCompatibleProvider` — Anthropic Messages API.

Модели/провайдеры/ключи живут в БД и управляются из админки. Env-переменные —
только initial seed при первом старте.

## Статусы

Проект: `accepted → queued → running → packaging → ready | partial_ready
| needs_topup | needs_provider | failed | cancelled`.

Фаза: `pending → running → done | failed | skipped`.

## Frontend

Next.js App Router. Все запросы идут через единый клиент `lib/api.ts`
(cookie-аутентификация, таймауты, редирект на логин при 401/403, разбор
ошибок). Состояние — локальное для страниц + активный polling статуса
проекта каждые 2s, пока проект в работе. Кэш профиля в localStorage — только
для мгновенного рендера шапки; источник истины `/api/auth/me`.

## Замена компонентов

- Очередь: `workers/project_worker.py` повторяет сигнатуру RQ/Celery-джоба —
  замена `enqueue` подключает Redis-воркер.
- БД: SQLite для dev, PostgreSQL в docker-compose; миграции аддитивные
  (`database._migrate_missing_columns`).
- Провайдер: новый адаптер = один класс с методом `complete()`.
