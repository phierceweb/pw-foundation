"""The framework check's rules: hand-rolled code pw-foundation already replaces, each naming its fix.

pw-core contributes rules for what *it* replaces through :data:`PLUGIN_MODULE`.

A rule's ``name`` is what ``disable``, ``replace`` and ``exempt`` refer to. ``kind`` picks the
mechanism: ``import`` and ``raise`` match the AST, ``call`` is a regex over code with strings
and comments blanked, and ``json-write`` is its own AST shape.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pw_foundation._plugins import optional_module
from pw_foundation.exceptions import ConfigurationError


@dataclass(frozen=True)
class FrameworkRule:
    name: str
    kind: str  # "import" | "raise" | "call" | "json-write"
    use: str
    why: str
    pattern: re.Pattern[str] | None = None  # "call" rules only
    default_on: bool = True  # False: a 1.x addition a project must list under ``enable``


def _import(name: str, use: str, why: str) -> FrameworkRule:
    return FrameworkRule(name=name, kind="import", use=use, why=why)


def _raise(name: str, use: str, why: str) -> FrameworkRule:
    return FrameworkRule(name=name, kind="raise", use=use, why=why)


def _call(name: str, pattern: str, use: str, why: str) -> FrameworkRule:
    return FrameworkRule(name=name, kind="call", use=use, why=why, pattern=re.compile(pattern))


RULES: tuple[FrameworkRule, ...] = (
    _import(
        "logging",
        "pw_foundation.log.get_logger(__name__)",
        "structured events, and the project's log level and file wiring",
    ),
    _import(
        "dotenv",
        "pw_foundation.config.AppConfig",
        "entry points already load .env; a second loader fights the first",
    ),
    _import(
        "concurrent.futures",
        "pw_foundation.parallel.run_parallel",
        "a reporter, resilient failure collection, one cap on width",
    ),
    _import(
        "multiprocessing",
        "pw_foundation.parallel.run_parallel",
        "a reporter, resilient failure collection, without the process cost",
    ),
    _import(
        "hashlib",
        "pw_foundation.utils.hashing.content_hash",
        "one spelling of a digest for text and structured data",
    ),
    _raise(
        "Exception", "a pw_foundation.exceptions class", "an unsearchable log key and no context"
    ),
    _raise(
        "RuntimeError", "pw_foundation.exceptions.PreconditionError", "'required state not met'"
    ),
    _raise(
        "ValueError",
        "pw_foundation.exceptions.InvalidInputError",
        "'the caller passed something bad'",
    ),
    _call(
        "env-read",
        r"\bos\.(?:environ|getenv)\b",
        "pw_foundation.utils.env.resolve_int / resolve_str / resolve_bool",
        "malformed values warn and fall back instead of crashing",
    ),
    _call(
        "print",
        r"(?<![\w.])print\s*\(",
        "pw_foundation.log.get_logger(__name__), or pw_foundation.output.ConsoleReporter at the CLI boundary",
        "print() in a library is output nobody can level, filter or redirect",
    ),
    _call(
        "logger-exception",
        r"(?i)(?<!\w)(?:\w+_|_+)?log(?:ger|ging)?\.exception\s*\(",
        "pw_foundation.log.log_exception",
        "it carries the structured context and the project's event prefix",
    ),
    _call(
        "atomic-write",
        r"\bos\.replace\s*\(",
        "pw_foundation.utils.io.atomic_write_text / _json / _bytes",
        "the temp-file-then-rename dance is already written and tested",
    ),
    FrameworkRule(
        name="json-write",
        kind="json-write",
        use="pw_foundation.utils.io.atomic_write_json",
        why="a torn write leaves a file that parses as neither record",
    ),
)

# pw-core's rules about the facilities it provides (the HTTP clients its fetcher replaces) and the
# db modules the layering checker watches. Absent: base rules only. Present but broken: exit 2.
_PLUGIN_MODULE = "pw_core.guards_rules"
_KINDS = frozenset({"import", "raise", "call", "json-write"})


def _plugin():
    return optional_module(_PLUGIN_MODULE)


def all_rules() -> tuple[FrameworkRule, ...]:
    """Base rules followed by the plugin's, when pw-core is installed."""
    plugin = _plugin()
    if plugin is None:
        return RULES
    extra = tuple(getattr(plugin, "RULES", ()))
    for rule in extra:
        if not isinstance(rule, FrameworkRule) or rule.kind not in _KINDS:
            raise ConfigurationError(
                f"{_PLUGIN_MODULE}.RULES has a rule of unknown kind: {getattr(rule, 'kind', rule)!r}"
            )
    return (*RULES, *extra)


def rule_names() -> frozenset[str]:
    return frozenset(r.name for r in all_rules())


def layering_db_modules() -> tuple[str, ...]:
    """Modules an orchestrator must not import directly — the db layer, named by the plugin."""
    plugin = _plugin()
    return tuple(getattr(plugin, "DB_MODULES", ())) if plugin is not None else ()


__all__ = ["RULES", "FrameworkRule", "all_rules", "rule_names"]
