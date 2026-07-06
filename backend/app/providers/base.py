import json
import time
from dataclasses import dataclass, field


@dataclass
class ProviderResult:
    text: str
    input_tokens: int
    output_tokens: int
    status: str = "success"
    files: dict[str, str] = field(default_factory=dict)  # repo-relative path -> content


class ProviderHTTPError(RuntimeError):
    """Upstream HTTP error with enough structure for retry decisions.

    `retry_after` comes from the Retry-After header when the provider sent one,
    else 0 — the caller picks its own backoff in that case.
    """

    def __init__(self, message: str, status_code: int = 0, retry_after: float = 0.0):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


def parse_retry_after(headers) -> float:
    """Seconds from a Retry-After header (numeric form only), 0 if absent."""
    try:
        value = headers.get("Retry-After") if headers else None
        return max(0.0, float(value)) if value else 0.0
    except (TypeError, ValueError):
        return 0.0


class BaseProvider:
    def __init__(self, card: dict):
        self.card = card

    def complete(self, system: str, user: str, context: dict | None = None) -> ProviderResult:
        raise NotImplementedError

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        return round(
            input_tokens / 1_000_000 * self.card.get("input_cost_per_1m", 0)
            + output_tokens / 1_000_000 * self.card.get("output_cost_per_1m", 0), 6)


def read_json_with_deadline(resp, timeout_seconds: int | float, max_bytes: int = 5_000_000) -> dict:
    """Read chunked provider responses with a hard wall-clock deadline.

    urllib's socket timeout is not enough for slow chunked responses: a provider
    can keep the connection alive by sending tiny chunks. The worker needs a
    total deadline so one model/key cannot freeze a project phase.
    """
    timeout = max(1.0, float(timeout_seconds or 1))
    deadline = time.monotonic() + timeout
    chunks: list[bytes] = []
    total = 0
    while True:
        if time.monotonic() > deadline:
            raise TimeoutError(f"provider response exceeded {timeout:.0f}s deadline")
        # For chunked responses, large reads can block forever while the server
        # keeps the connection open with tiny chunks. A 1-byte read is slower
        # but gives the worker a real chance to enforce the deadline.
        chunk = resp.read(1)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"provider response exceeded {max_bytes} bytes")
        chunks.append(chunk)
    if time.monotonic() > deadline:
        raise TimeoutError(f"provider response exceeded {timeout:.0f}s deadline")
    return json.loads(b"".join(chunks))
