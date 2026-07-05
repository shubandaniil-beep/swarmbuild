# SwarmBuild AI — Rotating Swarm AI Project Factory (MVP)

Пользователь загружает идею проекта, выбирает бюджет — платформа запускает
**ротационный рой AI-агентов**, который проходит проект по фазам, меняясь
ролями (lead, critic, builder, reviewer, repairer, judge, packager), и выдаёт
скачиваемый zip: код, спека, бизнес-план, pitch-outline и честные ограничения.

```text
user idea → budget → swarm size → phase plan → rotating agent roles → artifacts → zip
```

## Быстрый старт (локально, без Docker)

Бэкенд (Python 3.11+):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Фронтенд (Node 18+):

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:3000. По умолчанию рой работает на **mock-моделях**
(API-ключи не нужны) — pipeline проходит все фазы и собирает реальный zip.
Курс экономики по умолчанию: **100 credits = $1**. Новый пользователь получает
100 стартовых credits и один минимальный demo-запуск.

Founder/CEO admin создаётся при первом запуске:

```text
email: founder@swarmbuild.ai
password: значение ADMIN_PASSWORD из env или auto-generated пароль из backend/.founder-password
```

Демо-данные (6 проектов во всех режимах: code / document / business / mixed):

```bash
cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo.py
# демо-логин: demo@swarmbuild.ai / demo12345
```

Founder/CEO вход в админку: `/admin-login`. После входа откройте
`/admin/providers`: там можно вводить, заменять, удалять и тестировать
API-ключи провайдеров. Обычные пользователи не получают доступ к `/admin`.
Ключи провайдеров шифруются через AES-GCM и в UI показываются только маской.

## Docker Compose (PostgreSQL + Redis)

```bash
cp .env.example .env
docker compose up --build
```

## Реальные модели

В `.env`:

```env
ENCRYPTION_SECRET=long-random-secret
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=strong-password
ENABLE_REAL_MODEL_CALLS=true
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
OPENROUTER_API_KEY=...
TELEGRAM_PAYMENT_BOT_URL=https://t.me/your_bot
```

Env-ключи используются только как initial seed. Дальше добавляйте и проверяйте
провайдеры через `/admin/providers`, а модели — через `/admin/models`.
Адаптеры: `MockProvider`, `OpenAICompatibleProvider` (OpenAI/DeepSeek/Qwen/Gemini/OpenRouter),
`AnthropicCompatibleProvider`. При ошибке вызова — 1 retry, затем same-cost
failover, затем mock fallback.

## Фазы

Intake → Swarm Understanding → Spec War → Architecture Battle → Build Sprint →
Review Stop → Repair Sprint → Final Audit → Packaging.

Размер роя и набор фаз зависят от бюджета: `<$25` → 3 агента / 5 фаз,
`$25–60` → 4 / базовый pipeline, `$60–150` → 6 / + repair sprint, `$150+` → 8.
При 85% расхода model-бюджета включается saving mode, при 100% — сборка
partial-результата (`partial_ready`), а не полная блокировка.

## Ключевые правила ротации

- модель не бывает lead более 2 фаз подряд;
- judge фазы ≠ lead фазы;
- роли ротируются каждую фазу, «любимых» ролей нет.

## API

```http
POST /api/projects              # создать проект
POST /api/projects/{id}/start   # запустить рой
GET  /api/projects/{id}         # статус + бюджет
GET  /api/projects/{id}/phases
GET  /api/projects/{id}/events
GET  /api/projects/{id}/artifacts
GET  /api/projects/{id}/artifacts/{artifact_id}/content
GET  /api/projects/{id}/artifacts/{artifact_id}/download
GET  /api/projects/{id}/download   # project.zip
POST /api/projects/{id}/continue
GET  /api/admin/dashboard
GET  /api/admin/providers
GET  /api/admin/models
GET  /api/admin/tariffs
GET  /api/admin/project-types
GET  /api/admin/projects/{id}/logs
POST /api/admin/projects/{id}/rerun-phase
POST /api/admin/projects/{id}/force-package
```

## Workspace проекта

```text
data/projects/{project_id}/
  brief.md  budget_state.json  phase_plan.json  swarm_state.json
  spec/  architecture/  repo/  reviews/  artifacts/  logs/
```

`logs/` содержит events.jsonl, agent-calls.jsonl, command-runs.jsonl.
Sandbox-команды выполняются только внутри workspace, по allowlist-у бинарей и
с timeout.

## Ограничения MVP (честно)

- фоновые задачи — поток в процессе API (интерфейс совместим с RQ/Celery);
- auth — email/password + роли `user`/`admin`; без OAuth и без полноценной
  production session policy;
- sandbox — subprocess с timeout и allowlist, без Docker-изоляции;
- mock-агенты генерируют детерминированные артефакты — этого достаточно, чтобы
  доказать механику ротации/фаз/ревью/репейра, но не заменяет реальные модели.

## Внутренняя документация

Подробный контекст по архитектуре, роутингу моделей, безопасности, honeypot-идее
и production-чеклисту лежит в `docs/internal/`.

Эти документы не должны попадать в публичный UI, клиентские zip-артефакты,
маркетинговые страницы или ответы поддержки.
