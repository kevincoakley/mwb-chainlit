"""Formatting helpers for user-facing study summary content."""

from __future__ import annotations

from typing import Any

SUMMARY_LABELS = [
    ("study_id", "Study ID"),
    ("study_title", "Title"),
    ("species", "Species"),
    ("institute", "Institute"),
    ("analysis_type", "Analysis Type"),
    ("number_of_samples", "Number of Samples"),
]


def format_study_summary(study_summary: Any) -> str:
    """Format study summary payload into short user-facing text."""
    if not isinstance(study_summary, dict):
        return ""

    lines = []
    for key, label in SUMMARY_LABELS:
        value = study_summary.get(key)
        if value is not None and str(value).strip():
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)
