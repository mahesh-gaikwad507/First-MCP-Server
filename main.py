
import os
import sqlite3
import tempfile

from pathlib import Path
from datetime import date
from contextlib import closing
from typing import TypedDict

from fastmcp import FastMCP


# --------------------------------------------------
# Initialize MCP Server
# --------------------------------------------------

mcp = FastMCP("Expense Tracker MCP Server")


# --------------------------------------------------
# Database Configuration
# --------------------------------------------------

# Use a writable temporary directory by default.
# Set DATA_DIR to a persistent mounted directory
# when deploying with persistent storage.

DEFAULT_DATA_DIR = Path(tempfile.gettempdir()) / "expense_tracker_data"

DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))

DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "expenses.db"


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
# Database Connection Helper
# --------------------------------------------------

def get_connection():
    """
    Create a SQLite connection.
    """

    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30
    )

    conn.execute("PRAGMA busy_timeout = 30000")

    return conn


# --------------------------------------------------
# Date Validation Helper
# --------------------------------------------------

def validate_date(date_value: str):
    """
    Validate date in YYYY-MM-DD format.
    """

    if date_value:
        try:
            date.fromisoformat(date_value)
        except ValueError:
            raise ValueError(
                "Invalid date. Use YYYY-MM-DD format."
            )

    return date_value


# --------------------------------------------------
# Database Setup
# --------------------------------------------------

def setup_database():
    """
    Create database directory and expenses table.
    """

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with closing(get_connection()) as conn:

        with conn:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS expenses (

                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    date TEXT NOT NULL,

                    amount REAL NOT NULL,

                    category TEXT NOT NULL,

                    subcategory TEXT DEFAULT '',

                    note TEXT DEFAULT ''

                )
            """)

    print(f"Database initialized: {DB_PATH}")


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

    Parameters:
        amount: Expense amount.
        category: Expense category.
        date_value: Date in YYYY-MM-DD format.
        subcategory: Optional subcategory.
        note: Optional expense description.
    """

    if amount <= 0:
        raise ValueError(
            "Amount must be greater than zero."
        )

    if not category or not category.strip():
        raise ValueError(
            "Category cannot be empty."
        )

    expense_date = date_value or date.today().isoformat()

    validate_date(expense_date)

    with closing(get_connection()) as conn:

        with conn:

            cursor = conn.execute("""
                INSERT INTO expenses
                (date, amount, category, subcategory, note)

                VALUES (?, ?, ?, ?, ?)
            """, (
                expense_date,
                amount,
                category.strip(),
                subcategory.strip(),
                note.strip()
            ))

            expense_id = cursor.lastrowid

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

    Optionally filter using start_date and end_date.

    Date format: YYYY-MM-DD.
    """

    validate_date(start_date)
    validate_date(end_date)

    if start_date and end_date and start_date > end_date:
        raise ValueError(
            "start_date cannot be after end_date."
        )

    query = """
        SELECT
            id,
            date,
            amount,
            category,
            subcategory,
            note

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

    query += " ORDER BY date DESC, id DESC"

    with closing(get_connection()) as conn:

        conn.row_factory = sqlite3.Row

        rows = conn.execute(
            query,
            params
        ).fetchall()

        expenses = []

        for row in rows:

            expenses.append({
                "id": row["id"],
                "date": row["date"],
                "amount": row["amount"],
                "category": row["category"],
                "subcategory": row["subcategory"] or "",
                "note": row["note"] or ""
            })

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

    if expense_id <= 0:
        raise ValueError(
            "Expense ID must be greater than zero."
        )

    with closing(get_connection()) as conn:

        with conn:

            cursor = conn.execute(
                "DELETE FROM expenses WHERE id = ?",
                (expense_id,)
            )

            deleted = cursor.rowcount

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

    Optionally filter using a date range.
    """

    validate_date(start_date)
    validate_date(end_date)

    if start_date and end_date and start_date > end_date:
        raise ValueError(
            "start_date cannot be after end_date."
        )

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

    with closing(get_connection()) as conn:

        rows = conn.execute(
            query,
            params
        ).fetchall()

        results = []

        for row in rows:

            results.append({
                "category": row[0],
                "total": float(row[1]),
                "number_of_expenses": row[2]
            })

    return results


# --------------------------------------------------
# Initialize Database
# --------------------------------------------------

setup_database()


# --------------------------------------------------
# Run MCP Server
# --------------------------------------------------

if __name__ == "__main__":

    print("Starting Expense Tracker MCP Server...")

    print(f"Database location: {DB_PATH}")

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000"))
    )
