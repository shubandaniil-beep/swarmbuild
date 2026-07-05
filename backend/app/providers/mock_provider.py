"""Deterministic mock provider — proves the rotating-swarm pipeline without API keys.

Output depends on (phase, mandate, project brief), so different agents in the
same phase produce distinct artifacts and the demo flow is reproducible.
"""
import json

from .base import BaseProvider, ProviderResult
from .repo_templates import generate_repo


class MockProvider(BaseProvider):
    def complete(self, system: str, user: str, context: dict | None = None) -> ProviderResult:
        ctx = context or {}
        self._ctx_requires_codebase = ctx.get("requires_codebase", True)
        self._ctx_outputs = ctx.get("requested_outputs", [])
        self._ctx_level = ctx.get("technical_level", "non_technical")
        phase = ctx.get("phase", "unknown")
        mandate = ctx.get("mandate", "lead")
        title = ctx.get("title", "Project")
        brief = ctx.get("brief", "")
        project_type = ctx.get("project_type", "generic")
        agent_name = ctx.get("agent_name", "agent")
        issues = ctx.get("open_issues", [])

        files: dict[str, str] = {}
        handler = getattr(self, f"_{mandate}", self._generic)
        text = handler(phase, title, brief, project_type, agent_name, issues, files)

        input_tokens = max(len(system + user) // 4, 200)
        output_tokens = max(len(text) // 4, 150)
        return ProviderResult(text=text, input_tokens=input_tokens,
                              output_tokens=output_tokens, files=files)

    # --- mandate handlers -------------------------------------------------

    def _lead(self, phase, title, brief, ptype, agent, issues, files):
        if phase == "swarm_understanding":
            return (f"# Understanding — {agent}\n\n"
                    f"## Interpretation of «{title}»\n\n{brief}\n\n"
                    "## Key deliverables detected\n"
                    f"- project type: **{ptype}**\n"
                    "- working code skeleton\n- docs (README, INSTALL)\n"
                    "- business plan + pitch outline\n\n"
                    "## Assumptions\n- Single-tenant MVP\n- Russian-speaking end users\n"
                    "- No payment processing in v1\n")
        if phase == "spec_war":
            return (f"# Technical Spec — {title}\n\n## Scope\n{brief}\n\n"
                    "## Functional requirements\n"
                    "1. Core entity CRUD\n2. Simple UI or CLI entry point\n"
                    "3. Local persistence (SQLite/JSON)\n4. Setup in under 5 minutes\n\n"
                    "## Non-functional\n- Python 3.11+/Node 18+\n- No external paid services\n\n"
                    "## Acceptance criteria\n"
                    "- [ ] App starts with documented command\n"
                    "- [ ] Main flow works end-to-end\n"
                    "- [ ] README and INSTALL are accurate\n")
        if phase == "architecture_battle":
            return (f"# Architecture — {title}\n\n## Selected option: A (monolith-first)\n\n"
                    "```text\nclient → app layer → storage (SQLite/JSON)\n```\n\n"
                    "## Why\nSmallest surface that satisfies the spec; option B (services) "
                    "is overkill for the budget.\n\n## Risks\n- single point of failure\n"
                    "- no auth in MVP\n")
        if phase == "build_sprint":
            return "# Build lead notes\n\nCoordinated builders, merged outputs, resolved file conflicts.\n"
        return self._generic(phase, title, brief, ptype, agent, issues, files)

    def _critic(self, phase, title, brief, ptype, agent, issues, files):
        return (f"# Critique — phase {phase} — {agent}\n\n"
                "## Critical\n- (none found)\n\n"
                "## Major\n- Error handling is minimal; document as limitation\n"
                "- No automated tests beyond smoke check\n\n"
                "## Minor\n- Naming could be more consistent\n- README could add screenshots\n\n"
                "## Suggested fixes\nDocument the gaps in limitations.md and add a smoke test.\n")

    def _builder(self, phase, title, brief, ptype, agent, issues, files):
        if phase == "build_sprint":
            if not self._ctx_requires_codebase:
                return self._document_build(title, brief, agent)
            files.update(generate_repo(ptype, title, brief))
            return (f"# Implementation log — {agent}\n\n"
                    f"Generated `{ptype}` skeleton: {len(files)} files.\n\n"
                    "## Self-check\n- entry point present\n- README present\n"
                    "- .env.example present\n\n## Known issues\n"
                    "- No auth, no tests beyond smoke check.\n")
        if phase == "architecture_battle":
            return (f"# Architecture option B — {agent}\n\n"
                    "Split into API service + worker + static frontend.\n\n"
                    "Pros: scalable. Cons: 3x ops surface for an MVP. "
                    "Recommend only if budget > $150.\n")
        if phase == "swarm_understanding":
            return (f"# Understanding (independent) — {agent}\n\n"
                    f"Reading the brief literally: {brief[:200]}\n\n"
                    "Riskiest assumption: the user wants running code, not mockups. "
                    "Deliver the smallest runnable skeleton.\n")
        return self._generic(phase, title, brief, ptype, agent, issues, files)

    def _reviewer(self, phase, title, brief, ptype, agent, issues, files):
        if phase == "review_stop":
            found = [
                {"id": "ISSUE-001", "severity": "major",
                 "title": "Missing install instructions detail",
                 "description": "INSTALL steps do not mention virtualenv creation.",
                 "suggested_fix": "Add python -m venv step to INSTALL.md",
                 "assigned_to": None, "status": "open"},
                {"id": "ISSUE-002", "severity": "minor",
                 "title": "No .gitignore in generated repo",
                 "description": "Generated repo lacks .gitignore.",
                 "suggested_fix": "Add standard Python/Node .gitignore",
                 "assigned_to": None, "status": "open"},
            ]
            return ("# Review report — " + agent + "\n\n"
                    "Checked artifacts against spec and acceptance criteria.\n\n"
                    "```json\n" + json.dumps(found, indent=2, ensure_ascii=False) + "\n```\n")
        return (f"# Review — phase {phase} — {agent}\n\n"
                "Work matches the phase goal. No fake completion detected. "
                "Minor documentation gaps noted for the packager.\n")

    def _repairer(self, phase, title, brief, ptype, agent, issues, files):
        fixed = []
        for issue in issues:
            if issue.get("id") == "ISSUE-001" or "INSTALL" in issue.get("title", ""):
                files["INSTALL_PATCH.md"] = (
                    "## Extra install step\n\n```bash\npython -m venv .venv && "
                    "source .venv/bin/activate\n```\n")
            if issue.get("id") == "ISSUE-002" or "gitignore" in issue.get("title", "").lower():
                files[".gitignore"] = ".venv/\n__pycache__/\nnode_modules/\n.env\n*.db\n"
            fixed.append(issue.get("id", "?"))
        return (f"# Repair log — {agent}\n\nFixed issues: {', '.join(fixed) or 'none assigned'}.\n"
                "No unrelated parts were redesigned. Existing behavior preserved.\n")

    def _judge(self, phase, title, brief, ptype, agent, issues, files):
        decision = "APPROVE_WITH_WARNINGS" if phase in ("review_stop", "final_audit") else "APPROVE"
        return (f"# Judge decision — phase {phase} — {agent}\n\n"
                f"**Decision: {decision}**\n\n"
                "Exit criteria checked against produced artifacts. "
                "Warnings: minimal error handling, no automated test suite. "
                "These must be listed in limitations.md.\n")

    def _packager(self, phase, title, brief, ptype, agent, issues, files):
        return (f"# Packaging notes — {agent}\n\n"
                f"Assembled final artifacts for «{title}»: README, INSTALL, business plan, "
                "pitch outline, limitations, next steps, cost report, zip archive.\n")

    def _document_build(self, title, brief, agent):
        """Build sprint for non-code projects: structured document deliverable."""
        audience = {"non_technical": "заказчика без технического бэкграунда",
                    "student_academic": "академической аудитории",
                    "investor_pitch": "инвесторов",
                    "business_owner": "владельца бизнеса"}.get(
            self._ctx_level, "широкой аудитории")
        return (f"# {title} — основной документ\n\n"
                f"Подготовлено для {audience}.\n\n"
                f"## Введение\n{brief}\n\n"
                "## Основная часть\n"
                "1. Анализ задачи и контекста\n2. Ключевые выводы\n"
                "3. Предлагаемое решение / структура\n4. Обоснование\n\n"
                "## Заключение\nИтоги и рекомендации по следующим шагам.\n\n"
                f"— {agent}\n")

    def _generic(self, phase, title, brief, ptype, agent, issues, files):
        return f"# Output — {agent} — phase {phase}\n\nStructured contribution for «{title}».\n"
