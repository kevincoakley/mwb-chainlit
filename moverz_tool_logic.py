"""Moverz context tool logic for Metabolomics Workbench."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def search_moverz_result(
    context: str,
    mz: float,
    adduct: str,
    tolerance: float,
    fetch_moverz: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return moverz search payload."""
    log(
        "tool_called",
        {
            "tool_name": "search_moverz",
            "context": context,
            "mz": mz,
            "adduct": adduct,
            "tolerance": tolerance,
        },
    )
    result = fetch_moverz(context=context, mz=mz, adduct=adduct, tolerance=tolerance)
    log("tool_result", {"tool_name": "search_moverz", "result": result})
    return result


def get_exact_mass_result(
    lipid_abbreviation: str,
    adduct: str,
    fetch_exact_mass: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return exact mass payload."""
    log(
        "tool_called",
        {
            "tool_name": "get_exact_mass",
            "lipid_abbreviation": lipid_abbreviation,
            "adduct": adduct,
        },
    )
    result = fetch_exact_mass(lipid_abbreviation=lipid_abbreviation, adduct=adduct)
    log("tool_result", {"tool_name": "get_exact_mass", "result": result})
    return result
