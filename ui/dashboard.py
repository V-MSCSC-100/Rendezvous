"""
HF Deluxe Pro Manager - Dashboard Page
Provides an overview of vehicle status, key performance metrics, quick actions,
upcoming maintenance alerts, and recent activities.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict, Any
from ui.styles import DARK_THEME, FONTS
from ui.components import StatCard, ScrollableFrame, DataTable
from models.vehicle import VehicleRepository, Vehicle
from models.fuel import RefuelRepository
from models.maintenance import MaintenanceRepository
from models.upgrades import UpgradeRepository
from models.expense import ExpenseRepository
from models.trips import TripRepository
from services.maintenance_calculator import ReminderItem


class DashboardPage(ttk.Frame):
    """Main dashboard page."""

    def __init__(
        self,
        parent: tk.Widget,
        navigate_callback: Callable[[str], None],
        get_active_vehicle_id: Callable[[], int],
        **kwargs,
    ):
        super().__init__(parent, style="TFrame", **kwargs)
        self.navigate = navigate_callback
        self.get_active_vehicle_id = get_active_vehicle_id

        self.vehicle_repo = VehicleRepository()
        self.fuel_repo = RefuelRepository()
        self.maint_repo = MaintenanceRepository()
        self.upgrade_repo = UpgradeRepository()
        self.expense_repo = ExpenseRepository()
        self.trip_repo = TripRepository()

        self._build_ui()

    def _build_ui(self):
        # Top scrollable container
        self.scroll_container = ScrollableFrame(self)
        self.scroll_container.pack(fill="both", expand=True)
        content = self.scroll_container.scrollable_content

        # 1. Header Banner
        self.header_frame = ttk.Frame(content, style="Card.TFrame", padding=16)
        self.header_frame.pack(fill="x", padx=16, pady=(16, 12))

        header_left = ttk.Frame(self.header_frame, style="Card.TFrame")
        header_left.pack(side="left", fill="x", expand=True)

        self.lbl_welcome = ttk.Label(
            header_left,
            text="HF DELUXE PRO MANAGER",
            style="Card.TLabel",
            font=FONTS["h1"],
        )
        self.lbl_welcome.pack(anchor="w")

        self.lbl_subtitle = ttk.Label(
            header_left,
            text="Motorcycle Management & Touring Companion",
            style="CardDim.TLabel",
        )
        self.lbl_subtitle.pack(anchor="w", pady=(2, 0))

        # Vehicle info badge on the right
        self.badge_frame = tk.Frame(
            self.header_frame, bg=DARK_THEME["bg_card_inner"], padx=12, pady=8
        )
        self.badge_frame.pack(side="right")

        self.lbl_vname = tk.Label(
            self.badge_frame,
            text="Hero HF Deluxe Pro",
            bg=DARK_THEME["bg_card_inner"],
            fg=DARK_THEME["text_primary"],
            font=FONTS["body_bold"],
        )
        self.lbl_vname.pack(anchor="e")

        self.lbl_vreg = tk.Label(
            self.badge_frame,
            text="DL-01-AB-1234",
            bg=DARK_THEME["bg_card_inner"],
            fg=DARK_THEME["primary"],
            font=FONTS["caption"],
        )
        self.lbl_vreg.pack(anchor="e")

        # 2. Key Metric Stat Cards Row
        cards_row = ttk.Frame(content, style="TFrame")
        cards_row.pack(fill="x", padx=16, pady=(0, 16))

        for i in range(4):
            cards_row.columnconfigure(i, weight=1)

        self.card_mileage = StatCard(
            cards_row,
            title="Lifetime Mileage",
            value="-- km/l",
            subtitle="Best: -- | Worst: --",
            accent_color="#10b981",
            icon_text="⚡",
        )
        self.card_mileage.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        self.card_odometer = StatCard(
            cards_row,
            title="Current Odometer",
            value="-- km",
            subtitle="Vehicle reading",
            accent_color="#0284c7",
            icon_text="🏍️",
        )
        self.card_odometer.grid(row=0, column=1, padx=4, sticky="nsew")

        self.card_expenditure = StatCard(
            cards_row,
            title="Total Ownership",
            value="₹ --",
            subtitle="Fuel + Maint + Upgrades",
            accent_color="#dc2626",
            icon_text="💰",
        )
        self.card_expenditure.grid(row=0, column=2, padx=4, sticky="nsew")

        self.card_cost_km = StatCard(
            cards_row,
            title="Running Cost / KM",
            value="₹ -- / km",
            subtitle="Operational expenditure",
            accent_color="#f59e0b",
            icon_text="📊",
        )
        self.card_cost_km.grid(row=0, column=3, padx=(8, 0), sticky="nsew")

        # 3. Quick Action Buttons Row
        actions_card = ttk.Frame(content, style="Card.TFrame", padding=12)
        actions_card.pack(fill="x", padx=16, pady=(0, 16))

        lbl_qa = ttk.Label(
            actions_card, text="QUICK ACTIONS", style="CardTitle.TLabel", font=FONTS["caption"]
        )
        lbl_qa.pack(anchor="w", pady=(0, 8))

        btn_row = ttk.Frame(actions_card, style="Card.TFrame")
        btn_row.pack(fill="x")

        ttk.Button(
            btn_row,
            text="+ Log Refuelling",
            style="Primary.TButton",
            command=lambda: self.navigate("fuel"),
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            btn_row,
            text="+ Record Service",
            style="Secondary.TButton",
            command=lambda: self.navigate("maintenance"),
        ).pack(side="left", padx=8)

        ttk.Button(
            btn_row,
            text="+ Plan Road Trip",
            style="Outline.TButton",
            command=lambda: self.navigate("trip_planner"),
        ).pack(side="left", padx=8)

        ttk.Button(
            btn_row,
            text="+ Add Modification",
            style="Outline.TButton",
            command=lambda: self.navigate("upgrades"),
        ).pack(side="left", padx=8)

        ttk.Button(
            btn_row,
            text="View Full Analytics →",
            style="Outline.TButton",
            command=lambda: self.navigate("analytics"),
        ).pack(side="right")

        # 4. Two-Column Middle Section: Maintenance Reminders & Recent Trips
        mid_row = ttk.Frame(content, style="TFrame")
        mid_row.pack(fill="x", padx=16, pady=(0, 16))
        mid_row.columnconfigure(0, weight=1)
        mid_row.columnconfigure(1, weight=1)

        # Left Column: Reminders
        rem_card = ttk.Frame(mid_row, style="Card.TFrame", padding=14)
        rem_card.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        rem_head = ttk.Frame(rem_card, style="Card.TFrame")
        rem_head.pack(fill="x", pady=(0, 8))
        ttk.Label(
            rem_head, text="MAINTENANCE ALERTS", style="CardTitle.TLabel", font=FONTS["caption"]
        ).pack(side="left")

        btn_all_rem = ttk.Button(
            rem_head,
            text="Manage →",
            style="Outline.TButton",
            command=lambda: self.navigate("maintenance"),
        )
        btn_all_rem.pack(side="right")

        self.reminders_container = ttk.Frame(rem_card, style="Card.TFrame")
        self.reminders_container.pack(fill="both", expand=True)

        # Right Column: Recent / Upcoming Trips
        trips_card = ttk.Frame(mid_row, style="Card.TFrame", padding=14)
        trips_card.grid(row=0, column=1, padx=(8, 0), sticky="nsew")

        trips_head = ttk.Frame(trips_card, style="Card.TFrame")
        trips_head.pack(fill="x", pady=(0, 8))
        ttk.Label(
            trips_head, text="TOURING & TRIPS", style="CardTitle.TLabel", font=FONTS["caption"]
        ).pack(side="left")

        btn_all_trips = ttk.Button(
            trips_head,
            text="History →",
            style="Outline.TButton",
            command=lambda: self.navigate("trip_history"),
        )
        btn_all_trips.pack(side="right")

        self.trips_container = ttk.Frame(trips_card, style="Card.TFrame")
        self.trips_container.pack(fill="both", expand=True)

        # 5. Bottom Section: Recent Refuelling Activity Table
        act_card = ttk.Frame(content, style="Card.TFrame", padding=14)
        act_card.pack(fill="both", expand=True, padx=16, pady=(0, 20))

        ttk.Label(
            act_card,
            text="RECENT REFUELLING LOGS",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(anchor="w", pady=(0, 8))

        cols = [
            ("date", "Date", 110),
            ("odometer", "Odometer (km)", 120),
            ("fuel_quantity", "Litres (L)", 100),
            ("price_per_litre", "Price / L (₹)", 110),
            ("total_amount", "Total Paid (₹)", 120),
            ("calculated_mileage", "Mileage (km/l)", 120),
            ("petrol_station", "Petrol Station", 180),
        ]
        self.recent_refuel_table = DataTable(act_card, columns=cols, show_search=False)
        self.recent_refuel_table.pack(fill="both", expand=True)

    def refresh_data(self):
        """Reload all metrics and tables from SQLite for the active vehicle."""
        vid = self.get_active_vehicle_id()
        vehicle = self.vehicle_repo.get_by_id(vid)
        if not vehicle:
            return

        # Header vehicle badge
        self.lbl_vname.config(text=f"{vehicle.manufacturer} {vehicle.model}")
        self.lbl_vreg.config(text=f"{vehicle.registration_number}  |  {vehicle.current_odometer:,.0f} km")

        # 1. Fuel Stats
        fuel_stats = self.fuel_repo.get_stats(vid)
        if fuel_stats.lifetime_avg_mileage:
            self.card_mileage.update_value(
                f"{fuel_stats.lifetime_avg_mileage:.1f} km/l",
                f"Best: {fuel_stats.best_mileage or 0:.1f} | Worst: {fuel_stats.lowest_mileage or 0:.1f} km/l",
            )
        else:
            self.card_mileage.update_value(
                "-- km/l", "Log consecutive full refills"
            )

        # 2. Odometer
        self.card_odometer.update_value(
            f"{vehicle.current_odometer:,.0f} km",
            f"Engine: {vehicle.engine_capacity:.1f} cc | {vehicle.fuel_type}",
        )

        # 3. Ownership expenditure
        fin = self.expense_repo.get_full_financial_summary(vid)
        self.card_expenditure.update_value(
            f"₹ {fin.total_ownership:,.0f}",
            f"Fuel: ₹{fin.total_fuel:,.0f} | Maint: ₹{fin.total_maintenance:,.0f}",
        )

        # 4. Running cost per km
        if fin.cost_per_km > 0:
            self.card_cost_km.update_value(
                f"₹ {fin.cost_per_km:.2f} / km",
                f"Avg Monthly: ₹{fin.avg_monthly_expenditure:,.0f}",
            )
        else:
            self.card_cost_km.update_value("₹ -- / km", "Awaiting ride records")

        # 5. Populate Maintenance Reminders
        reminders = self.maint_repo.get_maintenance_reminders(vid)
        for w in self.reminders_container.winfo_children():
            w.destroy()

        if not reminders:
            lbl = ttk.Label(
                self.reminders_container,
                text="No upcoming maintenance scheduled.",
                style="CardDim.TLabel",
            )
            lbl.pack(pady=10)
        else:
            # Display top 3 reminders
            for rem in reminders[:3]:
                item_f = tk.Frame(
                    self.reminders_container,
                    bg=DARK_THEME["bg_card_inner"],
                    padx=10,
                    pady=8,
                )
                item_f.pack(fill="x", pady=3)

                badge = tk.Label(
                    item_f,
                    text=f" {rem.status.upper()} ",
                    bg=rem.status_color,
                    fg="#ffffff",
                    font=("Segoe UI", 8, "bold"),
                    padx=4,
                    pady=2,
                )
                badge.pack(side="left", padx=(0, 8))

                lbl_name = tk.Label(
                    item_f,
                    text=rem.part_name,
                    bg=DARK_THEME["bg_card_inner"],
                    fg=DARK_THEME["text_primary"],
                    font=FONTS["body_bold"],
                )
                lbl_name.pack(side="left")

                # Detail on right (km remaining or due odo)
                due_info = ""
                if rem.km_remaining is not None:
                    if rem.km_remaining <= 0:
                        due_info = f"Overdue by {-rem.km_remaining:.0f} km"
                    else:
                        due_info = f"In {rem.km_remaining:.0f} km"
                elif rem.days_remaining is not None:
                    if rem.days_remaining <= 0:
                        due_info = f"Overdue by {-rem.days_remaining} days"
                    else:
                        due_info = f"In {rem.days_remaining} days"

                lbl_due = tk.Label(
                    item_f,
                    text=due_info,
                    bg=DARK_THEME["bg_card_inner"],
                    fg=DARK_THEME["text_secondary"],
                    font=FONTS["caption"],
                )
                lbl_due.pack(side="right")

        # 6. Populate Recent Trips
        trips = self.trip_repo.get_by_vehicle(vid)
        for w in self.trips_container.winfo_children():
            w.destroy()

        if not trips:
            lbl = ttk.Label(
                self.trips_container,
                text="No road trips planned yet. Click '+ Plan Road Trip' to begin!",
                style="CardDim.TLabel",
            )
            lbl.pack(pady=10)
        else:
            for trip in trips[:3]:
                tf = tk.Frame(
                    self.trips_container,
                    bg=DARK_THEME["bg_card_inner"],
                    padx=10,
                    pady=8,
                )
                tf.pack(fill="x", pady=3)

                status_color = (
                    DARK_THEME["success"]
                    if trip.status == "Completed"
                    else (DARK_THEME["secondary"] if trip.status == "Planned" else DARK_THEME["danger"])
                )
                tk.Label(
                    tf,
                    text=f" {trip.status} ",
                    bg=status_color,
                    fg="#ffffff",
                    font=("Segoe UI", 8, "bold"),
                    padx=4,
                ).pack(side="left", padx=(0, 8))

                tk.Label(
                    tf,
                    text=trip.title,
                    bg=DARK_THEME["bg_card_inner"],
                    fg=DARK_THEME["text_primary"],
                    font=FONTS["body_bold"],
                ).pack(side="left")

                tk.Label(
                    tf,
                    text=f"{trip.estimated_distance:.0f} km  |  ₹{trip.estimated_fuel_cost:.0f}",
                    bg=DARK_THEME["bg_card_inner"],
                    fg=DARK_THEME["text_secondary"],
                    font=FONTS["caption"],
                ).pack(side="right")

        # 7. Recent refuel table
        refuels = self.fuel_repo.get_by_vehicle(vid)
        table_rows = []
        for r in refuels[:5]:
            table_rows.append(
                {
                    "id": r.id,
                    "date": r.date,
                    "odometer": f"{r.odometer:,.0f}",
                    "fuel_quantity": f"{r.fuel_quantity:.2f}",
                    "price_per_litre": f"{r.price_per_litre:.2f}",
                    "total_amount": f"{r.total_amount:,.2f}",
                    "calculated_mileage": (
                        f"{r.calculated_mileage:.1f}" if r.calculated_mileage else "--"
                    ),
                    "petrol_station": r.petrol_station or "--",
                }
            )
        self.recent_refuel_table.set_data(table_rows)

