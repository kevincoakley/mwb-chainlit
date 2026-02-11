"""Tests for the Chainlit app helpers."""

from __future__ import annotations

import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app import (
    DATATABLE_CACHE,
    create_clustered_heatmap_analysis,
    build_agent_messages,
    create_volcano_plot_analysis,
    env_var_enabled,
    extract_first_analysis_id,
    extract_agent_reply,
    extract_llm_response_log,
    extract_tool_call_logs,
    get_analysis_datatable,
    format_study_summary,
    get_study_analysis_information,
    get_study_summary,
)


def test_get_study_summary_uses_mwb_api(monkeypatch) -> None:
    payload = {"study_id": "ST000001", "title": "Example"}

    def _fake_get_study_summary(study_id: str = "ST") -> dict[str, str]:
        assert study_id == "ST000001"
        return payload

    monkeypatch.setattr("app.mwb_get_study_summary", _fake_get_study_summary)

    result = get_study_summary.invoke({"study_id": "ST000001"})

    assert result == payload


def test_get_study_analysis_information_uses_mwb_api(monkeypatch) -> None:
    payload = {"study_id": "ST000001", "analysis_count": 3}

    def _fake_get_study_analysis_information(study_id: str = "ST") -> dict[str, int]:
        assert study_id == "ST000001"
        return payload

    monkeypatch.setattr(
        "app.mwb_get_study_analysis_information",
        _fake_get_study_analysis_information,
    )

    result = get_study_analysis_information.invoke({"study_id": "ST000001"})

    assert result == payload


def test_extract_first_analysis_id_from_nested_payload() -> None:
    payload = {
        "study_id": "ST000001",
        "results": [{"analysis_id": "AN000001"}, {"analysis_id": "AN000002"}],
    }
    assert extract_first_analysis_id(payload) == "AN000001"


def test_get_analysis_datatable_returns_ref(monkeypatch) -> None:
    datatable = pd.DataFrame(
        {
            "Samples": ["S1", "S2"],
            "Class": ["Control", "Case"],
            "met_1": [1.0, 2.0],
        }
    )

    DATATABLE_CACHE.clear()
    monkeypatch.setattr(
        "app.mwb_get_analysis_datatable", lambda analysis_id="AN": datatable
    )

    result = get_analysis_datatable.invoke({"analysis_id": "AN000001"})

    assert result["analysis_id"] == "AN000001"
    assert result["rows"] == 2
    assert result["columns"] == 3
    assert result["datatable_ref"].startswith("dt_")
    assert result["datatable_ref"] in DATATABLE_CACHE


def test_create_volcano_plot_analysis_uses_datatable_ref(monkeypatch) -> None:
    datatable = pd.DataFrame(
        {
            "Samples": ["S1", "S2"],
            "Class": ["Control", "Case"],
            "met_1": [1.0, 2.0],
        }
    )
    DATATABLE_CACHE.clear()
    DATATABLE_CACHE["dt_test"] = {
        "study_id": "ST000001",
        "analysis_id": "AN000001",
        "dataframe": datatable,
    }

    def _fake_run_volcano_plot_analysis(
        study_id: str, analysis_id: str, df: pd.DataFrame
    ) -> dict[str, str]:
        assert study_id == "ST000001"
        assert analysis_id == "AN000001"
        assert not df.empty
        return {"png_path": "/tmp/volcano.png", "title": "Volcano Plot"}

    monkeypatch.setattr(
        "app.run_volcano_plot_analysis", _fake_run_volcano_plot_analysis
    )

    result = create_volcano_plot_analysis.invoke(
        {
            "study_id": "ST000001",
            "analysis_id": "AN000001",
            "datatable_ref": "dt_test",
        }
    )

    assert result["study_id"] == "ST000001"
    assert result["analysis_id"] == "AN000001"
    assert result["datatable_ref"] == "dt_test"
    assert result["png_path"] == "/tmp/volcano.png"


def test_create_volcano_plot_analysis_errors_when_ref_missing() -> None:
    DATATABLE_CACHE.clear()
    result = create_volcano_plot_analysis.invoke(
        {
            "study_id": "ST000001",
            "analysis_id": "AN000001",
            "datatable_ref": "missing",
        }
    )

    assert "error" in result
    assert "Unknown datatable_ref" in result["error"]


def test_create_clustered_heatmap_analysis_uses_datatable_ref(monkeypatch) -> None:
    datatable = pd.DataFrame(
        {
            "Samples": ["S1", "S2"],
            "Class": ["Control", "Case"],
            "met_1": [1.0, 2.0],
        }
    )
    DATATABLE_CACHE.clear()
    DATATABLE_CACHE["dt_heatmap"] = {
        "study_id": "ST000001",
        "analysis_id": "AN000001",
        "dataframe": datatable,
    }

    def _fake_run_clustered_heatmap_analysis(
        study_id: str, analysis_id: str, df: pd.DataFrame
    ) -> dict[str, str]:
        assert study_id == "ST000001"
        assert analysis_id == "AN000001"
        assert not df.empty
        return {"png_path": "/tmp/clustered_heatmap.png", "title": "Clustered Heatmap"}

    monkeypatch.setattr(
        "app.run_clustered_heatmap_analysis", _fake_run_clustered_heatmap_analysis
    )

    result = create_clustered_heatmap_analysis.invoke(
        {
            "study_id": "ST000001",
            "analysis_id": "AN000001",
            "datatable_ref": "dt_heatmap",
        }
    )

    assert result["study_id"] == "ST000001"
    assert result["analysis_id"] == "AN000001"
    assert result["datatable_ref"] == "dt_heatmap"
    assert result["png_path"] == "/tmp/clustered_heatmap.png"


def test_format_study_summary_outputs_key_fields() -> None:
    summary = {
        "study_id": "ST000001",
        "study_title": "FatBIE",
        "species": "Arabidopsis thaliana",
        "institute": "UC Davis",
    }

    formatted = format_study_summary(summary)

    assert "Study ID: ST000001" in formatted
    assert "Title: FatBIE" in formatted


def test_extract_agent_reply_uses_last_ai_message() -> None:
    result = {
        "messages": [
            HumanMessage(content="Hi"),
            AIMessage(content="First"),
            AIMessage(content="Second"),
        ]
    }

    assert extract_agent_reply(result) == "Second"


def test_build_agent_messages_uses_chat_history_and_avoids_duplicates() -> None:
    history = [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "First answer"},
        {"role": "user", "content": "Second question"},
    ]

    result = build_agent_messages(history, "Second question")

    assert result == [
        ("user", "First question"),
        ("assistant", "First answer"),
        ("user", "Second question"),
    ]


def test_build_agent_messages_appends_latest_user_message_when_missing() -> None:
    history = [{"role": "assistant", "content": "How can I help?"}]

    result = build_agent_messages(history, "Run analysis for ST000001")

    assert result == [
        ("assistant", "How can I help?"),
        ("user", "Run analysis for ST000001"),
    ]


def test_build_agent_messages_ignores_non_user_assistant_entries() -> None:
    history = [
        {"role": "system", "content": "internal"},
        {"role": "user", "content": "  "},
        {"role": "assistant", "content": "Valid response"},
    ]

    result = build_agent_messages(history, "Next question")

    assert result == [
        ("assistant", "Valid response"),
        ("user", "Next question"),
    ]


def test_env_var_enabled_truthy_and_falsy(monkeypatch) -> None:
    monkeypatch.setenv("VERBOSE_UI_LOGGING", "true")
    assert env_var_enabled("VERBOSE_UI_LOGGING") is True

    monkeypatch.setenv("VERBOSE_UI_LOGGING", "0")
    assert env_var_enabled("VERBOSE_UI_LOGGING") is False


def test_extract_tool_call_logs_reads_tool_messages() -> None:
    result = {
        "messages": [
            HumanMessage(content="summarize ST000001"),
            ToolMessage(
                content='{"study_id":"ST000001"}',
                tool_call_id="call_1",
                name="get_study_summary",
            ),
        ]
    }

    logs = extract_tool_call_logs(result)

    assert logs == [
        {"tool_name": "get_study_summary", "content": {"study_id": "ST000001"}}
    ]


def test_extract_llm_response_log_includes_reasoning() -> None:
    result = {
        "messages": [
            AIMessage(
                content="Done",
                additional_kwargs={"reasoning": "Used study summary tool first."},
                tool_calls=[{"id": "call_1", "name": "get_study_summary", "args": {}}],
            )
        ]
    }

    log = extract_llm_response_log(result)

    assert log["content"] == "Done"
    assert log["reasoning"] == "Used study summary tool first."
    assert isinstance(log["tool_calls"], list)
    assert log["tool_calls"][0]["name"] == "get_study_summary"
