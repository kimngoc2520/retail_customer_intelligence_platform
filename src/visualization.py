"""
Reusable plotting functions, extracted from the repeated
plt.figure()/sns.xxx() blocks written directly across all 5 notebooks.
Notebooks stay the place for narrative + specific one-off charts;
this module holds the plots that get redrawn with different data
across multiple notebooks (distribution, boxplot-by-group, radar chart).

This is a library module — no run() entrypoint, since it has no
standalone pipeline step (nothing in main.py calls it). Import
individual functions from notebooks or other src/ modules instead.

Usage:
    from src.visualization import plot_distribution, plot_radar_chart
    plot_distribution(rfm['monetary'], title='Phan phoi Monetary')
"""

from typing import List, Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import seaborn as sns
import pandas as pd

sns.set_style("whitegrid")


def plot_distribution(
    series: pd.Series,
    title: str,
    bins: int = 50,
    xlim_quantile: Optional[float] = None,
    ax: Optional[Axes] = None,
) -> Axes:
    """Histogram for a single numeric column, with optional right-tail clipping
    (xlim_quantile=0.99 clips the x-axis at the 99th percentile — useful for
    the long-tail distributions common in RFM data)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 4))
    sns.histplot(series, bins=bins, ax=ax)
    if xlim_quantile:
        ax.set_xlim(0, series.quantile(xlim_quantile))
    ax.set_title(title)
    return ax


def plot_boxplot_by_group(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    order: Optional[List[str]] = None,
    ylim_quantile: Optional[float] = None,
    ax: Optional[Axes] = None,
) -> Axes:
    """Boxplot of y across categories of x — the standard bivariate chart
    used throughout 01_eda.ipynb and 02_statistical_analysis.ipynb."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5))
    sns.boxplot(data=df, x=x, y=y, order=order, ax=ax)
    if ylim_quantile:
        ax.set_ylim(0, df[y].quantile(ylim_quantile))
    ax.set_title(title)
    return ax


def plot_radar_chart(
    profile_df: pd.DataFrame,
    feature_cols: List[str],
    title: str,
    invert_cols: Optional[List[str]] = None,
) -> Axes:
    """
    Radar/spider chart comparing groups (e.g. clusters) across several
    normalized (0-1) features at once. invert_cols lists columns where
    LOWER is better (e.g. recency_days) — these get flipped before
    normalizing so "further out on the chart" always means "better"
    on every axis, avoiding a misleading shape.
    """
    invert_cols = invert_cols or []
    radar_df = profile_df[feature_cols].copy()
    for col in invert_cols:
        radar_df[col] = radar_df[col].max() - radar_df[col]

    radar_norm = (radar_df - radar_df.min()) / (radar_df.max() - radar_df.min())

    labels = [f"{c} (dao nguoc)" if c in invert_cols else c for c in feature_cols]
    num_vars = len(labels)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]

    _, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    for idx in radar_norm.index:
        values = radar_norm.loc[idx].tolist()
        values += values[:1]
        ax.plot(angles, values, linewidth=2, label=str(idx))
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_title(title)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    plt.tight_layout()
    return ax


def plot_revenue_contribution(
    contribution_df: pd.DataFrame,
    group_col: str,
    title: str,
) -> Axes:
    """Side-by-side % of customers vs. % of revenue bar chart — the key
    Pareto-style chart used in 04_business_analysis.ipynb."""
    _, ax = plt.subplots(figsize=(9, 5))
    x = range(len(contribution_df))
    width = 0.35
    ax.bar([i - width / 2 for i in x], contribution_df["pct_of_customers"], width, label="% khach hang")
    ax.bar([i + width / 2 for i in x], contribution_df["pct_of_revenue"], width, label="% doanh thu")
    ax.set_xticks(list(x))
    ax.set_xticklabels(contribution_df[group_col], rotation=15)
    ax.set_ylabel("%")
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    return ax
