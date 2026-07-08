#!/bin/bash
# ============================================================
#  SwarmBuild — запуск в один клик
#  Дважды кликни этот файл. Он сам поставит зависимости,
#  поднимет backend + frontend и откроет браузер.
#  Чтобы остановить — закрой это окно терминала или нажми Ctrl+C.
# ============================================================

set -u

# --- перейти в папку, где лежит сам скрипт (работает из любого места) ---
cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"
LOGS="$ROOT/.run-logs"
mkdir -p "$LOGS"

BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_PID=""
FRONTEND_PID=""

# --- цвета для читаемости ---
G="\033[32m"; Y="\033[33m"; R="\033[31m"; B="\033[36m"; N="\033[0m"
say()  { printf "${B}▶ %s${N}\n" "$1"; }
ok()   { printf "${G}✔ %s${N}\n" "$1"; }
warn() { printf "${Y}! %s${N}\n" "$1"; }
die()  { printf "${R}ОШИБКА: %s${N}\n" "$1"; printf "\nОкно можно закрыть.\n"; read -r _; exit 1; }

# --- аккуратно гасим оба процесса при выходе/закрытии окна ---
cleanup() {
  printf "\n"
  say "Останавливаю SwarmBuild..."
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
  # добить всё, что осталось на портах
  local fp bp
  fp="$(lsof -ti tcp:$FRONTEND_PORT 2>/dev/null)"; [ -n "$fp" ] && kill $fp 2>/dev/null
  bp="$(lsof -ti tcp:$BACKEND_PORT  2>/dev/null)"; [ -n "$bp" ] && kill $bp 2>/dev/null
  ok "Остановлено. Окно можно закрыть."
  exit 0
}
trap cleanup INT TERM EXIT

port_busy() { lsof -ti tcp:"$1" >/dev/null 2>&1; }

clear
printf "${G}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║        S W A R M B U I L D            ║"
echo "  ║        запуск в один клик            ║"
echo "  ╚══════════════════════════════════════╝"
printf "${N}\n"

# ------------------------------------------------------------
# 0. Проверка инструментов
# ------------------------------------------------------------
command -v python3 >/dev/null 2>&1 || die "Не найден Python 3. Установи с https://www.python.org/downloads/ и запусти снова."
command -v npm     >/dev/null 2>&1 || die "Не найден Node.js/npm. Установи с https://nodejs.org и запусти снова."

# ------------------------------------------------------------
# 1. Backend: venv + зависимости
# ------------------------------------------------------------
say "Готовлю backend..."
if [ ! -x "backend/.venv/bin/python" ]; then
  say "Создаю виртуальное окружение Python (первый раз, ~1 мин)..."
  python3 -m venv backend/.venv || die "Не удалось создать venv."
fi
VENV_PY="backend/.venv/bin/python"

# ставим зависимости, только если uvicorn ещё не установлен
if [ ! -x "backend/.venv/bin/uvicorn" ]; then
  say "Устанавливаю зависимости backend..."
  "$VENV_PY" -m pip install --quiet --upgrade pip
  "$VENV_PY" -m pip install --quiet -r backend/requirements.txt || die "Не удалось установить зависимости backend."
fi
ok "Backend готов."

# ------------------------------------------------------------
# 2. Frontend: node_modules
# ------------------------------------------------------------
say "Готовлю frontend..."
if [ ! -d "frontend/node_modules" ]; then
  say "Устанавливаю зависимости frontend (первый раз, ~1–2 мин)..."
  ( cd frontend && npm install --silent ) || die "Не удалось установить зависимости frontend."
fi
ok "Frontend готов."

# ------------------------------------------------------------
# 3. Запуск backend (FastAPI на :8000)
# ------------------------------------------------------------
if port_busy $BACKEND_PORT; then
  warn "Порт $BACKEND_PORT уже занят — считаю, что backend уже запущен."
else
  say "Запускаю backend на http://localhost:$BACKEND_PORT ..."
  ( cd backend && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $BACKEND_PORT ) \
      >"$LOGS/backend.log" 2>&1 &
  BACKEND_PID=$!
fi

# ждём, пока backend ответит на /api/health (до ~30 сек)
say "Жду готовности backend..."
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:$BACKEND_PORT/api/health" >/dev/null 2>&1; then
    ok "Backend отвечает."
    break
  fi
  if [ -n "$BACKEND_PID" ] && ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    printf "\n--- backend.log ---\n"; tail -n 30 "$LOGS/backend.log"
    die "Backend упал при старте. Лог выше."
  fi
  sleep 0.5
  [ "$i" = "60" ] && warn "Backend долго не отвечает — продолжаю, проверь $LOGS/backend.log"
done

# ------------------------------------------------------------
# 4. Запуск frontend (Next.js на :3000)
# ------------------------------------------------------------
if port_busy $FRONTEND_PORT; then
  warn "Порт $FRONTEND_PORT уже занят — считаю, что frontend уже запущен."
else
  say "Запускаю frontend на http://localhost:$FRONTEND_PORT ..."
  ( cd frontend && exec npm run dev ) >"$LOGS/frontend.log" 2>&1 &
  FRONTEND_PID=$!
fi

# ждём, пока фронт поднимется (до ~40 сек)
say "Жду готовности интерфейса..."
for i in $(seq 1 80); do
  if curl -fsS "http://127.0.0.1:$FRONTEND_PORT" >/dev/null 2>&1; then
    ok "Интерфейс готов."
    break
  fi
  if [ -n "$FRONTEND_PID" ] && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
    printf "\n--- frontend.log ---\n"; tail -n 30 "$LOGS/frontend.log"
    die "Frontend упал при старте. Лог выше."
  fi
  sleep 0.5
done

# ------------------------------------------------------------
# 5. Открыть браузер
# ------------------------------------------------------------
open "http://localhost:$FRONTEND_PORT" 2>/dev/null

printf "\n${G}════════════════════════════════════════════════${N}\n"
ok "SwarmBuild запущен!"
printf "   Интерфейс:  ${B}http://localhost:$FRONTEND_PORT${N}\n"
printf "   API:        ${B}http://localhost:$BACKEND_PORT${N}\n"
printf "${G}════════════════════════════════════════════════${N}\n\n"
printf "${Y}Чтобы остановить — закрой это окно или нажми Ctrl+C.${N}\n\n"
say "Логи идут ниже (backend + frontend):"
echo "----------------------------------------------------------------"

# показываем живые логи и держим окно открытым; Ctrl+C -> cleanup
touch "$LOGS/backend.log" "$LOGS/frontend.log"
tail -n 0 -f "$LOGS/backend.log" "$LOGS/frontend.log" &
TAIL_PID=$!

# ждём, пока живы сервисы
while true; do
  if [ -n "$BACKEND_PID" ]  && ! kill -0 "$BACKEND_PID"  2>/dev/null; then warn "Backend остановился."; break; fi
  if [ -n "$FRONTEND_PID" ] && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then warn "Frontend остановился."; break; fi
  sleep 2
done

kill "$TAIL_PID" 2>/dev/null
cleanup
