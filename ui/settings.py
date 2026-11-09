"""
HF Deluxe Pro Manager - Settings & Data Management Page
Handles app preferences, defaults, database backups & restores, and API configuration.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Callable, Optional
from datetime import datetime

from ui.styles import DARK_THEME, FONTS
from ui.components import ScrollableFrame, SectionHeader, ToastNotification
from models.settings import SettingsRepository
from models.vehicle import VehicleRepository
from database.db import get_db


class SettingsPage(ttk.Frame):
    """Settings and Data Management Page."""

    def __init__(
        self,
        parent: tk.Widget,
        get_active_vehicle_id: Callable[[], int],
        on_settings_saved: Callable[[], None],
        **kwargs,
    ):
        super().__init__(parent, style="TFrame", **kwargs)
        self.get_active_vehicle_id = get_active_vehicle_id
        self.on_settings_saved = on_settings_saved

        self.settings_repo = SettingsRepository()
        self.vehicle_repo = VehicleRepository()
        self.db = get_db()

        self._build_ui()

    def _build_ui(self):
        self.scroll = ScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True)
        content = self.scroll.scrollable_content

        # Header
        header = SectionHeader(
            content,
            title="SETTINGS & DATA MANAGEMENT",
            subtitle="Application defaults, unit configurations, API servers, and database backups",
        )
        header.pack(fill="x", padx=16, pady=16)

        # 1. Preferences Card
        pref_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        pref_card.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Label(
            pref_card,
            text="APPLICATION PREFERENCES & DEFAULTS",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(anchor="w", pady=(0, 12))

        # Default fuel efficiency
        f_eff = ttk.Frame(pref_card, style="Card.TFrame")
        f_eff.pack(fill="x", pady=4)
        ttk.Label(f_eff, text="Default Mileage Efficiency (km/l):", style="CardDim.TLabel", width=32).pack(side="left")
        self.e_eff = ttk.Entry(f_eff, width=20)
        self.e_eff.pack(side="left")

        # Default petrol price
        f_price = ttk.Frame(pref_card, style="Card.TFrame")
        f_price.pack(fill="x", pady=4)
        ttk.Label(f_price, text="Default Petrol Price (₹/L):", style="CardDim.TLabel", width=32).pack(side="left")
        self.e_price = ttk.Entry(f_price, width=20)
        self.e_price.pack(side="left")

        # Currency
        f_curr = ttk.Frame(pref_card, style="Card.TFrame")
        f_curr.pack(fill="x", pady=4)
        ttk.Label(f_curr, text="Currency Symbol & Code:", style="CardDim.TLabel", width=32).pack(side="left")
        self.e_curr = ttk.Entry(f_curr, width=20)
        self.e_curr.pack(side="left")

        # Distance unit
        f_unit = ttk.Frame(pref_card, style="Card.TFrame")
        f_unit.pack(fill="x", pady=4)
        ttk.Label(f_unit, text="Distance Unit:", style="CardDim.TLabel", width=32).pack(side="left")
        self.cb_unit = ttk.Combobox(f_unit, values=["Kilometres (km)", "Miles (mi)"], state="readonly", width=18)
        self.cb_unit.pack(side="left")

        # 2. API Endpoints Configuration
        api_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        api_card.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Label(
            api_card,
            text="OPENSTREETMAP & OSRM API CONFIGURATION",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(anchor="w", pady=(0, 12))

        f_osrm = ttk.Frame(api_card, style="Card.TFrame")
        f_osrm.pack(fill="x", pady=4)
        ttk.Label(f_osrm, text="OSRM Routing API Server:", style="CardDim.TLabel", width=32).pack(side="left")
        self.e_osrm = ttk.Entry(f_osrm)
        self.e_osrm.pack(side="left", fill="x", expand=True)

        f_nom = ttk.Frame(api_card, style="Card.TFrame")
        f_nom.pack(fill="x", pady=4)
        ttk.Label(f_nom, text="Nominatim Geocoding Server:", style="CardDim.TLabel", width=32).pack(side="left")
        self.e_nom = ttk.Entry(f_nom)
        self.e_nom.pack(side="left", fill="x", expand=True)

        ttk.Button(
            pref_card, text="Save Settings & Preferences", style="Primary.TButton", command=self._save_settings
        ).pack(anchor="w", pady=(12, 0))

        # 3. Database Backup & Restore Card
        db_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        db_card.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Label(
            db_card,
            text="DATABASE PERSISTENCE & BACKUP MANAGEMENT",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(anchor="w", pady=(0, 8))

        ttk.Label(
            db_card,
            text=f"Primary SQLite Database File: {self.db.db_path}",
            style="CardDim.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        db_btn_box = ttk.Frame(db_card, style="Card.TFrame")
        db_btn_box.pack(fill="x")

        ttk.Button(
            db_btn_box,
            text="📦 Backup Database to File",
            style="Secondary.TButton",
            command=self._backup_database,
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            db_btn_box,
            text="🔄 Restore Database from Backup",
            style="Outline.TButton",
            command=self._restore_database,
        ).pack(side="left")

        # 4. About & Attribution Card
        about_card = ttk.Frame(content, style="Card.TFrame", padding=16)
        about_card.pack(fill="x", padx=16, pady=(0, 20))

        ttk.Label(
            about_card,
            text="ABOUT & MAP ATTRIBUTION",
            style="CardTitle.TLabel",
            font=FONTS["caption"],
        ).pack(anchor="w", pady=(0, 8))

        about_text = (
            "HF Deluxe Pro Manager v1.0.0\n"
            "Personal motorcycle ownership tracking, fuel efficiency analytics, and road-trip planning companion.\n\n"
            "Attribution & Data Sources:\n"
            "• Map Data & Cartography © OpenStreetMap contributors (ODbL license)\n"
            "• Search & Geocoding by Nominatim under OpenStreetMap policies\n"
            "• Routing engines powered by Open Source Routing Machine (OSRM)\n"
            "• High-performance native GUI rendered with Python Tkinter & Matplotlib"
        )
        tk.Label(
            about_card,
            text=about_text,
            bg=DARK_THEME["bg_card"],
            fg=DARK_THEME["text_secondary"],
            font=FONTS["caption"],
            justify="left",
        ).pack(anchor="w")

    def refresh_data(self):
        """Load current settings from app_settings table."""
        settings = self.settings_repo.get_all()
        self.e_eff.delete(0, "end")
        self.e_eff.insert(0, settings.get("default_fuel_efficiency", "65.0"))

        self.e_price.delete(0, "end")
        self.e_price.insert(0, settings.get("default_petrol_price", "102.50"))

        self.e_curr.delete(0, "end")
        self.e_curr.insert(0, settings.get("currency_symbol", "₹") + " " + settings.get("currency", "INR"))

        self.cb_unit.set("Kilometres (km)")

        self.e_osrm.delete(0, "end")
        self.e_osrm.insert(0, settings.get("osrm_server", "https://router.project-osrm.org"))

        self.e_nom.delete(0, "end")
        self.e_nom.insert(0, settings.get("nominatim_server", "https://nominatim.openstreetmap.org"))

    def _save_settings(self):
        try:
            eff = float(self.e_eff.get())
            price = float(self.e_price.get())
            curr_str = self.e_curr.get().strip()
            osrm = self.e_osrm.get().strip()
            nom = self.e_nom.get().strip()

            self.settings_repo.update_multiple({
                "default_fuel_efficiency": str(eff),
                "default_petrol_price": str(price),
                "currency": "INR",
                "currency_symbol": "₹",
                "osrm_server": osrm,
                "nominatim_server": nom,
            })
            ToastNotification.show(self, "Settings saved successfully!", "success")
            self.on_settings_saved()
        except ValueError as e:
            messagebox.showerror("Validation Error", f"Invalid input values: {e}")

    def _backup_database(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
            initialfile=f"motorcycle_backup_{timestamp}.db",
        )
        if not dest:
            return

        success = self.db.backup_database(dest)
        if success:
            ToastNotification.show(self, f"Backup created successfully: {os.path.basename(dest)}", "success")
        else:
            messagebox.showerror("Backup Failed", "Failed to backup SQLite database.")

    def _restore_database(self):
        if not messagebox.askyesno(
            "Caution: Restore Database",
            "Restoring a database will replace all current vehicle, fuel, maintenance, and trip data with the backup file.\n\nAre you sure you want to proceed?",
        ):
            return

        src = filedialog.askopenfilename(
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if not src:
            return

        success = self.db.restore_database(src)
        if success:
            ToastNotification.show(self, "Database restored successfully!", "success")
            self.on_settings_saved()
        else:
            messagebox.showerror("Restore Failed", "Could not restore the selected database.")

