"""MetStat context tool logic for Metabolomics Workbench."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def get_metstat_result(
    fetch_metstat: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
    **kwargs: Any,
) -> dict[str, Any]:
    """Return MetStat search payload."""
    log("tool_called", {"tool_name": "get_metstat", **kwargs})
    result = fetch_metstat(**kwargs)
    log("tool_result", {"tool_name": "get_metstat", "result": result})
    return result
