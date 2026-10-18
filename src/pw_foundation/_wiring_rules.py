"""The rules step of ``pw-setup``: starter rules into ``.ai/rules/``, edited ones left alone."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

_AI_DIRS = ("rules", "plans", "skills")
_MANIFEST = ".pw-setup.json"  # in .ai/rules: the hash of each copy pw-setup wrote

Symlink = Callable[..., None]  # _Wiring.symlink(link, target, *, conflict=...)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def install_rules(
    root: Path, sources: list[tuple[str, Path]], symlink: Symlink, actions: list[str]
) -> None:
    """Copy every shipped rule that is not already the project's; keep edits; update unedited copies."""
    rules_dir = root / ".ai" / "rules"
    for sub in _AI_DIRS:
        d = root / ".ai" / sub
        d.mkdir(parents=True, exist_ok=True)
        if sub != "rules" and not any(d.iterdir()):
            (d / ".gitkeep").touch()
    manifest_path = rules_dir / _MANIFEST
    manifest: dict[str, str] = (
        json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    )
    seen: dict[str, str] = {}
    for origin, src in sources:
        for rule in sorted(src.glob("*.md")):
            if rule.name in seen:
                actions.append(
                    f"collision: .ai/rules/{rule.name} is shipped by {seen[rule.name]} and {origin} — "
                    f"{seen[rule.name]}'s copy applies"
                )
                continue
            seen[rule.name] = origin
            _install_rule(rules_dir, rule, origin, manifest, symlink, actions)
    text = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    if not manifest_path.is_file() or manifest_path.read_text() != text:
        manifest_path.write_text(text)


def _install_rule(
    rules_dir: Path,
    src: Path,
    origin: str,
    manifest: dict[str, str],
    symlink: Symlink,
    actions: list[str],
) -> None:
    dest = rules_dir / src.name
    rel = f".ai/rules/{src.name}"
    shipped = src.read_bytes()
    shipped_hash = _sha(shipped)
    if dest.is_symlink() and not dest.exists():
        dest.unlink()
    if not dest.exists():
        dest.write_bytes(shipped)
        manifest[src.name] = shipped_hash
        actions.append(f"rule: {rel} from {origin}")
    else:
        current = _sha(dest.read_bytes())
        if current == shipped_hash:
            manifest[src.name] = shipped_hash
            actions.append(f"ok: {rel}")
        elif manifest.get(src.name) == current:
            dest.write_bytes(shipped)
            manifest[src.name] = shipped_hash
            actions.append(f"updated: {rel} from {origin} (an unedited copy of an older version)")
        else:
            actions.append(f"kept: {rel} (edited — yours; {origin}'s copy not applied)")
    symlink(
        dest.with_suffix(".mdc"),
        Path(src.name),
        conflict=f"{rel[:-3]}.mdc is a real file — remove it so Cursor can follow the link",
    )
