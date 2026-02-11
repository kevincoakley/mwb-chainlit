"""Pure workflow helpers used by Chainlit tool entrypoints."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd


def get_study_summary_result(
    study_id: str,
    fetch_study_summary: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return study summary payload with standard tool logging."""
    log("tool_called", {"tool_name": "get_study_summary", "study_id": study_id})
    result = fetch_study_summary(study_id=study_id)
    log("tool_result", {"tool_name": "get_study_summary", "result": result})
    return result


def get_study_analysis_information_result(
    study_id: str,
    fetch_study_analysis_information: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return study analysis payload with standard tool logging."""
    log(
        "tool_called",
        {"tool_name": "get_study_analysis_information", "study_id": study_id},
    )
    result = fetch_study_analysis_information(study_id=study_id)
    log(
        "tool_result",
        {"tool_name": "get_study_analysis_information", "result": result},
    )
    return result


def get_analysis_datatable_result(
    analysis_id: str,
    fetch_analysis_datatable: Callable[..., pd.DataFrame],
    cache_datatable: Callable[[str, pd.DataFrame], str],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return a cached datatable reference or a structured error payload."""
    normalized_analysis_id = analysis_id.strip()
    log(
        "tool_called",
        {"tool_name": "get_analysis_datatable", "analysis_id": normalized_analysis_id},
    )
    if not normalized_analysis_id:
        return {"error": "Please provide a valid analysis_id."}

    datatable = fetch_analysis_datatable(analysis_id=normalized_analysis_id)
    if datatable.empty:
        return {
            "error": f"No datatable rows returned for analysis {normalized_analysis_id}.",
            "analysis_id": normalized_analysis_id,
        }
    if "error" in datatable.columns:
        return {
            "error": str(
                datatable.iloc[0].get("error", "Failed to retrieve analysis datatable.")
            ),
            "analysis_id": normalized_analysis_id,
        }

    datatable_ref = cache_datatable(
        analysis_id=normalized_analysis_id,
        datatable=datatable,
    )
    result = {
        "analysis_id": normalized_analysis_id,
        "datatable_ref": datatable_ref,
        "rows": int(datatable.shape[0]),
        "columns": int(datatable.shape[1]),
    }
    log("tool_result", {"tool_name": "get_analysis_datatable", "result": result})
    return result


def create_volcano_plot_analysis_result(
    study_id: str,
    analysis_id: str,
    datatable_ref: str,
    get_cached_datatable: Callable[[str], pd.DataFrame | None],
    run_volcano_plot_analysis: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Create a volcano plot output payload from a cached datatable reference."""
    return _create_plot_analysis_result(
        tool_name="create_volcano_plot_analysis",
        analysis_error_label="Volcano plot",
        study_id=study_id,
        analysis_id=analysis_id,
        datatable_ref=datatable_ref,
        get_cached_datatable=get_cached_datatable,
        run_plot_analysis=run_volcano_plot_analysis,
        log=log,
    )


def create_clustered_heatmap_analysis_result(
    study_id: str,
    analysis_id: str,
    datatable_ref: str,
    get_cached_datatable: Callable[[str], pd.DataFrame | None],
    run_clustered_heatmap_analysis: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Create a clustered heatmap payload from a cached datatable reference."""
    return _create_plot_analysis_result(
        tool_name="create_clustered_heatmap_analysis",
        analysis_error_label="Clustered heatmap",
        study_id=study_id,
        analysis_id=analysis_id,
        datatable_ref=datatable_ref,
        get_cached_datatable=get_cached_datatable,
        run_plot_analysis=run_clustered_heatmap_analysis,
        log=log,
    )


def _create_plot_analysis_result(
    tool_name: str,
    analysis_error_label: str,
    study_id: str,
    analysis_id: str,
    datatable_ref: str,
    get_cached_datatable: Callable[[str], pd.DataFrame | None],
    run_plot_analysis: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Create a generic plot payload from a cached datatable reference."""
    normalized_study_id = study_id.strip()
    normalized_analysis_id = analysis_id.strip()
    normalized_ref = datatable_ref.strip()
    log(
        "tool_called",
        {
            "tool_name": tool_name,
            "study_id": normalized_study_id,
            "analysis_id": normalized_analysis_id,
            "datatable_ref": normalized_ref,
        },
    )
    if not normalized_study_id:
        return {"error": "Please provide a valid study_id."}
    if not normalized_analysis_id:
        return {
            "error": "Please provide a valid analysis_id.",
            "study_id": normalized_study_id,
        }
    if not normalized_ref:
        return {
            "error": "Please provide a valid datatable_ref from get_analysis_datatable.",
            "study_id": normalized_study_id,
            "analysis_id": normalized_analysis_id,
        }
    datatable_df = get_cached_datatable(normalized_ref)
    if datatable_df is None:
        return {
            "error": f"Unknown datatable_ref '{normalized_ref}'. Run get_analysis_datatable first.",
            "study_id": normalized_study_id,
            "analysis_id": normalized_analysis_id,
        }
    try:
        plot_output = run_plot_analysis(
            study_id=normalized_study_id,
            analysis_id=normalized_analysis_id,
            df=datatable_df,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            "error": f"{analysis_error_label} generation failed: {exc}",
            "study_id": normalized_study_id,
            "analysis_id": normalized_analysis_id,
        }

    result = {
        "study_id": normalized_study_id,
        "analysis_id": normalized_analysis_id,
        "datatable_ref": normalized_ref,
        "png_path": plot_output["png_path"],
        "title": plot_output["title"],
    }
    log("tool_result", {"tool_name": tool_name, "result": result})
    return result
