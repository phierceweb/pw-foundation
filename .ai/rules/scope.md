# Scope

pw-foundation is the foundation every Python project in this family installs: structured logging, the
exception hierarchy, config and env resolution, console output, parallel helpers, the `Service`
base, pure utilities, and the structural build gate. Its dependencies are exactly python-dotenv,
pyyaml, structlog, nanoid and rich.

## What must never be here

- Anything that needs httpx, pydantic, sqlalchemy, fastapi, typer or an LLM SDK — that is pw-core.
- Anything about LLMs, HTTP fetching, documents, pipelines, databases or web serving, even when
  stdlib-only — domain code churns; this package must not.
- Business logic or project-specific values.

A module earns a place here when a project with no LLM, no database and no web layer would use it.
