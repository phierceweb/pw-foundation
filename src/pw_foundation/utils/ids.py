"""URL-safe nanoid generation.

Usage::

    from pw_foundation.utils.ids import generate_id

    new_id = generate_id()            # "V1StGXR8_Z5j"
    new_id = generate_id(size=8)      # "k3J9xQ2m"

Collision-safe allocation against a database table is ``pw_core.db.ids.allocate_id``.
"""

from __future__ import annotations

from nanoid import generate

# URL-safe alphabet: alphanumeric + underscore + hyphen
_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-"

_DEFAULT_SIZE = 12


def generate_id(*, size: int | None = None) -> str:
    """Generate a URL-safe nanoid string.

    Args:
        size: Character length. Defaults to the ``ID_LENGTH`` environment
            variable (clamped to 8–36), or 12 if it is unset.

    Returns:
        A random URL-safe string.
    """
    length = size if size is not None else _default_size()
    return generate(_ALPHABET, length)


def _default_size() -> int:
    """Read the ``ID_LENGTH`` env var (clamped to 8–36), else fall back to 12."""
    try:
        import os

        val = os.environ.get("ID_LENGTH", "")
        if val.strip():
            n = int(val)
            return max(8, min(36, n))
    except (ValueError, TypeError):
        pass
    return _DEFAULT_SIZE


__all__ = ["generate_id"]
