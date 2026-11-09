"""
HF Deluxe Pro Manager - Parts and Upgrades Page
Manages aftermarket accessories, aesthetic and functional modifications, and upgrade expenditure.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from datetime import date
from ui.styles import DARK_THEME, FONTS
from ui.components import StatCard, ScrollableFrame, SectionHeader, DataTable, ToastNotification
from models.upgrades import Upgrade, UpgradeRepository
from models.vehicle import VehicleRepository


UPGRADE_CATEGORIES = [
    "All",
    "Lighting modifications",
    "Luggage accessories",
    "Mirrors",
    "Seat modifications",
    "Electrical accessories",
    "Crash guards & Protection",
    "Exhaust & Performance",
    "Other aftermarket components",
]


class UpgradesPage(ttk.Frame):
    """Parts and Upgrades Page."""

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

        self.upgrade_repo = UpgradeRepository()
        self.vehicle_repo = VehicleRepository()

        self._build_ui()

    def _build_ui(self):
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        content = self.scroll.scrollable_content

        # Header
        header = SectionHeader(
            content,
            title="PARTS & AFTERMARKET UPGRADES",
            subtitle="Custom modifications, accessories, and aesthetic enhancements",
            action_text="+ Add New Upgrade",
            action_callback=self._open_add_upgrade_dialog,
        )
        header.pack(fill="x", padx=16, pady=16)

        # Stat cards row
        stats_row = ttk.Frame(content, style="TFrame")
        stats_row.pack(fill="x", padx=16, pady=(0, 16))
        for i in range(3):
            stats_row.columnconfigure(i, weight=1)

        self.card_total_cost = StatCard(
            stats_row,
            title="Total Upgrades Spend",
            value="₹ --",
            subtitle="Aftermarket investment",
            accent_color="#f59e0b",
            icon_text="✨",
        )
        self.card_total_cost.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        self.card_count = StatCard(
            stats_row,
            title="Installed Modifications",
            value="0 Upgrades",
            subtitle="Chronological log",
            accent_color="#0284c7",
            icon_text="🔧",
        )
        self.card_count.grid(row=0, column=1, padx=4, sticky="nsew")

        self.card_latest_mod = StatCard(
            stats_row,
            title="Latest Modification",
            value="--",
            subtitle="Most recent install",
            accent_color="#10b981",
            icon_text="🏍️",
        )
        self.card_latest_mod.grid(row=0, column=2, padx=(8, 0), sticky="nsew")

        # Table section
        table_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        table_card.pack(fill="both", expand=True, padx=16, pady=(0, 20))

        tb_head = ttk.Frame(table_card, style="Card.TFrame")
        tb_head.pack(fill="x", pady=(0, 12))

        ttk.Label(
            tb_head,
            text="CHRONOLOGICAL MODIFICATION HISTORY",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(side="left")

        filter_box = ttk.Frame(tb_head, style="Card.TFrame")
        filter_box.pack(side="right")

        ttk.Label(filter_box, text="Category:", style="CardDim.TLabel").pack(side="left", padx=(0, 6))
        self.cat_var = tk.StringVar(value="All")
        self.combo_cat = ttk.Combobox(
            filter_box, textvariable=self.cat_var, values=UPGRADE_CATEGORIES, state="readonly", width=22
        )
        self.combo_cat.pack(side="left", padx=(0, 12))
        self.combo_cat.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        ttk.Button(
            filter_box,
            text="Delete Selected",
            style="Outline.TButton",
            command=self._delete_selected_upgrade,
        ).pack(side="left")

        cols = [
            ("installation_date", "Install Date", 100),
            ("upgrade_name", "Upgrade / Modification", 160),
            ("category", "Category", 140),
            ("cost", "Cost (₹)", 90),
            ("odometer", "Odometer (km)", 110),
            ("vendor", "Vendor / Workshop", 140),
            ("description", "Description", 180),
            ("notes", "Notes", 140),
        ]

        self.table = DataTable(table_card, columns=cols, show_search=True)
        self.table.pack(fill="both", expand=True)

    def refresh_data(self):
        """Update stat cards and table with latest upgrade records."""
        vid = self.get_active_vehicle_id()
        selected_cat = self.cat_var.get()
        upgrades = self.upgrade_repo.get_by_vehicle(vid, category=selected_cat)
        all_upgrades = self.upgrade_repo.get_by_vehicle(vid)

        total_spent = sum(u.cost for u in all_upgrades)
        self.card_total_cost.update_value(f"₹ {total_spent:,.2f}")
        self.card_count.update_value(f"{len(all_upgrades)} Items", "Across all categories")

        if all_upgrades:
            latest = all_upgrades[0]
            self.card_latest_mod.update_value(latest.upgrade_name, f"₹{latest.cost:,.0f} on {latest.installation_date}")
        else:
            self.card_latest_mod.update_value("--", "No modifications yet")

        table_rows = []
        for u in upgrades:
            table_rows.append(
                {
                    "id": u.id,
                    "installation_date": u.installation_date,
                    "upgrade_name": u.upgrade_name,
                    "category": u.category,
                    "cost": f"{u.cost:,.2f}",
                    "odometer": f"{u.odometer:,.0f}" if u.odometer is not None else "--",
                    "vendor": u.vendor or "--",
                    "description": u.description or "--",
                    "notes": u.notes or "--",
                }
            )
        self.table.set_data(table_rows)

    def _open_add_upgrade_dialog(self):
        self._show_upgrade_dialog()

    def _delete_selected_upgrade(self):
        sel = self.table.get_selected()
        if not sel:
            messagebox.showinfo("Select Upgrade", "Please select an upgrade to delete.")
            return
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this upgrade record?"):
            return
        self.upgrade_repo.delete(int(sel["id"]))
        ToastNotification.show(self, "Upgrade removed.", "info")
        self.refresh_data()
        self.on_data_changed()

    def _show_upgrade_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Add Aftermarket Upgrade")
        dlg.geometry("480x560")
        dlg.configure(bg=DARK_THEME["bg_root"])
        dlg.grab_set()

        content = ttk.Frame(dlg, style="Card.TFrame", padding=20)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(
            content, text="RECORD MOTORCYCLE MODIFICATION", style="CardTitle.TLabel", font=FONTS["h3"]
        ).pack(anchor="w", pady=(0, 16))

        vid = self.get_active_vehicle_id()
        vehicle = self.vehicle_repo.get_by_id(vid)
        curr_odo = str(vehicle.current_odometer if vehicle else 1000.0)

        # Form fields
        fields = [
            ("Upgrade Name", "name", "LED Auxiliary Fog Lamps"),
            ("Category", "cat", "Lighting modifications"),
            ("Installation Date", "date", date.today().isoformat()),
            ("Odometer (km)", "odo", curr_odo),
            ("Cost (₹)", "cost", "1200.0"),
            ("Workshop / Vendor", "vendor", "Auto Accessories Mart"),
            ("Description", "desc", "Dual 20W LED pods with clamp and handlebar switch"),
            ("Notes", "notes", ""),
        ]

        entries: dict = {}
        for lbl_text, key, val in fields:
            rf = ttk.Frame(content, style="Card.TFrame")
            rf.pack(fill="x", pady=4)
            ttk.Label(rf, text=lbl_text, style="CardDim.TLabel", width=20).pack(side="left")

            if key == "cat":
                cb = ttk.Combobox(rf, values=UPGRADE_CATEGORIES[1:], state="readonly")
                cb.set(val)
                cb.pack(side="right", fill="x", expand=True)
                entries[key] = cb
            else:
                ent = ttk.Entry(rf)
                ent.insert(0, val)
                ent.pack(side="right", fill="x", expand=True)
                entries[key] = ent

        def save():
            try:
                name = entries["name"].get().strip()
                cat = entries["cat"].get().strip()
                inst_date = entries["date"].get().strip()
                odo_val = float(entries["odo"].get()) if entries["odo"].get().strip() else None
                cost_val = float(entries["cost"].get())
                vendor = entries["vendor"].get().strip()
                desc = entries["desc"].get().strip()
                notes = entries["notes"].get().strip()

                if not name:
                    messagebox.showerror("Error", "Upgrade name is required.")
                    return
                if cost_val < 0:
                    messagebox.showerror("Error", "Cost cannot be negative.")
                    return

                upg = Upgrade(
                    id=None,
                    vehicle_id=vid,
                    upgrade_name=name,
                    category=cat,
                    description=desc,
                    installation_date=inst_date,
                    odometer=odo_val,
                    cost=cost_val,
                    vendor=vendor,
                    notes=notes,
                )
                self.upgrade_repo.add(upg)
                ToastNotification.show(self, "Upgrade added successfully!", "success")
                dlg.destroy()
                self.refresh_data()
                self.on_data_changed()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        btn_box = ttk.Frame(content, style="Card.TFrame")
        btn_box.pack(fill="x", pady=(20, 0))
        ttk.Button(btn_box, text="Save Upgrade", style="Primary.TButton", command=save).pack(side="right", padx=(8, 0))
        ttk.Button(btn_box, text="Cancel", style="Outline.TButton", command=dlg.destroy).pack(side="right")

