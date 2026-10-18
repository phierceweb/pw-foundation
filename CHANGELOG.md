# Changelog

Notable changes to pw-foundation, newest first. Consumers pin `pw-foundation~=1.0`; every 1.x release is additive only (see CONTRIBUTING).

## v1.0.0 — 2026-10-18

Initial release: the foundation layer of pf-core 0.26.0 as its own package, `pw_foundation`.

- `pw_foundation.log`, `pw_foundation.exceptions`, `pw_foundation.config`, `pw_foundation.output`, `pw_foundation.parallel`,
  `pw_foundation.services.Service`.
- `pw_foundation.utils`: `io`, `env`, `hashing`, `slugify`, `dates`, `ids` (`generate_id`; table-checked
  allocation lives in pw-core's `pw_core.db.ids`), `json`, `yaml`, `throttle`, `config_path`,
  `periods`, `reload_cache`. The LLM-output helpers (`json_recovery`, `vocab`, `similarity`,
  `relative_dates`) stay in pw-core.
- `AppConfig` carries the generic settings (`LOG_LEVEL`, `LOG_FILE`, `APP_NAME`, `APP_URL`);
  the framework settings live on pw-core's subclass.
- The structural build gate: `pw-guards` / `python -m pw_foundation.guards`, configured by
  `.pw-guards.toml` (`[tool.pw_guards]`). The framework check's rules cover pw-foundation's own
  facilities; pw-core contributes rules for its own (`pw_core.guards_rules.RULES`) and the db
  modules the layering checker watches (`DB_MODULES`) when installed. A rule added in 1.x is off
  until a project lists it under `enable`. A present `.pw-guards.toml` without a
  `[tool.pw_guards]` table exits 2. A leftover `.pf-guards.toml` or `[tool.pf_guards]`
  table exits 2 with the rename message.
- `pw-doctor`: loaded copy and version of pw-foundation and, when installed, pw-core, with a
  `copy.mixed` warning when one is editable and the other from site-packages; interpreter; env
  resolution; consumer wiring; `--release` checks (the CHANGELOG row reads `## vX.Y.Z`, `## [X.Y.Z]`
  and `## X.Y.Z` headings). pw-core supplies its own checks through
  `pw_core.doctor.checks()`.
- `pw-setup`: links `docs/pw-foundation` (and `docs/pw-core` when installed) to the bundled docs,
  copies the seven starter rules shipped in `pw_foundation/rules/` into `.ai/rules/` (an edited rule is
  kept; an unedited copy follows the shipped one), points `.claude/` and `.cursor/` at `.ai/`,
  adds the docs links to `.gitignore`, writes a first `.pw-guards.toml` or migrates a legacy
  `.pf-guards.toml` into it, and removes leftover links. It refuses a directory that is not a
  project. `pw-doctor` reports `wiring.rules`, `wiring.editor_links`, `wiring.guards_config` and
  `wiring.leftovers`; a docs link into a different copy of the package is a FAIL.
