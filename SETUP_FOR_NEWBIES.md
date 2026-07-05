# SwarmBuild — Гайд для новых разработчиков

Быстрый старт за 5 минут! 🚀

---

## 1️⃣ Клонируй и установи зависимости

```bash
# Если еще не клонировал
git clone <repo-url>
cd swarmbuild

# Бэкенд
cd backend
python3 -m venv .venv
source .venv/bin/activate        # MacOS/Linux
# или: .venv\Scripts\activate   # Windows
pip install -r requirements.txt

# Вернись в корень и установи фронтенд
cd ../frontend
npm install
```

---

## 2️⃣ Запусти оба сервера

**Бэкенд (terminal 1):**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Фронтенд (terminal 2):**
```bash
cd frontend
npm run dev
```

✅ **Готово!** Открой http://localhost:3000

---

## 3️⃣ Вход в админку

1. Перейди http://localhost:3000/admin-login
2. Email: `founder@swarmbuild.ai`
3. Пароль: 
   ```bash
   cat backend/.founder-password
   ```
4. Откройся `/admin/providers` и проверь, что Mock провайдер активен

---

## 4️⃣ Создай тестовый проект

1. На главной странице http://localhost:3000 нажми **"Создать проект"**
2. Заполни:
   - Название: `My First MVP`
   - Описание: `A simple todo app with React and Python`
   - Бюджет: выбери **Free Test Run** ($1)
3. Нажми **"Запустить"**
4. Смотри, как рой работает! 🤖

---

## 5️⃣ Изучи структуру

```
swarmbuild/
├── backend/              # Python/FastAPI
│   ├── app/
│   │   ├── routers/      # API endpoints
│   │   ├── services/     # Business logic
│   │   └── models.py     # Database models
│   ├── requirements.txt
│   └── .venv/
│
├── frontend/             # React/Next.js
│   ├── app/
│   ├── components/
│   └── package.json
│
└── docs/
    └── DEVELOPMENT_COMMANDS.md  # Подробно
```

---

## 🎯 Что дальше?

- **Полное руководство**: [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md)
- **Команды разработки**: [docs/DEVELOPMENT_COMMANDS.md](./docs/DEVELOPMENT_COMMANDS.md)
- **API Docs**: http://localhost:8000/docs (OpenAPI)

---

## 🚨 Частые проблемы

### "ModuleNotFoundError: No module named 'app'"

```bash
cd backend
export PYTHONPATH=$PWD
uvicorn app.main:app --reload
```

### "Cannot find module '@/components'"

```bash
cd frontend
npm install
rm -rf .next
npm run dev
```

### "Connection refused on port 8000"

Проверь, что:
```bash
# Бэкенд запущен?
curl http://localhost:8000/docs
# Должна вернуть 200 OK
```

### Забыл пароль админа

```bash
cat backend/.founder-password
```

---

## ✅ Чеклист перед началом

- [ ] Установлены Python 3.11+ и Node.js 18+
- [ ] Виртуальное окружение создано (`source .venv/bin/activate`)
- [ ] Зависимости установлены (`pip install -r requirements.txt`, `npm install`)
- [ ] Оба сервера запущены (бэкенд на 8000, фронтенд на 3000)
- [ ] Админка доступна (http://localhost:3000/admin-login)
- [ ] Создан тестовый проект
- [ ] Видишь логи в обоих терминалах

---

## 💡 Советы

1. **Используй mock-провайдер** для разработки (не нужны реальные API-ключи)
2. **Открывай DevTools** (F12) если что-то сломалось
3. **Проверь логи**: `data/projects/{project_id}/logs/events.jsonl`
4. **Перезагрузи**: если странное поведение, перезагрузи оба сервера

---

Вопросы? Смотри [DEVELOPER_GUIDE.md](./DEVELOPER_GUIDE.md) или спроси в команде! 🤝
