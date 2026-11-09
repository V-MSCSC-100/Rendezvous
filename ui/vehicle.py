"""
HF Deluxe Pro Manager - Vehicle Management Page
Allows registering, viewing, editing, and managing multiple motorcycles.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
from ui.styles import DARK_THEME, FONTS
from ui.components import ScrollableFrame, SectionHeader, ToastNotification
from models.vehicle import Vehicle, VehicleRepository
from models.expense import ExpenseRepository


class VehiclePage(ttk.Frame):
    """My Vehicle page."""

    def __init__(
        self,
        parent: tk.Widget,
        get_active_vehicle_id: Callable[[], int],
        set_active_vehicle_id: Callable[[int], None],
        on_vehicle_updated: Callable[[], None],
        **kwargs,
    ):
        super().__init__(parent, style="TFrame", **kwargs)
        self.get_active_vehicle_id = get_active_vehicle_id
        self.set_active_vehicle_id = set_active_vehicle_id
        self.on_vehicle_updated = on_vehicle_updated

        self.vehicle_repo = VehicleRepository()
        self.expense_repo = ExpenseRepository()

        self._build_ui()

    def _build_ui(self):
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        content = self.scroll.scrollable_content

        # Header
        header = SectionHeader(
            content,
            title="MY VEHICLE",
            subtitle="Vehicle specifications, registration, and fleet management",
            action_text="+ Add New Motorcycle",
            action_callback=self._open_add_vehicle_dialog,
        )
        header.pack(fill="x", padx=16, pady=16)

        # Vehicle Selector Bar
        selector_card = ttk.Frame(content, style="Card.TFrame", padding=12)
        selector_card.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Label(selector_card, text="Select Active Motorcycle:", style="CardTitle.TLabel").pack(
            side="left", padx=(0, 10)
        )

        self.vehicle_var = tk.StringVar()
        self.combo_vehicles = ttk.Combobox(
            selector_card, textvariable=self.vehicle_var, state="readonly", width=36
        )
        self.combo_vehicles.pack(side="left", padx=(0, 12))
        self.combo_vehicles.bind("<<ComboboxSelected>>", self._on_vehicle_selected)

        ttk.Button(
            selector_card,
            text="Set as Default",
            style="Outline.TButton",
            command=self._set_current_as_default,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            selector_card,
            text="Edit Vehicle",
            style="Secondary.TButton",
            command=self._open_edit_vehicle_dialog,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            selector_card,
            text="Delete Vehicle",
            style="Outline.TButton",
            command=self._delete_current_vehicle,
        ).pack(side="right")

        # Main Info Grid
        info_grid = ttk.Frame(content, style="TFrame")
        info_grid.pack(fill="x", padx=16, pady=(0, 16))
        info_grid.columnconfigure(0, weight=3)
        info_grid.columnconfigure(1, weight=2)

        # Left Column: Detailed Specifications Card
        self.profile_card = ttk.Frame(info_grid, style="Card.TFrame", padding=20)
        self.profile_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")

        ttk.Label(
            self.profile_card,
            text="VEHICLE PROFILE & SPECIFICATIONS",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(anchor="w", pady=(0, 14))

        self.spec_labels: dict = {}
        specs = [
            ("Vehicle Name", "name"),
            ("Manufacturer", "manufacturer"),
            ("Model", "model"),
            ("Registration Number", "registration_number"),
            ("Purchase Date", "purchase_date"),
            ("Purchase Price", "purchase_price"),
            ("Current Odometer", "current_odometer"),
            ("Engine Capacity", "engine_capacity"),
            ("Fuel Type", "fuel_type"),
            ("Status", "is_default"),
            ("Notes", "notes"),
        ]

        for title, key in specs:
            row_frame = tk.Frame(self.profile_card, bg=DARK_THEME["bg_card"])
            row_frame.pack(fill="x", pady=4)

            tk.Label(
                row_frame,
                text=title,
                bg=DARK_THEME["bg_card"],
                fg=DARK_THEME["text_secondary"],
                font=FONTS["body_bold"],
                width=20,
                anchor="w",
            ).pack(side="left")

            val_lbl = tk.Label(
                row_frame,
                text="--",
                bg=DARK_THEME["bg_card"],
                fg=DARK_THEME["text_primary"],
                font=FONTS["body"],
                anchor="w",
            )
            val_lbl.pack(side="left", fill="x", expand=True)
            self.spec_labels[key] = val_lbl

        # Right Column: Ownership Financial Summary Card
        self.exp_card = ttk.Frame(info_grid, style="Card.TFrame", padding=20)
        self.exp_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")

        ttk.Label(
            self.exp_card,
            text="OWNERSHIP EXPENDITURE BREAKDOWN",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(anchor="w", pady=(0, 14))

        self.fin_labels: dict = {}
        fin_items = [
            ("Purchase Price", "purchase_price", DARK_THEME["text_primary"]),
            ("Fuel Expenditure", "fuel", "#10b981"),
            ("Routine Maintenance", "maintenance", "#0284c7"),
            ("Aftermarket Upgrades", "upgrades", "#f59e0b"),
            ("Miscellaneous Expenses", "misc", DARK_THEME["text_secondary"]),
            ("Total Operational", "operational", DARK_THEME["text_primary"]),
            ("Total Lifetime Ownership", "total", DARK_THEME["primary"]),
            ("Average Running Cost", "cost_km", "#38bdf8"),
        ]

        for title, key, color in fin_items:
            rf = tk.Frame(self.exp_card, bg=DARK_THEME["bg_card"])
            rf.pack(fill="x", pady=6)

            tk.Label(
                rf,
                text=title,
                bg=DARK_THEME["bg_card"],
                fg=DARK_THEME["text_secondary"],
                font=FONTS["body"],
                anchor="w",
            ).pack(side="left")

            v_lbl = tk.Label(
                rf,
                text="₹ --",
                bg=DARK_THEME["bg_card"],
                fg=color,
                font=FONTS["body_bold"],
                anchor="e",
            )
            v_lbl.pack(side="right")
            self.fin_labels[key] = v_lbl

    def refresh_data(self):
        """Reload vehicle list and details from database."""
        vehicles = self.vehicle_repo.get_all()
        if not vehicles:
            return

        active_id = self.get_active_vehicle_id()
        options = [f"{v.id}: {v.manufacturer} {v.model} ({v.registration_number})" for v in vehicles]
        self.combo_vehicles["values"] = options

        # Set selection to match active_id
        selected_idx = 0
        for i, v in enumerate(vehicles):
            if v.id == active_id:
                selected_idx = i
                break
        self.combo_vehicles.current(selected_idx)

        # Update profile display
        vehicle = vehicles[selected_idx]
        self.spec_labels["name"].config(text=vehicle.name)
        self.spec_labels["manufacturer"].config(text=vehicle.manufacturer)
        self.spec_labels["model"].config(text=vehicle.model)
        self.spec_labels["registration_number"].config(text=vehicle.registration_number)
        self.spec_labels["purchase_date"].config(text=vehicle.purchase_date)
        self.spec_labels["purchase_price"].config(text=f"₹ {vehicle.purchase_price:,.2f}")
        self.spec_labels["current_odometer"].config(text=f"{vehicle.current_odometer:,.1f} km")
        self.spec_labels["engine_capacity"].config(text=f"{vehicle.engine_capacity:.1f} cc")
        self.spec_labels["fuel_type"].config(text=vehicle.fuel_type)
        self.spec_labels["is_default"].config(
            text="Default Vehicle ★" if vehicle.is_default else "Secondary Vehicle"
        )
        self.spec_labels["notes"].config(text=vehicle.notes or "--")

        # Update financial breakdown
        fin = self.expense_repo.get_full_financial_summary(vehicle.id)
        self.fin_labels["purchase_price"].config(text=f"₹ {vehicle.purchase_price:,.2f}")
        self.fin_labels["fuel"].config(text=f"₹ {fin.total_fuel:,.2f}")
        self.fin_labels["maintenance"].config(text=f"₹ {fin.total_maintenance:,.2f}")
        self.fin_labels["upgrades"].config(text=f"₹ {fin.total_upgrades:,.2f}")
        self.fin_labels["misc"].config(text=f"₹ {fin.total_misc:,.2f}")
        self.fin_labels["operational"].config(text=f"₹ {fin.total_operational:,.2f}")
        self.fin_labels["total"].config(text=f"₹ {fin.total_ownership:,.2f}")
        self.fin_labels["cost_km"].config(
            text=f"₹ {fin.cost_per_km:.2f} / km" if fin.cost_per_km > 0 else "--"
        )

    def _on_vehicle_selected(self, event):
        val = self.vehicle_var.get()
        if ":" in val:
            vid = int(val.split(":")[0])
            self.set_active_vehicle_id(vid)
            self.refresh_data()
            self.on_vehicle_updated()

    def _set_current_as_default(self):
        vid = self.get_active_vehicle_id()
        self.vehicle_repo.set_default(vid)
        ToastNotification.show(self, "Set as default vehicle!", "success")
        self.refresh_data()
        self.on_vehicle_updated()

    def _delete_current_vehicle(self):
        vid = self.get_active_vehicle_id()
        if not messagebox.askyesno(
            "Confirm Deletion",
            "Are you sure you want to delete this vehicle and all associated logs? This cannot be undone.",
        ):
            return
        try:
            self.vehicle_repo.delete(vid)
            # Switch to first remaining vehicle
            vehicles = self.vehicle_repo.get_all()
            if vehicles:
                self.set_active_vehicle_id(vehicles[0].id)
            ToastNotification.show(self, "Vehicle deleted successfully.", "info")
            self.refresh_data()
            self.on_vehicle_updated()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def _open_add_vehicle_dialog(self):
        self._show_vehicle_form_dialog(None)

    def _open_edit_vehicle_dialog(self):
        vid = self.get_active_vehicle_id()
        vehicle = self.vehicle_repo.get_by_id(vid)
        if vehicle:
            self._show_vehicle_form_dialog(vehicle)

    def _show_vehicle_form_dialog(self, vehicle: Optional[Vehicle]):
        dlg = tk.Toplevel(self)
        is_edit = vehicle is not None
        dlg.title("Edit Vehicle" if is_edit else "Add New Motorcycle")
        dlg.geometry("480x600")
        dlg.configure(bg=DARK_THEME["bg_root"])
        dlg.grab_set()

        content = ttk.Frame(dlg, style="Card.TFrame", padding=20)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(
            content,
            text="EDIT MOTORCYCLE DETAILS" if is_edit else "REGISTER NEW MOTORCYCLE",
            style="CardTitle.TLabel",
            font=FONTS["h3"],
        ).pack(anchor="w", pady=(0, 16))

        # Fields
        fields = [
            ("Vehicle Name", "name", vehicle.name if is_edit else "Hero HF Deluxe"),
            ("Manufacturer", "manufacturer", vehicle.manufacturer if is_edit else "Hero"),
            ("Model", "model", vehicle.model if is_edit else "HF Deluxe Pro"),
            ("Registration Number", "reg", vehicle.registration_number if is_edit else ""),
            ("Purchase Date (YYYY-MM-DD)", "date", vehicle.purchase_date if is_edit else "2023-01-15"),
            ("Purchase Price (₹)", "price", str(vehicle.purchase_price) if is_edit else "68000"),
            ("Current Odometer (km)", "odo", str(vehicle.current_odometer) if is_edit else "1000"),
            ("Engine Capacity (cc)", "cc", str(vehicle.engine_capacity) if is_edit else "97.2"),
            ("Fuel Type", "fuel", vehicle.fuel_type if is_edit else "Petrol"),
            ("Vehicle Notes", "notes", vehicle.notes if is_edit else ""),
        ]

        entries: dict = {}
        for label_text, key, init_val in fields:
            row_f = ttk.Frame(content, style="Card.TFrame")
            row_f.pack(fill="x", pady=4)

            ttk.Label(row_f, text=label_text, style="CardDim.TLabel", width=22).pack(side="left")
            ent = ttk.Entry(row_f)
            ent.insert(0, str(init_val))
            ent.pack(side="right", fill="x", expand=True)
            entries[key] = ent

        def save():
            try:
                name = entries["name"].get().strip()
                manufacturer = entries["manufacturer"].get().strip()
                model = entries["model"].get().strip()
                reg = entries["reg"].get().strip().upper()
                p_date = entries["date"].get().strip()
                price = float(entries["price"].get())
                odo = float(entries["odo"].get())
                cc = float(entries["cc"].get())
                fuel_type = entries["fuel"].get().strip()
                notes = entries["notes"].get().strip()

                if not name or not reg:
                    messagebox.showerror("Validation Error", "Name and Registration Number are required.")
                    return

                if is_edit and vehicle:
                    vehicle.name = name
                    vehicle.manufacturer = manufacturer
                    vehicle.model = model
                    vehicle.registration_number = reg
                    vehicle.purchase_date = p_date
                    vehicle.purchase_price = price
                    vehicle.current_odometer = odo
                    vehicle.engine_capacity = cc
                    vehicle.fuel_type = fuel_type
                    vehicle.notes = notes
                    self.vehicle_repo.update(vehicle)
                    ToastNotification.show(self, "Vehicle updated successfully!", "success")
                else:
                    new_v = Vehicle(
                        id=None,
                        name=name,
                        manufacturer=manufacturer,
                        model=model,
                        registration_number=reg,
                        purchase_date=p_date,
                        purchase_price=price,
                        current_odometer=odo,
                        engine_capacity=cc,
                        fuel_type=fuel_type,
                        notes=notes,
                        is_default=0,
                    )
                    new_id = self.vehicle_repo.create(new_v)
                    self.set_active_vehicle_id(new_id)
                    ToastNotification.show(self, "New motorcycle added!", "success")

                dlg.destroy()
                self.refresh_data()
                self.on_vehicle_updated()
            except ValueError as e:
                messagebox.showerror("Input Error", f"Please check your input values: {e}")

        # Buttons
        btn_box = ttk.Frame(content, style="Card.TFrame")
        btn_box.pack(fill="x", pady=(20, 0))

        ttk.Button(btn_box, text="Save Motorcycle", style="Primary.TButton", command=save).pack(
            side="right", padx=(8, 0)
        )
        ttk.Button(btn_box, text="Cancel", style="Outline.TButton", command=dlg.destroy).pack(
            side="right"
        )

