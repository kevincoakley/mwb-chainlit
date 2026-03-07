"""Study context tool logic for Metabolomics Workbench."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd


def _generic_tool_result(
    tool_name: str,
    fetch_func: Callable[..., Any],
    log: Callable[[str, Any], None],
    **kwargs: Any,
) -> Any:
    """Helper to execute a tool function with standard logging."""
    log("tool_called", {"tool_name": tool_name, **kwargs})
    result = fetch_func(**kwargs)
    log("tool_result", {"tool_name": tool_name, "result": result})
    return result


def get_study_summary_result(
    study_id: str,
    fetch_study_summary: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return study summary payload."""
    return _generic_tool_result("get_study_summary", fetch_study_summary, log, study_id=study_id)


def get_study_analysis_information_result(
    study_id: str,
    fetch_study_analysis_information: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return study analysis payload."""
    return _generic_tool_result(
        "get_study_analysis_information",
        fetch_study_analysis_information,
        log,
        study_id=study_id,
    )


def get_study_factors_result(
    study_id: str,
    fetch_study_factors: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return study factors payload."""
    return _generic_tool_result("get_study_factors", fetch_study_factors, log, study_id=study_id)


def get_study_metabolites_result(
    study_id: str,
    fetch_study_metabolites: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return study metabolites payload."""
    return _generic_tool_result(
        "get_study_metabolites", fetch_study_metabolites, log, study_id=study_id
    )


def get_study_data_result(
    study_id: str,
    fetch_study_data: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return study data payload."""
    return _generic_tool_result("get_study_data", fetch_study_data, log, study_id=study_id)


def get_study_mwtab_result(
    analysis_id: str,
    fetch_study_mwtab: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return study mwTab payload."""
    return _generic_tool_result("get_study_mwtab", fetch_study_mwtab, log, analysis_id=analysis_id)


def get_untargeted_studies_result(
    fetch_untargeted_studies: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return untargeted studies list."""
    return _generic_tool_result("get_untargeted_studies", fetch_untargeted_studies, log)


def get_untargeted_data_result(
    analysis_id: str,
    fetch_untargeted_data: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return untargeted data payload."""
    return _generic_tool_result(
        "get_untargeted_data", fetch_untargeted_data, log, analysis_id=analysis_id
    )


def get_untargeted_factors_result(
    analysis_id: str,
    fetch_untargeted_factors: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return untargeted factors payload."""
    return _generic_tool_result(
        "get_untargeted_factors", fetch_untargeted_factors, log, analysis_id=analysis_id
    )


def get_named_metabolite_studies_result(
    fetch_named_metabolite_studies: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return named metabolite studies list."""
    return _generic_tool_result(
        "get_named_metabolite_studies", fetch_named_metabolite_studies, log
    )


def get_number_of_metabolites_result(
    study_id: str,
    fetch_number_of_metabolites: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return number of metabolites for a study."""
    return _generic_tool_result(
        "get_number_of_metabolites", fetch_number_of_metabolites, log, study_id=study_id
    )


def get_metabolite_id_info_result(
    metabolite_id: str,
    fetch_metabolite_id_info: Callable[..., dict[str, Any]],
    log: Callable[[str, Any], None],
) -> dict[str, Any]:
    """Return metabolite ID info payload."""
    return _generic_tool_result(
        "get_metabolite_id_info", fetch_metabolite_id_info, log, metabolite_id=metabolite_id
    )


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
    except Exception as exc:  # pragma: no cover
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
