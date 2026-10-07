from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .helpers import month_label, safe_float


def apply_filters(
    df: pd.DataFrame,
    start_date: Any | None = None,
    end_date: Any | None = None,
    type_filter: str = "All",
    category: str = "All",
    search: str = "",
    min_amount: float = 0,
    max_amount: float = float("inf"),
) -> pd.DataFrame:
    """Return a filtered dataframe after applying dashboard controls."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date", "Description", "Category", "Type", "Income", "Expense", "Balance"])

    filtered = df.copy()

    if start_date is not None:
        filtered = filtered[filtered["Date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        filtered = filtered[filtered["Date"] <= pd.to_datetime(end_date)]

    if type_filter and type_filter != "All":
        filtered = filtered[filtered["Type"] == type_filter]

    if category and category != "All":
        filtered = filtered[filtered["Category"] == category]

    if search:
        search_term = str(search).lower()
        filtered = filtered[filtered["Description"].str.lower().str.contains(search_term, na=False)]

    if "Income" in filtered.columns:
        filtered["Income"] = pd.to_numeric(filtered["Income"], errors="coerce").fillna(0.0)
    if "Expense" in filtered.columns:
        filtered["Expense"] = pd.to_numeric(filtered["Expense"], errors="coerce").fillna(0.0)

    if min_amount is not None:
        filtered = filtered[(filtered["Expense"] >= min_amount) | (filtered["Income"] >= min_amount)]
    if max_amount is not None and np.isfinite(max_amount):
        filtered = filtered[(filtered["Expense"] <= max_amount) | (filtered["Income"] <= max_amount)]

    return filtered.reset_index(drop=True)


def financial_overview(df: pd.DataFrame) -> dict:
    """Compute key dashboard metrics."""
    if df is None or df.empty:
        return {
            "current_balance": 0.0,
            "total_income": 0.0,
            "total_expenses": 0.0,
            "net_cash_flow": 0.0,
            "transaction_count": 0,
            "average_expense": 0.0,
        }

    total_income = float(df["Income"].sum())
    total_expenses = float(df["Expense"].sum())
    current_balance = float(df["Balance"].iloc[-1]) if "Balance" in df.columns and not df.empty else total_income - total_expenses
    transaction_count = int(len(df))
    average_expense = float(df.loc[df["Type"] == "Expense", "Expense"].mean()) if (df["Type"] == "Expense").any() else 0.0

    return {
        "current_balance": current_balance,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_cash_flow": total_income - total_expenses,
        "transaction_count": transaction_count,
        "average_expense": average_expense,
    }


def balance_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Return daily balance trend data."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Date", "Balance"])
    frame = df.copy()
    frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
    frame = frame.dropna(subset=["Date"]).sort_values("Date")
    if frame.empty:
        return pd.DataFrame(columns=["Date", "Balance"])
    balance_series = pd.to_numeric(frame["Balance"], errors="coerce").ffill().fillna(0.0)
    frame["Balance"] = balance_series
    return frame[["Date", "Balance"]].drop_duplicates(subset=["Date"]).reset_index(drop=True)


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build income and expense monthly summary."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Month", "Income", "Expenses"])

    frame = df.copy()
    frame["Month"] = frame["Date"].dt.to_period("M").astype(str)
    summary = frame.groupby("Month", as_index=False).agg(Income=("Income", "sum"), Expenses=("Expense", "sum"))
    summary["Month"] = summary["Month"].apply(lambda x: pd.Period(x, freq="M").strftime("%b %Y"))
    return summary


def expense_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate expenses by category."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Category", "Expense"])
    filtered = df[df["Type"] == "Expense"].copy()
    if filtered.empty:
        return pd.DataFrame(columns=["Category", "Expense"])
    summary = filtered.groupby("Category", as_index=False)["Expense"].sum().sort_values("Expense", ascending=False)
    return summary.rename(columns={"Expense": "Amount"})


def top_expenses(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Return the top expenses by amount."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Description", "Expense"])
    filtered = df[df["Type"] == "Expense"].copy()
    if filtered.empty:
        return pd.DataFrame(columns=["Description", "Expense"])
    return filtered.nlargest(top_n, "Expense")[["Description", "Expense"]].reset_index(drop=True)


def transaction_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Count income vs expense transactions."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Type", "Count"])
    counts = df["Type"].value_counts().reset_index()
    counts.columns = ["Type", "Count"]
    return counts


def monthly_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """Compare revenue, expenses, net cash flow and count by month."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["Month", "Income", "Expenses", "Net Cash Flow", "Transactions"])
    frame = df.copy()
    frame["Month"] = frame["Date"].dt.to_period("M").astype(str)
    summary = frame.groupby("Month").agg(Income=("Income", "sum"), Expenses=("Expense", "sum"), Transactions=("Description", "count"))
    summary["Net Cash Flow"] = summary["Income"] - summary["Expenses"]
    summary = summary.reset_index()
    summary["Month"] = summary["Month"].apply(lambda x: pd.Period(x, freq="M").strftime("%b %Y"))
    return summary


def analysis_summary(df: pd.DataFrame) -> dict:
    """Return a rich summary used on the analytics page."""
    if df is None or df.empty:
        return {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "net_cash_flow": 0.0,
            "income_transactions": 0,
            "expense_transactions": 0,
            "avg_income": 0.0,
            "avg_expense": 0.0,
            "largest_income": 0.0,
            "largest_expense": 0.0,
            "income_by_month": pd.DataFrame(columns=["Month", "Income"]),
            "expense_by_category": pd.DataFrame(columns=["Category", "Amount"]),
            "top_10_expenses": pd.DataFrame(columns=["Description", "Expense"]),
        }

    income_df = df[df["Type"] == "Income"]
    expense_df = df[df["Type"] == "Expense"]

    income_by_month = income_df.groupby(df["Date"].dt.to_period("M").astype(str)).agg(Income=("Income", "sum")).reset_index()
    income_by_month["Month"] = income_by_month["Date"].apply(lambda x: pd.Period(x, freq="M").strftime("%b %Y"))
    income_by_month = income_by_month[["Month", "Income"]]

    expense_by_category = expense_df.groupby("Category")["Expense"].sum().reset_index().rename(columns={"Expense": "Amount"})

    avg_income = float(income_df["Income"].mean()) if not income_df.empty else 0.0
    avg_expense = float(expense_df["Expense"].mean()) if not expense_df.empty else 0.0

    return {
        "total_income": float(income_df["Income"].sum()),
        "total_expenses": float(expense_df["Expense"].sum()),
        "net_cash_flow": float(income_df["Income"].sum() - expense_df["Expense"].sum()),
        "income_transactions": int(len(income_df)),
        "expense_transactions": int(len(expense_df)),
        "avg_income": avg_income,
        "avg_expense": avg_expense,
        "largest_income": float(income_df["Income"].max()) if not income_df.empty else 0.0,
        "largest_expense": float(expense_df["Expense"].max()) if not expense_df.empty else 0.0,
        "income_by_month": income_by_month,
        "expense_by_category": expense_by_category,
        "top_10_expenses": expense_df.nlargest(10, "Expense")[["Description", "Expense"]].reset_index(drop=True),
    }


def generate_insights(df: pd.DataFrame) -> list[str]:
    """Create factual, non-predictive insights."""
    if df is None or df.empty:
        return ["No transactions are available to analyze yet."]

    overview = financial_overview(df)
    insights: list[str] = []

    if overview["net_cash_flow"] > 0:
        insights.append(f"Your net cash flow was positive at {overview['net_cash_flow']:.2f}.")
    elif overview["net_cash_flow"] < 0:
        insights.append(f"Your net cash flow was negative at {abs(overview['net_cash_flow']):.2f}.")
    else:
        insights.append("Your income and expenses were equal during this period.")

    if not df.empty:
        month_group = df.groupby(df["Date"].dt.to_period("M").astype(str)).agg(Income=("Income", "sum"), Expenses=("Expense", "sum")).reset_index()
        if len(month_group) > 1:
            month_group["NetCashFlow"] = month_group["Income"] - month_group["Expenses"]
            best_month = month_group.loc[month_group["NetCashFlow"].idxmax()]
            heavy_month = month_group.loc[month_group["Expenses"].idxmax()]
            income_month = month_group.loc[month_group["Income"].idxmax()]
            insights.append(f"The strongest cash-flow month was {pd.Period(best_month['Date'], freq='M').strftime('%b %Y')}.")
            insights.append(f"Your highest spending month was {pd.Period(heavy_month['Date'], freq='M').strftime('%b %Y')}.")
            insights.append(f"Your highest income month was {pd.Period(income_month['Date'], freq='M').strftime('%b %Y')}.")

    expense_by_category = df[df["Type"] == "Expense"].groupby("Category")["Expense"].sum()
    if not expense_by_category.empty:
        top_category = expense_by_category.idxmax()
        insights.append(f"Your expenses were highest in the {top_category} category.")

    if (df["Type"] == "Expense").any():
        expense_count = int((df["Type"] == "Expense").sum())
        insights.append(f"You made {expense_count} expense transactions.")

    largest_expense = df.loc[df["Type"] == "Expense", "Expense"].max() if (df["Type"] == "Expense").any() else 0
    if largest_expense > 0:
        insights.append(f"Your largest expense was ₹{largest_expense:,.2f}.")

    return insights[:6]
