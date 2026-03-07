"""Tests for mwb_api helpers."""

from __future__ import annotations

import pandas as pd
import requests

from mwb_api import get_analysis_datatable, get_study_summary, get_compound_info


class _FakeResponse:
    def __init__(self, data: str | dict, is_json: bool = False) -> None:
        self.text = data if isinstance(data, str) else ""
        self.data = data if isinstance(data, dict) else None
        self.is_json = is_json

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        if self.is_json:
            return self.data
        raise ValueError("Not JSON")


def test_get_analysis_datatable_parses_tsv_response(monkeypatch) -> None:
    tsv = "analysis_id\tmetabolite\tvalue\nAN000001\tGlucose\t1.5\nAN000001\tLactate\t2.1\n"

    def _fake_get(url: str, params=None) -> _FakeResponse:
        assert (
            url
            == "https://www.metabolomicsworkbench.org/rest/study/analysis_id/AN000001/datatable"
        )
        return _FakeResponse(tsv)

    monkeypatch.setattr("mwb_api.requests.get", _fake_get)

    result = get_analysis_datatable("AN000001")

    assert isinstance(result, pd.DataFrame)
    assert list(result["analysis_id"]) == ["AN000001", "AN000001"]
    assert list(result["metabolite"]) == ["Glucose", "Lactate"]


def test_get_study_summary_returns_json(monkeypatch) -> None:
    expected = {"study_id": "ST000001", "summary": "test summary"}

    def _fake_get(url: str, params=None) -> _FakeResponse:
        assert (
            url
            == "https://www.metabolomicsworkbench.org/rest/study/study_id/ST000001/summary"
        )
        return _FakeResponse(expected, is_json=True)

    monkeypatch.setattr("mwb_api.requests.get", _fake_get)

    result = get_study_summary("ST000001")
    assert result == expected


def test_get_compound_info_returns_json(monkeypatch) -> None:
    expected = {"name": "Glucose", "pubchem_cid": "5793"}

    def _fake_get(url: str, params=None) -> _FakeResponse:
        assert (
            url
            == "https://www.metabolomicsworkbench.org/rest/compound/pubchem_cid/5793/all"
        )
        return _FakeResponse(expected, is_json=True)

    monkeypatch.setattr("mwb_api.requests.get", _fake_get)

    result = get_compound_info("pubchem_cid", "5793")
    assert result == expected


def test_get_analysis_datatable_wraps_request_error(monkeypatch) -> None:
    def _fake_get(_url: str) -> _FakeResponse:
        raise requests.exceptions.RequestException("network down")

    monkeypatch.setattr("mwb_api.requests.get", _fake_get)

    result = get_analysis_datatable("AN000001")

    assert isinstance(result, pd.DataFrame)
    assert "API request failed" in result.loc[0, "error"]
