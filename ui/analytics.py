"""
HF Deluxe Pro Manager - Financial Analytics Page
Embeds interactive Matplotlib visualisations and comprehensive cost breakdowns.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, Any, List
from collections import defaultdict
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from ui.styles import DARK_THEME, FONTS
from ui.components import StatCard, ScrollableFrame, SectionHeader
from models.expense import ExpenseRepository
from models.vehicle import VehicleRepository
from models.fuel import RefuelRepository
from models.maintenance import MaintenanceRepository
from models.upgrades import UpgradeRepository
from visualizations.expense_charts import create_expense_donut_chart, create_monthly_expense_bar_chart
from visualizations.fuel_charts import (
    create_mileage_trend_chart,
    create_petrol_price_chart,
    create_odometer_progression_chart,
)


class AnalyticsPage(ttk.Frame):
    """Financial Analytics and Charts Page."""

    def __init__(
        self,
        parent: tk.Widget,
        get_active_vehicle_id: Callable[[], int],
        **kwargs,
    ):
        super().__init__(parent, style="TFrame", **kwargs)
        self.get_active_vehicle_id = get_active_vehicle_id

        self.expense_repo = ExpenseRepository()
        self.vehicle_repo = VehicleRepository()
        self.fuel_repo = RefuelRepository()
        self.maint_repo = MaintenanceRepository()
        self.upgrade_repo = UpgradeRepository()

        self.canvas_widgets: List[FigureCanvasTkAgg] = []
        self._build_ui()

    def _build_ui(self):
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        content = self.scroll.scrollable_content

        # Header
        header = SectionHeader(
            content,
            title="FINANCIAL ANALYTICS & INSIGHTS",
            subtitle="Complete cost of ownership, efficiency trends, and expenditure distribution",
        )
        header.pack(fill="x", padx=16, pady=16)

        # Stat cards row
        stats_row = ttk.Frame(content, style="TFrame")
        stats_row.pack(fill="x", padx=16, pady=(0, 16))
        for i in range(4):
            stats_row.columnconfigure(i, weight=1)

        self.card_total_cost = StatCard(
            stats_row,
            title="Total Ownership Spend",
            value="₹ --",
            subtitle="Vehicle + Operational",
            accent_color="#dc2626",
            icon_text="💰",
        )
        self.card_total_cost.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        self.card_operational = StatCard(
            stats_row,
            title="Total Operational Spend",
            value="₹ --",
            subtitle="Fuel + Maint + Upgrades",
            accent_color="#f59e0b",
            icon_text="🧾",
        )
        self.card_operational.grid(row=0, column=1, padx=4, sticky="nsew")

        self.card_cost_km = StatCard(
            stats_row,
            title="Running Cost / KM",
            value="₹ -- / km",
            subtitle="Real-world average",
            accent_color="#0284c7",
            icon_text="📊",
        )
        self.card_cost_km.grid(row=0, column=2, padx=4, sticky="nsew")

        self.card_monthly = StatCard(
            stats_row,
            title="Avg Monthly Cost",
            value="₹ -- / mo",
            subtitle="Active months",
            accent_color="#10b981",
            icon_text="📅",
        )
        self.card_monthly.grid(row=0, column=3, padx=(8, 0), sticky="nsew")

        # Charts Section
        self.charts_container = ttk.Frame(content, style="TFrame")
        self.charts_container.pack(fill="both", expand=True, padx=16, pady=(0, 20))
        self.charts_container.columnconfigure(0, weight=1)
        self.charts_container.columnconfigure(1, weight=1)

        # 4 Chart card containers
        self.chart_frame_donut = ttk.Frame(self.charts_container, style="Card.TFrame", padding=10)
        self.chart_frame_donut.grid(row=0, column=0, padx=(0, 8), pady=(0, 16), sticky="nsew")

        self.chart_frame_monthly = ttk.Frame(self.charts_container, style="Card.TFrame", padding=10)
        self.chart_frame_monthly.grid(row=0, column=1, padx=(8, 0), pady=(0, 16), sticky="nsew")

        self.chart_frame_mileage = ttk.Frame(self.charts_container, style="Card.TFrame", padding=10)
        self.chart_frame_mileage.grid(row=1, column=0, padx=(0, 8), pady=(0, 16), sticky="nsew")

        self.chart_frame_price = ttk.Frame(self.charts_container, style="Card.TFrame", padding=10)
        self.chart_frame_price.grid(row=1, column=1, padx=(8, 0), pady=(0, 16), sticky="nsew")

        self.chart_frame_odo = ttk.Frame(self.charts_container, style="Card.TFrame", padding=10)
        self.chart_frame_odo.grid(row=2, column=0, columnspan=2, pady=(0, 16), sticky="nsew")

    def refresh_data(self):
        """Regenerate and render all charts and metrics for active vehicle."""
        vid = self.get_active_vehicle_id()
        fin = self.expense_repo.get_full_financial_summary(vid)

        # Update cards
        self.card_total_cost.update_value(f"₹ {fin.total_ownership:,.2f}")
        self.card_operational.update_value(f"₹ {fin.total_operational:,.2f}")
        self.card_cost_km.update_value(f"₹ {fin.cost_per_km:.2f} / km" if fin.cost_per_km > 0 else "--")
        self.card_monthly.update_value(f"₹ {fin.avg_monthly_expenditure:,.2f} / mo")

        # Clear existing canvases
        for c in self.canvas_widgets:
            c.get_tk_widget().destroy()
        self.canvas_widgets.clear()

        # Gather dataset
        refuels = [r.to_dict() for r in self.fuel_repo.get_by_vehicle(vid)]
        services = self.maint_repo.get_services_by_vehicle(vid)
        upgrades = self.upgrade_repo.get_by_vehicle(vid)
        expenses = self.expense_repo.get_by_vehicle(vid)

        # Chart 1: Donut chart
        fig_donut = create_expense_donut_chart(
            fin.total_fuel, fin.total_maintenance, fin.total_upgrades, fin.total_misc
        )
        c_donut = FigureCanvasTkAgg(fig_donut, master=self.chart_frame_donut)
        c_donut.draw()
        c_donut.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_widgets.append(c_donut)

        # Chart 2: Monthly breakdown
        monthly_map: Dict[str, Dict[str, float]] = defaultdict(lambda: {"fuel": 0.0, "maint": 0.0, "upgrades": 0.0, "misc": 0.0})
        for r in refuels:
            if r.get("date"):
                m = r["date"][:7]
                monthly_map[m]["fuel"] += float(r.get("total_amount") or 0.0)
        for s in services:
            if s.service_date:
                m = s.service_date[:7]
                monthly_map[m]["maint"] += float(s.total_expenditure)
        for u in upgrades:
            if u.installation_date:
                m = u.installation_date[:7]
                monthly_map[m]["upgrades"] += float(u.cost)
        for e in expenses:
            if e.expense_date:
                m = e.expense_date[:7]
                monthly_map[m]["misc"] += float(e.amount)

        fig_monthly = create_monthly_expense_bar_chart(dict(monthly_map))
        c_monthly = FigureCanvasTkAgg(fig_monthly, master=self.chart_frame_monthly)
        c_monthly.draw()
        c_monthly.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_widgets.append(c_monthly)

        # Chart 3: Fuel efficiency trend
        fig_mileage = create_mileage_trend_chart(refuels)
        c_mileage = FigureCanvasTkAgg(fig_mileage, master=self.chart_frame_mileage)
        c_mileage.draw()
        c_mileage.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_widgets.append(c_mileage)

        # Chart 4: Petrol price trend
        fig_price = create_petrol_price_chart(refuels)
        c_price = FigureCanvasTkAgg(fig_price, master=self.chart_frame_price)
        c_price.draw()
        c_price.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_widgets.append(c_price)

        # Chart 5: Distance progression
        # Combine dates and odometers from refuels and services
        odo_points = []
        for r in refuels:
            odo_points.append({"date": r["date"], "odometer": r["odometer"]})
        for s in services:
            odo_points.append({"date": s.service_date, "odometer": s.odometer})
        fig_odo = create_odometer_progression_chart(odo_points)
        c_odo = FigureCanvasTkAgg(fig_odo, master=self.chart_frame_odo)
        c_odo.draw()
        c_odo.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_widgets.append(c_odo)

