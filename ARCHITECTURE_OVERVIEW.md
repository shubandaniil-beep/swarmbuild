# SwarmBuild — Архитектурный обзор

Высокоуровневое описание архитектуры и того, как компоненты взаимодействуют.

---

## 🎯 Основная идея

```
User загружает идею + выбирает бюджет
           ↓
      Создается Project
           ↓
    Инициируется Phase Pipeline
           ↓
   Ротирующийся Swarm агентов
      выполняет фазы
           ↓
Генерируются артефакты
    (код, спека, docs)
           ↓
  Собирается project.zip
```

---

## 🏛️ Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React/Next.js)                │
│  - Project creation form                                        │
│  - Admin dashboard (/admin/providers, /admin/models, etc)       │
│  - Project progress tracking                                    │
│  - Artifact viewer & download                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    HTTP / REST API
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                     API ROUTERS                            │ │
│  │  - /api/projects (CRUD)                                    │ │
│  │  - /api/auth (register, login)                             │ │
│  │  - /api/admin/* (management)                               │ │
│  │  - /api/artifacts (download)                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    SERVICES                                │ │
│  │  - ProjectIntake: create project, init workspace           │ │
│  │  - ProjectSwarm: orchestrate rotating agents               │ │
│  │  - PhaseExecutor: execute each phase                       │ │
│  │  - ArtifactBuilder: collect & package artifacts            │ │
│  │  - ModelRouter: route to LLM providers                      │ │
│  │  - SecretScanner: detect & redact secrets                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               SANDBOX & EXECUTION                          │ │
│  │  - CommandExecutor: run git/npm/python safely              │ │
│  │  - Whitelist: allowed binaries only                        │ │
│  │  - Timeout: 30s per command                                │ │
│  │  - Workspace: confined to project dir                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               LLMS & AGENTS                                │ │
│  │  - Mock Provider (deterministic, for dev)                  │ │
│  │  - OpenAI Provider (GPT-4, etc)                            │ │
│  │  - Anthropic Provider (Claude)                             │ │
│  │  - Gemini, DeepSeek, Qwen, OpenRouter                      │ │
│  │  - Key pool & failover logic                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           ↓                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              DATABASE (SQLAlchemy)                         │ │
│  │  - Users, Projects, Phases, Artifacts                      │ │
│  │  - Providers, Models, Tariffs                              │ │
│  │  - API Keys (encrypted AES-GCM)                            │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│               PERSISTENT STORAGE                                │
│  - PostgreSQL (user, project, billing data)                     │
│  - Filesystem: data/projects/{id}/ (workspaces)                 │
│  - Redis (optional, for caching/queue)                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Поток выполнения проекта

### 1. Создание проекта (Intake)

```python
POST /api/projects
{
  "title": "My App",
  "brief": "A todo app...",
  "tariff_id": "small-mvp",
  "personality_mode": "startup_aggressive"
}
```

**Что происходит:**
1. Валидация brief (prompt injection detection)
2. Создание `Project` в БД (состояние: `created`)
3. Создание workspace: `data/projects/{id}/`
4. Инициализация: `brief.md`, `budget_state.json`, `phase_plan.json`
5. Возврат project ID пользователю

---

### 2. Запуск проекта (Swarm Pipeline)

```python
POST /api/projects/{id}/start
```

**Что происходит:**
1. Проверка бюджета (достаточно credits?)
2. Создание Phase Plan (какие фазы + их стоимость)
3. Инициализация Swarm State (распределение ролей агентов)
4. **Запуск background task**: фазовый executor

**Каждая фаза (async loop):**

```
Phase N (e.g., spec_war)
  ↓
  Load swarm_state (выбрать lead, critic, builder, judge)
  ↓
  Generate agent directives (prompts/spec_war.py)
  ↓
  Call LLM (leader agent)
    → retry logic (1 retry, then failover to mock)
  ↓
  Execute commands in sandbox
    → git init, npm install, python script, etc
  ↓
  Collect artifacts (spec.md, code/, etc)
  ↓
  Judge phase (другой agent проверяет качество)
  ↓
  Log event in events.jsonl
  ↓
  Update budget_state.json
  ↓
  Rotate swarm roles
  ↓
  Phase N+1 (repeat)
```

---

### 3. Логирование

Все события логируются в `data/projects/{id}/logs/`:

```
events.jsonl
{
  "timestamp": "2025-01-15T10:30:45Z",
  "phase": "spec_war",
  "event_type": "phase_started",
  "agent": "claude-3-sonnet",
  "role": "lead",
  "details": {...}
}

agent-calls.jsonl
{
  "timestamp": "...",
  "agent": "claude-3-sonnet",
  "phase": "spec_war",
  "prompt_tokens": 1200,
  "completion_tokens": 3400,
  "cost_credits": 25,
  ...
}

command-runs.jsonl
{
  "timestamp": "...",
  "command": "npm install",
  "exit_code": 0,
  "stdout": "added 245 packages",
  "stderr": "",
  "duration_ms": 8500
}
```

---

### 4. Сборка артефактов (Packaging)

На финальной фазе система собирает:

```
artifacts/
├── mvp/
│   ├── code.zip              # Исходный код
│   ├── setup.md              # Инструкции по установке
│   └── running.md            # Как запустить
├── docs/
│   ├── technical_spec.md
│   ├── architecture.md
│   └── API.md
├── business_plan.md
├── pitch_outline.md
├── limitations.md
└── security-report.md
```

Все скачивается как **project.zip** (с очисткой secrets!)

---

## 🔄 Ротация агентов (Swarm Orchestration)

### Правила ротации

```python
# swarm_state.json
{
  "agents": [
    {"model": "gpt-4", "current_role": "lead"},
    {"model": "claude-opus", "current_role": "critic"},
    {"model": "gemini-2", "current_role": "builder"},
    {"model": "gpt-4-turbo", "current_role": "reviewer"}
  ],
  "phase_history": {
    "intake": {"lead": "gpt-4"},
    "swarm_understanding": {"lead": "claude-opus"},
    ...
  }
}
```

**При переходе к следующей фазе:**

1. **Judge фазы ≠ Lead фазы** (разные модели)
2. **Rotate roles** (lead → critic, critic → builder, и т.д.)
3. **Avoid back-to-back lead** (модель не lead > 2 фаз подряд)
4. Выбрать новых агентов для новых ролей

---

## 💾 Модель данных

### Основные таблицы

```python
# Users
class User:
  id: UUID
  email: str (unique)
  password_hash: str
  role: enum("user", "admin")
  created_at: datetime
  device_fingerprints: list[str]  # against hijacking
  credits: int (balance)

# Projects
class Project:
  id: UUID
  user_id: UUID (FK)
  title: str
  brief: str
  state: enum("created", "running", "paused", "completed", "failed")
  personality_mode: str
  workspace_path: str  # data/projects/{id}/
  created_at: datetime
  started_at: datetime (nullable)
  completed_at: datetime (nullable)

# Phases
class Phase:
  id: UUID
  project_id: UUID (FK)
  key: str  # "intake", "spec_war", etc
  state: enum("pending", "running", "completed", "failed")
  agent_role: str  # "lead", "critic", etc
  model_id: UUID (FK)
  started_at: datetime
  completed_at: datetime
  cost_credits: int
  output_summary: str

# Artifacts
class Artifact:
  id: UUID
  project_id: UUID (FK)
  phase_id: UUID (FK)
  name: str  # "technical_spec.md", "main.py"
  artifact_type: str  # "spec", "code", "doc", "plan"
  file_path: str
  mime_type: str
  size_bytes: int
  created_at: datetime

# Providers
class Provider:
  id: UUID
  name: str  # "openai", "anthropic"
  provider_type: str
  base_url: str
  is_enabled: bool
  created_at: datetime

# APIKey
class APIKey:
  id: UUID
  provider_id: UUID (FK)
  key_encrypted: str (AES-GCM)
  is_enabled: bool
  last_used_at: datetime
  error_count: int
  created_at: datetime

# Models
class Model:
  id: UUID
  name: str  # "gpt-4-turbo", "claude-3-opus"
  provider_id: UUID (FK)
  model_identifier: str
  capabilities: list[str]  # "chat", "vision", etc
  cost_per_1k_input: float (credits)
  cost_per_1k_output: float (credits)
  is_enabled: bool
  max_tokens: int

# Tariff
class Tariff:
  id: UUID
  name: str  # "Free Test Run", "Standard MVP"
  price_usd: float
  credits_included: int
  bonus_percent: int
  max_phases: int
  max_swaps: int
  created_at: datetime
```

---

## 🔑 Key Components

### 1. ProjectIntake (`services/project_intake.py`)

**Задача:** инициализировать проект и workspace

```python
def create_project(user_id, title, brief, tariff_id):
  # 1. Validate brief (prompt injection detection)
  # 2. Create Project record in DB
  # 3. Create workspace dir
  # 4. Write brief.md
  # 5. Initialize phase_plan.json based on budget
  # 6. Create budget_state.json
  # 7. Return project_id
```

---

### 2. ProjectSwarm (`services/project_swarm.py`)

**Задача:** управлять ротацией агентов и запуском фаз

```python
def rotate_swarm_roles():
  # 1. Load swarm_state.json
  # 2. Check phase history (avoid back-to-back lead)
  # 3. Judge != Lead of next phase
  # 4. Rotate roles (lead → critic → ...)
  # 5. Save updated swarm_state.json
  
def select_judge():
  # 1. Load swarm_state.json
  # 2. Find agent who is NOT lead
  # 3. Return judge_agent_id
```

---

### 3. PhaseExecutor (`services/phase_executor.py`)

**Задача:** выполнить одну фазу (например, spec_war)

```python
async def execute_phase(project_id, phase_key):
  # 1. Load phase directives from prompts/{phase_key}.py
  # 2. Load swarm_state (get lead agent)
  # 3. Call LLM with directive + project context
  # 4. Parse response → actions (write files, run commands)
  # 5. Execute commands in sandbox
  # 6. Judge phase (call judge agent)
  # 7. Log all events
  # 8. Update budget_state
  # 9. Move to next phase or pause if budget low
```

---

### 4. ModelRouter (`services/model_router.py`)

**Задача:** маршрутизировать запросы к LLM провайдерам

```python
async def call_model(model_id, prompt, messages):
  # 1. Get Model from DB
  # 2. Get Provider for model
  # 3. Load API keys for provider (pool rotation)
  # 4. Call LLM (with retry logic)
  # 5. On error (429, 401): switch to next key or failover to mock
  # 6. Log token usage & cost
  # 7. Update provider key stats
  # 8. Return response
```

---

### 5. CommandExecutor (`sandbox/command_executor.py`)

**Задача:** безопасно выполнять команды в workspace

```python
def execute_command(project_id, command):
  # 1. Parse command (whitelist binaries)
  # 2. Check workspace confinement (no `..`, `~`, abs paths)
  # 3. Set timeout (30s)
  # 4. Run in subprocess
  # 5. Capture stdout/stderr
  # 6. Redact secrets from output
  # 7. Log execution
  # 8. Return exit_code, stdout, stderr
```

---

### 6. SecretScanner (`lib/secret_scanner.py`)

**Задача:** обнаружить и скрыть secrets в артефактах

```python
def scan_artifacts(project_id):
  # 1. Walk through artifacts/
  # 2. Regex scan for: API keys, DB URLs, JWT tokens, etc
  # 3. Either redact in-place or flag for review
  # 4. Convert .env → .env.example
  # 5. Block download if high-risk secrets found
```

---

## 🔐 Безопасность

### Шифрование

```python
# API Keys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def encrypt_key(api_key: str, secret: str) -> str:
  cipher = AESGCM(secret.encode()[:32].ljust(32, b'0'))
  nonce = os.urandom(12)
  ciphertext = cipher.encrypt(nonce, api_key.encode(), None)
  return base64.b64encode(nonce + ciphertext)

def decrypt_key(encrypted: str, secret: str) -> str:
  # Reverse process
```

### Sandbox изоляция

```bash
# Whitelist только разрешенные бинарии
ALLOWED_COMMANDS = {
  "python", "python3", "npm", "node", "git",
  "cat", "ls", "mkdir", "cd", "echo"
}

# Запретить опасные пути
FORBIDDEN_PATHS = ["/..", "~", "/etc/passwd", "/root"]

# Конфайн в workspace
chdir(f"data/projects/{project_id}/repo")
# Команда: git init
# Реально выполняется: cd data/projects/{id}/repo && git init
```

---

## 📈 Кредитная система

### Стоимость фаз

```python
PHASE_COSTS = {
  "intake": 150,
  "swarm_understanding": 180,
  "spec_war": 250,
  "architecture_battle": 280,
  "build_sprint": 400,  # дорого
  "review_stop": 150,
  "repair_sprint": 300,
  "final_audit": 100,
  "packaging": 50
}

# Итого за Full pipeline = ~1860 credits (~$18.60)
```

### Режимы экономии

```python
# Если расходовано 85% бюджета
if spent_percent >= 85:
  enable_saving_mode()  # Сокращение scope следующих фаз

# Если 100% расходовано
if spent_percent >= 100:
  state = "partial_ready"  # Собрать имеющиеся артефакты
  # Не блокируем, выдаем partial результат
```

---

## 🚀 Как добавить новую фазу

1. Создать `app/prompts/new_phase.py` с директивами
2. Добавить в `PHASE_COSTS` стоимость
3. Добавить в `PHASE_SEQUENCE` порядок выполнения
4. Реализовать логику в `PhaseExecutor.execute_phase()`
5. Добавить тесты в `tests/test_phases.py`

---

## 📚 Дополнительные ресурсы

- [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) — все детали
- [docs/DEVELOPMENT_COMMANDS.md](./docs/DEVELOPMENT_COMMANDS.md) — команды
- [docs/internal/SYSTEM_CONTEXT.md](./docs/internal/SYSTEM_CONTEXT.md) — глубоко внутрь
- API Docs: http://localhost:8000/docs (OpenAPI)

---

**Вопросы?** Спроси в команде или открой issue! 🤝
