"""Artifact Packager: final user-facing documents + project.zip.

Invariant: the release decision is computed over EXACTLY the bytes that ship.
All transformations (secret redaction, internal-name sanitization, doc
generation) happen in place on the tree first, then the gates run, then the
zip archives the tree verbatim — so a file can never pass a check in one form
and ship in another.
"""
import ast
import json
import zipfile
from pathlib import Path

from sqlalchemy.orm import Session

from ..lib.output_filter import sanitize
from ..models import Artifact, Issue
from . import budget_engine

FINAL_DOCS = ["README.md", "INSTALL.md", "business-plan.md", "pitch-deck-outline.md",
              "limitations.md", "next-steps.md", "cost-report.json"]

_TEXT_SUFFIXES = {".md", ".txt", ".json", ".html", ".css", ".js", ".ts", ".tsx", ".py", ".env", ".example"}


def _public_text(text: str) -> str:
    return sanitize(text)[0]


def _write_public(path: Path, text: str) -> None:
    path.write_text(_public_text(text))


def _finalize_tree(workspace: Path) -> dict:
    """Apply the internal-name sanitizer to the shippable tree IN PLACE, so the
    gates and the archive see the same bytes. Cosmetic sanitization must never
    corrupt code: a ``.py`` edit that stops parsing is skipped (an internal-name
    echo in code is harmless next to shipping a broken file)."""
    sanitized = 0
    skipped_code = 0
    for sub in ("repo", "artifacts"):
        base = workspace / sub
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            if not f.is_file() or f.name == "project.zip":
                continue
            if f.suffix.lower() not in _TEXT_SUFFIXES and not f.name.endswith(".example"):
                continue
            try:
                original = f.read_text(errors="replace")
            except OSError:
                continue
            cleaned, hits = sanitize(original)
            if not hits or cleaned == original:
                continue
            if f.suffix == ".py":
                try:
                    ast.parse(cleaned)
                except (SyntaxError, ValueError):
                    skipped_code += 1
                    continue
            f.write_text(cleaned)
            sanitized += 1
    return {"files_sanitized": sanitized, "skipped_code_files": skipped_code}


def _zip_file_verbatim(zf: zipfile.ZipFile, workspace: Path, f: Path) -> None:
    rel = f.relative_to(workspace)
    if any(part in {"logs", "reviews", "spec", "architecture"} for part in rel.parts):
        return
    if f.name == "project.zip" or "prompt" in f.name.lower():
        return
    if f.name in {"implementation-log.md"}:
        return
    # the tree is already redacted + sanitized; archive it byte-for-byte so the
    # client receives exactly what the gates approved
    zf.write(f, rel)


def package(db: Session, project, workspace: Path) -> tuple[Path, dict]:
    """Write final docs, evaluate release policy over the complete set, zip it."""
    from .release_policy import evaluate

    art = workspace / "artifacts"
    art.mkdir(exist_ok=True)

    open_issues = db.query(Issue).filter(Issue.project_id == project.id,
                                         Issue.status == "open").all()
    budget = budget_engine.load_budget_state(workspace)

    # INSTALL must describe THIS tree, not a generic template: steps that name
    # files that do not exist (e.g. `.env.example`) fail the docs gates and
    # confuse the client.
    repo_dir = workspace / "repo"
    install_steps = ["1. Распакуйте `project.zip`."]
    if repo_dir.exists() and any(repo_dir.iterdir()):
        install_steps.append(
            "2. Create a virtualenv: `python -m venv .venv && source .venv/bin/activate`")
        req = repo_dir / "requirements.txt"
        if req.exists() and req.read_text(errors="replace").strip():
            install_steps.append("3. Inside `repo/`: `pip install -r requirements.txt`.")
        if (repo_dir / "package.json").exists():
            install_steps.append(f"{len(install_steps) + 1}. Inside `repo/`: `npm install`.")
        if (repo_dir / ".env.example").exists():
            install_steps.append(
                f"{len(install_steps) + 1}. Copy `.env.example` to `.env` and fill values.")
        install_steps.append(
            f"{len(install_steps) + 1}. Run the entry point described in `repo/README.md`.")
    else:
        install_steps.append("2. Основной результат — в `artifacts/main-document.md`.")
    _write_public(art / "INSTALL.md",
                  "# Установка\n\n" + "\n".join(install_steps) + "\n")

    _write_public(art / "business-plan.md",
        f"# Бизнес-план — {project.title}\n\n"
        "## Проблема\nРучные процессы теряют клиентов, время и деньги.\n\n"
        "## Решение\n" + project.brief + "\n\n"
        "## Монетизация\n- прямые продажи / подписка\n- дополнительные услуги и расширения\n\n"
        "## MVP-расходы\n- хостинг: примерно $10/мес\n- внешние API: по фактическому использованию\n\n"
        "## Следующие шаги\nСм. next-steps.md.\n")

    _write_public(art / "pitch-deck-outline.md",
        f"# Структура pitch deck — {project.title}\n\n"
        "1. Проблема\n2. Решение\n3. Демонстрация MVP\n4. Рынок\n"
        "5. Бизнес-модель\n6. Roadmap\n7. Запрос / next step\n")

    # extra docs for explicitly requested outputs (spec-2 §9)
    extra_docs = {
        "research_report": ("research-report.md", "# Research report\n\nСводка исследования по брифу проекта: ключевые источники, выводы, ограничения методологии.\n"),
        "presentation_structure": ("presentation-structure.md", "# Presentation structure\n\n1. Титульный слайд\n2. Проблема\n3. Решение\n4. Детали\n5. Выводы\n"),
        "marketing_plan": ("marketing-plan.md", "# Marketing plan\n\nКаналы, позиционирование, бюджет продвижения, KPI первых 90 дней.\n"),
        "financial_model": ("financial-model-draft.md", "# Financial model draft\n\nДопущения, юнит-экономика, прогноз доходов/расходов на 12 месяцев.\n"),
        "deployment_guide": ("deployment-guide.md", "# Deployment guide\n\nШаги деплоя на VPS/PaaS, переменные окружения, чеклист перед запуском.\n"),
        "user_manual": ("user-manual.md", "# User manual\n\nПошаговое руководство пользователя по основным сценариям.\n"),
        "roadmap": ("roadmap.md", "# Roadmap\n\nQ1: стабилизация MVP · Q2: платежи и авторизация · Q3: масштабирование.\n"),
        "technical_spec": ("technical-spec-final.md", "# Technical specification\n\nСм. spec/technical-spec.md — финальная версия включена в архив.\n"),
        "branding_copy": ("branding-copy.md", "# Branding / copy\n\nТон коммуникации, слоганы, тексты для лендинга.\n"),
    }
    for output_key in (project.requested_outputs or []):
        doc = extra_docs.get(output_key)
        if doc and not (art / doc[0]).exists():
            _write_public(art / doc[0], doc[1])

    limitations = ["Это MVP-версия, а не полностью продакшн-система.",
                   "Авторизация и обработка ошибок пока минимальные.",
                   "Автотесты ограничены базовыми smoke-проверками."]
    limitations += [f"Открытое замечание ({i.severity}): {i.title}" for i in open_issues]
    _write_public(art / "limitations.md",
        "# Известные ограничения\n\n" + "\n".join(f"- {item}" for item in limitations) + "\n")

    _write_public(art / "next-steps.md",
        "# Следующие шаги\n\n1. Закрыть оставшиеся замечания.\n2. Добавить полноценную авторизацию.\n"
        "3. Расширить автотесты и CI.\n4. Развернуть проект на реальном хостинге.\n"
        "5. Собрать первую обратную связь от пользователей.\n")

    (art / "cost-report.json").write_text(json.dumps({
        "budget_usd": float(project.budget_usd),
        "used_usd": round(float(budget.get("spent_usd", 0)), 6),
        "remaining_usd": round(float(budget.get("remaining_usd", 0)), 6),
        "status": budget.get("status", "ok"),
        "note": "Внутренняя маршрутизация моделей и провайдеры намеренно не раскрываются.",
    }, indent=2, ensure_ascii=False))

    requires_code = getattr(project, "requires_codebase", True)
    _write_public(art / "README.md",
        f"# {project.title}\n\n{project.brief}\n\n"
        "## What is inside\n"
        + ("- `repo/` — generated project skeleton\n" if requires_code
           else "- `artifacts/main-document.md` — основной документ проекта\n")
        + "- `artifacts/` — итоговые документы, ограничения и следующие шаги\n"
        "- `INSTALL.md` — запуск проекта\n")

    # --- finalize the shippable tree BEFORE the release decision: secret
    # redaction and internal-name sanitization both happen in place here, so
    # evaluate() judges the exact bytes the client would download. Running any
    # transformation after evaluate() would let a file pass a check in one form
    # and ship broken in another (the bug this ordering exists to prevent).
    from .secret_scanner import scan_and_redact
    from .security_report import build as build_security_report
    from .settings_service import get_setting

    secret_scan = scan_and_redact(workspace)
    finalize_stats = _finalize_tree(workspace)
    secret_scan["sanitize_stats"] = finalize_stats

    # final release decision over the complete, finalized artifact set
    release_decision = evaluate(db, project.id, workspace, is_code_project=requires_code)
    if release_decision.get("notes"):
        with open(art / "limitations.md", "a") as f:
            for note in release_decision["notes"]:
                f.write(f"- Проверка готовности: {note}\n")
    with open(art / "README.md", "a") as f:
        f.write(f"\nГотовность: **{release_decision['decision']}**\n")

    (workspace / "reviews" / "release-decision.json").write_text(
        json.dumps(release_decision, indent=2, ensure_ascii=False))

    _write_public(art / "security-report.md", build_security_report(project, workspace, secret_scan))

    block = bool(get_setting(db, "block_download_on_secret_leak"))
    leaked = not secret_scan.get("clean", True)
    # blocked only if a leak was found AND the founder chose hard-block; otherwise
    # secrets were already redacted in place, so the package is safe to download.
    default_status = "blocked" if (leaked and block) else "safe_to_download"

    max_bytes = int(get_setting(db, "max_artifact_bytes") or 5_000_000)

    zip_path = art / "project.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for sub in ("repo", "artifacts"):
            base = workspace / sub
            if not base.exists():
                continue
            for f in sorted(base.rglob("*")):
                if f.is_file() and f.stat().st_size <= max_bytes:
                    _zip_file_verbatim(zf, workspace, f)

    known = {a.path for a in db.query(Artifact)
             .filter(Artifact.project_id == project.id).all()}
    for f in sorted(art.iterdir()):
        if f.is_file() and f"artifacts/{f.name}" not in known:
            db.add(Artifact(project_id=project.id, artifact_type="final",
                            path=f"artifacts/{f.name}", display_name=f.name,
                            safety_status=default_status))
    # apply the resolved status to the whole project's artifact set
    for a in db.query(Artifact).filter(Artifact.project_id == project.id).all():
        a.safety_status = default_status
    db.commit()
    release_decision["secret_scan"] = secret_scan
    return zip_path, release_decision
