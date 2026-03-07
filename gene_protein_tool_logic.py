"""Gene and Protein context tool logic for Metabolomics Workbench."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def get_gene_info_result(
    input_item: str,
    input_value: str,
    output_item: str,
    fetch_gene_info: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return gene info payload."""
    log(
        "tool_called",
        {
            "tool_name": "get_gene_info",
            "input_item": input_item,
            "input_value": input_value,
            "output_item": output_item,
        },
    )
    result = fetch_gene_info(
        input_item=input_item, input_value=input_value, output_item=output_item
    )
    log("tool_result", {"tool_name": "get_gene_info", "result": result})
    return result


def get_protein_info_result(
    input_item: str,
    input_value: str,
    output_item: str,
    fetch_protein_info: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return protein info payload."""
    log(
        "tool_called",
        {
            "tool_name": "get_protein_info",
            "input_item": input_item,
            "input_value": input_value,
            "output_item": output_item,
        },
    )
    result = fetch_protein_info(
        input_item=input_item, input_value=input_value, output_item=output_item
    )
    log("tool_result", {"tool_name": "get_protein_info", "result": result})
    return result
