from __future__ import annotations

CATEGORY_KEYWORDS = {
    "Food": ["zomato", "swiggy", "restaurant", "cafe", "food", "pizza", "burger", "coffee"],
    "Groceries": ["grocery", "supermarket", "mart", "vegetables", "grocer", "milk", "walmart", "spice"],
    "Travel": ["irctc", "railway", "train", "flight", "airline", "hotel", "trip", "travel"],
    "Transport": ["rapido", "uber", "ola", "metro", "bus", "auto", "cab", "transport"],
    "Shopping": ["fashion", "clothing", "shopping", "amazon", "mall", "store", "apparel", "retail"],
    "Healthcare": ["pharmacy", "hospital", "clinic", "medical", "medicine", "health", "diagnostic", "pharma"],
    "Utilities": ["electricity", "water", "gas", "utility", "internet", "broadband"],
    "Mobile & Internet": ["airtel", "jio", "vodafone", "idea", "mobile", "internet", "recharge"],
    "Fuel": ["petrol", "diesel", "fuel", "gasoline", "lsd"],
    "Entertainment": ["netflix", "spotify", "movie", "cinema", "entertainment", "streaming"],
    "Cash Withdrawal": ["atm", "cash withdrawal", "withdrawal"],
    "Other": ["misc", "miscellaneous", "other"],
}


def categorize_transaction(description: str) -> str:
    """Classify a transaction using keyword rules."""
    text = str(description or "").strip().upper()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.upper() in text:
                return category
    return "Other"
