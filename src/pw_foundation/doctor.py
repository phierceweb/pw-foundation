"""Runtime ground-truth attestation for pw-foundation installs.

``pw-doctor`` (or ``python -m pw_foundation.doctor``) prints verified facts about the
current environment: which copy of pw-foundation — and of pw-core, when installed — is
loaded, interpreter and venv, resolved env vars (redacted), consumer wiring.
``--release`` adds tag / version / CHANGELOG / tree checks. pw-core contributes
its own checks (extras, router config, dependency versions, ``--db``) through
:data:`PLUGIN_MODULE`.

Invariants: doctor never writes, never touches the network except pw-core's
opt-in ``--db`` connect (``--release`` runs read-only local git commands), and
never imports consumer application code. Exit code is ``0`` when no check FAILs
(WARNs don't flip it), ``1`` otherwise.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import sys
import tomllib
from pathlib import Path

from pw_foundation._doctor_release import release_checks
from pw_foundation._doctor_types import CheckResult, redact_value
from pw_foundation._plugins import optional_module
from pw_foundation.exceptions import ConfigurationError

_MIN_PY = (3, 12)

# Env vars pw-foundation itself reads; pw-core's plugin reports its own.
_ENV_VARS = ("LOG_LEVEL", "LOG_FILE")

# pw-core's ``checks(**options) -> list[CheckResult]`` extends the report when installed. It
# receives every CLI flag as a keyword (``db=`` today) and must accept ones it does not know.
_PLUGIN_MODULE = "pw_core.doctor"
_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")

_PACKAGES = ("pw_foundation", "pw_core")


def _package_roots() -> dict[str, Path]:
    """Installed package -> its directory, for each of ``_PACKAGES`` present (nothing imported)."""
    roots: dict[str, Path] = {}
    for pkg in _PACKAGES:
        spec = importlib.util.find_spec(pkg)
        if spec is not None and spec.origin:
            roots[pkg] = Path(spec.origin).resolve().parent
    return roots


def _installed_version(dist: str) -> str:
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _adjacent_pyproject_version(root: Path) -> str | None:
    """Version from the pyproject.toml two levels above the package (src layout).

    Present only for editable/source installs; site-packages installs return
    ``None``.
    """
    pyproject = root.parent.parent / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        with pyproject.open("rb") as fh:
            return tomllib.load(fh)["project"]["version"]
    except Exception:
        return None


def _installed_editable(dist: str) -> bool | None:
    """PEP 610: whether the install was editable, or ``None`` when nothing recorded it."""
    try:
        text = importlib.metadata.distribution(dist).read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        return None
    if not text:
        return None
    try:
        return bool(json.loads(text).get("dir_info", {}).get("editable", False))
    except ValueError:
        return None


def _kind(dist: str, root: Path) -> str:
    editable = _installed_editable(dist)
    if editable is None:  # no direct_url.json: fall back to where the files sit
        editable = not any(part in ("site-packages", "dist-packages") for part in root.parts)
    return "editable" if editable else "installed"


def check_copy() -> list[CheckResult]:
    roots = _package_roots()
    results: list[CheckResult] = []
    kinds: dict[str, str] = {}
    for pkg, root in roots.items():
        dist = pkg.replace("_", "-")
        kind = kinds[pkg] = _kind(dist, root)
        version = _installed_version(dist)
        detail = f"{root} ({kind}), version {version}"
        status = "PASS"
        if kind == "editable":
            src_version = _adjacent_pyproject_version(root)
            if src_version is not None and src_version != version:
                status = "WARN"
                detail += (
                    f" — adjacent pyproject says {src_version}; "
                    "stale editable install? reinstall with pip install -e ."
                )
        results.append(CheckResult("copy", dist, status, detail))
    if len(set(kinds.values())) > 1:
        parts = "; ".join(f"{pkg.replace('_', '-')} {kinds[pkg]} at {roots[pkg]}" for pkg in roots)
        results.append(
            CheckResult(
                "copy",
                "mixed",
                "WARN",
                f"{parts} — install both editable (pip install -e ../pw-foundation -e ../pw-core) "
                "or both from PyPI",
            )
        )
    return results


def check_python() -> list[CheckResult]:
    cur = sys.version_info[:2]
    detail = f"python {cur[0]}.{cur[1]}, venv {sys.prefix}"
    if cur < _MIN_PY:
        return [
            CheckResult(
                "python",
                "interpreter",
                "FAIL",
                f"{detail} — pw-foundation requires >= {_MIN_PY[0]}.{_MIN_PY[1]}",
            )
        ]
    return [CheckResult("python", "interpreter", "PASS", detail)]


def check_env() -> list[CheckResult]:
    # Load the consumer's .env first so the report shows the EFFECTIVE env the
    # app would boot with, not just the bare shell. Existing shell vars win
    # (dotenv default), matching consumer boot behavior.
    dotenv_path = Path.cwd() / ".env"
    source = "shell only (no .env in cwd)"
    if dotenv_path.is_file():
        from dotenv import load_dotenv

        load_dotenv(dotenv_path)
        source = f".env loaded from {dotenv_path}"
    lines = [source]
    for var in _ENV_VARS:
        value = os.environ.get(var)
        lines.append(f"{var}={redact_value(var, value)}" if value else f"{var} unset")
    return [CheckResult("env", "resolution", "PASS", "; ".join(lines))]


def check_consumer_wiring() -> list[CheckResult]:
    from pw_foundation._wiring_check import _check_wiring

    return [CheckResult("wiring", name, status, detail) for name, status, detail in _check_wiring()]


def _plugin_checks(**options: object) -> list[CheckResult]:
    """pw-core's checks when it is installed; a broken plugin is a FAIL row, never a crash."""
    try:
        plugin = optional_module(_PLUGIN_MODULE)
    except ConfigurationError as e:
        return [CheckResult("plugin", _PLUGIN_MODULE, "FAIL", str(e))]
    if plugin is None:
        return []
    try:
        rows = list(plugin.checks(**options))
    except Exception as e:  # a plugin bug must not take the whole report down
        return [
            CheckResult(
                "plugin", _PLUGIN_MODULE, "FAIL", f"checks() raised {type(e).__name__}: {e}"
            )
        ]
    out: list[CheckResult] = []
    for row in rows:
        if isinstance(row, CheckResult) and row.status in _STATUSES:
            out.append(row)
        else:
            detail = (
                f"row {getattr(row, 'group', '?')}.{getattr(row, 'name', '?')} has unknown "
                f"status {getattr(row, 'status', row)!r}"
            )
            out.append(CheckResult("plugin", _PLUGIN_MODULE, "FAIL", detail))
    return out


_CORE_CHECKS = (check_copy, check_python, check_env, check_consumer_wiring)


def run_checks(*, db: bool = False, release: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []
    for fn in _CORE_CHECKS:
        results.extend(fn())
    results.extend(_plugin_checks(db=db))
    if release:
        results.extend(release_checks())
    return results


def run_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pw-doctor", description="pw-foundation runtime ground-truth attestation"
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="include pw-core's read-only database checks (connect + migration state)",
    )
    parser.add_argument(
        "--release",
        action="store_true",
        help="include release-state checks (tag vs pyproject vs CHANGELOG, dirty tree)",
    )
    args = parser.parse_args(argv)

    from rich.console import Console
    from rich.table import Table

    results = run_checks(db=args.db, release=args.release)
    table = Table(title="pw-doctor", show_lines=False)
    table.add_column("status", no_wrap=True)
    table.add_column("check", no_wrap=True)
    table.add_column("detail", overflow="fold")
    styles = {"PASS": "green", "WARN": "yellow", "FAIL": "red", "SKIP": "dim"}
    for r in results:
        table.add_row(f"[{styles[r.status]}]{r.status}[/]", f"{r.group}.{r.name}", r.detail)
    console = Console()
    console.print(table)

    counts = {s: sum(1 for r in results if r.status == s) for s in styles}
    console.print(
        f"{counts['PASS']} pass, {counts['WARN']} warn, "
        f"{counts['FAIL']} fail, {counts['SKIP']} skip"
    )
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(run_cli())


__all__ = ["CheckResult", "redact_value", "run_checks", "run_cli"]
