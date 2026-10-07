# FinTrack — Personal Financial Tracker

**Personal Finance, Simplified.** FinTrack is a portfolio-quality personal finance dashboard built with Python, Streamlit, Pandas, Plotly and OpenPyXL. It helps users review balance trends, expenses, income, monthly summaries and cash-flow performance using a synthetic demo dataset.

The FinTrack brand logo is included at `assets/fintrack-logo.png` and displayed in the app sidebar.

## Features

- Dashboard overview with key financial metrics
- Interactive balance and spending charts
- Monthly income vs. expense analysis
- Expense-by-category breakdown
- Transaction explorer with search and filters
- Session-only CSV/XLSX upload support
- Download filtered transactions as CSV
- Privacy-focused demo-only workflow

## Technology

- Python
- Streamlit
- Pandas
- Plotly
- OpenPyXL

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub

1. Create a new GitHub repository named `personal-financial-tracker`.
2. Initialize it locally and add the project files.
3. Commit and push the repository to GitHub.
4. Keep the demo dataset in `data/demo_transactions.csv` and avoid adding any personal bank statements.

## Streamlit Deployment

1. Create a GitHub repository.
2. Upload the project files.
3. Open Streamlit Community Cloud.
4. Connect your GitHub account.
5. Select the repository.
6. Choose the branch to deploy.
7. Select `app.py` as the app entry point.
8. Deploy the app.

## Privacy

The repository contains only synthetic demo data. It does not include real banking information or uploaded personal files. The app does not permanently store uploaded files and they are only processed during the active session.
