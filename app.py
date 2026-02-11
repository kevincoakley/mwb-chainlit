"""Chainlit app with a LangChain study assistant backed by OpenAI-compatible APIs."""

from __future__ import annotations

import os
from typing import Any

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
    "You are a metabolomics assistant. "
    "Use the available tools for all study questions. "
    "When the user asks for a volcano plot or clustered heatmap, do this sequence: "
    "1) get_study_summary(study_id), "
    "2) get_study_analysis_information(study_id) and extract analysis_id, "
    "3) get_analysis_datatable(analysis_id) to get datatable_ref, "
    "4) call the requested analysis tool with study_id, analysis_id, datatable_ref. "
    "Include study summary details in your final response. "
    "Keep responses concise and grounded in tool output."
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
def get_analysis_datatable(analysis_id: str) -> dict[str, Any]:
    """Get analysis datatable and return a cached reference for downstream tools."""
    return get_analysis_datatable_result(
        analysis_id=analysis_id,
        fetch_analysis_datatable=mwb_get_analysis_datatable,
        cache_datatable=_cache_datatable,
        log=_console_verbose_log,
    )


@tool
def create_volcano_plot_analysis(
    study_id: str, analysis_id: str, datatable_ref: str
) -> dict[str, Any]:
    """
    Create a volcano plot from an already fetched analysis datatable.

    Workflow:
    1) Look up dataframe by datatable_ref.
    2) Run volcano plot analysis to create PNG output.
    """
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
    """
    Create a clustered heatmap from an already fetched analysis datatable.

    Workflow:
    1) Look up dataframe by datatable_ref.
    2) Run clustered heatmap analysis to create PNG output.
    """
    return create_clustered_heatmap_analysis_result(
        study_id=study_id,
        analysis_id=analysis_id,
        datatable_ref=datatable_ref,
        get_cached_datatable=_get_cached_datatable,
        run_clustered_heatmap_analysis=run_clustered_heatmap_analysis,
        log=_console_verbose_log,
    )


def create_langchain_agent() -> Any:
    """Build the LangChain agent with OpenAI-compatible APIs and study tools."""
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
            get_analysis_datatable,
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
            "Study agent is ready. Ask for study summaries, analysis details, "
            "or to create a volcano plot / clustered heatmap (for example: create a clustered heatmap for ST000001)."
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
