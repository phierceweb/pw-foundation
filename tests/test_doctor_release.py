"""``pw-doctor --release``: the CHANGELOG heading styles the versions row accepts."""

from __future__ import annotations

import subprocess

import pytest

from pw_foundation._doctor_release import _changelog_version, release_checks


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("## v0.6.0 — 2026-10-18", "0.6.0"),
        ("## [0.6.0] — 2026-10-18", "0.6.0"),
        ("## 0.13.0 — 2026-10-18", "0.13.0"),
        ("## [0.6.0]", "0.6.0"),
        ("## v1.0.0rc1", "1.0.0rc1"),
    ],
)
def test_the_three_heading_styles_yield_the_version(tmp_path, monkeypatch, heading, expected):
    (tmp_path / "CHANGELOG.md").write_text(f"# Changelog\n\n{heading}\n\n- a change\n")
    monkeypatch.chdir(tmp_path)
    assert _changelog_version() == expected


def test_an_unreleased_heading_above_the_version_is_skipped(tmp_path, monkeypatch):
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n- pending\n\n## [0.6.0] — 2026-10-18\n\n- shipped\n"
    )
    monkeypatch.chdir(tmp_path)
    assert _changelog_version() == "0.6.0"


def test_no_version_heading_is_none(tmp_path, monkeypatch):
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- pending\n")
    monkeypatch.chdir(tmp_path)
    assert _changelog_version() is None


def test_versions_row_passes_for_a_keep_a_changelog_file(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.6.0"\n')
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## [0.6.0] — 2026-10-18\n\n- shipped\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    row = next(r for r in release_checks() if r.name == "versions")
    assert row.status == "PASS", row.detail
