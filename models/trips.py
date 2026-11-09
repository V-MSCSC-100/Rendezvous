"""
HF Deluxe Pro Manager - Trip and Waypoint Model and Repository
"""

import json
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from database.db import DatabaseManager, get_db
from services.trip_calculator import compare_estimated_vs_actual, TripComparison


@dataclass
class TripWaypoint:
    id: Optional[int]
    trip_id: int
    sequence_order: int
    location_name: str
    latitude: float
    longitude: float
    stop_type: str = "Stop"  # Start, Stop, Destination
    notes: str = ""

    @classmethod
    def from_row(cls, row) -> "TripWaypoint":
        return cls(
            id=row["id"],
            trip_id=row["trip_id"],
            sequence_order=int(row["sequence_order"]),
            location_name=row["location_name"],
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            stop_type=row["stop_type"] or "Stop",
            notes=row["notes"] or "",
        )


@dataclass
class Trip:
    id: Optional[int]
    vehicle_id: int
    title: str
    start_location: str
    destination: str
    status: str  # Planned, Completed, Cancelled
    start_date: str
    end_date: str = ""
    is_round_trip: int = 0
    estimated_distance: float = 0.0
    estimated_duration: float = 0.0
    assumed_mileage: float = 65.0
    petrol_price_used: float = 102.0
    estimated_fuel_litres: float = 0.0
    estimated_fuel_cost: float = 0.0
    estimated_cost_per_km: float = 0.0
    actual_start_odometer: Optional[float] = None
    actual_end_odometer: Optional[float] = None
    actual_distance: Optional[float] = None
    actual_fuel_litres: Optional[float] = None
    actual_fuel_cost: Optional[float] = None
    toll_charges: float = 0.0
    parking_charges: float = 0.0
    additional_expenses: float = 0.0
    actual_cost_per_km: Optional[float] = None
    actual_mileage: Optional[float] = None
    notes: str = ""
    route_geometry_json: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    waypoints: Optional[List[TripWaypoint]] = None

    @classmethod
    def from_row(cls, row, waypoints: Optional[List[TripWaypoint]] = None) -> "Trip":
        return cls(
            id=row["id"],
            vehicle_id=row["vehicle_id"],
            title=row["title"],
            start_location=row["start_location"],
            destination=row["destination"],
            status=row["status"] or "Planned",
            start_date=row["start_date"],
            end_date=row["end_date"] or "",
            is_round_trip=int(row["is_round_trip"]),
            estimated_distance=float(row["estimated_distance"]),
            estimated_duration=float(row["estimated_duration"]),
            assumed_mileage=float(row["assumed_mileage"]),
            petrol_price_used=float(row["petrol_price_used"]),
            estimated_fuel_litres=float(row["estimated_fuel_litres"]),
            estimated_fuel_cost=float(row["estimated_fuel_cost"]),
            estimated_cost_per_km=float(row["estimated_cost_per_km"]),
            actual_start_odometer=(
                float(row["actual_start_odometer"])
                if row["actual_start_odometer"] is not None
                else None
            ),
            actual_end_odometer=(
                float(row["actual_end_odometer"])
                if row["actual_end_odometer"] is not None
                else None
            ),
            actual_distance=(
                float(row["actual_distance"])
                if row["actual_distance"] is not None
                else None
            ),
            actual_fuel_litres=(
                float(row["actual_fuel_litres"])
                if row["actual_fuel_litres"] is not None
                else None
            ),
            actual_fuel_cost=(
                float(row["actual_fuel_cost"])
                if row["actual_fuel_cost"] is not None
                else None
            ),
            toll_charges=float(row["toll_charges"]),
            parking_charges=float(row["parking_charges"]),
            additional_expenses=float(row["additional_expenses"]),
            actual_cost_per_km=(
                float(row["actual_cost_per_km"])
                if row["actual_cost_per_km"] is not None
                else None
            ),
            actual_mileage=(
                float(row["actual_mileage"])
                if row["actual_mileage"] is not None
                else None
            ),
            notes=row["notes"] or "",
            route_geometry_json=row["route_geometry_json"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            waypoints=waypoints or [],
        )


@dataclass
class SavedLocation:
    id: Optional[int]
    name: str
    address: str
    latitude: float
    longitude: float
    category: str = "General"
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "SavedLocation":
        return cls(
            id=row["id"],
            name=row["name"],
            address=row["address"] or "",
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            category=row["category"] or "General",
            created_at=row["created_at"],
        )


class TripRepository:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def get_by_id(self, trip_id: int) -> Optional[Trip]:
        row = self.db.fetchone("SELECT * FROM trips WHERE id = ?", (trip_id,))
        if not row:
            return None
        waypoints = self.get_waypoints_for_trip(trip_id)
        return Trip.from_row(row, waypoints=waypoints)

    def get_by_vehicle(
        self, vehicle_id: int, status: Optional[str] = None, search: str = ""
    ) -> List[Trip]:
        query = "SELECT * FROM trips WHERE vehicle_id = ?"
        params: List[Any] = [vehicle_id]

        if status and status != "All":
            query += " AND status = ?"
            params.append(status)

        if search:
            query += " AND (title LIKE ? OR start_location LIKE ? OR destination LIKE ? OR notes LIKE ?)"
            pat = f"%{search.strip()}%"
            params.extend([pat, pat, pat, pat])

        query += " ORDER BY start_date DESC, id DESC"
        rows = self.db.fetchall(query, tuple(params))
        result = []
        for r in rows:
            wps = self.get_waypoints_for_trip(r["id"])
            result.append(Trip.from_row(r, waypoints=wps))
        return result

    def get_waypoints_for_trip(self, trip_id: int) -> List[TripWaypoint]:
        rows = self.db.fetchall(
            "SELECT * FROM trip_waypoints WHERE trip_id = ? ORDER BY sequence_order ASC",
            (trip_id,),
        )
        return [TripWaypoint.from_row(r) for r in rows]

    def add(self, trip: Trip, waypoints: Optional[List[TripWaypoint]] = None) -> int:
        if not trip.title.strip():
            raise ValueError("Trip title cannot be empty.")
        if not trip.start_location.strip() or not trip.destination.strip():
            raise ValueError("Start location and destination are required.")

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO trips (
                    vehicle_id, title, start_location, destination, status,
                    start_date, end_date, is_round_trip, estimated_distance,
                    estimated_duration, assumed_mileage, petrol_price_used,
                    estimated_fuel_litres, estimated_fuel_cost, estimated_cost_per_km,
                    notes, route_geometry_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trip.vehicle_id,
                    trip.title.strip(),
                    trip.start_location.strip(),
                    trip.destination.strip(),
                    trip.status,
                    trip.start_date.strip(),
                    trip.end_date.strip(),
                    1 if trip.is_round_trip else 0,
                    trip.estimated_distance,
                    trip.estimated_duration,
                    trip.assumed_mileage,
                    trip.petrol_price_used,
                    trip.estimated_fuel_litres,
                    trip.estimated_fuel_cost,
                    trip.estimated_cost_per_km,
                    trip.notes.strip(),
                    trip.route_geometry_json,
                ),
            )
            trip_id = cursor.lastrowid or 0

            # Insert waypoints
            if waypoints:
                for idx, wp in enumerate(waypoints):
                    cursor.execute(
                        """
                        INSERT INTO trip_waypoints (
                            trip_id, sequence_order, location_name, latitude, longitude, stop_type, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            trip_id,
                            idx,
                            wp.location_name.strip(),
                            wp.latitude,
                            wp.longitude,
                            wp.stop_type,
                            wp.notes.strip(),
                        ),
                    )

        return trip_id

    def update(self, trip: Trip, waypoints: Optional[List[TripWaypoint]] = None) -> bool:
        if trip.id is None:
            raise ValueError("Trip ID required for update.")

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE trips SET
                    title = ?, start_location = ?, destination = ?, status = ?,
                    start_date = ?, end_date = ?, is_round_trip = ?,
                    estimated_distance = ?, estimated_duration = ?,
                    assumed_mileage = ?, petrol_price_used = ?,
                    estimated_fuel_litres = ?, estimated_fuel_cost = ?,
                    estimated_cost_per_km = ?, notes = ?, route_geometry_json = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    trip.title.strip(),
                    trip.start_location.strip(),
                    trip.destination.strip(),
                    trip.status,
                    trip.start_date.strip(),
                    trip.end_date.strip(),
                    1 if trip.is_round_trip else 0,
                    trip.estimated_distance,
                    trip.estimated_duration,
                    trip.assumed_mileage,
                    trip.petrol_price_used,
                    trip.estimated_fuel_litres,
                    trip.estimated_fuel_cost,
                    trip.estimated_cost_per_km,
                    trip.notes.strip(),
                    trip.route_geometry_json,
                    trip.id,
                ),
            )
            if waypoints is not None:
                conn.execute("DELETE FROM trip_waypoints WHERE trip_id = ?", (trip.id,))
                for idx, wp in enumerate(waypoints):
                    conn.execute(
                        """
                        INSERT INTO trip_waypoints (
                            trip_id, sequence_order, location_name, latitude, longitude, stop_type, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            trip.id,
                            idx,
                            wp.location_name.strip(),
                            wp.latitude,
                            wp.longitude,
                            wp.stop_type,
                            wp.notes.strip(),
                        ),
                    )
        return True

    def complete_trip(
        self,
        trip_id: int,
        actual_start_odo: float,
        actual_end_odo: float,
        actual_fuel_litres: float,
        actual_fuel_cost: float,
        toll_charges: float = 0.0,
        parking_charges: float = 0.0,
        additional_expenses: float = 0.0,
        notes: str = "",
        create_refuel_entry: bool = False,
    ) -> bool:
        """Mark trip as completed and compute actual stats."""
        trip = self.get_by_id(trip_id)
        if not trip:
            raise ValueError(f"Trip #{trip_id} not found.")

        actual_distance = max(0.0, round(actual_end_odo - actual_start_odo, 1))
        actual_mileage = (
            round(actual_distance / actual_fuel_litres, 2)
            if (actual_fuel_litres > 0 and actual_distance > 0)
            else None
        )
        total_trip_exp = actual_fuel_cost + toll_charges + parking_charges + additional_expenses
        actual_cost_per_km = (
            round(total_trip_exp / actual_distance, 2) if actual_distance > 0 else 0.0
        )

        with self.db.transaction() as conn:
            conn.execute(
                """
                UPDATE trips SET
                    status = 'Completed',
                    actual_start_odometer = ?,
                    actual_end_odometer = ?,
                    actual_distance = ?,
                    actual_fuel_litres = ?,
                    actual_fuel_cost = ?,
                    toll_charges = ?,
                    parking_charges = ?,
                    additional_expenses = ?,
                    actual_cost_per_km = ?,
                    actual_mileage = ?,
                    notes = CASE WHEN ? != '' THEN ? ELSE notes END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    actual_start_odo,
                    actual_end_odo,
                    actual_distance,
                    actual_fuel_litres,
                    actual_fuel_cost,
                    toll_charges,
                    parking_charges,
                    additional_expenses,
                    actual_cost_per_km,
                    actual_mileage,
                    notes.strip(),
                    notes.strip(),
                    trip_id,
                ),
            )

            # Update vehicle current odometer if higher
            conn.execute(
                """
                UPDATE vehicles 
                SET current_odometer = MAX(current_odometer, ?), updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (actual_end_odo, trip.vehicle_id),
            )

            # Optionally create refuel record
            if create_refuel_entry and actual_fuel_litres > 0 and actual_fuel_cost > 0:
                price_per_l = round(actual_fuel_cost / actual_fuel_litres, 2)
                conn.execute(
                    """
                    INSERT INTO refuels (
                        vehicle_id, date, odometer, fuel_quantity,
                        price_per_litre, total_amount, petrol_station,
                        is_full_tank, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    """,
                    (
                        trip.vehicle_id,
                        trip.start_date,
                        actual_end_odo,
                        actual_fuel_litres,
                        price_per_l,
                        actual_fuel_cost,
                        "Trip Refuel",
                        f"Auto-logged from completed trip: {trip.title}",
                    ),
                )

        return True

    def delete(self, trip_id: int) -> bool:
        self.db.execute("DELETE FROM trips WHERE id = ?", (trip_id,))
        return True

    def get_trip_comparison(self, trip_id: int) -> Optional[TripComparison]:
        trip = self.get_by_id(trip_id)
        if not trip or trip.status != "Completed":
            return None
        return compare_estimated_vs_actual(
            estimated_distance=trip.estimated_distance,
            estimated_fuel_litres=trip.estimated_fuel_litres,
            estimated_fuel_cost=trip.estimated_fuel_cost,
            estimated_cost_per_km=trip.estimated_cost_per_km,
            actual_distance=trip.actual_distance or 0.0,
            actual_fuel_litres=trip.actual_fuel_litres or 0.0,
            actual_fuel_cost=trip.actual_fuel_cost or 0.0,
            toll_charges=trip.toll_charges,
            parking_charges=trip.parking_charges,
            additional_expenses=trip.additional_expenses,
        )

    # Saved Locations
    def get_saved_locations(self) -> List[SavedLocation]:
        rows = self.db.fetchall("SELECT * FROM saved_locations ORDER BY name ASC")
        return [SavedLocation.from_row(r) for r in rows]

    def add_saved_location(
        self, name: str, address: str, latitude: float, longitude: float, category: str = "General"
    ) -> int:
        return self.db.insert(
            """
            INSERT OR REPLACE INTO saved_locations (name, address, latitude, longitude, category)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name.strip(), address.strip(), latitude, longitude, category.strip()),
        )

    def delete_saved_location(self, loc_id: int) -> bool:
        self.db.execute("DELETE FROM saved_locations WHERE id = ?", (loc_id,))
        return True

