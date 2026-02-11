"""Verbose logging helpers shared by the Chainlit app."""

from __future__ import annotations

import json
import os
from typing import Any

import chainlit as cl


def env_var_enabled(name: str) -> bool:
    """Return True when an environment variable is set to a truthy value."""
    value = os.environ.get(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _serialize_for_log(payload: Any) -> str:
    """Serialize payload for debug logging with safe fallback conversion."""
    try:
        return json.dumps(payload, indent=2, default=str)
    except TypeError:
        return str(payload)


def console_verbose_log(event: str, payload: Any, enabled: bool) -> None:
    """Write verbose diagnostics to console when enabled."""
    if not enabled:
        return
    print(
        f"[VERBOSE_UI_LOGGING] {event}\n{_serialize_for_log(payload)}",
        flush=True,
    )


async def emit_ui_verbose_log(event: str, payload: Any, enabled: bool) -> None:
    """Emit verbose diagnostics to Chainlit UI and mirror to console."""
    console_verbose_log(event, payload, enabled)
    if not enabled:
        return
    await cl.Message(
        author="debug",
        content=f"**Verbose log: {event}**\n```json\n{_serialize_for_log(payload)}\n```",
    ).send()
