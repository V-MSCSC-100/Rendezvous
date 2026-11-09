"""
HF Deluxe Pro Manager - Fuel Calculator Service
Handles full-to-full mileage computation, partial refill accumulation, and fuel statistics.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class FuelStats:
    latest_mileage: Optional[float] = None
    lifetime_avg_mileage: Optional[float] = None
    best_mileage: Optional[float] = None
    lowest_mileage: Optional[float] = None
    total_litres: float = 0.0
    total_expenditure: float = 0.0
    average_price: float = 0.0
    refuel_count: int = 0
    total_fuel_distance: float = 0.0


def calculate_fuel_cost(litres: float, price_per_litre: float) -> float:
    """Calculate total fuel cost: litres * price_per_litre."""
    if litres < 0 or price_per_litre < 0:
        raise ValueError("Litres and price per litre must be non-negative.")
    return round(litres * price_per_litre, 2)


def recalculate_mileage_series(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Given a list of refuel records (as dicts or objects), recalculates full-to-full
    mileage chronologically, properly accumulating any partial refills between full tanks.

    Each record must have:
      - 'id': int
      - 'date': str
      - 'odometer': float
      - 'fuel_quantity': float
      - 'price_per_litre': float
      - 'is_full_tank': bool or int (1/0)
    
    Returns updated records with 'calculated_mileage' and 'distance_travelled'.
    """
    if not records:
        return []

    # Sort chronologically by odometer, then date, then id
    sorted_records = sorted(
        records,
        key=lambda r: (float(r["odometer"]), str(r["date"]), int(r.get("id") or 0))
    )

    last_full_record: Optional[Dict[str, Any]] = None
    accumulated_litres: float = 0.0

    for rec in sorted_records:
        rec_is_full = bool(rec.get("is_full_tank", 1))
        qty = float(rec["fuel_quantity"])
        odo = float(rec["odometer"])

        if last_full_record is None:
            # We haven't encountered our first full tank baseline yet
            if rec_is_full:
                last_full_record = rec
                accumulated_litres = 0.0
                rec["calculated_mileage"] = None
                rec["distance_travelled"] = None
            else:
                # Partial refill before any full tank cannot establish baseline
                rec["calculated_mileage"] = None
                rec["distance_travelled"] = None
        else:
            # We have a baseline full tank
            accumulated_litres += qty
            if rec_is_full:
                distance = odo - float(last_full_record["odometer"])
                if distance > 0 and accumulated_litres > 0:
                    mileage = round(distance / accumulated_litres, 2)
                    rec["calculated_mileage"] = mileage
                    rec["distance_travelled"] = round(distance, 1)
                else:
                    rec["calculated_mileage"] = None
                    rec["distance_travelled"] = None
                
                # Update baseline to this new full tank
                last_full_record = rec
                accumulated_litres = 0.0
            else:
                # Partial refill accumulates towards the next full tank
                rec["calculated_mileage"] = None
                rec["distance_travelled"] = None

    return sorted_records


def compute_fuel_statistics(records: List[Dict[str, Any]]) -> FuelStats:
    """Calculate aggregate fuel statistics across refuel records."""
    stats = FuelStats()
    stats.refuel_count = len(records)
    if not records:
        return stats

    processed = recalculate_mileage_series(records)
    valid_mileages = [
        r["calculated_mileage"]
        for r in processed
        if r.get("calculated_mileage") is not None and r["calculated_mileage"] > 0
    ]

    total_litres = sum(float(r["fuel_quantity"]) for r in processed)
    total_expenditure = sum(float(r.get("total_amount") or (float(r["fuel_quantity"]) * float(r["price_per_litre"]))) for r in processed)
    
    stats.total_litres = round(total_litres, 2)
    stats.total_expenditure = round(total_expenditure, 2)
    stats.average_price = round(total_expenditure / total_litres, 2) if total_litres > 0 else 0.0

    if valid_mileages:
        stats.latest_mileage = valid_mileages[-1]
        stats.best_mileage = round(max(valid_mileages), 2)
        stats.lowest_mileage = round(min(valid_mileages), 2)
        
        # Calculate lifetime average mileage: total valid distance / total litres consumed across full-tank legs
        total_dist = sum(r["distance_travelled"] for r in processed if r.get("distance_travelled") is not None)
        stats.total_fuel_distance = round(total_dist, 1)
        stats.lifetime_avg_mileage = round(sum(valid_mileages) / len(valid_mileages), 2)

    return stats

