"""
HF Deluxe Pro Manager - Trip History and Actual Expenditure Page
Manages saved trips, marks trips as completed with actual vs estimated comparison,
and provides PDF report generation.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from ui.styles import DARK_THEME, FONTS
from ui.components import StatCard, ScrollableFrame, SectionHeader, DataTable, ToastNotification
from models.trips import Trip, TripRepository
from models.vehicle import VehicleRepository
from services.trip_calculator import compare_estimated_vs_actual


class TripHistoryPage(ttk.Frame):
    """Trip History and Reporting Page."""

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

        self.trip_repo = TripRepository()
        self.vehicle_repo = VehicleRepository()

        self._build_ui()

    def _build_ui(self):
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        content = self.scroll.scrollable_content

        # Header
        header = SectionHeader(
            content,
            title="TRIP HISTORY & ACTUAL EXPENDITURE",
            subtitle="Review journeys, mark completed rides, and compare estimated vs actual fuel expenditure",
        )
        header.pack(fill="x", padx=16, pady=16)

        # Stat cards row
        stats_row = ttk.Frame(content, style="TFrame")
        stats_row.pack(fill="x", padx=16, pady=(0, 16))
        for i in range(4):
            stats_row.columnconfigure(i, weight=1)

        self.card_total_trips = StatCard(
            stats_row,
            title="Total Planned Trips",
            value="0 Trips",
            subtitle="Touring history",
            accent_color="#0284c7",
            icon_text="🗺️",
        )
        self.card_total_trips.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        self.card_completed = StatCard(
            stats_row,
            title="Completed Rides",
            value="0 Done",
            subtitle="Ridden to destination",
            accent_color="#10b981",
            icon_text="🏁",
        )
        self.card_completed.grid(row=0, column=1, padx=4, sticky="nsew")

        self.card_touring_km = StatCard(
            stats_row,
            title="Touring Distance",
            value="0 km",
            subtitle="Completed journeys",
            accent_color="#f59e0b",
            icon_text="🏍️",
        )
        self.card_touring_km.grid(row=0, column=2, padx=4, sticky="nsew")

        self.card_avg_trip_cost = StatCard(
            stats_row,
            title="Avg Actual Mileage",
            value="-- km/l",
            subtitle="Touring efficiency",
            accent_color="#dc2626",
            icon_text="⚡",
        )
        self.card_avg_trip_cost.grid(row=0, column=3, padx=(8, 0), sticky="nsew")

        # Table section
        table_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        table_card.pack(fill="both", expand=True, padx=16, pady=(0, 20))

        tb_head = ttk.Frame(table_card, style="Card.TFrame")
        tb_head.pack(fill="x", pady=(0, 12))

        ttk.Label(
            tb_head,
            text="SAVED TRIPS & TOUR ITINERARIES",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(side="left")

        actions_f = ttk.Frame(tb_head, style="Card.TFrame")
        actions_f.pack(side="right")

        # Status filter
        ttk.Label(actions_f, text="Status:", style="CardDim.TLabel").pack(side="left", padx=(0, 6))
        self.status_var = tk.StringVar(value="All")
        self.cb_status = ttk.Combobox(
            actions_f,
            textvariable=self.status_var,
            values=["All", "Planned", "Completed", "Cancelled"],
            state="readonly",
            width=12,
        )
        self.cb_status.pack(side="left", padx=(0, 12))
        self.cb_status.bind("<<ComboboxSelected>>", lambda e: self.refresh_data())

        ttk.Button(
            actions_f,
            text="🏁 Mark Completed",
            style="Primary.TButton",
            command=self._open_complete_dialog,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions_f,
            text="📊 View Comparison",
            style="Secondary.TButton",
            command=self._view_trip_comparison,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions_f,
            text="📄 Export PDF",
            style="Outline.TButton",
            command=self._export_trip_pdf,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            actions_f,
            text="Delete",
            style="Outline.TButton",
            command=self._delete_selected_trip,
        ).pack(side="left")

        cols = [
            ("id", "ID", 50),
            ("title", "Trip Title", 160),
            ("start_location", "Start", 130),
            ("destination", "Destination", 130),
            ("status", "Status", 90),
            ("estimated_distance", "Est. Dist (km)", 100),
            ("estimated_fuel_cost", "Est. Cost (₹)", 100),
            ("actual_distance", "Actual Dist (km)", 110),
            ("actual_fuel_cost", "Actual Cost (₹)", 110),
            ("actual_mileage", "Actual Mileage", 110),
        ]

        self.table = DataTable(table_card, columns=cols, show_search=True)
        self.table.pack(fill="both", expand=True)

    def refresh_data(self):
        """Update cards and table from SQLite."""
        vid = self.get_active_vehicle_id()
        selected_status = self.status_var.get()
        trips = self.trip_repo.get_by_vehicle(vid, status=selected_status)
        all_trips = self.trip_repo.get_by_vehicle(vid)

        completed_trips = [t for t in all_trips if t.status == "Completed"]
        total_km = sum(t.actual_distance or 0.0 for t in completed_trips)
        
        valid_mileages = [t.actual_mileage for t in completed_trips if t.actual_mileage and t.actual_mileage > 0]
        avg_mileage = (sum(valid_mileages) / len(valid_mileages)) if valid_mileages else 0.0

        self.card_total_trips.update_value(f"{len(all_trips)} Trips")
        self.card_completed.update_value(f"{len(completed_trips)} Finished")
        self.card_touring_km.update_value(f"{total_km:,.1f} km")
        self.card_avg_trip_cost.update_value(
            f"{avg_mileage:.1f} km/l" if avg_mileage > 0 else "-- km/l"
        )

        table_rows = []
        for t in trips:
            table_rows.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "start_location": t.start_location,
                    "destination": t.destination,
                    "status": t.status,
                    "estimated_distance": f"{t.estimated_distance:.1f}",
                    "estimated_fuel_cost": f"₹ {t.estimated_fuel_cost:,.0f}",
                    "actual_distance": f"{t.actual_distance:.1f}" if t.actual_distance is not None else "--",
                    "actual_fuel_cost": f"₹ {t.actual_fuel_cost:,.0f}" if t.actual_fuel_cost is not None else "--",
                    "actual_mileage": f"{t.actual_mileage:.1f} km/l" if t.actual_mileage is not None else "--",
                }
            )
        self.table.set_data(table_rows)

    def _open_complete_dialog(self):
        sel = self.table.get_selected()
        if not sel:
            messagebox.showinfo("Select Trip", "Please select a planned trip to mark as completed.")
            return

        trip_id = int(sel["id"])
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            return

        dlg = tk.Toplevel(self)
        dlg.title(f"Complete Trip #{trip.id}: {trip.title}")
        dlg.geometry("480x620")
        dlg.configure(bg=DARK_THEME["bg_root"])
        dlg.grab_set()

        content = ttk.Frame(dlg, style="Card.TFrame", padding=20)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(
            content,
            text=f"COMPLETE TRIP: {trip.title.upper()}",
            style="CardTitle.TLabel",
            font=FONTS["h3"],
        ).pack(anchor="w", pady=(0, 4))
        ttk.Label(
            content,
            text=f"Estimated: {trip.estimated_distance:.1f} km | ₹ {trip.estimated_fuel_cost:.2f}",
            style="CardDim.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        # Fields
        vid = self.get_active_vehicle_id()
        vehicle = self.vehicle_repo.get_by_id(vid)
        curr_odo = vehicle.current_odometer if vehicle else 1000.0

        f_start_odo = ttk.Frame(content, style="Card.TFrame"); f_start_odo.pack(fill="x", pady=3)
        ttk.Label(f_start_odo, text="Starting Odometer (km):", style="CardDim.TLabel", width=24).pack(side="left")
        e_start_odo = ttk.Entry(f_start_odo); e_start_odo.insert(0, str(curr_odo)); e_start_odo.pack(side="right", fill="x", expand=True)

        f_end_odo = ttk.Frame(content, style="Card.TFrame"); f_end_odo.pack(fill="x", pady=3)
        ttk.Label(f_end_odo, text="Ending Odometer (km):", style="CardDim.TLabel", width=24).pack(side="left")
        e_end_odo = ttk.Entry(f_end_odo); e_end_odo.insert(0, str(curr_odo + trip.estimated_distance)); e_end_odo.pack(side="right", fill="x", expand=True)

        f_fuel_l = ttk.Frame(content, style="Card.TFrame"); f_fuel_l.pack(fill="x", pady=3)
        ttk.Label(f_fuel_l, text="Actual Fuel Consumed (L):", style="CardDim.TLabel", width=24).pack(side="left")
        e_fuel_l = ttk.Entry(f_fuel_l); e_fuel_l.insert(0, str(trip.estimated_fuel_litres)); e_fuel_l.pack(side="right", fill="x", expand=True)

        f_fuel_c = ttk.Frame(content, style="Card.TFrame"); f_fuel_c.pack(fill="x", pady=3)
        ttk.Label(f_fuel_c, text="Actual Fuel Cost (₹):", style="CardDim.TLabel", width=24).pack(side="left")
        e_fuel_c = ttk.Entry(f_fuel_c); e_fuel_c.insert(0, str(trip.estimated_fuel_cost)); e_fuel_c.pack(side="right", fill="x", expand=True)

        f_toll = ttk.Frame(content, style="Card.TFrame"); f_toll.pack(fill="x", pady=3)
        ttk.Label(f_toll, text="Toll Charges (₹):", style="CardDim.TLabel", width=24).pack(side="left")
        e_toll = ttk.Entry(f_toll); e_toll.insert(0, "0.0"); e_toll.pack(side="right", fill="x", expand=True)

        f_park = ttk.Frame(content, style="Card.TFrame"); f_park.pack(fill="x", pady=3)
        ttk.Label(f_park, text="Parking Charges (₹):", style="CardDim.TLabel", width=24).pack(side="left")
        e_park = ttk.Entry(f_park); e_park.insert(0, "0.0"); e_park.pack(side="right", fill="x", expand=True)

        f_extra = ttk.Frame(content, style="Card.TFrame"); f_extra.pack(fill="x", pady=3)
        ttk.Label(f_extra, text="Additional Expenses (₹):", style="CardDim.TLabel", width=24).pack(side="left")
        e_extra = ttk.Entry(f_extra); e_extra.insert(0, "0.0"); e_extra.pack(side="right", fill="x", expand=True)

        f_notes = ttk.Frame(content, style="Card.TFrame"); f_notes.pack(fill="x", pady=3)
        ttk.Label(f_notes, text="Trip Notes & Highlights:", style="CardDim.TLabel", width=24).pack(side="left")
        e_notes = ttk.Entry(f_notes); e_notes.insert(0, "Great scenic touring experience"); e_notes.pack(side="right", fill="x", expand=True)

        # Checkbox: Link to refuel records
        link_refuel_var = tk.IntVar(value=1)
        chk_refuel = ttk.Checkbutton(
            content,
            text="Automatically add this fuel expenditure to Refuel Manager",
            variable=link_refuel_var,
        )
        chk_refuel.pack(anchor="w", pady=(10, 0))

        def finish():
            try:
                s_odo = float(e_start_odo.get())
                e_odo = float(e_end_odo.get())
                f_litres = float(e_fuel_l.get())
                f_cost = float(e_fuel_c.get())
                toll = float(e_toll.get())
                park = float(e_park.get())
                extra = float(e_extra.get())
                notes = e_notes.get().strip()

                if e_odo < s_odo:
                    messagebox.showerror("Error", "Ending odometer cannot be less than starting odometer.")
                    return

                self.trip_repo.complete_trip(
                    trip_id=trip_id,
                    actual_start_odo=s_odo,
                    actual_end_odo=e_odo,
                    actual_fuel_litres=f_litres,
                    actual_fuel_cost=f_cost,
                    toll_charges=toll,
                    parking_charges=park,
                    additional_expenses=extra,
                    notes=notes,
                    create_refuel_entry=bool(link_refuel_var.get()),
                )

                ToastNotification.show(self, f"Trip #{trip_id} completed successfully!", "success")
                dlg.destroy()
                self.refresh_data()
                self.on_data_changed()
            except ValueError as err:
                messagebox.showerror("Error", str(err))

        btn_box = ttk.Frame(content, style="Card.TFrame")
        btn_box.pack(fill="x", pady=(20, 0))
        ttk.Button(btn_box, text="Mark as Completed", style="Primary.TButton", command=finish).pack(side="right", padx=(8, 0))
        ttk.Button(btn_box, text="Cancel", style="Outline.TButton", command=dlg.destroy).pack(side="right")

    def _view_trip_comparison(self):
        sel = self.table.get_selected()
        if not sel:
            messagebox.showinfo("Select Trip", "Please select a completed trip to view comparison.")
            return

        trip_id = int(sel["id"])
        comp = self.trip_repo.get_trip_comparison(trip_id)
        if not comp:
            messagebox.showinfo(
                "Incomplete Trip",
                "Comparison is available once a trip has been marked as Completed.",
            )
            return

        c_win = tk.Toplevel(self)
        c_win.title(f"Estimated vs Actual Analysis - Trip #{trip_id}")
        c_win.geometry("500x420")
        c_win.configure(bg=DARK_THEME["bg_root"])
        c_win.grab_set()

        content = ttk.Frame(c_win, style="Card.TFrame", padding=20)
        content.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(
            content,
            text=f"ESTIMATED VS ACTUAL ANALYSIS (TRIP #{trip_id})",
            style="CardTitle.TLabel",
            font=FONTS["h3"],
        ).pack(anchor="w", pady=(0, 16))

        # Comparison Grid
        grid_f = tk.Frame(content, bg=DARK_THEME["bg_card_inner"], padx=12, pady=10)
        grid_f.pack(fill="both", expand=True)

        headers = ["Metric", "Estimated", "Actual", "Variance"]
        for col_idx, h in enumerate(headers):
            tk.Label(
                grid_f, text=h, bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_secondary"], font=FONTS["body_bold"], width=13, anchor="w"
            ).grid(row=0, column=col_idx, pady=(0, 8), sticky="w")

        metrics = [
            ("Distance (km)", f"{comp.estimated_distance:.1f}", f"{comp.actual_distance:.1f}", f"{comp.distance_difference:+.1f}"),
            ("Fuel (Litres)", f"{comp.estimated_fuel_litres:.2f}", f"{comp.actual_fuel_litres:.2f}", f"{comp.fuel_litres_difference:+.2f}"),
            ("Fuel Cost (₹)", f"₹ {comp.estimated_fuel_cost:.0f}", f"₹ {comp.actual_fuel_cost:.0f}", f"₹ {comp.fuel_cost_difference:+.0f}"),
            ("Cost / KM (₹)", f"₹ {comp.estimated_cost_per_km:.2f}", f"₹ {comp.actual_cost_per_km:.2f}", f"₹ {comp.cost_per_km_difference:+.2f}"),
        ]

        for r_idx, (m_name, est_v, act_v, diff_v) in enumerate(metrics, start=1):
            tk.Label(grid_f, text=m_name, bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_primary"], font=FONTS["caption"], anchor="w").grid(row=r_idx, column=0, pady=4, sticky="w")
            tk.Label(grid_f, text=est_v, bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_secondary"], font=FONTS["caption"], anchor="w").grid(row=r_idx, column=1, pady=4, sticky="w")
            tk.Label(grid_f, text=act_v, bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_primary"], font=FONTS["caption"], anchor="w").grid(row=r_idx, column=2, pady=4, sticky="w")
            
            # Variance color
            diff_color = DARK_THEME["danger"] if "+" in diff_v and not m_name.startswith("Mileage") else DARK_THEME["success"]
            tk.Label(grid_f, text=diff_v, bg=DARK_THEME["bg_card_inner"], fg=diff_color, font=FONTS["body_bold"], anchor="w").grid(row=r_idx, column=3, pady=4, sticky="w")

        # Bottom actual mileage
        extra_info = tk.Frame(content, bg=DARK_THEME["bg_card"], pady=10)
        extra_info.pack(fill="x", pady=(10, 0))
        act_mileage_str = f"{comp.actual_mileage:.1f} km/l" if comp.actual_mileage else "--"
        tk.Label(
            extra_info,
            text=f"Actual Achieved Mileage: {act_mileage_str}  |  Total Ride Spend: ₹ {comp.total_actual_expenditure:,.2f}",
            bg=DARK_THEME["bg_card"],
            fg=DARK_THEME["primary"],
            font=FONTS["body_bold"],
        ).pack(anchor="w")

        ttk.Button(content, text="Close", style="Outline.TButton", command=c_win.destroy).pack(anchor="e", pady=(16, 0))

    def _export_trip_pdf(self):
        sel = self.table.get_selected()
        if not sel:
            messagebox.showinfo("Select Trip", "Please select a trip to export.")
            return

        trip_id = int(sel["id"])
        trip = self.trip_repo.get_by_id(trip_id)
        if not trip:
            return

        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf")],
            initialfile=f"Trip_{trip_id}_{trip.title.replace(' ', '_')}.pdf",
        )
        if not out_path:
            return

        try:
            c = canvas.Canvas(out_path, pagesize=letter)
            width, height = letter

            # Title
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, height - 50, "HF Deluxe Pro Manager - Trip Summary")

            c.setFont("Helvetica", 10)
            c.drawString(50, height - 70, f"Generated on {date.today().isoformat()} | Trip Reference #{trip.id}")

            # Draw divider
            c.setStrokeColorRGB(0.8, 0.2, 0.2)
            c.setLineWidth(2)
            c.line(50, height - 80, width - 50, height - 80)

            # Details
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 110, f"Trip Title: {trip.title}")

            c.setFont("Helvetica", 11)
            lines = [
                f"Starting Point: {trip.start_location}",
                f"Destination: {trip.destination}",
                f"Trip Status: {trip.status}",
                f"Planned Start Date: {trip.start_date}",
                f"Estimated Distance: {trip.estimated_distance:.1f} km",
                f"Estimated Fuel Consumption: {trip.estimated_fuel_litres:.2f} Litres",
                f"Estimated Fuel Cost: Rs. {trip.estimated_fuel_cost:.2f}",
                f"Assumed Fuel Mileage: {trip.assumed_mileage:.1f} km/l",
                f"Petrol Price Used: Rs. {trip.petrol_price_used:.2f} / L",
            ]

            if trip.status == "Completed":
                lines.extend([
                    "--- Actual Results ---",
                    f"Actual Distance Travelled: {trip.actual_distance or 0:.1f} km",
                    f"Actual Fuel Consumed: {trip.actual_fuel_litres or 0:.2f} Litres",
                    f"Actual Fuel Expenditure: Rs. {trip.actual_fuel_cost or 0:.2f}",
                    f"Actual Achieved Mileage: {trip.actual_mileage or 0:.1f} km/l",
                    f"Toll / Parking / Extra Charges: Rs. {(trip.toll_charges + trip.parking_charges + trip.additional_expenses):.2f}",
                ])

            y = height - 135
            for line in lines:
                c.drawString(50, y, line)
                y -= 20

            # Waypoints list
            if trip.waypoints:
                y -= 10
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, y, "Tour Waypoints & Route Stops:")
                y -= 20
                c.setFont("Helvetica", 10)
                for wp in trip.waypoints:
                    c.drawString(65, y, f"• [{wp.stop_type}] {wp.location_name} (Lat: {wp.latitude:.4f}, Lon: {wp.longitude:.4f})")
                    y -= 18

            # Footer
            c.setFont("Helvetica-Oblique", 9)
            c.drawString(50, 40, "Hero HF Deluxe Pro - Touring & Ownership Management Companion")

            c.save()
            ToastNotification.show(self, f"Exported PDF to {os.path.basename(out_path)}", "success")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def _delete_selected_trip(self):
        sel = self.table.get_selected()
        if not sel:
            messagebox.showinfo("Select Trip", "Please select a trip to delete.")
            return
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this trip record?"):
            return
        self.trip_repo.delete(int(sel["id"]))
        ToastNotification.show(self, "Trip deleted.", "info")
        self.refresh_data()
        self.on_data_changed()

