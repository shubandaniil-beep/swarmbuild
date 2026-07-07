"""Regression tests for transient-provider resilience.

A real run once died in `build_sprint` on a Gemini **HTTP 503** ("model
overloaded"): the error was classified as neither transient nor permanent, so
`_call_with_pool` gave up after a single attempt and the project fell to
`needs_provider`. Transient 5xx / gateway / network / deadline faults must be
retried instead.
"""
import pytest

from app.providers.base import ProviderHTTPError, ProviderResult, guard_egress_url
from app.services import agent_runner, key_pool
from app.services.agent_runner import _cooldown_seconds


@pytest.mark.parametrize("msg", [
    "provider HTTP 503: ",                      # Gemini overload, empty body
    "provider HTTP 503: empty error response",
    "provider HTTP 502: Bad Gateway",
    "provider HTTP 500: internal error",
    "provider HTTP 504: gateway timeout",
    "provider HTTP 529: overloaded",            # Anthropic overload
    "provider connection error: [Errno 60] Operation timed out",
    "provider response exceeded 60s deadline",
    "The model is overloaded. Please try again later.",
    "provider HTTP 429: rate limit exceeded",
    "RESOURCE_EXHAUSTED: quota",
])
def test_transient_errors_are_retryable(msg):
    assert key_pool.is_transient_key_error(msg) is True
    assert key_pool.is_permanent_key_error(msg) is False


@pytest.mark.parametrize("msg", [
    "provider HTTP 401: invalid api key",
    "provider HTTP 403: forbidden",
    "insufficient credits",
])
def test_permanent_errors_are_not_transient(msg):
    assert key_pool.is_permanent_key_error(msg) is True
    assert key_pool.is_transient_key_error(msg) is False


@pytest.mark.parametrize("msg", [
    "provider HTTP 400: bad request",
    "provider HTTP 404: model not found",
    "provider returned no choices (response keys: none)",
])
def test_client_errors_are_neither(msg):
    # A 4xx (bad request/model gone) is neither a passing blip nor a dead key:
    # don't burn retries and don't bench the key — let model failover decide.
    assert key_pool.is_transient_key_error(msg) is False
    assert key_pool.is_permanent_key_error(msg) is False


def test_server_fault_backoff_escalates_but_rate_limit_is_flat():
    # 5xx / network faults clear in seconds → short backoff that escalates on
    # repeated failure (5 → 10 → 20, capped) so a struggling upstream isn't hammered.
    assert key_pool.is_transient_server_error("provider HTTP 503: ") is True
    assert _cooldown_seconds(RuntimeError(), "provider HTTP 503: ", 1) == 5.0
    assert _cooldown_seconds(RuntimeError(), "provider HTTP 503: ", 2) == 10.0
    assert _cooldown_seconds(RuntimeError(), "provider HTTP 503: ", 3) == 20.0
    assert _cooldown_seconds(RuntimeError(), "provider HTTP 503: ", 9) == 20.0  # capped
    # A plain rate limit is retryable but not a *server* fault → flat window.
    assert key_pool.is_transient_server_error("429 too many requests") is False
    assert _cooldown_seconds(RuntimeError(), "429 too many requests", 3) == 30.0
    # Per-minute free-tier windows reset on the minute.
    assert _cooldown_seconds(RuntimeError(), "free-models-per-min limit", 2) == 61.0
    # An explicit Retry-After header always wins, regardless of attempt.
    assert _cooldown_seconds(ProviderHTTPError("x", 503, retry_after=8.0), "x", 3) == 9.0


def _e503():
    return ProviderHTTPError("provider HTTP 503: ", status_code=503)


class _ScriptedProvider:
    """Provider stub whose complete() follows a script; the last step repeats."""

    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls = 0

    def complete(self, system, user, context=None):
        self.calls += 1
        step = self.steps[min(self.calls - 1, len(self.steps) - 1)]
        if isinstance(step, Exception):
            raise step
        return step


def _new_provider(db, keys: str):
    from app.models import Provider
    provider = Provider(name="Gemini-Test", provider_type="gemini",
                        base_url="https://example.invalid/openai",
                        enabled=True, status="untested", priority=50)
    db.add(provider)
    db.commit()
    added = key_pool.add_keys(db, provider, keys)
    return provider, added


def _card(provider):
    return {"provider": "gemini", "provider_id": provider.id,
            "model_name": "gemini-2.5-flash",
            "input_cost_per_1m": 0.15, "output_cost_per_1m": 0.6}


def test_single_key_503_then_success_after_real_wait(client, monkeypatch):
    """The exact real-run failure: the *only* key returns 503 once. The runner
    must cool it down, wait, and retry — not abort the phase. Exercises the real
    cooldown/wait path (backoff shrunk so the test stays snappy)."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        provider, added = _new_provider(db, "k-solo-1")
        assert added == 1
        stub = _ScriptedProvider(_e503(), ProviderResult("ok", 5, 2))
        monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": stub)
        monkeypatch.setattr(agent_runner.random, "uniform", lambda *a, **k: 0.0)
        monkeypatch.setattr(agent_runner, "_cooldown_seconds", lambda *a, **k: 0.1)

        result, route = agent_runner._call_with_pool(db, _card(provider), "s", "u", {})
        assert result.text == "ok"
        assert stub.calls == 2           # failed once, waited, retried, succeeded
        assert route["provider_key_mask"]  # the successful key is recorded
    finally:
        db.close()


def test_single_key_survives_two_consecutive_503s(client, monkeypatch):
    """Two transient 503s in a row must still be survived within the budget.
    (is_cooling stubbed off so retries fire immediately — this asserts the retry
    *count*, not the wait timing.)"""
    from app.database import SessionLocal
    from app.services.settings_service import get_setting
    db = SessionLocal()
    try:
        provider, _ = _new_provider(db, "k-two-1")
        stub = _ScriptedProvider(_e503(), _e503(), ProviderResult("ok", 5, 2))
        monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": stub)
        monkeypatch.setattr(key_pool, "is_cooling", lambda *a, **k: False)

        assert int(get_setting(db, "provider_retry_attempts") or 3) >= 3
        result, _ = agent_runner._call_with_pool(db, _card(provider), "s", "u", {})
        assert result.text == "ok"
        assert stub.calls == 3
    finally:
        db.close()


def test_persistent_503_spends_exactly_the_attempt_budget(client, monkeypatch):
    """A never-recovering 503 must stop after exactly `provider_retry_attempts`
    *real* calls — proving idle waiting no longer steals from the retry budget —
    then surface as a provider block, not a generic failure."""
    from app.database import SessionLocal
    from app.services.agent_runner import ProviderPoolError
    from app.services.settings_service import get_setting
    db = SessionLocal()
    try:
        provider, _ = _new_provider(db, "k-persist-1")
        stub = _ScriptedProvider(_e503())  # last step repeats → always 503
        monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": stub)
        monkeypatch.setattr(key_pool, "is_cooling", lambda *a, **k: False)
        attempts = int(get_setting(db, "provider_retry_attempts") or 3)

        with pytest.raises(ProviderPoolError, match="all usable keys failed"):
            agent_runner._call_with_pool(db, _card(provider), "s", "u", {})
        assert stub.calls == attempts
    finally:
        db.close()


def test_two_key_pool_fails_over_without_waiting(client, monkeypatch):
    """When one key 503s and another is ready, failover happens in the same pass
    with no idle wait."""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        provider, added = _new_provider(db, "k-a-1, k-b-2")
        assert added == 2
        stub = _ScriptedProvider(_e503(), ProviderResult("ok", 5, 2))
        monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": stub)

        def no_sleep(*a, **k):
            raise AssertionError("must not wait while a key is ready")
        monkeypatch.setattr(agent_runner.time, "sleep", no_sleep)

        result, _ = agent_runner._call_with_pool(db, _card(provider), "s", "u", {})
        assert result.text == "ok"
        assert stub.calls == 2
    finally:
        db.close()


def test_permanent_error_disables_key_and_stops_immediately(client, monkeypatch):
    """A bad-key (401) error is not retried and takes the key out of rotation."""
    from app.database import SessionLocal
    from app.models import ProviderKey
    from app.services.agent_runner import ProviderPoolError
    db = SessionLocal()
    try:
        provider, _ = _new_provider(db, "k-bad-1")
        stub = _ScriptedProvider(
            ProviderHTTPError("provider HTTP 401: invalid api key", status_code=401))
        monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": stub)

        def no_sleep(*a, **k):
            raise AssertionError("permanent errors must not wait or retry")
        monkeypatch.setattr(agent_runner.time, "sleep", no_sleep)

        with pytest.raises(ProviderPoolError):
            agent_runner._call_with_pool(db, _card(provider), "s", "u", {})
        assert stub.calls == 1
        key = db.query(ProviderKey).filter(ProviderKey.provider_id == provider.id).first()
        assert key.status == "error"
    finally:
        db.close()


def test_egress_guard_blocks_ssrf_to_internal_targets():
    """Runtime SSRF guard: a provider base_url that resolves to loopback or
    link-local (cloud metadata 169.254.169.254) is refused right before the
    request, closing the DNS-rebinding window; public LLM hosts pass."""
    for blocked in ("http://169.254.169.254/latest/meta-data/",
                    "http://127.0.0.1:8000/v1",
                    "http://localhost/v1",
                    "http://[::1]/v1",
                    "http://10.0.0.5/v1",
                    "http://172.16.0.5/v1",
                    "http://192.168.1.5/v1"):
        with pytest.raises(RuntimeError):
            guard_egress_url(blocked)

    # Explicit private-provider mode allows RFC1918 LAN targets, but still not
    # loopback or link-local metadata.
    guard_egress_url("http://10.0.0.5/v1", allow_private=True)
    with pytest.raises(RuntimeError):
        guard_egress_url("http://127.0.0.1:8000/v1", allow_private=True)
    with pytest.raises(RuntimeError):
        guard_egress_url("http://169.254.169.254/latest/meta-data/", allow_private=True)

    # public provider endpoints are allowed (no exception)
    for ok in ("https://api.openai.com/v1", "https://api.groq.com/openai/v1"):
        guard_egress_url(ok)
