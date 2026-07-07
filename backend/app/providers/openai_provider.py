import json
import urllib.error
import urllib.request

from .base import (
    BaseProvider,
    ProviderHTTPError,
    ProviderResult,
    guarded_urlopen,
    parse_retry_after,
    read_json_with_deadline,
)


def _provider_error_from_body(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return "empty error response"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return text[:600]
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict):
        return str(err.get("message") or err.get("code") or err.get("type") or "unknown error")
    if err:
        return str(err)
    return text[:600]


def _message_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "".join(parts)
    if message.get("tool_calls"):
        # e.g. Gemini's OpenAI shim: the model decided to "call a tool" even
        # though no tools were offered → no usable text in the choice.
        raise ToolUseMismatchError("model attempted a tool call but no tools are configured")
    # Reasoning-model fallback: a thinking model can burn its whole token
    # budget on reasoning and hand back an empty `content` while the actual
    # prose sits in `reasoning_content`. Better a billed call yields that than
    # nothing at all.
    reasoning = message.get("reasoning_content")
    if isinstance(reasoning, str) and reasoning.strip():
        return reasoning
    raise RuntimeError("provider returned a choice without message.content")


class ToolUseMismatchError(RuntimeError):
    """The model emitted (or the backend rejected) a tool call in a plain-text
    conversation — e.g. "Tool choice is none, but model called a tool". Not a
    key/quota fault: retried once with an explicit no-tools instruction."""


_TOOL_MISMATCH_MARKERS = ("tool choice is none", "model called a tool",
                          "tool call", "tool_calls", "function call", "function_call")


def _is_tool_mismatch(message: str) -> bool:
    text = (message or "").lower()
    return any(marker in text for marker in _TOOL_MISMATCH_MARKERS)


_NO_TOOLS_NUDGE = ("\n\nCRITICAL: You have NO tools or functions available in this "
                   "conversation. Respond with plain text (markdown) only; never "
                   "emit a tool call or function call.")


class OpenAICompatibleProvider(BaseProvider):
    """Chat Completions adapter for OpenAI/DeepSeek/Qwen/Gemini-compatible endpoints."""

    def __init__(self, card: dict, base_url: str, api_key: str):
        super().__init__(card)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def complete(self, system: str, user: str, context: dict | None = None) -> ProviderResult:
        try:
            return self._complete_once(system, user)
        except (ToolUseMismatchError, ProviderHTTPError, RuntimeError) as exc:
            # Tool-config compatibility: some backends 400 with "Tool choice is
            # none, but model called a tool" (or return a tool_calls-only
            # choice). The request is fine — the model misbehaved. One retry
            # with an explicit no-tools instruction resolves it; anything else
            # re-raises for the normal key/model failover to judge.
            status = getattr(exc, "status_code", 0)
            retryable_http = isinstance(exc, ProviderHTTPError) and 400 <= status < 500
            if isinstance(exc, ToolUseMismatchError) or \
                    ((retryable_http or not isinstance(exc, ProviderHTTPError))
                     and _is_tool_mismatch(str(exc))):
                return self._complete_once(system + _NO_TOOLS_NUDGE, user)
            raise

    def _complete_once(self, system: str, user: str) -> ProviderResult:
        payload = {
            "model": self.card["model_name"],
            "temperature": self.card.get("default_temperature", 0.3),
            "max_tokens": self.card.get("max_output_tokens", 4000),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        # z.ai GLM ships as a reasoning model: left on, it spends the whole
        # max_tokens budget on `reasoning_content` and returns an EMPTY
        # `content` (finish_reason=length) — a billed call with no usable
        # result. We want the answer, not the monologue: disable thinking so
        # it responds directly (≈3x faster, no wasted reasoning tokens).
        if self.card.get("provider") == "glm":
            payload["thinking"] = {"type": "disabled"}
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {self.api_key}",
                   "User-Agent": "SwarmBuild/1.0"}
        if self.card.get("provider") == "openrouter":
            referer = str(self.card.get("http_referer") or "").strip()
            title = str(self.card.get("app_title") or "").strip()
            if referer:
                headers["HTTP-Referer"] = referer
            if title:
                headers["X-OpenRouter-Title"] = title
        allow_private = bool(self.card.get("allow_private_provider_urls"))
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        timeout = float(self.card.get("timeout_seconds", 30))
        try:
            with guarded_urlopen(req, timeout, allow_private) as resp:
                data = read_json_with_deadline(resp, timeout)
        except urllib.error.HTTPError as exc:
            message = _provider_error_from_body(exc.read(65536))
            raise ProviderHTTPError(f"provider HTTP {exc.code}: {message}",
                                    status_code=exc.code,
                                    retry_after=parse_retry_after(exc.headers)) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"provider connection error: {exc.reason}") from exc
        if "error" in data:
            err = data["error"]
            if isinstance(err, dict):
                message = err.get("message") or err.get("code") or err.get("type") or "unknown error"
            else:
                message = str(err)
            raise RuntimeError(f"provider error: {message}")
        choices = data.get("choices")
        if not choices:
            keys = ", ".join(sorted(str(k) for k in data.keys())[:8])
            raise RuntimeError(f"provider returned no choices (response keys: {keys or 'none'})")
        message = choices[0].get("message") or {}
        text = _message_text(message)
        usage = data.get("usage", {})
        return ProviderResult(
            text=text,
            input_tokens=usage.get("prompt_tokens", len(system + user) // 4),
            output_tokens=usage.get("completion_tokens", len(text) // 4),
        )
