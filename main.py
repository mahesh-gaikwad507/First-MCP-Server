
import sqlite3
from pathlib import Path
from datetime import date
from typing import TypedDict

from fastmcp import FastMCP


# --------------------------------------------------
# Initialize MCP Server
# --------------------------------------------------

mcp = FastMCP("Expense Tracker MCP Server")


# --------------------------------------------------
# Database Configuration
# --------------------------------------------------

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "expenses.db"


# --------------------------------------------------
# Explicit Output Schemas
# --------------------------------------------------

class Expense(TypedDict):
    id: int
    date: str
    amount: float
    category: str
    subcategory: str
    note: str


class CategorySummary(TypedDict):
    category: str
    total: float
    number_of_expenses: int


class ExpenseResponse(TypedDict):
    status: str
    expense_id: int
    message: str


class DeleteResponse(TypedDict):
    status: str
    message: str


# --------------------------------------------------
# Database Setup
# --------------------------------------------------

def setup_database():
    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            note TEXT
        )
    """)

    conn.commit()
    conn.close()


# --------------------------------------------------
# Tool 1: Add Expense
# --------------------------------------------------

@mcp.tool()
def add_expense(
    amount: float,
    category: str,
    date_value: str = "",
    subcategory: str = "",
    note: str = ""
) -> ExpenseResponse:
    """
    Add a new expense to the expense tracker.
    """

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    expense_date = date_value or date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO expenses
        (date, amount, category, subcategory, note)
        VALUES (?, ?, ?, ?, ?)
    """, (
        expense_date,
        amount,
        category,
        subcategory,
        note
    ))

    expense_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "expense_id": expense_id,
        "message": "Expense added successfully."
    }


# --------------------------------------------------
# Tool 2: List Expenses
# --------------------------------------------------

@mcp.tool()
def list_expenses(
    start_date: str = "",
    end_date: str = ""
) -> list[Expense]:
    """
    List all expenses.

    Optionally filter expenses using start_date
    and end_date in YYYY-MM-DD format.
    """

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    query = "SELECT * FROM expenses WHERE 1=1"

    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += " ORDER BY date DESC"

    cursor.execute(query, params)

    expenses = []

    for row in cursor.fetchall():
        expenses.append({
            "id": row["id"],
            "date": row["date"],
            "amount": row["amount"],
            "category": row["category"],
            "subcategory": row["subcategory"] or "",
            "note": row["note"] or ""
        })

    conn.close()

    return expenses


# --------------------------------------------------
# Tool 3: Delete Expense
# --------------------------------------------------

@mcp.tool()
def delete_expense(
    expense_id: int
) -> DeleteResponse:
    """
    Delete an expense using its unique ID.
    """

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM expenses WHERE id = ?",
        (expense_id,)
    )

    deleted = cursor.rowcount

    conn.commit()
    conn.close()

    if deleted == 0:
        return {
            "status": "error",
            "message": "Expense not found."
        }

    return {
        "status": "success",
        "message": "Expense deleted successfully."
    }


# --------------------------------------------------
# Tool 4: Summarize Expenses
# --------------------------------------------------

@mcp.tool()
def summarize_expenses(
    start_date: str = "",
    end_date: str = ""
) -> list[CategorySummary]:
    """
    Calculate total expenses grouped by category.

    Optionally filter the summary using a date range.
    """

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    query = """
        SELECT
            category,
            SUM(amount) AS total,
            COUNT(*) AS number_of_expenses
        FROM expenses
        WHERE 1=1
    """

    params = []

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    query += """
        GROUP BY category
        ORDER BY total DESC
    """

    cursor.execute(query, params)

    results = []

    for row in cursor.fetchall():
        results.append({
            "category": row[0],
            "total": row[1],
            "number_of_expenses": row[2]
        })

    conn.close()

    return results


# --------------------------------------------------
# Initialize Database
# --------------------------------------------------

setup_database()


# --------------------------------------------------
# Run MCP Server
# --------------------------------------------------

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )
