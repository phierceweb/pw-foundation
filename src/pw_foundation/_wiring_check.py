"""The read-only wiring report ``pw-doctor`` prints: what ``pw-setup`` would do or has done."""

from __future__ import annotations

import re
from pathlib import Path

from pw_foundation import wiring as _w

_RULE_LEGACY = re.compile(r"\bpf_core\b|docs/pf-core")  # drift the doctor warns about

Row = tuple[str, str, str]


def _docs_rows(root: Path) -> list[Row]:
    rows: list[Row] = []
    for name, target in _w._docs_targets():
        link = root / "docs" / name
        row = f"docs_link.{name}"
        if link.is_symlink():
            if not link.exists():
                rows.append((row, "FAIL", f"docs/{name} is a broken symlink — re-run pw-setup"))
            elif link.resolve() != target.resolve():
                rows.append(
                    (
                        row,
                        "FAIL",
                        f"docs/{name} points at a different copy ({link.resolve()}) — re-run pw-setup",
                    )
                )
            else:
                rows.append((row, "PASS", f"docs/{name} -> {link.resolve()}"))
        elif link.exists():
            rows.append((row, "FAIL", f"docs/{name} exists but is not a symlink"))
        else:
            rows.append((row, "WARN", f"docs/{name} missing — run pw-setup"))
    return rows


def _rules_row(root: Path) -> Row:
    shipped: dict[str, str] = {}
    for origin, src in _w._rule_sources():
        for f in src.glob("*.md"):
            shipped.setdefault(f.name, origin)
    rules_dir = root / ".ai" / "rules"
    present = [n for n in shipped if (rules_dir / n).is_file()]
    missing = sorted(set(shipped) - set(present))
    if missing:
        return ("rules", "WARN", f".ai/rules is missing {', '.join(missing)} — run pw-setup")
    broken = sorted(f"{n[:-3]}.mdc" for n in present if not (rules_dir / f"{n[:-3]}.mdc").is_file())
    if broken:
        return ("rules", "FAIL", f"broken rule link(s): {', '.join(broken)} — re-run pw-setup")
    legacy = sorted(
        n for n in present if _RULE_LEGACY.search((rules_dir / n).read_text(errors="replace"))
    )
    if legacy:
        return (
            "rules",
            "WARN",
            f"{', '.join(legacy)} still name the old framework — re-read them against docs/pw-foundation",
        )
    return ("rules", "PASS", f".ai/rules has every shipped rule ({len(shipped)})")


def _editor_row(root: Path) -> Row:
    real: list[str] = []
    missing: list[str] = []
    for editor in _w._EDITORS:
        for sub in _w._AI_DIRS:
            link = root / editor / sub
            if (
                link.is_symlink()
                and link.exists()
                and link.resolve() == (root / ".ai" / sub).resolve()
            ):
                continue
            (real if link.exists() and not link.is_symlink() else missing).append(f"{editor}/{sub}")
    if real:
        return (
            "editor_links",
            "FAIL",
            f"{', '.join(real)} are real directories — move their files into .ai/ and re-run pw-setup",
        )
    if missing:
        return ("editor_links", "WARN", f"{', '.join(missing)} not linked to .ai/ — run pw-setup")
    return ("editor_links", "PASS", ".claude/ and .cursor/ point at .ai/")


def _guards_row(root: Path) -> Row:
    if (root / _w._LEGACY_GUARDS).exists():
        return (
            "guards_config",
            "FAIL",
            f"{_w._LEGACY_GUARDS} present — the gate refuses to run; pw-setup migrates it",
        )
    if (root / _w._GUARDS_CONFIG).is_file():
        return ("guards_config", "PASS", f"{_w._GUARDS_CONFIG} present")
    return ("guards_config", "WARN", f"no {_w._GUARDS_CONFIG} — run pw-setup")


def _leftovers_row(root: Path) -> Row:
    found: list[str] = []
    if (root / "docs" / _w._LEGACY_LINK).is_dir():
        found.append(f"docs/{_w._LEGACY_LINK} is a real directory")
    installed = {name for name, _ in _w._installed()}
    if "pw-core" not in installed and (root / "docs" / "pw-core").is_symlink():
        found.append("docs/pw-core link with pw-core not installed")
    if found:
        return (
            "leftovers",
            "WARN",
            "; ".join(found) + " — pw-setup removes links, directories are yours",
        )
    return ("leftovers", "PASS", "none")


def _check_wiring(root: Path | None = None) -> list[Row]:
    root = (Path(root) if root is not None else Path.cwd()).resolve()
    if (root / "src" / "pw_foundation").is_dir() or (root / "src" / _w._CORE_PACKAGE).is_dir():
        return [("context", "SKIP", "framework checkout — consumer wiring n/a")]
    if not any((root / m).exists() for m in _w._PROJECT_MARKERS):
        return [
            (
                "context",
                "SKIP",
                "not a project root (no pyproject.toml, setup.cfg, setup.py or .git)",
            )
        ]
    return [
        *_docs_rows(root),
        _rules_row(root),
        _editor_row(root),
        _guards_row(root),
        _leftovers_row(root),
    ]
