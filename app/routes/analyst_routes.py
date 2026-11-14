from flask import Blueprint, request, jsonify, g
from app.models.user import UserRole
from app.models.audit import AuditAction, AuditStatus
from app.services.audit_service import log_audit
from app.services.analyst_service import (
    get_authorized_datasets,
    run_portfolio_stress_test,
    run_monte_carlo_simulation,
    seed_analyst_datasets_if_needed,
)
from app.security.decorators import jwt_required, roles_required
from app.security.input_validator import validate_numeric_range
from app.extensions import limiter

analyst_bp = Blueprint("analyst", __name__, url_prefix="/api/v1/analyst")


@analyst_bp.before_request
def ensure_datasets_seeded():
    """Ensure authorized analyst datasets are present."""
    seed_analyst_datasets_if_needed()


@analyst_bp.route("/datasets", methods=["GET"])
@jwt_required()
@roles_required(UserRole.ANALYST, UserRole.ADMIN)
def list_datasets():
    """Retrieve authorized macro and benchmark datasets for analyst users."""
    category = request.args.get("category")
    datasets = get_authorized_datasets(category)
    return jsonify({
        "authorized_datasets": datasets,
        "count": len(datasets)
    }), 200


@analyst_bp.route("/stress-test", methods=["POST"])
@jwt_required()
@roles_required(UserRole.ANALYST, UserRole.ADMIN)
@limiter.limit("30 per minute")
def stress_test():
    """Simulate asset class portfolio drawdowns under macro inflation & rate hike stress."""
    data = request.get_json(silent=True) or {}

    equity = float(data.get("equity_pct", 60.0))
    bond = float(data.get("bond_pct", 30.0))
    cash = float(data.get("cash_pct", 10.0))
    inf_shock = float(data.get("inflation_shock_bps", 200.0))
    rate_shock = float(data.get("interest_rate_hike_bps", 150.0))

    result = run_portfolio_stress_test(
        equity_pct=equity,
        bond_pct=bond,
        cash_pct=cash,
        inflation_shock_bps=inf_shock,
        interest_rate_hike_bps=rate_shock,
    )

    log_audit(
        action=AuditAction.ANALYST_REPORT_GENERATE,
        resource="/api/v1/analyst/stress-test",
        status=AuditStatus.SUCCESS,
        user_id=g.current_user.id,
        username=g.current_user.username,
        details=f"Ran stress test: Equity={equity}%, Bond={bond}%, Cash={cash}%"
    )

    return jsonify(result), 200


@analyst_bp.route("/monte-carlo", methods=["POST"])
@jwt_required()
@roles_required(UserRole.ANALYST, UserRole.ADMIN)
@limiter.limit("20 per minute")
def monte_carlo():
    """Run educational Monte Carlo projection with confidence intervals (10th, 50th, 90th percentiles)."""
    data = request.get_json(silent=True) or {}

    valid_init, init_bal, err = validate_numeric_range(data.get("initial_balance", 10000), 0.0, 50_000_000.0, "initial_balance")
    if not valid_init:
        return jsonify({"error": err}), 400

    valid_dep, monthly_dep, err = validate_numeric_range(data.get("monthly_deposit", 500), 0.0, 1_000_000.0, "monthly_deposit")
    if not valid_dep:
        return jsonify({"error": err}), 400

    valid_mean, mean_ret, err = validate_numeric_range(data.get("annual_mean_return_pct", 8.0), -20.0, 40.0, "annual_mean_return_pct")
    if not valid_mean:
        return jsonify({"error": err}), 400

    valid_vol, vol, err = validate_numeric_range(data.get("annual_volatility_pct", 15.0), 1.0, 50.0, "annual_volatility_pct")
    if not valid_vol:
        return jsonify({"error": err}), 400

    valid_yrs, years, err = validate_numeric_range(data.get("years", 10), 1.0, 30.0, "years")
    if not valid_yrs:
        return jsonify({"error": err}), 400

    simulations = int(data.get("num_simulations", 300))
    # Cap simulations to prevent DoS
    simulations = min(max(50, simulations), 1000)

    result = run_monte_carlo_simulation(
        initial_balance=init_bal,
        monthly_deposit=monthly_dep,
        annual_mean_return_pct=mean_ret,
        annual_volatility_pct=vol,
        years=int(years),
        num_simulations=simulations,
    )

    log_audit(
        action=AuditAction.ANALYST_REPORT_GENERATE,
        resource="/api/v1/analyst/monte-carlo",
        status=AuditStatus.SUCCESS,
        user_id=g.current_user.id,
        username=g.current_user.username,
        details=f"Ran Monte Carlo: {years} years, {simulations} iterations"
    )

    return jsonify(result), 200
