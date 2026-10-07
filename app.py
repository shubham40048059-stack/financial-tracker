from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.analyzer import (
    analysis_summary,
    apply_filters,
    balance_trend,
    expense_by_category,
    financial_overview,
    generate_insights,
    monthly_comparison,
    monthly_summary,
    top_expenses,
    transaction_distribution,
)
from utils.data_loader import DEFAULT_DEMO_PATH, load_demo_data, load_uploaded_data
from utils.helpers import format_inr

APP_ROOT = Path(__file__).resolve().parent
BRAND_LOGO_PATH = APP_ROOT / "assets" / "fintrack-logo.png"

st.set_page_config(page_title="FinTrack | Personal Financial Tracker", page_icon="💰", layout="wide")


@st.cache_data
def get_demo_data() -> pd.DataFrame:
    return load_demo_data(DEFAULT_DEMO_PATH)


def initialize_session_state() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "🏠 Dashboard"
    if "active_df" not in st.session_state:
        st.session_state.active_df = get_demo_data()
        st.session_state.data_source = "Demo data"


def get_page_options() -> list[str]:
    return ["🏠 Dashboard", "💳 Transactions", "📊 Analytics", "📁 Upload Data", "ℹ️ About"]


def render_sidebar_filters(df: pd.DataFrame):
    if df.empty:
        st.sidebar.warning("No transactions are available yet.")
        return None, None, "All", "All", "", 0.0, 0.0

    date_values = pd.to_datetime(df["Date"], errors="coerce").dropna()
    if date_values.empty:
        return None, None, "All", "All", "", 0.0, 0.0

    min_date = date_values.min().date()
    max_date = date_values.max().date()

    start_date, end_date = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    type_filter = st.sidebar.selectbox("Transaction Type", ["All", "Income", "Expense"])
    categories = ["All"] + sorted(df["Category"].dropna().unique().tolist())
    category = st.sidebar.selectbox("Category", categories)
    search = st.sidebar.text_input("Search description")
    min_amount = st.sidebar.number_input("Min amount", min_value=0.0, step=100.0, format="%.2f")
    max_amount = st.sidebar.number_input("Max amount", min_value=min_amount, step=100.0, value=max(1000000.0, min_amount), format="%.2f")

    if max_amount < min_amount:
        st.sidebar.warning("Maximum amount must be greater than or equal to minimum amount.")
        max_amount = min_amount

    return start_date, end_date, type_filter, category, search, min_amount, max_amount


def render_dashboard(df: pd.DataFrame) -> None:
    st.title("Financial Overview")
    st.caption("A quick view of your income, expenses, balance and transaction patterns.")

    with st.container(key="fintrack-demo-notice"):
        st.info("You're viewing demo data. This dataset contains synthetic transactions for demonstration purposes.")
    if st.button("Upload Your Own Data"):
        st.session_state.page = "📁 Upload Data"
        st.rerun()

    st.sidebar.markdown("### Filters")
    start_date, end_date, type_filter, category, search, min_amount, max_amount = render_sidebar_filters(df)
    filtered = apply_filters(
        df,
        start_date=start_date,
        end_date=end_date,
        type_filter=type_filter,
        category=category,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
    )

    if filtered.empty:
        st.warning("No transactions match your current filters.")
        return

    metrics = financial_overview(filtered)

    with st.container(key="fintrack-metrics"):
        metric_columns = st.columns(6)
        cards = [
            ("Current Balance", metrics["current_balance"], "🏦"),
            ("Total Income", metrics["total_income"], "💰"),
            ("Total Expenses", metrics["total_expenses"], "💸"),
            ("Net Cash Flow", metrics["net_cash_flow"], "📈"),
            ("Number of Transactions", metrics["transaction_count"], "🧾"),
            ("Average Expense", metrics["average_expense"], "📉"),
        ]

        for container, (label, value, icon) in zip(metric_columns, cards):
            value_class = "positive" if label == "Total Income" or (label in {"Current Balance", "Net Cash Flow"} and value >= 0) else "negative" if label in {"Current Balance", "Net Cash Flow"} and value < 0 else ""
            with container:
                st.markdown(
                    f"""
                    <div class="fintrack-metric-card">
                        <div class="fintrack-metric-label">{icon} {label}</div>
                        <div class="fintrack-metric-value {value_class}">{format_inr(value)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("## Your Financial Summary")
    income_total = metrics["total_income"]
    expense_total = metrics["total_expenses"]
    net_cash = metrics["net_cash_flow"]
    largest_spend = filtered.loc[filtered["Type"] == "Expense", "Expense"].max() if (filtered["Type"] == "Expense").any() else 0
    category_summary = filtered[filtered["Type"] == "Expense"].groupby("Category")["Expense"].sum()
    top_category = category_summary.idxmax() if not category_summary.empty else "Other"

    summary_lines = [
        f"Your total income during this period was {format_inr(income_total)}.",
        f"Your total expenses were {format_inr(expense_total)}.",
        f"Your net cash flow was {'positive' if net_cash >= 0 else 'negative'} at {format_inr(abs(net_cash))}.",
        f"Your largest spending category was {top_category}.",
        f"Your average expense was {format_inr(metrics['average_expense'])}.",
        f"Your highest individual expense was {format_inr(largest_spend)}.",
    ]
    for line in summary_lines:
        st.write(line)

    balance_df = balance_trend(filtered)
    fig = px.line(balance_df, x="Date", y="Balance", title="Balance Trend", template="plotly_white")
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Balance")
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

    monthly_df = monthly_summary(filtered)
    if not monthly_df.empty:
        bar_fig = px.bar(
            monthly_df,
            x="Month",
            y=["Income", "Expenses"],
            barmode="group",
            title="Monthly Income vs Expenses",
            template="plotly_white",
        )
        bar_fig.update_xaxes(title_text="Month")
        bar_fig.update_yaxes(title_text="Amount")
        st.plotly_chart(bar_fig, use_container_width=True)
    else:
        st.info("No monthly data is available for the selected filter range.")

    category_df = expense_by_category(filtered)
    if not category_df.empty:
        pie_fig = px.pie(category_df, names="Category", values="Amount", title="Expense by Category", hole=0.45)
        st.plotly_chart(pie_fig, use_container_width=True)
    else:
        st.info("No expense category data is available.")

    monthly_expense = monthly_summary(filtered)
    if not monthly_expense.empty:
        expense_figure = px.bar(
            monthly_expense,
            x="Month",
            y="Expenses",
            title="Monthly Expenses",
            template="plotly_white",
        )
        expense_figure.update_xaxes(title_text="Month")
        expense_figure.update_yaxes(title_text="Expenses")
        st.plotly_chart(expense_figure, use_container_width=True)

    spending_trend = filtered[filtered["Type"] == "Expense"].copy()
    if not spending_trend.empty:
        spending_trend["Date"] = pd.to_datetime(spending_trend["Date"], errors="coerce")
        spending_trend = spending_trend.dropna(subset=["Date"]).sort_values("Date")
        spending_trend = spending_trend.groupby("Date", as_index=False)["Expense"].sum()
        spending_fig = px.line(spending_trend, x="Date", y="Expense", title="Spending Trend", template="plotly_white")
        spending_fig.update_xaxes(title_text="Date")
        spending_fig.update_yaxes(title_text="Expenses")
        st.plotly_chart(spending_fig, use_container_width=True)

    top_expenses_df = top_expenses(filtered, 10)
    if not top_expenses_df.empty:
        top_fig = px.bar(
            top_expenses_df,
            x="Expense",
            y="Description",
            orientation="h",
            title="Top Expenses",
            template="plotly_white",
        )
        top_fig.update_xaxes(title_text="Amount")
        top_fig.update_yaxes(title_text="Description")
        st.plotly_chart(top_fig, use_container_width=True)

    dist_df = transaction_distribution(filtered)
    if not dist_df.empty:
        dist_fig = px.bar(dist_df, x="Type", y="Count", title="Transaction Distribution", template="plotly_white")
        dist_fig.update_xaxes(title_text="Transaction Type")
        dist_fig.update_yaxes(title_text="Number of Transactions")
        st.plotly_chart(dist_fig, use_container_width=True)


def render_transactions(df: pd.DataFrame) -> None:
    st.title("Transactions")
    st.caption("Search and explore individual records from the active dataset.")

    start_date, end_date, type_filter, category, search, min_amount, max_amount = render_sidebar_filters(df)
    filtered = apply_filters(
        df,
        start_date=start_date,
        end_date=end_date,
        type_filter=type_filter,
        category=category,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
    )

    if filtered.empty:
        st.warning("No transactions match your current filters.")
        return

    display_df = filtered.copy()
    display_df["Date"] = pd.to_datetime(display_df["Date"]).dt.strftime("%Y-%m-%d")
    display_df["Income"] = display_df["Income"].map(lambda x: format_inr(x))
    display_df["Expense"] = display_df["Expense"].map(lambda x: format_inr(x))
    display_df["Balance"] = display_df["Balance"].map(lambda x: format_inr(x))

    st.dataframe(display_df[["Date", "Description", "Category", "Type", "Income", "Expense", "Balance"]], use_container_width=True)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Filtered Transactions",
        data=csv,
        file_name="filtered_transactions.csv",
        mime="text/csv",
    )


def render_analytics(df: pd.DataFrame) -> None:
    st.title("Analytics")
    st.caption("Detailed analysis of your cash flow, spending patterns and monthly performance.")

    start_date, end_date, type_filter, category, search, min_amount, max_amount = render_sidebar_filters(df)
    filtered = apply_filters(
        df,
        start_date=start_date,
        end_date=end_date,
        type_filter=type_filter,
        category=category,
        search=search,
        min_amount=min_amount,
        max_amount=max_amount,
    )

    if filtered.empty:
        st.warning("No transactions match your current filters.")
        return

    metrics = analysis_summary(filtered)
    total_income = metrics["total_income"]
    total_expenses = metrics["total_expenses"]
    net_cash = metrics["net_cash_flow"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total income", format_inr(total_income))
        st.metric("Number of income transactions", metrics["income_transactions"])
        st.metric("Average income transaction", format_inr(metrics["avg_income"]))
        st.metric("Largest income", format_inr(metrics["largest_income"]))

    with col2:
        st.metric("Total expenses", format_inr(total_expenses))
        st.metric("Number of expense transactions", metrics["expense_transactions"])
        st.metric("Average expense", format_inr(metrics["avg_expense"]))
        st.metric("Largest expense", format_inr(metrics["largest_expense"]))

    income_month_df = metrics["income_by_month"]
    if not income_month_df.empty:
        income_bar = px.bar(income_month_df, x="Month", y="Income", title="Income by Month", template="plotly_white")
        st.plotly_chart(income_bar, use_container_width=True)

    expense_category_df = metrics["expense_by_category"]
    if not expense_category_df.empty:
        exp_cat = px.bar(expense_category_df, x="Category", y="Amount", title="Expense by Category", template="plotly_white")
        st.plotly_chart(exp_cat, use_container_width=True)

    top_10 = metrics["top_10_expenses"]
    if not top_10.empty:
        top_fig = px.bar(top_10, x="Expense", y="Description", orientation="h", title="Top 10 Expenses", template="plotly_white")
        st.plotly_chart(top_fig, use_container_width=True)

    st.markdown("### Cash Flow")
    cash_flow_rate = (net_cash / total_income * 100) if total_income > 0 else 0
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Total income", format_inr(total_income))
    with col_b:
        st.metric("Total expenses", format_inr(total_expenses))
    with col_c:
        st.metric("Net cash flow", format_inr(net_cash))
    with col_d:
        st.metric("Savings / Cash-flow rate", f"{cash_flow_rate:.2f}%" if total_income > 0 else "N/A")

    st.markdown("### Monthly Comparison")
    comparison = monthly_comparison(filtered)
    if not comparison.empty:
        comparison_chart = px.bar(
            comparison,
            x="Month",
            y=["Income", "Expenses", "Net Cash Flow"],
            barmode="group",
            title="Monthly Income, Expenses and Net Cash Flow",
            template="plotly_white",
        )
        st.plotly_chart(comparison_chart, use_container_width=True)

        best_cash = comparison.loc[comparison["Net Cash Flow"].idxmax()]
        highest_spending = comparison.loc[comparison["Expenses"].idxmax()]
        highest_income = comparison.loc[comparison["Income"].idxmax()]
        st.write(f"Best cash-flow month: {best_cash['Month']} ({format_inr(best_cash['Net Cash Flow'])})")
        st.write(f"Highest spending month: {highest_spending['Month']} ({format_inr(highest_spending['Expenses'])})")
        st.write(f"Highest income month: {highest_income['Month']} ({format_inr(highest_income['Income'])})")

    st.markdown("### Smart Insights")
    for insight in generate_insights(filtered):
        st.write(f"• {insight}")


def render_upload_data() -> None:
    st.title("Upload Data")
    st.caption("Upload your own CSV or Excel file for a session-only analysis.")
    st.warning("Your personal financial data is processed for this session and is not included in the public demo database.")
    st.info("Do not upload sensitive banking credentials. Never share your bank password, PIN, OTP or internet banking credentials.")

    uploaded_file = st.file_uploader("Upload your own transaction data", type=["csv", "xlsx", "xls"])
    if uploaded_file is not None:
        try:
            uploaded_df = load_uploaded_data(uploaded_file)
            st.session_state.active_df = uploaded_df
            st.session_state.data_source = uploaded_file.name
            st.success("Your file was loaded successfully for this session.")
            st.info("Demo data is synthetic and contains no real banking information.")
            st.session_state.page = "🏠 Dashboard"
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error("We couldn't process this file. Please check the columns and try again.")

    st.markdown("### Privacy")
    st.write("Demo data is synthetic and contains no real banking information.")
    st.write("Do not upload sensitive banking credentials.")
    st.write("Never share your bank password, PIN, OTP or internet banking credentials.")
    st.write("Uploaded files are not stored permanently and are only used for the current session.")


def render_about() -> None:
    st.title("About Personal Financial Tracker")
    st.write(
        "This application helps users understand their income, expenses, spending categories and financial trends through interactive dashboards."
    )
    st.markdown(
        """
        ### Features
        - Income tracking
        - Expense tracking
        - Category analysis
        - Monthly comparison
        - Cash-flow analysis
        - Interactive charts
        - CSV/XLSX upload
        - Download filtered transactions
        """
    )
    st.write("Built with Python, Streamlit, Pandas and Plotly.")
    st.write("Demo data is synthetic and contains no real banking information.")


def main() -> None:
    initialize_session_state()

    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(ellipse at 8% 8%, rgba(87, 170, 216, 0.08), transparent 32rem),
                radial-gradient(ellipse at 92% 18%, rgba(43, 166, 132, 0.07), transparent 30rem),
                linear-gradient(135deg, #f5f9ff 0%, #eefaf7 50%, #f8fbff 100%);
        }
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"] {
            background: transparent;
        }
        [data-testid="stMainBlockContainer"] {
            color: #18334f;
        }
        [data-testid="stMainBlockContainer"] h1,
        [data-testid="stMainBlockContainer"] h2,
        [data-testid="stMainBlockContainer"] h3 {
            color: #173653;
            letter-spacing: -0.025em;
        }
        [data-testid="stMainBlockContainer"] h1 {
            font-weight: 750;
        }
        [data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] {
            color: #64778b;
        }
        [data-testid="stSidebar"] {
            background: rgba(246, 250, 253, 0.96);
            border-right: 1px solid rgba(89, 119, 143, 0.12);
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid rgba(100, 116, 139, 0.18);
            border-radius: 0.9rem;
            background: #f8fafc;
            box-shadow: 0 3px 12px rgba(15, 23, 42, 0.035);
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] h4 {
            margin: 0 0 0.6rem;
            color: #173c5a;
            font-size: 1.05rem;
            font-weight: 650;
        }
        [data-testid="stSidebar"] [data-testid="stRadioGroup"] {
            gap: 0.25rem;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"] {
            position: relative;
            min-height: 2.65rem;
            padding: 0.65rem 0.75rem !important;
            border: 1px solid transparent;
            border-radius: 0.65rem;
            color: #334155;
            cursor: pointer;
            transition: background-color 170ms ease, border-color 170ms ease, color 170ms ease;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {
            display: none;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"] p {
            margin: 0;
            font-size: 0.95rem;
            font-weight: 500;
            line-height: 1.35;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {
            background: #edf5f3;
            border-color: #d8e9e4;
            color: #123b45;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {
            background: #e8f4f1;
            border-color: #c8e2da;
            color: #123f45;
            font-weight: 650;
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"]::before {
            position: absolute;
            top: 0.55rem;
            bottom: 0.55rem;
            left: 0;
            width: 3px;
            border-radius: 0 3px 3px 0;
            background: #168267;
            content: "";
        }
        [data-testid="stSidebar"] [data-testid="stRadioOption"]:focus-visible {
            outline: 2px solid #168267;
            outline-offset: 2px;
        }
        @media (min-width: 1024px) {
            [data-testid="stSidebar"][aria-expanded="true"] {
                width: 250px !important;
                min-width: 250px !important;
                max-width: 250px !important;
            }
        }
        @media (min-width: 768px) and (max-width: 1023px) {
            [data-testid="stSidebar"][aria-expanded="true"] {
                width: 230px !important;
                min-width: 230px !important;
                max-width: 230px !important;
            }
        }
        [data-testid="stMainBlockContainer"] {
            padding-top: 4rem !important;
        }
        [class*="st-key-fintrack-metrics"] [data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.85rem;
        }
        [class*="st-key-fintrack-metrics"] [data-testid="stColumn"] {
            width: auto !important;
            min-width: 0 !important;
            flex: initial !important;
        }
        .fintrack-metric-card {
            min-height: 104px;
            padding: 1rem 0.9rem;
            border: 1px solid rgba(180, 199, 215, 0.48);
            border-radius: 0.9rem;
            background: rgba(255, 255, 255, 0.88);
            box-shadow: 0 5px 16px rgba(24, 57, 82, 0.055);
            transition: transform 170ms ease, box-shadow 170ms ease, border-color 170ms ease;
        }
        .fintrack-metric-card:hover {
            transform: translateY(-2px);
            border-color: rgba(61, 141, 137, 0.32);
            box-shadow: 0 9px 22px rgba(24, 57, 82, 0.1);
        }
        .fintrack-metric-label {
            color: #64778b;
            font-size: 0.8rem;
            font-weight: 600;
            line-height: 1.4;
        }
        .fintrack-metric-value {
            margin-top: 0.55rem;
            color: #183653;
            font-size: clamp(1rem, 1.35vw, 1.35rem);
            font-weight: 750;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }
        .fintrack-metric-value.positive {
            color: #13775d;
        }
        .fintrack-metric-value.negative {
            color: #b54747;
        }
        [class*="st-key-fintrack-demo-notice"] [data-testid="stAlert"] {
            border: 1px solid rgba(87, 151, 190, 0.2);
            border-left: 4px solid #3c8da3;
            border-radius: 0.85rem;
            background: rgba(239, 248, 253, 0.9);
            box-shadow: 0 4px 14px rgba(33, 86, 117, 0.045);
            color: #234c68;
        }
        [data-testid="stPlotlyChart"] {
            border: 1px solid rgba(180, 199, 215, 0.4);
            border-radius: 0.9rem;
            background: rgba(255, 255, 255, 0.86);
            box-shadow: 0 4px 16px rgba(24, 57, 82, 0.045);
        }
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button {
            border-radius: 0.7rem;
            font-weight: 600;
            transition: transform 150ms ease, box-shadow 150ms ease, border-color 150ms ease;
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {
            transform: translateY(-1px);
            border-color: rgba(22, 130, 103, 0.45);
            box-shadow: 0 4px 12px rgba(24, 57, 82, 0.08);
        }
        @media (min-width: 768px) and (max-width: 1023px) {
            [class*="st-key-fintrack-metrics"] [data-testid="stHorizontalBlock"] {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        @media (max-width: 767px) {
            [class*="st-key-fintrack-metrics"] [data-testid="stHorizontalBlock"] {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.65rem;
            }
            .fintrack-metric-card {
                min-height: 92px;
                padding: 0.85rem 0.75rem;
            }
            .fintrack-metric-label {
                font-size: 0.76rem;
            }
            .fintrack-metric-value {
                margin-top: 0.4rem;
                font-size: clamp(0.95rem, 4.6vw, 1.2rem);
            }
            [data-testid="stMainBlockContainer"] h1 {
                font-size: clamp(1.75rem, 7vw, 2.4rem);
            }
        }
        [class*="st-key-fintrack-header"] {
            min-height: 72px;
            display: flex;
            align-items: center;
            padding: 0 0.75rem;
            margin-bottom: 0.4rem;
            border-bottom: 1px solid rgba(100, 116, 139, 0.2);
            box-shadow: 0 2px 5px rgba(15, 23, 42, 0.025);
        }
        [class*="st-key-fintrack-header"] > [data-testid="stElementContainer"] {
            align-self: flex-start !important;
        }
        [class*="st-key-fintrack-header"] [data-testid="stImage"] {
            margin: 0 !important;
            display: flex;
            justify-content: flex-start !important;
        }
        [class*="st-key-fintrack-header"] [data-testid="stImage"] > div {
            margin-left: 0 !important;
            margin-right: auto !important;
        }
        [class*="st-key-fintrack-header"] img {
            display: block;
            width: clamp(220px, 28vw, 270px) !important;
            height: auto !important;
        }
        [data-testid="stExpandSidebarButton"],
        [data-testid="stSidebarCollapseButton"] {
            position: fixed !important;
            top: 4rem !important;
            right: 1.25rem !important;
            left: auto !important;
            z-index: 1001 !important;
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
            width: 2.5rem;
            height: 2.5rem;
            border: 1px solid rgba(100, 116, 139, 0.2);
            border-radius: 0.65rem;
            background: #ffffff;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
        }
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] {
                padding-top: 3.5rem !important;
            }
            [class*="st-key-fintrack-header"] {
                min-height: 64px;
                padding: 0 0.5rem;
                margin-bottom: 0.5rem;
            }
            [class*="st-key-fintrack-header"] img {
                width: min(200px, 48vw) !important;
            }
            [data-testid="stExpandSidebarButton"],
            [data-testid="stSidebarCollapseButton"] {
                top: 3.5rem !important;
                right: 0.75rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar.container(border=True):
        st.markdown("#### Navigation")
        options = get_page_options()
        selected = st.radio(
            "Navigation",
            options,
            index=options.index(st.session_state.page),
            label_visibility="collapsed",
        )
    st.session_state.page = selected

    st.sidebar.markdown("---")
    st.sidebar.caption("Demo data is synthetic and contains no real banking information.")

    with st.container(key="fintrack-header"):
        st.image(str(BRAND_LOGO_PATH), width=270)

    df = st.session_state.active_df

    if selected == "🏠 Dashboard":
        render_dashboard(df)
    elif selected == "💳 Transactions":
        render_transactions(df)
    elif selected == "📊 Analytics":
        render_analytics(df)
    elif selected == "📁 Upload Data":
        render_upload_data()
    elif selected == "ℹ️ About":
        render_about()


if __name__ == "__main__":
    main()
