"""
HF Deluxe Pro Manager - Refuel Model and Repository
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from database.db import DatabaseManager, get_db
from services.fuel_calculator import (
    calculate_fuel_cost,
    recalculate_mileage_series,
    compute_fuel_statistics,
    FuelStats,
)


@dataclass
class Refuel:
    id: Optional[int]
    vehicle_id: int
    date: str
    odometer: float
    fuel_quantity: float
    price_per_litre: float
    total_amount: float
    petrol_station: str = ""
    is_full_tank: int = 1
    calculated_mileage: Optional[float] = None
    distance_travelled: Optional[float] = None
    notes: str = ""
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Refuel":
        return cls(
            id=row["id"],
            vehicle_id=row["vehicle_id"],
            date=row["date"],
            odometer=float(row["odometer"]),
            fuel_quantity=float(row["fuel_quantity"]),
            price_per_litre=float(row["price_per_litre"]),
            total_amount=float(row["total_amount"]),
            petrol_station=row["petrol_station"] or "",
            is_full_tank=int(row["is_full_tank"]),
            calculated_mileage=float(row["calculated_mileage"]) if row["calculated_mileage"] is not None else None,
            distance_travelled=float(row["distance_travelled"]) if row["distance_travelled"] is not None else None,
            notes=row["notes"] or "",
            created_at=row["created_at"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "date": self.date,
            "odometer": self.odometer,
            "fuel_quantity": self.fuel_quantity,
            "price_per_litre": self.price_per_litre,
            "total_amount": self.total_amount,
            "petrol_station": self.petrol_station,
            "is_full_tank": self.is_full_tank,
            "calculated_mileage": self.calculated_mileage,
            "distance_travelled": self.distance_travelled,
            "notes": self.notes,
            "created_at": self.created_at,
        }


class RefuelRepository:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def get_by_id(self, refuel_id: int) -> Optional[Refuel]:
        row = self.db.fetchone("SELECT * FROM refuels WHERE id = ?", (refuel_id,))
        return Refuel.from_row(row) if row else None

    def get_by_vehicle(self, vehicle_id: int, search: str = "") -> List[Refuel]:
        if search:
            pattern = f"%{search.strip()}%"
            rows = self.db.fetchall(
                """
                SELECT * FROM refuels 
                WHERE vehicle_id = ? AND (date LIKE ? OR petrol_station LIKE ? OR notes LIKE ?)
                ORDER BY odometer DESC, date DESC, id DESC
                """,
                (vehicle_id, pattern, pattern, pattern),
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM refuels WHERE vehicle_id = ? ORDER BY odometer DESC, date DESC, id DESC",
                (vehicle_id,),
            )
        return [Refuel.from_row(r) for r in rows]

    def add(self, refuel: Refuel) -> int:
        self._validate_refuel(refuel)
        total_amount = calculate_fuel_cost(refuel.fuel_quantity, refuel.price_per_litre)

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO refuels (
                    vehicle_id, date, odometer, fuel_quantity,
                    price_per_litre, total_amount, petrol_station,
                    is_full_tank, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    refuel.vehicle_id,
                    refuel.date.strip(),
                    refuel.odometer,
                    refuel.fuel_quantity,
                    refuel.price_per_litre,
                    total_amount,
                    refuel.petrol_station.strip(),
                    1 if refuel.is_full_tank else 0,
                    refuel.notes.strip(),
                ),
            )
            refuel_id = cursor.lastrowid or 0

            # Update vehicle current odometer if higher
            conn.execute(
                """
                UPDATE vehicles 
                SET current_odometer = MAX(current_odometer, ?), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (refuel.odometer, refuel.vehicle_id),
            )

        # Recalculate mileage sequence for the vehicle
        self.recalculate_for_vehicle(refuel.vehicle_id)
        return refuel_id

    def update(self, refuel: Refuel) -> bool:
        if refuel.id is None:
            raise ValueError("Refuel ID required for update")
        self._validate_refuel(refuel, updating_id=refuel.id)
        total_amount = calculate_fuel_cost(refuel.fuel_quantity, refuel.price_per_litre)

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE refuels SET
                    date = ?, odometer = ?, fuel_quantity = ?,
                    price_per_litre = ?, total_amount = ?, petrol_station = ?,
                    is_full_tank = ?, notes = ?
                WHERE id = ?
                """,
                (
                    refuel.date.strip(),
                    refuel.odometer,
                    refuel.fuel_quantity,
                    refuel.price_per_litre,
                    total_amount,
                    refuel.petrol_station.strip(),
                    1 if refuel.is_full_tank else 0,
                    refuel.notes.strip(),
                    refuel.id,
                ),
            )
            # Update vehicle current odometer if higher
            conn.execute(
                """
                UPDATE vehicles 
                SET current_odometer = MAX(current_odometer, ?), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (refuel.odometer, refuel.vehicle_id),
            )

        self.recalculate_for_vehicle(refuel.vehicle_id)
        return True

    def delete(self, refuel_id: int) -> bool:
        rec = self.get_by_id(refuel_id)
        if not rec:
            return False
        vehicle_id = rec.vehicle_id
        self.db.execute("DELETE FROM refuels WHERE id = ?", (refuel_id,))
        self.recalculate_for_vehicle(vehicle_id)
        return True

    def recalculate_for_vehicle(self, vehicle_id: int) -> None:
        """Fetch all refuels for the vehicle, recalculate full-to-full mileage, and save back to DB."""
        rows = self.db.fetchall(
            "SELECT * FROM refuels WHERE vehicle_id = ? ORDER BY odometer ASC, date ASC, id ASC",
            (vehicle_id,),
        )
        dict_records = [dict(r) for r in rows]
        processed = recalculate_mileage_series(dict_records)

        with self.db.transaction() as conn:
            for item in processed:
                conn.execute(
                    """
                    UPDATE refuels 
                    SET calculated_mileage = ?, distance_travelled = ?
                    WHERE id = ?
                    """,
                    (item.get("calculated_mileage"), item.get("distance_travelled"), item["id"]),
                )

    def get_stats(self, vehicle_id: int) -> FuelStats:
        """Return aggregate fuel statistics for a vehicle."""
        records = self.get_by_vehicle(vehicle_id)
        dict_records = [r.to_dict() for r in records]
        return compute_fuel_statistics(dict_records)

    def _validate_refuel(self, refuel: Refuel, updating_id: Optional[int] = None) -> None:
        if refuel.fuel_quantity <= 0:
            raise ValueError("Fuel quantity must be greater than zero.")
        if refuel.price_per_litre <= 0:
            raise ValueError("Price per litre must be greater than zero.")
        if refuel.odometer < 0:
            raise ValueError("Odometer reading cannot be negative.")
        if not refuel.date.strip():
            raise ValueError("Date is mandatory.")

