"""SQLite database layer for SQLMentor AI.

SQLite executes the learner's SQL. This module never calls an LLM.
"""
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "sqlmentor.db"
MAX_ROWS = 500

SCHEMA = """
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    city        TEXT NOT NULL
);
CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    category     TEXT NOT NULL,
    price        REAL NOT NULL
);
CREATE TABLE orders (
    order_id    INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    product_id  INTEGER NOT NULL REFERENCES products(product_id),
    order_date  TEXT NOT NULL,
    quantity    INTEGER NOT NULL,
    amount      REAL NOT NULL
);
"""

CUSTOMERS = [
    (1, "Aarav Sharma", "Mumbai"), (2, "Priya Singh", "Delhi"),
    (3, "Rohan Mehta", "Bengaluru"), (4, "Sneha Iyer", "Chennai"),
    (5, "Vikram Rao", "Hyderabad"), (6, "Ananya Das", "Kolkata"),
    (7, "Karan Malhotra", "Delhi"), (8, "Neha Gupta", "Mumbai"),
    (9, "Arjun Nair", "Bengaluru"), (10, "Pooja Verma", "Jaipur"),
    (11, "Rahul Joshi", "Pune"),   # no orders (useful for LEFT JOIN)
    (12, "Isha Kapoor", "Delhi"),  # no orders (useful for LEFT JOIN)
]

PRODUCTS = [
    (1, "Laptop", "Electronics", 55000), (2, "Smartphone", "Electronics", 25000),
    (3, "Headphones", "Electronics", 3000), (4, "Running Shoes", "Fashion", 4000),
    (5, "Denim Jacket", "Fashion", 2500), (6, "Backpack", "Fashion", 1800),
    (7, "Coffee Maker", "Home", 3500), (8, "Desk Lamp", "Home", 1200),
    (9, "Notebook Pack", "Stationery", 250),
    (10, "Gel Pens", "Stationery", 150),  # never ordered (useful for LEFT JOIN)
]

# (customer_id, product_id, order_date, quantity); amount = quantity * price
ORDERS = [
    (1, 1, "2026-01-05", 1), (1, 3, "2026-01-18", 2), (2, 2, "2026-01-20", 1),
    (2, 9, "2026-02-02", 5), (3, 4, "2026-02-10", 1), (3, 3, "2026-02-14", 1),
    (4, 7, "2026-02-21", 1), (4, 8, "2026-03-01", 2), (5, 2, "2026-03-05", 1),
    (5, 6, "2026-03-12", 1), (6, 5, "2026-03-15", 2), (6, 9, "2026-03-22", 10),
    (7, 1, "2026-04-02", 1), (7, 3, "2026-04-09", 1), (8, 4, "2026-04-15", 2),
    (8, 6, "2026-04-20", 1), (9, 2, "2026-04-28", 2), (9, 7, "2026-05-03", 1),
    (10, 8, "2026-05-10", 3), (10, 9, "2026-05-17", 4), (1, 4, "2026-05-24", 1),
    (2, 3, "2026-06-01", 1), (3, 5, "2026-06-08", 1), (4, 2, "2026-06-15", 1),
    (5, 1, "2026-06-22", 1), (6, 7, "2026-07-01", 1), (7, 9, "2026-07-09", 6),
    (8, 3, "2026-07-16", 2), (9, 6, "2026-07-23", 2), (10, 5, "2026-07-30", 1),
]


def init_db(force: bool = False) -> None:
    """Create the database with sample data if it doesn't exist yet."""
    if DB_PATH.exists() and not force:
        return
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    price = {p[0]: p[3] for p in PRODUCTS}
    orders = [
        (i, cust, prod, date, qty, qty * price[prod])
        for i, (cust, prod, date, qty) in enumerate(ORDERS, start=1)
    ]

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?)", CUSTOMERS)
        conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", PRODUCTS)
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)", orders)
        conn.commit()
    finally:
        conn.close()


def _only_select(action, arg1, arg2, db_name, source):
    """SQLite authorizer: allow reading data only, deny everything else."""
    allowed = (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION)
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


def run_query(sql: str) -> dict:
    """Run the learner's SQL safely.

    Returns {"ok": bool, "df": DataFrame or None, "error": str or None}.
    """
    sql = (sql or "").strip()
    if not sql:
        return {"ok": False, "df": None, "error": "Please write a query first."}

    init_db()
    # Read-only connection + authorizer = learners can't change or damage data.
    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=ro", uri=True)
    conn.set_authorizer(_only_select)
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(MAX_ROWS)
        columns = [c[0] for c in cur.description] if cur.description else []
        return {"ok": True, "df": pd.DataFrame(rows, columns=columns), "error": None}
    except sqlite3.Error as exc:
        msg = str(exc)
        if "not authorized" in msg or "readonly" in msg:
            msg = "Only SELECT queries are allowed in SQLMentor."
        return {"ok": False, "df": None, "error": msg}
    except sqlite3.Warning as exc:  # e.g. more than one statement
        return {"ok": False, "df": None, "error": str(exc)}
    finally:
        conn.close()


if __name__ == "__main__":
    init_db(force=True)
    tests = [
        "SELECT * FROM customers",
        "SELECT city, COUNT(*) AS n FROM customers GROUP BY city",
        "SELEC * FROM customers",              # typo -> syntax error
        "SELECT * FROM customer",              # wrong table -> error
        "DROP TABLE customers",                # must be blocked
    ]
    for q in tests:
        result = run_query(q)
        print("\n>>", q)
        print(result["df"].head(5) if result["ok"] else "ERROR: " + result["error"])