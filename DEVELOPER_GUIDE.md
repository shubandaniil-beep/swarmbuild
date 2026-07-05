# SwarmBuild — Руководство для разработчиков

Добро пожаловать в SwarmBuild — платформу для создания проектов с помощью ротирующихся AI-агентов. Этот документ содержит всю необходимую информацию для работы с проектом.

---

## 📋 Быстрый старт

### Требования
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (опционально, для production)
- Redis (опционально, для production)

### Локальная разработка (без Docker)

**Бэкенд:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Фронтенд (в отдельном терминале):**
```bash
cd frontend
npm install
npm run dev
```

**Доступ:**
- Фронтенд: http://localhost:3000
- Бэкенд: http://localhost:8000
- API Docs: http://localhost:8000/docs

**Админка:**
- Вход: http://localhost:3000/admin-login
- Email: `founder@swarmbuild.ai`
- Пароль: смотри файл `backend/.founder-password`

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

---

## 🏗️ Архитектура проекта

### Структура директорий

```
swarmbuild/
├── backend/                          # Python/FastAPI
│   ├── app/
│   │   ├── main.py                  # Entry point
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── schemas.py               # Pydantic schemas
│   │   ├── config.py                # Settings & env vars
│   │   ├── routers/                 # API endpoints
│   │   ├── services/                # Business logic
│   │   ├── lib/                     # Utilities (crypto, logging, etc)
│   │   ├── prompts/                 # Agent directives for each phase
│   │   └── sandbox/                 # Sandbox execution
│   ├── scripts/
│   │   └── seed_demo.py            # Демо-данные
│   ├── tests/                       # Pytest tests
│   ├── requirements.txt             # Dependencies
│   └── .env.example                # Environment template
│
├── frontend/                         # Next.js / React
│   ├── app/
│   │   ├── page.tsx               # Main page
│   │   ├── admin/                 # Admin pages
│   │   └── api/                   # API routes (if any)
│   ├── components/                # React components
│   ├── lib/                       # Frontend utilities
│   ├── public/                    # Static assets
│   ├── package.json
│   └── tsconfig.json
│
├── docs/
│   ├── DEVELOPMENT_COMMANDS.md    # Разработка & deployment
│   └── internal/                  # Внутренние docs (secret ≠ public)
│
├── docker-compose.yml
├── README.md
└── DEVELOPER_GUIDE.md            # Этот файл
```

---

## 🎯 Основные концепции

### Проект (Project)
Когда пользователь загружает идею и выбирает бюджет, создается проект. Каждый проект проходит через фазы (phases), выполняемые ротирующимся роем AI-агентов.

### Фазы (Phases)
```
intake → swarm_understanding → spec_war → architecture_battle → 
build_sprint → review_stop → repair_sprint* → final_audit → packaging

* repair_sprint опционально (зависит от бюджета)
```

Каждая фаза:
- Имеет фиксированную стоимость в credits
- Выполняется другим агентом (ротация ролей)
- Генерирует артефакты (спека, код, документация, etc)
- Логируется в `logs/events.jsonl`

### Рой агентов (Swarm)
Набор AI-моделей, которые выполняют разные роли в разных фазах:
- **Lead** — координатор фазы
- **Critic** — проверяет качество
- **Builder** — пишет код/спеку
- **Reviewer** — рецензент
- **Judge** — выносит финальное решение
- **Packager** — собирает артефакты

**Правила ротации:**
- Модель не может быть lead более 2 фаз подряд
- Judge фазы ≠ lead фазы
- Роли ротируются каждую фазу

### Кредитная система
- **1 credit = $0.01 USD** (настраивается)
- Credits списываются за каждую завершенную фазу (фиксированная стоимость)
- Если бюджет заканчивается → `saving_mode` → `partial_ready` (сборка имеющихся результатов)

### Workspace проекта
При создании проекта создается директория:
```
data/projects/{project_id}/
├── brief.md                    # Исходное описание
├── budget_state.json           # Текущий бюджет
├── phase_plan.json             # План фаз
├── swarm_state.json            # История вызовов агентов
├── spec/                       # Техническая спецификация
├── architecture/               # Архитектура & диаграммы
├── repo/                       # Исходный код
├── reviews/                    # Рецензии
├── artifacts/                  # Финальные артефакты
└── logs/                       # Логи (events.jsonl, agent-calls.jsonl, etc)
```

---

## 🔑 Управление API ключами

### Добавить ключи (админка `/admin/providers`)

1. Выбери провайдера (OpenAI, Anthropic, Gemini, DeepSeek, Qwen, OpenRouter)
2. Нажми "Показать пул ключей"
3. Вставь ключи (разделены пробелом, запятой или переносом)
4. Нажми "Добавить"

### Тестировать ключи

```bash
POST /api/admin/providers/{id}/test
```

Система проверит каждый ключ и покажет статус.

### Включить/отключить ключ

В админке откройте пул ключей провайдера и переключите статус ключа.

### Ключи автоматически используются:
- **Mock mode** (разработка) — не требуют реальных ключей
- **Real mode** — система циклирует ключи, fallback на mock при ошибке (429, 401)

---

## 🚀 Запуск проекта в разработке

### Режим разработки (mock-агенты)

```bash
# Бэкенд уже использует mock-агенты по умолчанию
cd backend
uvicorn app.main:app --reload --port 8000

# Фронтенд в отдельном терминале
cd frontend
npm run dev
```

**Mock-агенты** генерируют детерминированные артефакты — этого достаточно для тестирования механики, но не заменяют реальные модели.

### Включить реальные модели

В `.env`:
```env
ENABLE_REAL_MODEL_CALLS=true
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

И добавь ключи через админку (`/admin/providers`).

---

## 📡 API endpoints

### Проекты

```http
POST   /api/projects                    # Создать проект
GET    /api/projects                    # Мои проекты
GET    /api/projects/{id}               # Статус + бюджет
GET    /api/projects/{id}/phases        # Фазы
GET    /api/projects/{id}/events        # События/логи
GET    /api/projects/{id}/artifacts     # Артефакты
GET    /api/projects/{id}/download      # Скачать project.zip
POST   /api/projects/{id}/start         # Запустить рой
POST   /api/projects/{id}/continue      # Продолжить после паузы
```

### Аутентификация

```http
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
POST   /api/auth/change-password
```

### Админка

```http
GET    /api/admin/dashboard             # Статистика
GET    /api/admin/providers             # Провайдеры & ключи
GET    /api/admin/models                # Модели
GET    /api/admin/tariffs               # Тарифы
GET    /api/admin/projects/{id}/logs    # Логи проекта
POST   /api/admin/projects/{id}/rerun-phase   # Перезапустить фазу
POST   /api/admin/projects/{id}/force-package # Завершить проект
```

Полная документация: http://localhost:8000/docs (OpenAPI)

---

## 🧪 Тестирование

### Бэкенд (pytest)

```bash
cd backend

# Все тесты
pytest

# С покрытием
pytest --cov=app --cov-report=html

# Конкретный файл
pytest tests/test_auth.py

# С verbose выводом
pytest -v

# С stdout
pytest -s
```

### Фронтенд (Jest)

```bash
cd frontend

# Все тесты
npm test

# Watch mode
npm test -- --watch

# С покрытием
npm test -- --coverage
```

---

## 🔐 Безопасность

### Встроенные механизмы

1. **Secret scanning** — автоматическое обнаружение API-ключей в артефактах
2. **Prompt injection detection** — сканирование brief на подозрительные паттерны
3. **Sandbox ограничения** — whitelist бинарей, timeout, workspace confinement
4. **Audit logging** — все операции админа логируются

### Чувствительные данные

- API-ключи шифруются через AES-GCM
- `.env` файлы конвертируются в `.env.example` перед скачиванием
- Секреты redact-ятся из логов

### Sandbox (команды)

При выполнении команд агентами:
- Только whitelist: python, node, npm, git, docker (если разрешено)
- Timeout 30 сек
- Workspace confinement (no `..`, `~`, абсолютные пути)
- Блокированные: `rm -rf`, `chmod`, `sudo`, `mkfs`, `/etc/passwd`

---

## 💳 Кредитная система

### Тарифные пакеты

| Пакет | Цена | Credits | Бонус | Фазы |
|-------|------|---------|-------|------|
| Free Test Run | $1 | 100 | 0% | 5 |
| Fast Build | $20 | 2,000 | 0% | 5 |
| Small MVP | $40 | 4,400 | 10% | 8 |
| Standard MVP | $100 | 12,000 | 20% | 9 |
| Heavy Build | $200 | 26,000 | 30% | 9 |
| Custom | $500 | 70,000 | 40% | 9 |

### Pre-run оценка

```bash
POST /api/projects/estimate
{
  "phase_keys": ["intake", "swarm_understanding", "spec_war"],
  "tariff_id": "small-mvp"
}
```

Возвращает стоимость + breakdown по фазам.

---

## 📝 Типы проектов & Personality Modes

### Типы проектов (21 встроенный)

Code, Document, Business, Presentation, Research, Data Analysis, и др.

### Personality Modes

При создании проекта:
```bash
{
  "title": "My MVP",
  "brief": "...",
  "personality_mode": "startup_aggressive"
}
```

Доступные:
- `balanced` — сбалансированный подход
- `conservative_build` — стабильность, тесты
- `startup_aggressive` — быстро, минимум фич
- `cheap_mvp` — минимальные costs
- `enterprise_clean` — production-ready
- `creative_chaos` — экспериментальный
- `academic_formal` — научный стиль

---

## 🐛 Troubleshooting

### Бэкенд не запускается

```bash
cd backend

# Очистить Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Переустановить зависимости
pip install --force-reinstall -r requirements.txt
```

### Фронтенд не собирается

```bash
cd frontend

# Очистить node_modules
rm -rf node_modules package-lock.json
npm install

# Очистить Next.js cache
rm -rf .next
npm run dev
```

### Проект заморозился (stuck on phase)

```bash
# Проверить логи
GET /api/admin/projects/{id}/logs

# Перезапустить фазу
POST /api/admin/projects/{id}/rerun-phase
{
  "phase_key": "build_sprint"
}

# Если не помогло — принудительно завершить
POST /api/admin/projects/{id}/force-package
```

### Ошибка: "no usable real API keys"

- Проверь, что `ENABLE_REAL_MODEL_CALLS=true` в `.env`
- Добавь ключи через админку (`/admin/providers`)
- Перезагрузи бэкенд
- Используй mock-модели для разработки

---

## 📚 Структура кода (бэкенд)

### app/models.py
SQLAlchemy модели:
- `User` — пользователи
- `Project` — проекты
- `Phase` — фазы проекта
- `Artifact` — артефакты
- `Provider` — AI провайдеры
- `Model` — AI модели
- `Tariff` — тарифные пакеты

### app/routers/
API endpoints:
- `auth.py` — регистрация/логин
- `projects.py` — управление проектами
- `artifacts.py` — скачивание артефактов
- `admin.py` — админка

### app/services/
Business logic:
- `project_intake.py` — создание & intake фаза
- `project_swarm.py` — ротация агентов
- `phase_executor.py` — выполнение фаз
- `artifact_builder.py` — сборка артефактов

### app/sandbox/
Безопасное выполнение команд:
- `command_executor.py` — запуск команд
- `whitelist.py` — список разрешенных бинарей
- `secret_scanner.py` — детектирование secrets

### app/prompts/
Директивы для агентов:
- `intake.py` — промпт для intake фазы
- `spec_war.py` — промпт для spec_war
- `build_sprint.py` — промпт для build_sprint
- и т.д.

---

## 🔄 Git workflow

### Ветки

- `main` — production-ready код
- `develop` — базовая ветка для разработки
- `feature/xxx` — новые фичи
- `fix/xxx` — баг-фиксы
- `docs/xxx` — документация

### Commit messages

```
[type]([scope]): brief description

Longer explanation if needed.

Fixes #123
```

Типы: feat, fix, docs, style, refactor, test, chore

### Pull Request

1. Fork или создай feature-ветку
2. Пиши код + тесты
3. Запусти `pytest` и `npm test`
4. Создай PR с описанием
5. Получи review
6. Merge в `develop`, затем в `main`

---

## 📖 Внутренняя документация

**Не для публики!** Следующие документы содержат чувствительную информацию:

- `docs/internal/SYSTEM_CONTEXT.md` — детали архитектуры и роутинга
- `docs/internal/SECURITY_AND_HONEYPOT.md` — security & abuse detection
- `docs/internal/PRODUCTION_RUNBOOK.md` — production deployment & monitoring

Эти docs:
- **Не должны** попадать в публичный UI
- **Не должны** быть в клиентских zip-артефактах
- **Не должны** быть в поддержке или маркетинге

---

## 📞 Контакты & ресурсы

- **API OpenAPI**: http://localhost:8000/docs
- **README**: [README.md](./README.md)
- **Development Commands**: [docs/DEVELOPMENT_COMMANDS.md](./docs/DEVELOPMENT_COMMANDS.md)
- **Архитектура**: [docs/internal/SYSTEM_CONTEXT.md](./docs/internal/SYSTEM_CONTEXT.md)
- **Безопасность**: [docs/internal/SECURITY_AND_HONEYPOT.md](./docs/internal/SECURITY_AND_HONEYPOT.md)
- **Production**: [docs/internal/PRODUCTION_RUNBOOK.md](./docs/internal/PRODUCTION_RUNBOOK.md)

---

## ✨ Полезные советы

### Локальная разработка

- Используй **mock-агенты** для быстрого тестирования
- Демо-данные помогают понять механику: `python scripts/seed_demo.py`
- OpenAPI docs всегда актуален: http://localhost:8000/docs

### Дебаgging

- Логи проекта: `data/projects/{id}/logs/`
- API логи: stdout бэкенда
- Browser DevTools: для фронтенда
- `docker compose logs -f backend` для Docker

### Продакшен

- **Никогда** не коммитьте `.env` с реальными ключами
- Используй `.env.example` как template
- Запускай с `--reload=false` на продакшене
- Настрой мониторинг через `/api/admin/dashboard`

---

Good luck! 🚀
