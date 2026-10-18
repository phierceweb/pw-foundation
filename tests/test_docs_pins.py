"""Docs drift gates: version examples in public prose must track released state."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A pw-foundation pin as consumers write it: two components (``~=1.0`` accepts every 1.x).
BASE_PIN_RE = re.compile(r"pw-foundation(?:\[[^\]]*\])?~=\s*(\d+)\.(\d+)(\.\d+)?")

# Real dependency versions share version-ish shapes; a line is exempt when the
# match sits next to one of these package names.
_DEP_VERSIONS = (
    "ruff",
    "mypy",
    "pytest",
    "python-dotenv",
    "pyyaml",
    "structlog",
    "nanoid",
    "rich",
    "build",
    "pydantic",
)


def _current_version() -> tuple[int, int]:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    major, minor = version.split(".")[:2]
    return int(major), int(minor)


def _versionish_re(major: int) -> re.Pattern[str]:
    """Tokens on this major's line: ``vM.N``, the ``pre-M.N`` idiom, or bare ``M.N.P``.

    Bare two-component decimals (scores like 0.85) are deliberately not matched.
    """
    return re.compile(
        rf"(?<![\w.])v{major}\.(\d{{1,3}})(?!\d)"
        rf"|(?<![\w.])pre-{major}\.(\d{{1,3}})(?!\d)"
        rf"|(?<![\d.]){major}\.(\d{{1,3}})\.\d"
    )


def _offending_minors(line: str, released_minor: int, *, major: int = 1) -> list[int]:
    """Minors referenced on the released major's line that are ahead of ``released_minor``."""
    minors = [
        int(g) for m in _versionish_re(major).finditer(line) for g in m.groups() if g is not None
    ]
    return [m for m in minors if m > released_minor]


def _pin_example_files() -> list[Path]:
    return [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        *sorted((ROOT / "src/pw_foundation/docs").rglob("*.md")),
        *sorted((ROOT / ".ai/rules").glob("*.md")),
    ]


def test_base_pin_examples_use_two_components():
    """``pw-foundation~=1.0.0`` accepts only 1.0.x and silently freezes a project out of 1.1."""
    offenders = [
        f"{path.relative_to(ROOT)}:{lineno}: {m.group(0)}"
        for path in _pin_example_files()
        for lineno, line in enumerate(path.read_text().splitlines(), 1)
        for m in BASE_PIN_RE.finditer(line)
        if m.group(3)
    ]
    assert not offenders, "pw-foundation pins must be two components (~=M.N):\n" + "\n".join(
        offenders
    )


def test_pin_examples_track_current_major_minor():
    """A pin example on a stale line points consumers at a frozen release."""
    major, minor = _current_version()
    offenders = [
        f"{path.relative_to(ROOT)}:{lineno}: {m.group(0)}"
        for path in _pin_example_files()
        for lineno, line in enumerate(path.read_text().splitlines(), 1)
        for m in BASE_PIN_RE.finditer(line)
        if (int(m.group(1)), int(m.group(2))) != (major, minor)
    ]
    assert not offenders, f"pw-foundation pin examples not on {major}.{minor}:\n" + "\n".join(
        offenders
    )


def test_no_prepublication_version_references():
    """The shipped tree must not reference versions ahead of the released line.

    Scans prose, source, scripts, workflows; skips this file (it manufactures
    version tokens) and dependency-version lines.
    """
    major, minor = _current_version()
    scan = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "CHANGELOG.md",
        ROOT / "pyproject.toml",
        *sorted((ROOT / "src/pw_foundation").rglob("*.md")),
        *sorted((ROOT / "src/pw_foundation").rglob("*.py")),
        *sorted((ROOT / "tests").rglob("*.py")),
        *sorted((ROOT / "bin").iterdir()),
        *sorted((ROOT / ".github").rglob("*")),
        *sorted((ROOT / ".ai/rules").glob("*.md")),
    ]
    self_path = Path(__file__).resolve()
    offenders = []
    for path in scan:
        if not path.is_file() or path.resolve() == self_path:
            continue
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if not _offending_minors(line, minor, major=major):
                continue
            if any(dep in line for dep in _DEP_VERSIONS):
                continue
            offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
    assert not offenders, (
        "version references ahead of the released line (pre-publication/future numbering):\n"
        + "\n".join(offenders)
    )


def test_no_backup_or_debris_files_are_tracked():
    """No editor backup or debris file is tracked (enumerated from git, not globbed)."""
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    debris = [
        f
        for f in tracked
        if f.endswith((".bak", ".orig", ".rej", ".tmp", ".swp", "~")) or Path(f).name == ".DS_Store"
    ]
    assert not debris, f"debris committed: {debris}"


def _requires_python() -> tuple[int, int]:
    spec = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["requires-python"]
    m = re.search(r">=\s*(\d+)\.(\d+)", spec)
    assert m, f"cannot parse requires-python: {spec!r}"
    return int(m.group(1)), int(m.group(2))


def test_doctor_floor_matches_requires_python():
    """``pw-doctor`` reports whether the interpreter can run pw-foundation, so a stale
    floor makes it PASS the exact environment the install rejects."""
    from pw_foundation.doctor import _MIN_PY

    assert _MIN_PY == _requires_python(), (
        f"pw_foundation.doctor._MIN_PY {_MIN_PY} != requires-python {_requires_python()}"
    )


def test_setup_scripts_track_requires_python():
    """The bare-install verifier builds venvs, so a stale floor there produces an
    interpreter that cannot install the package it was created for."""
    major, minor = _requires_python()
    wanted = f"({major}, {minor})"
    stale_interpreters = re.compile(rf"python{major}\.(\d+)\b")
    offenders = []
    for path in [ROOT / "bin" / "verify-bare-install"]:
        rel = path.relative_to(ROOT)
        text = path.read_text()
        found = set(re.findall(r"sys\.version_info >= (\(\d+, \d+\))", text))
        if found != {wanted}:
            offenders.append(f"{rel}: version_info {sorted(found) or 'check missing'} != {wanted}")
        stale = sorted({int(m) for m in stale_interpreters.findall(text) if int(m) < minor})
        if stale:
            offenders.append(f"{rel}: offers {major}.{stale} below the floor")
    assert not offenders, f"setup scripts do not enforce the package floor {wanted}:\n" + "\n".join(
        offenders
    )


def test_ruff_target_version_tracks_requires_python():
    """``target-version`` tells ruff which syntax to accept. Below the floor it
    silently rejects language features the project is entitled to use."""
    major, minor = _requires_python()
    wanted = f"py{major}{minor}"
    offenders = []
    for lineno, line in enumerate((ROOT / "pyproject.toml").read_text().splitlines(), 1):
        m = re.match(r'\s*target-version\s*=\s*"([^"]+)"', line)
        if m and m.group(1) != wanted:
            offenders.append(f"pyproject.toml:{lineno}: {m.group(1)} != {wanted}")
    assert not offenders, (
        f"ruff target-version does not match requires-python ({wanted}):\n" + "\n".join(offenders)
    )
