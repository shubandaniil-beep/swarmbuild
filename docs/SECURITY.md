# Безопасность

## Аутентификация и сессии

- Сессия — HttpOnly-cookie `sb_session` (`SameSite=Lax`, `Secure` на HTTPS).
  Bearer-заголовок поддерживается для CLI/API-клиентов.
- Токены подписаны HMAC-SHA256 и содержат версию сессии: logout инкрементирует
  версию и мгновенно отзывает все выданные токены пользователя.
- Токены **никогда** не передаются в query-параметрах (утечка в логи/историю).
- Пароли: PBKDF2-HMAC-SHA256, 200 000 итераций, случайная соль на пароль,
  constant-time сравнение. Цель на прод: Argon2id + MFA для админов.
- Rate-limit логина по IP и email (sliding window); анти-абьюз регистраций
  по device fingerprint и IP.

## API-ключи провайдеров

- Хранятся в БД зашифрованными **AES-256-GCM**; ключ шифрования выводится из
  `ENCRYPTION_SECRET` (или автогенерируется в `backend/.secret` для dev).
- UI и API отдают только маску (`sk-…f604`); плейнтекст существует в памяти
  только в момент вызова провайдера.
- `ENCRYPTION_SECRET` задаётся один раз до первого запуска; смена делает
  сохранённые ключи нерасшифровываемыми.

## CSRF / CORS / заголовки

- CORS: строгий allowlist (`CORS_ALLOW_ORIGINS`); без конфигурации — только
  localhost. Wildcard невозможен, т.к. включены credentials.
- Мутации с cookie дополнительно проверяются по Origin/Referer и
  `Sec-Fetch-Site` (middleware `cookie_origin_guard`).
- На всех ответах: `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, `Permissions-Policy`, `COOP`;
  на `/api/*` — `Cache-Control: no-store`.
- `X-Forwarded-For` доверяется только при явном `trust_proxy_headers`.

## Sandbox и сгенерированный код

- Команды выполняются только внутри workspace проекта, по allowlist бинарей,
  с timeout (`MAX_COMMAND_RUNTIME_SECONDS`).
- Сгенерированный агентами код **не исполняется** на хосте: smoke-проверка —
  это `ast.parse` (синтаксис без выполнения).
- Агенты могут писать файлы только в `repo/` своего workspace (path traversal
  отсекается резолвом пути).

## Логи и артефакты

- Никогда не логируются: пароли, plaintext-ключи, полные токены, сырые промпты.
- Ошибки провайдеров проходят redaction (`lib/redact.py`) до записи в журнал.
- Артефакты перед выдачей сканируются на секреты (`secret_scanner`) и
  фильтруются от внутренних упоминаний (`output_filter`); заблокированные
  файлы доступны только админу.
- Бриф пользователя сканируется на prompt-injection (`prompt_guard`);
  подозрительные проекты помечаются `risk_level`.

## Чеклист перед продом

1. Задать `ENCRYPTION_SECRET`, `ADMIN_PASSWORD`, `CORS_ALLOW_ORIGINS`.
2. Выключить `ENABLE_API_DOCS` (по умолчанию выключен).
3. PostgreSQL вместо SQLite; бэкапы БД и `STORAGE_PATH`.
4. Reverse-proxy с TLS; `trust_proxy_headers=true` только за доверенным прокси.
5. Ротация провайдерских ключей через админку (`/admin/providers`).
6. Если ключ когда-либо попадал в git/чат/скриншот — немедленно ротировать.
