"""
HF Deluxe Pro Manager - Interactive Trip Planner Page
Integrates TkinterMapView with OpenStreetMap tiles, Nominatim geocoding, OSRM routing,
multi-stop waypoints, and automated fuel expenditure estimation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, List, Tuple, Dict, Any
import tkintermapview
import json

from ui.styles import DARK_THEME, FONTS
from ui.components import StatCard, ToastNotification
from api.geocoding import GeocodingService
from api.routing import RoutingService, RouteResult
from models.trips import Trip, TripWaypoint, TripRepository, SavedLocation
from models.vehicle import VehicleRepository
from models.fuel import RefuelRepository
from models.settings import SettingsRepository
from services.trip_calculator import calculate_trip_estimates, TripEstimate


class TripPlannerPage(ttk.Frame):
    """Interactive Map and Trip Planner."""

    def __init__(
        self,
        parent: tk.Widget,
        get_active_vehicle_id: Callable[[], int],
        on_trip_saved: Callable[[], None],
        **kwargs,
    ):
        super().__init__(parent, style="TFrame", **kwargs)
        self.get_active_vehicle_id = get_active_vehicle_id
        self.on_trip_saved = on_trip_saved

        self.geocoder = GeocodingService()
        self.router = RoutingService()
        self.trip_repo = TripRepository()
        self.vehicle_repo = VehicleRepository()
        self.fuel_repo = RefuelRepository()
        self.settings_repo = SettingsRepository()

        # Route State
        self.start_coord: Optional[Tuple[float, float, str]] = None  # (lat, lon, name)
        self.dest_coord: Optional[Tuple[float, float, str]] = None
        self.waypoints: List[Tuple[float, float, str]] = []  # List of (lat, lon, name)
        self.active_path = None
        self.markers: list = []
        self.current_route_result: Optional[RouteResult] = None
        self.current_estimates: Optional[TripEstimate] = None

        self._build_ui()

    def _build_ui(self):
        # Two-panel layout: Left sidebar for controls & fuel estimate, Right for TkinterMapView
        self.columnconfigure(0, weight=0, minsize=380)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Left Control Panel (Scrollable canvas)
        left_container = ttk.Frame(self, style="Card.TFrame")
        left_container.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)

        left_canvas = tk.Canvas(left_container, bg=DARK_THEME["bg_card"], highlightthickness=0)
        left_scroll = ttk.Scrollbar(
            left_container, orient="vertical", command=left_canvas.yview, style="Vertical.TScrollbar"
        )
        self.panel = ttk.Frame(left_canvas, style="Card.TFrame", padding=14)
        self.panel.bind("<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))

        canvas_win = left_canvas.create_window((0, 0), window=self.panel, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scroll.set)
        left_canvas.bind("<Configure>", lambda e: left_canvas.itemconfig(canvas_win, width=e.width))

        left_canvas.pack(side="left", fill="both", expand=True)
        left_scroll.pack(side="right", fill="y")

        # Title
        ttk.Label(
            self.panel, text="ROAD TRIP PLANNER", style="CardTitle.TLabel", font=FONTS["h2"]
        ).pack(anchor="w", pady=(0, 2))
        ttk.Label(
            self.panel,
            text="Plan motorcycle journeys, calculate distance & fuel budgets",
            style="CardDim.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        # Trip Title
        ttk.Label(self.panel, text="Trip Title:", style="CardDim.TLabel").pack(anchor="w")
        self.e_title = ttk.Entry(self.panel)
        self.e_title.insert(0, "Weekend Coastal Ride")
        self.e_title.pack(fill="x", pady=(2, 8))

        # Start Location
        ttk.Label(self.panel, text="Starting Location:", style="CardDim.TLabel").pack(anchor="w")
        f_start = ttk.Frame(self.panel, style="Card.TFrame")
        f_start.pack(fill="x", pady=(2, 8))
        self.e_start = ttk.Entry(f_start)
        self.e_start.insert(0, "Chennai, Tamil Nadu")
        self.e_start.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_start, text="Locate", style="Outline.TButton", command=self._locate_start).pack(side="right")

        # Intermediate Waypoints Box
        wp_header = ttk.Frame(self.panel, style="Card.TFrame")
        wp_header.pack(fill="x", pady=(4, 2))
        ttk.Label(wp_header, text="Intermediate Stops:", style="CardDim.TLabel").pack(side="left")
        ttk.Button(wp_header, text="+ Add Stop", style="Outline.TButton", command=self._prompt_add_waypoint).pack(side="right")

        self.wp_listbox = tk.Listbox(
            self.panel,
            bg=DARK_THEME["bg_input"],
            fg=DARK_THEME["text_primary"],
            selectbackground=DARK_THEME["selection"],
            selectforeground="#ffffff",
            height=3,
            bd=0,
            font=FONTS["caption"],
        )
        self.wp_listbox.pack(fill="x", pady=(2, 4))

        wp_btn_box = ttk.Frame(self.panel, style="Card.TFrame")
        wp_btn_box.pack(fill="x", pady=(0, 8))
        ttk.Button(wp_btn_box, text="Remove Stop", style="Outline.TButton", command=self._remove_selected_waypoint).pack(side="left", padx=(0, 4))
        ttk.Button(wp_btn_box, text="Move Up ↑", style="Outline.TButton", command=self._move_waypoint_up).pack(side="left", padx=4)
        ttk.Button(wp_btn_box, text="Move Down ↓", style="Outline.TButton", command=self._move_waypoint_down).pack(side="left")

        # Destination Location
        ttk.Label(self.panel, text="Destination:", style="CardDim.TLabel").pack(anchor="w")
        f_dest = ttk.Frame(self.panel, style="Card.TFrame")
        f_dest.pack(fill="x", pady=(2, 8))
        self.e_dest = ttk.Entry(f_dest)
        self.e_dest.insert(0, "Pondicherry")
        self.e_dest.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(f_dest, text="Locate", style="Outline.TButton", command=self._locate_dest).pack(side="right")

        # Mileage & Fuel Parameters
        param_box = tk.Frame(self.panel, bg=DARK_THEME["bg_card_inner"], padx=10, pady=8)
        param_box.pack(fill="x", pady=(4, 10))

        tk.Label(
            param_box, text="FUEL EFFICIENCY & PRICING", bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_secondary"], font=FONTS["caption"]
        ).pack(anchor="w", pady=(0, 6))

        p_row1 = tk.Frame(param_box, bg=DARK_THEME["bg_card_inner"])
        p_row1.pack(fill="x", pady=2)
        tk.Label(p_row1, text="Assumed Mileage (km/l):", bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_primary"], font=FONTS["caption"], width=22, anchor="w").pack(side="left")
        self.e_mileage = ttk.Entry(p_row1, width=10)
        self.e_mileage.insert(0, "65.0")
        self.e_mileage.pack(side="right")

        p_row2 = tk.Frame(param_box, bg=DARK_THEME["bg_card_inner"])
        p_row2.pack(fill="x", pady=2)
        tk.Label(p_row2, text="Petrol Price (₹ / L):", bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_primary"], font=FONTS["caption"], width=22, anchor="w").pack(side="left")
        self.e_price = ttk.Entry(p_row2, width=10)
        self.e_price.insert(0, "102.50")
        self.e_price.pack(side="right")

        self.round_trip_var = tk.IntVar(value=0)
        chk_round = ttk.Checkbutton(
            param_box,
            text="Round Trip (Calculate Return Route)",
            variable=self.round_trip_var,
            command=self._on_parameters_changed,
        )
        chk_round.pack(anchor="w", pady=(6, 0))

        # Calculate Route Button
        self.btn_calculate = ttk.Button(
            self.panel,
            text="⚡ Calculate Route & Fuel Budget",
            style="Primary.TButton",
            command=self._calculate_route_action,
        )
        self.btn_calculate.pack(fill="x", pady=(4, 12))

        # Status & Estimation Summary Box
        self.summary_box = tk.Frame(self.panel, bg=DARK_THEME["bg_card_inner"], padx=12, pady=10)
        self.summary_box.pack(fill="x", pady=(0, 12))

        tk.Label(
            self.summary_box,
            text="TRIP ESTIMATES SUMMARY",
            bg=DARK_THEME["bg_card_inner"],
            fg=DARK_THEME["text_secondary"],
            font=FONTS["caption"],
        ).pack(anchor="w", pady=(0, 6))

        self.sum_labels: dict = {}
        sum_rows = [
            ("One-Way Distance", "dist", "-- km"),
            ("Return Distance", "ret_dist", "-- km"),
            ("Estimated Ride Time", "time", "-- hrs"),
            ("Fuel Consumption", "fuel", "-- L"),
            ("One-Way Fuel Spend", "cost", "₹ --"),
            ("Total Estimated Spend", "total_cost", "₹ --"),
            ("Estimated Cost / KM", "cost_km", "₹ -- / km"),
        ]

        for title, key, default_val in sum_rows:
            rf = tk.Frame(self.summary_box, bg=DARK_THEME["bg_card_inner"])
            rf.pack(fill="x", pady=2)
            tk.Label(
                rf, text=title, bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_secondary"], font=FONTS["caption"], anchor="w"
            ).pack(side="left")
            vl = tk.Label(
                rf, text=default_val, bg=DARK_THEME["bg_card_inner"], fg=DARK_THEME["text_primary"], font=FONTS["body_bold"], anchor="e"
            )
            vl.pack(side="right")
            self.sum_labels[key] = vl

        # Notice regarding OSRM estimates
        tk.Label(
            self.panel,
            text="* Route distances & durations are computed via OSRM estimates. Always plan for real-world traffic, breaks, and road conditions.",
            wraplength=340,
            justify="left",
            bg=DARK_THEME["bg_card"],
            fg=DARK_THEME["text_dim"],
            font=("Segoe UI", 8),
        ).pack(fill="x", pady=(0, 10))

        # Save Trip Button
        self.btn_save = ttk.Button(
            self.panel,
            text="💾 Save Itinerary to My Trips",
            style="Secondary.TButton",
            command=self._save_trip_action,
        )
        self.btn_save.pack(fill="x")

        # 2. Right Map Panel (TkinterMapView)
        map_container = ttk.Frame(self, style="Card.TFrame", padding=4)
        map_container.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)

        self.map_widget = tkintermapview.TkinterMapView(
            map_container,
            corner_radius=4,
            bg_color=DARK_THEME["bg_root"],
        )
        self.map_widget.pack(fill="both", expand=True)

        # Configure OpenStreetMap tiles
        self.map_widget.set_tile_server(
            "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=19
        )
        # Default view: Southern/Central India
        self.map_widget.set_position(13.0827, 80.2707)  # Chennai
        self.map_widget.set_zoom(8)

        # Right-click context menus on map
        self.map_widget.add_right_click_menu_command(
            label="Set as Starting Point",
            command=self._context_set_start,
            pass_coords=True,
        )
        self.map_widget.add_right_click_menu_command(
            label="Set as Destination",
            command=self._context_set_dest,
            pass_coords=True,
        )
        self.map_widget.add_right_click_menu_command(
            label="Add Intermediate Stop",
            command=self._context_add_stop,
            pass_coords=True,
        )

    def refresh_data(self):
        """Update active vehicle default assumed mileage and petrol price."""
        vid = self.get_active_vehicle_id()
        stats = self.fuel_repo.get_stats(vid)
        if stats.lifetime_avg_mileage:
            self.e_mileage.delete(0, "end")
            self.e_mileage.insert(0, f"{stats.lifetime_avg_mileage:.1f}")

        if stats.average_price > 0:
            self.e_price.delete(0, "end")
            self.e_price.insert(0, f"{stats.average_price:.2f}")

    def _locate_start(self):
        q = self.e_start.get().strip()
        if not q:
            return
        res = self.geocoder.geocode(q)
        if res:
            lat, lon, dname = res
            self.start_coord = (lat, lon, q)
            self._update_map_markers()
            self.map_widget.set_position(lat, lon)
            ToastNotification.show(self, f"Located start: {q}", "success")
        else:
            ToastNotification.show(self, f"Could not geocode '{q}'. You can right-click map directly.", "warning")

    def _locate_dest(self):
        q = self.e_dest.get().strip()
        if not q:
            return
        res = self.geocoder.geocode(q)
        if res:
            lat, lon, dname = res
            self.dest_coord = (lat, lon, q)
            self._update_map_markers()
            ToastNotification.show(self, f"Located destination: {q}", "success")
        else:
            ToastNotification.show(self, f"Could not geocode '{q}'. You can right-click map directly.", "warning")

    def _prompt_add_waypoint(self):
        w_win = tk.Toplevel(self)
        w_win.title("Add Intermediate Stop")
        w_win.geometry("360x180")
        w_win.configure(bg=DARK_THEME["bg_root"])
        w_win.grab_set()

        content = ttk.Frame(w_win, style="Card.TFrame", padding=16)
        content.pack(fill="both", expand=True, padx=12, pady=12)

        ttk.Label(content, text="Location Name (City or Town):", style="CardDim.TLabel").pack(anchor="w")
        e_wp = ttk.Entry(content)
        e_wp.insert(0, "Mahabalipuram")
        e_wp.pack(fill="x", pady=(4, 12))

        def add_wp():
            val = e_wp.get().strip()
            if not val:
                return
            res = self.geocoder.geocode(val)
            if res:
                lat, lon, dname = res
                self.waypoints.append((lat, lon, val))
                self.wp_listbox.insert("end", f"{len(self.waypoints)}. {val}")
                self._update_map_markers()
                w_win.destroy()
                ToastNotification.show(self, f"Added stop: {val}", "success")
            else:
                messagebox.showwarning("Geocoding", f"Could not find coordinates for '{val}'.")

        ttk.Button(content, text="Add Stop", style="Primary.TButton", command=add_wp).pack(side="right")
        ttk.Button(content, text="Cancel", style="Outline.TButton", command=w_win.destroy).pack(side="right", padx=6)

    def _remove_selected_waypoint(self):
        sel = self.wp_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.wp_listbox.delete(idx)
        del self.waypoints[idx]
        self._refresh_wp_listbox()
        self._update_map_markers()

    def _move_waypoint_up(self):
        sel = self.wp_listbox.curselection()
        if not sel or sel[0] == 0:
            return
        idx = sel[0]
        self.waypoints[idx - 1], self.waypoints[idx] = self.waypoints[idx], self.waypoints[idx - 1]
        self._refresh_wp_listbox()
        self.wp_listbox.selection_set(idx - 1)
        self._update_map_markers()

    def _move_waypoint_down(self):
        sel = self.wp_listbox.curselection()
        if not sel or sel[0] >= len(self.waypoints) - 1:
            return
        idx = sel[0]
        self.waypoints[idx + 1], self.waypoints[idx] = self.waypoints[idx], self.waypoints[idx + 1]
        self._refresh_wp_listbox()
        self.wp_listbox.selection_set(idx + 1)
        self._update_map_markers()

    def _refresh_wp_listbox(self):
        self.wp_listbox.delete(0, "end")
        for i, wp in enumerate(self.waypoints):
            self.wp_listbox.insert("end", f"{i + 1}. {wp[2]}")

    def _context_set_start(self, coords: Tuple[float, float]):
        lat, lon = coords
        addr = self.geocoder.reverse_geocode(lat, lon) or f"{lat:.4f}, {lon:.4f}"
        self.start_coord = (lat, lon, addr)
        self.e_start.delete(0, "end")
        self.e_start.insert(0, addr)
        self._update_map_markers()
        ToastNotification.show(self, "Start point set from map.", "success")

    def _context_set_dest(self, coords: Tuple[float, float]):
        lat, lon = coords
        addr = self.geocoder.reverse_geocode(lat, lon) or f"{lat:.4f}, {lon:.4f}"
        self.dest_coord = (lat, lon, addr)
        self.e_dest.delete(0, "end")
        self.e_dest.insert(0, addr)
        self._update_map_markers()
        ToastNotification.show(self, "Destination set from map.", "success")

    def _context_add_stop(self, coords: Tuple[float, float]):
        lat, lon = coords
        addr = self.geocoder.reverse_geocode(lat, lon) or f"{lat:.4f}, {lon:.4f}"
        self.waypoints.append((lat, lon, addr))
        self._refresh_wp_listbox()
        self._update_map_markers()
        ToastNotification.show(self, "Intermediate stop added from map.", "success")

    def _update_map_markers(self):
        for m in self.markers:
            m.delete()
        self.markers.clear()

        if self.start_coord:
            m = self.map_widget.set_marker(
                self.start_coord[0], self.start_coord[1], text=f"Start: {self.start_coord[2][:16]}", marker_color_circle="#10b981"
            )
            self.markers.append(m)

        for i, wp in enumerate(self.waypoints):
            m = self.map_widget.set_marker(
                wp[0], wp[1], text=f"Stop {i+1}: {wp[2][:16]}", marker_color_circle="#f59e0b"
            )
            self.markers.append(m)

        if self.dest_coord:
            m = self.map_widget.set_marker(
                self.dest_coord[0], self.dest_coord[1], text=f"End: {self.dest_coord[2][:16]}", marker_color_circle="#dc2626"
            )
            self.markers.append(m)

    def _calculate_route_action(self):
        # Ensure start and dest coordinates are resolved
        if not self.start_coord:
            self._locate_start()
        if not self.dest_coord:
            self._locate_dest()

        if not self.start_coord or not self.dest_coord:
            messagebox.showerror(
                "Missing Locations",
                "Please enter and locate both starting point and destination (or right-click the map).",
            )
            return

        all_points = [self.start_coord[:2]] + [wp[:2] for wp in self.waypoints] + [self.dest_coord[:2]]

        self.btn_calculate.config(text="Calculating Route...", state="disabled")

        def on_complete(result: RouteResult):
            self.after(0, lambda: self._handle_route_calculated(result))

        self.router.calculate_route_async(all_points, on_complete)

    def _handle_route_calculated(self, result: RouteResult):
        self.btn_calculate.config(text="⚡ Calculate Route & Fuel Budget", state="normal")
        self.current_route_result = result

        if self.active_path:
            self.active_path.delete()
            self.active_path = None

        if result.geometry_coords:
            self.active_path = self.map_widget.set_path(
                result.geometry_coords, color="#dc2626", width=4
            )
            # Center map around middle coordinate
            mid_idx = len(result.geometry_coords) // 2
            mid_pt = result.geometry_coords[mid_idx]
            self.map_widget.set_position(mid_pt[0], mid_pt[1])

        self._update_estimates_display()

        if result.is_estimate_fallback:
            ToastNotification.show(self, "Route estimated (Offline mode).", "warning")
        else:
            ToastNotification.show(self, f"Route calculated: {result.distance_km:.1f} km", "success")

    def _on_parameters_changed(self):
        if self.current_route_result:
            self._update_estimates_display()

    def _update_estimates_display(self):
        if not self.current_route_result:
            return

        try:
            mileage = float(self.e_mileage.get())
            price = float(self.e_price.get())
            is_round = bool(self.round_trip_var.get())

            est = calculate_trip_estimates(
                distance_km=self.current_route_result.distance_km,
                duration_minutes=self.current_route_result.duration_minutes,
                mileage_km_per_l=mileage,
                petrol_price_per_l=price,
                is_round_trip=is_round,
            )
            self.current_estimates = est

            self.sum_labels["dist"].config(text=f"{est.one_way_distance_km:.1f} km")
            self.sum_labels["ret_dist"].config(
                text=f"{est.return_distance_km:.1f} km" if is_round else "One-way only"
            )

            # Format duration
            hours = int(est.duration_minutes // 60)
            mins = int(est.duration_minutes % 60)
            dur_str = f"{hours}h {mins}m" if hours > 0 else f"{mins} mins"
            if is_round:
                dur_str += " (x2 round-trip)"
            self.sum_labels["time"].config(text=dur_str)

            self.sum_labels["fuel"].config(text=f"{est.fuel_required_litres:.2f} Litres")
            self.sum_labels["cost"].config(text=f"₹ {est.one_way_fuel_cost:,.2f}")
            self.sum_labels["total_cost"].config(text=f"₹ {est.total_fuel_cost:,.2f}")
            self.sum_labels["cost_km"].config(text=f"₹ {est.cost_per_km:.2f} / km")
        except ValueError:
            pass

    def _save_trip_action(self):
        if not self.current_route_result or not self.current_estimates:
            messagebox.showinfo("Calculate First", "Please calculate the route first before saving.")
            return

        title = self.e_title.get().strip() or "Planned Road Trip"
        start_loc = self.e_start.get().strip() or "Start"
        dest_loc = self.e_dest.get().strip() or "Destination"
        vid = self.get_active_vehicle_id()
        est = self.current_estimates

        # Serialize route geometry
        geom_json = json.dumps(self.current_route_result.geometry_coords)

        # Prepare waypoints
        wp_models: List[TripWaypoint] = []
        # Start
        wp_models.append(
            TripWaypoint(
                id=None,
                trip_id=0,
                sequence_order=0,
                location_name=start_loc,
                latitude=self.start_coord[0],
                longitude=self.start_coord[1],
                stop_type="Start",
            )
        )
        # Intermediate
        for i, wp in enumerate(self.waypoints):
            wp_models.append(
                TripWaypoint(
                    id=None,
                    trip_id=0,
                    sequence_order=i + 1,
                    location_name=wp[2],
                    latitude=wp[0],
                    longitude=wp[1],
                    stop_type="Stop",
                )
            )
        # Dest
        wp_models.append(
            TripWaypoint(
                id=None,
                trip_id=0,
                sequence_order=len(self.waypoints) + 1,
                location_name=dest_loc,
                latitude=self.dest_coord[0],
                longitude=self.dest_coord[1],
                stop_type="Destination",
            )
        )

        from datetime import date
        today_str = date.today().isoformat()

        trip_model = Trip(
            id=None,
            vehicle_id=vid,
            title=title,
            start_location=start_loc,
            destination=dest_loc,
            status="Planned",
            start_date=today_str,
            is_round_trip=1 if self.round_trip_var.get() else 0,
            estimated_distance=est.total_distance_km,
            estimated_duration=est.duration_minutes * (2 if self.round_trip_var.get() else 1),
            assumed_mileage=est.assumed_mileage,
            petrol_price_used=est.fuel_price,
            estimated_fuel_litres=est.fuel_required_litres,
            estimated_fuel_cost=est.total_fuel_cost,
            estimated_cost_per_km=est.cost_per_km,
            route_geometry_json=geom_json,
        )

        trip_id = self.trip_repo.add(trip_model, wp_models)
        ToastNotification.show(self, f"Saved trip '{title}' (#{trip_id}) to Itinerary!", "success")
        self.on_trip_saved()

