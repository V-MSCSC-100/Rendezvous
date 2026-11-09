"""
HF Deluxe Pro Manager - Matplotlib Expense & Financial Visualizations
"""

import os
import tempfile
# Ensure Matplotlib config dir is writable
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib_hf"))

import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from typing import List, Dict, Any, Optional

CHART_THEME = {
    "fig_bg": "#1e293b",
    "ax_bg": "#1e293b",
    "text": "#f8fafc",
    "subtext": "#94a3b8",
    "grid": "#334155",
    "colors": ["#10b981", "#0284c7", "#f59e0b", "#dc2626", "#8b5cf6", "#ec4899"],
}


def apply_dark_plot_style(ax: plt.Axes, title: str = "", xlabel: str = "", ylabel: str = ""):
    """Applies clean dark theme styling to a Matplotlib axes."""
    ax.set_facecolor(CHART_THEME["ax_bg"])
    if title:
        ax.set_title(title, color=CHART_THEME["text"], fontsize=11, fontweight="bold", pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, color=CHART_THEME["subtext"], fontsize=9, labelpad=8)
    if ylabel:
        ax.set_ylabel(ylabel, color=CHART_THEME["subtext"], fontsize=9, labelpad=8)

    ax.tick_params(colors=CHART_THEME["subtext"], labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(CHART_THEME["grid"])
    ax.grid(True, linestyle="--", alpha=0.3, color=CHART_THEME["grid"])


def create_expense_donut_chart(
    fuel_total: float, maint_total: float, upgrades_total: float, misc_total: float
) -> Figure:
    """Generates an expense distribution donut chart."""
    fig = Figure(figsize=(5, 3.8), dpi=100, facecolor=CHART_THEME["fig_bg"])
    ax = fig.add_subplot(111)

    labels = []
    values = []
    colors = []

    cat_defs = [
        ("Fuel", fuel_total, "#10b981"),
        ("Maintenance", maint_total, "#0284c7"),
        ("Upgrades", upgrades_total, "#f59e0b"),
        ("Misc / Other", misc_total, "#8b5cf6"),
    ]

    for lbl, val, col in cat_defs:
        if val > 0:
            labels.append(lbl)
            values.append(val)
            colors.append(col)

    if not values:
        ax.text(
            0.5, 0.5, "No Expenditure Data Yet",
            color=CHART_THEME["subtext"], ha="center", va="center", fontsize=11
        )
        ax.axis("off")
        return fig

    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.75,
        textprops={"color": CHART_THEME["text"], "fontsize": 8},
        wedgeprops=dict(width=0.45, edgecolor=CHART_THEME["fig_bg"]),
    )

    for at in autotexts:
        at.set_color("#ffffff")
        at.set_fontweight("bold")

    ax.set_title("Expense Distribution", color=CHART_THEME["text"], fontsize=11, fontweight="bold")
    fig.tight_layout()
    return fig


def create_monthly_expense_bar_chart(monthly_data: Dict[str, Dict[str, float]]) -> Figure:
    """
    Generates stacked monthly expenditure bar chart.
    monthly_data: {"2023-01": {"fuel": 1200, "maint": 500, "upgrades": 0, "misc": 0}, ...}
    """
    fig = Figure(figsize=(6, 3.8), dpi=100, facecolor=CHART_THEME["fig_bg"])
    ax = fig.add_subplot(111)
    apply_dark_plot_style(ax, title="Monthly Expenditure (₹)", xlabel="Month", ylabel="Amount (₹)")

    if not monthly_data:
        ax.text(
            0.5, 0.5, "No Monthly Data Available",
            color=CHART_THEME["subtext"], ha="center", va="center", fontsize=11,
            transform=ax.transAxes,
        )
        return fig

    months = sorted(monthly_data.keys())
    fuel_vals = [monthly_data[m].get("fuel", 0.0) for m in months]
    maint_vals = [monthly_data[m].get("maint", 0.0) for m in months]
    upg_vals = [monthly_data[m].get("upgrades", 0.0) for m in months]
    misc_vals = [monthly_data[m].get("misc", 0.0) for m in months]

    # Stacked bars
    p1 = ax.bar(months, fuel_vals, label="Fuel", color="#10b981", width=0.5)
    bottom_maint = fuel_vals
    p2 = ax.bar(months, maint_vals, bottom=bottom_maint, label="Maint", color="#0284c7", width=0.5)
    bottom_upg = [f + m for f, m in zip(bottom_maint, maint_vals)]
    p3 = ax.bar(months, upg_vals, bottom=bottom_upg, label="Upgrades", color="#f59e0b", width=0.5)
    bottom_misc = [b + u for b, u in zip(bottom_upg, upg_vals)]
    p4 = ax.bar(months, misc_vals, bottom=bottom_misc, label="Misc", color="#8b5cf6", width=0.5)

    ax.legend(
        loc="upper left",
        facecolor=CHART_THEME["ax_bg"],
        edgecolor=CHART_THEME["grid"],
        labelcolor=CHART_THEME["text"],
        fontsize=8,
    )
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    return fig

