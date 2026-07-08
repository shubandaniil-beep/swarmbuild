"""Build integrity: deterministic gates + honest progress proof (spec §7.7, §7.10).

Two ideas the paid pipeline depends on, kept in one place so the orchestrator,
release policy and admin views all read the same source of truth:

1. **Progress proof.** An LLM call is *not* progress. A phase only counts as
   progress when it left evidence behind: parsed files written to the repo,
   substantive artifacts on disk, deterministic checks that passed, or open
   tasks (issues) that decreased. `assess_phase_progress` turns a finished
   phase into a signals dict + a `made_progress` boolean. Credits are charged
   only when that boolean is true.

2. **Deterministic gates.** Before a code project may be released, machine
   checks must pass — dependencies parse, an entry point exists, every Python
   file parses (AST only, never executed), and INSTALL/README describe the real
   files. `run_gates` returns per-gate pass/fail; the release policy refuses a
   full "release" decision unless the hard gates pass, and each failed gate is
   turned into a tracked issue that review/repair can see.
"""
import ast
import builtins
import json
import re
import sys
from pathlib import Path

from ..lib.file_extractor import extract_repo_files, is_junk_filename, is_placeholder_content

# Minimum characters a phase's designated text artifact must contain before we
# treat it as real work rather than an empty/failed generation.
_MIN_ARTIFACT_CHARS = 120
_MIN_DOCUMENT_CHARS = 400

# Code entry points we know how to smoke-check.
_ENTRYPOINTS = ("main.py", "app.py", "bot.py", "cli.py", "run.py", "manage.py")

# Which on-disk artifact each phase is expected to produce. Progress for a
# text phase means: this file exists and is substantive.
_PHASE_ARTIFACT: dict[str, str] = {
    "swarm_understanding": "spec/understanding-summary.md",
    "spec_war": "spec/technical-spec.md",
    "architecture_battle": "architecture/architecture.md",
    "review_stop": "reviews/review-report.md",
    "final_audit": "reviews/final-audit.md",
}


# --------------------------------------------------------------------------- #
# repo snapshots / diffing                                                     #
# --------------------------------------------------------------------------- #

def snapshot_repo(workspace: Path) -> dict[str, int]:
    """Map every repo-relative file path to (size, mtime_ns) fingerprint int."""
    repo = workspace / "repo"
    snap: dict[str, int] = {}
    if not repo.exists():
        return snap
    for f in repo.rglob("*"):
        if f.is_file():
            st = f.stat()
            snap[str(f.relative_to(repo))] = st.st_size * 1_000_000_000 + st.st_mtime_ns % 1_000_000_000
    return snap


def diff_repo(before: dict[str, int], after: dict[str, int]) -> dict:
    """What changed in repo/ between two snapshots."""
    written = sorted(p for p in after if p not in before)
    changed = sorted(p for p in after if p in before and after[p] != before[p])
    removed = sorted(p for p in before if p not in after)
    touched = set(written) | set(changed)
    code_files = [p for p in touched if p.endswith((".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java"))]
    return {
        "written": written,
        "changed": changed,
        "removed": removed,
        "files_written": len(written),
        "files_changed": len(changed),
        "code_files_touched": len(code_files),
    }


# --------------------------------------------------------------------------- #
# progress proof                                                               #
# --------------------------------------------------------------------------- #

def _artifact_is_substantive(workspace: Path, rel: str, minimum: int) -> tuple[bool, int]:
    f = workspace / rel
    if not f.exists():
        return False, 0
    try:
        size = len(f.read_text(errors="replace").strip())
    except OSError:
        return False, 0
    return size >= minimum, size


def assess_phase_progress(workspace: Path, phase_key: str, *, repo_diff: dict,
                          outputs: dict[str, list[str]], issues_before: int,
                          issues_after: int, is_code_project: bool,
                          parsed_files: int = 0) -> dict:
    """Decide whether a finished phase made real, chargeable progress.

    `outputs` maps mandate -> list of produced text bodies for this phase.
    `parsed_files` is the number of files the builder/repairer actually emitted
    through the file contract and that landed in repo/ — the honest "the model
    built something" signal, distinct from prose logs the orchestrator itself
    writes into repo/ (e.g. implementation-log.md).
    Returns {"made_progress": bool, "reason": str, "signals": {...}}.
    """
    non_empty_outputs = sum(1 for texts in outputs.values()
                            for t in texts if t and t.strip())
    signals = {
        "parsed_files": parsed_files,
        "files_written": repo_diff.get("files_written", 0),
        "files_changed": repo_diff.get("files_changed", 0),
        "code_files_touched": repo_diff.get("code_files_touched", 0),
        "non_empty_outputs": non_empty_outputs,
        "issues_before": issues_before,
        "issues_after": issues_after,
        "open_tasks_decreased": max(0, issues_before - issues_after),
    }

    made = False
    reason = "no evidence of progress"

    if phase_key == "build_sprint":
        if is_code_project:
            # Strict builder contract: a build phase that emitted no files from
            # the file contract did not build anything, no matter how much prose
            # the model returned (a prose implementation-log does not count).
            if parsed_files > 0:
                made, reason = True, f"{parsed_files} file(s) written from build contract"
            else:
                made, reason = False, "builder produced no parsed files"
        else:
            ok, size = _artifact_is_substantive(workspace, "artifacts/main-document.md",
                                                _MIN_DOCUMENT_CHARS)
            signals["document_chars"] = size
            made = ok
            reason = "document deliverable produced" if ok else "no substantive document produced"

    elif phase_key == "repair_sprint":
        closed = signals["open_tasks_decreased"]
        touched = parsed_files + repo_diff.get("files_changed", 0)
        signals["files_touched"] = touched
        if closed > 0 or touched > 0:
            made, reason = True, f"closed {closed} issue(s), touched {touched} file(s)"
        else:
            made, reason = False, "no issues closed and no files changed"

    elif phase_key in _PHASE_ARTIFACT:
        ok, size = _artifact_is_substantive(workspace, _PHASE_ARTIFACT[phase_key],
                                            _MIN_ARTIFACT_CHARS)
        signals["artifact_chars"] = size
        made = ok
        reason = "substantive artifact produced" if ok else "phase artifact missing or empty"

    else:
        # intake / packaging / anything else: progress == produced some output.
        made = non_empty_outputs > 0
        reason = "output produced" if made else "no output produced"

    return {"made_progress": made, "reason": reason, "signals": signals}


# --------------------------------------------------------------------------- #
# document salvage                                                             #
# --------------------------------------------------------------------------- #

# prose documents where models regularly hide FILE-marker code instead of
# putting it through the build contract
_SALVAGE_SOURCES = ("artifacts/main-document.md", "repo/implementation-log.md",
                    "artifacts/README.md")


def salvage_files_from_documents(workspace: Path) -> dict[str, str]:
    """Extract FILE-marker code that landed inside prose documents into repo/.

    A model that wrote the whole project into `main-document.md` (or the
    implementation log) still did the work — the files just ended up as text.
    Pull them into repo/ so the deterministic gates judge real files, never
    overwriting anything the build contract already produced.
    Returns {repo_relative_path: source_document} for what was salvaged.
    """
    repo = workspace / "repo"
    salvaged: dict[str, str] = {}
    for rel_src in _SALVAGE_SOURCES:
        src = workspace / rel_src
        if not src.exists():
            continue
        try:
            files = extract_repo_files(src.read_text(errors="replace"))
        except OSError:
            continue
        for rel, content in files.items():
            target = (repo / rel).resolve()
            if not str(target).startswith(str(repo.resolve())):
                continue
            if target.exists():
                continue  # the build contract wins; salvage only fills gaps
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            salvaged[rel] = rel_src
    return salvaged


# --------------------------------------------------------------------------- #
# deterministic gates                                                          #
# --------------------------------------------------------------------------- #

_REQ_LINE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]*(\s*[<>=!~]=?\s*[0-9A-Za-z.\-*]+)?"
                       r"(\s*;.*)?$")


def _gate(passed: bool, detail: str) -> dict:
    return {"passed": bool(passed), "detail": detail}


def _check_dependencies(repo: Path) -> dict:
    req = repo / "requirements.txt"
    pkg = repo / "package.json"
    if req.exists():
        bad = []
        for raw in req.read_text(errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            if not _REQ_LINE.match(line):
                bad.append(line[:60])
        if bad:
            return _gate(False, f"invalid requirements: {', '.join(bad[:5])}")
        return _gate(True, "requirements.txt parses")
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(errors="replace"))
        except (json.JSONDecodeError, OSError) as e:
            return _gate(False, f"package.json does not parse: {e}")
        if not isinstance(data, dict):
            return _gate(False, "package.json is not an object")
        return _gate(True, "package.json parses")
    # No dependency manifest is fine for a stdlib-only utility.
    return _gate(True, "no dependency manifest (stdlib-only)")


def _check_entrypoint(repo: Path) -> dict:
    for name in _ENTRYPOINTS:
        if (repo / name).exists():
            return _gate(True, f"entry point: {name}")
    # a static site opens straight from index.html — that IS the entry point
    if (repo / "index.html").exists() or (repo / "index.htm").exists():
        return _gate(True, "web entry point: index.html")
    pkg = repo / "package.json"
    if pkg.exists():
        try:
            scripts = json.loads(pkg.read_text(errors="replace")).get("scripts", {})
            if "start" in scripts or "dev" in scripts:
                return _gate(True, "npm start/dev script")
        except (json.JSONDecodeError, OSError):
            pass
    py = list(repo.rglob("*.py"))
    if py:
        return _gate(True, f"python module: {py[0].relative_to(repo)}")
    return _gate(False, "no runnable entry point found")


def _check_python_syntax(repo: Path) -> dict:
    """Parse (never execute) every .py file. AST-only, so a prompt-injected
    entry point cannot gain code execution from the gate."""
    broken = []
    checked = 0
    for f in repo.rglob("*.py"):
        checked += 1
        try:
            ast.parse(f.read_text(errors="replace"))
        except (SyntaxError, ValueError) as e:
            broken.append(f"{f.relative_to(repo)}: {e.__class__.__name__}")
    if not checked:
        return _gate(True, "no python files to check")
    if broken:
        return _gate(False, f"{len(broken)} file(s) do not parse: {'; '.join(broken[:5])}")
    return _gate(True, f"{checked} python file(s) parse")


def _is_static_page(repo: Path) -> bool:
    """A self-contained single-page site (index.html, no code to install or run):
    it opens straight in a browser, so README/INSTALL docs are not owed."""
    if not (repo / "index.html").exists():
        return False
    return not (list(repo.rglob("*.py")) or (repo / "package.json").exists()
                or (repo / "requirements.txt").exists())


def _check_install_matches(workspace: Path, repo: Path) -> dict:
    if _is_static_page(repo):
        return _gate(True, "static single-page site — no install step needed")
    install = workspace / "artifacts" / "INSTALL.md"
    readme = repo / "README.md"
    if not install.exists() and not readme.exists():
        return _gate(False, "no INSTALL.md or repo README.md")
    text = ""
    if install.exists():
        text += install.read_text(errors="replace")
    if readme.exists():
        text += "\n" + readme.read_text(errors="replace")
    # If the repo ships a dependency manifest, the docs must tell the user to
    # install it; otherwise the "runs as documented" promise is false.
    if (repo / "requirements.txt").exists() and (repo / "requirements.txt").read_text().strip():
        if "pip install" not in text.lower():
            return _gate(False, "requirements.txt present but docs never run pip install")
    if (repo / "package.json").exists():
        if "npm install" not in text.lower() and "npm i" not in text.lower():
            return _gate(False, "package.json present but docs never run npm install")
    # docs must not send the user to files that do not exist
    if ".env.example" in text and not (repo / ".env.example").exists():
        return _gate(False, "docs reference .env.example but the repo has none")
    return _gate(True, "install docs reference the real dependency step")


def _check_readme_references_real_files(repo: Path) -> dict:
    if _is_static_page(repo):
        return _gate(True, "static single-page site — no README needed")
    readme = repo / "README.md"
    if not readme.exists():
        return _gate(False, "repo has no README.md")
    text = readme.read_text(errors="replace")
    # Any command referencing a *.py the docs claim to run must actually exist.
    referenced = set(re.findall(r"(?:python3?|uvicorn|node)\s+([\w./\-]+\.(?:py|js))", text))
    referenced |= set(re.findall(r"([\w./\-]+\.py)", text))
    missing = [name for name in referenced if not (repo / name.split(":")[0]).exists()
               and not (repo / Path(name).name).exists()]
    if missing:
        return _gate(False, f"README references missing files: {', '.join(sorted(missing)[:5])}")
    return _gate(True, "README references existing files")


_STDLIB_MODULES = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}
_BUILTIN_NAMES = set(dir(builtins)) | {"__name__", "__file__", "__doc__", "self", "cls"}

# import name → PyPI distribution, for packages whose module differs from the
# distribution name (the common offenders in generated code)
_IMPORT_TO_DIST = {
    "PIL": "pillow", "cv2": "opencv-python", "sklearn": "scikit-learn",
    "yaml": "pyyaml", "dotenv": "python-dotenv", "bs4": "beautifulsoup4",
    "telegram": "python-telegram-bot", "dateutil": "python-dateutil",
    "jwt": "pyjwt", "jose": "python-jose", "multipart": "python-multipart",
    "fitz": "pymupdf", "OpenSSL": "pyopenssl", "socketio": "python-socketio",
}
# importable module → distributions that ship it transitively, so importing
# pydantic with only fastapi pinned is not flagged as a missing dependency
_PROVIDED_BY = {
    "pydantic": {"fastapi"}, "starlette": {"fastapi"},
    "jinja2": {"flask", "fastapi"}, "werkzeug": {"flask"}, "click": {"flask"},
    "itsdangerous": {"flask"}, "markupsafe": {"flask"},
    "aiohttp": {"aiogram"}, "magic_filter": {"aiogram"},
    "sqlalchemy": {"flask-sqlalchemy"},
}


def _normalize_dist(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_requirements(repo: Path) -> set[str] | None:
    """Normalized distribution names from requirements.txt, or None if absent."""
    req = repo / "requirements.txt"
    if not req.exists():
        return None
    out: set[str] = set()
    for raw in req.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-")):
            continue
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._\-]*)", line)
        if m:
            out.add(_normalize_dist(m.group(1)))
    return out


def _local_modules(repo: Path) -> set[str]:
    """Module/package names importable from within the repo itself."""
    local: set[str] = set()
    for f in repo.rglob("*.py"):
        rel = f.relative_to(repo)
        local.add(rel.stem)
        local.update(rel.parts[:-1])  # package directories (src, app, ...)
    return local


def _top_level_imports(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module.split(".")[0])
    return found


def _check_imports_covered(repo: Path) -> dict:
    """Every third-party import must be installable from requirements.txt —
    catches "code imports pandas but pandas is not a dependency" before a
    client hits ModuleNotFoundError on the documented install."""
    declared = _declared_requirements(repo)
    local = _local_modules(repo)
    missing: set[str] = set()
    for f in repo.rglob("*.py"):
        try:
            tree = ast.parse(f.read_text(errors="replace"))
        except (SyntaxError, ValueError):
            continue  # python_syntax_ok reports parse failures
        for mod in _top_level_imports(tree):
            if mod in _STDLIB_MODULES or mod in local:
                continue
            dist = _normalize_dist(_IMPORT_TO_DIST.get(mod, mod))
            if declared is not None and dist in declared:
                continue
            providers = {_normalize_dist(p) for p in _PROVIDED_BY.get(mod, ())}
            if declared is not None and providers & declared:
                continue
            missing.add(mod)
    if missing:
        listing = ", ".join(sorted(missing)[:6])
        if declared is None:
            return _gate(False, f"code imports {listing} but there is no requirements.txt")
        return _gate(False, f"imports not covered by requirements.txt: {listing}")
    return _gate(True, "all third-party imports are declared dependencies")


def _bound_names(tree: ast.AST) -> set[str]:
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            bound.update((a.asname or a.name).split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            bound.update(a.asname or a.name for a in node.names)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bound.update(node.names)
    return bound


def _check_no_undefined_module_refs(repo: Path) -> dict:
    """A file that calls `sqlite3.connect(...)` without importing sqlite3 will
    NameError at runtime even though it parses. Flag module-looking names that
    are attribute-accessed but never imported or otherwise bound in the file."""
    problems: list[str] = []
    for f in repo.rglob("*.py"):
        try:
            tree = ast.parse(f.read_text(errors="replace"))
        except (SyntaxError, ValueError):
            continue
        bound = _bound_names(tree)
        seen: set[str] = set()
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                    and isinstance(node.value.ctx, ast.Load)):
                continue
            name = node.value.id
            if name in bound or name in _BUILTIN_NAMES or name in seen:
                continue
            if name in _STDLIB_MODULES or name in _IMPORT_TO_DIST:
                seen.add(name)
                problems.append(f"{f.relative_to(repo)}: uses `{name}.…` without importing it")
    if problems:
        return _gate(False, "; ".join(sorted(problems)[:5]))
    return _gate(True, "no missing-import module references")


def _check_flask_app_context(repo: Path) -> dict:
    """Flask-SQLAlchemy's `db.create_all()` outside `app.app_context()` raises
    "Working outside of application context" the first time the app starts."""
    for f in repo.rglob("*.py"):
        text = f.read_text(errors="replace")
        if "flask" not in text.lower():
            continue
        if re.search(r"\bdb\.create_all\(", text) and "app_context" not in text:
            return _gate(False, f"{f.relative_to(repo)}: db.create_all() without app.app_context()")
    return _gate(True, "no app-context hazards detected")


def _module_exports(tree: ast.AST) -> set[str]:
    """Names importable from a module: top-level defs, classes, assignments and
    re-exported imports."""
    exports: set[str] = set()
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            exports.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    exports.add(target.id)
                elif isinstance(target, ast.Tuple):
                    exports.update(e.id for e in target.elts if isinstance(e, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            exports.add(node.target.id)
        elif isinstance(node, ast.Import):
            exports.update((a.asname or a.name).split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            exports.update(a.asname or a.name for a in node.names)
        elif isinstance(node, (ast.If, ast.Try)):
            # common patterns: guarded defs / try-import fallbacks
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    exports.add(sub.name)
    return exports


def _resolve_local_module(repo: Path, importer: Path, module: str, level: int) -> Path | None:
    """Best-effort resolution of an import to a file inside the repo."""
    if level > 0:  # relative import: anchor at the importing file's package
        base = importer.parent
        for _ in range(level - 1):
            base = base.parent
    else:
        base = repo
    rel = module.replace(".", "/") if module else ""
    for candidate in ((base / f"{rel}.py") if rel else None,
                      (base / rel / "__init__.py") if rel else None,
                      (repo / f"{rel}.py") if rel else None,
                      (repo / rel / "__init__.py") if rel else None):
        if candidate is not None and candidate.exists():
            return candidate
    return None


def _parsed_modules(repo: Path) -> dict[Path, ast.AST]:
    modules: dict[Path, ast.AST] = {}
    for f in repo.rglob("*.py"):
        try:
            modules[f] = ast.parse(f.read_text(errors="replace"))
        except (SyntaxError, ValueError):
            continue  # python_syntax_ok reports these
    return modules


def _check_local_imports_resolve(repo: Path) -> dict:
    """`from storage import get_current_oil_price` must name something the
    local `storage` module actually exports — otherwise the app dies on import
    even though every file parses in isolation."""
    modules = _parsed_modules(repo)
    exports_cache: dict[Path, set[str]] = {}
    problems: list[str] = []
    for f, tree in modules.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            target = _resolve_local_module(repo, f, node.module or "", node.level)
            if target is None or target not in modules:
                continue
            if target not in exports_cache:
                exports_cache[target] = _module_exports(modules[target])
            exported = exports_cache[target]
            for alias in node.names:
                if alias.name == "*" or alias.name in exported:
                    continue
                problems.append(
                    f"{f.relative_to(repo)}: imports `{alias.name}` from "
                    f"`{target.relative_to(repo)}`, which does not define it")
    if problems:
        return _gate(False, "; ".join(sorted(problems)[:5]))
    return _gate(True, "all local imports resolve")


def _function_signatures(tree: ast.AST) -> dict[str, tuple[int, int | None]]:
    """Module-level, undecorated functions → (required_args, max_args or None
    when *args). Decorators can change arity, so decorated defs are skipped."""
    sigs: dict[str, tuple[int, int | None]] = {}
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.decorator_list:
            continue
        a = node.args
        positional = len(a.posonlyargs) + len(a.args)
        required = positional - len(a.defaults)
        max_args = None if a.vararg else positional
        sigs[node.name] = (required, max_args)
    return sigs


def _check_call_arity(repo: Path) -> dict:
    """A test calling `calculate_fuel_price(price)` while the function requires
    two arguments crashes at runtime. Checked conservatively: only direct calls
    by name to module-level undecorated functions defined in the repo, with no
    `*args`/`**kwargs` at the call site."""
    modules = _parsed_modules(repo)
    sigs_by_file = {f: _function_signatures(tree) for f, tree in modules.items()}
    problems: list[str] = []

    for f, tree in modules.items():
        # callables visible by bare name in this file
        visible: dict[str, tuple[int, int | None]] = dict(sigs_by_file.get(f, {}))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                target = _resolve_local_module(repo, f, node.module or "", node.level)
                if target is None or target not in sigs_by_file:
                    continue
                for alias in node.names:
                    sig = sigs_by_file[target].get(alias.name)
                    if sig is not None:
                        visible[alias.asname or alias.name] = sig
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            sig = visible.get(node.func.id)
            if sig is None:
                continue
            if any(isinstance(a, ast.Starred) for a in node.args) or \
                    any(k.arg is None for k in node.keywords):
                continue  # *args/**kwargs at call site — can't judge statically
            required, max_args = sig
            supplied = len(node.args) + len(node.keywords)
            if max_args is not None and len(node.args) > max_args:
                problems.append(f"{f.relative_to(repo)}:{node.lineno}: "
                                f"`{node.func.id}` takes at most {max_args} args, "
                                f"got {len(node.args)}")
            elif supplied < required:
                problems.append(f"{f.relative_to(repo)}:{node.lineno}: "
                                f"`{node.func.id}` requires {required} args, "
                                f"got {supplied}")
    if problems:
        return _gate(False, "; ".join(sorted(problems)[:5]))
    return _gate(True, "call sites match function signatures")


_ENTRY_CANDIDATES = ("main.py", "app.py", "src/main.py", "src/app.py")

_STUB_MARKERS = ("deprecated", "placeholder", "устарел", "заглушка", "moved to",
                 "см. main", "see main.py", "see app.py", "no longer used")


def _is_stub_module(path: Path) -> bool:
    """A file that only says 'deprecated / moved / placeholder', or whose body
    has no real statements, is not an implementation — it must not count as a
    competing entry point (and should not scare the conflict gate)."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return False
    if is_placeholder_content(text):
        return True
    head = text[:400].lower()
    if any(marker in head for marker in _STUB_MARKERS):
        return True
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return False
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Pass)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue  # docstring / bare literal
        if isinstance(node, ast.Raise):
            continue  # raise NotImplementedError
        return False  # found a real statement
    return True


def _module_reference_patterns(rel: str) -> list[str]:
    """Regexes that would count as one entry file referencing another."""
    dotted = rel[:-3].replace("/", ".")           # src/main.py → src.main
    stem = Path(rel).stem                          # → main
    pats = [rf"\bimport\s+{re.escape(dotted)}\b", rf"\bfrom\s+{re.escape(dotted)}\s+import\b"]
    if dotted != stem:
        pats += [rf"\bfrom\s+{re.escape(dotted.rsplit('.', 1)[0])}\s+import\s+.*\b{re.escape(stem)}\b"]
    else:
        pats += [rf"\bimport\s+{re.escape(stem)}\b", rf"\bfrom\s+{re.escape(stem)}\s+import\b"]
    return pats


def _check_no_conflicting_entrypoints(repo: Path) -> dict:
    """Two unrelated implementations of the same project (e.g. a root `app.py`
    stack AND an unconnected `src/main.py` stack) must not ship in one archive
    — that is an unresolved merge, not a deliverable. Deprecated/placeholder
    stubs are not implementations and do not conflict."""
    present = [rel for rel in _ENTRY_CANDIDATES
               if (repo / rel).exists() and not _is_stub_module(repo / rel)]
    if len(present) < 2:
        return _gate(True, "single entry point implementation")
    texts = {rel: (repo / rel).read_text(errors="replace") for rel in present}
    for a in present:
        for b in present:
            if a == b:
                continue
            if any(re.search(p, texts[a]) for p in _module_reference_patterns(b)):
                return _gate(True, f"entry files are related ({a} references {b})")
    return _gate(False, "unrelated parallel implementations: " + ", ".join(present))


def _check_no_placeholder_files(repo: Path) -> dict:
    """`(no changes)` bodies and scratch-named files (temp/draft/final2/copy)
    are agent debris, never deliverables. The extractor and integration pass
    stop these upstream — this gate is the last line."""
    bad: list[str] = []
    for f in repo.rglob("*"):
        if not f.is_file():
            continue
        rel = str(f.relative_to(repo))
        if is_junk_filename(rel):
            bad.append(f"{rel} (junk name)")
            continue
        try:
            if f.stat().st_size > 4096:
                continue
            if is_placeholder_content(f.read_text(errors="replace")):
                bad.append(rel)
        except (OSError, UnicodeDecodeError):
            continue
    if bad:
        return _gate(False, f"placeholder/junk files: {', '.join(sorted(bad)[:5])}")
    return _gate(True, "no placeholder files")


_DOC_STUB_MARKERS = ("lorem ipsum", "заглушка", "placeholder text",
                     "structured contribution for", "структурированный вклад")


def _check_document_is_deliverable(workspace: Path) -> dict:
    """Document projects must ship a real document: substantive, not a stub,
    and with no unextracted FILE-marker code hiding inside it."""
    doc = workspace / "artifacts" / "main-document.md"
    ok, size = _artifact_is_substantive(workspace, "artifacts/main-document.md",
                                        _MIN_DOCUMENT_CHARS)
    if not ok:
        return _gate(False, f"main-document.md missing or too short ({size} chars)")
    text = doc.read_text(errors="replace")
    low = text.lower()
    for marker in _DOC_STUB_MARKERS:
        if marker in low:
            return _gate(False, f"main-document.md contains stub text: {marker!r}")
    if re.search(r"(?im)^[#=*\s]*FILE:\s", text) and extract_repo_files(text):
        return _gate(False, "main-document.md contains unextracted FILE-marker code")
    return _gate(True, f"substantive document ({size} chars)")


# Gates that must pass for a full "release" (blocking). Others are advisory.
HARD_GATES = {"dependencies_valid", "python_syntax_ok", "entrypoint_present",
              "imports_covered", "undefined_module_refs", "flask_app_context",
              "no_conflicting_entrypoints", "no_placeholder_files",
              "local_imports_resolve", "call_arity_ok",
              "install_matches_repo", "readme_references_real_files"}


def run_gates(workspace: Path, is_code_project: bool) -> dict:
    """Run deterministic gates over the workspace. Returns
    {"gates": {name: {passed, detail}}, "passed": bool, "failed": [names],
     "hard_failed": [names]}."""
    if not is_code_project:
        gates = {"main_document_present": _check_document_is_deliverable(workspace)}
        failed = [k for k, g in gates.items() if not g["passed"]]
        return {"gates": gates, "passed": not failed, "failed": failed,
                "hard_failed": failed}

    repo = workspace / "repo"
    if not repo.exists() or not any(repo.iterdir()):
        gates = {"repo_present": _gate(False, "repo/ is empty — nothing was built")}
        return {"gates": gates, "passed": False, "failed": ["repo_present"],
                "hard_failed": ["repo_present"]}

    gates = {
        "repo_present": _gate(True, "repo/ has files"),
        "dependencies_valid": _check_dependencies(repo),
        "entrypoint_present": _check_entrypoint(repo),
        "python_syntax_ok": _check_python_syntax(repo),
        "imports_covered": _check_imports_covered(repo),
        "undefined_module_refs": _check_no_undefined_module_refs(repo),
        "local_imports_resolve": _check_local_imports_resolve(repo),
        "call_arity_ok": _check_call_arity(repo),
        "flask_app_context": _check_flask_app_context(repo),
        "no_conflicting_entrypoints": _check_no_conflicting_entrypoints(repo),
        "no_placeholder_files": _check_no_placeholder_files(repo),
        "install_matches_repo": _check_install_matches(workspace, repo),
        "readme_references_real_files": _check_readme_references_real_files(repo),
    }
    failed = [k for k, g in gates.items() if not g["passed"]]
    hard_failed = [k for k in failed if k in HARD_GATES or k == "repo_present"]
    return {"gates": gates, "passed": not failed, "failed": failed,
            "hard_failed": hard_failed}


def issues_from_gate_failures(db, project_id: str, gate_result: dict) -> int:
    """Turn each failed deterministic gate into a tracked issue so review/repair
    (and the admin) can see exactly what a real run of the code broke on.
    Idempotent: an existing open issue for the same gate is not duplicated."""
    from ..models import Issue

    created = 0
    for name in gate_result.get("failed", []):
        detail = gate_result["gates"].get(name, {}).get("detail", "")
        title = f"GATE-{name}"
        exists = (db.query(Issue)
                  .filter(Issue.project_id == project_id, Issue.title == title,
                          Issue.status == "open").first())
        if exists:
            continue
        severity = "critical" if name in HARD_GATES or name == "repo_present" else "major"
        db.add(Issue(project_id=project_id, phase_key="final_audit", severity=severity,
                     title=title, description=detail,
                     suggested_fix="Fix deterministic build gate before release."))
        created += 1
    if created:
        db.commit()
    return created
