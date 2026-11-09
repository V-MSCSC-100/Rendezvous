"""
HF Deluxe Pro Manager - Main Application Entry Point
Modular desktop application for Hero HF Deluxe Pro motorcycle management and touring.
"""

import sys
import os
import tempfile
import logging

# Configure Matplotlib writable directory before import
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib_hf"))

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict

# Ensure local packages in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import get_db
from models.vehicle import VehicleRepository
from ui.styles import apply_theme, DARK_THEME, FONTS
from ui.dashboard import DashboardPage
from ui.vehicle import VehiclePage
from ui.fuel import FuelPage
from ui.maintenance import MaintenancePage
from ui.upgrades import UpgradesPage
from ui.analytics import AnalyticsPage
from ui.trip_planner import TripPlannerPage
from ui.trip_history import TripHistoryPage
from ui.settings import SettingsPage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hf_manager")


class HFDeluxeManagerApp(tk.Tk):
    """Main desktop application window and navigation controller."""

    def __init__(self):
        super().__init__()

        self.title("HF Deluxe Pro Manager - Motorcycle Ownership & Touring Companion")
        self.geometry("1280x820")
        self.minsize(1040, 680)

        # Database and state
        self.db = get_db()
        self.vehicle_repo = VehicleRepository(self.db)
        
        # Load active vehicle
        default_vehicle = self.vehicle_repo.get_default_vehicle()
        self.active_vehicle_id = default_vehicle.id if default_vehicle else 1

        # Apply dark theme
        self.palette = apply_theme(self, theme_name="dark")

        self.pages: Dict[str, ttk.Frame] = {}
        self.nav_buttons: Dict[str, ttk.Button] = {}
        self.current_page_key: str = "dashboard"

        self._build_layout()
        self.navigate_to("dashboard")

    def _build_layout(self):
        """Build the persistent sidebar and main content dynamic container."""
        # Top-level grid: Sidebar on left (col 0), content area on right (col 1)
        self.columnconfigure(0, weight=0, minsize=240)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # 1. Persistent Sidebar
        self.sidebar = tk.Frame(self, bg=self.palette["bg_sidebar"], width=240)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.pack_propagate(False)

        # Brand / App Header
        brand_frame = tk.Frame(self.sidebar, bg=self.palette["bg_sidebar"], padx=20, pady=24)
        brand_frame.pack(fill="x")

        lbl_logo = tk.Label(
            brand_frame,
            text="🏍️ HF DELUXE PRO",
            bg=self.palette["bg_sidebar"],
            fg=self.palette["text_primary"],
            font=("Segoe UI", 13, "bold"),
        )
        lbl_logo.pack(anchor="w")

        lbl_edition = tk.Label(
            brand_frame,
            text="PRO MANAGER EDITION",
            bg=self.palette["bg_sidebar"],
            fg=self.palette["primary"],
            font=("Segoe UI", 8, "bold"),
        )
        lbl_edition.pack(anchor="w", pady=(2, 0))

        # Divider
        div = tk.Frame(self.sidebar, bg=self.palette["border"], height=1)
        div.pack(fill="x", padx=16, pady=(0, 16))

        # Nav items
        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("vehicle", "🏍️  My Vehicle"),
            ("fuel", "⛽  Fuel Manager"),
            ("maintenance", "🔧  Maintenance"),
            ("upgrades", "✨  Parts & Upgrades"),
            ("analytics", "📈  Financial Analytics"),
            ("trip_planner", "🗺️  Trip Planner"),
            ("trip_history", "🏁  Trip History"),
            ("settings", "⚙️  Settings"),
        ]

        self.nav_frame = tk.Frame(self.sidebar, bg=self.palette["bg_sidebar"])
        self.nav_frame.pack(fill="both", expand=True)

        for key, label in nav_items:
            btn = ttk.Button(
                self.nav_frame,
                text=label,
                style="Nav.TButton",
                command=lambda k=key: self.navigate_to(k),
            )
            btn.pack(fill="x", padx=8, pady=2)
            self.nav_buttons[key] = btn

        # Bottom Vehicle Quick Status Pill
        self.bottom_pill = tk.Frame(
            self.sidebar, bg=self.palette["bg_card_inner"], padx=12, pady=10
        )
        self.bottom_pill.pack(fill="x", side="bottom", padx=12, pady=16)

        self.lbl_pill_name = tk.Label(
            self.bottom_pill,
            text="Hero HF Deluxe Pro",
            bg=self.palette["bg_card_inner"],
            fg=self.palette["text_primary"],
            font=FONTS["body_bold"],
        )
        self.lbl_pill_name.pack(anchor="w")

        self.lbl_pill_sub = tk.Label(
            self.bottom_pill,
            text="Ready for tour",
            bg=self.palette["bg_card_inner"],
            fg=self.palette["success"],
            font=FONTS["caption"],
        )
        self.lbl_pill_sub.pack(anchor="w")

        # 2. Main Content Dynamic Container
        self.content_container = ttk.Frame(self, style="TFrame")
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.columnconfigure(0, weight=1)
        self.content_container.rowconfigure(0, weight=1)

        # Initialize all pages
        self._init_pages()

    def _init_pages(self):
        """Instantiate and register all page frames."""
        self.pages["dashboard"] = DashboardPage(
            self.content_container,
            navigate_callback=self.navigate_to,
            get_active_vehicle_id=self.get_active_vehicle_id,
        )
        self.pages["vehicle"] = VehiclePage(
            self.content_container,
            get_active_vehicle_id=self.get_active_vehicle_id,
            set_active_vehicle_id=self.set_active_vehicle_id,
            on_vehicle_updated=self.refresh_all_data,
        )
        self.pages["fuel"] = FuelPage(
            self.content_container,
            get_active_vehicle_id=self.get_active_vehicle_id,
            on_data_changed=self.refresh_all_data,
        )
        self.pages["maintenance"] = MaintenancePage(
            self.content_container,
            get_active_vehicle_id=self.get_active_vehicle_id,
            on_data_changed=self.refresh_all_data,
        )
        self.pages["upgrades"] = UpgradesPage(
            self.content_container,
            get_active_vehicle_id=self.get_active_vehicle_id,
            on_data_changed=self.refresh_all_data,
        )
        self.pages["analytics"] = AnalyticsPage(
            self.content_container,
            get_active_vehicle_id=self.get_active_vehicle_id,
        )
        self.pages["trip_planner"] = TripPlannerPage(
            self.content_container,
            get_active_vehicle_id=self.get_active_vehicle_id,
            on_trip_saved=lambda: self.navigate_to("trip_history"),
        )
        self.pages["trip_history"] = TripHistoryPage(
            self.content_container,
            get_active_vehicle_id=self.get_active_vehicle_id,
            on_data_changed=self.refresh_all_data,
        )
        self.pages["settings"] = SettingsPage(
            self.content_container,
            get_active_vehicle_id=self.get_active_vehicle_id,
            on_settings_saved=self.refresh_all_data,
        )

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def get_active_vehicle_id(self) -> int:
        return self.active_vehicle_id

    def set_active_vehicle_id(self, vehicle_id: int):
        self.active_vehicle_id = vehicle_id
        self._update_pill_info()
        self.refresh_all_data()

    def _update_pill_info(self):
        v = self.vehicle_repo.get_by_id(self.active_vehicle_id)
        if v:
            self.lbl_pill_name.config(text=f"{v.manufacturer} {v.model}")
            self.lbl_pill_sub.config(text=f"{v.registration_number}  |  {v.current_odometer:,.0f} km")

    def navigate_to(self, page_key: str):
        """Switch active page view dynamically and refresh its contents."""
        if page_key not in self.pages:
            logger.warning("Attempted to navigate to unknown page: %s", page_key)
            return

        self.current_page_key = page_key

        # Update button highlights
        for key, btn in self.nav_buttons.items():
            if key == page_key:
                btn.configure(style="NavActive.TButton")
            else:
                btn.configure(style="Nav.TButton")

        # Raise selected page frame
        page = self.pages[page_key]
        page.tkraise()
        if hasattr(page, "refresh_data"):
            page.refresh_data()

        self._update_pill_info()

    def refresh_all_data(self):
        """Refresh the active page and global indicators."""
        current_page = self.pages.get(self.current_page_key)
        if current_page and hasattr(current_page, "refresh_data"):
            current_page.refresh_data()
        self._update_pill_info()


def main():
    app = HFDeluxeManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
