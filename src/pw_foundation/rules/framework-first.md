---
description: Check the framework's module index before writing a helper; what to use instead of logging, os.environ, hashlib and friends
alwaysApply: true
---

# Framework First

Before writing a helper, check whether the framework already has it. The module index is
`docs/pw-foundation/modules.md` — and `docs/pw-core/modules.md` on a pw-core project — a symlink into
the installed package's own docs, so it matches the version in the venv (`pw-setup` recreates it).

A framework's surface is larger than one session's memory of it. Check before hand-rolling, and
let the gate check too: `pw-guards --framework --report` lists every hand-rolled replacement for
what the framework ships.

| Instead of | Use |
|---|---|
| `import logging` | `pw_foundation.log.get_logger(__name__)` |
| `os.environ` / `os.getenv` | `pw_foundation.utils.env.resolve_str` / `resolve_int` / `resolve_bool` |
| `from dotenv import load_dotenv` | `pw_foundation.config.AppConfig` — the entry point loads `.env` once |
| `raise Exception` / `RuntimeError` / `ValueError` at a boundary | `pw_foundation.exceptions` (`InvalidInputError`, `PreconditionError`, `NotFoundError`, …) |
| `logger.exception(...)` | `pw_foundation.log.log_exception` |
| `print()` for operational output | `pw_foundation.log`, or `pw_foundation.output.ConsoleReporter` at the CLI boundary |
| `os.replace` after a temp write; `path.write_text(json.dumps(...))` | `pw_foundation.utils.io.atomic_write_text` / `atomic_write_json` / `atomic_write_bytes` |
| `hashlib` for a content digest | `pw_foundation.utils.hashing.content_hash` |
| `concurrent.futures` / `multiprocessing` for a batch | `pw_foundation.parallel.run_parallel` |
| `requests` / `httpx` (pw-core projects) | `pw_core.fetch`; LLM and search APIs through `pw_core.clients` |

## Where the boundary sits

Write down which modules form the entry layer (the CLI, the web routes) and which are the
library. The entry layer is where `setup_logging` is called, `pw_foundation.exceptions` classes are
raised for the user, and output happens; the library stays importable and quiet. The framework
check's `exempt` and `disable` keys in `.pw-guards.toml` encode that decision — state it here so
the next reader does not re-derive it.
