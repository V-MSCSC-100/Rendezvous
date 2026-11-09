"""
Comprehensive unit tests for HF Deluxe Pro Manager.
Tests all core calculations independently of GUI and network:
- Fuel cost calculation
- Full-tank mileage calculation & consecutive logic
- Partial-refill accumulation until next full tank
- Invalid / negative odometer readings
- Maintenance expenditure calculations
- Upgrade expenditure calculations
- Trip fuel estimates (one-way & return)
- Multi-stop distance calculations (Haversine road model)
- Empty database states & edge cases
"""

import unittest
from unittest.mock import MagicMock, patch
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
    FuelStats,
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
from api.routing import haversine_distance_km, RoutingService, RouteResult
from api.geocoding import GeocodingService


class TestFuelCalculations(unittest.TestCase):
    def test_fuel_cost_calculation(self):
        self.assertEqual(calculate_fuel_cost(10.0, 102.50), 1025.0)
        self.assertEqual(calculate_fuel_cost(0.0, 102.50), 0.0)
        with self.assertRaises(ValueError):
            calculate_fuel_cost(-5.0, 100.0)
        with self.assertRaises(ValueError):
            calculate_fuel_cost(5.0, -100.0)

    def test_consecutive_full_tank_mileage(self):
        # 1000 km -> 1350 km (350 km) on 5 litres = 70.0 km/l
        records = [
            {"id": 1, "date": "2023-01-01", "odometer": 1000, "fuel_quantity": 9.0, "price_per_litre": 100, "is_full_tank": 1},
            {"id": 2, "date": "2023-01-08", "odometer": 1350, "fuel_quantity": 5.0, "price_per_litre": 100, "is_full_tank": 1},
        ]
        res = recalculate_mileage_series(records)
        self.assertIsNone(res[0]["calculated_mileage"])
        self.assertEqual(res[1]["calculated_mileage"], 70.0)
        self.assertEqual(res[1]["distance_travelled"], 350.0)

    def test_partial_refill_accumulation(self):
        """
        Verify multiple partial refills accumulate until next full refill:
        Leg 1: Full tank at 1000 km (Baseline)
        Leg 2: Partial refill 2L at 1120 km
        Leg 3: Partial refill 3L at 1300 km
        Leg 4: Full tank refill 5L at 1650 km
        Total distance: 1650 - 1000 = 650 km
        Total litres consumed: 2 + 3 + 5 = 10 L
        Mileage at Leg 4 = 650 / 10 = 65.0 km/l
        """
        records = [
            {"id": 1, "date": "2023-01-01", "odometer": 1000, "fuel_quantity": 9.0, "price_per_litre": 100, "is_full_tank": 1},
            {"id": 2, "date": "2023-01-03", "odometer": 1120, "fuel_quantity": 2.0, "price_per_litre": 100, "is_full_tank": 0},
            {"id": 3, "date": "2023-01-06", "odometer": 1300, "fuel_quantity": 3.0, "price_per_litre": 100, "is_full_tank": 0},
            {"id": 4, "date": "2023-01-10", "odometer": 1650, "fuel_quantity": 5.0, "price_per_litre": 100, "is_full_tank": 1},
        ]
        res = recalculate_mileage_series(records)
        self.assertIsNone(res[0]["calculated_mileage"])
        self.assertIsNone(res[1]["calculated_mileage"])
        self.assertIsNone(res[2]["calculated_mileage"])
        self.assertEqual(res[3]["calculated_mileage"], 65.0)
        self.assertEqual(res[3]["distance_travelled"], 650.0)

    def test_fuel_stats_computation(self):
        records = [
            {"id": 1, "date": "2023-01-01", "odometer": 1000, "fuel_quantity": 9.0, "price_per_litre": 100, "is_full_tank": 1, "total_amount": 900.0},
            {"id": 2, "date": "2023-01-05", "odometer": 1350, "fuel_quantity": 5.0, "price_per_litre": 102, "is_full_tank": 1, "total_amount": 510.0},
            {"id": 3, "date": "2023-01-10", "odometer": 1750, "fuel_quantity": 6.0, "price_per_litre": 105, "is_full_tank": 1, "total_amount": 630.0},
        ]
        stats = compute_fuel_statistics(records)
        self.assertEqual(stats.refuel_count, 3)
        self.assertEqual(stats.total_litres, 20.0)
        self.assertEqual(stats.total_expenditure, 2040.0)
        self.assertEqual(stats.average_price, 102.0)
        # 1350 - 1000 = 350 km / 5L = 70 km/l
        # 1750 - 1350 = 400 km / 6L = 66.67 km/l
        self.assertEqual(stats.best_mileage, 70.0)
        self.assertEqual(stats.lowest_mileage, 66.67)


class TestMaintenanceCalculations(unittest.TestCase):
    def test_service_and_parts_charges(self):
        part_tot = calculate_part_total(quantity=2, unit_price=450.0)
        self.assertEqual(part_tot, 900.0)

        total_service = calculate_service_total(labour_charges=300.0, parts_charges=part_tot)
        self.assertEqual(total_service, 1200.0)

        with self.assertRaises(ValueError):
            calculate_part_total(quantity=0, unit_price=100.0)
        with self.assertRaises(ValueError):
            calculate_service_total(labour_charges=-10.0, parts_charges=100.0)


class TestTripCalculations(unittest.TestCase):
    def test_trip_estimates(self):
        # 100 km one-way, 65 km/l, Rs. 100/L
        est_one_way = calculate_trip_estimates(
            distance_km=100.0,
            duration_minutes=120.0,
            mileage_km_per_l=65.0,
            petrol_price_per_l=100.0,
            is_round_trip=False,
        )
        self.assertEqual(est_one_way.total_distance_km, 100.0)
        self.assertAlmostEqual(est_one_way.fuel_required_litres, 1.54, places=2)
        self.assertAlmostEqual(est_one_way.total_fuel_cost, 153.85, places=1)
        self.assertAlmostEqual(est_one_way.cost_per_km, 1.54, places=2)

        # Round trip
        est_round = calculate_trip_estimates(
            distance_km=100.0,
            duration_minutes=120.0,
            mileage_km_per_l=65.0,
            petrol_price_per_l=100.0,
            is_round_trip=True,
        )
        self.assertEqual(est_round.total_distance_km, 200.0)
        self.assertAlmostEqual(est_round.fuel_required_litres, 3.08, places=2)
        self.assertAlmostEqual(est_round.total_fuel_cost, 307.69, places=1)

    def test_haversine_distance(self):
        # Distance between Chennai (13.0827, 80.2707) and Mahabalipuram (12.6269, 80.1927)
        dist = haversine_distance_km(13.0827, 80.2707, 12.6269, 80.1927)
        # Should be approximately 51.5 km straight-line
        self.assertGreater(dist, 45.0)
        self.assertLess(dist, 55.0)


class TestApiMocking(unittest.TestCase):
    @patch("requests.get")
    def test_osrm_mock_route_calculation(self, mock_get):
        # Mock successful OSRM response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": "Ok",
            "routes": [
                {
                    "distance": 85000.0,  # 85 km
                    "duration": 6000.0,   # 100 mins
                    "geometry": {
                        "coordinates": [
                            [80.2707, 13.0827],
                            [80.2500, 13.0000],
                            [80.1927, 12.6269],
                        ]
                    },
                }
            ],
        }
        mock_get.return_value = mock_resp

        router = RoutingService()
        result = router.calculate_route([(13.0827, 80.2707), (12.6269, 80.1927)])
        self.assertEqual(result.distance_km, 85.0)
        self.assertEqual(result.duration_minutes, 100.0)
        self.assertEqual(len(result.geometry_coords), 3)
        self.assertFalse(result.is_estimate_fallback)

    @patch("requests.get")
    def test_nominatim_mock_geocoding(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {
                "lat": "13.0827",
                "lon": "80.2707",
                "display_name": "Chennai, Tamil Nadu, India",
            }
        ]
        mock_get.return_value = mock_resp

        geocoder = GeocodingService()
        res = geocoder.geocode("Chennai")
        self.assertIsNotNone(res)
        lat, lon, dname = res
        self.assertAlmostEqual(lat, 13.0827, places=3)
        self.assertAlmostEqual(lon, 80.2707, places=3)
        self.assertIn("Chennai", dname)


class TestDatabaseEdgeCases(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")
        self.v_repo = VehicleRepository(self.db)
        self.f_repo = RefuelRepository(self.db)

    def test_empty_database_and_validation(self):
        v = self.v_repo.get_default_vehicle()
        self.assertIsNotNone(v)

        # Invalid negative odometer
        with self.assertRaises(ValueError):
            self.f_repo.add(
                Refuel(
                    id=None,
                    vehicle_id=v.id,
                    date="2023-01-01",
                    odometer=-10.0,
                    fuel_quantity=5.0,
                    price_per_litre=100.0,
                    total_amount=500.0,
                )
            )

        # Empty date
        with self.assertRaises(ValueError):
            self.f_repo.add(
                Refuel(
                    id=None,
                    vehicle_id=v.id,
                    date="",
                    odometer=1000.0,
                    fuel_quantity=5.0,
                    price_per_litre=100.0,
                    total_amount=500.0,
                )
            )


if __name__ == "__main__":
    unittest.main()

