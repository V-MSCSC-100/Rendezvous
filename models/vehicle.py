"""
HF Deluxe Pro Manager - Vehicle Model and Repository
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from database.db import DatabaseManager, get_db


@dataclass
class Vehicle:
    id: Optional[int]
    name: str
    manufacturer: str
    model: str
    registration_number: str
    purchase_date: str
    purchase_price: float
    current_odometer: float
    engine_capacity: float
    fuel_type: str
    notes: str = ""
    is_default: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Vehicle":
        if row is None:
            raise ValueError("Row cannot be None")
        return cls(
            id=row["id"],
            name=row["name"],
            manufacturer=row["manufacturer"],
            model=row["model"],
            registration_number=row["registration_number"],
            purchase_date=row["purchase_date"],
            purchase_price=float(row["purchase_price"]),
            current_odometer=float(row["current_odometer"]),
            engine_capacity=float(row["engine_capacity"]),
            fuel_type=row["fuel_type"],
            notes=row["notes"] or "",
            is_default=int(row["is_default"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class VehicleRepository:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def get_by_id(self, vehicle_id: int) -> Optional[Vehicle]:
        row = self.db.fetchone("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
        return Vehicle.from_row(row) if row else None

    def get_all(self) -> List[Vehicle]:
        rows = self.db.fetchall("SELECT * FROM vehicles ORDER BY is_default DESC, id ASC")
        return [Vehicle.from_row(r) for r in rows]

    def get_default_vehicle(self) -> Optional[Vehicle]:
        row = self.db.fetchone("SELECT * FROM vehicles WHERE is_default = 1 LIMIT 1")
        if not row:
            row = self.db.fetchone("SELECT * FROM vehicles ORDER BY id ASC LIMIT 1")
        return Vehicle.from_row(row) if row else None

    def create(self, vehicle: Vehicle) -> int:
        if vehicle.purchase_price < 0:
            raise ValueError("Purchase price cannot be negative")
        if vehicle.current_odometer < 0:
            raise ValueError("Odometer reading cannot be negative")
        if not vehicle.registration_number.strip():
            raise ValueError("Registration number cannot be empty")

        # If marked default, unset existing defaults
        if vehicle.is_default:
            self.db.execute("UPDATE vehicles SET is_default = 0")

        vehicle_id = self.db.insert(
            """
            INSERT INTO vehicles (
                name, manufacturer, model, registration_number,
                purchase_date, purchase_price, current_odometer,
                engine_capacity, fuel_type, notes, is_default
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                vehicle.name.strip(),
                vehicle.manufacturer.strip(),
                vehicle.model.strip(),
                vehicle.registration_number.strip().upper(),
                vehicle.purchase_date.strip(),
                vehicle.purchase_price,
                vehicle.current_odometer,
                vehicle.engine_capacity,
                vehicle.fuel_type.strip(),
                vehicle.notes.strip(),
                1 if vehicle.is_default else 0,
            ),
        )
        return vehicle_id

    def update(self, vehicle: Vehicle) -> bool:
        if vehicle.id is None:
            raise ValueError("Vehicle ID is required for update")
        if vehicle.purchase_price < 0:
            raise ValueError("Purchase price cannot be negative")
        if vehicle.current_odometer < 0:
            raise ValueError("Odometer reading cannot be negative")

        if vehicle.is_default:
            self.db.execute("UPDATE vehicles SET is_default = 0 WHERE id != ?", (vehicle.id,))

        self.db.execute(
            """
            UPDATE vehicles SET
                name = ?, manufacturer = ?, model = ?, registration_number = ?,
                purchase_date = ?, purchase_price = ?, current_odometer = ?,
                engine_capacity = ?, fuel_type = ?, notes = ?, is_default = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                vehicle.name.strip(),
                vehicle.manufacturer.strip(),
                vehicle.model.strip(),
                vehicle.registration_number.strip().upper(),
                vehicle.purchase_date.strip(),
                vehicle.purchase_price,
                vehicle.current_odometer,
                vehicle.engine_capacity,
                vehicle.fuel_type.strip(),
                vehicle.notes.strip(),
                1 if vehicle.is_default else 0,
                vehicle.id,
            ),
        )
        return True

    def set_default(self, vehicle_id: int) -> bool:
        with self.db.transaction() as conn:
            conn.execute("UPDATE vehicles SET is_default = 0")
            conn.execute("UPDATE vehicles SET is_default = 1 WHERE id = ?", (vehicle_id,))
        return True

    def delete(self, vehicle_id: int) -> bool:
        count_row = self.db.fetchone("SELECT COUNT(*) as cnt FROM vehicles")
        if count_row and count_row["cnt"] <= 1:
            raise ValueError("Cannot delete the only registered vehicle.")

        self.db.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
        # Ensure at least one default remains
        def_row = self.db.fetchone("SELECT id FROM vehicles WHERE is_default = 1")
        if not def_row:
            first_v = self.db.fetchone("SELECT id FROM vehicles ORDER BY id ASC LIMIT 1")
            if first_v:
                self.set_default(first_v["id"])
        return True

    def update_odometer(self, vehicle_id: int, new_odometer: float) -> bool:
        current = self.get_by_id(vehicle_id)
        if not current:
            return False
        if new_odometer > current.current_odometer:
            self.db.execute(
                "UPDATE vehicles SET current_odometer = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (new_odometer, vehicle_id),
            )
        return True

