"""No pf-era name survives in the tree (CHANGELOG history and listed exceptions aside)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = re.compile(
    r"\bpf_core\b|\bpf-core\b|\bPF_[A-Z]|\bpf-(guards|doctor|setup|jobs|eval|export)\b|\bpf[-_ ]|\bpf\b"
    r"|pf_guards|\.pf-guards\.toml|\bpf_(schema|tables|connection|engine)\b"
)
# (path, substring a line may carry a legacy name in); "" allows the whole file.
ALLOW: tuple[tuple[str, str], ...] = (
    ("README.md", "formerly"),
    ("src/pw_foundation/docs/INSTALLATION.md", "formerly"),
    ("src/pw_foundation/docs/INSTALLATION.md", "legacy"),
    ("src/pw_foundation/docs/guards.md", "leftover"),
    ("src/pw_foundation/docs/wiring.md", "legacy"),
    ("src/pw_foundation/guards/structure.py", "_LEGACY_CONFIG"),
    ("src/pw_foundation/guards/config.py", "pf_guards"),
    ("src/pw_foundation/wiring.py", "_LEGACY"),
    ("src/pw_foundation/wiring.py", '": "'),
    ("src/pw_foundation/_wiring_check.py", "_RULE_LEGACY"),
    ("tests/test_guards_cli.py", ".pf-guards.toml"),
    ("tests/test_guards_cli.py", "pf_guards"),
    ("tests/test_guards_config.py", "pf_guards"),
    ("tests/test_wiring.py", ""),
    ("tests/test_no_legacy_names.py", ""),
)
SKIP = {"CHANGELOG.md"}


def _text_files() -> list[Path]:
    # Tracked plus untracked-but-not-ignored, so the gate also covers a tree before its first commit.
    out = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = []
    for rel in out.stdout.split():
        p = ROOT / rel
        if rel in SKIP or not p.is_file():
            continue
        try:
            p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        files.append(p)
    return files


def _allowed(rel: str, line: str) -> bool:
    return any(rel == path and (not needle or needle in line) for path, needle in ALLOW)


def test_no_legacy_pf_names() -> None:
    hits = []
    for p in _text_files():
        rel = p.relative_to(ROOT).as_posix()
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if LEGACY.search(line) and not _allowed(rel, line):
                hits.append(f"{rel}:{n}: {line.strip()[:100]}")
    assert not hits, "legacy pf-era names:\n" + "\n".join(hits)


def test_every_allow_entry_is_still_needed() -> None:
    used = set()
    for p in _text_files():
        rel = p.relative_to(ROOT).as_posix()
        for line in p.read_text(encoding="utf-8").splitlines():
            if LEGACY.search(line):
                used |= {
                    (path, needle)
                    for path, needle in ALLOW
                    if rel == path and (not needle or needle in line)
                }
    stale = sorted(set(ALLOW) - used - {("tests/test_no_legacy_names.py", "")})
    assert stale == [], f"ALLOW entries with no matching line left: {stale}"
