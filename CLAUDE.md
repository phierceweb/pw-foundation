# pw-foundation — the foundation package

## What this is

`pw-foundation` is the dependency-light layer under every project in this family: structured logging
(`pw_foundation.log`), the exception hierarchy (`pw_foundation.exceptions`), config and env resolution
(`pw_foundation.config`, `pw_foundation.utils.env`), console output, parallel helpers, the `Service` base,
pure utilities, and the structural build gate (`pw-guards`, `pw_foundation.guards`) with `pw-doctor`
and `pw-setup`. Five dependencies, no extras.

`pw-core` (the LLM / HTTP / database / web framework) depends on it. Projects that need none of
that install only pw-foundation.

## Rules

All project rules live in `.claude/rules/` (symlinked to `.ai/rules/`): `scope.md` (what may live
here), `versioning.md` (1.x is additive-only), `code-style.md`, `docs-sync.md`, `plans.md`.

## Plans

Tracking documents live in `.claude/plans/` (symlinked to `.ai/plans/`), never the repo root.

## Docs

One reference doc per module in `src/pw_foundation/docs/`, shipped in the wheel; `modules.md` is the
index. A consumer links them at `docs/pw-foundation/` with `pw-setup`.

## How projects use this

```bash
pip install pw-foundation            # or pin: "pw-foundation~=1.0" in pyproject.toml
pip install -e ../pw-foundation      # editable, when developing pw-foundation alongside a consumer
```

## Testing

```bash
pip install -e ".[dev]"
bin/test
.venv/bin/python -m pw_foundation.guards
```

pw-core imports this package: run pw-core's suite against this tree before any release here.
