# SwarmBuild — Стандарты кодирования и best practices

Руководство для написания чистого, поддерживаемого кода в проекте.

---

## 🐍 Python (Backend)

### Структура и организация

**Следуй структуре приложения:**

```
app/
├── main.py              # Entry point, FastAPI app initialization
├── config.py            # Settings, env vars, constants
├── models.py            # SQLAlchemy ORM models
├── schemas.py           # Pydantic request/response models
├── routers/             # API endpoints (grouped by feature)
│   ├── projects.py
│   ├── auth.py
│   └── admin.py
├── services/            # Business logic (NOT in routers)
│   ├── project_intake.py
│   ├── phase_executor.py
│   └── model_router.py
├── lib/                 # Utilities (helpers, crypto, logging, etc)
│   ├── security.py
│   ├── secrets.py
│   └── logging.py
├── prompts/             # Agent directives (one file per phase)
│   ├── intake.py
│   ├── spec_war.py
│   └── build_sprint.py
└── sandbox/             # Safe command execution
    ├── command_executor.py
    └── whitelist.py
```

### Naming conventions

```python
# Classes: PascalCase
class ProjectManager:
    pass

# Functions/methods: snake_case
def execute_phase(project_id):
    pass

# Constants: UPPER_SNAKE_CASE
MAX_COMMAND_TIMEOUT = 30
ALLOWED_COMMANDS = {"python", "npm", "git"}

# Private methods: _leading_underscore
def _validate_brief(brief: str) -> bool:
    pass

# Database table names: snake_case, singular or plural
class user_account:
    __tablename__ = "user_account"

# API endpoint paths: /api/v1/projects
# POST   /api/projects
# GET    /api/projects/{id}
# PUT    /api/projects/{id}
# DELETE /api/projects/{id}
```

### Типизация (Type hints)

**ОБЯЗАТЕЛЬНО используй type hints:**

```python
# ❌ Плохо
def create_project(user_id, title, brief):
    return {"id": "...", "title": title}

# ✅ Хорошо
from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime

def create_project(
    user_id: UUID,
    title: str,
    brief: str,
    personality_mode: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new project and initialize workspace.
    
    Args:
        user_id: UUID of user creating project
        title: Project title
        brief: Project description
        personality_mode: Optional personality mode (default: balanced)
    
    Returns:
        Project dict with id, title, state, workspace_path
    """
    pass
```

### Обработка ошибок

```python
# ✅ Используй custom exceptions
class ProjectNotFoundError(Exception):
    pass

class InsufficientCreditsError(Exception):
    pass

# ✅ Обработай ошибки в API endpoints
from fastapi import HTTPException, status

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
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
```

### Логирование

```python
import logging

logger = logging.getLogger(__name__)

# ✅ Логируй важные события
logger.info(f"Project {project_id} started")
logger.warning(f"Low credits for project {project_id}")
logger.error(f"Failed to call model: {error}", exc_info=True)

# ❌ Не логируй sensitive data
logger.info(f"API key: {api_key}")  # BAD!

# ✅ Redact sensitive data
logger.info(f"API key: {api_key[:4]}...***")  # OK
```

### Async/Await

```python
# ✅ Используй async для I/O операций
from fastapi import BackgroundTasks

@router.post("/projects/{id}/start")
async def start_project(project_id: UUID, bg_tasks: BackgroundTasks):
    # Быстро вернуть ответ, потом выполнить в background
    bg_tasks.add_task(execute_project_phases, project_id)
    return {"status": "running"}

# ✅ Правильное использование await
async def execute_project_phases(project_id: UUID):
    project = await get_project_async(project_id)
    for phase in project.phases:
        result = await execute_phase(project_id, phase.key)
        await log_event(project_id, "phase_completed", result)
```

### Тестирование

```python
# tests/test_projects.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def sample_user(db):
    """Create a test user."""
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
    """Test validation: brief is required."""
    response = client.post("/api/projects", json={
        "title": "Test MVP"
        # missing brief
    })
    
    assert response.status_code == 422
```

---

## ⚛️ JavaScript/React (Frontend)

### Структура и организация

```
frontend/
├── app/
│   ├── page.tsx                # Home page
│   ├── layout.tsx              # Root layout
│   ├── admin/
│   │   ├── layout.tsx
│   │   ├── providers/          # Admin providers page
│   │   ├── models/             # Admin models page
│   │   └── page.tsx            # Admin dashboard
│   └── api/                    # API routes (if needed)
├── components/
│   ├── ProjectForm.tsx         # Reusable components
│   ├── PhaseProgressBar.tsx
│   └── AdminTable.tsx
├── lib/
│   ├── api.ts                  # API client
│   ├── utils.ts                # Helper functions
│   └── types.ts                # Shared types
├── public/                     # Static assets
├── package.json
└── tsconfig.json
```

### Naming conventions

```typescript
// Components: PascalCase, file name same
export function ProjectForm() { }       // ProjectForm.tsx
export function AdminProviders() { }    // AdminProviders.tsx

// Functions/constants: camelCase
const fetchProjects = async () => { }
const API_BASE_URL = "http://localhost:8000"

// Files: kebab-case or PascalCase
// components/ProjectForm.tsx ✅
// components/project-form.tsx ✅
// components/projectForm.tsx ❌

// Type names: PascalCase
interface Project {
  id: string
  title: string
  status: "created" | "running" | "completed"
}
```

### Type Safety

```typescript
// ✅ Всегда используй TypeScript
interface Project {
  id: string
  title: string
  brief: string
  state: ProjectState
  workspace_path: string
  created_at: string
}

type ProjectState = "created" | "running" | "paused" | "completed" | "failed"

// ✅ Правильная типизация компонентов
interface ProjectFormProps {
  onSubmit: (data: ProjectFormData) => Promise<void>
  isLoading?: boolean
}

function ProjectForm({ onSubmit, isLoading = false }: ProjectFormProps) {
  // ...
}

// ❌ Избегай any
function fetchProject(id: any) {  // BAD!
  return fetch(`/api/projects/${id}`)
}

// ✅ Используй unknown если необходимо
function parseJSON(str: string): unknown {
  return JSON.parse(str)
}
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

### Forms & Validation

```typescript
// ✅ Используй React Hook Form + Zod для валидации
import { useForm } from "react-hook-form"
import { z } from "zod"
import { zodResolver } from "@hookform/resolvers/zod"

const projectSchema = z.object({
  title: z.string().min(1, "Title is required"),
  brief: z.string().min(10, "Brief must be at least 10 chars"),
  tariff_id: z.string().min(1, "Select a tariff"),
  personality_mode: z.enum(["balanced", "startup_aggressive", "conservative_build"])
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
      // Success
    } catch (error) {
      // Error handling
    }
  }
  
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register("title")} />
      {errors.title && <span>{errors.title.message}</span>}
    </form>
  )
}
```

### State Management

```typescript
// ✅ Используй React Context для простого state
import { createContext, useContext, useState, ReactNode } from "react"

interface AuthContext {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContext | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  
  const login = async (email: string, password: string) => {
    const response = await fetchAPI("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password })
    })
    setUser(response.user)
  }
  
  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be within AuthProvider")
  return context
}
```

### Styling

```typescript
// ✅ Используй Tailwind CSS (встроен в Next.js)
export function Button({ children, variant = "primary" }: ButtonProps) {
  const baseStyles = "px-4 py-2 rounded font-semibold"
  const variants = {
    primary: "bg-blue-500 text-white hover:bg-blue-600",
    secondary: "bg-gray-200 text-gray-900 hover:bg-gray-300"
  }
  
  return (
    <button className={`${baseStyles} ${variants[variant]}`}>
      {children}
    </button>
  )
}

// ✅ Или используй CSS modules
// Button.module.css
.button {
  padding: 8px 16px;
  border-radius: 4px;
  font-weight: 600;
}

.primary {
  background-color: #3b82f6;
  color: white;
}

// Button.tsx
import styles from "./Button.module.css"

export function Button() {
  return <button className={styles.primary}>Click me</button>
}
```

---

## 📋 Git workflow

### Commit messages

**Format:**
```
[type]([scope]): brief description (under 50 chars)

Longer explanation if needed.
- Point 1
- Point 2

Fixes #123
Relates to #456
```

**Types:**
- `feat` — новая фича
- `fix` — баг-фикс
- `docs` — документация
- `style` — форматирование, без изменения логики
- `refactor` — рефакторинг
- `test` — тесты
- `chore` — зависимости, конфиг

**Examples:**
```
feat(projects): add personality mode selection

- Add personality_mode field to Project model
- Update project creation API to accept mode
- Implement mode-based agent directives

Fixes #42

---

fix(sandbox): prevent directory traversal attacks

Validate workspace paths before command execution.

---

docs: update architecture overview
```

### Branches

```bash
# Feature
git checkout -b feature/user-authentication

# Bug fix
git checkout -b fix/sandbox-timeout

# Docs
git checkout -b docs/api-documentation

# Refactor
git checkout -b refactor/project-services
```

### Pull Request

```markdown
## Summary
Brief description of changes

## Changes
- Point 1
- Point 2

## Testing
How to test these changes

## Screenshots (if applicable)
[Screenshot/gif]

## Checklist
- [ ] Tests written/updated
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Code follows project standards
```

---

## 🧪 Testing Best Practices

### Backend (pytest)

```python
# ✅ Test one thing per test
def test_create_project_success(db, sample_user):
    """Test successful project creation."""
    response = client.post("/api/projects", json={...})
    assert response.status_code == 201

# ✅ Use descriptive names
def test_create_project_fails_with_missing_brief():
    """Test validation error when brief is missing."""
    pass

# ❌ Avoid test interdependencies
def test_user_workflow():
    # Creates user, project, phase, etc all in one test
    # Hard to debug when it fails
    pass

# ✅ Use fixtures
@pytest.fixture
def auth_headers(sample_user):
    return {"Authorization": f"Bearer {sample_user.token}"}

def test_protected_endpoint(auth_headers):
    response = client.get("/api/admin/dashboard", headers=auth_headers)
    assert response.status_code == 200
```

### Frontend (Jest/React Testing Library)

```typescript
// ✅ Test user behavior, not implementation
import { render, screen, fireEvent } from "@testing-library/react"

test("user can create a project", async () => {
  render(<CreateProjectForm />)
  
  fireEvent.change(screen.getByLabelText(/title/i), {
    target: { value: "My App" }
  })
  fireEvent.change(screen.getByLabelText(/brief/i), {
    target: { value: "A cool app" }
  })
  fireEvent.click(screen.getByRole("button", { name: /create/i }))
  
  await screen.findByText(/project created/i)
})

// ❌ Avoid snapshot tests (brittle)
test("renders ProjectForm", () => {
  const tree = renderer.create(<ProjectForm />).toJSON()
  expect(tree).toMatchSnapshot()  // BAD!
})
```

---

## 🔒 Security Checklist

- [ ] **No hardcoded secrets** (API keys, passwords) in code
- [ ] **Validate all user input** (brief, project name, etc)
- [ ] **Sanitize output** (prevent XSS, injection)
- [ ] **Use HTTPS** in production
- [ ] **Encrypt sensitive data** (API keys with AES-GCM)
- [ ] **Rate limiting** on API endpoints
- [ ] **CORS** configured properly
- [ ] **SQL injection prevention** (use ORM, parameterized queries)
- [ ] **Don't log secrets** (API keys, tokens, passwords)
- [ ] **Secure cookies** (HttpOnly, Secure, SameSite)

---

## 📊 Code Quality

### Tools

- **Python:** `pylint`, `black` (formatting), `mypy` (type checking)
- **JavaScript:** `eslint`, `prettier`, `typescript`

### Before committing

```bash
# Backend
cd backend
black .                    # Format
mypy .                     # Type check
pylint app/                # Lint
pytest --cov=app           # Test + coverage

# Frontend
cd frontend
prettier --write .         # Format
eslint .                   # Lint
npm test                   # Tests
npm run build              # Build check
```

---

## 🤝 Code Review Checklist

When reviewing PRs, check:

- [ ] Code follows project standards
- [ ] Type hints are present (Python/TS)
- [ ] Tests are included
- [ ] No hardcoded secrets
- [ ] Error handling is proper
- [ ] Performance considerations (N+1 queries, etc)
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] Commit messages are descriptive

---

## 📚 Additional Resources

- [PEP 8](https://www.python.org/dev/peps/pep-0008/) — Python style guide
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [React Documentation](https://react.dev)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)
- [Next.js Guide](https://nextjs.org/docs)

---

**Questions?** Ask in team chat or open an issue! 🚀
