import ipaddress
import json
import socket
import time
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse


def guard_egress_url(url: str, allow_private: bool = False) -> None:
    """Runtime SSRF guard, called right before every provider request.

    A provider's base_url is checked when it is saved, but DNS can be re-pointed
    between that check and the actual call (DNS rebinding). Re-resolve here and
    block host-internal ranges. RFC1918/private ranges are only allowed when
    the admin has explicitly enabled private provider URLs; loopback, link-local
    metadata, multicast, reserved and unspecified addresses are always blocked.
    """
    host = (urlparse(url).hostname or "").strip("[]")
    if not host:
        return
    addrs: set[str] = set()
    try:
        addrs.add(host)  # host is already an IP literal
        ipaddress.ip_address(host)
    except ValueError:
        try:
            addrs = {info[4][0] for info in socket.getaddrinfo(host, None)}
        except socket.gaierror:
            return  # let urlopen surface the DNS failure with its own error
    for addr in addrs:
        try:
            ip = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            continue
        always_block = any((
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        ))
        if always_block or (ip.is_private and not allow_private):
            raise RuntimeError("blocked egress to a host-internal address (SSRF guard)")


class _GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-runs the SSRF guard on every redirect target.

    urlopen() follows up to 10 redirects by default. Guarding only the original
    URL leaves a hole: a provider host (or a rebound DNS name) can answer with
    `30x Location: http://169.254.169.254/…` or an internal address, and urllib
    would follow it — carrying the request's API key — past a guard that only
    ever saw the first hop. Validating each hop closes that."""

    def __init__(self, allow_private: bool = False):
        super().__init__()
        self._allow_private = allow_private

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        guard_egress_url(newurl, self._allow_private)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def guarded_urlopen(req, timeout, allow_private: bool = False):
    """Drop-in urlopen that SSRF-guards the initial URL *and* every redirect hop."""
    url = req.full_url if hasattr(req, "full_url") else req
    guard_egress_url(url, allow_private)
    opener = urllib.request.build_opener(_GuardedRedirectHandler(allow_private))
    return opener.open(req, timeout=timeout)


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
