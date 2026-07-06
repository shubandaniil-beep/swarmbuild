import ast

from app.lib.redact import PLACEHOLDER, redact
from app.services.secret_scanner import scan_and_redact


def test_redact_does_not_treat_control_flow_colon_as_secret_assignment():
    source = "def read_key(API_KEY):\n    if not API_KEY: return None\n    return API_KEY\n"

    cleaned, labels = redact(source)

    assert cleaned == source
    assert labels == []
    ast.parse(cleaned)


def test_redact_only_literal_secret_values_in_real_assignments():
    source = "\n".join([
        "API_KEY = 'live-secret-value'",
        "token = os.getenv('BOT_TOKEN')",
        "return_value = get_secret(api_key='function-call-value')",
        "settings = {'api_key': 'dict-secret-value'}",
        "if not API_KEY: return None",
        "",
    ])

    cleaned, labels = redact(source)

    assert f"API_KEY = '{PLACEHOLDER}'" in cleaned
    assert f"'api_key': '{PLACEHOLDER}'" in cleaned
    assert "token = os.getenv('BOT_TOKEN')" in cleaned
    assert "get_secret(api_key='function-call-value')" in cleaned
    assert "if not API_KEY: return None" in cleaned
    assert "assigned_api_key" in labels


def test_scan_and_redact_preserves_python_syntax_after_safe_redaction(tmp_path):
    ws = tmp_path / "ws"
    repo = ws / "repo"
    repo.mkdir(parents=True)
    path = repo / "main.py"
    path.write_text(
        "API_KEY = 'live-secret-value'\n"
        "def load(API_KEY):\n"
        "    if not API_KEY: return None\n"
        "    return API_KEY\n"
    )

    summary = scan_and_redact(ws)

    cleaned = path.read_text()
    assert f"API_KEY = '{PLACEHOLDER}'" in cleaned
    assert "if not API_KEY: return None" in cleaned
    assert summary["syntax_broken_by_redaction"] == []
    ast.parse(cleaned)
