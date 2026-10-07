from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .categorizer import categorize_transaction
from .helpers import normalize_name, safe_float

DEFAULT_DEMO_PATH = Path("data/demo_transactions.csv")

COLUMN_ALIASES = {
    "date": ["date", "transaction_date", "txn_date", "posted_date", "booking_date"],
    "description": ["description", "narration", "particulars", "transaction_particulars", "details", "memo"],
    "category": ["category", "type_of_transaction", "sub_category"],
    "income": ["income", "deposit", "credit", "credit_amount", "inflow"],
    "expense": ["expense", "withdrawal", "debit", "debit_amount", "outflow"],
    "balance": ["balance", "closing_balance", "running_balance", "available_balance"],
    "type": ["type", "transaction_type", "entry_type"],
    "amount": ["amount", "value", "transaction_amount"],
}


def _match_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized_map = {normalize_name(col): col for col in columns}
    for candidate in candidates:
        hit = normalized_map.get(normalize_name(candidate))
        if hit:
            return hit
    return None


def _ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    frame.columns = [str(col).strip() for col in frame.columns]

    date_col = _match_column(frame.columns.tolist(), COLUMN_ALIASES["date"])
    desc_col = _match_column(frame.columns.tolist(), COLUMN_ALIASES["description"])
    income_col = _match_column(frame.columns.tolist(), COLUMN_ALIASES["income"])
    expense_col = _match_column(frame.columns.tolist(), COLUMN_ALIASES["expense"])
    balance_col = _match_column(frame.columns.tolist(), COLUMN_ALIASES["balance"])
    type_col = _match_column(frame.columns.tolist(), COLUMN_ALIASES["type"])
    category_col = _match_column(frame.columns.tolist(), COLUMN_ALIASES["category"])
    amount_col = _match_column(frame.columns.tolist(), COLUMN_ALIASES["amount"])

    if date_col is None or desc_col is None:
        raise ValueError("We couldn't identify the transaction columns in this file.")

    frame.rename(columns={date_col: "Date", desc_col: "Description"}, inplace=True)

    if category_col is not None:
        frame.rename(columns={category_col: "Category"}, inplace=True)
    else:
        frame["Category"] = frame["Description"].apply(categorize_transaction)

    if type_col is not None:
        frame.rename(columns={type_col: "Type"}, inplace=True)

    if income_col is not None:
        frame.rename(columns={income_col: "Income"}, inplace=True)
    else:
        frame["Income"] = 0.0

    if expense_col is not None:
        frame.rename(columns={expense_col: "Expense"}, inplace=True)
    else:
        frame["Expense"] = 0.0

    if amount_col is not None and "Income" not in frame.columns and "Expense" not in frame.columns:
        frame["Income"] = 0.0
        frame["Expense"] = 0.0
        if "Type" in frame.columns:
            mask_income = frame["Type"].astype(str).str.lower().str.contains("income|credit|deposit", na=False)
            mask_expense = frame["Type"].astype(str).str.lower().str.contains("expense|debit|withdrawal", na=False)
            frame.loc[mask_income, "Income"] = frame.loc[mask_income, amount_col]
            frame.loc[mask_expense, "Expense"] = frame.loc[mask_expense, amount_col]

    if balance_col is not None:
        frame.rename(columns={balance_col: "Balance"}, inplace=True)
    else:
        frame["Balance"] = 0.0

    frame["Income"] = pd.to_numeric(frame.get("Income", 0), errors="coerce").fillna(0.0)
    frame["Expense"] = pd.to_numeric(frame.get("Expense", 0), errors="coerce").fillna(0.0)

    if "Type" in frame.columns:
        frame["Type"] = frame["Type"].apply(lambda x: "Income" if str(x).strip().lower() in {"income", "credit", "deposit"} else "Expense" if str(x).strip().lower() in {"expense", "debit", "withdrawal"} else "Income" if safe_float(x) > 0 else "Expense")
    else:
        frame["Type"] = frame.apply(
            lambda row: "Income" if safe_float(row.get("Income", 0)) > 0 and safe_float(row.get("Expense", 0)) == 0 else "Expense" if safe_float(row.get("Expense", 0)) > 0 else "Income",
            axis=1,
        )

    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame["Description"] = frame["Description"].fillna("Unknown transaction").astype(str)
    frame["Category"] = frame["Category"].fillna("Other").astype(str)
    frame["Balance"] = pd.to_numeric(frame.get("Balance", 0), errors="coerce").fillna(0.0)

    if frame["Date"].notna().sum() == 0:
        raise ValueError("No valid dates were found in this file.")

    if "Income" not in frame.columns or "Expense" not in frame.columns:
        raise ValueError("The uploaded file is missing income/expense information.")

    return frame[["Date", "Description", "Category", "Type", "Income", "Expense", "Balance"]]


def load_demo_data(path: str | Path = DEFAULT_DEMO_PATH) -> pd.DataFrame:
    """Load the built-in demo dataset."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Demo dataset not found: {path}")
    df = pd.read_csv(path)
    return _ensure_required_columns(df)


def load_uploaded_data(uploaded_file: Any) -> pd.DataFrame:
    """Load and normalize uploaded user data from CSV/XLS/XLSX."""
    if uploaded_file is None:
        raise ValueError("Please upload a CSV or Excel file.")

    filename = str(uploaded_file.name).lower()
    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("Please upload a CSV or Excel file.")

    return _ensure_required_columns(df)
