from typing import Dict, Any, List
from app.security.guardrails import EDUCATIONAL_DISCLAIMER

def calculate_budget(
    monthly_income: float,
    needs_pct: float = 50.0,
    wants_pct: float = 30.0,
    savings_pct: float = 20.0,
) -> Dict[str, Any]:
    """Calculate budget breakdown based on 50/30/20 standard or custom percentages."""
    total_pct = needs_pct + wants_pct + savings_pct
    if abs(total_pct - 100.0) > 0.01:
        # Normalize to 100%
        needs_pct = (needs_pct / total_pct) * 100.0
        wants_pct = (wants_pct / total_pct) * 100.0
        savings_pct = (savings_pct / total_pct) * 100.0

    needs_amount = round((monthly_income * needs_pct) / 100.0, 2)
    wants_amount = round((monthly_income * wants_pct) / 100.0, 2)
    savings_amount = round((monthly_income * savings_pct) / 100.0, 2)

    return {
        "monthly_income": round(monthly_income, 2),
        "percentages": {
            "needs": round(needs_pct, 1),
            "wants": round(wants_pct, 1),
            "savings": round(savings_pct, 1),
        },
        "allocations": {
            "needs": needs_amount,
            "wants": wants_amount,
            "savings": savings_amount,
        },
        "summary": {
            "total_allocated": round(needs_amount + wants_amount + savings_amount, 2),
            "emergency_fund_target_6mo": round(needs_amount * 6, 2),
        },
        "assumptions": [
            "Assumes net take-home monthly income after taxes.",
            "Needs cover non-negotiables: rent/mortgage, utilities, basic groceries, insurance.",
            "Wants cover lifestyle, dining, entertainment, discretionary purchases.",
            "Savings include emergency savings, debt reduction above minimums, and investments."
        ],
        "disclaimer": EDUCATIONAL_DISCLAIMER,
    }


def calculate_savings(
    initial_deposit: float,
    monthly_contribution: float,
    annual_rate_pct: float,
    years: int,
    compounding_frequency: int = 12,
) -> Dict[str, Any]:
    """Calculate future value with compound interest and recurring deposits."""
    r = (annual_rate_pct / 100.0)
    n = max(1, compounding_frequency)
    total_months = years * 12

    yearly_trajectory: List[Dict[str, Any]] = []
    current_balance = float(initial_deposit)
    total_deposited = float(initial_deposit)

    # Monthly stepping for accuracy
    monthly_rate = r / 12.0

    for month in range(1, total_months + 1):
        # Add interest
        interest = current_balance * monthly_rate
        current_balance += interest + monthly_contribution
        total_deposited += monthly_contribution

        if month % 12 == 0 or month == total_months:
            year_num = month // 12
            total_interest = current_balance - total_deposited
            yearly_trajectory.append({
                "year": year_num,
                "principal_invested": round(total_deposited, 2),
                "interest_earned": round(max(0.0, total_interest), 2),
                "total_balance": round(current_balance, 2),
            })

    total_interest_earned = max(0.0, current_balance - total_deposited)

    return {
        "parameters": {
            "initial_deposit": round(initial_deposit, 2),
            "monthly_contribution": round(monthly_contribution, 2),
            "annual_rate_pct": round(annual_rate_pct, 2),
            "years": years,
        },
        "results": {
            "future_value": round(current_balance, 2),
            "total_principal": round(total_deposited, 2),
            "total_interest_earned": round(total_interest_earned, 2),
            "interest_ratio_pct": round((total_interest_earned / current_balance * 100.0) if current_balance > 0 else 0, 1),
        },
        "trajectory": yearly_trajectory,
        "assumptions": [
            f"Constant annual return rate of {annual_rate_pct}%. Actual market returns fluctuate.",
            "Monthly contributions made consistently at the end of each period.",
            "Taxes and inflation are not deducted from gross interest."
        ],
        "disclaimer": EDUCATIONAL_DISCLAIMER,
    }


def calculate_loan(
    principal: float,
    annual_rate_pct: float,
    term_months: int,
) -> Dict[str, Any]:
    """Calculate fixed-rate loan amortization, monthly payment, and total interest."""
    if term_months <= 0:
        raise ValueError("Term must be at least 1 month.")

    if annual_rate_pct == 0:
        monthly_payment = principal / term_months
        total_interest = 0.0
    else:
        monthly_rate = (annual_rate_pct / 100.0) / 12.0
        # M = P * [r(1+r)^n] / [(1+r)^n - 1]
        factor = (1.0 + monthly_rate) ** term_months
        monthly_payment = principal * (monthly_rate * factor) / (factor - 1.0)
        total_interest = (monthly_payment * term_months) - principal

    # Generate amortization schedule preview (first 12 months)
    schedule: List[Dict[str, Any]] = []
    balance = principal
    monthly_rate = (annual_rate_pct / 100.0) / 12.0

    for m in range(1, min(term_months + 1, 13)):
        interest_payment = balance * monthly_rate if annual_rate_pct > 0 else 0.0
        principal_payment = monthly_payment - interest_payment
        balance = max(0.0, balance - principal_payment)
        schedule.append({
            "month": m,
            "payment": round(monthly_payment, 2),
            "principal_payment": round(principal_payment, 2),
            "interest_payment": round(interest_payment, 2),
            "remaining_balance": round(balance, 2),
        })

    return {
        "parameters": {
            "principal": round(principal, 2),
            "annual_rate_pct": round(annual_rate_pct, 2),
            "term_months": term_months,
            "term_years": round(term_months / 12.0, 1),
        },
        "results": {
            "monthly_payment": round(monthly_payment, 2),
            "total_interest": round(max(0.0, total_interest), 2),
            "total_cost": round(principal + max(0.0, total_interest), 2),
        },
        "schedule_preview": schedule,
        "assumptions": [
            "Fixed interest rate compounded monthly throughout the entire term.",
            "No prepayment penalties, origination fees, or escrow additions included.",
            "Payments made on time each month."
        ],
        "disclaimer": EDUCATIONAL_DISCLAIMER,
    }
