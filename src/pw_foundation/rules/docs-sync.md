---
description: Every substantive change ships with its documentation
alwaysApply: true
---

# Docs Sync

**Every substantive change ships with its documentation.** A change that adds, removes, or
changes a module's public behavior is incomplete without the matching doc update.

## What counts as substantive

- A public function, class or command added, removed, renamed, or changed in signature
- A behavior change in an existing module, even with the same API surface
- A new module
- A new rule in `.ai/rules/`
- A new operational setting (`.env.example` and the settings doc move together)

## What does not

- Internal refactors that leave public behavior alone
- Test-only changes
- Comment or docstring improvements

## Checklist

- [ ] Update the module's doc; update code examples that use the changed API
- [ ] A new doc goes into the project's docs index — a silently partial index is worse than none
- [ ] `CHANGELOG.md`: what shipped, functionality only — no rationale narratives, no attributions
- [ ] A new rule file gets a relative `.mdc` symlink: `ln -sf <name>.md <name>.mdc`
- [ ] Plans live in `.ai/plans/`, never the project root

## Principle

Code and docs travel together. When in doubt, update the doc.
