from flask import Blueprint, request, jsonify
from app.services.calculator_service import calculate_budget, calculate_savings, calculate_loan
from app.security.decorators import jwt_required
from app.security.input_validator import validate_numeric_range
from app.extensions import limiter

calculator_bp = Blueprint("calculators", __name__, url_prefix="/api/v1/calculators")


@calculator_bp.route("/budget", methods=["POST"])
@jwt_required()
@limiter.limit("60 per minute")
def budget():
    """Calculate 50/30/20 or custom percentage budget allocation."""
    data = request.get_json(silent=True) or {}

    valid_inc, income, err = validate_numeric_range(data.get("monthly_income"), 1.0, 10_000_000.0, "monthly_income")
    if not valid_inc:
        return jsonify({"error": err}), 400

    needs_pct = float(data.get("needs_pct", 50.0))
    wants_pct = float(data.get("wants_pct", 30.0))
    savings_pct = float(data.get("savings_pct", 20.0))

    if needs_pct < 0 or wants_pct < 0 or savings_pct < 0:
        return jsonify({"error": "Percentages cannot be negative."}), 400

    result = calculate_budget(income, needs_pct, wants_pct, savings_pct)
    return jsonify(result), 200


@calculator_bp.route("/savings", methods=["POST"])
@jwt_required()
@limiter.limit("60 per minute")
def savings():
    """Calculate compound interest future value and yearly trajectory."""
    data = request.get_json(silent=True) or {}

    valid_init, init_dep, err = validate_numeric_range(data.get("initial_deposit", 0), 0.0, 100_000_000.0, "initial_deposit")
    if not valid_init:
        return jsonify({"error": err}), 400

    valid_mon, monthly_dep, err = validate_numeric_range(data.get("monthly_contribution", 0), 0.0, 1_000_000.0, "monthly_contribution")
    if not valid_mon:
        return jsonify({"error": err}), 400

    valid_rate, rate, err = validate_numeric_range(data.get("annual_rate_pct"), 0.0, 100.0, "annual_rate_pct")
    if not valid_rate:
        return jsonify({"error": err}), 400

    valid_yrs, years, err = validate_numeric_range(data.get("years"), 1.0, 60.0, "years")
    if not valid_yrs:
        return jsonify({"error": err}), 400

    result = calculate_savings(
        initial_deposit=init_dep,
        monthly_contribution=monthly_dep,
        annual_rate_pct=rate,
        years=int(years)
    )
    return jsonify(result), 200


@calculator_bp.route("/loan", methods=["POST"])
@jwt_required()
@limiter.limit("60 per minute")
def loan():
    """Calculate monthly loan amortization payment and total interest cost."""
    data = request.get_json(silent=True) or {}

    valid_p, principal, err = validate_numeric_range(data.get("principal"), 100.0, 50_000_000.0, "principal")
    if not valid_p:
        return jsonify({"error": err}), 400

    valid_rate, rate, err = validate_numeric_range(data.get("annual_rate_pct"), 0.0, 100.0, "annual_rate_pct")
    if not valid_rate:
        return jsonify({"error": err}), 400

    valid_term, term_months, err = validate_numeric_range(data.get("term_months"), 1.0, 600.0, "term_months")
    if not valid_term:
        return jsonify({"error": err}), 400

    result = calculate_loan(
        principal=principal,
        annual_rate_pct=rate,
        term_months=int(term_months)
    )
    return jsonify(result), 200
