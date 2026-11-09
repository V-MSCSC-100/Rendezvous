"""
HF Deluxe Pro Manager - Fuel Management Page
Handles refuelling logging, full-tank mileage tracking, fuel expenditure, and statistics.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from datetime import date
from ui.styles import DARK_THEME, FONTS
from ui.components import StatCard, ScrollableFrame, SectionHeader, DataTable, ToastNotification
from models.fuel import Refuel, RefuelRepository
from models.vehicle import VehicleRepository
from services.fuel_calculator import calculate_fuel_cost


class FuelPage(ttk.Frame):
    """Fuel Manager Page."""

    def __init__(
        self,
        parent: tk.Widget,
        get_active_vehicle_id: Callable[[], int],
        on_data_changed: Callable[[], None],
        **kwargs,
    ):
        super().__init__(parent, style="TFrame", **kwargs)
        self.get_active_vehicle_id = get_active_vehicle_id
        self.on_data_changed = on_data_changed

        self.fuel_repo = RefuelRepository()
        self.vehicle_repo = VehicleRepository()

        self._build_ui()

    def _build_ui(self):
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        content = self.scroll.scrollable_content

        # Header
        header = SectionHeader(
            content,
            title="FUEL & MILEAGE MANAGER",
            subtitle="Full-to-full refuelling logs, mileage analysis, and fuel expenditures",
            action_text="+ Log New Refuelling",
            action_callback=self._open_add_refuel_dialog,
        )
        header.pack(fill="x", padx=16, pady=16)

        # Aggregate Statistics Row (Cards)
        stats_row = ttk.Frame(content, style="TFrame")
        stats_row.pack(fill="x", padx=16, pady=(0, 16))
        for i in range(4):
            stats_row.columnconfigure(i, weight=1)

        self.card_lifetime = StatCard(
            stats_row,
            title="Lifetime Avg Mileage",
            value="-- km/l",
            subtitle="Best: -- | Lowest: --",
            accent_color="#10b981",
            icon_text="⚡",
        )
        self.card_lifetime.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        self.card_latest = StatCard(
            stats_row,
            title="Latest Mileage",
            value="-- km/l",
            subtitle="Consecutive full refills",
            accent_color="#0284c7",
            icon_text="⛽",
        )
        self.card_latest.grid(row=0, column=1, padx=4, sticky="nsew")

        self.card_litres = StatCard(
            stats_row,
            title="Total Fuel Purchased",
            value="-- Litres",
            subtitle="Refuel events: 0",
            accent_color="#f59e0b",
            icon_text="🛢️",
        )
        self.card_litres.grid(row=0, column=2, padx=4, sticky="nsew")

        self.card_fuel_spent = StatCard(
            stats_row,
            title="Total Fuel Spend",
            value="₹ --",
            subtitle="Avg price: ₹ -- / L",
            accent_color="#dc2626",
            icon_text="💳",
        )
        self.card_fuel_spent.grid(row=0, column=3, padx=(8, 0), sticky="nsew")

        # Refuel Records Table Section
        table_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        table_card.pack(fill="both", expand=True, padx=16, pady=(0, 20))

        tb_head = ttk.Frame(table_card, style="Card.TFrame")
        tb_head.pack(fill="x", pady=(0, 12))

        ttk.Label(
            tb_head,
            text="REFUELLING HISTORY & CONSUMPTION LOGS",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(side="left")

        btn_box = ttk.Frame(tb_head, style="Card.TFrame")
        btn_box.pack(side="right")

        ttk.Button(
            btn_box,
            text="Edit Selected",
            style="Outline.TButton",
            command=self._edit_selected_refuel,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            btn_box,
            text="Delete Selected",
            style="Outline.TButton",
            command=self._delete_selected_refuel,
        ).pack(side="left")

        cols = [
            ("date", "Refuel Date", 100),
            ("odometer", "Odometer (km)", 110),
            ("fuel_quantity", "Fuel Qty (L)", 90),
            ("price_per_litre", "Price / L (₹)", 100),
            ("total_amount", "Total Paid (₹)", 110),
            ("is_full_tank", "Tank Status", 100),
            ("distance_travelled", "Trip Dist (km)", 100),
            ("calculated_mileage", "Mileage (km/l)", 110),
            ("petrol_station", "Petrol Station", 150),
            ("notes", "Notes", 140),
        ]

        self.table = DataTable(
            table_card,
            columns=cols,
            show_search=True,
            on_double_click=self._on_table_double_click,
        )
        self.table.pack(fill="both", expand=True)

    def refresh_data(self):
        """Update stat cards and table with latest SQLite data."""
        vid = self.get_active_vehicle_id()
        stats = self.fuel_repo.get_stats(vid)

        # 1. Update Cards
        if stats.lifetime_avg_mileage:
            self.card_lifetime.update_value(
                f"{stats.lifetime_avg_mileage:.1f} km/l",
                f"Best: {stats.best_mileage or 0:.1f} | Lowest: {stats.lowest_mileage or 0:.1f} km/l",
            )
        else:
            self.card_lifetime.update_value(
                "-- km/l", "Requires 2+ full tank refills"
            )

        if stats.latest_mileage:
            self.card_latest.update_value(
                f"{stats.latest_mileage:.1f} km/l", "Latest full-to-full leg"
            )
        else:
            self.card_latest.update_value("-- km/l", "No full-to-full leg yet")

        self.card_litres.update_value(
            f"{stats.total_litres:,.1f} L",
            f"Total events: {stats.refuel_count}",
        )

        self.card_fuel_spent.update_value(
            f"₹ {stats.total_expenditure:,.2f}",
            f"Avg: ₹ {stats.average_price:.2f} / L",
        )

        # 2. Update Table
        records = self.fuel_repo.get_by_vehicle(vid)
        table_data = []
        for r in records:
            tank_status = "Full Tank" if r.is_full_tank else "Partial"
            table_data.append(
                {
                    "id": r.id,
                    "date": r.date,
                    "odometer": f"{r.odometer:,.1f}",
                    "fuel_quantity": f"{r.fuel_quantity:.2f}",
                    "price_per_litre": f"{r.price_per_litre:.2f}",
                    "total_amount": f"{r.total_amount:,.2f}",
                    "is_full_tank": tank_status,
                    "distance_travelled": (
                        f"{r.distance_travelled:.1f}" if r.distance_travelled is not None else "--"
                    ),
                    "calculated_mileage": (
                        f"{r.calculated_mileage:.1f}" if r.calculated_mileage is not None else "--"
                    ),
                    "petrol_station": r.petrol_station or "--",
                    "notes": r.notes or "--",
                }
            )
        self.table.set_data(table_data)

    def _open_add_refuel_dialog(self):
        self._show_refuel_form(None)

    def _edit_selected_refuel(self):
        sel = self.table.get_selected()
        if not sel:
            messagebox.showinfo("Select Record", "Please select a refuelling record to edit.")
            return
        refuel = self.fuel_repo.get_by_id(int(sel["id"]))
        if refuel:
            self._show_refuel_form(refuel)

    def _on_table_double_click(self, item_dict: dict):
        refuel = self.fuel_repo.get_by_id(int(item_dict["id"]))
        if refuel:
            self._show_refuel_form(refuel)

    def _delete_selected_refuel(self):
        sel = self.table.get_selected()
        if not sel:
            messagebox.showinfo("Select Record", "Please select a refuelling record to delete.")
            return
        if not messagebox.askyesno(
            "Confirm Deletion", "Are you sure you want to delete this refuelling entry?"
        ):
            return
        self.fuel_repo.delete(int(sel["id"]))
        ToastNotification.show(self, "Refuelling entry deleted.", "info")
        self.refresh_data()
        self.on_data_changed()

    def _show_refuel_form(self, refuel: Optional[Refuel]):
        dlg = tk.Toplevel(self)
        is_edit = refuel is not None
        dlg.title("Edit Refuelling Record" if is_edit else "Log New Refuelling")
        dlg.geometry("450x550")
        dlg.configure(bg=DARK_THEME["bg_root"])
        dlg.grab_set()

        content = ttk.Frame(dlg, style="Card.TFrame", padding=20)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(
            content,
            text="EDIT REFUELLING DETAILS" if is_edit else "NEW REFUELLING ENTRY",
            style="CardTitle.TLabel",
            font=FONTS["h3"],
        ).pack(anchor="w", pady=(0, 16))

        # Defaults
        vid = self.get_active_vehicle_id()
        vehicle = self.vehicle_repo.get_by_id(vid)
        curr_odo = vehicle.current_odometer if vehicle else 1000.0

        today_str = date.today().isoformat()
        init_date = refuel.date if is_edit else today_str
        init_odo = str(refuel.odometer) if is_edit else str(curr_odo)
        init_qty = str(refuel.fuel_quantity) if is_edit else "5.0"
        init_price = str(refuel.price_per_litre) if is_edit else "102.50"
        init_station = refuel.petrol_station if is_edit else "Indian Oil"
        init_notes = refuel.notes if is_edit else ""
        init_full = refuel.is_full_tank if is_edit else 1

        fields = [
            ("Date (YYYY-MM-DD)", "date", init_date),
            ("Odometer Reading (km)", "odo", init_odo),
            ("Fuel Quantity (Litres)", "qty", init_qty),
            ("Price per Litre (₹)", "price", init_price),
            ("Petrol Station", "station", init_station),
            ("Notes", "notes", init_notes),
        ]

        entries: dict = {}
        for lbl_text, key, val in fields:
            rf = ttk.Frame(content, style="Card.TFrame")
            rf.pack(fill="x", pady=4)
            ttk.Label(rf, text=lbl_text, style="CardDim.TLabel", width=20).pack(side="left")
            ent = ttk.Entry(rf)
            ent.insert(0, val)
            ent.pack(side="right", fill="x", expand=True)
            entries[key] = ent

        # Full Tank Checkbox
        tank_f = ttk.Frame(content, style="Card.TFrame")
        tank_f.pack(fill="x", pady=8)
        ttk.Label(tank_f, text="Refill Type:", style="CardDim.TLabel", width=20).pack(side="left")
        full_tank_var = tk.IntVar(value=init_full)
        chk = ttk.Checkbutton(
            tank_f,
            text="Full Tank (Recommended for accurate mileage)",
            variable=full_tank_var,
        )
        chk.pack(side="left")

        # Live calculated cost display
        cost_preview_f = tk.Frame(content, bg=DARK_THEME["bg_card_inner"], padx=10, pady=8)
        cost_preview_f.pack(fill="x", pady=(10, 0))
        lbl_calc_cost = tk.Label(
            cost_preview_f,
            text="Estimated Total: ₹ 0.00",
            bg=DARK_THEME["bg_card_inner"],
            fg=DARK_THEME["text_primary"],
            font=FONTS["body_bold"],
        )
        lbl_calc_cost.pack()

        def update_cost_preview(*args):
            try:
                q = float(entries["qty"].get())
                p = float(entries["price"].get())
                lbl_calc_cost.config(text=f"Total Cost: ₹ {calculate_fuel_cost(q, p):,.2f}")
            except Exception:
                lbl_calc_cost.config(text="Total Cost: --")

        entries["qty"].bind("<KeyRelease>", update_cost_preview)
        entries["price"].bind("<KeyRelease>", update_cost_preview)
        update_cost_preview()

        def save():
            try:
                d_str = entries["date"].get().strip()
                odo_val = float(entries["odo"].get())
                qty_val = float(entries["qty"].get())
                price_val = float(entries["price"].get())
                station_val = entries["station"].get().strip()
                notes_val = entries["notes"].get().strip()
                is_full = full_tank_var.get()

                if qty_val <= 0 or price_val <= 0:
                    messagebox.showerror("Error", "Quantity and price must be positive.")
                    return

                total_amt = calculate_fuel_cost(qty_val, price_val)

                if is_edit and refuel:
                    refuel.date = d_str
                    refuel.odometer = odo_val
                    refuel.fuel_quantity = qty_val
                    refuel.price_per_litre = price_val
                    refuel.total_amount = total_amt
                    refuel.petrol_station = station_val
                    refuel.is_full_tank = is_full
                    refuel.notes = notes_val
                    self.fuel_repo.update(refuel)
                    ToastNotification.show(self, "Refuelling updated successfully!", "success")
                else:
                    new_refuel = Refuel(
                        id=None,
                        vehicle_id=vid,
                        date=d_str,
                        odometer=odo_val,
                        fuel_quantity=qty_val,
                        price_per_litre=price_val,
                        total_amount=total_amt,
                        petrol_station=station_val,
                        is_full_tank=is_full,
                        notes=notes_val,
                    )
                    self.fuel_repo.add(new_refuel)
                    ToastNotification.show(self, "Refuelling logged successfully!", "success")

                dlg.destroy()
                self.refresh_data()
                self.on_data_changed()
            except ValueError as e:
                messagebox.showerror("Validation Error", str(e))

        # Buttons
        btn_box = ttk.Frame(content, style="Card.TFrame")
        btn_box.pack(fill="x", pady=(20, 0))

        ttk.Button(btn_box, text="Save Refuelling", style="Primary.TButton", command=save).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(btn_box, text="Cancel", style="Outline.TButton", command=dlg.destroy).pack(
            side="right"
        )

