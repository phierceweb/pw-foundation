"""pw-foundation: the dependency-light foundation.

Structured logging, the exception hierarchy, config and env resolution, console
output, parallel helpers, the ``Service`` base, pure utilities, and the
structural build gate — on python-dotenv, pyyaml, structlog, nanoid and rich.
The LLM / HTTP / database / web layers live in ``pw-core``, which depends on
this package. See ``docs/modules.md`` for the module index.
"""


def __getattr__(name: str) -> str:
    """PEP 562: ``__version__`` reads package metadata on first access, not at import."""
    if name != "__version__":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib.metadata import PackageNotFoundError, version

    try:
        value = version("pw-foundation")
    except PackageNotFoundError:  # running from a source tree with no install
        value = "0.0.0+unknown"
    globals()["__version__"] = value
    return value
