"""
HF Deluxe Pro Manager - Maintenance and Servicing Page
Tracks scheduled services, parts replacements, service costs, and maintenance reminders.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List
from datetime import date
from ui.styles import DARK_THEME, FONTS
from ui.components import StatCard, ScrollableFrame, SectionHeader, DataTable, ToastNotification
from models.maintenance import ServiceRecord, ServicePart, MaintenanceRepository
from models.vehicle import VehicleRepository
from services.maintenance_calculator import DEFAULT_SERVICE_INTERVALS


class MaintenancePage(ttk.Frame):
    """Maintenance & Servicing Page."""

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

        self.maint_repo = MaintenanceRepository()
        self.vehicle_repo = VehicleRepository()

        self._build_ui()

    def _build_ui(self):
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        content = self.scroll.scrollable_content

        # Header
        header = SectionHeader(
            content,
            title="MAINTENANCE & SERVICING",
            subtitle="Workshop records, replacement parts, and scheduled maintenance alerts",
            action_text="+ Log New Service",
            action_callback=self._open_add_service_dialog,
        )
        header.pack(fill="x", padx=16, pady=16)

        # Maintenance Reminders Box
        self.reminders_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        self.reminders_card.pack(fill="x", padx=16, pady=(0, 16))

        rem_head = ttk.Frame(self.reminders_card, style="Card.TFrame")
        rem_head.pack(fill="x", pady=(0, 10))

        ttk.Label(
            rem_head,
            text="UPCOMING & OVERDUE SERVICE SCHEDULE",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(side="left")

        self.reminders_grid = ttk.Frame(self.reminders_card, style="Card.TFrame")
        self.reminders_grid.pack(fill="x")

        # Service History Table Card
        table_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        table_card.pack(fill="both", expand=True, padx=16, pady=(0, 20))

        tb_head = ttk.Frame(table_card, style="Card.TFrame")
        tb_head.pack(fill="x", pady=(0, 12))

        ttk.Label(
            tb_head,
            text="SERVICE HISTORY & PARTS REPLACEMENTS",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(side="left")

        # Category filter combo
        filter_f = ttk.Frame(tb_head, style="Card.TFrame")
        filter_f.pack(side="right")

        ttk.Label(filter_f, text="Category:", style="CardDim.TLabel").pack(side="left", padx=(0, 6))
        self.cat_var = tk.StringVar(value="All")
        categories = ["All"] + list(DEFAULT_SERVICE_INTERVALS.keys())
        self.combo_cat = ttk.Combobox(
            filter_f, textvariable=self.cat_var, values=categories, state="readonly", width=22
        )
        self.combo_cat.pack(side="left", padx=(0, 12))
        self.combo_cat.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        ttk.Button(
            filter_f,
            text="Delete Selected",
            style="Outline.TButton",
            command=self._delete_selected_service,
        ).pack(side="left")

        cols = [
            ("service_date", "Date", 100),
            ("odometer", "Odometer (km)", 110),
            ("category", "Service Category", 160),
            ("description", "Description", 180),
            ("labour_charges", "Labour (₹)", 90),
            ("parts_charges", "Parts (₹)", 90),
            ("total_expenditure", "Total (₹)", 100),
            ("workshop_name", "Workshop / Mechanic", 150),
            ("parts_count", "Parts Replaced", 110),
        ]

        self.table = DataTable(table_card, columns=cols, show_search=True)
        self.table.pack(fill="both", expand=True)

    def refresh_data(self):
        """Update reminders and service history table."""
        vid = self.get_active_vehicle_id()

        # 1. Reminders
        reminders = self.maint_repo.get_maintenance_reminders(vid)
        for w in self.reminders_grid.winfo_children():
            w.destroy()

        if not reminders:
            ttk.Label(
                self.reminders_grid, text="All systems running smoothly! No maintenance due.", style="CardDim.TLabel"
            ).pack(pady=6)
        else:
            for idx, r in enumerate(reminders):
                row_f = tk.Frame(self.reminders_grid, bg=DARK_THEME["bg_card_inner"], padx=12, pady=6)
                row_f.pack(fill="x", pady=2)

                tk.Label(
                    row_f,
                    text=f" {r.status.upper()} ",
                    bg=r.status_color,
                    fg="#ffffff",
                    font=("Segoe UI", 8, "bold"),
                    padx=4,
                ).pack(side="left", padx=(0, 10))

                tk.Label(
                    row_f,
                    text=r.part_name,
                    bg=DARK_THEME["bg_card_inner"],
                    fg=DARK_THEME["text_primary"],
                    font=FONTS["body_bold"],
                ).pack(side="left")

                due_text = ""
                if r.km_remaining is not None:
                    if r.km_remaining <= 0:
                        due_text = f"Overdue by {-r.km_remaining:.0f} km"
                    else:
                        due_text = f"Due in {r.km_remaining:.0f} km (at {r.next_due_odometer:,.0f} km)"
                if r.days_remaining is not None:
                    if r.days_remaining <= 0:
                        due_text += f" | {-r.days_remaining} days overdue"
                    else:
                        due_text += f" | in {r.days_remaining} days"

                tk.Label(
                    row_f,
                    text=due_text,
                    bg=DARK_THEME["bg_card_inner"],
                    fg=DARK_THEME["text_secondary"],
                    font=FONTS["caption"],
                ).pack(side="right")

        # 2. Table
        selected_cat = self.cat_var.get()
        services = self.maint_repo.get_services_by_vehicle(vid, category=selected_cat)
        table_rows = []
        for s in services:
            parts_summary = f"{len(s.parts)} parts" if s.parts else "None"
            table_rows.append(
                {
                    "id": s.id,
                    "service_date": s.service_date,
                    "odometer": f"{s.odometer:,.1f}",
                    "category": s.category,
                    "description": s.description or "--",
                    "labour_charges": f"{s.labour_charges:,.2f}",
                    "parts_charges": f"{s.parts_charges:,.2f}",
                    "total_expenditure": f"{s.total_expenditure:,.2f}",
                    "workshop_name": s.workshop_name or "--",
                    "parts_count": parts_summary,
                }
            )
        self.table.set_data(table_rows)

    def _open_add_service_dialog(self):
        self._show_service_dialog()

    def _delete_selected_service(self):
        sel = self.table.get_selected()
        if not sel:
            messagebox.showinfo("Select Service", "Please select a service record to delete.")
            return
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this service record?"):
            return
        self.maint_repo.delete_service(int(sel["id"]))
        ToastNotification.show(self, "Service record deleted.", "info")
        self.refresh_data()
        self.on_data_changed()

    def _show_service_dialog(self):
        dlg = tk.Toplevel(self)
        dlg.title("Log Maintenance Service")
        dlg.geometry("560x700")
        dlg.configure(bg=DARK_THEME["bg_root"])
        dlg.grab_set()

        content = ttk.Frame(dlg, style="Card.TFrame", padding=20)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(
            content, text="RECORD MAINTENANCE & SERVICING", style="CardTitle.TLabel", font=FONTS["h3"]
        ).pack(anchor="w", pady=(0, 16))

        vid = self.get_active_vehicle_id()
        vehicle = self.vehicle_repo.get_by_id(vid)
        curr_odo = str(vehicle.current_odometer if vehicle else 1000.0)

        # Service Form fields
        f_date = ttk.Frame(content, style="Card.TFrame")
        f_date.pack(fill="x", pady=3)
        ttk.Label(f_date, text="Service Date (YYYY-MM-DD):", style="CardDim.TLabel", width=24).pack(side="left")
        e_date = ttk.Entry(f_date)
        e_date.insert(0, date.today().isoformat())
        e_date.pack(side="right", fill="x", expand=True)

        f_odo = ttk.Frame(content, style="Card.TFrame")
        f_odo.pack(fill="x", pady=3)
        ttk.Label(f_odo, text="Odometer Reading (km):", style="CardDim.TLabel", width=24).pack(side="left")
        e_odo = ttk.Entry(f_odo)
        e_odo.insert(0, curr_odo)
        e_odo.pack(side="right", fill="x", expand=True)

        f_cat = ttk.Frame(content, style="Card.TFrame")
        f_cat.pack(fill="x", pady=3)
        ttk.Label(f_cat, text="Service Category:", style="CardDim.TLabel", width=24).pack(side="left")
        cb_cat = ttk.Combobox(f_cat, values=list(DEFAULT_SERVICE_INTERVALS.keys()), state="readonly")
        cb_cat.current(0)
        cb_cat.pack(side="right", fill="x", expand=True)

        f_desc = ttk.Frame(content, style="Card.TFrame")
        f_desc.pack(fill="x", pady=3)
        ttk.Label(f_desc, text="Description:", style="CardDim.TLabel", width=24).pack(side="left")
        e_desc = ttk.Entry(f_desc)
        e_desc.insert(0, "Periodic service and inspection")
        e_desc.pack(side="right", fill="x", expand=True)

        f_shop = ttk.Frame(content, style="Card.TFrame")
        f_shop.pack(fill="x", pady=3)
        ttk.Label(f_shop, text="Workshop / Mechanic:", style="CardDim.TLabel", width=24).pack(side="left")
        e_shop = ttk.Entry(f_shop)
        e_shop.insert(0, "Hero Service Center")
        e_shop.pack(side="right", fill="x", expand=True)

        f_labour = ttk.Frame(content, style="Card.TFrame")
        f_labour.pack(fill="x", pady=3)
        ttk.Label(f_labour, text="Labour Charges (₹):", style="CardDim.TLabel", width=24).pack(side="left")
        e_labour = ttk.Entry(f_labour)
        e_labour.insert(0, "250.0")
        e_labour.pack(side="right", fill="x", expand=True)

        # Replacement Parts Section
        parts_box = ttk.Frame(content, style="Card.TFrame")
        parts_box.pack(fill="both", expand=True, pady=(12, 0))

        ttk.Label(parts_box, text="REPLACEMENT PARTS (OPTIONAL):", style="CardTitle.TLabel", font=FONTS["caption"]).pack(anchor="w", pady=(0, 6))

        p_list_frame = tk.Frame(parts_box, bg=DARK_THEME["bg_card_inner"], padx=8, pady=8)
        p_list_frame.pack(fill="both", expand=True)

        added_parts: List[ServicePart] = []
        lbl_parts_summary = tk.Label(
            p_list_frame, text="No parts added yet.", bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_secondary"], font=FONTS["caption"]
        )
        lbl_parts_summary.pack(anchor="w")

        def refresh_parts_display():
            if not added_parts:
                lbl_parts_summary.config(text="No parts added yet.")
            else:
                summary = "\n".join(f"• {p.part_name} (x{p.quantity}) - ₹{p.total_price:.2f}" for p in added_parts)
                lbl_parts_summary.config(text=summary)

        def add_part_subform():
            p_win = tk.Toplevel(dlg)
            p_win.title("Add Replacement Part")
            p_win.geometry("380x360")
            p_win.configure(bg=DARK_THEME["bg_root"])
            p_win.grab_set()

            p_content = ttk.Frame(p_win, style="Card.TFrame", padding=16)
            p_content.pack(fill="both", expand=True, padx=12, pady=12)

            ttk.Label(p_content, text="ADD PART DETAILS", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 10))

            f1 = ttk.Frame(p_content, style="Card.TFrame"); f1.pack(fill="x", pady=2)
            ttk.Label(f1, text="Part Name:", style="CardDim.TLabel", width=16).pack(side="left")
            p_name = ttk.Entry(f1); p_name.pack(side="right", fill="x", expand=True)

            f2 = ttk.Frame(p_content, style="Card.TFrame"); f2.pack(fill="x", pady=2)
            ttk.Label(f2, text="Quantity:", style="CardDim.TLabel", width=16).pack(side="left")
            p_qty = ttk.Entry(f2); p_qty.insert(0, "1"); p_qty.pack(side="right", fill="x", expand=True)

            f3 = ttk.Frame(p_content, style="Card.TFrame"); f3.pack(fill="x", pady=2)
            ttk.Label(f3, text="Unit Price (₹):", style="CardDim.TLabel", width=16).pack(side="left")
            p_price = ttk.Entry(f3); p_price.insert(0, "350.0"); p_price.pack(side="right", fill="x", expand=True)

            f4 = ttk.Frame(p_content, style="Card.TFrame"); f4.pack(fill="x", pady=2)
            ttk.Label(f4, text="Interval (km):", style="CardDim.TLabel", width=16).pack(side="left")
            p_km = ttk.Entry(f4); p_km.insert(0, "3000"); p_km.pack(side="right", fill="x", expand=True)

            f5 = ttk.Frame(p_content, style="Card.TFrame"); f5.pack(fill="x", pady=2)
            ttk.Label(f5, text="Interval (months):", style="CardDim.TLabel", width=16).pack(side="left")
            p_mon = ttk.Entry(f5); p_mon.insert(0, "6"); p_mon.pack(side="right", fill="x", expand=True)

            def save_part():
                name_str = p_name.get().strip()
                if not name_str:
                    messagebox.showerror("Error", "Part name is required.")
                    return
                try:
                    q = int(p_qty.get())
                    pr = float(p_price.get())
                    km_int = float(p_km.get()) if p_km.get().strip() else None
                    mon_int = int(p_mon.get()) if p_mon.get().strip() else None
                    current_odo_val = float(e_odo.get())
                    next_odo = (current_odo_val + km_int) if km_int else None

                    added_parts.append(
                        ServicePart(
                            id=None,
                            vehicle_id=vid,
                            part_name=name_str,
                            quantity=q,
                            unit_price=pr,
                            total_price=round(q * pr, 2),
                            replacement_date=e_date.get().strip(),
                            next_recommended_odometer=next_odo,
                            replacement_interval_km=km_int,
                            replacement_interval_months=mon_int,
                        )
                    )
                    refresh_parts_display()
                    p_win.destroy()
                except ValueError as err:
                    messagebox.showerror("Error", f"Invalid input: {err}")

            ttk.Button(p_content, text="Add Part", style="Primary.TButton", command=save_part).pack(pady=(16, 0))

        ttk.Button(parts_box, text="+ Add Replacement Part", style="Outline.TButton", command=add_part_subform).pack(anchor="w", pady=(6, 0))

        def save_service():
            try:
                s_date = e_date.get().strip()
                s_odo = float(e_odo.get())
                s_cat = cb_cat.get()
                s_desc = e_desc.get().strip()
                s_shop = e_shop.get().strip()
                s_labour = float(e_labour.get())

                record = ServiceRecord(
                    id=None,
                    vehicle_id=vid,
                    service_date=s_date,
                    odometer=s_odo,
                    category=s_cat,
                    description=s_desc,
                    labour_charges=s_labour,
                    parts_charges=0.0,
                    total_expenditure=0.0,
                    workshop_name=s_shop,
                )
                self.maint_repo.add_service(record, added_parts)
                ToastNotification.show(self, "Service recorded successfully!", "success")
                dlg.destroy()
                self.refresh_data()
                self.on_data_changed()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

        btn_box = ttk.Frame(content, style="Card.TFrame")
        btn_box.pack(fill="x", pady=(20, 0))
        ttk.Button(btn_box, text="Save Service Record", style="Primary.TButton", command=save_service).pack(side="right", padx=(8, 0))
        ttk.Button(btn_box, text="Cancel", style="Outline.TButton", command=dlg.destroy).pack(side="right")

