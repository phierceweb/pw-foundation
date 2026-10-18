"""[tool.pw_guards.framework]: which framework rules run, what they name, and who is exempt.

The section's presence turns the check on. Every refusal is a ``ConfigurationError`` naming the
offending key or rule, so a typo cannot quietly switch a rule off — and the dataclasses refuse
the same things when built in code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeGuard

from pw_foundation.exceptions import ConfigurationError
from pw_foundation.guards.framework_rules import all_rules, rule_names

_SECTION = "[tool.pw_guards.framework]"
_KEYS = frozenset({"root", "disable", "enable", "replace", "exempt"})
_EXEMPT_KEYS = frozenset({"rule", "path", "reason"})
_MIN_REASON_WORDS = 4  # "legacy code" is a blanket skip wearing a key


@dataclass(frozen=True)
class FrameworkExemption:
    """One rule off for one path, with the reason; refused unless all three hold up."""

    rule: str
    path: str  # the whole path relative to the scan root, never a basename
    reason: str

    def __post_init__(self) -> None:
        _known(self.rule, "exempt")
        if not self.path.strip():
            raise ConfigurationError(f"{_SECTION} exemption for {self.rule!r} needs a path")
        if len(self.reason.split()) < _MIN_REASON_WORDS:
            raise ConfigurationError(
                f"{_SECTION} exemption for {self.rule!r} in {self.path} needs a reason of at "
                f"least {_MIN_REASON_WORDS} words: what the file does that pw-foundation does not cover"
            )


@dataclass(frozen=True)
class FrameworkConfig:
    """Which rules run and what they name; refuses an unknown rule or an empty replacement."""

    root: str | list[str] | None = None  # None: the gate's own root
    disable: tuple[str, ...] = ()
    enable: tuple[str, ...] = ()  # default-off rules this project takes
    replace: dict[str, tuple[str, str]] = field(default_factory=dict)  # rule -> (use, why)
    exempt: tuple[FrameworkExemption, ...] = ()

    def __post_init__(self) -> None:
        for name in self.disable:
            _known(name, "disable")
        for name in self.enable:
            _known(name, "enable")
        for name, value in self.replace.items():
            _known(name, "replace")
            if not (len(value) == 2 and all(isinstance(s, str) and s.strip() for s in value)):
                raise ConfigurationError(
                    f'{_SECTION} replace.{name} must be "replacement" or ["replacement", "why"]'
                )


def parse_framework_config(raw: object) -> FrameworkConfig:
    """Validate a parsed ``[tool.pw_guards.framework]`` table.

    ``replace`` takes ``"replacement"`` (keeping the rule's own why) or
    ``["replacement", "why"]``.

    Raises:
        ConfigurationError: an unknown key or rule name, a malformed value, or an
            exemption whose reason is missing or under four words.
    """
    table = _table(raw, _SECTION)
    _no_unknown_keys(table, _KEYS, _SECTION)
    root = _root(table.get("root"))
    disable = table.get("disable", [])
    if not _is_str_list(disable):
        raise ConfigurationError(f"{_SECTION} disable must be a list of rule names")
    enable = table.get("enable", [])
    if not _is_str_list(enable):
        raise ConfigurationError(f"{_SECTION} enable must be a list of rule names")
    replace = _table(table.get("replace", {}), f"{_SECTION} replace")
    exempt = table.get("exempt", [])
    if not isinstance(exempt, list):
        raise ConfigurationError(
            f"{_SECTION} exempt must be an array of tables: [[tool.pw_guards.framework.exempt]]"
        )
    return FrameworkConfig(
        root=root,
        disable=tuple(disable),
        enable=tuple(enable),
        replace={name: _replacement(name, v) for name, v in replace.items()},
        exempt=tuple(_exemption(e) for e in exempt),
    )


def _table(raw: object, where: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{where} must be a table")
    return raw


def _is_str_list(value: object) -> TypeGuard[list[str]]:
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def _root(value: object) -> str | list[str] | None:
    if value is None or isinstance(value, str):
        return value
    if _is_str_list(value):
        return value
    raise ConfigurationError(f"{_SECTION} root must be a path or a list of paths")


def _no_unknown_keys(table: dict[str, object], allowed: frozenset[str], where: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ConfigurationError(f"{where}: unknown key(s) {unknown} (allowed: {sorted(allowed)})")


def _known(name: str, where: str) -> str:
    if name not in rule_names():
        raise ConfigurationError(
            f"{_SECTION} {where}: unknown rule {name!r} (rules: {sorted(rule_names())})"
        )
    return name


def _replacement(name: str, value: object) -> tuple[str, str]:
    if isinstance(value, str) and value.strip():
        return value, next((r.why for r in all_rules() if r.name == name), "")
    if _is_str_list(value) and len(value) == 2:
        return value[0], value[1]
    raise ConfigurationError(
        f'{_SECTION} replace.{name} must be "replacement" or ["replacement", "why"]'
    )


def _exemption(raw: object) -> FrameworkExemption:
    table = _table(raw, f"{_SECTION} exemption")
    _no_unknown_keys(table, _EXEMPT_KEYS, f"{_SECTION} exemption")
    rule, path, reason = table.get("rule"), table.get("path"), table.get("reason")
    if not isinstance(rule, str):
        raise ConfigurationError(f"{_SECTION} exemption needs a rule name")
    return FrameworkExemption(rule=rule, path=_text(path), reason=_text(reason))


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


__all__ = ["FrameworkConfig", "FrameworkExemption", "parse_framework_config"]
