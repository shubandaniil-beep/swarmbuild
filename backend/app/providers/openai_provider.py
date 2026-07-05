import json
import urllib.error
import urllib.request

from .base import BaseProvider, ProviderResult, read_json_with_deadline


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
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        if parts:
            return "".join(parts)
    raise RuntimeError("provider returned a choice without message.content")


class OpenAICompatibleProvider(BaseProvider):
    """Chat Completions adapter for OpenAI/DeepSeek/Qwen/Gemini-compatible endpoints."""

    def __init__(self, card: dict, base_url: str, api_key: str):
        super().__init__(card)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def complete(self, system: str, user: str, context: dict | None = None) -> ProviderResult:
        payload = {
            "model": self.card["model_name"],
            "temperature": self.card.get("default_temperature", 0.3),
            "max_tokens": self.card.get("max_output_tokens", 4000),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
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
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        timeout = float(self.card.get("timeout_seconds", 30))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = read_json_with_deadline(resp, timeout)
        except urllib.error.HTTPError as exc:
            message = _provider_error_from_body(exc.read(65536))
            raise RuntimeError(f"provider HTTP {exc.code}: {message}") from exc
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
