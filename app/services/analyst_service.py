import json
import random
import math
from typing import Dict, Any, List
from app.extensions import db
from app.models.finance import AnalystDataset
from app.security.guardrails import EDUCATIONAL_DISCLAIMER

# Benchmark market and macroeconomic historical datasets
DEFAULT_DATASETS = [
    {
        "dataset_code": "MACRO_INFLATION_BENCHMARK_2015_2024",
        "title": "US Headline CPI vs. 10-Year Treasury Yield (2015-2024)",
        "category": "macro",
        "description": "Annualized headline Consumer Price Index (CPI) compared with 10-Year Treasury constant maturity yields.",
        "payload": {
            "years": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024],
            "cpi_inflation_pct": [0.1, 1.3, 2.1, 2.4, 1.8, 1.2, 4.7, 8.0, 4.1, 2.9],
            "us_10yr_treasury_yield_pct": [2.14, 1.84, 2.33, 2.91, 2.14, 0.89, 1.45, 2.95, 3.88, 4.25],
            "sp500_annual_return_pct": [1.38, 11.96, 21.83, -4.38, 31.49, 18.40, 28.71, -18.11, 26.29, 24.50]
        }
    },
    {
        "dataset_code": "ASSET_CLASS_RISK_RETURN_MATRIX",
        "title": "Multi-Asset Class Long-Term Volatility & Expected Real Returns",
        "category": "benchmarks",
        "description": "Historical annualized expected return, standard deviation, and maximum historical drawdown benchmarks.",
        "payload": {
            "asset_classes": [
                {"name": "Cash & Cash Equivalents", "expected_return": 3.8, "volatility": 1.2, "max_drawdown": -0.5},
                {"name": "Investment Grade Bonds", "expected_return": 5.2, "volatility": 6.8, "max_drawdown": -15.2},
                {"name": "Large Cap Global Equities", "expected_return": 9.5, "volatility": 16.5, "max_drawdown": -37.0},
                {"name": "Emerging Markets Equities", "expected_return": 10.8, "volatility": 22.1, "max_drawdown": -53.2},
                {"name": "Real Estate Investment Trusts (REITs)", "expected_return": 8.4, "volatility": 18.2, "max_drawdown": -41.5}
            ]
        }
    },
    {
        "dataset_code": "CONSUMER_DEBT_COHORT_ANALYSIS",
        "title": "National Household Debt by Category & Average APR",
        "category": "credit",
        "description": "Aggregate distribution of consumer debt obligations and prevailing interest rate bands.",
        "payload": {
            "categories": [
                {"debt_type": "Mortgages (30-Year Fixed)", "avg_apr": 6.85, "aggregate_share_pct": 71.0},
                {"debt_type": "Student Loans", "avg_apr": 5.80, "aggregate_share_pct": 9.0},
                {"debt_type": "Auto Loans", "avg_apr": 7.40, "aggregate_share_pct": 9.0},
                {"debt_type": "Revolving Credit Card Debt", "avg_apr": 21.50, "aggregate_share_pct": 7.0},
                {"debt_type": "Other Consumer Debt", "avg_apr": 11.20, "aggregate_share_pct": 4.0}
            ]
        }
    }
]


def seed_analyst_datasets_if_needed():
    """Ensure authorized datasets exist in the database for Financial Analysts."""
    for item in DEFAULT_DATASETS:
        existing = AnalystDataset.query.filter_by(dataset_code=item["dataset_code"]).first()
        if not existing:
            new_dataset = AnalystDataset(
                dataset_code=item["dataset_code"],
                title=item["title"],
                category=item["category"],
                description=item["description"],
                payload_json=json.dumps(item["payload"]),
            )
            db.session.add(new_dataset)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()


def get_authorized_datasets(category: str = None) -> List[Dict[str, Any]]:
    """Retrieve datasets authorized for Analyst role inspection."""
    query = AnalystDataset.query
    if category:
        query = query.filter_by(category=category)
    datasets = query.order_by(AnalystDataset.id.asc()).all()
    return [ds.to_dict() for ds in datasets]


def run_portfolio_stress_test(
    equity_pct: float,
    bond_pct: float,
    cash_pct: float,
    inflation_shock_bps: float = 200.0,
    interest_rate_hike_bps: float = 150.0
) -> Dict[str, Any]:
    """Simulate portfolio sensitivity to combined inflation and interest rate shocks."""
    total = equity_pct + bond_pct + cash_pct
    if abs(total - 100.0) > 0.01:
        equity_pct = (equity_pct / total) * 100.0
        bond_pct = (bond_pct / total) * 100.0
        cash_pct = (cash_pct / total) * 100.0

    # Sensitivity coefficients based on empirical duration and equity risk premia
    # Equity valuation multiple contraction from discount rate hike
    equity_shock = -(interest_rate_hike_bps / 100.0) * 3.8 - (inflation_shock_bps / 100.0) * 1.5
    # Bond price change approx: -Duration * Delta_y (assume intermediate duration ~ 6 years)
    bond_shock = -(interest_rate_hike_bps / 10000.0) * 6.2 * 100.0
    # Cash benefits modestly from rising short rates but suffers real purchasing power erosion
    cash_shock = (interest_rate_hike_bps / 10000.0) * 0.9 * 100.0 - (inflation_shock_bps / 10000.0) * 100.0

    weighted_impact_pct = (
        (equity_pct / 100.0) * equity_shock +
        (bond_pct / 100.0) * bond_shock +
        (cash_pct / 100.0) * cash_shock
    )

    risk_rating = "Moderate"
    if abs(weighted_impact_pct) > 15.0:
        risk_rating = "High Sensitivity"
    elif abs(weighted_impact_pct) < 5.0:
        risk_rating = "Low Sensitivity (Defensive)"

    return {
        "portfolio_allocation": {
            "equity_pct": round(equity_pct, 1),
            "bond_pct": round(bond_pct, 1),
            "cash_pct": round(cash_pct, 1),
        },
        "stress_parameters": {
            "inflation_shock_bps": inflation_shock_bps,
            "interest_rate_hike_bps": interest_rate_hike_bps,
        },
        "simulated_impact": {
            "equity_segment_change_pct": round(equity_shock, 2),
            "bond_segment_change_pct": round(bond_shock, 2),
            "cash_segment_change_pct": round(cash_shock, 2),
            "net_portfolio_impact_pct": round(weighted_impact_pct, 2),
            "risk_rating": risk_rating,
        },
        "disclaimer": EDUCATIONAL_DISCLAIMER,
    }


def run_monte_carlo_simulation(
    initial_balance: float,
    monthly_deposit: float,
    annual_mean_return_pct: float,
    annual_volatility_pct: float,
    years: int,
    num_simulations: int = 500
) -> Dict[str, Any]:
    """Run educational Monte Carlo projection to estimate 10th, 50th, and 90th percentile trajectories."""
    random.seed(42)  # Deterministic seed for reproducible testing
    total_months = years * 12
    monthly_mean = (annual_mean_return_pct / 100.0) / 12.0
    monthly_vol = (annual_volatility_pct / 100.0) / math.sqrt(12.0)

    # Store balance snapshots at each year-end for all runs
    yearly_runs: List[List[float]] = [[] for _ in range(years + 1)]

    # Initial year 0
    for _ in range(num_simulations):
        yearly_runs[0].append(initial_balance)

    for _ in range(num_simulations):
        bal = initial_balance
        for m in range(1, total_months + 1):
            shock = random.gauss(monthly_mean, monthly_vol)
            bal = max(0.0, bal * (1.0 + shock) + monthly_deposit)
            if m % 12 == 0:
                y = m // 12
                yearly_runs[y].append(bal)

    percentiles_by_year = []
    for y in range(years + 1):
        vals = sorted(yearly_runs[y])
        p10 = vals[int(0.10 * len(vals))]
        p50 = vals[int(0.50 * len(vals))]
        p90 = vals[int(0.90 * len(vals))]
        percentiles_by_year.append({
            "year": y,
            "percentile_10_bear": round(p10, 2),
            "percentile_50_median": round(p50, 2),
            "percentile_90_bull": round(p90, 2),
        })

    final_median = percentiles_by_year[-1]["percentile_50_median"]
    total_invested = initial_balance + (monthly_deposit * total_months)

    return {
        "simulation_parameters": {
            "initial_balance": initial_balance,
            "monthly_deposit": monthly_deposit,
            "annual_mean_return_pct": annual_mean_return_pct,
            "annual_volatility_pct": annual_volatility_pct,
            "years": years,
            "simulations_count": num_simulations,
            "total_capital_invested": round(total_invested, 2),
        },
        "terminal_metrics": {
            "bear_case_10th_percentile": percentiles_by_year[-1]["percentile_10_bear"],
            "median_case_50th_percentile": final_median,
            "bull_case_90th_percentile": percentiles_by_year[-1]["percentile_90_bull"],
            "success_probability_over_capital_pct": round(
                (sum(1 for v in yearly_runs[-1] if v >= total_invested) / num_simulations) * 100.0, 1
            ),
        },
        "yearly_trajectory": percentiles_by_year,
        "disclaimer": EDUCATIONAL_DISCLAIMER,
    }
