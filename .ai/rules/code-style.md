# Code Style

## General

- Python 3.12+ — use modern syntax (type unions with `|`, `match` where clearer).
- No star imports (`from x import *`).
- Imports grouped: stdlib → third-party → pw_foundation. One blank line between groups.
- Use `from __future__ import annotations` in files with forward references.
- Dependencies are the five in `pyproject.toml`; a module that needs anything else belongs in
  pw-core (`scope.md`).

## File size

File-size budgets are enforced by the `pw_foundation.guards` build gate (pre-commit + CI); the canonical
limit values live in `pw_foundation/guards/config.py`, not in prose. Split past the soft target by
concern, naming the new files `{domain}_{concern}.py`.

## Naming

- Files: `snake_case.py`. Private modules prefixed with `_` (e.g. `_util.py`).
- Classes: `PascalCase`. Exceptions end with `Error` or `Exception`.
- Functions/methods: `snake_case`. Private prefixed with `_`.
- Constants: `UPPER_SNAKE_CASE`.

## Functions

- Prefer pure functions that take inputs and return outputs.
- Use keyword-only arguments for functions with more than 2 parameters.

## Type hints

- All public function signatures must have type hints.
- Use `dict`, `list`, `tuple` (lowercase) not `Dict`, `List`, `Tuple`.
- Use `X | None` not `Optional[X]`.

## Docstrings

- Required on: modules, public classes, public functions with non-obvious behavior.
- Not required on: private helpers, obvious getters/setters, test functions.
- Use Google-style docstrings (Args/Returns/Raises sections).

## Error handling

- Raise from the `pw_foundation.exceptions` hierarchy — never bare `Exception`.
- Never swallow exceptions silently (`except Exception: pass`).

## Logging

- Use `pw_foundation.log.get_logger(__name__)` — never raw `print()` for operational output.
- `print()` is acceptable only in CLI entry points for user-facing output.
