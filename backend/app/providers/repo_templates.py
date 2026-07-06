"""Generated-repo templates for the three MVP project types (spec §14)."""


def detect_project_type(brief: str, requested: str = "auto") -> str:
    if requested and requested != "auto":
        return requested
    b = brief.lower()
    if any(k in b for k in ("crm", "заявк", "клиентская база", "lead")):
        return "mini_crm"
    if any(k in b for k in ("telegram", "телеграм", "бот", "bot")):
        return "telegram_bot"
    if any(k in b for k in ("кальку", "calculator", "стоимост", "расчет", "расчёт")):
        return "python_utility"
    return "python_utility"


def generate_repo(project_type: str, title: str, brief: str) -> dict[str, str]:
    if project_type == "mini_crm":
        return _mini_crm(title, brief)
    if project_type == "telegram_bot":
        return _telegram_bot(title, brief)
    return _python_utility(title, brief)


def _python_utility(title: str, brief: str) -> dict[str, str]:
    return {
        "README.md": f"# {title}\n\nService price calculator (CLI).\n\n"
                     "```bash\npython main.py --help\n```\n",
        "requirements.txt": "",
        ".env.example": "# no secrets needed for the CLI version\n",
        "formulas.md": "# Pricing formulas\n\nprice = base_rate * size_factor + sum(options)\n",
        "main.py": '''"""Car wash price calculator CLI."""
import argparse

BASE = {"sedan": 1500, "suv": 2000, "minivan": 2500}
OPTIONS = {"wax": 500, "interior": 1200, "engine": 900}


def price(car: str, options: list[str]) -> int:
    return BASE[car] + sum(OPTIONS[o] for o in options)


def main() -> None:
    p = argparse.ArgumentParser(description="Car wash price calculator")
    p.add_argument("--car", choices=sorted(BASE), default="sedan")
    p.add_argument("--option", action="append", choices=sorted(OPTIONS), default=[])
    args = p.parse_args()
    print(f"Total: {price(args.car, args.option)} KZT")


if __name__ == "__main__":
    main()
''',
        "src/__init__.py": "",
    }


def _telegram_bot(title: str, brief: str) -> dict[str, str]:
    return {
        "README.md": f"# {title}\n\nTelegram booking bot skeleton (aiogram).\n\n"
                     "```bash\npip install -r requirements.txt\ncp .env.example .env  # set BOT_TOKEN\npython bot.py\n```\n",
        "requirements.txt": "aiogram>=3.4\naiosqlite>=0.19\npython-dotenv>=1.0\n",
        ".env.example": "BOT_TOKEN=your-telegram-bot-token\nDATABASE_PATH=bookings.db\n",
        "bot.py": '''"""Booking bot skeleton: /start, /book, /my."""
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv

from storage import init_db, add_booking, list_bookings

load_dotenv()
dp = Dispatcher()


@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("Привет! /book <дата> <время> — записаться, /my — мои записи.")


@dp.message(Command("book"))
async def book(m: Message):
    parts = (m.text or "").split(maxsplit=2)
    slot = parts[1] if len(parts) > 1 else "завтра 10:00"
    await add_booking(m.from_user.id, slot)
    await m.answer(f"Записал: {slot}")


@dp.message(Command("my"))
async def my(m: Message):
    rows = await list_bookings(m.from_user.id)
    await m.answer("\\n".join(r[0] for r in rows) or "Записей нет")


async def main():
    await init_db()
    bot = Bot(os.environ["BOT_TOKEN"])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
''',
        "storage.py": '''import os

import aiosqlite

DB = os.getenv("DATABASE_PATH", "bookings.db")


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS bookings "
                         "(id INTEGER PRIMARY KEY, user_id INTEGER, slot TEXT)")
        await db.commit()


async def add_booking(user_id: int, slot: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO bookings (user_id, slot) VALUES (?, ?)", (user_id, slot))
        await db.commit()


async def list_bookings(user_id: int):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT slot FROM bookings WHERE user_id = ?", (user_id,))
        return await cur.fetchall()
''',
    }


def _mini_crm(title: str, brief: str) -> dict[str, str]:
    return {
        "README.md": f"# {title}\n\nMini-CRM skeleton (FastAPI + SQLite + static HTML).\n\n"
                     "```bash\npip install -r requirements.txt\nuvicorn app:app --reload\n```\n\n"
                     "Open http://127.0.0.1:8000\n",
        "requirements.txt": "fastapi>=0.110\nuvicorn>=0.29\n",
        ".env.example": "DATABASE_PATH=crm.db\n",
        "app.py": '''"""Mini-CRM: leads CRUD + static UI."""
import os
import sqlite3

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

DB = os.getenv("DATABASE_PATH", "crm.db")
app = FastAPI(title="Mini CRM")


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS leads "
                 "(id INTEGER PRIMARY KEY, name TEXT, phone TEXT, status TEXT DEFAULT 'new')")
    return conn


class Lead(BaseModel):
    name: str
    phone: str
    status: str = "new"


@app.get("/", response_class=HTMLResponse)
def index():
    return open("index.html", encoding="utf-8").read()


@app.get("/api/leads")
def list_leads():
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM leads")]


@app.post("/api/leads")
def create_lead(lead: Lead):
    with db() as conn:
        cur = conn.execute("INSERT INTO leads (name, phone, status) VALUES (?, ?, ?)",
                           (lead.name, lead.phone, lead.status))
        return {"id": cur.lastrowid}


@app.put("/api/leads/{lead_id}")
def update_lead(lead_id: int, lead: Lead):
    with db() as conn:
        conn.execute("UPDATE leads SET name=?, phone=?, status=? WHERE id=?",
                     (lead.name, lead.phone, lead.status, lead_id))
        return {"ok": True}
''',
        "index.html": '''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>Mini CRM</title></head>
<body>
<h1>Заявки</h1>
<form id="f"><input name="name" placeholder="Имя" required>
<input name="phone" placeholder="Телефон" required>
<button>Добавить</button></form>
<ul id="list"></ul>
<script>
async function load() {
  const leads = await (await fetch('/api/leads')).json();
  list.innerHTML = leads.map(l => `<li>${l.name} — ${l.phone} [${l.status}]`).join('');
}
f.onsubmit = async e => {
  e.preventDefault();
  await fetch('/api/leads', {method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: f.name.value, phone: f.phone.value})});
  f.reset(); load();
};
load();
</script>
</body></html>
''',
    }
