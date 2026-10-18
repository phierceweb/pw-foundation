# Modules

What each module in `src/pw_foundation/` is responsible for, grouped by concern. Every entry links to the module's own doc for usage details.

This file is the navigational index. It describes responsibilities, not APIs — for API-level detail (function signatures, parameters, examples) see the linked module doc. For install and pinning see [INSTALLATION.md](INSTALLATION.md).

The LLM clients, HTTP fetching, database, jobs, eval and web layers are in [pw-core](https://github.com/phierceweb/pw-core/blob/main/src/pw_core/docs/modules.md), which depends on this package.

---

## Table of Contents

- [Foundation](#foundation)
- [Build gate & tooling](#build-gate--tooling)
- [Utilities](#utilities)

---

## Foundation

| Module | Responsibility |
|--------|----------------|
| [Logging](logging.md) | structlog setup with colored console for development and JSON-lines for production ingestion. |
| [Exceptions](exceptions.md) | Two-branch hierarchy that keeps expected domain failures (`FlowException`) separate from unexpected system errors (`AppError`); `unwrap_flow_exception` recovers a validator's `InvalidInputError` from a pydantic wrapper. |
| [Config](config.md) | `AppConfig` base class. Resolution order: explicit override > environment variable > YAML > class default. Type coercion built in. |
| [Output reporters](output.md) | Reporter protocol for batch progress, with console (Rich) and structlog implementations. |
| [Parallel](parallel.md) | Thread-pool batch execution with progress reporting, per-item failure isolation, and opt-in end-of-batch summary log. |
| [Services](services.md) | Base class for single-domain business logic. Standard hooks for repos, logging, and configuration. |

## Build gate & tooling

| Module | Responsibility |
|--------|----------------|
| [Structural guards](guards.md) | Build gate (`python -m pw_foundation.guards` / `pw-guards`, config in `.pw-guards.toml`): fails pre-commit + CI on file-size violations (flat limits for library code, per-layer for `app/` trees), layering violations, and — once a project opts in — function length, comment budget and the framework check. |
| [Linting](linting.md) | How ruff and the structural gate divide the work, and the commands that run both. |
| [Doctor](doctor.md) | `pw-doctor` — runtime ground-truth attestation: loaded copy and version of pw-foundation (and pw-core when installed), interpreter, env resolution (redacted), consumer wiring; `--release` adds tag / CHANGELOG / dirty-tree checks. pw-core contributes its own checks when present. |

| [Wiring](wiring.md) | `pw-setup` — wires a consumer to the installed packages: docs links at `docs/pw-foundation/` and `docs/pw-core/`, starter rules into `.ai/rules/` (never overwriting the project's), `.claude/` and `.cursor/` symlinks, a first `.pw-guards.toml`. `pw-doctor` reports the result. |

## Utilities

| Module | Responsibility |
|--------|----------------|
| [Atomic file writes](io.md) | Crash-safe `atomic_write_text` / `atomic_write_json` for caches, manifests, and run-record sidecars. Target file is either old or new content, never a torn write. |
| [Env-var resolver](env.md) | `resolve_int` / `resolve_str` / `resolve_bool` / `resolve_positive_int` — explicit-arg → env var → default with warn-on-malformed, plus a `>= min_value` bounded variant. |
| [Config-path resolver](config-path.md) | `resolve_config_path` — find a config file via override-dir → CWD `config/` → package-bundled default; always absolute, bundled-as-floor. |
| [Content hashing](hashing.md) | `content_hash` — stable hex digest of text or a structured object (via `canonical_json`) for change-detection and cache keys. Not a security primitive. |
| [Slugify](slugify.md) | Fold free text to a stable lowercase ASCII slug (diacritics folded, punctuation collapsed) for filenames, ids, and URL fragments. |
| [IDs](ids.md) | URL-safe nanoid generation. |
| [Dates](dates.md) | Stable parsing, formatting, and range generation for ISO dates and YYYY-MM month labels. |
| [Periods](periods.md) | Resolve named period presets (`yesterday`, `last_7d`, `day:2026-05-12`) into `(start, end, label)` tuples — one shared label convention. |
| [JSON utils](json-utils.md) | Tolerant JSON parsing for columns that may already be parsed, plus `canonical_json` — sorted-key serialization so equal objects compare and hash identically. |
| [YAML utils](yaml-utils.md) | `safe_load` / `UniqueKeyLoader` — a drop-in for `yaml.safe_load` that raises on a repeated mapping key instead of silently keeping the last value. |
| [Throttle](throttle.md) | `Throttle` — thread-safe client-side request pacing (minimum interval / max-per-second) for staying under a rate-limited API's cap. |
| [Reload cache](reload-cache.md) | TTL hot-reload cache for config loaders — double-checked lock, per-call TTL read, key invalidation, optional serve-stale-on-error. |
