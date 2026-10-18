# Versioning

pw-foundation is 1.x and consumers pin `pw-foundation~=1.0`, which accepts every 1.x release. So:

- A minor release is **additive only**: new functions, new optional parameters with defaults that
  keep today's behavior, new guard checks that are **off** until a consumer turns them on.
- A patch release restores documented behavior.
- A default-behavior change, a removal, a rename, a stricter default in the gate: **2.0**.
- A `DeprecationWarning` precedes every removal by at least one minor and the removal lands in the
  next major.

Links to pw-core's docs are informational, not part of this package's contract.

Before tagging: full suite, `python -m pw_foundation.guards`, ruff, mypy, the fingerprint gate,
`rm -rf build dist`, then a wheel built, inspected (`unzip -l dist/*.whl | grep docs/`) and installed into a throwaway venv
(`python bin/verify-bare-install dist/*.whl`), and pw-core's suite against this tree.
