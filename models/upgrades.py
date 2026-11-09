"""
HF Deluxe Pro Manager - Parts and Upgrades Model and Repository
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from database.db import DatabaseManager, get_db


@dataclass
class Upgrade:
    id: Optional[int]
    vehicle_id: int
    upgrade_name: str
    category: str
    description: str
    installation_date: str
    odometer: Optional[float]
    cost: float
    vendor: str = ""
    notes: str = ""
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Upgrade":
        return cls(
            id=row["id"],
            vehicle_id=row["vehicle_id"],
            upgrade_name=row["upgrade_name"],
            category=row["category"] or "Accessories",
            description=row["description"] or "",
            installation_date=row["installation_date"],
            odometer=float(row["odometer"]) if row["odometer"] is not None else None,
            cost=float(row["cost"]),
            vendor=row["vendor"] or "",
            notes=row["notes"] or "",
            created_at=row["created_at"],
        )


class UpgradeRepository:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def get_by_id(self, upgrade_id: int) -> Optional[Upgrade]:
        row = self.db.fetchone("SELECT * FROM upgrades WHERE id = ?", (upgrade_id,))
        return Upgrade.from_row(row) if row else None

    def get_by_vehicle(
        self, vehicle_id: int, search: str = "", category: str = ""
    ) -> List[Upgrade]:
        query = "SELECT * FROM upgrades WHERE vehicle_id = ?"
        params: List[Any] = [vehicle_id]

        if category and category != "All":
            query += " AND category = ?"
            params.append(category)

        if search:
            query += " AND (upgrade_name LIKE ? OR vendor LIKE ? OR description LIKE ? OR notes LIKE ?)"
            pat = f"%{search.strip()}%"
            params.extend([pat, pat, pat, pat])

        query += " ORDER BY installation_date DESC, id DESC"
        rows = self.db.fetchall(query, tuple(params))
        return [Upgrade.from_row(r) for r in rows]

    def add(self, upgrade: Upgrade) -> int:
        if upgrade.cost < 0:
            raise ValueError("Upgrade cost cannot be negative.")
        if not upgrade.upgrade_name.strip():
            raise ValueError("Upgrade name cannot be empty.")
        if not upgrade.installation_date.strip():
            raise ValueError("Installation date is mandatory.")

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO upgrades (
                    vehicle_id, upgrade_name, category, description,
                    installation_date, odometer, cost, vendor, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    upgrade.vehicle_id,
                    upgrade.upgrade_name.strip(),
                    upgrade.category.strip(),
                    upgrade.description.strip(),
                    upgrade.installation_date.strip(),
                    upgrade.odometer,
                    upgrade.cost,
                    upgrade.vendor.strip(),
                    upgrade.notes.strip(),
                ),
            )
            upgrade_id = cursor.lastrowid or 0

            if upgrade.odometer is not None:
                conn.execute(
                    """
                    UPDATE vehicles 
                    SET current_odometer = MAX(current_odometer, ?), updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (upgrade.odometer, upgrade.vehicle_id),
                )

        return upgrade_id

    def update(self, upgrade: Upgrade) -> bool:
        if upgrade.id is None:
            raise ValueError("Upgrade ID is required for update.")
        if upgrade.cost < 0:
            raise ValueError("Upgrade cost cannot be negative.")
        if not upgrade.upgrade_name.strip():
            raise ValueError("Upgrade name cannot be empty.")

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE upgrades SET
                    upgrade_name = ?, category = ?, description = ?,
                    installation_date = ?, odometer = ?, cost = ?,
                    vendor = ?, notes = ?
                WHERE id = ?
                """,
                (
                    upgrade.upgrade_name.strip(),
                    upgrade.category.strip(),
                    upgrade.description.strip(),
                    upgrade.installation_date.strip(),
                    upgrade.odometer,
                    upgrade.cost,
                    upgrade.vendor.strip(),
                    upgrade.notes.strip(),
                    upgrade.id,
                ),
            )
            if upgrade.odometer is not None:
                conn.execute(
                    """
                    UPDATE vehicles 
                    SET current_odometer = MAX(current_odometer, ?), updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (upgrade.odometer, upgrade.vehicle_id),
                )
        return True

    def delete(self, upgrade_id: int) -> bool:
        self.db.execute("DELETE FROM upgrades WHERE id = ?", (upgrade_id,))
        return True

    def get_total_cost(self, vehicle_id: int) -> float:
        row = self.db.fetchone(
            "SELECT COALESCE(SUM(cost), 0.0) as total FROM upgrades WHERE vehicle_id = ?",
            (vehicle_id,),
        )
        return float(row["total"]) if row else 0.0

