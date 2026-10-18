# Security Policy

## Reporting a vulnerability

**Please do not open a public issue for security vulnerabilities.**

Report privately through GitHub's [private vulnerability reporting][gh-pvr]:
the repository's **Security** tab → **Report a vulnerability**.

Include the affected version, a description of the issue, and steps to
reproduce. You can expect an initial acknowledgement within a few days.

[gh-pvr]: https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability

## Supported versions

Security fixes land in the latest 1.x release. Consumers pin `pw-foundation~=1.0`, so a
fix reaches them on their next install; there is no long-term-support branch.

## Scope

pw-foundation is a library, not a deployed service, and makes no network calls. The
security-relevant surfaces are:

- **`pw_foundation.config` / `pw_foundation.utils.env`** — read configuration, including
  secrets, from the environment and `.env`. Values are never logged;
  `pw-doctor` prints key-, token- and password-like variables as present/absent
  only and masks credentials in URLs.
- **`pw_foundation.utils.yaml`** — YAML is loaded with `yaml.safe_load` semantics only.
- **`pw-guards`** — parses source files with `ast` and `tokenize`; it never
  imports or executes the code it checks.
- **`pw-setup`** — the only command that writes: symlinks under the repo's
  `docs/`, never replacing a real file or directory.

Secrets must never be committed; pw-foundation does not log credential values.
