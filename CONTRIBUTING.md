# Contributing to pw-foundation

Thanks for your interest. pw-foundation is the dependency-light foundation under pw-core
and the projects built on it; contributions that keep it small, well-tested, and
documented are welcome.

## Scope — read this first

pw-foundation ships what a Python project with no LLM, no database and no web layer still
uses: structured logging, the exception hierarchy, config and env resolution,
console output, parallel helpers, the `Service` base, pure utilities, and the
structural build gate. Its dependencies are exactly python-dotenv, pyyaml,
structlog, nanoid and rich. Anything that needs more — HTTP, LLM clients, SQL, a
web framework — belongs in [pw-core](https://github.com/phierceweb/pw-core). See
[`.ai/rules/scope.md`](.ai/rules/scope.md).

## Development setup

Python 3.12+ is required.

```bash
git clone https://github.com/phierceweb/pw-foundation
cd pw-foundation
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Before you open a pull request

These checks run in CI and as pre-commit hooks — run them locally first:

```bash
bin/test                                  # full suite, must be green
.venv/bin/ruff check src tests bin        # lint
.venv/bin/ruff format --check src tests bin
.venv/bin/python -m mypy                  # type check (config in [tool.mypy])
.venv/bin/python -m pw_foundation.guards        # structural gate (reads .pw-guards.toml)
```

And hold the change to these standards:

- **Tests travel with code.** New behavior needs tests; a bug fix needs a
  regression test that fails before your change and passes after.
- **Docs travel with code.** A change to a module's public API is incomplete
  without the matching `src/pw_foundation/docs/*.md` update — see
  [`.ai/rules/docs-sync.md`](.ai/rules/docs-sync.md).
- **File-size gate.** Python files over the hard limit fail the build; over the
  soft target they warn (canonical values in `pw_foundation/guards/config.py`).
- **pw-core must still pass.** pw-core imports this package; run its suite
  against your tree before tagging.

## Coding conventions

The full set lives in [`.ai/rules/`](.ai/rules/). The essentials:

- Modern Python 3.12+ syntax — `X | None`, lowercase `dict`/`list`/`tuple`.
- Type hints on every public signature; Google-style docstrings on public APIs.
- Structured logging via `pw_foundation.log.get_logger(__name__)` — never bare `print`
  outside CLI entry points.
- Raise from the `pw_foundation.exceptions` hierarchy — never a bare `Exception`.

## Versioning & deprecations

Consumers pin `pw-foundation~=1.0`, which accepts every 1.x release, so a 1.x release is
**additive only**: new functions, new optional parameters whose defaults keep
today's behavior, new guard checks that stay off until a project turns them on. A
patch release restores documented behavior. A default-behavior change, a removal,
a rename, or a stricter gate default is a major release, preceded by a
`DeprecationWarning` for at least one minor. Anything documented under
`src/pw_foundation/docs/` is the surface that contract covers.

## License

Contributions are accepted under the Apache License 2.0. Opening a pull request
licenses your work to the project under those terms.

## Questions

Open an issue for bugs and feature requests. For anything security-sensitive,
follow [`SECURITY.md`](SECURITY.md) instead of filing a public issue.
