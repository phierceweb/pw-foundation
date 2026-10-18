"""Consumer wiring — ``pw-setup`` puts what the installed packages ship where people and coding
assistants look. The read-only report for ``pw-doctor`` is :mod:`pw_foundation._wiring_check`.

It links ``docs/pw-foundation`` (and ``docs/pw-core`` when pw-core is installed) to the bundled docs,
copies each package's starter rules into ``.ai/rules/`` (an edited rule is the project's and is
never touched; an unedited copy follows the shipped one), points ``.claude/`` and ``.cursor/`` at
``.ai/``, keeps the links out of git, and writes or migrates ``.pw-guards.toml``. It refuses to
replace anything real, and refuses a directory that is not a project.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import os
from pathlib import Path

from pw_foundation._wiring_rules import install_rules

_LEGACY_LINK = "pf-core"
_CORE_PACKAGE = "pw_core"
_EDITORS = (".claude", ".cursor")
_AI_DIRS = ("rules", "plans", "skills")
_GUARDS_CONFIG = ".pw-guards.toml"
_LEGACY_GUARDS = ".pf-guards.toml"
_LEGACY_REWRITES = {  # the old gate config's spellings -> today's, applied when migrating it
    "[tool.pf_guards": "[tool.pw_guards",
    ".pf-guards.toml": ".pw-guards.toml",
    "pf_core.guards": "pw_foundation.guards",
    "pf-guards": "pw-guards",
}
_PROJECT_MARKERS = ("pyproject.toml", "setup.cfg", "setup.py", ".git")
_GITIGNORE_HEADER = "# pw-setup: links into this machine's venv"


def _package_dir(pkg: str) -> Path | None:
    """Where ``pkg`` is installed, without importing it; ``None`` for absent or a bare directory."""
    try:
        spec = importlib.util.find_spec(pkg)
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.origin:
        return None
    return Path(spec.origin).resolve().parent


def installed_docs_dir(pkg: str = "pw_foundation") -> Path:
    """The bundled docs directory of an installed package."""
    root = _package_dir(pkg)
    if root is None:
        raise ModuleNotFoundError(pkg)
    return root / "docs"


def installed_rules_dir(pkg: str = "pw_foundation") -> Path:
    """The starter rules an installed package ships for consumers."""
    root = _package_dir(pkg)
    if root is None:
        raise ModuleNotFoundError(pkg)
    return root / "rules"


def _installed() -> list[tuple[str, Path]]:
    """``(dist name, package dir)`` for pw-foundation and, when installed, pw-core."""
    base = _package_dir("pw_foundation")
    assert base is not None  # we are running from it
    out = [("pw-foundation", base)]
    core = _package_dir(_CORE_PACKAGE)
    if core is not None:
        out.append(("pw-core", core))
    return out


def _docs_targets() -> list[tuple[str, Path]]:
    return [(name, root / "docs") for name, root in _installed() if (root / "docs").is_dir()]


def _rule_sources() -> list[tuple[str, Path]]:
    return [(name, root / "rules") for name, root in _installed() if (root / "rules").is_dir()]


def _installed_version(dist: str) -> str | None:
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return None


def _guess_scan_root(root: Path) -> str | None:
    """``src/<package>`` when there is exactly one, else a Python ``app/`` tree, else nothing."""
    src = root / "src"
    pkgs = [p for p in src.iterdir() if (p / "__init__.py").is_file()] if src.is_dir() else []
    app = root / "app"
    app_py = app.is_dir() and any(app.rglob("*.py"))
    if app_py:
        return "app"
    if len(pkgs) == 1:
        return f"src/{pkgs[0].name}"
    return None


class _Wiring:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.actions: list[str] = []
        self.errors: list[str] = []

    def _rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix()

    def _is_project(self) -> bool:
        if self.root == Path.home().resolve():
            self.errors.append(
                "refusing to wire your home directory — run pw-setup from a project root"
            )
            return False
        if not any((self.root / m).exists() for m in _PROJECT_MARKERS):
            self.errors.append(
                f"{self.root} has no pyproject.toml, setup.cfg, setup.py or .git — run pw-setup from a "
                "project root, or pass --project-root"
            )
            return False
        return True

    def symlink(self, link: Path, target: Path, *, conflict: str) -> None:
        rel = self._rel(link)
        try:
            if link.is_symlink():
                current = link.parent / os.readlink(link)
                if link.exists() and current.resolve() == (link.parent / target).resolve():
                    self.actions.append(f"ok: {rel}")
                    return
                link.unlink()
            elif link.exists():
                self.errors.append(conflict)
                return
            link.parent.mkdir(parents=True, exist_ok=True)
            link.symlink_to(target)
            self.actions.append(f"linked: {rel} -> {target}")
        except OSError as e:
            self.errors.append(
                f"could not create the symlink {rel}: {e} — on Windows, symlinks need Developer Mode "
                "or an elevated shell"
            )

    # -- steps -----------------------------------------------------------------------------

    def rules(self) -> None:
        install_rules(self.root, _rule_sources(), self.symlink, self.actions)

    def docs(self) -> None:
        for name, target in _docs_targets():
            self.symlink(
                self.root / "docs" / name,
                target,
                conflict=f"docs/{name} is a real directory — move it aside; pw-setup links the installed docs there",
            )
        if _CORE_PACKAGE not in {n.replace("-", "_") for n, _ in _installed()}:
            stale = self.root / "docs" / "pw-core"
            if stale.is_symlink():
                stale.unlink()
                self.actions.append("removed: docs/pw-core link (pw-core is not installed)")
        legacy = self.root / "docs" / _LEGACY_LINK
        if legacy.is_symlink():
            legacy.unlink()
            self.actions.append(f"removed: legacy docs/{_LEGACY_LINK} symlink")
        elif legacy.is_dir():
            self.actions.append(
                f"note: docs/{_LEGACY_LINK} is a real directory, left alone — remove it so assistants "
                "stop reading stale docs"
            )

    def editors(self) -> None:
        for editor in _EDITORS:
            for sub in _AI_DIRS:
                self.symlink(
                    self.root / editor / sub,
                    Path("..") / ".ai" / sub,
                    conflict=f"{editor}/{sub} is a real directory — move its files into .ai/{sub}/ "
                    "(rules into .ai/rules/, skills into .ai/skills/), delete the emptied directory, re-run",
                )

    def gitignore(self) -> None:
        gi = self.root / ".gitignore"
        if not gi.exists() and not (self.root / ".git").exists():
            return
        wanted = [f"docs/{name}" for name, _ in _docs_targets()]
        lines = gi.read_text().splitlines() if gi.exists() else []
        missing = [w for w in wanted if w not in lines]
        if not missing:
            self.actions.append("ok: .gitignore covers the docs links")
            return
        block = (
            []
            if _GITIGNORE_HEADER in lines
            else ([""] if lines and lines[-1] else []) + [_GITIGNORE_HEADER]
        )
        gi.write_text("\n".join([*lines, *block, *missing]) + "\n")
        self.actions.append(f"gitignore: added {', '.join(missing)}")

    def guards_config(self) -> None:
        new, old = self.root / _GUARDS_CONFIG, self.root / _LEGACY_GUARDS
        if old.exists() and new.exists():
            self.errors.append(
                f"both {_LEGACY_GUARDS} and {_GUARDS_CONFIG} exist — fold the old one into {_GUARDS_CONFIG} "
                f"and delete it; the gate refuses to run while {_LEGACY_GUARDS} is present"
            )
            return
        if old.exists():
            text = old.read_text(encoding="utf-8")
            for before, after in _LEGACY_REWRITES.items():
                text = text.replace(before, after)
            new.write_text(text, encoding="utf-8")
            old.unlink()
            self.actions.append(
                f"migrated: {_LEGACY_GUARDS} -> {_GUARDS_CONFIG} (table renamed to [tool.pw_guards])"
            )
            return
        if new.exists():
            self.actions.append(f"ok: {_GUARDS_CONFIG}")
            return
        scan = _guess_scan_root(self.root)
        if scan is None:
            self.actions.append(
                f"note: could not tell the scan root (no single src/<package>, no Python app/) — "
                f"write {_GUARDS_CONFIG} by hand"
            )
            return
        new.write_text(
            "# Structural gate config — `pw-guards` reads this file. See docs/pw-foundation/guards.md.\n"
            f'[tool.pw_guards]\nroot = "{scan}"\n',
            encoding="utf-8",
        )
        self.actions.append(f'created: {_GUARDS_CONFIG} (root = "{scan}")')

    def run(self) -> None:
        if not self._is_project():
            return
        self.rules()
        self.docs()
        self.editors()
        self.gitignore()
        self.guards_config()


def _ensure_wiring(root: Path) -> tuple[list[str], list[str]]:
    """Idempotently wire a consumer. Returns ``(actions, errors)``."""
    w = _Wiring(Path(root))
    w.run()
    return w.actions, w.errors


def _pin(dist: str) -> str:
    version = _installed_version(dist)
    if version is None:
        return f'"{dist}" (installed from a source tree — pin its release)'
    major, minor = version.split(".")[:2]
    return f'"{dist}~={major}.{minor}"'


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pw-setup",
        description="Wire a project to the installed pw-foundation (and pw-core): docs links, starter "
        "rules in .ai/rules, editor symlinks, .gitignore entries, .pw-guards.toml. Idempotent; "
        "never overwrites what is yours.",
    )
    parser.add_argument("--project-root", default=".", help="consumer repo root (default: cwd)")
    args = parser.parse_args(argv)
    actions, errors = _ensure_wiring(Path(args.project_root))
    for line in actions:
        print(f"  + {line}")
    for line in errors:
        print(f"  ! {line}")
    if errors:
        return 1
    names = [name for name, _ in _installed()]
    print(f"\n  Pin in pyproject.toml: {' and '.join(_pin(n) for n in names)}")
    docs = " and ".join(f"docs/{n}/modules.md" for n in names)
    print(f"  CLAUDE.md: point assistants at .ai/rules/ and {docs}.")
    return 0


__all__ = ["installed_docs_dir", "installed_rules_dir", "run_cli"]
