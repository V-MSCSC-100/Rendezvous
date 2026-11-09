"""
HF Deluxe Pro Manager - Expenses Model and Repository
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from database.db import DatabaseManager, get_db
from services.expense_calculator import compute_financial_breakdown, FinancialSummary


@dataclass
class Expense:
    id: Optional[int]
    vehicle_id: int
    expense_date: str
    category: str
    amount: float
    odometer: Optional[float] = None
    notes: str = ""
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Expense":
        return cls(
            id=row["id"],
            vehicle_id=row["vehicle_id"],
            expense_date=row["expense_date"],
            category=row["category"],
            amount=float(row["amount"]),
            odometer=float(row["odometer"]) if row["odometer"] is not None else None,
            notes=row["notes"] or "",
            created_at=row["created_at"],
        )


class ExpenseRepository:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def get_by_id(self, expense_id: int) -> Optional[Expense]:
        row = self.db.fetchone("SELECT * FROM expenses WHERE id = ?", (expense_id,))
        return Expense.from_row(row) if row else None

    def get_by_vehicle(
        self, vehicle_id: int, search: str = "", category: str = ""
    ) -> List[Expense]:
        query = "SELECT * FROM expenses WHERE vehicle_id = ?"
        params: List[Any] = [vehicle_id]

        if category and category != "All":
            query += " AND category = ?"
            params.append(category)

        if search:
            query += " AND (notes LIKE ? OR category LIKE ?)"
            pat = f"%{search.strip()}%"
            params.extend([pat, pat])

        query += " ORDER BY expense_date DESC, id DESC"
        rows = self.db.fetchall(query, tuple(params))
        return [Expense.from_row(r) for r in rows]

    def add(self, exp: Expense) -> int:
        if exp.amount < 0:
            raise ValueError("Expense amount cannot be negative.")
        if not exp.expense_date.strip():
            raise ValueError("Expense date is mandatory.")

        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO expenses (vehicle_id, expense_date, category, amount, odometer, notes)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    exp.vehicle_id,
                    exp.expense_date.strip(),
                    exp.category.strip(),
                    exp.amount,
                    exp.odometer,
                    exp.notes.strip(),
                ),
            )
            exp_id = cursor.lastrowid or 0
            if exp.odometer is not None:
                conn.execute(
                    """
                    UPDATE vehicles 
                    SET current_odometer = MAX(current_odometer, ?), updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (exp.odometer, exp.vehicle_id),
                )
        return exp_id

    def delete(self, expense_id: int) -> bool:
        self.db.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return True

    def get_full_financial_summary(
        self,
        vehicle_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> FinancialSummary:
        v_row = self.db.fetchone("SELECT * FROM vehicles WHERE id = ?", (vehicle_id,))
        if not v_row:
            return FinancialSummary()

        purchase_price = float(v_row["purchase_price"])
        current_odometer = float(v_row["current_odometer"])

        refuels = [dict(r) for r in self.db.fetchall("SELECT * FROM refuels WHERE vehicle_id = ?", (vehicle_id,))]
        services = [dict(r) for r in self.db.fetchall("SELECT * FROM services WHERE vehicle_id = ?", (vehicle_id,))]
        upgrades = [dict(r) for r in self.db.fetchall("SELECT * FROM upgrades WHERE vehicle_id = ?", (vehicle_id,))]
        misc = [dict(r) for r in self.db.fetchall("SELECT * FROM expenses WHERE vehicle_id = ?", (vehicle_id,))]

        return compute_financial_breakdown(
            purchase_price=purchase_price,
            current_odometer=current_odometer,
            refuel_records=refuels,
            service_records=services,
            upgrade_records=upgrades,
            expense_records=misc,
            filter_start_date=start_date,
            filter_end_date=end_date,
        )

