#!/usr/bin/env python3
"""Clustered heatmap analysis for Metabolomics Workbench analysis datatables."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from typing import Optional
from typing import Tuple

import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt


def normalize_data(df: pd.DataFrame, method: str = "ZScore") -> pd.DataFrame:
    """Center by mean and scale by the requested method."""
    normalized_method = (method or "ZScore").strip().lower()
    if normalized_method == "none":
        return df

    centered = df - df.mean()

    if normalized_method == "median":
        denominator = df.median().replace(0, np.nan)
        return centered.div(denominator, axis=1)
    if normalized_method in {"auto", "zscore"}:
        denominator = df.std().replace(0, np.nan)
        return centered.div(denominator, axis=1)
    if normalized_method == "pareto":
        denominator = np.sqrt(df.std()).replace(0, np.nan)
        return centered.div(denominator, axis=1)
    if normalized_method == "range":
        denominator = (df.max() - df.min()).replace(0, np.nan)
        return centered.div(denominator, axis=1)

    raise ValueError(f"Unknown scaling/normalization method: {method}")


def generate_clustered_heatmap_data(
    input_df: pd.DataFrame,
    scaling: str = "ZScore",
    class_col: Optional[str] = "Class",
    class_num_col: str = "ClassNum",
) -> Tuple[pd.DataFrame, pd.Series]:
    """Prepare normalized feature matrix and row colors based on ClassNum."""
    df = input_df.copy()

    if class_col is not None and class_col in df.columns:
        df = df.drop(columns=[class_col])

    if class_num_col not in df.columns:
        raise KeyError(f"Expected '{class_num_col}' column in the analysis dataframe.")

    class_nums = df[class_num_col]
    features_df = df.drop(columns=[class_num_col])
    for column in features_df.columns:
        features_df[column] = pd.to_numeric(features_df[column], errors="coerce")

    unique_class_nums = pd.unique(class_nums)
    palette = sns.color_palette("hls", len(unique_class_nums))
    class_colors_map = {
        class_num: palette[i] for i, class_num in enumerate(unique_class_nums)
    }
    row_colors = class_nums.map(class_colors_map)

    normalized = normalize_data(features_df, method=scaling)
    return normalized, row_colors


def draw_and_save_clustered_heatmap(
    normalized_features_df: pd.DataFrame,
    *,
    method: str = "average",
    metric: str = "correlation",
    row_cluster: bool = True,
    col_cluster: bool = True,
    cmap: str = "inferno",
    row_colors: Optional[pd.Series] = None,
    width: float = 9.0,
    height: float = 9.0,
    out_png: str = "clustered_heatmap.png",
    dpi: int = 300,
    title: str | None = None,
) -> None:
    """Draw seaborn clustermap and save as PNG."""
    plt.close("all")

    matrix = normalized_features_df.copy()
    matrix = matrix.apply(pd.to_numeric, errors="coerce")
    matrix = matrix.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    matrix = matrix.loc[matrix.std(axis=1) > 0]
    matrix = matrix.loc[:, matrix.std(axis=0) > 0]

    if matrix.empty:
        raise ValueError(
            "No valid features available for clustered heatmap generation."
        )

    cluster_map = sns.clustermap(
        matrix,
        method=method,
        metric=metric,
        z_score=None,
        standard_scale=None,
        figsize=(width, height),
        row_cluster=row_cluster,
        col_cluster=col_cluster,
        row_colors=row_colors,
        cmap=cmap,
    )

    if title:
        cluster_map.fig.suptitle(title, y=1.02, fontweight="bold")

    cluster_map.fig.tight_layout()
    cluster_map.savefig(out_png, dpi=dpi, bbox_inches="tight")
    plt.close(cluster_map.fig)


def main(study_id: str, analysis_id: str, df: pd.DataFrame) -> dict[str, Any]:
    """Generate clustered heatmap PNG and return metadata for Chainlit display."""
    if df.empty:
        raise ValueError("Analysis datatable is empty.")
    if "error" in df.columns:
        raise ValueError(
            str(df.iloc[0].get("error", "Analysis datatable request failed."))
        )
    if "Class" not in df.columns:
        raise ValueError("Expected a 'Class' column in analysis datatable.")

    working_df = df.copy().fillna(0)
    feature_columns = [
        col for col in working_df.columns if col not in {"Samples", "Class"}
    ]
    working_df[feature_columns] = working_df[feature_columns].apply(
        pd.to_numeric, errors="coerce"
    )
    working_df[feature_columns] = working_df[feature_columns].fillna(0)

    working_df["ClassNum"], _ = pd.factorize(working_df["Class"])
    working_df["ClassNum"] += 1

    if working_df["ClassNum"].nunique() < 2:
        raise ValueError("Need at least two classes to run clustered heatmap analysis.")

    scaling = "ZScore"
    method = "average"
    metric = "correlation"
    cluster_rows = True
    cluster_cols = True
    cmap = "inferno"
    width, height = 9.0, 9.0
    dpi = 300

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path("generated_plots")
    out_png = out_dir / f"clustered_heatmap_{study_id}_{analysis_id}_{timestamp}.png"

    normalized_df, row_colors = generate_clustered_heatmap_data(
        working_df,
        scaling=scaling,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    title = f"Clustered Heatmap: {study_id} / {analysis_id}"
    draw_and_save_clustered_heatmap(
        normalized_df,
        method=method,
        metric=metric,
        row_cluster=cluster_rows,
        col_cluster=cluster_cols,
        cmap=cmap,
        row_colors=row_colors,
        width=width,
        height=height,
        out_png=str(out_png),
        dpi=dpi,
        title=title,
    )

    return {
        "study_id": study_id,
        "analysis_id": analysis_id,
        "png_path": str(out_png.resolve()),
        "title": title,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a clustered heatmap from a TSV datatable file."
    )
    parser.add_argument("--study-id", required=True)
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--datatable-tsv", required=True)
    args = parser.parse_args()

    datatable_df = pd.read_csv(args.datatable_tsv, sep="\t")
    output = main(
        study_id=args.study_id,
        analysis_id=args.analysis_id,
        df=datatable_df,
    )
    print(output["png_path"])
