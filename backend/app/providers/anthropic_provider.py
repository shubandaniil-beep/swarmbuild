import json
import urllib.error
import urllib.request

from .base import (
    BaseProvider,
    ProviderHTTPError,
    ProviderResult,
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
        return str(err.get("message") or err.get("type") or "unknown error")
    if err:
        return str(err)
    return text[:600]


class AnthropicCompatibleProvider(BaseProvider):
    def __init__(self, card: dict, base_url: str, api_key: str):
        super().__init__(card)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def complete(self, system: str, user: str, context: dict | None = None) -> ProviderResult:
        payload = {
            "model": self.card["model_name"],
            "max_tokens": self.card.get("max_output_tokens", 4000),
            "temperature": self.card.get("default_temperature", 0.3),
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        req = urllib.request.Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "x-api-key": self.api_key,
                     "anthropic-version": "2023-06-01",
                     "User-Agent": "SwarmBuild/1.0"},
        )
        timeout = float(self.card.get("timeout_seconds", 30))
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
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
                message = err.get("message") or err.get("type") or "unknown error"
            else:
                message = str(err)
            raise RuntimeError(f"provider error: {message}")
        content = data.get("content")
        if not isinstance(content, list):
            keys = ", ".join(sorted(str(k) for k in data.keys())[:8])
            raise RuntimeError(f"provider returned no content list (response keys: {keys or 'none'})")
        text = "".join(b.get("text", "") for b in content)
        usage = data.get("usage", {})
        return ProviderResult(
            text=text,
            input_tokens=usage.get("input_tokens", len(system + user) // 4),
            output_tokens=usage.get("output_tokens", len(text) // 4),
        )
