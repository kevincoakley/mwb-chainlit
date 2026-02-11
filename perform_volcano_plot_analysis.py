#!/usr/bin/env python3
"""
MWPerformVolcanoPlotAnalysis.py

Non-interactive volcano-plot workflow for Metabolomics Workbench (MW) studies
using the MW REST API only (no Jupyter widgets / no file-upload widget).

Requirements:
  - requests, pandas, numpy, scipy, statsmodels, matplotlib
  - MWUtil.py in the same directory (or importable via PYTHONPATH)

Example:
  python MWPerformVolcanoPlotAnalysis.py \
      --study-id ST000001 \
      --analysis-id AN000001 \
      --class-a Control --class-b Treatment \
      --pvalue 0.05 --logfc 1.0 \
      --out-png volcano.png --out-csv significant.csv
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

import numpy as np
import pandas as pd
import requests  # noqa: F401  (used indirectly via MWUtil)
import scipy.stats
import statsmodels.stats.multitest
import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

MW_BASE_URL_DEFAULT = "https://www.metabolomicsworkbench.org/rest"


def generate_volcano_plot_data(
    df: pd.DataFrame,
    first_class_num: int,
    second_class_num: int,
    class_num_col: str = "ClassNum",
    contains_class_col: bool = True,
) -> Tuple[pd.DataFrame, Optional[str]]:
    """Generate volcano-plot statistics for two classes in the MW datatable.

    Returns:
      (volcano_df, err_msg)
    """
    volcano_df: Optional[pd.DataFrame] = None
    err_msg: Optional[str] = None

    with np.errstate(all="raise"):
        try:
            volcano_df = _generate_volcano_plot_data(
                df, first_class_num, second_class_num, class_num_col, contains_class_col
            )
        except FloatingPointError as e:
            err_msg = f"Failed to generate data for volcano plot: {e}"
        except Exception as e:
            err_msg = f"Failed to generate data for volcano plot: {e}"

    return volcano_df, err_msg


def _generate_volcano_plot_data(
    df: pd.DataFrame,
    first_class_num: int,
    second_class_num: int,
    class_num_col: str = "ClassNum",
    contains_class_col: bool = True,
) -> pd.DataFrame:
    # Drop Class column if present...
    work = df.copy()

    ##
    work = work.drop("Samples", axis=1)
    ##

    if contains_class_col and "Class" in work.columns:
        work = work.drop("Class", axis=1)

    if class_num_col not in work.columns:
        raise ValueError(f"Expected a '{class_num_col}' column in the dataframe.")

    # Extract data for two specified classes...
    data_a = work[work[class_num_col] == first_class_num].drop(class_num_col, axis=1)
    data_b = work[work[class_num_col] == second_class_num].drop(class_num_col, axis=1)

    if data_a.shape[0] < 2 or data_b.shape[0] < 2:
        raise ValueError(
            f"Need at least 2 samples per class for t-test; got classA={data_a.shape[0]}, classB={data_b.shape[0]}"
        )

    # Transform data (log2). Note: values must be > 0.
    data_a = np.log2(data_a)
    data_b = np.log2(data_b)

    # Calculate statistics...
    t_stats, p_values = scipy.stats.ttest_ind(
        data_a, data_b, equal_var=False, nan_policy="omit"
    )
    p_values = np.asarray(p_values, dtype=float)

    # Adjust P-values (FDR)...
    _, adj_p_values = statsmodels.stats.multitest.fdrcorrection(
        p_values, alpha=0.05, method="indep", is_sorted=False
    )

    # Calculate fold change (meanB - meanA) in log2 space...
    mean_a = data_a.mean(axis=0)
    mean_b = data_b.mean(axis=0)
    log2_fc = (mean_b - mean_a).to_numpy(dtype=float)

    # -log10(p)
    with np.errstate(divide="ignore", invalid="ignore"):
        log10_p = -np.log10(p_values)

    volcano_df = pd.DataFrame(
        {
            "log2(FoldChange)": log2_fc,
            "P-value": p_values,
            "-log10(P-value)": log10_p,
            "AdjustedP-value": np.asarray(adj_p_values, dtype=float),
            "t-Statistic": np.asarray(t_stats, dtype=float),
        },
        index=data_a.columns,
    )

    # Clean up any pathological values (e.g., p=0 -> inf); keep them but make them plottable.
    volcano_df.replace([np.inf, -np.inf], np.nan, inplace=True)

    return volcano_df


def write_significant_metabolites_csv(
    volcano_df: pd.DataFrame,
    out_csv: str,
    logfc_threshold: float,
    pvalue_threshold: float,
    logfc_col: str = "log2(FoldChange)",
    pvalue_col: str = "P-value",
) -> pd.DataFrame:
    sig = volcano_df[
        (volcano_df[pvalue_col] <= pvalue_threshold)
        & (np.abs(volcano_df[logfc_col]) >= logfc_threshold)
    ]
    sig = sig.sort_values(by=[logfc_col], ascending=True)
    sig.to_csv(out_csv, index=True)
    return sig


def save_volcano_plot_png(
    volcano_df: pd.DataFrame,
    out_png: str,
    logfc_threshold: float,
    pvalue_threshold: float,
    title: str = "Volcano Plot",
    logfc_col: str = "log2(FoldChange)",
    logp_col: str = "-log10(P-value)",
    figsize: Tuple[float, float] = (9, 6),
) -> None:
    df = volcano_df.copy()

    # Classify points to color them similarly to the notebook.
    # Note: we avoid seaborn here to keep the script lightweight.
    colors = np.full(len(df), "purple", dtype=object)

    sig_mask = df["P-value"] <= pvalue_threshold
    up_mask = sig_mask & (df[logfc_col] >= logfc_threshold)
    down_mask = sig_mask & (df[logfc_col] <= -logfc_threshold)
    mid_mask = sig_mask & (~up_mask) & (~down_mask)

    colors[up_mask.to_numpy()] = "red"
    colors[down_mask.to_numpy()] = "blue"
    colors[mid_mask.to_numpy()] = "orange"

    # Plot
    plt.figure(figsize=figsize)
    plt.scatter(
        df[logfc_col], df[logp_col], c=colors, s=22, alpha=0.85, edgecolors="none"
    )

    # Threshold lines
    plt.axvline(-logfc_threshold, linewidth=1, linestyle="dashed")
    plt.axvline(logfc_threshold, linewidth=1, linestyle="dashed")
    hline = -np.log10(pvalue_threshold)
    plt.axhline(hline, linewidth=1, linestyle="dashed")

    plt.title(title, fontweight="bold")
    plt.xlabel(logfc_col, fontweight="bold")
    plt.ylabel(logp_col, fontweight="bold")

    # Save
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()


def _pick_first_key(d: Dict[str, Any], what: str) -> str:
    if not d:
        raise ValueError(f"No {what} available.")
    return next(iter(d.keys()))


def resolve_analysis_and_classes(
    studies_results: Dict[str, Any],
    study_id: str,
    analysis_id: Optional[str],
    class_a: Optional[str],
    class_b: Optional[str],
) -> Tuple[str, str, str, int, int]:
    """Return (analysis_id, classA_name, classB_name, classA_num, classB_num)."""
    if study_id not in studies_results:
        raise ValueError(f"Study '{study_id}' not found in retrieved results.")

    study_block = studies_results[study_id]
    if analysis_id is None:
        analysis_id = _pick_first_key(study_block, "analysis IDs")
    if analysis_id not in study_block:
        raise ValueError(
            f"Analysis '{analysis_id}' not found under study '{study_id}'. Available: {list(study_block.keys())}"
        )

    class_map = study_block[analysis_id].get("class_names_to_nums", {})
    if not class_map:
        raise ValueError("No class mapping found (class_names_to_nums missing).")

    class_names = list(class_map.keys())

    if class_a is None or class_b is None:
        if len(class_names) < 2:
            raise ValueError(f"Need at least 2 classes; found: {class_names}")
        # default: first two by sorted name for reproducibility
        class_names_sorted = sorted(class_names)
        class_a = class_names_sorted[0]
        class_b = class_names_sorted[1]

    if class_a not in class_map:
        raise ValueError(
            f"Class A '{class_a}' not found. Available: {sorted(class_names)}"
        )
    if class_b not in class_map:
        raise ValueError(
            f"Class B '{class_b}' not found. Available: {sorted(class_names)}"
        )

    if class_a == class_b:
        raise ValueError("Class A and Class B must be different.")

    return (
        analysis_id,
        class_a,
        class_b,
        int(class_map[class_a]),
        int(class_map[class_b]),
    )


"""
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Generate a volcano plot for an MW study/analysis using the MW REST API.")
    p.add_argument("--study-id", required=True, help="MW study ID (e.g., ST000001)")
    p.add_argument("--analysis-id", default=None, help="MW analysis ID (e.g., AN000001). If omitted, the first analysis is used.")
    p.add_argument("--class-a", default=None, help="Class name for group A. If omitted, the first two classes (sorted) are used.")
    p.add_argument("--class-b", default=None, help="Class name for group B.")
    p.add_argument("--mw-base-url", default=MW_BASE_URL_DEFAULT, help="MW REST API base URL.")
    p.add_argument("--missing-values", default=None,
                   help="Missing value handling: NoAction, DeleteRows, DeleteColumns, ReplaceByColumnMean, ReplaceColumnMedian, ReplaceByZero, LinearInterpolation.")
    p.add_argument("--pvalue", type=float, default=0.05, help="P-value threshold for significance.")
    p.add_argument("--logfc", type=float, default=1.0, help="Absolute log2 fold-change threshold for significance.")
    p.add_argument("--out-png", default="volcano_plot.png", help="Output PNG path.")
    #p.add_argument("--out-csv", default="significant_metabolites.csv", help="Output CSV path for significant metabolites.")
    p.add_argument("--plot-width", type=float, default=9.0, help="Plot width (inches).")
    p.add_argument("--plot-height", type=float, default=6.0, help="Plot height (inches).")
    return p
"""


def main(study_id: str, analysis_id: str, df: pd.DataFrame) -> Dict[str, Any]:
    # args = build_arg_parser().parse_args()

    # Retrieve study analysis + datatable via REST API.
    # studies_results = MWUtil.RetrieveStudiesAnalysisAndResultsData(
    #    args.study_id,
    #    MWBaseURL=args.mw_base_url,
    #    MissingValuesMethod=args.missing_values,
    # )

    # analysis_id, class_a, class_b, class_a_num, class_b_num = resolve_analysis_and_classes(
    #    studies_results, args.study_id, args.analysis_id, args.class_a, args.class_b
    # )

    # df = studies_results[args.study_id][analysis_id]["data_frame"]

    # Default values
    pvalue = 0.05
    logfc = 1.0
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path("generated_plots")
    out_png = out_dir / f"volcano_{study_id}_{analysis_id}_{timestamp}.png"
    plot_width = 9.0
    plot_height = 6.0

    if df.empty:
        raise ValueError("Analysis datatable is empty.")
    if "error" in df.columns:
        raise ValueError(
            str(df.iloc[0].get("error", "Analysis datatable request failed."))
        )
    if "Class" not in df.columns:
        raise ValueError("Expected a 'Class' column in analysis datatable.")

    df = df.fillna(0)

    feature_columns = [col for col in df.columns if col not in {"Samples", "Class"}]
    df[feature_columns] = df[feature_columns].apply(pd.to_numeric, errors="coerce")
    df[feature_columns] = df[feature_columns].fillna(0)

    df = df.copy()
    df["ClassNum"], uniques = pd.factorize(df["Class"])

    # If you want numbering to start at 1 instead of 0:
    df["ClassNum"] += 1

    unique_df = df[["Class", "ClassNum"]].drop_duplicates()

    class_list = unique_df["Class"].tolist()
    classnum_list = unique_df["ClassNum"].tolist()
    if len(class_list) < 2:
        raise ValueError("Need at least two classes to run volcano plot analysis.")

    class_a = class_list[0]
    class_b = class_list[1]
    class_a_num = classnum_list[0]
    class_b_num = classnum_list[1]

    # print(f"\nStudy: {args.study_id}")
    # print(f"Analysis: {analysis_id}")
    # print(f"Class A: {class_a} (ClassNum={class_a_num})")
    # print(f"Class B: {class_b} (ClassNum={class_b_num})")

    volcano_df, err = generate_volcano_plot_data(
        df, class_a_num, class_b_num, class_num_col="ClassNum", contains_class_col=True
    )
    if err:
        raise RuntimeError(err)

    # Persist outputs
    # out_png = args.out_png
    # out_csv = args.out_csv
    os.makedirs(os.path.dirname(str(out_png)) or ".", exist_ok=True)
    # os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)

    title = f"Volcano Plot: {study_id} / {analysis_id} ({class_a} vs {class_b})"
    save_volcano_plot_png(
        volcano_df,
        str(out_png),
        logfc_threshold=logfc,
        pvalue_threshold=pvalue,
        title=title,
        figsize=(plot_width, plot_height),
    )

    # sig_df = write_significant_metabolites_csv(
    #    volcano_df,
    #    out_csv,
    #    logfc_threshold=args.logfc,
    #    pvalue_threshold=args.pvalue,
    # )

    # print(f"\nSaved volcano plot PNG: {out_png}")
    # print(f"Saved significant metabolites CSV: {out_csv}")
    # print(f"Significant metabolites found: {len(sig_df)}")

    # Print a small preview for CLI usability
    # if len(sig_df) > 0:
    #    print("\nTop 20 significant metabolites (sorted by log2(FoldChange)):")
    #    with pd.option_context("display.max_rows", 20, "display.max_columns", 10, "display.width", 140):
    #        print(sig_df.head(20))

    return {
        "study_id": study_id,
        "analysis_id": analysis_id,
        "class_a": class_a,
        "class_b": class_b,
        "png_path": str(out_png.resolve()),
        "title": title,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a volcano plot from a TSV datatable file."
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
