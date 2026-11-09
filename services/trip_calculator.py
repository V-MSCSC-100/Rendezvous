"""
HF Deluxe Pro Manager - Trip Calculator Service
Handles route distance aggregation, fuel consumption and cost estimation,
return trip estimates, and actual vs estimated comparisons.
"""

from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class TripEstimate:
    one_way_distance_km: float
    return_distance_km: float
    total_distance_km: float
    duration_minutes: float
    assumed_mileage: float
    fuel_price: float
    fuel_required_litres: float
    one_way_fuel_cost: float
    return_fuel_cost: float
    total_fuel_cost: float
    cost_per_km: float


@dataclass
class TripComparison:
    estimated_distance: float
    actual_distance: float
    distance_difference: float

    estimated_fuel_litres: float
    actual_fuel_litres: float
    fuel_litres_difference: float

    estimated_fuel_cost: float
    actual_fuel_cost: float
    fuel_cost_difference: float

    estimated_cost_per_km: float
    actual_cost_per_km: float
    cost_per_km_difference: float

    actual_mileage: Optional[float]
    total_actual_expenditure: float  # fuel + toll + parking + additional


def calculate_trip_estimates(
    distance_km: float,
    duration_minutes: float,
    mileage_km_per_l: float,
    petrol_price_per_l: float,
    is_round_trip: bool = False,
) -> TripEstimate:
    """Calculate fuel requirements and expenditures for a planned trip."""
    if distance_km < 0:
        raise ValueError("Distance cannot be negative.")
    if mileage_km_per_l <= 0:
        raise ValueError("Mileage must be greater than zero.")
    if petrol_price_per_l < 0:
        raise ValueError("Petrol price cannot be negative.")

    one_way_fuel = distance_km / mileage_km_per_l
    one_way_cost = one_way_fuel * petrol_price_per_l
    cost_per_km = petrol_price_per_l / mileage_km_per_l

    if is_round_trip:
        total_dist = distance_km * 2.0
        return_dist = distance_km
        total_fuel = one_way_fuel * 2.0
        return_cost = one_way_cost
        total_cost = one_way_cost * 2.0
    else:
        total_dist = distance_km
        return_dist = 0.0
        total_fuel = one_way_fuel
        return_cost = 0.0
        total_cost = one_way_cost

    return TripEstimate(
        one_way_distance_km=round(distance_km, 1),
        return_distance_km=round(return_dist, 1),
        total_distance_km=round(total_dist, 1),
        duration_minutes=round(duration_minutes, 1),
        assumed_mileage=round(mileage_km_per_l, 2),
        fuel_price=round(petrol_price_per_l, 2),
        fuel_required_litres=round(total_fuel, 2),
        one_way_fuel_cost=round(one_way_cost, 2),
        return_fuel_cost=round(return_cost, 2),
        total_fuel_cost=round(total_cost, 2),
        cost_per_km=round(cost_per_km, 2),
    )


def compare_estimated_vs_actual(
    estimated_distance: float,
    estimated_fuel_litres: float,
    estimated_fuel_cost: float,
    estimated_cost_per_km: float,
    actual_distance: float,
    actual_fuel_litres: float,
    actual_fuel_cost: float,
    toll_charges: float = 0.0,
    parking_charges: float = 0.0,
    additional_expenses: float = 0.0,
) -> TripComparison:
    """Calculates variance and comparison metrics between estimated and actual trip results."""
    actual_mileage = (
        round(actual_distance / actual_fuel_litres, 2)
        if (actual_fuel_litres > 0 and actual_distance > 0)
        else None
    )
    total_actual_exp = round(
        actual_fuel_cost + toll_charges + parking_charges + additional_expenses, 2
    )
    actual_cost_per_km = (
        round(total_actual_exp / actual_distance, 2) if actual_distance > 0 else 0.0
    )

    return TripComparison(
        estimated_distance=round(estimated_distance, 1),
        actual_distance=round(actual_distance, 1),
        distance_difference=round(actual_distance - estimated_distance, 1),
        estimated_fuel_litres=round(estimated_fuel_litres, 2),
        actual_fuel_litres=round(actual_fuel_litres, 2),
        fuel_litres_difference=round(actual_fuel_litres - estimated_fuel_litres, 2),
        estimated_fuel_cost=round(estimated_fuel_cost, 2),
        actual_fuel_cost=round(actual_fuel_cost, 2),
        fuel_cost_difference=round(actual_fuel_cost - estimated_fuel_cost, 2),
        estimated_cost_per_km=round(estimated_cost_per_km, 2),
        actual_cost_per_km=round(actual_cost_per_km, 2),
        cost_per_km_difference=round(actual_cost_per_km - estimated_cost_per_km, 2),
        actual_mileage=actual_mileage,
        total_actual_expenditure=total_actual_exp,
    )

