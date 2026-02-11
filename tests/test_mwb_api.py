"""Tests for mwb_api helpers."""

from __future__ import annotations

import pandas as pd
import requests

from mwb_api import get_analysis_datatable


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


def test_get_analysis_datatable_parses_tsv_response(monkeypatch) -> None:
    tsv = "analysis_id\tmetabolite\tvalue\nAN000001\tGlucose\t1.5\nAN000001\tLactate\t2.1\n"

    def _fake_get(url: str) -> _FakeResponse:
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


def test_get_analysis_datatable_wraps_request_error(monkeypatch) -> None:
    def _fake_get(_url: str) -> _FakeResponse:
        raise requests.exceptions.RequestException("network down")

    monkeypatch.setattr("mwb_api.requests.get", _fake_get)

    result = get_analysis_datatable("AN000001")

    assert isinstance(result, pd.DataFrame)
    assert "API request failed" in result.loc[0, "error"]
