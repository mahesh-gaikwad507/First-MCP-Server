
import sqlite3
from pathlib import Path
from datetime import date
from fastmcp import FastMCP

# Initialize MCP server
mcp = FastMCP("Expense Tracker MCP Server")

# Database configuration
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "expenses.db"


# Create database and table
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


# Tool 1: Add an expense
@mcp.tool()
def add_expense(
    amount: float,
    category: str,
    date_value: str = "",
    subcategory: str = "",
    note: str = ""
) -> dict:
    """Add a new expense to the expense tracker."""

    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    expense_date = date_value or date.today().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO expenses
        (date, amount, category, subcategory, note)
        VALUES (?, ?, ?, ?, ?)
    """, (expense_date, amount, category, subcategory, note))

    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "expense_id": expense_id,
        "message": "Expense added successfully."
    }


# Tool 2: List expenses
@mcp.tool()
def list_expenses(
    start_date: str = "",
    end_date: str = ""
) -> list:
    """List expenses, optionally filtered by a date range."""

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
    expenses = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return expenses


# Tool 3: Delete an expense
@mcp.tool()
def delete_expense(expense_id: int) -> dict:
    """Delete an expense using its ID."""

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
        "message": "Expense deleted."
    }


# Tool 4: Summarize expenses by category
@mcp.tool()
def summarize_expenses(
    start_date: str = "",
    end_date: str = ""
) -> list:
    """Calculate total expenses grouped by category."""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT category, SUM(amount) AS total,
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

    query += " GROUP BY category ORDER BY total DESC"

    cursor.execute(query, params)

    results = [
        {
            "category": row[0],
            "total": row[1],
            "number_of_expenses": row[2]
        }
        for row in cursor.fetchall()
    ]

    conn.close()
    return results


# Initialize database
setup_database()


# Run remote MCP server
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8000
    )
