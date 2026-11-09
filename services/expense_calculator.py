"""
HF Deluxe Pro Manager - Expense Calculator Service
Calculates overall ownership expenditure, running cost per km, monthly breakdown, and category distribution.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FinancialSummary:
    purchase_price: float = 0.0
    total_fuel: float = 0.0
    total_maintenance: float = 0.0
    total_parts: float = 0.0
    total_upgrades: float = 0.0
    total_misc: float = 0.0
    total_operational: float = 0.0  # Fuel + Maintenance + Upgrades + Misc
    total_ownership: float = 0.0    # Purchase Price + Total Operational
    total_distance_km: float = 0.0
    cost_per_km: float = 0.0        # Total Operational / Distance
    avg_monthly_expenditure: float = 0.0


def calculate_running_cost_per_km(total_operational_cost: float, total_km: float) -> float:
    """Calculate running cost per kilometre."""
    if total_km <= 0:
        return 0.0
    return round(total_operational_cost / total_km, 2)


def compute_financial_breakdown(
    purchase_price: float,
    current_odometer: float,
    refuel_records: List[Dict[str, Any]],
    service_records: List[Dict[str, Any]],
    upgrade_records: List[Dict[str, Any]],
    expense_records: Optional[List[Dict[str, Any]]] = None,
    filter_start_date: Optional[str] = None,
    filter_end_date: Optional[str] = None,
) -> FinancialSummary:
    """
    Computes complete financial statistics with optional date filtering.
    """
    summary = FinancialSummary(purchase_price=purchase_price, total_distance_km=current_odometer)
    expenses = expense_records or []

    def in_range(date_str: str) -> bool:
        if not date_str:
            return True
        if filter_start_date and date_str < filter_start_date:
            return False
        if filter_end_date and date_str > filter_end_date:
            return False
        return True

    # Fuel sum
    filtered_fuel = [r for r in refuel_records if in_range(r.get("date", ""))]
    summary.total_fuel = round(
        sum(float(r.get("total_amount") or 0.0) for r in filtered_fuel), 2
    )

    # Maintenance sum and parts sum
    filtered_services = [s for s in service_records if in_range(s.get("service_date", ""))]
    summary.total_maintenance = round(
        sum(float(s.get("total_expenditure") or 0.0) for s in filtered_services), 2
    )
    summary.total_parts = round(
        sum(float(s.get("parts_charges") or 0.0) for s in filtered_services), 2
    )

    # Upgrades sum
    filtered_upgrades = [u for u in upgrade_records if in_range(u.get("installation_date", ""))]
    summary.total_upgrades = round(
        sum(float(u.get("cost") or 0.0) for u in filtered_upgrades), 2
    )

    # Miscellaneous expenses sum
    filtered_misc = [e for e in expenses if in_range(e.get("expense_date", ""))]
    summary.total_misc = round(
        sum(float(e.get("amount") or 0.0) for e in filtered_misc), 2
    )

    # Totals
    summary.total_operational = round(
        summary.total_fuel + summary.total_maintenance + summary.total_upgrades + summary.total_misc, 2
    )
    summary.total_ownership = round(summary.purchase_price + summary.total_operational, 2)

    # Cost per km
    summary.cost_per_km = calculate_running_cost_per_km(summary.total_operational, current_odometer)

    # Monthly average calculation
    all_dates = []
    for r in filtered_fuel:
        if r.get("date"):
            all_dates.append(r["date"][:7])  # YYYY-MM
    for s in filtered_services:
        if s.get("service_date"):
            all_dates.append(s["service_date"][:7])
    for u in filtered_upgrades:
        if u.get("installation_date"):
            all_dates.append(u["installation_date"][:7])
    for e in filtered_misc:
        if e.get("expense_date"):
            all_dates.append(e["expense_date"][:7])

    unique_months = set(all_dates)
    num_months = max(1, len(unique_months))
    summary.avg_monthly_expenditure = round(summary.total_operational / num_months, 2)

    return summary

