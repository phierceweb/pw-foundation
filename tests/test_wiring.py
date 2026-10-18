"""pw-setup (pw_foundation.wiring) and the wiring rows pw-doctor reports."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from pw_foundation import wiring
from pw_foundation.guards.structure import run_cli as guards_cli
from pw_foundation._wiring_check import _check_wiring as check_wiring
from pw_foundation.wiring import _ensure_wiring as ensure_wiring
from pw_foundation.wiring import installed_docs_dir, installed_rules_dir, run_cli

SHIPPED_RULES = {
    "code-style.md",
    "config-driven.md",
    "docs-sync.md",
    "error-handling.md",
    "framework-first.md",
    "logging.md",
    "plans.md",
}


def _project(tmp_path: Path, layout: str = "src", name: str = "proj") -> Path:
    """A consumer-shaped directory: a project marker plus a package layout."""
    proj = tmp_path / name
    proj.mkdir()
    (proj / "pyproject.toml").write_text('[project]\nname = "mytool"\nversion = "0.1.0"\n')
    if layout == "src":
        (proj / "src" / "mytool").mkdir(parents=True)
        (proj / "src" / "mytool" / "__init__.py").write_text("")
    elif layout == "app":
        (proj / "app").mkdir()
        (proj / "app" / "__init__.py").write_text("")
    return proj


def _snapshot(root: Path) -> dict[str, str]:
    out = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            out[rel] = "-> " + os.readlink(p)
        elif p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


@pytest.fixture
def fake_core(tmp_path: Path, monkeypatch) -> Path:
    """A real importable ``pw_core`` package on sys.path, with docs and rules — discovered, not patched."""
    pkg = tmp_path / "site" / "pw_core"
    (pkg / "docs").mkdir(parents=True)
    (pkg / "rules").mkdir()
    (pkg / "__init__.py").write_text("")
    (pkg / "docs" / "modules.md").write_text("# pw-core modules\n")
    (pkg / "rules" / "layering.md").write_text("# Layering\n")
    monkeypatch.syspath_prepend(str(tmp_path / "site"))
    return pkg


# ---------------------------------------------------------------------------
# docs links
# ---------------------------------------------------------------------------


class TestDocsLinks:
    def test_links_every_shipped_doc_into_a_fresh_project(self, tmp_path):
        proj = _project(tmp_path)
        _, errors = ensure_wiring(proj)
        assert errors == []
        link = proj / "docs" / "pw-foundation"
        assert link.is_symlink() and link.resolve() == installed_docs_dir().resolve()
        assert {p.name for p in link.glob("*.md")} == {
            p.name for p in installed_docs_dir().glob("*.md")
        }

    def test_replaces_a_wrong_or_dangling_link(self, tmp_path):
        proj = _project(tmp_path)
        (proj / "docs").mkdir()
        (proj / "docs" / "pw-foundation").symlink_to(tmp_path / "old-venv-gone")
        _, errors = ensure_wiring(proj)
        assert errors == []
        assert (proj / "docs" / "pw-foundation").resolve() == installed_docs_dir().resolve()

    def test_refuses_a_real_directory_at_the_link(self, tmp_path):
        proj = _project(tmp_path)
        real = proj / "docs" / "pw-foundation"
        real.mkdir(parents=True)
        (real / "keep.md").write_text("mine\n")
        _, errors = ensure_wiring(proj)
        assert len(errors) == 1 and "docs/pw-foundation" in errors[0]
        assert (real / "keep.md").read_text() == "mine\n"

    def test_removes_a_legacy_symlink_and_mentions_a_real_legacy_directory(self, tmp_path):
        proj = _project(tmp_path)
        (proj / "docs").mkdir()
        (proj / "docs" / "pf-core").symlink_to(proj / "gone")
        actions, _ = ensure_wiring(proj)
        assert not (proj / "docs" / "pf-core").is_symlink()
        assert any("removed" in a and "docs/pf-core" in a for a in actions)
        other = _project(tmp_path, name="other")
        (other / "docs" / "pf-core").mkdir(parents=True)
        actions, errors = ensure_wiring(other)
        assert errors == [] and any("docs/pf-core" in a and "directory" in a for a in actions)

    def test_links_pw_core_docs_when_a_real_package_is_installed(self, tmp_path, fake_core):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        assert (proj / "docs" / "pw-core" / "modules.md").read_text() == "# pw-core modules\n"

    def test_a_pw_core_without_docs_is_not_linked(self, tmp_path, fake_core):
        (fake_core / "docs" / "modules.md").unlink()
        (fake_core / "docs").rmdir()
        proj = _project(tmp_path)
        _, errors = ensure_wiring(proj)
        assert errors == [] and not (proj / "docs" / "pw-core").exists()
        assert not (proj / "docs" / "pw-core").is_symlink()

    def test_a_leftover_pw_core_link_is_removed_when_pw_core_is_gone(self, tmp_path):
        proj = _project(tmp_path)
        (proj / "docs").mkdir()
        (proj / "docs" / "pw-core").symlink_to(tmp_path / "uninstalled")
        actions, _ = ensure_wiring(proj)
        assert not (proj / "docs" / "pw-core").is_symlink()
        assert any("docs/pw-core" in a and "removed" in a for a in actions)

    def test_a_namespace_pw_core_directory_is_ignored(self, tmp_path, monkeypatch):
        (tmp_path / "site" / "pw_core").mkdir(parents=True)
        monkeypatch.syspath_prepend(str(tmp_path / "site"))
        assert [name for name, _ in wiring._installed()] == ["pw-foundation"]


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------


class TestRules:
    def test_shipped_rules_land_with_mdc_links_and_a_manifest(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        rules = proj / ".ai" / "rules"
        assert {p.name for p in rules.glob("*.md")} == SHIPPED_RULES
        shipped = installed_rules_dir() / "framework-first.md"
        assert (rules / "framework-first.md").read_bytes() == shipped.read_bytes()
        mdc = rules / "framework-first.mdc"
        assert mdc.is_symlink() and os.readlink(mdc) == "framework-first.md"
        manifest = json.loads((rules / ".pw-setup.json").read_text())
        assert set(manifest) == SHIPPED_RULES

    def test_every_shipped_rule_has_cursor_frontmatter(self):
        for rule in installed_rules_dir().glob("*.md"):
            head = rule.read_text().split("---")
            assert head[0] == "" and "alwaysApply: true" in head[1] and "description:" in head[1], (
                rule.name
            )

    def test_an_edited_rule_is_kept(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        rule = proj / ".ai" / "rules" / "code-style.md"
        rule.write_text(rule.read_text() + "\n## Ours\n")
        mine = rule.read_bytes()
        actions, _ = ensure_wiring(proj)
        assert rule.read_bytes() == mine
        assert any("kept" in a and "code-style.md" in a and "edited" in a for a in actions)

    def test_a_pre_existing_rule_of_unknown_origin_is_kept(self, tmp_path):
        proj = _project(tmp_path)
        (proj / ".ai" / "rules").mkdir(parents=True)
        (proj / ".ai" / "rules" / "code-style.md").write_text("# Mine\n")
        actions, _ = ensure_wiring(proj)
        assert (proj / ".ai" / "rules" / "code-style.md").read_text() == "# Mine\n"
        assert any("kept" in a and "code-style.md" in a for a in actions)

    def test_an_unedited_copy_is_updated_when_the_shipped_rule_changes(self, tmp_path, monkeypatch):
        src = tmp_path / "shipped"
        src.mkdir()
        (src / "logging.md").write_text("v1\n")
        monkeypatch.setattr(wiring, "_rule_sources", lambda: [("pw-foundation", src)])
        proj = _project(tmp_path)
        ensure_wiring(proj)
        (src / "logging.md").write_text("v2\n")
        actions, _ = ensure_wiring(proj)
        assert (proj / ".ai" / "rules" / "logging.md").read_text() == "v2\n"
        assert any("updated" in a and "logging.md" in a for a in actions)

    def test_a_stale_mdc_link_is_repointed(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        mdc = proj / ".ai" / "rules" / "docs-sync.mdc"
        mdc.unlink()
        mdc.symlink_to("plans.md")
        ensure_wiring(proj)
        assert os.readlink(mdc) == "docs-sync.md"

    def test_pw_core_rules_install_alongside_and_a_collision_is_named(self, tmp_path, fake_core):
        (fake_core / "rules" / "code-style.md").write_text("# core's\n")
        proj = _project(tmp_path)
        actions, _ = ensure_wiring(proj)
        rules = proj / ".ai" / "rules"
        assert (rules / "layering.md").read_text() == "# Layering\n"
        assert (rules / "code-style.md").read_bytes() == (
            installed_rules_dir() / "code-style.md"
        ).read_bytes()
        assert any("collision" in a and "code-style.md" in a and "pw-core" in a for a in actions)
        assert not any("yours" in a and "code-style.md" in a for a in actions)


# ---------------------------------------------------------------------------
# editor dirs, gitignore, guards config, project check
# ---------------------------------------------------------------------------


class TestScaffold:
    def test_editor_dirs_point_at_ai(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        for editor in (".claude", ".cursor"):
            for sub in ("rules", "plans", "skills"):
                link = proj / editor / sub
                assert link.is_symlink() and link.resolve() == (proj / ".ai" / sub).resolve(), link
        assert (proj / ".ai" / "plans" / ".gitkeep").is_file()
        assert (proj / ".claude" / "rules" / "framework-first.md").is_file()

    def test_a_real_editor_rules_directory_is_refused_with_a_safe_message(self, tmp_path):
        proj = _project(tmp_path)
        (proj / ".claude" / "rules").mkdir(parents=True)
        (proj / ".claude" / "rules" / "mine.md").write_text("mine\n")
        _, errors = ensure_wiring(proj)
        [err] = [e for e in errors if ".claude/rules" in e]
        assert ".ai/rules" in err and "skills" in err and "move aside" not in err
        assert (proj / ".claude" / "rules" / "mine.md").read_text() == "mine\n"

    def test_gitignore_gets_the_link_entries_once(self, tmp_path):
        proj = _project(tmp_path)
        (proj / ".gitignore").write_text(".venv/\n")
        ensure_wiring(proj)
        ensure_wiring(proj)
        text = (proj / ".gitignore").read_text()
        assert text.count("docs/pw-foundation") == 1 and text.startswith(".venv/\n")

    def test_gitignore_is_created_only_in_a_git_repo(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        assert not (proj / ".gitignore").exists()
        repo = _project(tmp_path, name="repo")
        (repo / ".git").mkdir()
        ensure_wiring(repo)
        assert "docs/pw-foundation" in (repo / ".gitignore").read_text()

    def test_guards_config_root_from_the_src_package(self, tmp_path):
        proj = _project(tmp_path)
        (proj / "src" / "tests").mkdir()
        (proj / "src" / "__pycache__").mkdir()
        ensure_wiring(proj)
        assert 'root = "src/mytool"' in (proj / ".pw-guards.toml").read_text()

    def test_guards_config_root_from_an_app_tree(self, tmp_path):
        proj = _project(tmp_path, layout="app")
        ensure_wiring(proj)
        assert 'root = "app"' in (proj / ".pw-guards.toml").read_text()

    def test_an_app_directory_without_python_does_not_win(self, tmp_path):
        proj = _project(tmp_path)
        (proj / "app").mkdir()
        (proj / "app" / "page.tsx").write_text("")
        ensure_wiring(proj)
        assert 'root = "src/mytool"' in (proj / ".pw-guards.toml").read_text()

    def test_an_existing_guards_config_is_untouched(self, tmp_path):
        proj = _project(tmp_path)
        (proj / ".pw-guards.toml").write_text('[tool.pw_guards]\nroot = "src/mytool"\nhard = 400\n')
        ensure_wiring(proj)
        assert "hard = 400" in (proj / ".pw-guards.toml").read_text()

    def test_a_legacy_guards_config_is_migrated_not_shadowed(self, tmp_path, monkeypatch):
        proj = _project(tmp_path)
        (proj / ".pf-guards.toml").write_text(
            '# the gate\n[tool.pf_guards]\nroot = "src/mytool"\nmax_function_lines = 30\n'
            "[tool.pf_guards.framework]\n"
        )
        (proj / "src" / "mytool" / "big.py").write_text("def f():\n" + "    x = 1\n" * 40)
        actions, errors = ensure_wiring(proj)
        assert errors == [] and any("migrated" in a for a in actions)
        assert not (proj / ".pf-guards.toml").exists()
        new = (proj / ".pw-guards.toml").read_text()
        assert (
            "[tool.pw_guards]" in new
            and "[tool.pw_guards.framework]" in new
            and "pf_guards" not in new
        )
        monkeypatch.chdir(proj)
        assert guards_cli([]) == 1  # the migrated limits still bite

    def test_both_guards_configs_present_is_an_error(self, tmp_path):
        proj = _project(tmp_path)
        (proj / ".pf-guards.toml").write_text("[tool.pf_guards]\n")
        (proj / ".pw-guards.toml").write_text("[tool.pw_guards]\n")
        _, errors = ensure_wiring(proj)
        assert any(".pf-guards.toml" in e for e in errors)

    def test_refuses_a_directory_that_is_not_a_project(self, tmp_path):
        _, errors = ensure_wiring(tmp_path)
        assert errors and "pyproject.toml" in errors[0]
        assert not (tmp_path / ".ai").exists() and not (tmp_path / ".claude").exists()

    def test_refuses_the_home_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        (tmp_path / ".git").mkdir()
        _, errors = ensure_wiring(tmp_path)
        assert errors and "home" in errors[0]

    def test_symlink_failure_is_reported_and_rules_still_land(self, tmp_path, monkeypatch):
        proj = _project(tmp_path)

        def boom(self, target, *a, **k):
            raise OSError("symlinks unsupported")

        monkeypatch.setattr(Path, "symlink_to", boom)
        _, errors = ensure_wiring(proj)
        assert errors and any("symlink" in e for e in errors)
        assert (proj / ".ai" / "rules" / "code-style.md").is_file()

    def test_second_run_changes_nothing(self, tmp_path, fake_core):
        proj = _project(tmp_path)
        (proj / ".git").mkdir()
        ensure_wiring(proj)
        before = _snapshot(proj)
        actions, errors = ensure_wiring(proj)
        assert errors == [] and _snapshot(proj) == before
        assert all(a.split(":")[0] in ("ok", "collision") for a in actions), actions


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestRunCli:
    def test_exit_zero_and_prints_installed_pins(self, tmp_path, capsys):
        proj = _project(tmp_path)
        assert run_cli(["--project-root", str(proj)]) == 0
        out = capsys.readouterr().out
        assert '"pw-foundation~=1.0"' in out and "CLAUDE.md" in out and "✓" not in out

    def test_exit_one_on_refusal(self, tmp_path):
        proj = _project(tmp_path)
        (proj / "docs" / "pw-foundation").mkdir(parents=True)
        assert run_cli(["--project-root", str(proj)]) == 1

    def test_relative_project_root_from_another_cwd(self, tmp_path, monkeypatch):
        proj = _project(tmp_path)
        monkeypatch.chdir(tmp_path)
        assert run_cli(["--project-root", "proj"]) == 0
        assert (proj / ".claude" / "rules" / "plans.md").is_file()


# ---------------------------------------------------------------------------
# doctor rows
# ---------------------------------------------------------------------------


def _rows(root: Path) -> dict[str, tuple[str, str]]:
    return {name: (status, detail) for name, status, detail in check_wiring(root)}


class TestCheckWiring:
    def test_fresh_project_warns_everywhere_and_names_pw_setup(self, tmp_path):
        rows = _rows(_project(tmp_path))
        for name in ("docs_link.pw-foundation", "rules", "guards_config", "editor_links"):
            assert rows[name][0] == "WARN" and "pw-setup" in rows[name][1], name

    def test_wired_project_passes_everything(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        assert {status for status, _ in _rows(proj).values()} == {"PASS"}

    def test_a_link_to_a_different_copy_fails(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        other = tmp_path / "other-venv-docs"
        other.mkdir()
        (other / "modules.md").write_text("OLD 0.9\n")
        link = proj / "docs" / "pw-foundation"
        link.unlink()
        link.symlink_to(other)
        assert _rows(proj)["docs_link.pw-foundation"][0] == "FAIL"

    def test_a_broken_rule_or_mdc_fails(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        mdc = proj / ".ai" / "rules" / "plans.mdc"
        mdc.unlink()
        mdc.symlink_to("gone.md")
        status, detail = _rows(proj)["rules"]
        assert status == "FAIL" and "plans.mdc" in detail

    def test_a_rule_still_naming_the_old_framework_warns(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        (proj / ".ai" / "rules" / "logging.md").write_text("Use pf_core.log.\n")
        status, detail = _rows(proj)["rules"]
        assert status == "WARN" and "logging.md" in detail

    def test_a_legacy_guards_config_fails(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        (proj / ".pf-guards.toml").write_text("[tool.pf_guards]\n")
        assert _rows(proj)["guards_config"][0] == "FAIL"

    def test_a_real_editor_directory_fails(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        (proj / ".cursor" / "rules").unlink()
        (proj / ".cursor" / "rules").mkdir()
        status, detail = _rows(proj)["editor_links"]
        assert status == "FAIL" and ".cursor/rules" in detail

    def test_leftovers_are_reported(self, tmp_path):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        (proj / "docs" / "pf-core").mkdir()
        (proj / "docs" / "pw-core").symlink_to(tmp_path / "uninstalled")
        rows = _rows(proj)
        assert rows["leftovers"][0] == "WARN" and "docs/pf-core" in rows["leftovers"][1]
        assert "docs/pw-core" in rows["leftovers"][1]

    def test_framework_checkout_and_non_project_skip(self, tmp_path):
        (tmp_path / "fw" / "src" / "pw_foundation").mkdir(parents=True)
        assert [s for _, s, _ in check_wiring(tmp_path / "fw")] == ["SKIP"]
        (tmp_path / "nothing").mkdir()
        assert [s for _, s, _ in check_wiring(tmp_path / "nothing")] == ["SKIP"]

    def test_pw_core_rows_appear_with_a_real_package(self, tmp_path, fake_core):
        proj = _project(tmp_path)
        ensure_wiring(proj)
        rows = _rows(proj)
        assert rows["docs_link.pw-core"][0] == "PASS"
        assert "8" in rows["rules"][1]  # seven base rules plus pw-core's layering.md


class TestDoctorIntegration:
    def test_doctor_includes_wiring_group(self, tmp_path, monkeypatch):
        from pw_foundation import doctor

        monkeypatch.setattr(doctor, "_PLUGIN_MODULE", "pw_core_not_installed.doctor")
        monkeypatch.chdir(_project(tmp_path))
        rows = [r for r in doctor.run_checks() if r.group == "wiring"]
        assert any(r.name == "docs_link.pw-foundation" and r.status == "WARN" for r in rows)
