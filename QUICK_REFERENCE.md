# SwarmBuild — Quick Reference Card

Быстрый справочник для разработчиков. Распечатай или сохрани как закладку! 📌

---

## 🚀 Быстрый старт (3 команды)

```bash
# 1. Бэкенд (terminal 1)
cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

# 2. Фронтенд (terminal 2)
cd frontend && npm run dev

# 3. Открыть
http://localhost:3000
```

---

## 🔐 Логины

| Что | Email | Пароль |
|-----|-------|--------|
| Админка | founder@swarmbuild.ai | `cat backend/.founder-password` |
| Demo | demo@swarmbuild.ai | demo12345 |

---

## 📡 Основные endpoints

```
POST   /api/projects              Create project
GET    /api/projects/{id}         Get project status
POST   /api/projects/{id}/start   Run swarm
GET    /api/projects/{id}/phases  List phases
GET    /api/projects/{id}/download  Get project.zip

GET    /api/admin/dashboard       Stats
GET    /api/admin/providers       Manage API keys
POST   /api/admin/projects/{id}/rerun-phase  Restart phase

Docs: http://localhost:8000/docs
```

---

## 🗂️ Project structure

```
backend/          Python/FastAPI
  ├── app/routers/      API endpoints
  ├── app/services/     Business logic
  ├── app/models.py     Database
  └── requirements.txt

frontend/         React/Next.js
  ├── app/              Pages
  ├── components/       Components
  └── package.json
```

---

## 💾 Файлы проекта

```
data/projects/{project_id}/
├── brief.md                # User's idea
├── budget_state.json       # Credits spent
├── phase_plan.json         # Phase schedule
├── swarm_state.json        # Agent assignments
├── logs/
│   ├── events.jsonl       # All events
│   ├── agent-calls.jsonl  # LLM calls
│   └── command-runs.jsonl # Shell commands
└── artifacts/             # Final output
```

---

## 🔄 Фазы проекта

```
intake
  ↓ (150 credits)
swarm_understanding
  ↓ (180 credits)
spec_war
  ↓ (250 credits)
architecture_battle
  ↓ (280 credits)
build_sprint
  ↓ (400 credits)
review_stop
  ↓ (150 credits)
repair_sprint (if budget allows)
  ↓ (300 credits)
final_audit
  ↓ (100 credits)
packaging
  ↓ (50 credits)
```

---

## 💳 Credits

- 1 credit = $0.01 USD
- Фиксированная стоимость per фаза
- Budget mode: spend 85% → saving mode, 100% → partial_ready

| Tariff | Price | Credits | Phases |
|--------|-------|---------|--------|
| Free Test | $1 | 100 | 5 |
| Fast Build | $20 | 2,000 | 5 |
| Small MVP | $40 | 4,400 | 8 |
| Standard MVP | $100 | 12,000 | 9 |
| Heavy | $200 | 26,000 | 9 |
| Custom | $500 | 70,000 | 9 |

---

## 🧪 Тестирование

```bash
# Backend
cd backend
pytest                          # Run tests
pytest --cov=app              # With coverage
pytest tests/test_auth.py      # One file
pytest -v                      # Verbose
pytest -s                      # Show prints

# Frontend
cd frontend
npm test                       # Run tests
npm test -- --watch           # Watch mode
npm test -- --coverage        # Coverage
```

---

## 🔑 API ключи (Админка)

1. Перейди `/admin/providers`
2. Выбери провайдера (OpenAI, Anthropic, Gemini, etc)
3. Нажми "Показать пул ключей"
4. Вставь ключи (space/comma/newline separated)
5. Нажми "Добавить"
6. Опционально: "Тест" для проверки

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: app` | `cd backend && export PYTHONPATH=$PWD` |
| Backend не стартует | `pip install --force-reinstall -r requirements.txt` |
| Frontend не строится | `rm -rf node_modules && npm install && npm run dev` |
| Забыл пароль админа | `cat backend/.founder-password` |
| Project stuck on phase | `POST /api/admin/projects/{id}/rerun-phase` |

---

## 📝 Git workflow

```bash
# Feature branch
git checkout -b feature/xyz
git add .
git commit -m "[feat](scope): description"
git push

# Commit types
[feat]     New feature
[fix]      Bug fix
[docs]     Documentation
[refactor] Code cleanup
[test]     Tests
[chore]    Dependencies
```

---

## 🔒 Security reminders

- ❌ Never commit `.env` with real keys
- ❌ No hardcoded secrets in code
- ✅ Use `.env.example` as template
- ✅ Encrypt API keys (AES-GCM)
- ✅ Validate all user input
- ✅ Redact secrets from logs

---

## 🐍 Python conventions

```python
# Classes: PascalCase
class ProjectManager:
    pass

# Functions: snake_case
def execute_phase():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_TIMEOUT = 30

# Always use type hints
def create_project(user_id: UUID, title: str) -> Project:
    pass

# Logging (no secrets!)
logger.info(f"Project {project_id} started")
logger.error(f"Error: {error}", exc_info=True)
```

---

## ⚛️ TypeScript/React conventions

```typescript
// Components: PascalCase
function ProjectForm() {}

// Functions: camelCase
const fetchProjects = async () => {}

// Constants: UPPER_SNAKE_CASE
const API_URL = "http://localhost:8000"

// Always use types
interface Project {
  id: string
  title: string
}

function handleSubmit(data: ProjectFormData) {}
```

---

## 📊 Database models

```
User        → projects
Project     → phases, artifacts, events
Phase       → artifacts, events
Artifact    → (file in filesystem)
Provider    → api_keys, models
Model       → provider_id
APIKey      → provider_id (encrypted)
Tariff      → (pricing)
```

---

## 🚀 Deployment checklist

- [ ] Update version in code
- [ ] Run all tests (`pytest`, `npm test`)
- [ ] Build check (`npm run build`)
- [ ] Set `.env` with production values
- [ ] Backup database
- [ ] Deploy backend
- [ ] Deploy frontend
- [ ] Run smoke tests
- [ ] Monitor logs

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [README.md](./README.md) | Project overview |
| [SETUP_FOR_NEWBIES.md](./SETUP_FOR_NEWBIES.md) | First 5 minutes |
| [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) | Full developer guide |
| [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) | System design |
| [CODING_STANDARDS.md](./CODING_STANDARDS.md) | Code conventions |
| [docs/DEVELOPMENT_COMMANDS.md](./docs/DEVELOPMENT_COMMANDS.md) | All commands |
| [docs/internal/](./docs/internal/) | Internal docs (secret) |

---

## 🔗 Useful links

- **API Docs**: http://localhost:8000/docs
- **Frontend**: http://localhost:3000
- **Backend**: http://localhost:8000
- **Admin login**: http://localhost:3000/admin-login
- **GitHub**: [repo-url]
- **Linear/Issues**: [tracker-url]

---

## 💬 Communication

- **Questions?** Ask in Slack/Discord
- **Found a bug?** Create an issue
- **Need help?** Check DEVELOPER_GUIDE.md
- **Code review?** Tag maintainers

---

## 🎯 Daily workflow

```bash
# Morning
source .venv/bin/activate          # Activate venv
git pull origin develop             # Get latest
uvicorn app.main:app --reload       # Start backend
npm run dev                          # Start frontend
# Open http://localhost:3000

# During day
# Make changes → Test → Commit

# Before push
pytest                              # Backend tests
npm test                            # Frontend tests
git log --oneline -5                # Check commits
git push origin feature/xyz          # Push

# Code review
# → Merge to develop
# → Deploy to staging
# → Deploy to production
```

---

## ⚡ Keyboard shortcuts

| Shortcut | What |
|----------|------|
| `F12` | DevTools (browser) |
| `Ctrl+K` | Command palette (VS Code) |
| `Ctrl+Shift+D` | Debug (VS Code) |
| `npm run dev -- --turbopack` | Faster Next.js dev |

---

## 🎓 Learning resources

- [FastAPI docs](https://fastapi.tiangolo.com/)
- [React docs](https://react.dev)
- [TypeScript handbook](https://www.typescriptlang.org/docs/)
- [SQLAlchemy tutorial](https://docs.sqlalchemy.org/)
- [Pytest tutorial](https://docs.pytest.org/)

---

**Last updated:** 2025-01-15  
**Version:** 1.0

---

*Bookmark this page! 🔖*
