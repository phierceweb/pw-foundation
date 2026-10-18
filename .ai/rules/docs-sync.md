# Docs Sync

**Every substantive change must include documentation updates.** A changeset that adds, removes, or
changes a module's public API is incomplete without the matching doc update.

## What counts as substantive

- Public function/class added, removed, renamed, or signature changed
- Behavior change in an existing module (even if the API surface is the same)
- New module under `src/pw_foundation/`
- New rule added

## What does NOT require doc updates

- Internal refactors that don't change public API
- Test-only changes
- Comment or docstring improvements

## Checklist

### Existing module's public API changed?
- [ ] Update the corresponding `src/pw_foundation/docs/<module>.md`
- [ ] Update code examples that use the changed API
- [ ] pw-core imports this package: check its callers before removing or renaming anything
      (`versioning.md` — a removal is a major)

### New file added to `src/pw_foundation/docs/`?
- [ ] Add it to `docs/modules.md` under the right group — the index must list **every** doc
- [ ] Add it to the README's collapsed **All docs** index as an absolute `blob/main` URL — the
      README is the PyPI long-description (relative links 404 there)
- [ ] Add it to `llms.txt` at the repo root (raw URL form) — enforced by `tests/test_llms_txt.py`

### New rule file added to `.ai/rules/`?
- [ ] Create the rule as `<name>.md`
- [ ] Create a relative symlink: `ln -sf <name>.md <name>.mdc`

### CHANGELOG
- [ ] One entry per shipped change, functionality only — no rationale narratives, no attributions

## Principle

Code and docs travel together. When in doubt, update the doc.
