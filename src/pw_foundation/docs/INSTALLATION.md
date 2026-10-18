# Installation

How to install `pw-foundation`, pin it, and develop it alongside a consumer.

`pw-foundation` is one tier: five small dependencies (python-dotenv, pyyaml, structlog, nanoid, rich), no extras. It is the foundation layer formerly published as part of pf-core (through 0.26.0); from pw-core 0.27.0 it ships separately so projects that need only logging, exceptions, config and the build gate pin it alone.

## Quick reference

| Scenario | Command |
|----------|---------|
| A project with no LLM, database or web layer | `pip install pw-foundation`, and pin `"pw-foundation~=1.0"` in `pyproject.toml` |
| A project on the pw-core framework | pin both: `"pw-foundation~=1.0"` and `"pw-core[<extras>]~=<current pw-core minor>"` — a pw-core consumer imports `pw_foundation.*` directly, so it declares it |
| Developing pw-foundation itself | `pip install -e path/to/pw-foundation` |
| Developing pw-core alongside pw-foundation | `pip install -e ../pw-foundation -e ../pw-core` — both editable, or `pw-doctor` warns about a mixed install |

**The pin is two components.** `pw-foundation~=1.0` accepts every 1.x release; a three-component pin (`~=1.0.0`) would accept only 1.0.x and silently freeze a project out of 1.1. pw-foundation's 1.x line is additive-only (see [CONTRIBUTING](https://github.com/phierceweb/pw-foundation/blob/main/CONTRIBUTING.md)), so the wide pin is safe.

## Wiring a consumer

From the project root, after installing:

```bash
pw-setup        # docs links, starter rules in .ai/rules/, .claude/ and .cursor/ symlinks, a first .pw-guards.toml
pw-doctor       # which copy is loaded, interpreter, env resolution, wiring; --release adds tag/CHANGELOG checks
pw-guards       # the structural build gate — reads .pw-guards.toml at the repo root
```

`pw-setup` is idempotent and never overwrites what is yours — an edited rule or an existing config stays as it is, and a legacy `.pf-guards.toml` is migrated. With pw-core installed it wires that package too. Details: [wiring.md](wiring.md); the gate's config: [guards.md](guards.md).

## Local development

An editable install picks up edits with no reinstall:

```bash
cd my-project
pip install -e ../pw-foundation
```

If the project also uses pw-core, install pw-core editable too. `pip install -e ../pw-core` alone resolves `pw-foundation` from PyPI, so edits to pw-foundation would not reach that venv; `pw-doctor` reports this as `copy.mixed`.

## From PyPI

```toml
dependencies = [
    "pw-foundation~=1.0",
]
```

Then `pip install -e .` resolves it from PyPI.

## Verifying an install

```bash
python -c "import pw_foundation; print(pw_foundation.__version__)"
pw-doctor
```

`pw-doctor` prints the loaded path (site-packages vs an editable source tree) and the version; a WARN on `copy.pw-foundation` means the editable tree's `pyproject.toml` disagrees with the installed metadata — reinstall with `pip install -e .`.
