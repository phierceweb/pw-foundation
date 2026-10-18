"""Base rules speak only of base facilities; pw-core contributes its own rules when installed."""

from __future__ import annotations

import importlib.machinery
import sys
import types
from pathlib import Path

import pytest

from pw_foundation.exceptions import ConfigurationError
from pw_foundation.guards import framework_rules
from pw_foundation.guards.framework import active_rules
from pw_foundation.guards.framework_config import FrameworkConfig
from pw_foundation.guards.framework_rules import RULES, FrameworkRule, all_rules, rule_names
from pw_foundation.guards.layering import check_layering

_NO_PLUGIN = "pw_core_not_installed.guards_rules"


def _fake_plugin(monkeypatch, **attrs) -> types.ModuleType:
    """A one-segment fake plugin module carrying ``attrs`` (RULES, DB_MODULES, ...)."""
    mod = types.ModuleType("fake_guards_rules")
    mod.__spec__ = importlib.machinery.ModuleSpec(
        "fake_guards_rules", None, origin="/fake/fake_guards_rules.py"
    )
    for k, v in attrs.items():
        setattr(mod, k, v)
    monkeypatch.setitem(sys.modules, "fake_guards_rules", mod)
    monkeypatch.setattr(framework_rules, "_PLUGIN_MODULE", "fake_guards_rules")
    return mod


def _partial_parent(monkeypatch) -> None:
    """A package that exists but lacks the plugin child module: a broken or old pw-core."""
    pkg = types.ModuleType("fake_core")
    pkg.__spec__ = importlib.machinery.ModuleSpec(
        "fake_core", None, origin="/fake/fake_core/__init__.py", is_package=True
    )
    pkg.__path__ = []  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fake_core", pkg)
    monkeypatch.setattr(framework_rules, "_PLUGIN_MODULE", "fake_core.guards_rules")


HTTP = FrameworkRule(name="requests", kind="import", use="pw_core.fetch", why="an SSRF guard")


def test_base_rules_never_name_pw_core() -> None:
    assert [r.name for r in RULES if "pw_core" in r.use or "pw_core" in r.why] == []


def test_http_client_rules_are_not_base_rules() -> None:
    assert {"requests", "httpx", "aiohttp", "urllib3"}.isdisjoint(r.name for r in RULES)


def test_without_the_plugin_all_rules_is_the_base_set(monkeypatch) -> None:
    monkeypatch.setattr(framework_rules, "_PLUGIN_MODULE", _NO_PLUGIN)
    assert all_rules() == RULES
    assert rule_names() == frozenset(r.name for r in RULES)


def test_plugin_rules_are_appended_and_named(monkeypatch) -> None:
    _fake_plugin(monkeypatch, RULES=(HTTP,))
    assert all_rules() == (*RULES, HTTP)
    assert "requests" in rule_names()


def test_active_rules_include_plugin_rules_and_honor_disable(monkeypatch) -> None:
    _fake_plugin(monkeypatch, RULES=(HTTP,))
    assert HTTP in active_rules(FrameworkConfig())
    assert HTTP not in active_rules(FrameworkConfig(disable=("requests",)))


def test_a_namespace_directory_counts_as_absent(monkeypatch, tmp_path: Path) -> None:
    """A leftover ``pw_core/`` directory without ``__init__.py`` is not a plugin."""
    (tmp_path / "ns_core").mkdir()
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(framework_rules, "_PLUGIN_MODULE", "ns_core.guards_rules")
    assert all_rules() == RULES


def test_a_present_package_without_the_plugin_module_is_a_configuration_error(monkeypatch) -> None:
    _partial_parent(monkeypatch)
    with pytest.raises(ConfigurationError, match="fake_core.guards_rules"):
        all_rules()


def test_a_plugin_rule_of_unknown_kind_is_refused(monkeypatch) -> None:
    bad = FrameworkRule(name="odd", kind="telepathy", use="x", why="y")
    _fake_plugin(monkeypatch, RULES=(bad,))
    with pytest.raises(ConfigurationError, match="telepathy"):
        all_rules()


def test_a_default_off_rule_runs_only_when_enabled(monkeypatch) -> None:
    """In 1.x a new rule ships off; a consumer lists it under ``enable`` to take it."""
    new = FrameworkRule(name="new-rule", kind="import", use="x", why="y", default_on=False)
    _fake_plugin(monkeypatch, RULES=(new,))
    assert new not in active_rules(FrameworkConfig())
    assert new in active_rules(FrameworkConfig(enable=("new-rule",)))


def test_enable_refuses_an_unknown_rule(monkeypatch) -> None:
    monkeypatch.setattr(framework_rules, "_PLUGIN_MODULE", _NO_PLUGIN)
    with pytest.raises(ConfigurationError, match="nope"):
        FrameworkConfig(enable=("nope",))


def test_layering_db_modules_come_from_the_plugin(monkeypatch, tmp_path: Path) -> None:
    """The orchestrator-imports-the-db rule names pw-core modules, so pw-core supplies them."""
    app = tmp_path / "app" / "orchestrators"
    app.mkdir(parents=True)
    (app / "flow.py").write_text("from pw_core.db import transaction\n", encoding="utf-8")
    monkeypatch.setattr(framework_rules, "_PLUGIN_MODULE", _NO_PLUGIN)
    assert check_layering(tmp_path / "app") == []
    _fake_plugin(monkeypatch, RULES=(), DB_MODULES=("pw_core.db",))
    assert [v.imported for v in check_layering(tmp_path / "app")] == ["pw_core.db"]
