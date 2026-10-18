"""Bare-install smoke check — run INSIDE a venv that has only `pip install .` of pw-foundation.

Proves every module imports on the five declared dependencies, that no HTTP /
validation / database stack came along, and that the three console scripts run.

Invoked by `bin/verify-bare-install`. Not a pytest test (it must run in the bare
venv, not the dev venv) — the filename intentionally avoids `test_*` so pytest
does not collect it. Exits non-zero on any failure.
"""

import importlib
import pkgutil
import shutil
import subprocess
import sys

failures: list[str] = []


def check(desc, fn):
    try:
        fn()
        print(f"PASS: {desc}")
    except AssertionError as e:
        print(f"FAIL: {desc}: {e}")
        failures.append(desc)
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {desc}: {type(e).__name__}: {e}")
        failures.append(desc)


# 1. Every module imports with only the declared deps installed.
import pw_foundation  # noqa: E402

modules = ["pw_foundation"] + [
    m.name for m in pkgutil.walk_packages(pw_foundation.__path__, prefix="pw_foundation.")
]
for mod in modules:
    check(f"import {mod}", lambda m=mod: importlib.import_module(m))


def _walked_subpackages():
    assert len(modules) > 30, f"only {len(modules)} modules found — walk_packages did not recurse"


check("walked more than the package root", _walked_subpackages)


# 2. The heavy stacks must be absent.
for pkg in ["httpx", "pydantic", "json_repair", "tenacity", "typer", "sqlalchemy", "fastapi"]:

    def _absent(p=pkg):
        try:
            importlib.import_module(p)
        except ImportError:
            return
        raise AssertionError(f"{p} unexpectedly importable")

    check(f"{pkg} NOT installed", _absent)


# 3. The console scripts landed and run.
def _script_runs(name):
    exe = shutil.which(name)
    assert exe, f"{name} not on PATH of this venv"
    proc = subprocess.run([exe, "--help"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


for script in ["pw-guards", "pw-doctor", "pw-setup"]:
    check(f"{script} --help exits 0", lambda s=script: _script_runs(s))

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL BARE-INSTALL CHECKS PASSED")
