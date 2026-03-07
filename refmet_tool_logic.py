"""RefMet context tool logic for Metabolomics Workbench."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Optional


def get_refmet_info_result(
    input_item: str,
    input_value: Optional[str],
    output_item: str,
    fetch_refmet_info: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return RefMet info payload."""
    log(
        "tool_called",
        {
            "tool_name": "get_refmet_info",
            "input_item": input_item,
            "input_value": input_value,
            "output_item": output_item,
        },
    )
    result = fetch_refmet_info(
        input_item=input_item, input_value=input_value, output_item=output_item
    )
    log("tool_result", {"tool_name": "get_refmet_info", "result": result})
    return result
