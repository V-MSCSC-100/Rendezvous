"""
HF Deluxe Pro Manager - Matplotlib Fuel & Mileage Visualizations
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from typing import List, Dict, Any, Optional
from visualizations.expense_charts import CHART_THEME, apply_dark_plot_style


def create_mileage_trend_chart(records: List[Dict[str, Any]]) -> Figure:
    """Generates a fuel efficiency (km/l) line graph over time."""
    fig = Figure(figsize=(6, 3.8), dpi=100, facecolor=CHART_THEME["fig_bg"])
    ax = fig.add_subplot(111)
    apply_dark_plot_style(ax, title="Fuel Efficiency Trend (km/l)", xlabel="Date", ylabel="Mileage (km/l)")

    valid_data = [
        (r["date"], r["calculated_mileage"])
        for r in records
        if r.get("calculated_mileage") is not None and r["calculated_mileage"] > 0
    ]

    if not valid_data:
        ax.text(
            0.5, 0.5, "Need 2+ Full Tank Refills to Plot Mileage",
            color=CHART_THEME["subtext"], ha="center", va="center", fontsize=11,
            transform=ax.transAxes,
        )
        return fig

    # Sort by date
    valid_data.sort(key=lambda x: x[0])
    dates = [x[0] for x in valid_data]
    mileages = [x[1] for x in valid_data]

    ax.plot(dates, mileages, marker="o", color="#10b981", linewidth=2.2, markersize=5, label="Recorded Mileage")
    
    # Average line
    avg_mileage = sum(mileages) / len(mileages)
    ax.axhline(avg_mileage, color="#f59e0b", linestyle="--", alpha=0.8, label=f"Avg: {avg_mileage:.1f} km/l")

    ax.legend(
        loc="best",
        facecolor=CHART_THEME["ax_bg"],
        edgecolor=CHART_THEME["grid"],
        labelcolor=CHART_THEME["text"],
        fontsize=8,
    )
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    return fig


def create_petrol_price_chart(records: List[Dict[str, Any]]) -> Figure:
    """Generates petrol price history chart over time."""
    fig = Figure(figsize=(6, 3.8), dpi=100, facecolor=CHART_THEME["fig_bg"])
    ax = fig.add_subplot(111)
    apply_dark_plot_style(ax, title="Petrol Price History (₹/L)", xlabel="Date", ylabel="Price per Litre (₹)")

    valid = [(r["date"], float(r["price_per_litre"])) for r in records if r.get("price_per_litre")]
    if not valid:
        ax.text(
            0.5, 0.5, "No Petrol Price Records",
            color=CHART_THEME["subtext"], ha="center", va="center", fontsize=11,
            transform=ax.transAxes,
        )
        return fig

    valid.sort(key=lambda x: x[0])
    dates = [x[0] for x in valid]
    prices = [x[1] for x in valid]

    ax.plot(dates, prices, marker="s", color="#0284c7", linewidth=2, markersize=5, label="Fuel Price")
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    return fig


def create_odometer_progression_chart(records: List[Dict[str, Any]]) -> Figure:
    """Generates odometer distance progression over time."""
    fig = Figure(figsize=(6, 3.8), dpi=100, facecolor=CHART_THEME["fig_bg"])
    ax = fig.add_subplot(111)
    apply_dark_plot_style(ax, title="Cumulative Odometer Reading (km)", xlabel="Date", ylabel="Odometer (km)")

    valid = [(r["date"], float(r["odometer"])) for r in records if r.get("odometer")]
    if not valid:
        ax.text(
            0.5, 0.5, "No Odometer History Yet",
            color=CHART_THEME["subtext"], ha="center", va="center", fontsize=11,
            transform=ax.transAxes,
        )
        return fig

    valid.sort(key=lambda x: (x[0], x[1]))
    dates = [x[0] for x in valid]
    odos = [x[1] for x in valid]

    ax.plot(dates, odos, marker="^", color="#ec4899", linewidth=2, markersize=5, label="Odometer")
    ax.fill_between(dates, odos, color="#ec4899", alpha=0.15)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()
    return fig

