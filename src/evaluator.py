"""Evaluation engine for SQLMentor AI.

SQLite decides correctness (by running both queries). No LLM is involved here.
"""
import json
from collections import Counter
from pathlib import Path

from src.database import run_query

QUESTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "questions.json"


def load_questions() -> list:
    with open(QUESTIONS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _clean(v):
    """Make values comparable: round floats, turn NaN into None."""
    if isinstance(v, float):
        return None if v != v else round(v, 2)
    return v


def _rows(df, sort_cols=False) -> list:
    """Turn a result table into a list of row tuples.

    If sort_cols is True, the values inside each row are sorted,
    so the order of the columns does not matter.
    """
    rows = [tuple(_clean(v) for v in row) for row in df.itertuples(index=False, name=None)]
    if sort_cols:
        rows = [tuple(sorted(r, key=str)) for r in rows]
    return rows


def evaluate(user_sql: str, question: dict) -> dict:
    """Compare the learner's result with the expected result.

    status: "error" | "correct" | "partial" | "incorrect"
    reason: short code the LLM coach (or fallback hints) can use later.
    Column names are ignored on purpose, so aliases never cause a wrong verdict.
    Column order is also forgiven (same values in a different column order is correct).
    """
    user = run_query(user_sql)
    if not user["ok"]:
        return {"status": "error", "reason": "sql_error", "error": user["error"]}

    expected = run_query(question["expected_sql"])
    if not expected["ok"]:
        raise ValueError(f"Bad expected_sql in {question['id']}: {expected['error']}")

    u_df, e_df = user["df"], expected["df"]
    result = {"error": None, "user_rows": len(u_df), "expected_rows": len(e_df)}

    if u_df.shape[1] != e_df.shape[1]:
        return {**result, "status": "incorrect", "reason": "wrong_columns",
                "user_cols": u_df.shape[1], "expected_cols": e_df.shape[1]}

    u_rows, e_rows = _rows(u_df), _rows(e_df)

    # Case 1: same rows, same column order.
    if Counter(u_rows) == Counter(e_rows):
        if question.get("order_matters") and u_rows != e_rows:
            return {**result, "status": "partial", "reason": "wrong_order"}
        return {**result, "status": "correct", "reason": "match"}

    # Case 2: same values, but the columns are in a different order.
    u_alt, e_alt = _rows(u_df, True), _rows(e_df, True)
    if Counter(u_alt) == Counter(e_alt):
        if question.get("order_matters") and u_alt != e_alt:
            return {**result, "status": "partial", "reason": "wrong_order"}
        return {**result, "status": "correct", "reason": "match_other_column_order"}

    # Case 3: the result is really different.
    overlap = sum((Counter(u_rows) & Counter(e_rows)).values())
    if overlap == 0:
        return {**result, "status": "incorrect", "reason": "wrong_values"}
    if len(u_rows) > len(e_rows):
        return {**result, "status": "partial", "reason": "extra_rows"}
    if len(u_rows) < len(e_rows):
        return {**result, "status": "partial", "reason": "missing_rows"}
    return {**result, "status": "partial", "reason": "wrong_values"}


if __name__ == "__main__":
    questions = load_questions()

    # 1) Every expected query must run and match itself.
    ok = sum(evaluate(q["expected_sql"], q)["status"] == "correct" for q in questions)
    print(f"Self-check: {ok}/{len(questions)} questions valid")

    # 2) Try some answers on q01.
    q1 = questions[0]
    tests = [
        "SELECT name, city FROM customers WHERE city = 'Delhi'",   # correct
        "SELECT city, name FROM customers WHERE city = 'Delhi'",   # correct (other column order)
        "SELECT * FROM customers WHERE city = 'Delhi'",            # wrong_columns
        "SELECT name, city FROM customers",                        # partial: extra_rows
        "SELECT name, city FROM customers WHERE city = 'Mumbai'",  # incorrect
        "SELEC name, city FROM customers",                         # error
    ]
    for sql in tests:
        print("\n>>", sql)
        print(evaluate(sql, q1))