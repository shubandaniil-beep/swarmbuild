"""Real-API canary checks — the ONLY tests that spend provider money.

Everything else in the suite runs on the mock provider and static gates for
free. These canaries exist to answer one question cheaply: "does a real,
minimal call still work end-to-end?" — one tiny completion and one one-file
build-contract probe against the cheapest Groq model.

They are skipped unless BOTH are set (so CI and casual `pytest` never pay):

    SWARMBUILD_REAL_CANARY=1
    SWARMBUILD_CANARY_GROQ_KEY=<real groq key>

(conftest.py blanks GROQ_API_KEY for test isolation, hence the dedicated var.)
Run via `make canary`.
"""
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("SWARMBUILD_REAL_CANARY") != "1"
    or not os.getenv("SWARMBUILD_CANARY_GROQ_KEY"),
    reason="real-API canary: set SWARMBUILD_REAL_CANARY=1 and "
           "SWARMBUILD_CANARY_GROQ_KEY (spends real money)",
)

_CANARY_MODEL = "llama-3.1-8b-instant"  # cheapest production Groq chat model


def _provider():
    from app.providers.openai_provider import OpenAICompatibleProvider
    card = {"provider": "groq", "model_name": _CANARY_MODEL,
            "max_output_tokens": 300, "default_temperature": 0,
            "timeout_seconds": 45}
    return OpenAICompatibleProvider(card, "https://api.groq.com/openai/v1",
                                    os.environ["SWARMBUILD_CANARY_GROQ_KEY"])


def test_canary_minimal_completion():
    result = _provider().complete(
        "You are a health check. Answer in one short line.",
        "Reply with exactly: CANARY OK")
    assert result.text.strip()
    assert result.output_tokens > 0


def test_canary_file_contract_roundtrip():
    """The core production contract: a real model, given the FILE format, must
    produce output our extractor turns into an actual file."""
    from app.lib.file_extractor import extract_repo_files
    result = _provider().complete(
        "You emit files using this exact contract:\n"
        "=== FILE: path ===\n```lang\n<contents>\n```",
        "Emit exactly one file `hello.py` that prints 'hello'. "
        "Use the FILE contract, nothing else.")
    files = extract_repo_files(result.text)
    assert "hello.py" in files, result.text[:500]
    assert "hello" in files["hello.py"]
