"""Agent Runner: assemble prompt, call provider, persist output + call log."""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from ..lib.output_filter import sanitize
from ..lib.redact import redact_error
from ..models import AgentCall
from ..providers import get_provider
from ..providers.base import ProviderResult
from .settings_service import get_setting

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class ProviderPoolError(RuntimeError):
    def __init__(self, message: str, route: dict):
        super().__init__(message)
        self.route = route


def _prompt(name: str) -> str:
    p = PROMPTS_DIR / f"{name}.md"
    return p.read_text() if p.exists() else ""


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


def _call_with_pool(db: Session, card: dict, system: str, user: str,
                    context: dict) -> tuple[ProviderResult, dict]:
    """Complete one call, rotating across the provider's key pool.

    Keys are tried least-recently-used first and failed over key-by-key on
    error, so a single rate-limited key never stalls the swarm. Raises only
    when every key in the pool fails.
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

    keys = key_pool.ordered_key_records(db, provider)
    if not keys:
        raise RuntimeError(f"{provider.name}: no usable API keys configured")

    last_exc: Exception | None = None
    last_error = ""
    for record in keys:
        route = _route_base(card) | {
            "provider_key_id": record["id"],
            "provider_key_mask": record["mask"],
        }
        try:
            result = get_provider(card, record["plaintext"]).complete(system, user, context)
            key_pool.mark_ok(db, record["id"])
            return result, route
        except Exception as exc:  # try the next key in the pool
            last_error = redact_error(exc)
            if key_pool.is_key_scoped_error(last_error):
                key_pool.mark_error(db, record["id"], last_error)
            last_exc = exc
    route["route_error"] = last_error
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
            f"Project: {project.title}\n\nBrief:\n{project.brief}\n")

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
                       "failover_from": card.get("model_name", "")},
                      workspace)
            try:
                result, route = _call_with_pool(db, alt, system, user, context)
                status = f"failover:{alt['model_name']}"
                card = alt
                error_message = ""
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
                    status = f"failover:{alt['model_name']}"
                    card = alt
                    error_message = ""
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
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }, ensure_ascii=False) + "\n")
            raise RuntimeError(error_message) from exc

    result.text, _ = sanitize(result.text)

    # abuse limit: cap runaway model output
    max_out = int(get_setting(db, "max_output_chars") or 200_000)
    if len(result.text) > max_out:
        result.text = result.text[:max_out] + "\n\n[output truncated at limit]"

    # Persist output for founder diagnostics. Full prompts are proprietary and
    # are not stored unless explicitly enabled in admin settings.
    calls_dir = workspace / "logs" / "calls"
    calls_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S%f")
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
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False) + "\n")

    return result, cost
