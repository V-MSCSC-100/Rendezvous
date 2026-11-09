"""
HF Deluxe Pro Manager - Maintenance and Parts Model and Repository
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from database.db import DatabaseManager, get_db
from services.maintenance_calculator import (
    calculate_service_total,
    calculate_part_total,
    evaluate_reminders,
    ReminderItem,
    DEFAULT_SERVICE_INTERVALS,
)


@dataclass
class ServicePart:
    id: Optional[int]
    vehicle_id: int
    part_name: str
    quantity: int
    unit_price: float
    total_price: float
    replacement_date: str
    service_id: Optional[int] = None
    next_recommended_odometer: Optional[float] = None
    replacement_interval_km: Optional[float] = None
    replacement_interval_months: Optional[int] = None
    notes: str = ""
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "ServicePart":
        return cls(
            id=row["id"],
            service_id=row["service_id"],
            vehicle_id=row["vehicle_id"],
            part_name=row["part_name"],
            quantity=int(row["quantity"]),
            unit_price=float(row["unit_price"]),
            total_price=float(row["total_price"]),
            replacement_date=row["replacement_date"],
            next_recommended_odometer=(
                float(row["next_recommended_odometer"])
                if row["next_recommended_odometer"] is not None
                else None
            ),
            replacement_interval_km=(
                float(row["replacement_interval_km"])
                if row["replacement_interval_km"] is not None
                else None
            ),
            replacement_interval_months=(
                int(row["replacement_interval_months"])
                if row["replacement_interval_months"] is not None
                else None
            ),
            notes=row["notes"] or "",
            created_at=row["created_at"],
        )


@dataclass
class ServiceRecord:
    id: Optional[int]
    vehicle_id: int
    service_date: str
    odometer: float
    category: str
    description: str = ""
    labour_charges: float = 0.0
    parts_charges: float = 0.0
    total_expenditure: float = 0.0
    workshop_name: str = ""
    notes: str = ""
    created_at: Optional[str] = None
    parts: Optional[List[ServicePart]] = None

    @classmethod
    def from_row(cls, row, parts: Optional[List[ServicePart]] = None) -> "ServiceRecord":
        return cls(
            id=row["id"],
            vehicle_id=row["vehicle_id"],
            service_date=row["service_date"],
            odometer=float(row["odometer"]),
            category=row["category"],
            description=row["description"] or "",
            labour_charges=float(row["labour_charges"]),
            parts_charges=float(row["parts_charges"]),
            total_expenditure=float(row["total_expenditure"]),
            workshop_name=row["workshop_name"] or "",
            notes=row["notes"] or "",
            created_at=row["created_at"],
            parts=parts or [],
        )


class MaintenanceRepository:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def get_service_by_id(self, service_id: int) -> Optional[ServiceRecord]:
        row = self.db.fetchone("SELECT * FROM services WHERE id = ?", (service_id,))
        if not row:
            return None
        parts = self.get_parts_for_service(service_id)
        return ServiceRecord.from_row(row, parts=parts)

    def get_services_by_vehicle(
        self, vehicle_id: int, search: str = "", category: str = ""
    ) -> List[ServiceRecord]:
        query = "SELECT * FROM services WHERE vehicle_id = ?"
        params: List[Any] = [vehicle_id]

        if category and category != "All":
            query += " AND category = ?"
            params.append(category)

        if search:
            query += " AND (description LIKE ? OR workshop_name LIKE ? OR notes LIKE ?)"
            pat = f"%{search.strip()}%"
            params.extend([pat, pat, pat])

        query += " ORDER BY odometer DESC, service_date DESC, id DESC"
        rows = self.db.fetchall(query, tuple(params))
        result = []
        for r in rows:
            parts = self.get_parts_for_service(r["id"])
            result.append(ServiceRecord.from_row(r, parts=parts))
        return result

    def get_parts_for_service(self, service_id: int) -> List[ServicePart]:
        rows = self.db.fetchall(
            "SELECT * FROM parts WHERE service_id = ? ORDER BY id ASC", (service_id,)
        )
        return [ServicePart.from_row(r) for r in rows]

    def get_all_parts_by_vehicle(self, vehicle_id: int) -> List[ServicePart]:
        rows = self.db.fetchall(
            "SELECT * FROM parts WHERE vehicle_id = ? ORDER BY replacement_date DESC, id DESC",
            (vehicle_id,),
        )
        return [ServicePart.from_row(r) for r in rows]

    def add_service(
        self, service: ServiceRecord, parts: Optional[List[ServicePart]] = None
    ) -> int:
        parts_list = parts or []
        parts_sum = sum(p.total_price for p in parts_list)
        total_exp = calculate_service_total(service.labour_charges, parts_sum)

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO services (
                    vehicle_id, service_date, odometer, category,
                    description, labour_charges, parts_charges,
                    total_expenditure, workshop_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service.vehicle_id,
                    service.service_date.strip(),
                    service.odometer,
                    service.category.strip(),
                    service.description.strip(),
                    service.labour_charges,
                    parts_sum,
                    total_exp,
                    service.workshop_name.strip(),
                    service.notes.strip(),
                ),
            )
            service_id = cursor.lastrowid or 0

            # Insert parts linked to this service
            for p in parts_list:
                cursor.execute(
                    """
                    INSERT INTO parts (
                        service_id, vehicle_id, part_name, quantity,
                        unit_price, total_price, replacement_date,
                        next_recommended_odometer, replacement_interval_km,
                        replacement_interval_months, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        service_id,
                        service.vehicle_id,
                        p.part_name.strip(),
                        p.quantity,
                        p.unit_price,
                        p.total_price,
                        p.replacement_date.strip() or service.service_date.strip(),
                        p.next_recommended_odometer,
                        p.replacement_interval_km,
                        p.replacement_interval_months,
                        p.notes.strip(),
                    ),
                )

            # Update vehicle odometer if higher
            conn.execute(
                """
                UPDATE vehicles 
                SET current_odometer = MAX(current_odometer, ?), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (service.odometer, service.vehicle_id),
            )

        return service_id

    def update_service(
        self, service: ServiceRecord, parts: Optional[List[ServicePart]] = None
    ) -> bool:
        if service.id is None:
            raise ValueError("Service ID required for update")

        parts_list = parts if parts is not None else self.get_parts_for_service(service.id)
        parts_sum = sum(p.total_price for p in parts_list)
        total_exp = calculate_service_total(service.labour_charges, parts_sum)

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE services SET
                    service_date = ?, odometer = ?, category = ?,
                    description = ?, labour_charges = ?, parts_charges = ?,
                    total_expenditure = ?, workshop_name = ?, notes = ?
                WHERE id = ?
                """,
                (
                    service.service_date.strip(),
                    service.odometer,
                    service.category.strip(),
                    service.description.strip(),
                    service.labour_charges,
                    parts_sum,
                    total_exp,
                    service.workshop_name.strip(),
                    service.notes.strip(),
                    service.id,
                ),
            )

            # If parts list was explicitly provided, replace parts
            if parts is not None:
                conn.execute("DELETE FROM parts WHERE service_id = ?", (service.id,))
                for p in parts_list:
                    conn.execute(
                        """
                        INSERT INTO parts (
                            service_id, vehicle_id, part_name, quantity,
                            unit_price, total_price, replacement_date,
                            next_recommended_odometer, replacement_interval_km,
                            replacement_interval_months, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            service.id,
                            service.vehicle_id,
                            p.part_name.strip(),
                            p.quantity,
                            p.unit_price,
                            p.total_price,
                            p.replacement_date.strip() or service.service_date.strip(),
                            p.next_recommended_odometer,
                            p.replacement_interval_km,
                            p.replacement_interval_months,
                            p.notes.strip(),
                        ),
                    )

            # Update vehicle odometer if higher
            conn.execute(
                """
                UPDATE vehicles 
                SET current_odometer = MAX(current_odometer, ?), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (service.odometer, service.vehicle_id),
            )

        return True

    def delete_service(self, service_id: int) -> bool:
        self.db.execute("DELETE FROM services WHERE id = ?", (service_id,))
        return True

    def get_maintenance_reminders(self, vehicle_id: int) -> List[ReminderItem]:
        """Fetch parts and services to evaluate upcoming and overdue maintenance."""
        v_row = self.db.fetchone(
            "SELECT current_odometer FROM vehicles WHERE id = ?", (vehicle_id,)
        )
        current_odo = float(v_row["current_odometer"]) if v_row else 0.0

        # Query parts with their replacement information
        query = """
            SELECT p.part_name, p.replacement_date, p.next_recommended_odometer,
                   p.replacement_interval_km, p.replacement_interval_months,
                   COALESCE(s.odometer, 0.0) as last_odometer,
                   COALESCE(s.category, 'General') as category
            FROM parts p
            LEFT JOIN services s ON p.service_id = s.id
            WHERE p.vehicle_id = ?
        """
        rows = self.db.fetchall(query, (vehicle_id,))
        parts_data = [dict(r) for r in rows]

        # Also add default periodic reminders (e.g. Engine Oil, Spark Plug) if not already tracked
        existing_part_names = {p["part_name"].lower() for p in parts_data}
        for category, info in DEFAULT_SERVICE_INTERVALS.items():
            if category.lower() not in existing_part_names:
                # Find last service with this category if any
                last_s = self.db.fetchone(
                    "SELECT service_date, odometer FROM services WHERE vehicle_id = ? AND category = ? ORDER BY odometer DESC LIMIT 1",
                    (vehicle_id, category),
                )
                last_odo = float(last_s["odometer"]) if last_s else 0.0
                last_date = last_s["service_date"] if last_s else "2023-01-01"
                next_odo = last_odo + info["km"]
                parts_data.append(
                    {
                        "part_name": category,
                        "category": category,
                        "replacement_date": last_date,
                        "last_odometer": last_odo,
                        "next_recommended_odometer": next_odo,
                        "replacement_interval_km": info["km"],
                        "replacement_interval_months": info["months"],
                    }
                )

        return evaluate_reminders(current_odo, parts_records=parts_data)

