"""Helpers for caching analysis datatables by generated references."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pandas as pd


def cache_datatable(
    cache: dict[str, dict[str, Any]], analysis_id: str, datatable: pd.DataFrame
) -> str:
    """Store a datatable and return a reference for later tool calls."""
    datatable_ref = f"dt_{uuid4().hex}"
    cache[datatable_ref] = {
        "analysis_id": analysis_id,
        "dataframe": datatable,
    }
    return datatable_ref


def get_cached_datatable(
    cache: dict[str, dict[str, Any]], datatable_ref: str
) -> pd.DataFrame | None:
    """Return a cached datatable from a reference."""
    item = cache.get(datatable_ref)
    if not item:
        return None
    dataframe = item.get("dataframe")
    return dataframe if isinstance(dataframe, pd.DataFrame) else None
