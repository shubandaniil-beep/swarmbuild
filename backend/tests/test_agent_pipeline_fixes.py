"""Pipeline fixes: real models must receive working context, tool-config
mismatches must be survived, mock fallback must never bill the client, and a
single cheap model must build through verified micro-tasks."""
import pytest

from app.database import SessionLocal
from app.models import Project, ProjectPhase, User
from app.providers.base import ProviderHTTPError, ProviderResult
from app.providers.openai_provider import (
    OpenAICompatibleProvider,
    ToolUseMismatchError,
    _message_text,
)
from app.services import agent_runner, micro_build, phase_orchestrator
from app.services.project_intake import create_project, workspace_path


def _make_user(email: str) -> str:
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(email=email, role="user", password_hash="x",
                     token_balance=1_000_000, lifetime_tokens_granted=1_000_000,
                     lifetime_tokens_spent=0, demo_generations_remaining=1)
            db.add(u)
            db.commit()
        return u.id
    finally:
        db.close()


def _make_project(uid: str, title: str):
    db = SessionLocal()
    try:
        p = create_project(db, title, "Нужен рабочий Python-скрипт.", 1, ["mvp"],
                           "code_project", "code", "non_technical", "", user_id=uid)
        db.commit()
        return p.id
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# context injection: real providers must SEE issues/gates/repo listing        #
# --------------------------------------------------------------------------- #

class _CaptureProvider:
    def __init__(self):
        self.system = ""
        self.user = ""

    def complete(self, system, user, context=None):
        self.system, self.user = system, user
        return ProviderResult(text="ok", input_tokens=10, output_tokens=5)


def test_extra_context_reaches_real_provider_prompt(client, monkeypatch):
    capture = _CaptureProvider()
    monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": capture)
    uid = _make_user("ctx-user@example.com")
    pid = _make_project(uid, "Context test")
    db = SessionLocal()
    try:
        project = db.get(Project, pid)
        assignment = {"model_id": "mock_fast", "model_name": "mock-swarm-v1",
                      "provider": "mock", "mandate": "repairer", "agent_slot": 1,
                      "access": ["repo"]}
        extra = {
            "open_issues": [{"id": "ISSUE-9", "title": "ISSUE-9: сломан импорт",
                             "severity": "major",
                             "description": "main.py импортирует pandas без зависимости",
                             "suggested_fix": "добавить pandas в requirements.txt"}],
            "gate_failures": [{"name": "imports_covered",
                               "detail": "imports not covered: pandas"}],
            "repo_files": ["main.py", "README.md"],
            "spec_excerpt": "Приложение должно запускаться командой python main.py",
        }
        agent_runner.run_agent(db, workspace_path(pid), project, "repair_sprint",
                               assignment, "agent-1", extra)
    finally:
        db.close()

    # the whole working context is in the actual prompt, not a side channel
    assert "ISSUE-9: сломан импорт" in capture.user
    assert "добавить pandas в requirements.txt" in capture.user
    assert "imports_covered" in capture.user
    assert "main.py" in capture.user
    assert "python main.py" in capture.user


# --------------------------------------------------------------------------- #
# tool-config compatibility                                                   #
# --------------------------------------------------------------------------- #

def _provider():
    return OpenAICompatibleProvider(
        {"provider": "gemini", "model_name": "gemini-2.5-flash"},
        "https://example.invalid/openai", "k")


def test_tool_choice_error_is_retried_with_no_tools_nudge(monkeypatch):
    p = _provider()
    calls = []

    def scripted(system, user):
        calls.append(system)
        if len(calls) == 1:
            raise RuntimeError(
                "provider error: Tool choice is none, but model called a tool.")
        return ProviderResult(text="plain text now", input_tokens=5, output_tokens=5)

    monkeypatch.setattr(p, "_complete_once", scripted)
    result = p.complete("system prompt", "user prompt")
    assert result.text == "plain text now"
    assert len(calls) == 2
    assert "no tools" in calls[1].lower()


def test_tool_calls_only_choice_is_retried(monkeypatch):
    p = _provider()
    calls = []

    def scripted(system, user):
        calls.append(system)
        if len(calls) == 1:
            raise ToolUseMismatchError("model attempted a tool call")
        return ProviderResult(text="ok", input_tokens=5, output_tokens=5)

    monkeypatch.setattr(p, "_complete_once", scripted)
    assert p.complete("s", "u").text == "ok"
    assert len(calls) == 2


def test_message_with_tool_calls_raises_mismatch():
    with pytest.raises(ToolUseMismatchError):
        _message_text({"content": None, "tool_calls": [{"id": "x"}]})


def test_unrelated_errors_are_not_retried(monkeypatch):
    p = _provider()
    calls = []

    def scripted(system, user):
        calls.append(system)
        raise ProviderHTTPError("provider HTTP 429: rate limit", status_code=429)

    monkeypatch.setattr(p, "_complete_once", scripted)
    with pytest.raises(ProviderHTTPError):
        p.complete("s", "u")
    assert len(calls) == 1  # rate limits belong to the key pool, not this retry


# --------------------------------------------------------------------------- #
# mock fallback is never billable progress                                    #
# --------------------------------------------------------------------------- #

def test_mock_fallback_phase_is_unbilled_and_not_released(client, monkeypatch):
    def fake_run_agent(db, ws, project, phase_key, assignment, agent_db_id,
                       extra_context=None, retry=True):
        result = ProviderResult(
            text="# Черновик от mock\n\nРеальная модель недоступна.",
            input_tokens=50, output_tokens=50, status="mock_fallback",
            files={"main.py": "print('mock draft')\n"})
        return result, 0.01

    monkeypatch.setattr(phase_orchestrator, "run_agent", fake_run_agent)
    uid = _make_user("fallback-user@example.com")
    pid = _make_project(uid, "Fallback honesty")

    db = SessionLocal()
    try:
        phase_orchestrator.run_project(db, pid)
    finally:
        db.close()

    db = SessionLocal()
    try:
        project = db.get(Project, pid)
        # a pipeline carried entirely by mock fallback is a provider failure,
        # never a client-facing deliverable
        assert project.status == "needs_internal_repair", project.status
        assert project.release_decision != "release"
        phases = db.query(ProjectPhase).filter(ProjectPhase.project_id == pid).all()
        assert all((p.credits_charged or 0) == 0 for p in phases), \
            [(p.phase_key, p.credits_charged) for p in phases]
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# micro-task build                                                            #
# --------------------------------------------------------------------------- #

def _assignment(cost_level="low", provider="gemini", model="gemini-2.5-flash"):
    card = {"id": "m1", "provider": provider, "provider_id": "prov-1",
            "model_name": model, "cost_level": cost_level,
            "input_cost_per_1m": 0.1, "output_cost_per_1m": 0.4}
    return {"model_id": "m1", "model_name": model, "provider": provider,
            "mandate": "builder", "agent_slot": 1, "access": ["repo"], "card": card}


def test_should_microtask_when_the_code_author_is_weak(client):
    db = SessionLocal()
    try:
        # a single weak model authoring the build → decompose
        assert micro_build.should_microtask(db, [_assignment()]) is True
        # a weak author still decomposes even alongside other weak models —
        # a pool of small models one-shotting in parallel is exactly what
        # produces thin/garbage output.
        assert micro_build.should_microtask(
            db, [_assignment(), _assignment(model="other-weak")]) is True
        # a strong author (capability routing put a medium/high model on
        # `builder`) keeps the normal swarm build
        assert micro_build.should_microtask(db, [_assignment(cost_level="high")]) is False
        assert micro_build.should_microtask(db, [_assignment(cost_level="medium")]) is False
        # mock builds deterministic repos already
        assert micro_build.should_microtask(db, [_assignment(provider="mock")]) is False
    finally:
        db.close()


class _ScriptedProvider:
    def __init__(self, *texts):
        self.texts = list(texts)
        self.calls = 0

    def complete(self, system, user, context=None):
        self.calls += 1
        text = self.texts[min(self.calls - 1, len(self.texts) - 1)]
        return ProviderResult(text=text, input_tokens=20, output_tokens=20)


def test_micro_build_plans_generates_checks_and_repairs(client, monkeypatch):
    plan = ('План:\n```json\n[{"path": "main.py", "purpose": "entry point"},'
            '{"path": "README.md", "purpose": "docs"}]\n```\n')
    broken_main = "=== FILE: main.py ===\n```python\ndef main(:\n    broken\n```\n"
    fixed_main = ("=== FILE: main.py ===\n```python\ndef main():\n"
                  "    print('ok')\n\nmain()\n```\n")
    readme = "=== FILE: README.md ===\n```markdown\n# App\n\npython main.py\n```\n"
    stub = _ScriptedProvider(plan, broken_main, fixed_main, readme)
    monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": stub)

    uid = _make_user("micro-user@example.com")
    pid = _make_project(uid, "Micro build")
    db = SessionLocal()
    try:
        project = db.get(Project, pid)
        # provider "mock" routes _call_with_pool straight to our scripted stub
        assignment = _assignment(provider="mock")
        entries = micro_build.run_micro_build(
            db, workspace_path(pid), project, "build_sprint", assignment,
            "agent-1", budget_left_usd=0)
    finally:
        db.close()

    assert entries is not None
    assert stub.calls == 4  # plan + main.py + repair + README.md
    # the final applied set contains the repaired file, not the broken one
    merged: dict[str, str] = {}
    for _, _, result, _ in entries:
        merged.update(result.files)
    assert "def main():" in merged["main.py"]
    assert "README.md" in merged


def test_micro_build_falls_back_when_plan_is_garbage(client, monkeypatch):
    stub = _ScriptedProvider("Никакого JSON тут нет, просто проза.")
    monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": stub)
    uid = _make_user("micro-user2@example.com")
    pid = _make_project(uid, "Micro build no plan")
    db = SessionLocal()
    try:
        project = db.get(Project, pid)
        entries = micro_build.run_micro_build(
            db, workspace_path(pid), project, "build_sprint",
            _assignment(provider="mock"), "agent-1", budget_left_usd=0)
    finally:
        db.close()
    assert entries is None  # orchestrator falls back to the one-shot build
