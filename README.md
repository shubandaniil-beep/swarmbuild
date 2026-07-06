# SwarmBuild AI — Rotating Swarm AI Project Factory

Пользователь описывает идею и выбирает бюджет — платформа запускает
**ротационный рой AI-агентов**, который проходит проект по фазам, меняясь
ролями (lead, critic, builder, reviewer, repairer, judge, packager), и выдаёт
скачиваемый zip: код, спецификацию, бизнес-план, pitch-outline и честный
список ограничений.

```text
идея → бюджет → размер роя → план фаз → ротация ролей → артефакты → project.zip
```

## Стек

| Слой      | Технологии                                           |
|-----------|------------------------------------------------------|
| Backend   | Python 3.11+, FastAPI, SQLAlchemy 2, SQLite/PostgreSQL |
| Frontend  | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| Инфра     | Docker Compose (PostgreSQL + Redis), GitHub Actions  |

## Быстрый старт (локально, без Docker)

Backend (Python 3.11+):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev
```

Откройте http://localhost:3000. По умолчанию рой работает на **mock-моделях**
(API-ключи не нужны): pipeline проходит все фазы и собирает настоящий zip.
Экономика: **100 credits = $1**; новый пользователь получает 100 стартовых
credits на один trial-запуск.

Founder/admin создаётся при первом старте backend:

- email — `ADMIN_EMAIL` (по умолчанию `founder@swarmbuild.ai`);
- пароль — `ADMIN_PASSWORD`; если не задан, генерируется и сохраняется в
  `backend/.founder-password` (только для локальной разработки — в проде
  всегда задавайте `ADMIN_PASSWORD` явно).

Вход в админку: `/admin-login`. Демо-данные (6 проектов, логин
`demo@swarmbuild.ai` / `demo12345`):

```bash
cd backend && PYTHONPATH=. .venv/bin/python scripts/seed_demo.py
```

## Docker Compose (PostgreSQL + Redis)

```bash
cp .env.example .env   # заполните ENCRYPTION_SECRET и ADMIN_PASSWORD
docker compose up --build
```

## Команды

Из корня (см. `Makefile`):

```bash
make dev-backend    # uvicorn с автоперезагрузкой
make dev-frontend   # next dev
make lint           # ruff (backend) + eslint (frontend)
make typecheck      # tsc --noEmit
make test           # pytest: юнит + e2e mock-pipeline
make build          # production-сборка frontend
```

Или по отдельности:

| Где        | Команда                     | Что делает                          |
|------------|-----------------------------|-------------------------------------|
| `backend`  | `.venv/bin/ruff check app tests` | линт                           |
| `backend`  | `.venv/bin/python -m pytest`     | тесты (включая e2e mock-роя)   |
| `frontend` | `npm run dev` / `build` / `start` | dev / сборка / прод-сервер    |
| `frontend` | `npm run lint` / `typecheck`      | eslint / проверка типов       |

## Переменные окружения

Полный список — в [.env.example](.env.example). Ключевые:

| Переменная | Назначение | Default |
|---|---|---|
| `DATABASE_URL` | строка подключения SQLAlchemy | `sqlite:///backend/swarmbuild.db` |
| `STORAGE_PATH` | каталог workspace'ов проектов | `backend/data/projects` |
| `ENCRYPTION_SECRET` | ключ AES-GCM для провайдерских API-ключей. **Задайте один раз до первого запуска и не меняйте** | автогенерация в `backend/.secret` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | founder-аккаунт | `founder@swarmbuild.ai` / автогенерация |
| `ENABLE_REAL_MODEL_CALLS` | `false` = офлайн mock-рой, `true` = реальные провайдеры | `false` |
| `OPENAI_API_KEY` и др. | initial seed ключей; дальше ключи живут в админке (шифруются) | — |
| `CORS_ALLOW_ORIGINS` | продакшн-origin'ы через запятую; пусто = только localhost | — |
| `NEXT_PUBLIC_API_URL` | (frontend) адрес API для браузера | `http://<host>:8000` |

## Структура проекта

```text
swarmbuild/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI-приложение, CORS, security headers
│   │   ├── config.py          # env-конфигурация
│   │   ├── database.py        # engine, сессии, аддитивные миграции
│   │   ├── api/               # HTTP-слой: auth, projects, billing, admin
│   │   ├── models/            # SQLAlchemy-модели
│   │   ├── services/          # бизнес-логика:
│   │   │   ├── budget_engine.py       #   бюджет → размер роя и фазы
│   │   │   ├── role_rotation.py       #   ротация мандатов с инвариантами
│   │   │   ├── phase_orchestrator.py  #   прогон фаз, review/repair
│   │   │   ├── agent_runner.py        #   вызовы моделей, failover, логи
│   │   │   ├── model_pool.py          #   реестр моделей (БД)
│   │   │   ├── key_pool.py            #   пул API-ключей, cooldown
│   │   │   ├── artifact_packager.py   #   сборка финального zip
│   │   │   └── ...                    #   intake, sandbox, release policy
│   │   ├── providers/         # адаптеры: mock, OpenAI-compatible, Anthropic
│   │   ├── prompts/           # промпты ролей (lead, critic, builder, …)
│   │   ├── lib/               # crypto, redaction, rate limit, security
│   │   └── workers/           # фоновый прогон проекта (RQ/Celery-совместимый)
│   ├── tests/                 # pytest: smoke, e2e mock-pipeline, инварианты роя
│   ├── scripts/seed_demo.py
│   └── requirements[-dev].txt, pyproject.toml, Dockerfile
├── frontend/
│   ├── app/                   # страницы: landing, login, projects, admin/*
│   ├── components/            # NavBar, ProjectForm, PhaseTimeline, EventLog…
│   ├── lib/api.ts             # единый API-клиент (cookie-аутентификация)
│   └── package.json, eslint.config.mjs, Dockerfile
├── docs/                      # архитектура, безопасность, разработка
├── docker-compose.yml, Makefile, .env.example
└── .github/workflows/ci.yml   # lint + tests + build
```

## Как работает рой

Фазы: Intake → Swarm Understanding → Spec War → Architecture Battle →
Build Sprint → Review Stop → Repair Sprint → Final Audit → Packaging.

- Бюджет определяет размер роя и набор фаз: `<$25` → 3 агента / 5 фаз,
  `$25–60` → 4, `$60–150` → 6 (+repair sprint), `$150+` → 8.
- Правила ротации: модель не бывает lead более 2 фаз подряд; judge ≠ lead;
  роли меняются каждую фазу. Инварианты закреплены тестами.
- При 85% расхода model-бюджета включается saving mode; при 100% собирается
  частичный пакет (`partial_ready`) — результат не блокируется целиком.
- При ошибке провайдера: retry → ротация ключей пула → failover на модель той
  же ценовой категории → (опционально) mock. Никаких silent fail: проект
  переходит в `needs_provider`/`failed` с событием в журнале.

## Безопасность

- Сессии — HttpOnly-cookie + подписанные токены с версионированием
  (logout отзывает все сессии); токены никогда не передаются в URL.
- Пароли — PBKDF2-HMAC-SHA256 (200k итераций, соль на пароль).
- API-ключи провайдеров шифруются AES-256-GCM, в UI видна только маска.
- Rate-limit логина по IP и email; анти-абьюз регистраций по fingerprint/IP.
- Sandbox-команды: только внутри workspace, allowlist бинарей, timeout;
  сгенерированный код никогда не исполняется на хосте (только `ast.parse`).
- Выводы агентов проходят redaction секретов до выдачи пользователю.
- CORS: строгий allowlist, wildcard невозможен; security headers на всех ответах.

Подробнее — [docs/SECURITY.md](docs/SECURITY.md).

## Ограничения MVP (честно)

- Фоновые задачи — поток внутри процесса API (интерфейс совместим с RQ/Celery,
  вынос в отдельный воркер — одна строка в `workers/project_worker.py`).
- Auth — email/password + роли `user`/`admin`; без OAuth и MFA.
- Sandbox — subprocess с ограничениями, без Docker-изоляции.
- Mock-агенты детерминированы: доказывают механику ротации/фаз/ревью,
  но не заменяют реальные модели.
