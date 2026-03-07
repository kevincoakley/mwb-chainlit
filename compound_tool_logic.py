"""Compound context tool logic for Metabolomics Workbench."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def get_compound_info_result(
    input_item: str,
    input_value: str,
    output_item: str,
    fetch_compound_info: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return compound info payload."""
    log(
        "tool_called",
        {
            "tool_name": "get_compound_info",
            "input_item": input_item,
            "input_value": input_value,
            "output_item": output_item,
        },
    )
    result = fetch_compound_info(
        input_item=input_item, input_value=input_value, output_item=output_item
    )
    log("tool_result", {"tool_name": "get_compound_info", "result": result})
    return result
