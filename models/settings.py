"""
HF Deluxe Pro Manager - App Settings Model and Repository
"""

from typing import Optional, Dict, Any
from database.db import DatabaseManager, get_db


class SettingsRepository:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def get(self, key: str, default: str = "") -> str:
        row = self.db.fetchone("SELECT value FROM app_settings WHERE key = ?", (key,))
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, str(value))
        )

    def get_all(self) -> Dict[str, str]:
        rows = self.db.fetchall("SELECT key, value FROM app_settings")
        return {r["key"]: r["value"] for r in rows}

    def update_multiple(self, settings_dict: Dict[str, Any]) -> None:
        with self.db.transaction() as conn:
            for k, v in settings_dict.items():
                conn.execute(
                    "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                    (k, str(v)),
                )

