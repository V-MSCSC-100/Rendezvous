"""
Unit tests for HF Deluxe Pro Manager - Phase 1 Foundation & Business Logic
"""

import unittest
from database.db import DatabaseManager
from models.vehicle import Vehicle, VehicleRepository
from models.fuel import Refuel, RefuelRepository
from models.maintenance import ServiceRecord, ServicePart, MaintenanceRepository
from models.upgrades import Upgrade, UpgradeRepository
from models.expense import Expense, ExpenseRepository
from models.trips import Trip, TripWaypoint, TripRepository
from services.fuel_calculator import (
    calculate_fuel_cost,
    recalculate_mileage_series,
    compute_fuel_statistics,
)
from services.maintenance_calculator import (
    calculate_service_total,
    calculate_part_total,
    evaluate_reminders,
)
from services.trip_calculator import (
    calculate_trip_estimates,
    compare_estimated_vs_actual,
)
from services.expense_calculator import (
    calculate_running_cost_per_km,
    compute_financial_breakdown,
)


class TestPhase1Foundation(unittest.TestCase):
    def setUp(self):
        # Fresh in-memory database for isolation
        self.db = DatabaseManager(":memory:")
        self.vehicle_repo = VehicleRepository(self.db)
        self.fuel_repo = RefuelRepository(self.db)
        self.maint_repo = MaintenanceRepository(self.db)
        self.upgrade_repo = UpgradeRepository(self.db)
        self.expense_repo = ExpenseRepository(self.db)
        self.trip_repo = TripRepository(self.db)

    def test_database_initialization_and_seed(self):
        vehicles = self.vehicle_repo.get_all()
        self.assertEqual(len(vehicles), 1)
        v = vehicles[0]
        self.assertEqual(v.manufacturer, "Hero")
        self.assertEqual(v.model, "HF Deluxe Pro")
        self.assertEqual(v.is_default, 1)

    def test_vehicle_crud(self):
        new_v = Vehicle(
            id=None,
            name="Second Bike",
            manufacturer="Hero",
            model="Splendor Plus",
            registration_number="MH-02-CD-5678",
            purchase_date="2023-05-10",
            purchase_price=72000.0,
            current_odometer=500.0,
            engine_capacity=97.2,
            fuel_type="Petrol",
            notes="Second motorcycle",
            is_default=0,
        )
        vid = self.vehicle_repo.create(new_v)
        self.assertIsNotNone(vid)
        self.assertEqual(len(self.vehicle_repo.get_all()), 2)

        fetched = self.vehicle_repo.get_by_id(vid)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Second Bike")

        # Update
        fetched.name = "Updated Second Bike"
        self.vehicle_repo.update(fetched)
        updated = self.vehicle_repo.get_by_id(vid)
        self.assertEqual(updated.name, "Updated Second Bike")

        # Delete
        self.vehicle_repo.delete(vid)
        self.assertEqual(len(self.vehicle_repo.get_all()), 1)

    def test_cannot_delete_only_vehicle(self):
        vehicles = self.vehicle_repo.get_all()
        sole_id = vehicles[0].id
        with self.assertRaises(ValueError):
            self.vehicle_repo.delete(sole_id)

    def test_fuel_cost_calculation(self):
        cost = calculate_fuel_cost(5.5, 102.50)
        self.assertEqual(cost, 563.75)
        with self.assertRaises(ValueError):
            calculate_fuel_cost(-1.0, 100.0)

    def test_full_to_full_mileage_calculation_with_partials(self):
        """
        Verify:
        1. Full tank at 1000 km, 9L -> Baseline (no mileage yet)
        2. Partial refill at 1150 km, 3L -> Mileage is None (accumulated 3L)
        3. Full tank at 1350 km, 4L -> Distance = 350 km, Litres = 7L, Mileage = 50.0 km/l
        4. Full tank at 1700 km, 5L -> Distance = 350 km, Litres = 5L, Mileage = 70.0 km/l
        """
        records = [
            {"id": 1, "date": "2023-01-01", "odometer": 1000, "fuel_quantity": 9.0, "price_per_litre": 100, "is_full_tank": 1},
            {"id": 2, "date": "2023-01-05", "odometer": 1150, "fuel_quantity": 3.0, "price_per_litre": 100, "is_full_tank": 0},
            {"id": 3, "date": "2023-01-10", "odometer": 1350, "fuel_quantity": 4.0, "price_per_litre": 100, "is_full_tank": 1},
            {"id": 4, "date": "2023-01-15", "odometer": 1700, "fuel_quantity": 5.0, "price_per_litre": 100, "is_full_tank": 1},
        ]
        processed = recalculate_mileage_series(records)
        self.assertIsNone(processed[0]["calculated_mileage"])
        self.assertIsNone(processed[1]["calculated_mileage"])
        self.assertEqual(processed[2]["calculated_mileage"], 50.0)
        self.assertEqual(processed[2]["distance_travelled"], 350.0)
        self.assertEqual(processed[3]["calculated_mileage"], 70.0)
        self.assertEqual(processed[3]["distance_travelled"], 350.0)

        stats = compute_fuel_statistics(processed)
        self.assertEqual(stats.best_mileage, 70.0)
        self.assertEqual(stats.lowest_mileage, 50.0)
        self.assertEqual(stats.latest_mileage, 70.0)
        self.assertEqual(stats.lifetime_avg_mileage, 60.0)

    def test_maintenance_and_reminders(self):
        default_v = self.vehicle_repo.get_default_vehicle()
        vid = default_v.id

        service = ServiceRecord(
            id=None,
            vehicle_id=vid,
            service_date="2023-06-01",
            odometer=3000.0,
            category="Engine oil replacement",
            description="First periodic service and oil change",
            labour_charges=250.0,
            parts_charges=0.0,
            workshop_name="Hero Authorized Service Center",
        )
        part = ServicePart(
            id=None,
            vehicle_id=vid,
            part_name="Hero 4T Plus 10W-30 Oil",
            quantity=1,
            unit_price=350.0,
            total_price=350.0,
            replacement_date="2023-06-01",
            next_recommended_odometer=6000.0,
            replacement_interval_km=3000.0,
            replacement_interval_months=6,
        )
        sid = self.maint_repo.add_service(service, [part])
        self.assertIsNotNone(sid)

        # Vehicle odometer should have updated to 3000.0
        v_updated = self.vehicle_repo.get_by_id(vid)
        self.assertEqual(v_updated.current_odometer, 3000.0)

        # Check reminders when current odometer is 5800 (due soon, within 200 km of 6000)
        reminders = evaluate_reminders(
            current_odometer=5800.0,
            parts_records=[
                {
                    "part_name": "Engine Oil",
                    "replacement_date": "2026-10-01",
                    "odometer": 3000.0,
                    "next_recommended_odometer": 6000.0,
                    "replacement_interval_km": 3000.0,
                    "replacement_interval_months": 6,
                }
            ],
        )
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0].status, "Due Soon")
        self.assertEqual(reminders[0].km_remaining, 200.0)

    def test_upgrades_crud(self):
        default_v = self.vehicle_repo.get_default_vehicle()
        upgrade = Upgrade(
            id=None,
            vehicle_id=default_v.id,
            upgrade_name="LED Headlight Bulb",
            category="Lighting",
            description="Philips 6000K White LED",
            installation_date="2023-04-10",
            odometer=2000.0,
            cost=850.0,
            vendor="Amazon / Local Shop",
        )
        uid = self.upgrade_repo.add(upgrade)
        self.assertIsNotNone(uid)
        total_upg = self.upgrade_repo.get_total_cost(default_v.id)
        self.assertEqual(total_upg, 850.0)

    def test_trip_estimates_and_comparisons(self):
        est = calculate_trip_estimates(
            distance_km=150.0,
            duration_minutes=180.0,
            mileage_km_per_l=65.0,
            petrol_price_per_l=100.0,
            is_round_trip=False,
        )
        self.assertEqual(est.one_way_distance_km, 150.0)
        self.assertAlmostEqual(est.fuel_required_litres, 2.31, places=2)
        self.assertAlmostEqual(est.total_fuel_cost, 230.77, places=1)

        # Comparison
        comp = compare_estimated_vs_actual(
            estimated_distance=150.0,
            estimated_fuel_litres=2.31,
            estimated_fuel_cost=230.77,
            estimated_cost_per_km=1.54,
            actual_distance=160.0,
            actual_fuel_litres=2.5,
            actual_fuel_cost=255.0,
            toll_charges=50.0,
        )
        self.assertEqual(comp.distance_difference, 10.0)
        self.assertEqual(comp.actual_mileage, 64.0)
        self.assertEqual(comp.total_actual_expenditure, 305.0)


if __name__ == "__main__":
    unittest.main()
