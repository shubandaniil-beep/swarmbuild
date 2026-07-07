# Деплой SwarmBuild

Прод-стек: **Postgres + Redis + backend (FastAPI) + frontend (Next.js)** через
`docker-compose.yml`. Ниже — путь от чистого сервера до работающего сервиса.

## 0. Предварительно

- Хост с Docker + Docker Compose (VPS/облако).
- Домен и TLS. Рекомендуемая схема: два поддомена за reverse-proxy с HTTPS —
  `app.example.com` → frontend:3000, `api.example.com` → backend:8000.
  (Nginx/Caddy/Traefik — на ваш выбор; TLS обязателен, т.к. сессия в
  HttpOnly-cookie.)

## 1. Секреты и переменные (`.env` рядом с docker-compose.yml)

Обязательные:

```dotenv
# длинная случайная строка (шифрование ключей провайдеров и секретов)
ENCRYPTION_SECRET=<openssl rand -base64 48>

# founder-доступ в админку
ADMIN_EMAIL=founder@yourdomain.com
ADMIN_PASSWORD=<длинный уникальный пароль>

# origin фронта — иначе API отклонит браузерные запросы (CORS)
CORS_ALLOW_ORIGINS=https://app.example.com

# публичный URL бэкенда — ВБИВАЕТСЯ В BUILD фронта (NEXT_PUBLIC_*),
# поэтому меняется только пересборкой образа frontend
NEXT_PUBLIC_API_URL=https://api.example.com

# реальные вызовы моделей + ключи провайдеров (иначе mock)
ENABLE_REAL_MODEL_CALLS=true
GEMINI_API_KEY=...
OPENROUTER_API_KEY=...
# OPENAI_API_KEY / ANTHROPIC_API_KEY / DEEPSEEK_API_KEY / QWEN_API_KEY — по необходимости
```

> ⚠️ `NEXT_PUBLIC_API_URL` инлайнится в клиентский бандл на этапе `docker build`
> (см. `frontend/Dockerfile` ARG). Правка этой переменной требует **пересборки**
> образа frontend, а не только рестарта.

## 2. Сборка и запуск

```bash
docker compose build            # frontend соберётся с NEXT_PUBLIC_API_URL из .env
docker compose up -d
docker compose ps               # db healthy, backend/redis/frontend up
```

При старте backend сам создаёт схему (`Base.metadata.create_all`), выполняет
лёгкие миграции недостающих колонок и сидит дефолты + founder-аккаунт
(`registry_seed`). Отдельный шаг миграций не нужен.

## 3. Проверка

```bash
curl -fsS https://api.example.com/api/health || docker compose logs backend | tail
```

- Открыть `https://app.example.com/admin-login`, войти под `ADMIN_EMAIL` /
  `ADMIN_PASSWORD`.
- В админке `AI Runtime` добавить/проверить провайдеров и ключи, прогнать
  «Test API», убедиться, что usable keys > 0 и real models > 0.
- Создать тестовый проект и убедиться, что статус доходит до `ready` и
  `project.zip` скачивается.

## 4. Реальные вызовы — smoke

Опционально, дешёвый платный прогон против Groq:

```bash
make canary SWARMBUILD_CANARY_GROQ_KEY=gsk_...
```

## 5. Данные и бэкапы

- Постоянные тома: `pgdata` (Postgres) и `projects` (workspace’ы проектов).
  Настройте регулярный бэкап обоих.
- Секреты не хранятся в образе; `.env` держите вне git (уже в `.gitignore`).

## 6. Перед публичным запуском (обязательно)

- [ ] TLS настроен на обоих поддоменах; `CORS_ALLOW_ORIGINS` = точный origin фронта.
- [ ] Reverse-proxy пробрасывает `X-Forwarded-Proto` (и `X-Forwarded-For`). Бэкенд
      запускается с `--proxy-headers` (уже в Dockerfile) и по этому заголовку
      ставит `Secure` на сессионную куку — иначе за TLS-прокси кука уйдёт без Secure.
- [ ] **`FORWARDED_ALLOW_IPS` = IP/подсеть реверс-прокси** (не `*`!). При `*` uvicorn
      доверяет `X-Forwarded-For` от любого клиента → спуф source-IP обходит
      анти-фрод по IP (лимиты регистраций/брутфорса) и отравляет аудит-логи.
      Прокси при этом ДОЛЖЕН перезаписывать входящий `X-Forwarded-For`
      (`proxy_set_header X-Forwarded-For $remote_addr`), а не дописывать.
- [ ] Сменён `ADMIN_PASSWORD`, сгенерирован уникальный `ENCRYPTION_SECRET`.
- [ ] `DEFAULT_MODEL_PROVIDER`/`ENABLE_REAL_MODEL_CALLS` выставлены осознанно.
- [ ] **Юридический пакет** (`docs/legal/`) — заполнить плейсхолдеры, дать на
      проверку юристу и опубликовать `/terms`, `/privacy`, AUP, billing-политику.
      До этого не открывать публичный платный доступ. Черновики намеренно НЕ
      подключены как живые страницы (содержат `[ПЛЕЙСХОЛДЕРЫ]`).
- [ ] Проверены лимиты/квоты провайдеров и поведение при исчерпании ключей.

## 7. Известные ограничения

- Воркер проектов — in-process threads (`workers/project_worker.py`); Redis
  подключён, но очередь пока не вынесена. Для горизонтального масштабирования
  backend нужно вынести исполнение в отдельный воркер-процесс.
- Миграции — через `create_all` (без Alembic); для эволюции схемы на проде
  закладывайте отдельный инструмент миграций.
