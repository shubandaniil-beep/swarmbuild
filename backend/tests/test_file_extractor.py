"""File extraction contract: every marker format real models actually emit
must land in the repo, and placeholder/junk output must never become a file."""
from app.lib.file_extractor import extract_repo_files, is_placeholder_content


def test_plain_file_marker():
    text = "FILE: main.py\n```python\nprint('hi')\n```\n"
    assert extract_repo_files(text) == {"main.py": "print('hi')\n"}


def test_equals_wrapped_marker():
    text = "=== FILE: src/app.py ===\n```python\nx = 1\n```\n"
    assert extract_repo_files(text) == {"src/app.py": "x = 1\n"}


def test_heading_prefixed_marker():
    text = "### FILE: utils/helpers.py ===\n```python\ndef f():\n    return 2\n```\n"
    assert list(extract_repo_files(text)) == ["utils/helpers.py"]


def test_bold_marker():
    text = "**FILE: config.json**\n```json\n{\"a\": 1}\n```\n"
    assert list(extract_repo_files(text)) == ["config.json"]


def test_bare_path_heading():
    text = "## src/main.py\n```python\nprint(1)\n```\n"
    assert list(extract_repo_files(text)) == ["src/main.py"]


def test_fence_info_string_path():
    text = "```python path=lib/db.py\nconn = None\n```\n"
    assert list(extract_repo_files(text)) == ["lib/db.py"]
    text2 = "```lib/db2.py\nconn = None\n```\n"
    assert list(extract_repo_files(text2)) == ["lib/db2.py"]


def test_first_line_comment_path():
    text = "Some prose.\n```python\n# tools/run.py\nprint(3)\n```\n"
    assert list(extract_repo_files(text)) == ["tools/run.py"]


def test_known_bare_names_allowed():
    text = "FILE: .gitignore\n```\n.venv/\n```\nFILE: Dockerfile\n```\nFROM python:3.12\n```\n"
    assert set(extract_repo_files(text)) == {".gitignore", "Dockerfile"}


def test_language_tag_is_not_a_path():
    text = "Here is an example:\n```python\nprint('illustrative')\n```\n"
    assert extract_repo_files(text) == {}


def test_no_changes_placeholder_is_dropped():
    for body in ("(no changes)", "no changes", "unchanged", "...", "N/A"):
        text = f"FILE: main.py\n```\n{body}\n```\n"
        assert extract_repo_files(text) == {}, body
        assert is_placeholder_content(body)


def test_junk_path_is_dropped():
    text = "FILE: (no changes)\n```python\nprint('x')\n```\n"
    assert extract_repo_files(text) == {}


def test_traversal_and_absolute_paths_blocked():
    for path in ("../../etc/passwd", "/etc/passwd", "..\\secrets.txt"):
        text = f"FILE: {path}\n```\nboom\n```\n"
        assert extract_repo_files(text) == {}, path


def test_repo_prefix_and_dot_slash_stripped():
    text = "FILE: repo/app.py\n```python\nx=1\n```\nFILE: ./b.py\n```python\ny=2\n```\n"
    assert set(extract_repo_files(text)) == {"app.py", "b.py"}
