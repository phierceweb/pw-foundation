# Doctor — runtime ground-truth attestation

`pw-doctor` prints verified facts about the current environment so agents and
humans stop acting on stale assumptions.

---

## Table of Contents

- [Running it](#running-it)
- [Core checks (always on)](#core-checks-always-on)
- [Checks contributed by pw-core](#checks-contributed-by-pw-core)
- [`--release` (opt-in)](#--release-opt-in)
- [Invariants](#invariants)
- [Adding a new check](#adding-a-new-check)

## Running it

Run it from any consumer project:

```bash
.venv/bin/pw-doctor            # core checks: local, read-only, no network
.venv/bin/pw-doctor --db       # + pw-core's read-only database attestation (when pw-core is installed)
.venv/bin/pw-doctor --release  # + release-state checks (tag / version / CHANGELOG / tree)
```

The console script lands with the install; `python -m pw_foundation.doctor` is the
always-available module form.

Exit code: `0` when no check FAILs (WARNs don't flip it), `1` otherwise.

## Core checks (always on)

| Check | Attests |
|---|---|
| `copy.pw-foundation`, `copy.pw-core` | Which copy of each installed package is actually imported (path, editable/source vs site-packages, `importlib.metadata` version). WARNs when an editable install's metadata version disagrees with the adjacent `pyproject.toml` — the stale-editable trap. `pw-core` appears only when it is installed. |
| `copy.mixed` | WARN when one package is editable and the other comes from site-packages: edits to the site-packages one never reach this venv. Names both paths and the fix (`pip install -e ../pw-foundation -e ../pw-core`). Absent when both match. |
| `python.interpreter` | Interpreter version (FAIL below the 3.12 floor) and active venv path. |
| `env.resolution` | `LOG_LEVEL` and `LOG_FILE` as the app would see them — a `.env` in the working directory is loaded first (shell values win), and the report names which. |
| `wiring.docs_link.pw-foundation`, `wiring.docs_link.pw-core` | Is `docs/<package>` a live symlink to that package's installed docs. WARN names the fix (`pw-setup`); FAIL on a broken link or a non-symlink squatting on the path. The whole group SKIPs in a framework checkout or a directory with no `docs/`. |
| `wiring.rules`, `wiring.editor_links`, `wiring.guards_config`, `wiring.leftovers` | Whether every starter rule is present with a working `.mdc` link and none still names the old framework; whether `.claude/` and `.cursor/` point at `.ai/`; whether `.pw-guards.toml` exists (FAIL while a legacy gate config is present); leftover links and directories. WARN names `pw-setup`. See [wiring.md](wiring.md). |

## Checks contributed by pw-core

When pw-core is installed, `pw-doctor` appends the rows its `pw_core.doctor.checks()` returns, under their own groups; a plugin that is present but fails to load becomes a `plugin.pw_core.doctor` FAIL row instead of a crash. pw-core's doctor doc describes those checks. Without pw-core, `--db` adds nothing.

## `--release` (opt-in)

Read-only git introspection of the working-directory project — a local preflight
before you tag a release. Mirrors the CI tag-vs-version guard in `publish.yml`, so a
mismatch surfaces at your desk instead of when the upload 400s.

| Check | Attests |
|---|---|
| `release.versions` | `pyproject.toml` `version` vs the first versioned heading in `CHANGELOG.md` — `## vX.Y.Z`, `## [X.Y.Z]` or `## X.Y.Z`, with or without a date after it; an `Unreleased` heading above it is skipped. FAIL on mismatch ("sync before tagging"); WARN when the CHANGELOG has no v-heading; SKIP without a pyproject version. |
| `release.tag` | Whether `v<pyproject-version>` is among the git tags pointing at HEAD. FAIL when HEAD is tagged a different version (a build of that tag won't match the package); SKIP when nothing is tagged at HEAD. |
| `release.tree` | `git status --porcelain`. WARN on uncommitted changes — they're not part of any build of HEAD. |

SKIPs the whole group when the working directory isn't a git repo (or `git` is absent).

## Invariants

Doctor never writes, never touches the network except pw-core's opt-in `--db`
connect (`--release` runs read-only local git commands), and never imports
consumer application code. It is safe to run at any time, in any state,
including mid-incident.

## Adding a new check

A pw-foundation check is a function returning `list[CheckResult]` in `pw_foundation/doctor.py`
(or `_doctor_release.py` for a `--release` check), appended to the internal checks
tuple. A check about pw-core's surface belongs in `pw_core.doctor.checks()`, which
`pw-doctor` discovers by import (`PLUGIN_MODULE`) — there is no registry beyond that.
Keep new checks inside the invariants above: read-only, no network by default, no
consumer-code imports.
