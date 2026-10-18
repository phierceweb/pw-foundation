"""Every pw_foundation name or path the shipped docs and docstrings mention must exist."""

from __future__ import annotations

import importlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "pw_foundation"
DOTTED = re.compile(r"\bpw_foundation(?:\.[A-Za-z_][A-Za-z0-9_]*)+")
PATHS = re.compile(r"\bpw_foundation/[A-Za-z0-9_/]+\.py\b")


def _resolves(dotted: str) -> bool:
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        try:
            mod = importlib.import_module(".".join(parts[:i]))
        except ImportError:
            continue
        obj = mod
        for attr in parts[i:]:
            if not hasattr(obj, attr):
                return False
            obj = getattr(obj, attr)
        return True
    return False


def _sources() -> list[Path]:
    return [*sorted((SRC / "docs").glob("*.md")), *sorted(SRC.rglob("*.py")), ROOT / "README.md"]


def test_every_dotted_pw_foundation_reference_resolves() -> None:
    missing = []
    for path in _sources():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in DOTTED.finditer(line):
                name = m.group(0).rstrip(".")
                if not _resolves(name):
                    missing.append(f"{path.relative_to(ROOT)}:{lineno}: {name}")
    assert missing == [], "\n".join(missing)


def test_every_pw_foundation_file_path_in_docs_exists() -> None:
    missing = []
    for path in _sources():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for m in PATHS.finditer(line):
                if not (ROOT / "src" / m.group(0)).is_file():
                    missing.append(f"{path.relative_to(ROOT)}:{lineno}: {m.group(0)}")
    assert missing == [], "\n".join(missing)
