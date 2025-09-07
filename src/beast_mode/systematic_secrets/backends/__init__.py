"""Backend adapters for systematic secrets management."""

from .base import SecretBackend
from .local_adapter import LocalAdapter

__all__ = [
    "SecretBackend",
    "LocalAdapter",
]