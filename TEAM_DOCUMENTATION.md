# SwarmBuild — Полная документация для команды разработчиков

**Единый справочник по всему, что нужно знать при работе с SwarmBuild**

---

## 📋 Оглавление

1. [Быстрый старт](#быстрый-старт)
2. [Что такое SwarmBuild](#что-такое-swarmbuild)
3. [Архитектура](#архитектура)
4. [Структура проекта](#структура-проекта)
5. [API endpoints](#api-endpoints)
6. [Работа с кодом (Python)](#работа-с-кодом-python)
7. [Работа с кодом (JavaScript/React)](#работа-с-кодом-javascriptreact)
8. [Тестирование](#тестирование)
9. [Безопасность](#безопасность)
10. [Git workflow](#git-workflow)
11. [Troubleshooting](#troubleshooting)
12. [Полезные команды](#полезные-команды)

---

## 🚀 Быстрый старт

### За 5 минут

```bash
# 1. Подготовка бэкенда (terminal 1)
cd backend
python3 -m venv .venv
source .venv/bin/activate  # MacOS/Linux
# или: .venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
# 2. Подготовка фронтенда (terminal 2)
cd frontend
npm install
npm run dev
```

```
3. Открыть браузер
http://localhost:3000 → фронтенд
http://localhost:8000/docs → API docs
http://localhost:3000/admin-login → админка
```

### Логины

| Что | Email | Пароль |
|-----|-------|--------|
| **Админка** | founder@swarmbuild.ai | смотри `backend/.founder-password` |
| **Demo аккаунт** | demo@swarmbuild.ai | demo12345 |

### Демо-данные (опционально)

```bash
cd backend
PYTHONPATH=. .venv/bin/python scripts/seed_demo.py
```

Создаст 6 готовых проектов.

---

## 📖 Что такое SwarmBuild

**SwarmBuild** — платформа для создания проектов с помощью ротирующихся AI-агентов.

### Как это работает

```
Пользователь загружает идею + выбирает бюджет
              ↓
        Создается Project
              ↓
      Инициируется Phase Pipeline
              ↓
    Ротирующийся Swarm агентов
       выполняет разные фазы
              ↓
  Генерируются артефакты (код, спека, docs)
              ↓
    Собирается project.zip на скачивание
```

### Основные концепции

**Project** — задача пользователя (создать MVP, написать документацию, etc)

**Phases** — этапы выполнения:
- `intake` (150 cr) → сбор информации
- `swarm_understanding` (180 cr) → понимание требований
- `spec_war` (250 cr) → написание спеки
- `architecture_battle` (280 cr) → проектирование архитектуры
- `build_sprint` (400 cr) → написание кода
- `review_stop` (150 cr) → ревью
- `repair_sprint` (300 cr) → исправления (если бюджет)
- `final_audit` (100 cr) → финальная проверка
- `packaging` (50 cr) → сборка артефактов

**Swarm** — набор AI-агентов (моделей) с ротирующимися ролями:
- **Lead** — координирует фазу
- **Critic** — проверяет качество
- **Builder** — пишет код/спеку
- **Reviewer** — рецензирует
- **Judge** — выносит финальное решение

**Ротация правила:**
- Модель не может быть lead более 2 фаз подряд
- Judge текущей фазы ≠ Lead следующей фазы
- Роли ротируются каждую фазу

**Credits** — внутренняя валюта
- 1 credit = $0.01 USD
- Фиксированная стоимость per фаза
- Если 85% расходовано → saving mode
- Если 100% расходовано → partial_ready (возвращаем имеющиеся результаты)

**Тарифы:**

| Пакет | Цена | Credits | Фазы |
|-------|------|---------|------|
| Free Test Run | $1 | 100 | 5 |
| Fast Build | $20 | 2,000 | 5 |
| Small MVP | $40 | 4,400 | 8 |
| Standard MVP | $100 | 12,000 | 9 |
| Heavy Build | $200 | 26,000 | 9 |
| Custom | $500 | 70,000 | 9 |

---

## 🏛️ Архитектура

### High-level диаграмма

```
┌─────────────────────────────────────────────┐
│       Frontend (React/Next.js)              │
│  - Project creation                         │
│  - Admin dashboard                          │
│  - Progress tracking                        │
└──────────────────┬──────────────────────────┘
                   │ HTTP/REST
┌──────────────────▼──────────────────────────┐
│        Backend (FastAPI/Python)             │
│  ┌─────────────────────────────────────┐   │
│  │  Routers: auth, projects, admin     │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Services: intake, swarm, phases    │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Sandbox: command execution         │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  LLM routing (OpenAI, Anthropic,    │   │
│  │   Gemini, DeepSeek, Mock)           │   │
│  └─────────────────────────────────────┘   │
│  ┌─────────────────────────────────────┐   │
│  │  Database (SQLAlchemy + SQLite)     │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────────┐
│  File storage                               │
│  - data/projects/{id}/     (workspaces)     │
│  - PostgreSQL (production)                  │
│  - Redis (optional, caching)                │
└─────────────────────────────────────────────┘
```

### Поток выполнения проекта

```
1. POST /api/projects
   ↓
   Валидация brief (prompt injection detection)
   ↓
   Создание Project в БД
   ↓
   Создание workspace: data/projects/{id}/

2. POST /api/projects/{id}/start
   ↓
   Проверка бюджета
   ↓
   Phase 1: Intake
   ├─ Выбрать lead агента
   ├─ Вызвать LLM с директивой
   ├─ Выполнить команды в sandbox
   ├─ Собрать артефакты
   ├─ Judge проверяет качество
   ├─ Залогировать в events.jsonl
   ├─ Списать credits
   └─ Ротировать swarm roles
   ↓
   Phase 2: Swarm Understanding
   ├─ ... (то же самое)
   └─ ...
   ↓
   ... (все остальные фазы)
   ↓
   Packaging
   ├─ Сканировать артефакты на secrets
   ├─ Собрать project.zip
   └─ Отметить как completed

3. GET /api/projects/{id}/download
   ↓
   Скачать project.zip (код + документацию)
```

### Логирование проекта

Все события логируются в `data/projects/{id}/logs/`:

```json
events.jsonl
{
  "timestamp": "2025-01-15T10:30:45Z",
  "phase": "spec_war",
  "event_type": "phase_started",
  "agent": "claude-3-sonnet",
  "role": "lead"
}

agent-calls.jsonl
{
  "timestamp": "2025-01-15T10:35:12Z",
  "agent": "claude-3-sonnet",
  "phase": "spec_war",
  "prompt_tokens": 1200,
  "completion_tokens": 3400,
  "cost_credits": 25
}

command-runs.jsonl
{
  "timestamp": "2025-01-15T10:40:00Z",
  "command": "npm install",
  "exit_code": 0,
  "stdout": "added 245 packages",
  "duration_ms": 8500
}
```

---

## 📁 Структура проекта

### Директории

```
swarmbuild/
├── backend/                          # Python/FastAPI
│   ├── app/
│   │   ├── main.py                  # Entry point
│   │   ├── config.py                # Settings & env
│   │   ├── models.py                # SQLAlchemy модели
│   │   ├── schemas.py               # Pydantic схемы
│   │   ├── routers/
│   │   │   ├── auth.py             # Аутентификация
│   │   │   ├── projects.py         # Проекты
│   │   │   ├── artifacts.py        # Артефакты
│   │   │   └── admin.py            # Админка
│   │   ├── services/
│   │   │   ├── project_intake.py   # Создание проекта
│   │   │   ├── project_swarm.py    # Ротация агентов
│   │   │   ├── phase_executor.py   # Выполнение фаз
│   │   │   ├── artifact_builder.py # Сборка артефактов
│   │   │   └── model_router.py     # Маршрутизация LLM
│   │   ├── lib/
│   │   │   ├── security.py         # Шифрование
│   │   │   ├── secrets.py          # Сканирование secrets
│   │   │   └── logging.py          # Логирование
│   │   ├── prompts/                # Директивы для агентов
│   │   │   ├── intake.py
│   │   │   ├── spec_war.py
│   │   │   └── ...
│   │   └── sandbox/                # Безопасное выполнение
│   │       ├── command_executor.py
│   │       └── whitelist.py
│   ├── tests/                      # Pytest тесты
│   ├── requirements.txt
│   ├── .env.example
│   └── .venv/                      # Виртуальное окружение
│
├── frontend/                        # React/Next.js
│   ├── app/
│   │   ├── page.tsx               # Home
│   │   ├── layout.tsx             # Root layout
│   │   ├── admin/
│   │   │   ├── page.tsx          # Admin dashboard
│   │   │   ├── providers/        # Manage providers
│   │   │   └── models/           # Manage models
│   │   └── api/                  # API routes
│   ├── components/                # React компоненты
│   ├── lib/
│   │   ├── api.ts               # API client
│   │   ├── types.ts             # TypeScript типы
│   │   └── utils.ts             # Утилиты
│   ├── public/                   # Статика
│   ├── package.json
│   └── tsconfig.json
│
├── docs/
│   ├── DEVELOPMENT_COMMANDS.md  # Все команды
│   └── internal/                # Внутренние docs (secret!)
│       ├── SYSTEM_CONTEXT.md
│       ├── SECURITY_AND_HONEYPOT.md
│       └── PRODUCTION_RUNBOOK.md
│
├── docker-compose.yml
├── README.md
└── TEAM_DOCUMENTATION.md        # Этот файл
```

### Workspace проекта

Когда создается проект, создается директория:

```
data/projects/{project_id}/
├── brief.md                    # Исходное описание
├── budget_state.json           # Состояние бюджета
│   {
│     "initial_credits": 1000,
│     "spent": 250,
│     "available": 750,
│     "phases_completed": 2,
│     "saving_mode": false
│   }
├── phase_plan.json             # План фаз для этого проекта
│   [
│     {"phase": "intake", "cost": 150},
│     {"phase": "swarm_understanding", "cost": 180},
│     ...
│   ]
├── swarm_state.json            # История вызовов агентов
│   {
│     "agents": [
│       {"model": "gpt-4", "current_role": "lead"},
│       {"model": "claude-opus", "current_role": "critic"},
│       ...
│     ],
│     "phase_history": {
│       "intake": {"lead": "gpt-4"},
│       "swarm_understanding": {"lead": "claude-opus"}
│     }
│   }
├── spec/                       # Техническая спецификация
│   └── technical_spec.md
├── architecture/               # Архитектура
│   ├── architecture.md
│   └── diagrams/
├── repo/                       # Исходный код
│   ├── README.md
│   ├── src/
│   ├── package.json
│   └── ...
├── reviews/                    # Рецензии
│   └── build_sprint.md
├── artifacts/                  # Финальные артефакты
│   ├── mvp/
│   │   ├── code.zip
│   │   ├── setup.md
│   │   └── running.md
│   ├── docs/
│   │   ├── technical_spec.md
│   │   └── architecture.md
│   ├── business_plan.md
│   ├── pitch_outline.md
│   ├── limitations.md
│   └── security-report.md
└── logs/
    ├── events.jsonl            # Все события (1 JSON per line)
    ├── agent-calls.jsonl       # История LLM вызовов
    ├── command-runs.jsonl      # История shell команд
    └── system.log              # Логи системы
```

---

## 📡 API endpoints

### Проекты

```http
POST   /api/projects                    # Создать проект
GET    /api/projects                    # Мои проекты
GET    /api/projects/{id}               # Статус + бюджет
GET    /api/projects/{id}/phases        # Фазы проекта
GET    /api/projects/{id}/events        # События/логи
GET    /api/projects/{id}/artifacts     # Артефакты
GET    /api/projects/{id}/artifacts/{aid}       # Содержимое артефакта
GET    /api/projects/{id}/artifacts/{aid}/download  # Скачать артефакт
GET    /api/projects/{id}/download      # Скачать project.zip
POST   /api/projects/{id}/start         # Запустить рой
POST   /api/projects/{id}/continue      # Продолжить после паузы
POST   /api/projects/estimate           # Оценка стоимости
```

### Аутентификация

```http
POST   /api/auth/register               # Регистрация
POST   /api/auth/login                  # Логин
POST   /api/auth/logout                 # Логаут
GET    /api/auth/me                     # Текущий пользователь
POST   /api/auth/change-password        # Изменить пароль
```

### Админка

```http
GET    /api/admin/dashboard             # Статистика
GET    /api/admin/providers             # Список провайдеров
POST   /api/admin/providers             # Создать провайдера
PUT    /api/admin/providers/{id}        # Обновить провайдера
GET    /api/admin/providers/{id}/keys   # Пул ключей
POST   /api/admin/providers/{id}/keys   # Добавить ключи
POST   /api/admin/providers/{id}/test   # Тестировать ключи
DELETE /api/admin/providers/{id}/keys/{kid}    # Удалить ключ

GET    /api/admin/models                # Модели
POST   /api/admin/models                # Создать модель
PUT    /api/admin/models/{id}           # Обновить модель

GET    /api/admin/tariffs               # Тарифы
GET    /api/admin/projects/{id}/logs    # Логи проекта
POST   /api/admin/projects/{id}/rerun-phase   # Перезапустить фазу
POST   /api/admin/projects/{id}/force-package # Завершить проект
```

### Публичное API

```http
GET    /api/projects/personality-modes      # Доступные modes
GET    /api/projects/project-types          # Типы проектов
```

### OpenAPI документация

http://localhost:8000/docs (Swagger)  
http://localhost:8000/redoc (ReDoc)

---

## 💻 Работа с кодом (Python)

### Структура бэкенда

**Следуй этой структуре при создании нового функционала:**

```
app/routers/new_feature.py
  → обработчики HTTP запросов
  → валидация входных данных
  → вызов сервисов

app/services/new_feature.py
  → бизнес-логика
  → работа с БД
  → интеграция с внешними системами
  → логирование

app/models.py
  → SQLAlchemy модели (если нужны новые таблицы)

app/schemas.py
  → Pydantic schemas для входных/выходных данных

tests/test_new_feature.py
  → юнит-тесты
  → интеграционные тесты
```

### Python conventions

```python
# Classes: PascalCase
class ProjectManager:
    def __init__(self):
        pass

# Functions: snake_case
def execute_phase(project_id: UUID) -> Phase:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_COMMAND_TIMEOUT = 30
ALLOWED_COMMANDS = {"python", "npm", "git"}

# Private: _leading_underscore
def _validate_brief(brief: str) -> bool:
    pass

# Type hints: ОБЯЗАТЕЛЬНО!
from typing import Optional, Dict, List
from uuid import UUID

def create_project(
    user_id: UUID,
    title: str,
    brief: str,
    personality_mode: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new project.
    
    Args:
        user_id: UUID of user
        title: Project title
        brief: Project description
        personality_mode: Optional mode
    
    Returns:
        Project dict
    """
    pass
```

### Логирование

```python
import logging

logger = logging.getLogger(__name__)

# ✅ Хорошо
logger.info(f"Project {project_id} started")
logger.warning(f"Low credits: {remaining}")
logger.error(f"Failed to call model", exc_info=True)

# ❌ Плохо (не логируй secrets!)
logger.info(f"API key: {api_key}")  # DANGER!

# ✅ Правильно
logger.info(f"API key: {api_key[:4]}...***")
```

### Обработка ошибок

```python
from fastapi import HTTPException, status

class ProjectNotFoundError(Exception):
    """Custom exception."""
    pass

@router.get("/projects/{project_id}")
async def get_project(project_id: UUID):
    try:
        project = db.query(Project).filter_by(id=project_id).first()
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")
        return project
    except ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

### Async/Await

```python
from fastapi import BackgroundTasks

@router.post("/projects/{id}/start")
async def start_project(project_id: UUID, bg_tasks: BackgroundTasks):
    # Быстро вернуть ответ
    bg_tasks.add_task(execute_project_phases, project_id)
    return {"status": "running"}

async def execute_project_phases(project_id: UUID):
    project = await get_project_async(project_id)
    for phase in project.phases:
        result = await execute_phase(project_id, phase.key)
        await log_event(project_id, "phase_completed", result)
```

---

## 💻 Работа с кодом (JavaScript/React)

### Структура фронтенда

```
app/
├── page.tsx              # Home page
├── layout.tsx            # Root layout
├── admin/
│   ├── layout.tsx
│   ├── page.tsx         # Dashboard
│   ├── providers/       # Manage providers
│   └── models/          # Manage models
└── api/                 # API routes (if any)

components/
├── ProjectForm.tsx      # Reusable components
├── PhaseProgressBar.tsx
└── AdminTable.tsx

lib/
├── api.ts              # API client
├── types.ts            # Types
└── utils.ts            # Utilities
```

### TypeScript conventions

```typescript
// Components: PascalCase
function ProjectForm() {}        // ProjectForm.tsx
function AdminProviders() {}     // AdminProviders.tsx

// Functions: camelCase
const fetchProjects = async () => {}
const handleSubmit = (data: ProjectFormData) => {}

// Constants: UPPER_SNAKE_CASE
const API_BASE_URL = "http://localhost:8000"
const MAX_RETRIES = 3

// Types: PascalCase
interface Project {
  id: string
  title: string
  status: ProjectState
}

type ProjectState = "created" | "running" | "completed" | "failed"
```

### API Client

```typescript
// lib/api.ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface ApiError {
  detail: string
  status: number
}

export async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${getToken()}`,
      ...options?.headers
    },
    ...options
  })
  
  if (!response.ok) {
    const error: ApiError = await response.json()
    throw new Error(error.detail || "API Error")
  }
  
  return response.json()
}

// Usage
const projects = await fetchAPI<Project[]>("/api/projects")
```

### Forms with React Hook Form + Zod

```typescript
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"

const projectSchema = z.object({
  title: z.string().min(1, "Title required"),
  brief: z.string().min(10, "Brief must be 10+ chars"),
  tariff_id: z.string().min(1, "Select a tariff")
})

type ProjectFormData = z.infer<typeof projectSchema>

export function CreateProjectForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<ProjectFormData>({
    resolver: zodResolver(projectSchema)
  })
  
  const onSubmit = async (data: ProjectFormData) => {
    try {
      const project = await fetchAPI<Project>("/api/projects", {
        method: "POST",
        body: JSON.stringify(data)
      })
      console.log("Success:", project)
    } catch (error) {
      console.error("Error:", error)
    }
  }
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register("title")} placeholder="Project title" />
      {errors.title && <span>{errors.title.message}</span>}
      
      <textarea {...register("brief")} placeholder="Description" />
      {errors.brief && <span>{errors.brief.message}</span>}
      
      <button type="submit">Create Project</button>
    </form>
  )
}
```

---

## 🧪 Тестирование

### Backend (pytest)

```bash
# Все тесты
cd backend && pytest

# С покрытием
pytest --cov=app --cov-report=html

# Конкретный файл
pytest tests/test_auth.py

# Конкретный тест
pytest tests/test_auth.py::test_register

# Verbose
pytest -v

# С выводом print
pytest -s
```

**Пример теста:**

```python
# tests/test_projects.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def sample_user(db):
    user = User(email="test@example.com", role="user")
    db.add(user)
    db.commit()
    return user

def test_create_project(sample_user):
    """Test project creation."""
    response = client.post("/api/projects", json={
        "title": "Test MVP",
        "brief": "A test project",
        "tariff_id": "free-test-run"
    }, headers={"Authorization": f"Bearer {sample_user.token}"})
    
    assert response.status_code == 201
    assert response.json()["title"] == "Test MVP"

def test_create_project_missing_brief():
    """Test validation: brief required."""
    response = client.post("/api/projects", json={
        "title": "Test MVP"
        # missing brief
    })
    
    assert response.status_code == 422
```

### Frontend (Jest/React Testing Library)

```bash
cd frontend

# Все тесты
npm test

# Watch mode
npm test -- --watch

# С покрытием
npm test -- --coverage
```

**Пример теста:**

```typescript
import { render, screen, fireEvent } from "@testing-library/react"
import { CreateProjectForm } from "@/components/CreateProjectForm"

test("user can create a project", async () => {
  render(<CreateProjectForm />)
  
  fireEvent.change(screen.getByLabelText(/title/i), {
    target: { value: "My App" }
  })
  fireEvent.change(screen.getByLabelText(/brief/i), {
    target: { value: "A cool application" }
  })
  fireEvent.click(screen.getByRole("button", { name: /create/i }))
  
  await screen.findByText(/project created/i)
})
```

---

## 🔐 Безопасность

### Проверка перед коммитом

- ✅ Нет `.env` файлов с реальными ключами
- ✅ Нет hardcoded secrets в коде
- ✅ Все user input валидирован
- ✅ API-ключи в БД шифруются (AES-GCM)
- ✅ Secrets не логируются
- ✅ SQL injection protection (ORM + parameterized queries)

### Шифрование API ключей

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, base64

def encrypt_key(api_key: str, secret: str) -> str:
    cipher = AESGCM(secret.encode()[:32].ljust(32, b'0'))
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, api_key.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt_key(encrypted: str, secret: str) -> str:
    data = base64.b64decode(encrypted)
    nonce, ciphertext = data[:12], data[12:]
    cipher = AESGCM(secret.encode()[:32].ljust(32, b'0'))
    return cipher.decrypt(nonce, ciphertext, None).decode()
```

### Sandbox изоляция

```python
# Только разрешенные бинарии
ALLOWED_COMMANDS = {
    "python", "python3", "node", "npm", "git",
    "cat", "ls", "mkdir", "cd"
}

# Запретить опасные команды
FORBIDDEN_COMMANDS = ["rm -rf", "chmod", "sudo", "mkfs"]

# Конфайн в workspace
os.chdir(f"data/projects/{project_id}/repo")
# Команда: git init
# Реально: cd data/projects/{id}/repo && git init
```

### Secret scanning

```python
import re

SECRET_PATTERNS = {
    "api_key": r"api[_-]?key['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9\-_]+)['\"]?",
    "db_url": r"(postgres|mysql|mongodb)[+a-z]*://[^\s]+",
    "aws": r"AKIA[0-9A-Z]{16}",
    "jwt": r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
}

def scan_for_secrets(text: str) -> List[Dict]:
    findings = []
    for secret_type, pattern in SECRET_PATTERNS.items():
        matches = re.finditer(pattern, text)
        for match in matches:
            findings.append({
                "type": secret_type,
                "value": match.group(0),
                "position": match.start()
            })
    return findings
```

---

## 🔄 Git workflow

### Commit messages

**Format:**
```
[type]([scope]): brief description (max 50 chars)

Longer explanation if needed (max 72 chars per line)
- Point 1
- Point 2

Fixes #123
Relates to #456
```

**Types:**
- `feat` — новая фича
- `fix` — баг-фикс
- `docs` — документация
- `style` — форматирование
- `refactor` — рефакторинг
- `test` — тесты
- `chore` — конфиг, зависимости

**Примеры:**

```
feat(projects): add personality mode selection

Allow users to choose a development style (balanced, startup_aggressive, etc)
that affects how agents approach the project.

- Add personality_mode field to Project model
- Update project creation API
- Implement mode-based agent directives

Fixes #42

---

fix(sandbox): prevent directory traversal attacks

Validate all workspace paths before command execution to prevent
users from accessing files outside project directory.

---

docs: update architecture overview
```

### Branches

```bash
git checkout -b feature/user-authentication
git checkout -b fix/sandbox-timeout
git checkout -b docs/api-documentation
git checkout -b refactor/project-services
```

### Pull Request шаблон

```markdown
## Summary
Brief description of what this PR does

## Changes
- Added authentication to API
- Updated user model with new fields
- Fixed sandbox timeout issue

## Testing
Describe how to test these changes

## Checklist
- [x] Tests written/updated
- [x] Documentation updated
- [x] No breaking changes
- [x] Code follows standards
```

---

## 🚨 Troubleshooting

### Backend не запускается

```bash
# Очистить Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Переустановить зависимости
pip install --force-reinstall -r requirements.txt

# Проверить PostgreSQL
psql -U postgres -h localhost -d swarmbuild -c "SELECT 1"
```

### "ModuleNotFoundError: No module named 'app'"

```bash
cd backend
export PYTHONPATH=$PWD
uvicorn app.main:app --reload
```

### Frontend не собирается

```bash
cd frontend

# Очистить node_modules
rm -rf node_modules package-lock.json
npm install

# Очистить Next.js cache
rm -rf .next
npm run dev
```

### "Cannot find module '@/components'"

Убедись, что `tsconfig.json` содержит:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
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

# Если не помогло — завершить
POST /api/admin/projects/{id}/force-package
```

### Ошибка: "no usable real API keys"

1. Убедись, что `ENABLE_REAL_MODEL_CALLS=true` в `.env`
2. Добавь ключи через админку (`/admin/providers`)
3. Перезагрузи бэкенд
4. Используй mock-модели для разработки

### Забыл пароль админа

```bash
cat backend/.founder-password
```

### Ошибка подключения к БД

```bash
# Проверить, что PostgreSQL запущен
psql -U postgres

# Проверить DATABASE_URL в .env
echo $DATABASE_URL

# Проверить права доступа
psql -U postgres -h localhost -l
```

---

## 🎯 Полезные команды

### Backend

```bash
# Запуск в режиме разработки
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Запуск тестов
pytest
pytest --cov=app
pytest tests/test_auth.py
pytest tests/test_auth.py::test_register -v

# Создать миграцию (если используется Alembic)
alembic revision --autogenerate -m "add new table"
alembic upgrade head

# Сброс админ пароля
python << 'EOF'
from app.lib.security import hash_password
from app.models import User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///./test.db")
Session = sessionmaker(bind=engine)
db = Session()

admin = db.query(User).filter(User.role == "admin").first()
if admin:
    admin.password_hash = hash_password("newpassword123")
    db.commit()
    print("✓ Password reset")
EOF
```

### Frontend

```bash
# Запуск в режиме разработки
cd frontend
npm run dev

# Сборка production
npm run build

# Запуск production сборки локально
npm run build
npm start

# Запуск тестов
npm test
npm test -- --watch
npm test -- --coverage

# Линтинг
npx eslint .

# Форматирование
npx prettier --write .

# Проверка типов
npx tsc --noEmit
```

### Docker

```bash
# Запуск контейнеров
docker compose up --build

# Просмотр логов
docker compose logs -f backend
docker compose logs -f frontend

# Остановка
docker compose down

# Удаление volumes (осторожно!)
docker compose down -v

# Масштабирование бэкенда
docker compose up -d --scale backend=3
```

### Git

```bash
# Статус
git status

# Изменения
git diff                    # unstaged
git diff --staged          # staged

# Коммит
git add .
git commit -m "[feat](projects): add new feature"

# Push/Pull
git push origin feature/xyz
git pull origin develop

# История
git log --oneline -10
git log --graph --oneline --all

# Ветки
git branch -a
git checkout -b feature/new
git branch -D old-branch
```

---

## 📚 Дополнительные ресурсы

### Документация

- [docs/DEVELOPMENT_COMMANDS.md](./docs/DEVELOPMENT_COMMANDS.md) — все детали
- [docs/internal/SYSTEM_CONTEXT.md](./docs/internal/SYSTEM_CONTEXT.md) — глубокая архитектура
- [docs/internal/SECURITY_AND_HONEYPOT.md](./docs/internal/SECURITY_AND_HONEYPOT.md) — security
- [docs/internal/PRODUCTION_RUNBOOK.md](./docs/internal/PRODUCTION_RUNBOOK.md) — deployment

### Внешние ресурсы

- [FastAPI docs](https://fastapi.tiangolo.com/)
- [React docs](https://react.dev)
- [TypeScript handbook](https://www.typescriptlang.org/docs/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Pytest](https://docs.pytest.org/)
- [Next.js](https://nextjs.org/docs)

### API документация

- OpenAPI Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## ✅ Чеклист перед началом работы

- [ ] Python 3.11+ установлен
- [ ] Node.js 18+ установлен
- [ ] Виртуальное окружение создано
- [ ] Зависимости установлены (pip, npm)
- [ ] Оба сервера запущены
- [ ] Админка доступна
- [ ] Mock-провайдер активен
- [ ] Создан тестовый проект
- [ ] Логи видны в обоих терминалах
- [ ] Прочитана эта документация

---

## 🤝 Контакты и поддержка

- **Вопросы?** Спроси в команде
- **Нашел баг?** Создай issue
- **Нужна помощь?** Проверь Troubleshooting раздел
- **Идея улучшения?** Создай feature request

---

## 📊 Быстрая справка по структуре

```
Backend (Python/FastAPI):
  HTTP Request → Router → Service → Database
  
Frontend (React/Next.js):
  User Input → Component → API Call → Backend
  
Project Execution:
  POST /api/projects → ProjectIntake → Phase Loop → Packaging → ZIP
  
Phases:
  Intake → Understanding → Spec → Architecture → Build → Review → 
  Repair (optional) → Audit → Packaging
  
Agents (Swarm):
  Lead → Critic → Builder → Reviewer → Judge
  (ротируются каждую фазу)
  
Credits:
  1 cr = $0.01 USD
  Фиксированная стоимость per фаза
  85% → saving mode, 100% → partial_ready
```

---

**Версия:** 1.0  
**Обновлено:** 2025-01-15  
**Автор:** SwarmBuild Team

**🚀 Готов к разработке? Начни с [Быстрого старта](#быстрый-старт)**
