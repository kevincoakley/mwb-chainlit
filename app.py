"""Chainlit app with a LangChain study assistant backed by OpenAI-compatible APIs."""

from __future__ import annotations

import os
from typing import Any, Optional

import chainlit as cl
import pandas as pd
from agent_message_utils import build_agent_messages
from agent_message_utils import extract_agent_reply
from agent_message_utils import extract_first_analysis_id
from agent_message_utils import extract_llm_response_log
from agent_message_utils import extract_clustered_heatmap_payload
from agent_message_utils import extract_tool_call_logs
from agent_message_utils import extract_tool_payload
from agent_message_utils import extract_volcano_plot_payload
from datatable_cache import cache_datatable
from datatable_cache import get_cached_datatable
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from mwb_api import get_analysis_datatable as mwb_get_analysis_datatable
from mwb_api import get_study_analysis_information as mwb_get_study_analysis_information
from mwb_api import get_study_summary as mwb_get_study_summary
from mwb_api import get_study_factors as mwb_get_study_factors
from mwb_api import get_study_metabolites as mwb_get_study_metabolites
from mwb_api import get_study_data as mwb_get_study_data
from mwb_api import get_study_mwtab as mwb_get_study_mwtab
from mwb_api import get_untargeted_studies as mwb_get_untargeted_studies
from mwb_api import get_untargeted_data as mwb_get_untargeted_data
from mwb_api import get_untargeted_factors as mwb_get_untargeted_factors
from mwb_api import get_named_metabolite_studies as mwb_get_named_metabolite_studies
from mwb_api import get_number_of_metabolites as mwb_get_number_of_metabolites
from mwb_api import get_metabolite_id_info as mwb_get_metabolite_id_info
from mwb_api import get_compound_info as mwb_get_compound_info
from mwb_api import get_refmet_info as mwb_get_refmet_info
from mwb_api import get_metstat as mwb_get_metstat
from mwb_api import get_gene_info as mwb_get_gene_info
from mwb_api import get_protein_info as mwb_get_protein_info
from mwb_api import search_moverz as mwb_search_moverz
from mwb_api import get_exact_mass as mwb_get_exact_mass

from openai import AsyncOpenAI
from perform_clustered_heatmap_analysis import (
    main as run_clustered_heatmap_analysis,
)
from perform_volcano_plot_analysis import main as run_volcano_plot_analysis
from study_summary_formatter import format_study_summary

from study_tool_logic import create_clustered_heatmap_analysis_result
from study_tool_logic import create_volcano_plot_analysis_result
from study_tool_logic import get_analysis_datatable_result
from study_tool_logic import get_study_analysis_information_result
from study_tool_logic import get_study_summary_result
from study_tool_logic import get_study_factors_result
from study_tool_logic import get_study_metabolites_result
from study_tool_logic import get_study_data_result
from study_tool_logic import get_study_mwtab_result
from study_tool_logic import get_untargeted_studies_result
from study_tool_logic import get_untargeted_data_result
from study_tool_logic import get_untargeted_factors_result
from study_tool_logic import get_named_metabolite_studies_result
from study_tool_logic import get_number_of_metabolites_result
from study_tool_logic import get_metabolite_id_info_result

from compound_tool_logic import get_compound_info_result
from refmet_tool_logic import get_refmet_info_result
from metstat_tool_logic import get_metstat_result
from gene_protein_tool_logic import get_gene_info_result
from gene_protein_tool_logic import get_protein_info_result
from moverz_tool_logic import search_moverz_result
from moverz_tool_logic import get_exact_mass_result

from verbose_logging import emit_ui_verbose_log
from verbose_logging import env_var_enabled
from verbose_logging import console_verbose_log

BASE_URL = os.environ.get("BASE_URL")
API_KEY = os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY")
client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY) if API_KEY else None

MODEL = os.environ.get("MODEL")
settings = {
    "model": MODEL,
}
SYSTEM_PROMPT = (
    "You are a metabolomics assistant with access to the Metabolomics Workbench API. "
    "You MUST use the provided tools to fulfill user requests for analysis and data. "
    "NEVER provide external URLs or links to the Metabolomics Workbench website as a substitute for using a tool. "
    "When asked for a volcano plot or clustered heatmap, you MUST follow this exact sequence: "
    "1) get_study_summary(study_id), "
    "2) get_study_analysis_information(study_id) to extract analysis_id, "
    "3) get_analysis_datatable(analysis_id) to get datatable_ref, "
    "4) call the specific plot tool (create_volcano_plot_analysis or create_clustered_heatmap_analysis). "
    "Include study summary details in your final response. Your goal is to generate the plot within this UI, not to refer the user elsewhere."
)
DATATABLE_CACHE: dict[str, dict[str, Any]] = {}


VERBOSE_UI_LOGGING = env_var_enabled("VERBOSE_UI_LOGGING")


def _console_verbose_log(event: str, payload: Any) -> None:
    """Compatibility wrapper for verbose console logging."""
    console_verbose_log(event=event, payload=payload, enabled=VERBOSE_UI_LOGGING)


async def _emit_ui_verbose_log(event: str, payload: Any) -> None:
    """Compatibility wrapper for verbose UI logging."""
    await emit_ui_verbose_log(event=event, payload=payload, enabled=VERBOSE_UI_LOGGING)


def _cache_datatable(analysis_id: str, datatable: pd.DataFrame) -> str:
    """Compatibility wrapper for datatable cache writes."""
    return cache_datatable(
        cache=DATATABLE_CACHE,
        analysis_id=analysis_id,
        datatable=datatable,
    )


def _get_cached_datatable(datatable_ref: str) -> pd.DataFrame | None:
    """Compatibility wrapper for datatable cache reads."""
    return get_cached_datatable(cache=DATATABLE_CACHE, datatable_ref=datatable_ref)


# --- Study Context Tools ---


@tool
def get_study_summary(study_id: str = "ST") -> dict[str, Any]:
    """Get summary metadata for a Metabolomics Workbench study ID."""
    return get_study_summary_result(
        study_id=study_id,
        fetch_study_summary=mwb_get_study_summary,
        log=_console_verbose_log,
    )


@tool
def get_study_analysis_information(study_id: str = "ST") -> dict[str, Any]:
    """Get analysis metadata for a Metabolomics Workbench study ID."""
    return get_study_analysis_information_result(
        study_id=study_id,
        fetch_study_analysis_information=mwb_get_study_analysis_information,
        log=_console_verbose_log,
    )


@tool
def get_study_factors(study_id: str) -> dict[str, Any]:
    """Get samples and experimental variables (factors) for a study ID."""
    return get_study_factors_result(
        study_id=study_id,
        fetch_study_factors=mwb_get_study_factors,
        log=_console_verbose_log,
    )


@tool
def get_study_metabolites(study_id: str) -> dict[str, Any]:
    """Get metabolites and annotations detected in a study."""
    return get_study_metabolites_result(
        study_id=study_id,
        fetch_study_metabolites=mwb_get_study_metabolites,
        log=_console_verbose_log,
    )


@tool
def get_study_data(study_id: str) -> dict[str, Any]:
    """Get metabolites measurements for a study."""
    return get_study_data_result(
        study_id=study_id,
        fetch_study_data=mwb_get_study_data,
        log=_console_verbose_log,
    )


@tool
def get_study_mwtab(analysis_id: str) -> dict[str, Any]:
    """Get mwTab content for an analysis within a study."""
    return get_study_mwtab_result(
        analysis_id=analysis_id,
        fetch_study_mwtab=mwb_get_study_mwtab,
        log=_console_verbose_log,
    )


@tool
def get_untargeted_studies() -> dict[str, Any]:
    """Get list of studies with untargeted data in NMDR."""
    return get_untargeted_studies_result(
        fetch_untargeted_studies=mwb_get_untargeted_studies,
        log=_console_verbose_log,
    )


@tool
def get_untargeted_data(analysis_id: str) -> dict[str, Any]:
    """Get untargeted data for an analysis within a study."""
    return get_untargeted_data_result(
        analysis_id=analysis_id,
        fetch_untargeted_data=mwb_get_untargeted_data,
        log=_console_verbose_log,
    )


@tool
def get_untargeted_factors(analysis_id: str) -> dict[str, Any]:
    """Get experimental factors for an untargeted data analysis."""
    return get_untargeted_factors_result(
        analysis_id=analysis_id,
        fetch_untargeted_factors=mwb_get_untargeted_factors,
        log=_console_verbose_log,
    )


@tool
def get_named_metabolite_studies() -> dict[str, Any]:
    """Get list of studies with named metabolites in NMDR."""
    return get_named_metabolite_studies_result(
        fetch_named_metabolite_studies=mwb_get_named_metabolite_studies,
        log=_console_verbose_log,
    )


@tool
def get_number_of_metabolites(study_id: str) -> dict[str, Any]:
    """Get number of named metabolites in a study."""
    return get_number_of_metabolites_result(
        study_id=study_id,
        fetch_number_of_metabolites=mwb_get_number_of_metabolites,
        log=_console_verbose_log,
    )


@tool
def get_metabolite_id_info(metabolite_id: str) -> dict[str, Any]:
    """Get metabolite name and RefMet name for a metabolite_id."""
    return get_metabolite_id_info_result(
        metabolite_id=metabolite_id,
        fetch_metabolite_id_info=mwb_get_metabolite_id_info,
        log=_console_verbose_log,
    )


@tool
def get_analysis_datatable(analysis_id: str) -> dict[str, Any]:
    """Get analysis datatable and return a cached reference for downstream tools."""
    return get_analysis_datatable_result(
        analysis_id=analysis_id,
        fetch_analysis_datatable=mwb_get_analysis_datatable,
        cache_datatable=_cache_datatable,
        log=_console_verbose_log,
    )


# --- Compound Context Tools ---


@tool
def get_compound_info(
    input_item: str, input_value: str, output_item: str = "all"
) -> dict[str, Any]:
    """Get compound info by regno, pubchem_cid, inchi_key, formula, etc."""
    return get_compound_info_result(
        input_item=input_item,
        input_value=input_value,
        output_item=output_item,
        fetch_compound_info=mwb_get_compound_info,
        log=_console_verbose_log,
    )


# --- RefMet Context Tools ---


@tool
def get_refmet_info(
    input_item: str, input_value: Optional[str] = None, output_item: str = "all"
) -> dict[str, Any]:
    """Get RefMet info by name, inchi_key, formula, or fetch all/classification."""
    return get_refmet_info_result(
        input_item=input_item,
        input_value=input_value,
        output_item=output_item,
        fetch_refmet_info=mwb_get_refmet_info,
        log=_console_verbose_log,
    )


# --- MetStat Context Tools ---


@tool
def get_metstat(
    analysis_type: str = "",
    polarity: str = "",
    chromatography: str = "",
    species: str = "",
    sample_source: str = "",
    disease: str = "",
    kegg_id: str = "",
    refmet_name: str = "",
) -> dict[str, Any]:
    """Search for studies based on various MetStat criteria."""
    return get_metstat_result(
        fetch_metstat=mwb_get_metstat,
        log=_console_verbose_log,
        analysis_type=analysis_type,
        polarity=polarity,
        chromatography=chromatography,
        species=species,
        sample_source=sample_source,
        disease=disease,
        kegg_id=kegg_id,
        refmet_name=refmet_name,
    )


# --- Gene & Protein Context Tools ---


@tool
def get_gene_info(
    input_item: str, input_value: str, output_item: str = "all"
) -> dict[str, Any]:
    """Get gene info by gene_symbol, gene_id, etc."""
    return get_gene_info_result(
        input_item=input_item,
        input_value=input_value,
        output_item=output_item,
        fetch_gene_info=mwb_get_gene_info,
        log=_console_verbose_log,
    )


@tool
def get_protein_info(
    input_item: str, input_value: str, output_item: str = "all"
) -> dict[str, Any]:
    """Get protein info by uniprot_id, gene_id, etc."""
    return get_protein_info_result(
        input_item=input_item,
        input_value=input_value,
        output_item=output_item,
        fetch_protein_info=mwb_get_protein_info,
        log=_console_verbose_log,
    )


# --- Moverz Context Tools ---


@tool
def search_moverz(context: str, mz: float, adduct: str, tolerance: float) -> dict[str, Any]:
    """Perform MS precursor ion search on MB, LIPIDS, or REFMET databases."""
    return search_moverz_result(
        context=context,
        mz=mz,
        adduct=adduct,
        tolerance=tolerance,
        fetch_moverz=mwb_search_moverz,
        log=_console_verbose_log,
    )


@tool
def get_exact_mass(lipid_abbreviation: str, adduct: str) -> dict[str, Any]:
    """Calculate the exact mass (m/z) of an ion for a lipid abbreviation."""
    return get_exact_mass_result(
        lipid_abbreviation=lipid_abbreviation,
        adduct=adduct,
        fetch_exact_mass=mwb_get_exact_mass,
        log=_console_verbose_log,
    )


# --- Plotting Tools ---


@tool
def create_volcano_plot_analysis(
    study_id: str, analysis_id: str, datatable_ref: str
) -> dict[str, Any]:
    """Create a volcano plot from an already fetched analysis datatable."""
    return create_volcano_plot_analysis_result(
        study_id=study_id,
        analysis_id=analysis_id,
        datatable_ref=datatable_ref,
        get_cached_datatable=_get_cached_datatable,
        run_volcano_plot_analysis=run_volcano_plot_analysis,
        log=_console_verbose_log,
    )


@tool
def create_clustered_heatmap_analysis(
    study_id: str, analysis_id: str, datatable_ref: str
) -> dict[str, Any]:
    """Create a clustered heatmap from an already fetched analysis datatable."""
    return create_clustered_heatmap_analysis_result(
        study_id=study_id,
        analysis_id=analysis_id,
        datatable_ref=datatable_ref,
        get_cached_datatable=_get_cached_datatable,
        run_clustered_heatmap_analysis=run_clustered_heatmap_analysis,
        log=_console_verbose_log,
    )


def create_langchain_agent() -> Any:
    """Build the LangChain agent with OpenAI-compatible APIs and all tools."""
    if not settings["model"]:
        raise ValueError("MODEL environment variable is required.")
    if not API_KEY:
        raise ValueError(
            "API_KEY environment variable is required (or set OPENAI_API_KEY)."
        )

    async_client = client or AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)

    llm = ChatOpenAI(
        model=settings["model"],
        openai_api_key=API_KEY,
        openai_api_base=BASE_URL,
        root_async_client=async_client,
        temperature=0,
    )
    return create_agent(
        model=llm,
        tools=[
            get_study_summary,
            get_study_analysis_information,
            get_study_factors,
            get_study_metabolites,
            get_study_data,
            get_study_mwtab,
            get_untargeted_studies,
            get_untargeted_data,
            get_untargeted_factors,
            get_named_metabolite_studies,
            get_number_of_metabolites,
            get_metabolite_id_info,
            get_analysis_datatable,
            get_compound_info,
            get_refmet_info,
            get_metstat,
            get_gene_info,
            get_protein_info,
            search_moverz,
            get_exact_mass,
            create_volcano_plot_analysis,
            create_clustered_heatmap_analysis,
        ],
        system_prompt=SYSTEM_PROMPT,
    )


@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialize and store the agent for the user session."""
    cl.chat_context.clear()
    cl.user_session.set("agent", create_langchain_agent())
    await cl.Message(
        content=(
            "Study agent is ready. You can ask about study summaries, analysis details, "
            "metabolites, compounds, genes, proteins, or create plots."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Run the study agent for each incoming user message."""
    agent = cl.user_session.get("agent")
    if agent is None:
        agent = create_langchain_agent()
        cl.user_session.set("agent", agent)

    messages = build_agent_messages(
        chat_history=cl.chat_context.to_openai(),
        latest_user_message=message.content,
    )
    await _emit_ui_verbose_log(
        "llm_request",
        {
            "system_prompt": SYSTEM_PROMPT,
            "messages": messages,
        },
    )

    result = await agent.ainvoke({"messages": messages})
    await _emit_ui_verbose_log("tool_calls", extract_tool_call_logs(result))
    await _emit_ui_verbose_log("llm_response", extract_llm_response_log(result))
    reply_text = extract_agent_reply(result)
    volcano_payload = extract_volcano_plot_payload(result)
    clustered_heatmap_payload = extract_clustered_heatmap_payload(result)
    plot_payload = clustered_heatmap_payload or volcano_payload
    if plot_payload is None:
        await cl.Message(content=reply_text).send()
        return

    if "error" in plot_payload:
        summary_text = format_study_summary(
            extract_tool_payload(result, "get_study_summary")
        )
        content = f"{reply_text}\n\nPlot generation failed: {plot_payload['error']}"
        if summary_text:
            content = f"{content}\n\nStudy Summary:\n{summary_text}"
        await cl.Message(content=content).send()
        return

    png_path = plot_payload.get("png_path")
    summary_text = format_study_summary(
        extract_tool_payload(result, "get_study_summary")
    )
    content = reply_text
    if summary_text:
        content = f"{content}\n\nStudy Summary:\n{summary_text}"

    if isinstance(png_path, str) and os.path.exists(png_path):
        image = cl.Image(
            name=os.path.basename(png_path),
            path=png_path,
            display="inline",
        )
        await cl.Message(content=content, elements=[image]).send()
        return

    await cl.Message(content=content).send()
