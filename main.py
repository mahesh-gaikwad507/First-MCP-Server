
import os
import asyncio
import aiosqlite

from pathlib import Path
from datetime import date
from typing import TypedDict

from fastmcp import FastMCP


# --------------------------------------------------
# 1. Initialize MCP Server
# --------------------------------------------------

mcp = FastMCP("Expense Tracker MCP Server")


# --------------------------------------------------
# 2. Database Configuration
# --------------------------------------------------

# Set DATA_DIR to a persistent writable directory
# provided by your hosting platform.

DB_DIR = Path(
    os.getenv(
        "DATA_DIR",
        str(Path.home() / ".expense_mcp")
    )
)

DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "expenses.db"


# --------------------------------------------------
# 3. Output Schemas
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
# 4. Database Setup
# --------------------------------------------------

async def setup_database():
    """
    Initialize SQLite database asynchronously.
    """

    DB_DIR.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(DB_PATH)) as db:

        await db.execute("PRAGMA busy_timeout = 30000")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                date TEXT NOT NULL,

                amount REAL NOT NULL,

                category TEXT NOT NULL,

                subcategory TEXT DEFAULT '',

                note TEXT DEFAULT ''

            )
        """)

        await db.commit()

    print(f"Database initialized: {DB_PATH}")


# --------------------------------------------------
# 5. Date Validation
# --------------------------------------------------

def validate_date(date_value: str):

    if date_value:
        try:
            date.fromisoformat(date_value)

        except ValueError:
            raise ValueError(
                "Invalid date. Use YYYY-MM-DD format."
            )

    return date_value


# --------------------------------------------------
# 6. Tool: Add Expense
# --------------------------------------------------

@mcp.tool()
async def add_expense(
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

    async with aiosqlite.connect(str(DB_PATH)) as db:

        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
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

        await db.commit()

        expense_id = cursor.lastrowid

    return {
        "status": "success",
        "expense_id": expense_id,
        "message": "Expense added successfully."
    }


# --------------------------------------------------
# 7. Tool: List Expenses
# --------------------------------------------------

@mcp.tool()
async def list_expenses(
    start_date: str = "",
    end_date: str = ""
) -> list[Expense]:
    """
    Retrieve expenses.

    Optionally filter by date range.
    """

    validate_date(start_date)
    validate_date(end_date)

    if start_date and end_date and start_date > end_date:
        raise ValueError(
            "Start date cannot be after end date."
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

    async with aiosqlite.connect(str(DB_PATH)) as db:

        db.row_factory = aiosqlite.Row

        async with db.execute(query, params) as cursor:

            rows = await cursor.fetchall()

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
# 8. Tool: Delete Expense
# --------------------------------------------------

@mcp.tool()
async def delete_expense(
    expense_id: int
) -> DeleteResponse:
    """
    Delete an expense using its unique ID.
    """

    if expense_id <= 0:
        raise ValueError(
            "Expense ID must be greater than zero."
        )

    async with aiosqlite.connect(str(DB_PATH)) as db:

        cursor = await db.execute(
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        )

        deleted = cursor.rowcount

        await db.commit()

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
# 9. Tool: Summarize Expenses
# --------------------------------------------------

@mcp.tool()
async def summarize_expenses(
    start_date: str = "",
    end_date: str = ""
) -> list[CategorySummary]:
    """
    Calculate total expenses grouped by category.

    Optionally filter by date range.
    """

    validate_date(start_date)
    validate_date(end_date)

    if start_date and end_date and start_date > end_date:
        raise ValueError(
            "Start date cannot be after end date."
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

    async with aiosqlite.connect(str(DB_PATH)) as db:

        async with db.execute(query, params) as cursor:

            rows = await cursor.fetchall()

    results = []

    for row in rows:

        results.append({
            "category": row[0],
            "total": float(row[1]),
            "number_of_expenses": row[2]
        })

    return results


# --------------------------------------------------
# 10. Initialize Database and Run Server
# --------------------------------------------------

if __name__ == "__main__":

    asyncio.run(setup_database())

    print("Starting Expense Tracker MCP Server...")

    print(f"Database location: {DB_PATH}")

    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000"))
    )
