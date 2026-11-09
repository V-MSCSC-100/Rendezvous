"""
HF Deluxe Pro Manager - Database Management Module
Handles SQLite connection, schema migrations, seed data, transactions, and backups.
"""

import os
import sqlite3
import shutil
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("hf_manager.db")

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "motorcycle.db"
)
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")


class DatabaseManager:
    """Central SQLite database manager ensuring thread-safe access, transactions, and integrity."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._memory_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False, timeout=30.0)
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self.initialize_database()

    def get_connection(self) -> sqlite3.Connection:
        """Create and return a configured SQLite connection with foreign keys enabled."""
        if self._memory_conn is not None:
            return self._memory_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def transaction(self):
        """Context manager for atomic database transactions with automatic rollback on error."""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error("Transaction rolled back due to error: %s", e)
            raise
        finally:
            if self._memory_conn is None:
                conn.close()

    def execute(self, query: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a query and commit immediately."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
        finally:
            if self._memory_conn is None:
                conn.close()

    def executemany(self, query: str, params_list: List[Tuple[Any, ...]]) -> sqlite3.Cursor:
        """Execute a query across multiple parameter tuples atomically."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return cursor
        finally:
            if self._memory_conn is None:
                conn.close()

    def insert(self, query: str, params: Tuple[Any, ...] = ()) -> int:
        """Execute an INSERT query and return the last inserted row ID."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            if self._memory_conn is None:
                conn.close()

    def fetchone(self, query: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        """Execute a query and fetch a single row."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            if self._memory_conn is None:
                conn.close()

    def fetchall(self, query: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        """Execute a query and fetch all rows."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            if self._memory_conn is None:
                conn.close()

    def initialize_database(self) -> None:
        """Apply schema and initial seed data if not already present."""
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()
        else:
            raise FileNotFoundError(f"Schema file not found at: {SCHEMA_PATH}")

        with self.get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()

        # Seed initial vehicle and settings if vehicles table is empty
        self._seed_initial_data()

    def _seed_initial_data(self) -> None:
        """Seed default Hero HF Deluxe Pro motorcycle and settings if not present."""
        vehicle_count = self.fetchone("SELECT COUNT(*) as cnt FROM vehicles")
        if vehicle_count and vehicle_count["cnt"] == 0:
            self.insert(
                """
                INSERT INTO vehicles (
                    name, manufacturer, model, registration_number,
                    purchase_date, purchase_price, current_odometer,
                    engine_capacity, fuel_type, notes, is_default
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "My HF Deluxe Pro",
                    "Hero",
                    "HF Deluxe Pro",
                    "DL-01-AB-1234",
                    "2023-01-15",
                    68000.0,
                    1500.0,
                    97.2,
                    "Petrol",
                    "Hero HF Deluxe Pro - 97.2cc, 4-stroke single cylinder, xSens FI technology",
                    1,
                ),
            )
            logger.info("Seeded initial Hero HF Deluxe Pro vehicle.")

        # Seed initial app settings
        default_settings = [
            ("default_vehicle_id", "1"),
            ("default_fuel_efficiency", "65.0"),
            ("default_petrol_price", "102.50"),
            ("currency", "INR"),
            ("currency_symbol", "₹"),
            ("distance_unit", "km"),
            ("theme", "dark"),
            ("osrm_server", "https://router.project-osrm.org"),
            ("nominatim_server", "https://nominatim.openstreetmap.org"),
        ]
        with self.get_connection() as conn:
            for key, val in default_settings:
                conn.execute(
                    "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", (key, val)
                )
            conn.commit()

    def backup_database(self, backup_filepath: str) -> bool:
        """Create a safe SQLite live backup using the online backup API."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(backup_filepath)), exist_ok=True)
            source_conn = self.get_connection()
            dest_conn = sqlite3.connect(backup_filepath)
            with dest_conn:
                source_conn.backup(dest_conn)
            dest_conn.close()
            source_conn.close()
            logger.info("Database backed up successfully to %s", backup_filepath)
            return True
        except Exception as e:
            logger.error("Database backup failed: %s", e)
            return False

    def restore_database(self, backup_filepath: str) -> bool:
        """Restore database from a backup file."""
        if not os.path.exists(backup_filepath):
            raise FileNotFoundError(f"Backup file not found: {backup_filepath}")
        try:
            dest_conn = self.get_connection()
            source_conn = sqlite3.connect(backup_filepath)
            with dest_conn:
                source_conn.backup(dest_conn)
            source_conn.close()
            dest_conn.close()
            logger.info("Database restored successfully from %s", backup_filepath)
            return True
        except Exception as e:
            logger.error("Database restore failed: %s", e)
            return False


# Global singleton instance for application use
_default_db_manager: Optional[DatabaseManager] = None


def get_db(db_path: Optional[str] = None) -> DatabaseManager:
    """Get or create the global DatabaseManager instance."""
    global _default_db_manager
    if db_path is not None:
        return DatabaseManager(db_path)
    if _default_db_manager is None:
        _default_db_manager = DatabaseManager()
    return _default_db_manager
