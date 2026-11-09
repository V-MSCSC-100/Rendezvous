"""
HF Deluxe Pro Manager - Maintenance Calculator Service
Handles service cost calculations, parts total computations, and reminder tracking.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date
from dataclasses import dataclass


@dataclass
class ReminderItem:
    part_name: str
    category: str
    last_service_date: str
    last_odometer: float
    next_due_odometer: Optional[float]
    next_due_date: Optional[str]
    km_remaining: Optional[float]
    days_remaining: Optional[int]
    status: str  # "Overdue", "Due Soon", "Good"
    status_color: str  # Hex color for UI badges


DEFAULT_SERVICE_INTERVALS = {
    "Engine oil replacement": {"km": 3000, "months": 6},
    "Spark plug replacement": {"km": 10000, "months": 12},
    "Air filter replacement": {"km": 8000, "months": 12},
    "Brake servicing": {"km": 5000, "months": 6},
    "Chain maintenance": {"km": 1000, "months": 2},
    "General servicing": {"km": 4000, "months": 6},
    "Tyre replacement": {"km": 25000, "months": 36},
    "Electrical repairs": {"km": 10000, "months": 12},
    "Other repairs": {"km": 5000, "months": 6},
}


def calculate_service_total(labour_charges: float, parts_charges: float) -> float:
    """Calculate total service expenditure: labour + parts."""
    if labour_charges < 0 or parts_charges < 0:
        raise ValueError("Charges cannot be negative.")
    return round(labour_charges + parts_charges, 2)


def calculate_part_total(quantity: int, unit_price: float) -> float:
    """Calculate total price for a part: quantity * unit_price."""
    if quantity < 1:
        raise ValueError("Quantity must be at least 1.")
    if unit_price < 0:
        raise ValueError("Unit price cannot be negative.")
    return round(quantity * unit_price, 2)


def evaluate_reminders(
    current_odometer: float,
    current_date: Optional[date] = None,
    parts_records: Optional[List[Dict[str, Any]]] = None,
) -> List[ReminderItem]:
    """
    Evaluates upcoming and overdue maintenance reminders for parts/services
    based on current odometer and date.
    """
    today = current_date or date.today()
    reminders: List[ReminderItem] = []

    if not parts_records:
        return reminders

    for p in parts_records:
        part_name = p.get("part_name", "Service Item")
        rep_date_str = p.get("replacement_date", "")
        last_odo = float(p.get("last_odometer") or p.get("odometer") or 0.0)
        next_due_odo = p.get("next_recommended_odometer")
        if next_due_odo is not None:
            next_due_odo = float(next_due_odo)
        interval_km = p.get("replacement_interval_km")
        if interval_km:
            interval_km = float(interval_km)
            if next_due_odo is None and last_odo > 0:
                next_due_odo = last_odo + interval_km

        km_rem: Optional[float] = None
        if next_due_odo is not None:
            km_rem = round(next_due_odo - current_odometer, 1)

        days_rem: Optional[int] = None
        next_due_date_str: Optional[str] = None
        interval_months = p.get("replacement_interval_months")
        if interval_months and rep_date_str:
            try:
                rep_d = datetime.strptime(rep_date_str, "%Y-%m-%d").date()
                approx_days = int(interval_months * 30.4)
                target_d = date.fromordinal(rep_d.toordinal() + approx_days)
                next_due_date_str = target_d.isoformat()
                days_rem = (target_d - today).days
            except ValueError:
                pass

        # Determine status
        is_overdue = False
        is_due_soon = False

        if km_rem is not None:
            if km_rem <= 0:
                is_overdue = True
            elif km_rem <= 500:
                is_due_soon = True

        if days_rem is not None:
            if days_rem <= 0:
                is_overdue = True
            elif days_rem <= 15:
                is_due_soon = True

        if is_overdue:
            status = "Overdue"
            color = "#ef4444"  # Red
        elif is_due_soon:
            status = "Due Soon"
            color = "#f59e0b"  # Amber/Yellow
        else:
            status = "Good"
            color = "#10b981"  # Green

        reminders.append(
            ReminderItem(
                part_name=part_name,
                category=p.get("category", "General"),
                last_service_date=rep_date_str,
                last_odometer=last_odo,
                next_due_odometer=next_due_odo,
                next_due_date=next_due_date_str,
                km_remaining=km_rem,
                days_remaining=days_rem,
                status=status,
                status_color=color,
            )
        )

    # Sort reminders so Overdue comes first, then Due Soon, then Good
    priority = {"Overdue": 0, "Due Soon": 1, "Good": 2}
    reminders.sort(key=lambda x: (priority.get(x.status, 3), x.km_remaining if x.km_remaining is not None else 999999))
    return reminders

