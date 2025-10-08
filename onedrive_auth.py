"""Placeholder OneDrive auth module while integration is disabled."""
from __future__ import annotations


def get_access_token() -> str:
    """Raise an informative error while OneDrive integration is disabled."""

    raise RuntimeError("OneDrive authentication is disabled in this release.")
