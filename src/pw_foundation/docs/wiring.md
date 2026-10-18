# Wiring a consumer — `pw-setup`

`pw-setup` puts what the installed packages ship where people and coding assistants look. Run it
from a project's root after `pip install pw-foundation` (and after installing pw-core, if the project
uses it). It is idempotent, never overwrites anything that is yours, and refuses to run in a
directory that is not a project (no `pyproject.toml`, `setup.cfg`, `setup.py` or `.git`) or in
your home directory.

```bash
pw-setup                       # the project root is the current directory
pw-setup --project-root path   # or name it
```

## What it does

| Creates | On a re-run |
|---|---|
| `.ai/rules/<rule>.md` for each starter rule a package ships, plus a relative `<rule>.mdc` link, and `.ai/rules/.pw-setup.json` recording what it copied | an **edited** rule is yours and is kept; an **unedited** copy follows the shipped rule when a release changes it; a rule you wrote yourself is never touched |
| `.ai/plans/`, `.ai/skills/` (with `.gitkeep`) | untouched |
| `docs/pw-foundation` → the installed package's bundled docs; `docs/pw-core` too when pw-core is installed | re-pointed when the venv moved; a leftover `docs/pw-core` link is removed once pw-core is gone |
| `.claude/{rules,plans,skills}` and `.cursor/{rules,plans,skills}` → `../.ai/...` | re-pointed if wrong |
| `.gitignore` entries for the docs links (in a git repo) | added once |
| `.pw-guards.toml` with `root = "app"` (a Python `app/` tree) or `root = "src/<package>"` (one package with `__init__.py`) | untouched when present; a layout it cannot tell is reported |
| a legacy gate config is **migrated**: `.pf-guards.toml` becomes `.pw-guards.toml` with its table renamed, so its limits and exemptions keep biting | both present = an error; the gate refuses to run beside the legacy file |
| a legacy `docs/pf-core` symlink is removed | a real directory there is reported, not touched |

It ends by printing the pins to put in `pyproject.toml` (`"pw-foundation~=<installed major.minor>"`,
and pw-core's when installed) and the `CLAUDE.md` pointer: assistants read `.ai/rules/` and
`docs/pw-foundation/modules.md` (and `docs/pw-core/modules.md`).

**The docs links are absolute paths into this machine's venv.** `pw-setup` adds them to
`.gitignore`; do not commit them. A site built from `docs/` (mkdocs, Sphinx) will pick them up
unless its config excludes them.

**Real directories win.** If `.claude/rules` (or `.cursor/rules`, or `docs/pw-foundation`) is a real
directory, `pw-setup` reports it and exits 1 instead of replacing it. Move the files into
`.ai/rules/` (skills into `.ai/skills/`), delete the emptied directory, and re-run — the editor
then reads them through the link.

Symlinks need Developer Mode or an elevated shell on Windows; without them, the rules and the
gate config still land and each failed link is reported.

## The starter rules

pw-foundation ships seven: `framework-first.md` (check the module index before hand-rolling; what to use
instead of `logging`, `os.environ`, `hashlib`, …), `code-style.md`, `logging.md`,
`error-handling.md`, `config-driven.md`, `docs-sync.md`, `plans.md`. Each carries Cursor's
frontmatter (`alwaysApply: true`), which Claude Code ignores. They are a starting point in the
project's own `.ai/rules/`: edit them, add project rules beside them, and they stay yours.
pw-core adds its own set (layering, anti-patterns, project structure) when it is installed; a
name shipped by both packages is reported as a collision and pw-foundation's copy applies.

## Checking it

`pw-doctor` reports the wiring read-only, under the `wiring` group: `docs_link.<package>` (FAIL on
a broken link, a non-symlink at the path, or a link into a *different* copy of the package),
`rules` (WARN for missing rules, FAIL for a broken `.mdc` link, WARN for a rule that still names
the old framework), `editor_links`, `guards_config` (FAIL while a legacy config is present), and
`leftovers`. The group SKIPs in a framework checkout or outside a project root.
