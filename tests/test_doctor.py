"""Tests for pw_foundation.doctor — runtime ground-truth attestation.

All checks run against controlled state (monkeypatched env, tmp files, tmp git repos);
nothing here touches the network.
"""

from __future__ import annotations

import importlib.machinery
import subprocess
import sys
import types
from pathlib import Path

import pytest

from pw_foundation import doctor
from pw_foundation.doctor import (
    CheckResult,
    check_copy,
    check_env,
    check_python,
    redact_value,
    release_checks,
    run_checks,
    run_cli,
)

_NO_PLUGIN = "pw_core_not_installed.doctor"


@pytest.fixture(autouse=True)
def _path_based_kind(monkeypatch):
    """The dev venv has pw-foundation editable; path-shaped fakes decide the kind unless a test says otherwise."""
    monkeypatch.setattr(doctor, "_installed_editable", lambda dist: None)


class TestRedaction:
    def test_url_credentials_masked(self):
        out = redact_value("DATABASE_URL", "mysql://user:s3cr3t@db.host:3306/app")
        assert "s3cr3t" not in out
        assert "user" not in out
        assert "db.host" in out

    def test_key_vars_presence_only(self):
        out = redact_value("ANTHROPIC_API_KEY", "sk-ant-abc123")
        assert "sk-ant-abc123" not in out
        assert out == "set (redacted)"

    def test_plain_value_passthrough(self):
        assert redact_value("LOG_LEVEL", "DEBUG") == "DEBUG"

    def test_url_without_credentials_untouched(self):
        assert redact_value("DATABASE_URL", "sqlite:///data.db") == "sqlite:///data.db"


class TestCheckPython:
    def test_passes_on_current_interpreter(self):
        (res,) = check_python()
        assert res.status == "PASS"
        assert f"{sys.version_info[0]}.{sys.version_info[1]}" in res.detail

    def test_fails_below_floor(self, monkeypatch):
        monkeypatch.setattr(doctor, "_MIN_PY", (99, 0))
        (res,) = check_python()
        assert res.status == "FAIL"


def _roots(tmp_path: Path, *, base: str = "src", core: str | None = None) -> dict[str, Path]:
    """Fake package roots: ``src`` = an editable checkout tree, ``site`` = site-packages."""

    def mk(pkg: str, kind: str) -> Path:
        if kind == "site":
            p = tmp_path / "venv" / "lib" / "python3.12" / "site-packages" / pkg
        else:
            p = tmp_path / pkg.replace("_", "-") / "src" / pkg
        p.mkdir(parents=True, exist_ok=True)
        return p

    roots = {"pw_foundation": mk("pw_foundation", base)}
    if core:
        roots["pw_core"] = mk("pw_core", core)
    return roots


class TestCheckCopy:
    def test_reports_each_installed_package(self):
        by_name = {r.name: r for r in check_copy()}
        assert by_name["pw-foundation"].status in ("PASS", "WARN")
        assert "pw_foundation" in by_name["pw-foundation"].detail
        assert "version" in by_name["pw-foundation"].detail

    def test_warns_on_editable_metadata_mismatch(self, monkeypatch, tmp_path):
        roots = _roots(tmp_path)
        (tmp_path / "pw-foundation" / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "9.9.9"\n'
        )
        monkeypatch.setattr(doctor, "_package_roots", lambda: roots)
        monkeypatch.setattr(doctor, "_installed_version", lambda dist: "0.0.1")
        (res,) = check_copy()
        assert res.status == "WARN"
        assert "0.0.1" in res.detail
        assert "9.9.9" in res.detail

    def test_site_packages_never_reads_pyproject(self, monkeypatch, tmp_path):
        monkeypatch.setattr(doctor, "_package_roots", lambda: _roots(tmp_path, base="site"))
        monkeypatch.setattr(doctor, "_installed_version", lambda dist: "0.0.1")

        def _boom(root):
            raise AssertionError("pyproject read attempted for a site-packages install")

        monkeypatch.setattr(doctor, "_adjacent_pyproject_version", _boom)
        (res,) = check_copy()
        assert res.status == "PASS"
        assert "(installed)" in res.detail

    def test_editable_missing_pyproject_passes(self, monkeypatch, tmp_path):
        monkeypatch.setattr(doctor, "_package_roots", lambda: _roots(tmp_path))
        monkeypatch.setattr(doctor, "_installed_version", lambda dist: "0.0.1")
        (res,) = check_copy()
        assert res.status == "PASS"

    def test_editable_malformed_pyproject_passes(self, monkeypatch, tmp_path):
        roots = _roots(tmp_path)
        (tmp_path / "pw-foundation" / "pyproject.toml").write_text("not [valid toml")
        monkeypatch.setattr(doctor, "_package_roots", lambda: roots)
        monkeypatch.setattr(doctor, "_installed_version", lambda dist: "0.0.1")
        (res,) = check_copy()
        assert res.status == "PASS"

    def test_editable_matching_version_passes(self, monkeypatch, tmp_path):
        roots = _roots(tmp_path)
        (tmp_path / "pw-foundation" / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.0.1"\n'
        )
        monkeypatch.setattr(doctor, "_package_roots", lambda: roots)
        monkeypatch.setattr(doctor, "_installed_version", lambda dist: "0.0.1")
        (res,) = check_copy()
        assert res.status == "PASS"

    def test_adjacent_pyproject_version_reads_file(self, tmp_path):
        roots = _roots(tmp_path)
        (tmp_path / "pw-foundation" / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "1.0.3"\n'
        )
        assert doctor._adjacent_pyproject_version(roots["pw_foundation"]) == "1.0.3"

    def test_mixed_install_warns(self, monkeypatch, tmp_path):
        roots = _roots(tmp_path, base="site", core="src")
        monkeypatch.setattr(doctor, "_package_roots", lambda: roots)
        monkeypatch.setattr(doctor, "_installed_version", lambda dist: "0.0.1")
        rows = {r.name: r for r in check_copy()}
        assert set(rows) == {"pw-foundation", "pw-core", "mixed"}
        assert rows["mixed"].status == "WARN"
        assert "installed" in rows["mixed"].detail
        assert "pw-core" in rows["mixed"].detail
        assert "pip install -e" in rows["mixed"].detail

    def test_both_editable_is_not_mixed(self, monkeypatch, tmp_path):
        roots = _roots(tmp_path, core="src")
        monkeypatch.setattr(doctor, "_package_roots", lambda: roots)
        monkeypatch.setattr(doctor, "_installed_version", lambda dist: "0.0.1")
        assert {r.name for r in check_copy()} == {"pw-foundation", "pw-core"}


class TestCheckEnv:
    def test_reports_set_and_unset(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)  # no .env here
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.delenv("LOG_FILE", raising=False)
        (res,) = check_env()
        assert res.status == "PASS"
        assert "LOG_LEVEL=DEBUG" in res.detail
        assert "LOG_FILE unset" in res.detail
        assert "no .env" in res.detail

    def test_loads_cwd_dotenv_for_effective_env(self, monkeypatch, tmp_path):
        (tmp_path / ".env").write_text("LOG_LEVEL=TRACE_TEST\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        (res,) = check_env()
        assert "LOG_LEVEL=TRACE_TEST" in res.detail
        assert ".env loaded from" in res.detail

    def test_shell_value_wins_over_dotenv(self, monkeypatch, tmp_path):
        (tmp_path / ".env").write_text("LOG_LEVEL=FROM_FILE\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LOG_LEVEL", "FROM_SHELL")
        (res,) = check_env()
        assert "LOG_LEVEL=FROM_SHELL" in res.detail


def _fake_plugin(monkeypatch, calls: list[bool]) -> None:
    mod = types.ModuleType("fake_doctor_plugin")
    mod.__spec__ = importlib.machinery.ModuleSpec(
        "fake_doctor_plugin", None, origin="/fake/fake_doctor_plugin.py"
    )

    def checks(*, db: bool = False) -> list[CheckResult]:
        calls.append(db)
        return [CheckResult("extras", "available", "PASS", "fake")]

    mod.checks = checks  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fake_doctor_plugin", mod)
    monkeypatch.setattr(doctor, "_PLUGIN_MODULE", "fake_doctor_plugin")


class TestPlugin:
    def test_plugin_checks_are_skipped_when_pw_core_is_absent(self, monkeypatch):
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", _NO_PLUGIN)
        assert all(r.group not in {"extras", "router", "deps", "db"} for r in run_checks())

    def test_plugin_checks_are_appended_with_the_db_flag(self, monkeypatch):
        calls: list[bool] = []
        _fake_plugin(monkeypatch, calls)
        rows = run_checks(db=True)
        assert calls == [True]
        assert any(r.group == "extras" for r in rows)


def _git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _git_repo_with_release(tmp_path, *, version="1.0.0", changelog="1.0.0", tag=None):
    (tmp_path / "pyproject.toml").write_text(f'[project]\nname = "x"\nversion = "{version}"\n')
    if changelog is not None:
        (tmp_path / "CHANGELOG.md").write_text(f"# Changelog\n\n## v{changelog} — 2026-07-02\n")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "release")
    if tag:
        _git(tmp_path, "tag", tag)
    return tmp_path


class TestReleaseChecks:
    def test_skip_when_not_a_git_repo(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (res,) = release_checks()
        assert res.status == "SKIP"

    def test_versions_match_passes(self, tmp_path, monkeypatch):
        _git_repo_with_release(tmp_path)
        monkeypatch.chdir(tmp_path)
        by_name = {r.name: r for r in release_checks()}
        assert by_name["versions"].status == "PASS"

    def test_versions_mismatch_fails(self, tmp_path, monkeypatch):
        _git_repo_with_release(tmp_path, version="1.0.0", changelog="0.7.0")
        monkeypatch.chdir(tmp_path)
        by_name = {r.name: r for r in release_checks()}
        assert by_name["versions"].status == "FAIL"
        assert "1.0.0" in by_name["versions"].detail
        assert "0.7.0" in by_name["versions"].detail

    def test_missing_changelog_warns(self, tmp_path, monkeypatch):
        _git_repo_with_release(tmp_path, changelog=None)
        monkeypatch.chdir(tmp_path)
        by_name = {r.name: r for r in release_checks()}
        assert by_name["versions"].status == "WARN"

    def test_tag_matching_pyproject_passes(self, tmp_path, monkeypatch):
        _git_repo_with_release(tmp_path, tag="v1.0.0")
        monkeypatch.chdir(tmp_path)
        by_name = {r.name: r for r in release_checks()}
        assert by_name["tag"].status == "PASS"

    def test_tag_mismatch_fails(self, tmp_path, monkeypatch):
        _git_repo_with_release(tmp_path, tag="v2.0.0")
        monkeypatch.chdir(tmp_path)
        by_name = {r.name: r for r in release_checks()}
        assert by_name["tag"].status == "FAIL"

    def test_no_tag_at_head_skips(self, tmp_path, monkeypatch):
        _git_repo_with_release(tmp_path)
        monkeypatch.chdir(tmp_path)
        by_name = {r.name: r for r in release_checks()}
        assert by_name["tag"].status == "SKIP"

    def test_dirty_tree_warns(self, tmp_path, monkeypatch):
        _git_repo_with_release(tmp_path)
        (tmp_path / "extra.txt").write_text("uncommitted")
        monkeypatch.chdir(tmp_path)
        by_name = {r.name: r for r in release_checks()}
        assert by_name["tree"].status == "WARN"

    def test_clean_tree_passes(self, tmp_path, monkeypatch):
        _git_repo_with_release(tmp_path)
        monkeypatch.chdir(tmp_path)
        by_name = {r.name: r for r in release_checks()}
        assert by_name["tree"].status == "PASS"


class TestRunner:
    def test_run_checks_core_groups_without_the_plugin(self, monkeypatch):
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", _NO_PLUGIN)
        assert {r.group for r in run_checks()} == {"copy", "python", "env", "wiring"}

    def test_release_group_only_when_asked(self, tmp_path, monkeypatch):
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", _NO_PLUGIN)
        _git_repo_with_release(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert "release" not in {r.group for r in run_checks()}
        assert "release" in {r.group for r in run_checks(release=True)}


class TestRunCli:
    def test_exit_zero_when_no_fail(self, capsys, monkeypatch):
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", _NO_PLUGIN)
        code = run_cli([])
        out = capsys.readouterr().out
        assert code == 0
        assert "pass" in out.lower()

    def test_exit_one_on_fail(self, monkeypatch):
        monkeypatch.setattr(
            doctor, "run_checks", lambda **kw: [CheckResult("env", "forced", "FAIL", "boom")]
        )
        assert run_cli([]) == 1

    def test_warn_does_not_flip_exit(self, monkeypatch):
        monkeypatch.setattr(
            doctor, "run_checks", lambda **kw: [CheckResult("copy", "forced", "WARN", "meh")]
        )
        assert run_cli([]) == 0

    def test_db_flag_reaches_the_plugin(self, monkeypatch):
        calls: list[bool] = []
        _fake_plugin(monkeypatch, calls)
        assert run_cli(["--db"]) == 0
        assert calls == [True]

    def test_release_flag_parsed(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", _NO_PLUGIN)
        _git_repo_with_release(tmp_path)
        monkeypatch.chdir(tmp_path)
        code = run_cli(["--release"])
        out = capsys.readouterr().out
        assert code == 0
        assert "versions" in out


class TestPluginSafety:
    def test_a_package_without_the_plugin_module_is_a_fail_row(self, monkeypatch):
        pkg = types.ModuleType("fake_core_d")
        pkg.__spec__ = importlib.machinery.ModuleSpec(
            "fake_core_d", None, origin="/fake/fake_core_d/__init__.py", is_package=True
        )
        pkg.__path__ = []  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "fake_core_d", pkg)
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", "fake_core_d.doctor")
        rows = [r for r in run_checks() if r.group == "plugin"]
        assert rows and rows[0].status == "FAIL" and "fake_core_d.doctor" in rows[0].detail

    def test_a_namespace_directory_counts_as_absent(self, monkeypatch, tmp_path):
        (tmp_path / "ns_core_d").mkdir()
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", "ns_core_d.doctor")
        assert all(r.group != "plugin" for r in run_checks())

    def test_a_plugin_row_with_an_unknown_status_is_reported_not_crashed(self, monkeypatch):
        mod = types.ModuleType("fake_doctor_odd")
        mod.__spec__ = importlib.machinery.ModuleSpec(
            "fake_doctor_odd", None, origin="/fake/fake_doctor_odd.py"
        )
        mod.checks = lambda **_: [CheckResult("extras", "available", "OK", "fake")]  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "fake_doctor_odd", mod)
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", "fake_doctor_odd")
        assert run_cli([]) == 1
        rows = {(r.group, r.name): r for r in run_checks()}
        assert rows[("plugin", "fake_doctor_odd")].status == "FAIL"

    def test_plugin_receives_the_flags_as_keywords(self, monkeypatch):
        seen: list[dict] = []
        mod = types.ModuleType("fake_doctor_kw")
        mod.__spec__ = importlib.machinery.ModuleSpec(
            "fake_doctor_kw", None, origin="/fake/fake_doctor_kw.py"
        )

        def checks(**options):
            seen.append(options)
            return []

        mod.checks = checks  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "fake_doctor_kw", mod)
        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", "fake_doctor_kw")
        run_checks(db=True)
        assert seen == [{"db": True}]


class TestEditableDetection:
    def test_direct_url_editable_flag_decides_the_kind(self, monkeypatch, tmp_path):
        """PEP 610 metadata, not a 'site-packages' substring, says whether a copy is editable."""
        roots = _roots(tmp_path, base="site", core="site")
        monkeypatch.setattr(doctor, "_package_roots", lambda: roots)
        monkeypatch.setattr(doctor, "_installed_version", lambda dist: "0.0.1")
        monkeypatch.setattr(doctor, "_installed_editable", lambda dist: dist == "pw-core")
        rows = {r.name: r for r in check_copy()}
        assert "(editable)" in rows["pw-core"].detail
        assert "(installed)" in rows["pw-foundation"].detail
        assert rows["mixed"].status == "WARN"
