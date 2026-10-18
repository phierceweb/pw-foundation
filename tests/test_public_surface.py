"""The 1.x surface of record: which modules exist and what each one exports.

Consumers pin ``pw-foundation~=1.0``, so a public module and every name in its ``__all__`` is a
promise. Adding a module or a name is additive (CHANGELOG it); removing or renaming one is 2.0.
Internal modules are underscore-prefixed and make no promise.
"""

from __future__ import annotations

import importlib
import pkgutil

import pw_foundation

# module -> its __all__ (None: a public module that is not an import surface)
SURFACE: dict[str, list[str] | None] = {
    "pw_foundation": None,
    "pw_foundation.config": ["AppConfig"],
    "pw_foundation.doctor": ["CheckResult", "redact_value", "run_checks", "run_cli"],
    "pw_foundation.exceptions": [
        "FlowException",
        "InvalidInputError",
        "PreconditionError",
        "ActionNotAllowedError",
        "NotFoundError",
        "ConfigurationError",
        "AppError",
        "ClientError",
        "DataError",
        "TaskError",
        "unwrap_flow_exception",
    ],
    "pw_foundation.log": [
        "setup_logging",
        "get_logger",
        "log_verbose",
        "log_exception",
        "log_context",
    ],
    "pw_foundation.output": ["Reporter", "NullReporter", "ConsoleReporter", "LogReporter"],
    "pw_foundation.parallel": ["run_parallel", "resilient"],
    "pw_foundation.services": ["Service"],
    "pw_foundation.services.base": ["Service"],
    "pw_foundation.wiring": ["installed_docs_dir", "installed_rules_dir", "run_cli"],
    "pw_foundation.guards": [
        "CommentBudget",
        "FileSizeViolation",
        "FrameworkBreach",
        "FrameworkConfig",
        "FrameworkExemption",
        "FunctionLengthViolation",
        "FunctionLimits",
        "GuardsConfig",
        "LayeringViolation",
        "ProseViolation",
        "check_framework",
        "check_layering",
        "filter_baselined",
        "load_guards_config",
        "scan_comment_budget",
        "scan_file_sizes",
        "scan_function_lengths",
    ],
    "pw_foundation.guards.__main__": None,
    "pw_foundation.guards.comments": [
        "CommentBudget",
        "ProseViolation",
        "prose_and_code",
        "scan_comment_budget",
    ],
    "pw_foundation.guards.config": [
        "LAYER_DEFAULTS",
        "UTIL_LIMIT",
        "SOFT_FRACTION",
        "HARD_DEFAULT",
        "SOFT_DEFAULT",
        "FunctionLimits",
        "GuardsConfig",
        "load_guards_config",
    ],
    "pw_foundation.guards.framework": ["FrameworkBreach", "check_framework"],
    "pw_foundation.guards.framework_config": [
        "FrameworkConfig",
        "FrameworkExemption",
        "parse_framework_config",
    ],
    "pw_foundation.guards.framework_rules": ["FrameworkRule", "RULES", "all_rules", "rule_names"],
    "pw_foundation.guards.functions": ["FunctionLengthViolation", "scan_function_lengths"],
    "pw_foundation.guards.layering": ["ALLOWED_IMPORTS", "LayeringViolation", "check_layering"],
    "pw_foundation.guards.structure": [
        "FileSizeViolation",
        "filter_baselined",
        "scan_file_sizes",
        "run_cli",
    ],
    "pw_foundation.utils": [
        "content_hash",
        "canonical_json",
        "safe_json_col",
        "safe_json_loads",
        "slugify",
        "Throttle",
    ],
    "pw_foundation.utils.config_path": ["resolve_config_path"],
    "pw_foundation.utils.dates": [
        "now_iso",
        "parse_date",
        "try_parse_date",
        "month_label",
        "date_range",
        "month_range",
        "parse_timestamp",
        "to_iso",
    ],
    "pw_foundation.utils.env": [
        "resolve_int",
        "resolve_float",
        "resolve_str",
        "resolve_bool",
        "resolve_positive_int",
    ],
    "pw_foundation.utils.hashing": ["content_hash"],
    "pw_foundation.utils.ids": ["generate_id"],
    "pw_foundation.utils.io": [
        "atomic_write_text",
        "atomic_write_bytes",
        "atomic_write_json",
        "DEFAULT_MODE",
    ],
    "pw_foundation.utils.json": ["safe_json_loads", "safe_json_col", "canonical_json"],
    "pw_foundation.utils.periods": [
        "Period",
        "ROLLING_PRESETS",
        "resolve",
        "parse_period_arg",
        "parse_anchor_arg",
        "days_in_period",
    ],
    "pw_foundation.utils.reload_cache": ["ReloadCache"],
    "pw_foundation.utils.slugify": ["slugify"],
    "pw_foundation.utils.throttle": ["Throttle"],
    "pw_foundation.utils.yaml": ["UniqueKeyLoader", "safe_load"],
}
INTERNAL_MODULES = {
    "pw_foundation._doctor_release",
    "pw_foundation._doctor_types",
    "pw_foundation._plugins",
    "pw_foundation._wiring_check",
    "pw_foundation._wiring_rules",
    "pw_foundation.guards._adoption",
    "pw_foundation.guards._framework_converted",
    "pw_foundation.guards._framework_env",
    "pw_foundation.guards._opt_in",
    "pw_foundation.guards._sources",
}


def _modules() -> set[str]:
    return {"pw_foundation"} | {
        m.name for m in pkgutil.walk_packages(pw_foundation.__path__, "pw_foundation.")
    }


def test_module_set_is_the_surface_of_record() -> None:
    assert _modules() == set(SURFACE) | INTERNAL_MODULES


def test_every_public_module_exports_exactly_its_surface() -> None:
    drift = {}
    for name, expected in SURFACE.items():
        mod = importlib.import_module(name)
        if expected is None:
            if hasattr(mod, "__all__"):
                drift[name] = f"unexpected __all__ {sorted(mod.__all__)}"
            continue
        actual = sorted(getattr(mod, "__all__", ()))
        if actual != sorted(expected):
            drift[name] = f"__all__ is {actual}, surface says {sorted(expected)}"
    assert drift == {}, drift


def test_every_surface_name_is_a_public_attribute() -> None:
    bad = [
        f"{name}.{entry}"
        for name, expected in SURFACE.items()
        for entry in expected or ()
        if entry.startswith("_") or not hasattr(importlib.import_module(name), entry)
    ]
    assert bad == []
