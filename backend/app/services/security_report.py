"""Builds security-report.md for every completed/partial project."""
import json
from pathlib import Path


def _sandbox_summary(workspace: Path) -> list[dict]:
    log = workspace / "logs" / "command-runs.jsonl"
    if not log.exists():
        return []
    runs = []
    for line in log.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        runs.append({"command": r.get("command", ""), "status": r.get("status", ""),
                     "reason": r.get("reason")})
    return runs


def build(project, workspace: Path, secret_scan: dict) -> str:
    risk = getattr(project, "risk_level", "low")
    runs = _sandbox_summary(workspace)
    rejected = [r for r in runs if r["status"] == "rejected"]

    lines: list[str] = [f"# Security report — {project.title}", ""]

    # 1. secrets
    lines += ["## Проверка на секреты", ""]
    if secret_scan.get("clean", True):
        lines += ["- Секреты в артефактах не обнаружены.",
                  f"- Просканировано файлов: {secret_scan.get('files_scanned', 0)}.", ""]
    else:
        lines += [f"- Найдено и обезврежено: **{len(secret_scan.get('findings', []))}** файлов "
                  f"с секретами (типы: {', '.join(secret_scan.get('secret_types', [])) or '—'}).",
                  "- Значения заменены на плейсхолдеры `[REDACTED]`.",
                  "- Реальные `.env` конвертированы в `.env.example`.", ""]
        for f in secret_scan.get("findings", [])[:20]:
            lines.append(f"  - `{f['file']}` → {', '.join(f['types'])}")
        lines.append("")
    broken = secret_scan.get("syntax_broken_by_redaction", [])
    if broken:
        lines += ["- ⚠ Redaction затронула синтаксис следующих файлов — релиз "
                  "блокируется до их починки:", ""]
        lines += [f"  - `{rel}`" for rel in broken[:10]]
        lines.append("")

    # 2. sandbox
    lines += ["## Sandbox-команды", ""]
    if not runs:
        lines += ["- Команды в песочнице не запускались (только синтаксический разбор).", ""]
    else:
        lines.append(f"- Всего запусков: {len(runs)}; отклонено политикой: {len(rejected)}.")
        for r in runs[:20]:
            tail = f" — {r['reason']}" if r.get("reason") else ""
            lines.append(f"  - `{r['command']}` → {r['status']}{tail}")
        lines.append("")

    # 3. prompt injection
    lines += ["## Риск prompt-injection", "",
              f"- Уровень риска брифа: **{risk}**.",
              ("- Обнаружены подозрительные инструкции — доступ инструментов и сеть были ограничены."
               if risk in ("medium", "high")
               else "- Подозрительных инструкций не обнаружено."), ""]

    # 4/5. known limitations + production readiness
    lines += ["## Известные ограничения безопасности", "",
              "- Это сгенерированный MVP, а не проверенная продакшн-система.",
              "- Авторизация, валидация ввода и обработка ошибок — минимальные.",
              "- Перед публикацией проведите ручной security-review.", "",
              "## Готовность к продакшену — предупреждения", "",
              "- Не разворачивайте с дефолтными секретами.",
              "- Задайте реальные значения из `.env.example` через секрет-менеджер.",
              "- Включите HTTPS, бэкапы и мониторинг.", "",
              "## Рекомендуемые следующие шаги по безопасности", "",
              "1. Провести зависимость-аудит (`pip audit` / `npm audit`).",
              "2. Добавить аутентификацию и проверки прав.",
              "3. Настроить rate-limiting и логирование.",
              "4. Хранить секреты в vault, а не в коде.", ""]

    return "\n".join(lines)
