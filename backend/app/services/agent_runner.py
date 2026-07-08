"""Agent Runner: assemble prompt, call provider, persist output + call log."""
import json
import logging
import random
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..lib.output_filter import sanitize
from ..lib.redact import redact_error
from ..models import AgentCall
from ..providers import get_provider
from ..providers.base import ProviderResult
from .settings_service import get_setting

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

logger = logging.getLogger("swarmbuild.ai")


class ProviderPoolError(RuntimeError):
    def __init__(self, message: str, route: dict):
        super().__init__(message)
        self.route = route


def _prompt(name: str) -> str:
    p = PROMPTS_DIR / f"{name}.md"
    return p.read_text() if p.exists() else ""


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "\n…[truncated]"


def _render_context_sections(extra: dict) -> str:
    """Serialize orchestrator-supplied working context into the user prompt.

    Real providers only ever see `system` + `user` — the `context` dict is
    consumed by the mock provider alone. Anything the reviewer/repairer must
    act on (open issues, failed gates, the actual repo listing, the spec) has
    to be rendered into the message, or production models fly blind.
    """
    sections: list[str] = []

    issues = extra.get("open_issues") or []
    if issues:
        lines = []
        for i in issues[:20]:
            lines.append(f"- [{i.get('severity', '?')}] {i.get('title', 'untitled')}")
            if i.get("description"):
                lines.append(f"  problem: {_clip(i['description'], 400)}")
            if i.get("suggested_fix"):
                lines.append(f"  suggested fix: {_clip(i['suggested_fix'], 300)}")
        sections.append("## Open issues — fix exactly these\n" + "\n".join(lines))

    gates = extra.get("gate_failures") or []
    if gates:
        lines = [f"- {g.get('name', '?')}: {_clip(g.get('detail', ''), 300)}" for g in gates[:12]]
        sections.append("## Failed deterministic checks (must pass before release)\n"
                        + "\n".join(lines))
    elif extra.get("build_gate_summary"):
        summary = extra["build_gate_summary"]
        sections.append("## Deterministic check summary\n"
                        f"passed: {summary.get('passed')}\nfailed: {summary.get('failed')}")

    repo_files = extra.get("repo_files") or []
    if repo_files:
        sections.append("## Current repo files\n" + "\n".join(f"- {f}" for f in repo_files[:80]))

    if extra.get("spec_excerpt"):
        sections.append("## Specification excerpt\n" + _clip(extra["spec_excerpt"], 2500))

    if extra.get("build_log_tail"):
        sections.append("## Recent build/check log\n" + _clip(extra["build_log_tail"], 1500))

    if extra.get("file_rules"):
        sections.append("## Integration contract\n" + _clip(extra["file_rules"], 3000))

    if extra.get("integration_plan"):
        sections.append("## Integration plan\n" + _clip(extra["integration_plan"], 2500))

    if extra.get("micro_task"):
        sections.append("## Current micro-task\n" + _clip(extra["micro_task"], 2500))

    # Full source contents for the ASSEMBLER (pre-capped by the orchestrator).
    source_files = extra.get("source_files") or {}
    if source_files:
        parts = [f"### {path}\n```\n{content}\n```"
                 for path, content in source_files.items()]
        sections.append("## Source files to fuse into ONE index.html (full contents)\n"
                        + "\n\n".join(parts))

    return ("\n\n" + "\n\n".join(sections)) if sections else ""


def _estimate_cost(card: dict, input_tokens: int, output_tokens: int) -> float:
    return round(
        input_tokens / 1_000_000 * card.get("input_cost_per_1m", 0)
        + output_tokens / 1_000_000 * card.get("output_cost_per_1m", 0),
        6,
    )


def _route_base(card: dict) -> dict:
    return {
        "provider_id": card.get("provider_id") or "",
        "provider_type": card.get("provider", "mock"),
        "provider_model_name": card.get("model_name", ""),
        "provider_key_id": "",
        "provider_key_mask": "",
        "route_error": "",
    }


def _cooldown_seconds(exc: Exception, message: str, attempt: int = 1) -> float:
    """How long to bench a key before retrying it after a retryable error.

    `attempt` is the number of consecutive transient failures seen on this call;
    it escalates the backoff for server/network faults (5s → 10s → 20s) so a key
    that keeps meeting a struggling upstream is not hammered."""
    from . import key_pool
    retry_after = float(getattr(exc, "retry_after", 0) or 0)
    if retry_after > 0:
        return min(retry_after + 1.0, 120.0)
    text = (message or "").lower()
    if "per-min" in text or "per minute" in text:
        return 61.0  # e.g. OpenRouter free-models-per-min: resets on the minute
    if key_pool.is_transient_server_error(text):
        return min(5.0 * 2 ** max(0, attempt - 1), 20.0)  # 5xx/network: 5,10,20…
    return 30.0


def _call_with_pool(db: Session, card: dict, system: str, user: str,
                    context: dict) -> tuple[ProviderResult, dict]:
    """Complete one call, rotating across the provider's key pool.

    Keys are tried least-recently-used first and failed over key-by-key on
    error. `provider_retry_attempts` bounds the number of *real* provider
    attempts (a transient 503/overload counts, but idle waiting for a cooling
    key does not). Rate-limited or transiently-failed keys go into a short,
    escalating cooldown instead of a permanent error; when every key is cooling
    the call waits for the earliest window — bounded in total by
    `provider_retry_max_wait_seconds` — then retries. Raises only when the
    attempt budget is spent, the wait budget is spent, or the errors are
    non-transient (bad key / client error), leaving model failover to decide.
    """
    from ..models import Provider
    from . import key_pool

    route = _route_base(card)
    if card.get("provider") == "mock":
        return get_provider(card, "").complete(system, user, context), route

    provider_id = card.get("provider_id")
    if not provider_id:
        raise RuntimeError(f"provider id is missing for model {card.get('model_name')}")

    provider = db.get(Provider, provider_id)
    if not provider:
        raise RuntimeError(f"provider {provider_id} was not found")

    attempts = max(1, int(get_setting(db, "provider_retry_attempts") or 3))
    wait_budget = max(1.0, float(get_setting(db, "provider_retry_max_wait_seconds") or 70))
    model_name = card.get("model_name", "")

    last_exc: Exception | None = None
    last_error = ""
    tries = 0            # real provider attempts spent (idle waiting is free)
    transient_fails = 0  # consecutive transient failures → escalating backoff
    while tries < attempts:
        records = key_pool.ordered_key_records(db, provider)
        if not records:
            raise RuntimeError(f"{provider.name}: no usable API keys configured")
        now = datetime.now(UTC)
        ready = [r for r in records if not key_pool.is_cooling(r, now)]

        if not ready:
            # Every key is cooling: wait for the earliest window to reopen,
            # bounded by the total wait budget. Waiting is not an "attempt".
            cooldowns = [r["cooldown_until"] for r in records if r["cooldown_until"]]
            if not cooldowns or wait_budget <= 0:
                break
            wait = min(max((min(cooldowns) - now).total_seconds(), 1.0), wait_budget)
            wait_budget -= wait
            logger.info(
                "provider=%s model=%s: all %d key(s) cooling, waiting %.0fs "
                "(tries %d/%d, wait_budget %.0fs left)", provider.provider_type,
                model_name, len(records), wait, tries, attempts, wait_budget)
            time.sleep(wait + random.uniform(0.1, 1.0))
            continue

        transient_seen = False
        for record in ready:
            if tries >= attempts:
                break
            tries += 1
            route = _route_base(card) | {
                "provider_key_id": record["id"],
                "provider_key_mask": record["mask"],
            }
            started = time.monotonic()
            try:
                result = get_provider(card, record["plaintext"]).complete(system, user, context)
                key_pool.mark_ok(db, record["id"])
                logger.info(
                    "provider=%s model=%s key=%s status=ok duration=%.1fs tokens=%d/%d",
                    provider.provider_type, model_name, record["mask"],
                    time.monotonic() - started, result.input_tokens, result.output_tokens)
                return result, route
            except Exception as exc:  # try the next key in the pool
                last_exc = exc
                last_error = redact_error(exc)
                duration = time.monotonic() - started
                if key_pool.is_permanent_key_error(last_error):
                    key_pool.mark_error(db, record["id"], last_error)
                    logger.warning(
                        "provider=%s model=%s key=%s status=key_disabled duration=%.1fs error=%s",
                        provider.provider_type, model_name, record["mask"], duration, last_error)
                elif key_pool.is_transient_key_error(last_error):
                    transient_fails += 1
                    cooldown = _cooldown_seconds(exc, last_error, transient_fails)
                    key_pool.mark_cooldown(db, record["id"], last_error, cooldown)
                    transient_seen = True
                    logger.warning(
                        "provider=%s model=%s key=%s status=rate_limited cooldown=%.0fs error=%s",
                        provider.provider_type, model_name, record["mask"], cooldown, last_error)
                else:
                    logger.warning(
                        "provider=%s model=%s key=%s status=error duration=%.1fs error=%s",
                        provider.provider_type, model_name, record["mask"], duration, last_error)
        if not transient_seen:
            break  # waiting will not heal these errors — let model failover take over

    route["route_error"] = last_error
    logger.error("provider=%s model=%s: pool exhausted after %d attempt(s); last error: %s",
                 provider.provider_type, model_name, tries, last_error)
    raise ProviderPoolError(
        f"{provider.name}: all usable keys failed; last error: {last_error}",
        route,
    ) from last_exc


def run_agent(db: Session, workspace: Path, project, phase_key: str,
              assignment: dict, agent_db_id: str, extra_context: dict | None = None,
              retry: bool = True) -> tuple[ProviderResult, float]:
    """Run one agent call; returns (result, estimated_cost_usd)."""
    card = assignment.get("card") or {
        "id": assignment["model_id"], "provider": assignment.get("provider", "mock"),
        "provider_id": None, "model_name": assignment.get("model_name", "mock"),
        "cost_level": "free", "input_cost_per_1m": 0.01, "output_cost_per_1m": 0.02,
    }
    mandate = assignment["mandate"]
    from . import personality
    personality_mode = personality.normalize(getattr(project, "personality_mode", None))
    build_style = personality.directive_for(personality_mode)
    system = _prompt("base_agent") + "\n\n" + _prompt(mandate) + "\n\nBuild style: " + build_style
    # Inject vetted UI recipes so weak-UI models compose from patterns instead of
    # inventing layout. Retrieval picks only the 1-2 closest recipes (token-safe).
    from .ui_retrieval import build_ui_context
    ui_context = build_ui_context(project.brief or "", project.project_type, mandate)
    if ui_context:
        system += "\n\n" + ui_context
    context = {
        "phase": phase_key,
        "mandate": mandate,
        "title": project.title,
        "brief": project.brief,
        "project_type": project.project_type,
        "project_mode": getattr(project, "project_mode", "auto"),
        "personality_mode": personality_mode,
        "requires_codebase": getattr(project, "requires_codebase", True),
        "requested_outputs": project.requested_outputs or [],
        "technical_level": getattr(project, "technical_level", "non_technical"),
        "agent_name": f"{assignment['model_name']} (slot {assignment['agent_slot']})",
        "access": assignment.get("access", []),
        **(extra_context or {}),
    }
    user = (f"Phase: {phase_key}\nMandate: {mandate}\n"
            f"Allowed access: {', '.join(context['access'])}\n\n"
            f"Build style: {build_style}\n\n"
            f"Project: {project.title}\n\nBrief:\n{project.brief}\n"
            + _render_context_sections(extra_context or {}))

    status = "success"
    route = _route_base(card)
    from .event_log import log_event
    log_event(db, project.id, "agent_call_started",
              f"{assignment['model_name']} started as {mandate}",
              {"phase": phase_key, "mandate": mandate,
               "provider": card.get("provider", ""),
               "model": card.get("model_name", "")},
              workspace)
    try:
        # failover ladder: rotate the key pool, then optionally use same-cost
        # fallback/mock only when explicitly enabled in admin settings.
        result, route = _call_with_pool(db, card, system, user, context)
    except Exception as exc:
        route = getattr(exc, "route", route)
        error_message = redact_error(exc)
        primary_failure = f"failover from {card.get('model_name', '?')}: {error_message}"
        logger.warning("model %s failed as %s, trying alternatives: %s",
                       card.get("model_name", "?"), mandate, error_message)
        result = None
        from .model_pool import alternative_cards
        try:
            real_alternatives = alternative_cards(db, card)
        except Exception:
            real_alternatives = []
        for alt in real_alternatives:
            if alt.get("provider") == "mock":
                continue
            log_event(db, project.id, "agent_call_started",
                      f"{alt['model_name']} started as {mandate} after failover",
                      {"phase": phase_key, "mandate": mandate,
                       "provider": alt.get("provider", ""),
                       "model": alt.get("model_name", ""),
                       "failover_from": card.get("model_name", ""),
                       "failover_reason": error_message[:300]},
                      workspace)
            try:
                result, route = _call_with_pool(db, alt, system, user, context)
                status = f"failover:{alt['model_name']}"
                card = alt
                error_message = ""
                # keep the original failure visible in the call log
                route = dict(route) | {"route_error": primary_failure[:500]}
                break
            except Exception as alt_exc:
                route = getattr(alt_exc, "route", route)
                error_message = redact_error(alt_exc)
                result = None
        if result is None and bool(get_setting(db, "allow_mock_fallback")):
            try:
                mock_alternatives = alternative_cards(db, card)
            except Exception:
                mock_alternatives = []
            for alt in mock_alternatives:
                if alt.get("provider") != "mock":
                    continue
                log_event(db, project.id, "agent_call_started",
                          f"{alt['model_name']} started as {mandate} after failover",
                          {"phase": phase_key, "mandate": mandate,
                           "provider": alt.get("provider", ""),
                           "model": alt.get("model_name", ""),
                           "failover_from": card.get("model_name", "")},
                          workspace)
                try:
                    result, route = _call_with_pool(db, alt, system, user, context)
                    # A mock standing in for a failed real model is a diagnostic
                    # draft, never billable client progress — the orchestrator
                    # must not count its files as "the model built something".
                    result.status = "mock_fallback"
                    status = f"failover:{alt['model_name']}"
                    card = alt
                    error_message = ""
                    route = dict(route) | {"route_error": primary_failure[:500]}
                    break
                except Exception as alt_exc:
                    route = getattr(alt_exc, "route", route)
                    error_message = redact_error(alt_exc)
                    result = None
        if result is None:
            call = AgentCall(
                project_id=project.id, phase_key=phase_key, agent_id=agent_db_id,
                model_id=assignment["model_id"], mandate=mandate,
                prompt_path=None, output_path=None,
                input_tokens_estimated=0, output_tokens_estimated=0,
                cost_estimated_usd=0, status="provider_error",
                provider_id=route.get("provider_id", ""),
                provider_type=route.get("provider_type", card.get("provider", "")),
                provider_model_name=route.get("provider_model_name", card.get("model_name", "")),
                provider_key_id=route.get("provider_key_id", ""),
                provider_key_mask=route.get("provider_key_mask", ""),
                error_message=error_message[:1000],
            )
            db.add(call)
            db.commit()
            (workspace / "logs").mkdir(parents=True, exist_ok=True)
            with open(workspace / "logs" / "agent-calls.jsonl", "a") as f:
                f.write(json.dumps({
                    "project_id": project.id, "phase": phase_key,
                    "agent_id": agent_db_id, "model_id": assignment["model_id"],
                    "mandate": mandate, "cost_estimated_usd": 0,
                    "status": "provider_error", "error_message": error_message[:1000],
                    "provider_id": route.get("provider_id", ""),
                    "provider_type": route.get("provider_type", card.get("provider", "")),
                    "provider_model_name": route.get("provider_model_name", card.get("model_name", "")),
                    "provider_key_mask": route.get("provider_key_mask", ""),
                    "created_at": datetime.now(UTC).isoformat(),
                }, ensure_ascii=False) + "\n")
            raise RuntimeError(error_message) from exc

    # Real providers return prose with fenced code blocks; extract the files the
    # agent actually wrote so build/repair output lands in repo/ instead of being
    # discarded. Mock already fills result.files, so only parse when it's empty.
    # Any mandate may emit code during build/repair phases (a "lead" that wrote
    # the app into its implementation log still built the app).
    if (not result.files
            and (mandate in ("builder", "repairer")
                 or phase_key in ("build_sprint", "repair_sprint"))
            and context.get("requires_codebase", True)):
        from ..lib.file_extractor import extract_repo_files
        result.files = extract_repo_files(result.text)

    result.text, _ = sanitize(result.text)

    # abuse limit: cap runaway model output
    max_out = int(get_setting(db, "max_output_chars") or 200_000)
    if len(result.text) > max_out:
        result.text = result.text[:max_out] + "\n\n[output truncated at limit]"

    # Persist output for founder diagnostics. Full prompts are proprietary and
    # are not stored unless explicitly enabled in admin settings.
    calls_dir = workspace / "logs" / "calls"
    calls_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%H%M%S%f")
    prompt_rel = None
    if bool(get_setting(db, "store_internal_prompts")):
        prompt_path = calls_dir / f"{phase_key}_{mandate}_{stamp}_prompt.md"
        prompt_path.write_text(system + "\n\n---\n\n" + user)
        prompt_rel = str(prompt_path.relative_to(workspace))
    output_path = calls_dir / f"{phase_key}_{mandate}_{stamp}_output.md"
    output_path.write_text(result.text)

    cost = _estimate_cost(card, result.input_tokens, result.output_tokens)

    call = AgentCall(
        project_id=project.id, phase_key=phase_key, agent_id=agent_db_id,
        model_id=assignment["model_id"], mandate=mandate,
        prompt_path=prompt_rel,
        output_path=str(output_path.relative_to(workspace)),
        input_tokens_estimated=result.input_tokens,
        output_tokens_estimated=result.output_tokens,
        cost_estimated_usd=cost, status=status,
        provider_id=route.get("provider_id", ""),
        provider_type=route.get("provider_type", card.get("provider", "")),
        provider_model_name=route.get("provider_model_name", card.get("model_name", "")),
        provider_key_id=route.get("provider_key_id", ""),
        provider_key_mask=route.get("provider_key_mask", ""),
        error_message=route.get("route_error", ""),
    )
    db.add(call)
    db.commit()

    with open(workspace / "logs" / "agent-calls.jsonl", "a") as f:
        f.write(json.dumps({
            "project_id": project.id, "phase": phase_key,
            "agent_id": agent_db_id, "model_id": assignment["model_id"],
            "mandate": mandate,
            "input_tokens_estimated": result.input_tokens,
            "output_tokens_estimated": result.output_tokens,
            "cost_estimated_usd": cost, "status": status,
            "provider_id": route.get("provider_id", ""),
            "provider_type": route.get("provider_type", card.get("provider", "")),
            "provider_model_name": route.get("provider_model_name", card.get("model_name", "")),
            "provider_key_mask": route.get("provider_key_mask", ""),
            "created_at": datetime.now(UTC).isoformat(),
        }, ensure_ascii=False) + "\n")

    return result, cost
