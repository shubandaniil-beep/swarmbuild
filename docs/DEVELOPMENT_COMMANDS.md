# SwarmBuild — Команды разработки

Полное руководство по запуску, развертыванию и управлению SwarmBuild локально и на продакшене.

---

## Быстрый старт (локально, без Docker)

### Требования
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (опционально, для продакшена)
- Redis (опционально, для продакшена)

### Бэкенд

```bash
# Перейти в директорию бэкенда
cd backend

# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate  # или: .venv\Scripts\activate на Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить в режиме разработки (с автоперезагрузкой)
uvicorn app.main:app --reload --port 8000

# Или просто:
python -m uvicorn app.main:app --reload --port 8000
```

Бэкенд будет доступен по адресу **http://localhost:8000**. 
OpenAPI документация: **http://localhost:8000/docs**

### Фронтенд

```bash
# В отдельном терминале, в директории фронтенда
cd frontend

# Установить зависимости
npm install

# Запустить в режиме разработки
npm run dev
```

Фронтенд будет доступен по адресу **http://localhost:3000**

---

## Окружение и конфигурация

### Локальная разработка (`.env.local` или env vars)

По умолчанию используются **mock-модели** (не требуют API-ключей):

```env
# Опционально: переопределить порт
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Для включения реальных моделей (опционально)
# ENABLE_REAL_MODEL_CALLS=false
```

Локально система работает с SQLite в памяти и не требует PostgreSQL/Redis.

### Production (`.env`)

```bash
# Скопировать пример конфига
cp .env.example .env

# Заполнить критические значения:
ENCRYPTION_SECRET=your-long-random-secret-here
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=strong-password-here

# Для реальных моделей:
ENABLE_REAL_MODEL_CALLS=true
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=...

# Опционально:
DATABASE_URL=postgresql://user:password@localhost/swarmbuild
REDIS_URL=redis://localhost:6379/0
```

---

## Docker Compose (полная стоимость: PostgreSQL + Redis)

```bash
# Скопировать env конфиг
cp .env.example .env

# Собрать и запустить контейнеры
docker compose up --build

# Остановить
docker compose down

# Просмотреть логи
docker compose logs -f backend
docker compose logs -f frontend
```

Фронтенд: **http://localhost:3000**
Бэкенд: **http://localhost:8000**
PostgreSQL: `localhost:5432`
Redis: `localhost:6379`

---

## Инициализация данных

### Seed данные по умолчанию (провайдеры, модели, тарифы)

Автоматически создаются при первом запуске бэкенда. Содержат:
- Mock провайдер (для разработки без ключей)
- OpenAI, Anthropic, Gemini, DeepSeek, Qwen, OpenRouter
- 14 моделей (2 mock, 12 реальных)
- 6 тарифных пакетов (Free Test Run, Fast Build, Small MVP, Standard MVP, Heavy Build, Custom)
- 21 тип проекта (Code, Document, Business, Presentation, Research и др.)
- Системные настройки (credit economy, abuse limits, sandbox rules)

### Демо-проекты (6 проектов во всех режимах)

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/seed_demo.py
```

Создает 6 полностью завершенных проектов в режимах: code, document, business, mixed.

**Демо-вход:**
- Email: `demo@swarmbuild.ai`
- Пароль: `demo12345`

---

## Вход администратора

### Первый запуск (автоматический)

При первом запуске бэкенда создается admin-аккаунт:

```
Email: founder@swarmbuild.ai (или значение ADMIN_EMAIL из .env)
Пароль: значение ADMIN_PASSWORD из .env, или auto-generated в backend/.founder-password
```

Прочитайте пароль из файла:
```bash
cat backend/.founder-password
```

### Вход в админку

1. Перейти на http://localhost:3000/admin-login
2. Ввести email и пароль admin-аккаунта
3. После успешного входа доступны разделы:
   - `/admin/providers` — управление провайдерами и API-ключами
   - `/admin/models` — регистрация моделей
   - `/admin/tariffs` — тарифные пакеты
   - `/admin/projects` — полная история проектов и логи
   - `/admin/dashboard` — статистика и мониторинг

---

## Управление провайдерами и ключами

### В админке (`/admin/providers`)

1. **Добавить провайдер:**
   - Выбрать тип (openai, anthropic, gemini, deepseek, qwen, openrouter)
   - Указать имя, base URL, первый API-ключ
   - Нажать "Создать"

2. **Добавить API-ключи (bulk):**
   - Открыть провайдер в списке
   - Нажать "Показать пул ключей"
   - Вставить ключи (разделены пробелом, запятой или переносом строки)
   - Нажать "Добавить ключи"

3. **Тестировать ключи:**
   - Нажать кнопку "Тест" рядом с провайдером
   - Система проверит каждый ключ и покажет статус

4. **Включить/отключить ключ:**
   - Открыть пул ключей
   - Нажать иконку вкл/выкл для каждого ключа

### Из .env (initial seed только)

Ключи из .env используются только при первом запуске. После этого управление ведется через админку.

---

## Основные API endpoints

### Проекты

```http
POST   /api/projects                           # Создать проект
GET    /api/projects                           # Список проектов пользователя
GET    /api/projects/{id}                      # Статус + бюджет проекта
GET    /api/projects/{id}/phases               # Фазы проекта
GET    /api/projects/{id}/events               # События и логи
GET    /api/projects/{id}/artifacts            # Артефакты
GET    /api/projects/{id}/artifacts/{aid}      # Содержимое артефакта
GET    /api/projects/{id}/artifacts/{aid}/download  # Скачать артефакт
GET    /api/projects/{id}/download             # Скачать project.zip (все артефакты)
POST   /api/projects/{id}/start                # Запустить рой
POST   /api/projects/{id}/continue             # Продолжить после паузы
```

### Аутентификация

```http
POST   /api/auth/register                      # Зарегистрироваться (+ device fingerprint)
POST   /api/auth/login                         # Войти
POST   /api/auth/logout                        # Выйти (invalidate token)
GET    /api/auth/me                            # Текущий пользователь
POST   /api/auth/change-password               # Изменить пароль
```

### Админка

```http
GET    /api/admin/dashboard                    # Статистика и мониторинг
GET    /api/admin/providers                    # Список провайдеров
POST   /api/admin/providers                    # Создать провайдер
PUT    /api/admin/providers/{id}               # Обновить провайдер
DELETE /api/admin/providers/{id}               # Удалить провайдер
GET    /api/admin/providers/{id}/keys          # Пул ключей провайдера
POST   /api/admin/providers/{id}/keys          # Добавить ключи
POST   /api/admin/providers/{id}/keys/{kid}/toggle  # Вкл/выкл ключ
DELETE /api/admin/providers/{id}/keys/{kid}    # Удалить ключ
POST   /api/admin/providers/{id}/test          # Тестировать ключи

GET    /api/admin/models                       # Список моделей
POST   /api/admin/models                       # Создать модель
PUT    /api/admin/models/{id}                  # Обновить модель
DELETE /api/admin/models/{id}                  # Удалить модель

GET    /api/admin/tariffs                      # Тарифные пакеты
POST   /api/admin/tariffs                      # Создать тариф
PUT    /api/admin/tariffs/{id}                 # Обновить тариф
DELETE /api/admin/tariffs/{id}                 # Удалить тариф

GET    /api/admin/project-types                # Типы проектов
GET    /api/admin/projects/{id}/logs           # Логи проекта
POST   /api/admin/projects/{id}/rerun-phase    # Перезапустить фазу
POST   /api/admin/projects/{id}/force-package  # Принудительно собрать результат

GET    /api/admin/runtime                      # Статус runtime (real calls, mock mode, errors)
POST   /api/settings                           # Обновить системные настройки
```

### Публичное API (для CLI/интеграций)

```http
POST   /api/projects/estimate                  # Предварительная оценка credits
GET    /api/projects/personality-modes         # Доступные personality modes
GET    /api/projects/project-types             # Типы проектов
```

---

## Команды тестирования

### Запуск тестов бэкенда

```bash
cd backend

# Все тесты
pytest

# Тесты с покрытием
pytest --cov=app --cov-report=html

# Конкретный файл
pytest tests/test_auth.py

# Конкретный тест
pytest tests/test_auth.py::test_register

# С verbose выводом
pytest -v

# С вывод stdout
pytest -s
```

### Запуск тестов фронтенда

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

## Структура workspace проекта

При создании проекта создается директория:

```
data/projects/{project_id}/
├── brief.md                    # Исходное описание проекта
├── budget_state.json           # Состояние бюджета и credits
├── phase_plan.json             # План фаз для этого проекта
├── swarm_state.json            # История вызовов агентов
├── spec/                       # Спецификация (от фазы spec_war)
│   └── technical_spec.md
├── architecture/               # Архитектура (от фазы architecture_battle)
│   ├── architecture.md
│   └── diagrams/
├── repo/                       # Исходный код (от фазы build_sprint)
│   ├── README.md
│   ├── src/
│   ├── package.json (или requirements.txt)
│   └── ...
├── reviews/                    # Рецензии и замечания
│   └── build_sprint.md
├── artifacts/                  # Финальные артефакты для скачивания
│   ├── mvp/
│   ├── docs/
│   ├── business_plan.md
│   ├── pitch_outline.md
│   ├── limitations.md
│   └── security-report.md
└── logs/
    ├── events.jsonl            # Все события проекта (1 JSON-объект per line)
    ├── agent-calls.jsonl       # История вызовов агентов
    ├── command-runs.jsonl      # История sandbox команд
    └── system.log              # Логи системы
```

---

## Фазы проекта

```
intake
  ↓
swarm_understanding
  ↓
spec_war
  ↓
architecture_battle
  ↓
build_sprint
  ↓
review_stop
  ↓
repair_sprint (опционально)
  ↓
final_audit
  ↓
packaging
```

Каждая фаза:
- Имеет фиксированную стоимость в credits (см. credit_pricing.py)
- Выполняется ротирующим агентом из swarm
- Создает события в logs/events.jsonl
- Может быть перезапущена через `/api/admin/projects/{id}/rerun-phase`

---

## Кредитная экономика

### Основные понятия

- **1 credit = $0.01 USD** (настраивается в settings)
- **Фиксированная стоимость per фаза** (не variable по времени)
- **Metered per-phase burn** — credits списываются за каждую завершенную фазу
- **Stubborn agent eats margin** — если агент retry слишком много, margin платформы уменьшается, но баланс пользователя не страдает

###估算 (Pre-run estimation)

```http
POST /api/projects/estimate
{
  "phase_keys": ["intake", "swarm_understanding", "spec_war", "architecture_battle", "build_sprint"],
  "tariff_id": "small-mvp"
}
```

Возвращает:
```json
{
  "credits_estimate": 1200,
  "credits_min": 1100,
  "credits_max": 1400,
  "usd_equivalent": "12.00",
  "breakdown": {
    "intake": 150,
    "swarm_understanding": 180,
    ...
  }
}
```

### Тарифные пакеты

| Название | Цена | Credits | Бонус | Свопы | Фазы | Описание |
|---|---|---|---|---|---|---|
| Free Test Run | $1 | 100 | 0% | 3 | 5 | Тестовый запуск |
| Fast Build | $20 | 2,000 | 0% | 3 | 5 | Простые проекты |
| Small MVP | $40 | 4,400 | 10% | 4 | 8 | MVP + документация |
| Standard MVP | $100 | 12,000 | 20% | 6 | 9 | Полный pipeline |
| Heavy Build | $200 | 26,000 | 30% | 8 | 9 | +repair+audit |
| Custom | $500 | 70,000 | 40% | 8 | 9 | Крупные проекты |

---

## Modes и личностные стили (Personality Modes)

При создании проекта можно выбрать стиль разработки:

```http
POST /api/projects
{
  "title": "My MVP",
  "brief": "...",
  "personality_mode": "startup_aggressive"
}
```

Доступные modes:
- `balanced` — balanced approach
- `conservative_build` — emphasize stability, error handling, tests
- `startup_aggressive` — move fast, minimal features, launch ASAP
- `cheap_mvp` — minimal cost, free models only, cutting corners
- `enterprise_clean` — production-ready, full docs, compliance
- `creative_chaos` — experimental, unconventional approaches
- `academic_formal` — research-oriented, citations, rigor

Каждый mode влияет на директивы, передаваемые агентам (stack complexity, scope, docs level, tone).

---

## Безопасность и мониторинг

### Secret scanning

Система автоматически сканирует артефакты перед скачиванием:
- Обнаруживает API-ключи (Anthropic, OpenAI, AWS, Slack, JWT, DB URLs и др.)
- Redacts секреты in-place или блокирует скачивание (зависит от настройки)
- Файлы `.env` с секретами конвертируются в `.env.example`

### Prompt-injection detection

При создании проекта brief сканируется на подозрительные паттерны:
- `ignore instructions`, `reveal prompt`, `exfiltrate secrets`
- `read environment`, `system prompt is`
- Risk level: low/medium/high

### Sandbox ограничения

При выполнении команд:
- Только whitelist-разрешенные бинарии (python, node, npm, git и др.)
- Timeout 30 сек по умолчанию
- Workspace confinement (no `..`, `~`, абсолютные пути)
- Блокированные команды: `rm -rf`, `chmod`, `sudo`, `mkfs`, `/etc/passwd`
- Output redaction (secrets scrubbed)

### Audit logging

Все операции админа логируются:
- Создание/обновление провайдеров
- Добавление/удаление ключей
- Создание моделей
- Запуск проектов
- Скачивание артефактов

Просмотр в `/api/admin/projects/{id}/logs`

---

## Deployment

### Системные требования

- **CPU**: 2+ cores
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 20GB+ (для workspace проектов)
- **Database**: PostgreSQL 14+ с переменной окружения `DATABASE_URL`
- **Cache**: Redis (опционально, если используется Celery)

### Environment variables (Production)

```env
# === CRITICAL ===
ENCRYPTION_SECRET=your-long-random-secret-min-32-chars
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=strong-password

# === DATABASE ===
DATABASE_URL=postgresql://user:password@localhost:5432/swarmbuild

# === CACHE (опционально) ===
REDIS_URL=redis://localhost:6379/0

# === API KEYS ===
ENABLE_REAL_MODEL_CALLS=true
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=...

# === CORS & SECURITY ===
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=strict

# === LOGGING ===
LOG_LEVEL=info
```

### Docker Compose production

```bash
# Собрать и запустить
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Масштабировать бэкенд на 3 instance
docker compose up -d --scale backend=3

# Просмотреть логи
docker compose logs -f backend
```

### Kubernetes

Для production используйте Helm chart (см. `k8s/helm/`):

```bash
helm install swarmbuild ./k8s/helm \
  --set apiKey.anthropic="sk-ant-..." \
  --set database.url="postgresql://..." \
  --set adminPassword="..."
```

---

## Troubleshooting

### Бэкенд не запускается

```bash
# Очистить cache Python
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Переустановить зависимости
pip install --force-reinstall -r requirements.txt

# Проверить PostgreSQL (если используется)
psql -U postgres -h localhost -d swarmbuild -c "SELECT 1"
```

### Фронтенд не собирается

```bash
# Очистить node_modules
rm -rf node_modules package-lock.json
npm install

# Очистить Next.js cache
rm -rf .next
npm run dev
```

### Ключи провайдера не работают

1. Проверить ключи на админке (`/admin/providers`)
2. Нажать "Тест" — система проверит каждый ключ
3. Проверить логи: `/api/admin/projects/{id}/logs`
4. Если ключ заблокирован (429, 401), переключиться на другой ключ

### Проект заморозился (stuck on phase)

```bash
# Проверить статус в админке
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

- Убедиться, что `ENABLE_REAL_MODEL_CALLS=true` в .env
- Проверить, что добавлены ключи и они активны
- Перезагрузить бэкенд
- Использовать mock-модели в режиме разработки

---

## Полезные скрипты

### Экспорт проекта

```bash
cd backend
python -c "
from app.services.project_intake import workspace_path
from pathlib import Path
import shutil

project_id = 'YOUR_PROJECT_ID'
src = Path('data/projects') / project_id
dst = Path('/tmp') / f'{project_id}.zip'

if src.exists():
    shutil.make_archive(str(dst.with_suffix('')), 'zip', src)
    print(f'Exported to {dst}')
"
```

### Очистить старые проекты

```bash
cd backend
python -c "
from pathlib import Path
from datetime import datetime, timedelta
import shutil

projects_dir = Path('data/projects')
cutoff = datetime.now() - timedelta(days=30)

for project_dir in projects_dir.iterdir():
    if project_dir.stat().st_mtime < cutoff.timestamp():
        shutil.rmtree(project_dir)
        print(f'Deleted {project_dir.name}')
"
```

### Сброс админ-пароля

```bash
cd backend
python << 'EOF'
from app.lib.security import hash_password
from app.models import User, Base
from app.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(str(settings.DATABASE_URL))
Session = sessionmaker(bind=engine)
db = Session()

admin = db.query(User).filter(User.role == "admin").first()
if admin:
    new_password = "newpassword123"
    admin.password_hash = hash_password(new_password)
    db.commit()
    print(f"✓ Reset admin password to: {new_password}")
else:
    print("✗ No admin user found")
EOF
```

---

## Дополнительные ресурсы

- **API OpenAPI docs:** http://localhost:8000/docs
- **Архитектура:** [SYSTEM_CONTEXT.md](./internal/SYSTEM_CONTEXT.md)
- **Security:** [SECURITY_AND_HONEYPOT.md](./internal/SECURITY_AND_HONEYPOT.md)
- **Production Runbook:** [PRODUCTION_RUNBOOK.md](./internal/PRODUCTION_RUNBOOK.md)
- **Фазы и роли агентов:** backend/app/prompts/
