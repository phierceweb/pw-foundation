# pw-foundation

[![PyPI](https://img.shields.io/pypi/v/pw-foundation)](https://pypi.org/project/pw-foundation/)

The dependency-light foundation for a Python project: structured logging, an exception hierarchy that keeps expected domain failures apart from real errors, configuration resolved from the environment, console output and parallel helpers, a `Service` base class, a set of pure utilities, and a structural build gate that fails CI when a file, a function or an import crosses the line the project drew. Five small dependencies (python-dotenv, pyyaml, structlog, nanoid, rich), no extras, no HTTP or database stack.

pw-foundation is the foundation layer formerly shipped inside pf-core (through 0.26.0); it is published on its own so a project that needs none of the LLM, database or web machinery can pin this package alone. Projects that do need that machinery install [pw-core](https://github.com/phierceweb/pw-core), which depends on this.

## Install

```bash
pip install pw-foundation
```

Pin it as `"pw-foundation~=1.0"` — two components. The 1.x line is additive-only (see [Versioning](#versioning)), so the wide pin is safe and picks up every 1.x release.

## What you get

| Module | Does |
|---|---|
| `pw_foundation.log` | structlog setup: colored console in development, JSON lines to a file in production; `get_logger(__name__)`, `log_exception(exc, …)` with a searchable `PREFIX-ClassName` event key. |
| `pw_foundation.exceptions` | `FlowException` (expected: `InvalidInputError`, `PreconditionError`, `NotFoundError`, `ConfigurationError`, …) vs `AppError` (unexpected: `ClientError`, `DataError`, `TaskError`, with a `context` dict and a `cause`). `unwrap_flow_exception` recovers a validator's error from a pydantic wrapper. |
| `pw_foundation.config` | `AppConfig`: explicit override → environment variable → YAML → class default, with type coercion. Carries only the generic settings; pw-core's subclass adds the framework's. |
| `pw_foundation.utils.env` | `resolve_int` / `resolve_str` / `resolve_bool`: kwarg → env var → default, warning on a malformed value instead of crashing. |
| `pw_foundation.output` | A `Reporter` protocol for batch progress, with Rich console and structlog implementations. |
| `pw_foundation.parallel` | `run_parallel`: a thread pool with per-item failure isolation, a progress reporter, contextvars carried into workers, and one summary log at the end. |
| `pw_foundation.services` | `Service`: the base for single-domain business logic, with a logger, injected config, and repositories that share its connection. |
| `pw_foundation.utils.*` | Atomic file writes, content hashing, slugs, ids, dates and periods, tolerant JSON parsing, a duplicate-key-refusing YAML loader, a request throttle, a TTL reload cache. |

### The build gate

`pw-guards` turns structural rules into a check that fails pre-commit and CI: file-size budgets (flat for a library, per-layer for an `app/` tree), import layering, and — once a project opts in — a function-length limit, a comment budget, and a framework check that refuses hand-rolled replacements for what the foundation already provides. Three lines of config at the repo root:

```toml
# .pw-guards.toml
[tool.pw_guards]
root = "src/my_package"
```

```bash
pw-guards          # or: python -m pw_foundation.guards
```

A misconfigured gate exits 2 with the reason rather than passing silently. Details: [guards.md](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/guards.md).

### Doctor and setup

`pw-doctor` prints verified facts about the environment — which copy of the package is loaded (and whether an editable install has gone stale), the interpreter, the resolved env vars, the repo's wiring — and with `--release` checks the tag, `pyproject.toml` and `CHANGELOG.md` agree before you publish. `pw-setup` wires a project in one command: it links the installed package's bundled docs at `docs/pw-foundation/`, copies the starter rules (framework-first, code style, logging, error handling, config, docs discipline, plans) into `.ai/rules/` without ever overwriting yours, points `.claude/` and `.cursor/` at `.ai/`, and writes a first `.pw-guards.toml`. With pw-core installed it wires that package too. `pw-doctor` is read-only.

## Used with pw-core

[pw-core](https://github.com/phierceweb/pw-core) adds the LLM clients and output guards, run tracking, budgets, the eval harness, the SQLAlchemy database layer, background jobs and the FastAPI web layer on top of this package. A pw-core project pins both (`"pw-foundation~=1.0"` and `"pw-core[...]"`) because it imports `pw_foundation.*` directly; `pw-doctor` then reports both copies and warns when one is editable and the other is not.

## Documentation

Every module has a reference doc, shipped inside the package under `pw_foundation/docs/` so an installed copy always matches its version. `pw-setup` links them into a consumer repo; from Python:

```bash
python -c "import pw_foundation, pathlib; print(pathlib.Path(pw_foundation.__file__).parent / 'docs')"
```

<details>
<summary><b>All docs</b> — every file in <code>src/pw_foundation/docs/</code>, one link each</summary>

- [INSTALLATION](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/INSTALLATION.md)
- [modules](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/modules.md)
- [config](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/config.md)
- [config-path](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/config-path.md)
- [dates](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/dates.md)
- [doctor](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/doctor.md)
- [env](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/env.md)
- [exceptions](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/exceptions.md)
- [guards](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/guards.md)
- [hashing](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/hashing.md)
- [ids](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/ids.md)
- [io](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/io.md)
- [json-utils](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/json-utils.md)
- [linting](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/linting.md)
- [logging](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/logging.md)
- [output](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/output.md)
- [parallel](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/parallel.md)
- [periods](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/periods.md)
- [reload-cache](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/reload-cache.md)
- [services](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/services.md)
- [slugify](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/slugify.md)
- [throttle](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/throttle.md)
- [wiring](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/wiring.md)
- [yaml-utils](https://github.com/phierceweb/pw-foundation/blob/main/src/pw_foundation/docs/yaml-utils.md)

</details>

## Versioning

Consumers pin `pw-foundation~=1.0`, so a 1.x release is additive only: new functions, new optional parameters whose defaults keep today's behavior, new guard checks that stay off until a project turns them on. A default-behavior change, a removal, a rename or a stricter gate default is a major release, preceded by a `DeprecationWarning` for at least one minor. Anything documented under `src/pw_foundation/docs/` is the surface that contract covers. History: [CHANGELOG](https://github.com/phierceweb/pw-foundation/blob/main/CHANGELOG.md).

## Development

```bash
git clone https://github.com/phierceweb/pw-foundation
cd pw-foundation
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
bin/test
python -m pw_foundation.guards
```

CI runs the suite on Python 3.12, 3.13 and 3.14 plus a bare-install job that proves every module imports with none of the HTTP, validation or database stacks present. See [CONTRIBUTING](https://github.com/phierceweb/pw-foundation/blob/main/CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](https://github.com/phierceweb/pw-foundation/blob/main/LICENSE).
