"""pw-core's optional hooks, found without importing anything that is not there."""

from __future__ import annotations

import importlib
import importlib.util
from types import ModuleType

from pw_foundation.exceptions import ConfigurationError


def optional_module(name: str) -> ModuleType | None:
    """Import ``name`` (``package.module``) when its package is installed; ``None`` when it is not.

    An absent package, or a bare directory on ``sys.path`` without ``__init__.py``, counts as not
    installed. A package that is installed but lacks the module, or whose module fails to import,
    is a ``ConfigurationError``: the install is broken or predates the hook.
    """
    package = name.split(".")[0]
    try:
        parent = importlib.util.find_spec(package)
    except (ImportError, ValueError):
        return None
    if parent is None or parent.origin is None:
        return None
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError) as e:
        raise ConfigurationError(f"{package} is installed but {name} cannot be located: {e}") from e
    if spec is None:
        raise ConfigurationError(
            f"{package} is installed but has no {name} module — a version that predates it?"
        )
    try:
        return importlib.import_module(name)
    except Exception as e:
        raise ConfigurationError(f"{name} failed to import: {type(e).__name__}: {e}") from e
