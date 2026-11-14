import pytest
from app.services.calculator_service import calculate_budget, calculate_savings, calculate_loan

def test_budget_calculation_50_30_20():
    """Verify 50/30/20 standard budget math and emergency fund targets."""
    result = calculate_budget(monthly_income=5000.0, needs_pct=50, wants_pct=30, savings_pct=20)
    assert result["allocations"]["needs"] == 2500.0
    assert result["allocations"]["wants"] == 1500.0
    assert result["allocations"]["savings"] == 1000.0
    # 6-month emergency fund target = 6 * needs
    assert result["summary"]["emergency_fund_target_6mo"] == 15000.0
    assert "DISCLAIMER" in result["disclaimer"]


def test_savings_compound_calculation():
    """Verify compound interest calculation and trajectory generation."""
    # $10,000 initial, $500/month, 6% annual, 5 years
    result = calculate_savings(
        initial_deposit=10000.0,
        monthly_contribution=500.0,
        annual_rate_pct=6.0,
        years=5
    )
    assert result["results"]["future_value"] > 45000.0
    assert result["results"]["total_principal"] == 10000.0 + (500.0 * 60)
    assert result["results"]["total_interest_earned"] > 0
    assert len(result["trajectory"]) == 5
    # Verify last year matches future_value
    assert result["trajectory"][-1]["total_balance"] == result["results"]["future_value"]


def test_loan_amortization_calculation():
    """Verify loan monthly payment, interest total, and amortization schedule."""
    # $20,000, 6% APR, 36 months (3 years)
    result = calculate_loan(
        principal=20000.0,
        annual_rate_pct=6.0,
        term_months=36
    )
    # Expected payment for 20k @ 6% for 36 months is approx $608.44
    assert 600.0 < result["results"]["monthly_payment"] < 615.0
    assert result["results"]["total_interest"] > 0
    assert len(result["schedule_preview"]) == 12
    # Verify principal decreases over first 12 months
    first_month_bal = result["schedule_preview"][0]["remaining_balance"]
    twelfth_month_bal = result["schedule_preview"][11]["remaining_balance"]
    assert twelfth_month_bal < first_month_bal


def test_loan_zero_interest():
    """Verify zero interest rate edge case."""
    result = calculate_loan(
        principal=12000.0,
        annual_rate_pct=0.0,
        term_months=12
    )
    assert result["results"]["monthly_payment"] == 1000.0
    assert result["results"]["total_interest"] == 0.0
