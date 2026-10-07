from __future__ import annotations

from typing import Any

import pandas as pd


def format_inr(value: Any, default: str = "₹0.00") -> str:
    """Format a numeric value as Indian Rupee currency."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return f"₹{number:,.2f}"


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def month_label(date_value: Any) -> str:
    """Return a compact month label like Jan 2024."""
    if pd.isna(date_value):
        return "Unknown"
    dt = pd.to_datetime(date_value, errors="coerce")
    if pd.isna(dt):
        return "Unknown"
    return dt.strftime("%b %Y")


def normalize_name(name: Any) -> str:
    """Normalize column names across source files."""
    return str(name).strip().lower().replace(" ", "_")
