from flask import Blueprint, request, jsonify, g
from app.extensions import db
from app.models.finance import UserBudget, UserSavingsGoal, UserLoanScenario
from app.models.audit import AuditAction, AuditStatus
from app.services.audit_service import log_audit
from app.security.decorators import jwt_required, verify_ownership
from app.security.input_validator import sanitize_text, validate_numeric_range

user_bp = Blueprint("user", __name__, url_prefix="/api/v1/user")


@user_bp.route("/summary", methods=["GET"])
@jwt_required()
def financial_summary():
    """Return current user's aggregated financial summary and active plans."""
    user = g.current_user

    budgets = UserBudget.query.filter_by(user_id=user.id).order_by(UserBudget.id.desc()).all()
    savings = UserSavingsGoal.query.filter_by(user_id=user.id).order_by(UserSavingsGoal.id.desc()).all()
    loans = UserLoanScenario.query.filter_by(user_id=user.id).order_by(UserLoanScenario.id.desc()).all()

    latest_budget = budgets[0].to_dict() if budgets else None
    total_projected_savings = sum(s.projected_total for s in savings)
    total_loan_balances = sum(l.principal for l in loans)
    total_monthly_debt_service = sum(l.monthly_payment for l in loans)

    return jsonify({
        "user": user.to_dict(),
        "summary": {
            "saved_budgets_count": len(budgets),
            "savings_goals_count": len(savings),
            "loan_scenarios_count": len(loans),
            "total_projected_savings": round(total_projected_savings, 2),
            "total_loan_balances": round(total_loan_balances, 2),
            "total_monthly_debt_service": round(total_monthly_debt_service, 2),
        },
        "latest_budget": latest_budget,
        "savings_goals": [s.to_dict() for s in savings],
        "loan_scenarios": [l.to_dict() for l in loans],
    }), 200


# -------------------------------------------------------------
# Budget CRUD (Scoped to owner)
# -------------------------------------------------------------
@user_bp.route("/budgets", methods=["GET"])
@jwt_required()
def get_budgets():
    """List budgets belonging to the authenticated user."""
    budgets = UserBudget.query.filter_by(user_id=g.current_user.id).all()
    return jsonify({"budgets": [b.to_dict() for b in budgets]}), 200


@user_bp.route("/budgets", methods=["POST"])
@jwt_required()
def save_budget():
    """Save a new budget scenario for current user."""
    data = request.get_json(silent=True) or {}

    valid_inc, income, err = validate_numeric_range(data.get("monthly_income"), 1.0, 10_000_000.0, "monthly_income")
    if not valid_inc:
        return jsonify({"error": err}), 400

    needs = float(data.get("needs_amount", income * 0.5))
    wants = float(data.get("wants_amount", income * 0.3))
    savings = float(data.get("savings_amount", income * 0.2))
    notes = sanitize_text(data.get("notes", ""))

    budget = UserBudget(
        user_id=g.current_user.id,
        monthly_income=income,
        needs_amount=needs,
        wants_amount=wants,
        savings_amount=savings,
        notes=notes,
    )
    db.session.add(budget)
    db.session.commit()

    log_audit(
        action=AuditAction.FINANCE_DATA_MUTATION,
        resource="/api/v1/user/budgets",
        status=AuditStatus.SUCCESS,
        user_id=g.current_user.id,
        username=g.current_user.username,
        details=f"Created budget plan ID {budget.id}"
    )

    return jsonify({"message": "Budget saved successfully.", "budget": budget.to_dict()}), 201


@user_bp.route("/budgets/<int:budget_id>", methods=["DELETE"])
@jwt_required()
def delete_budget(budget_id: int):
    """Delete a budget with IDOR protection."""
    budget = db.session.get(UserBudget, budget_id)
    if not budget:
        return jsonify({"error": "Budget not found."}), 404

    # IDOR Check: Ensure current user owns this budget or is Admin
    if not verify_ownership(budget.user_id):
        return jsonify({"error": "Forbidden: You do not have permission to access or delete this resource."}), 403

    db.session.delete(budget)
    db.session.commit()

    log_audit(
        action=AuditAction.FINANCE_DATA_MUTATION,
        resource=f"/api/v1/user/budgets/{budget_id}",
        status=AuditStatus.SUCCESS,
        user_id=g.current_user.id,
        username=g.current_user.username,
        details=f"Deleted budget plan ID {budget_id}"
    )

    return jsonify({"message": "Budget deleted successfully."}), 200


# -------------------------------------------------------------
# Savings Goal CRUD (Scoped to owner)
# -------------------------------------------------------------
@user_bp.route("/savings-goals", methods=["GET"])
@jwt_required()
def get_savings_goals():
    """List savings goals belonging to the authenticated user."""
    goals = UserSavingsGoal.query.filter_by(user_id=g.current_user.id).all()
    return jsonify({"savings_goals": [g.to_dict() for g in goals]}), 200


@user_bp.route("/savings-goals", methods=["POST"])
@jwt_required()
def save_savings_goal():
    """Save a compound interest savings goal for current user."""
    data = request.get_json(silent=True) or {}
    title = sanitize_text(data.get("title", "My Savings Goal"), max_length=80)

    goal = UserSavingsGoal(
        user_id=g.current_user.id,
        title=title,
        target_amount=float(data.get("target_amount", 10000)),
        initial_deposit=float(data.get("initial_deposit", 0)),
        monthly_contribution=float(data.get("monthly_contribution", 200)),
        annual_interest_rate=float(data.get("annual_interest_rate", 5.0)),
        time_horizon_years=int(data.get("time_horizon_years", 5)),
        projected_total=float(data.get("projected_total", 0)),
        total_interest_earned=float(data.get("total_interest_earned", 0)),
    )
    db.session.add(goal)
    db.session.commit()

    return jsonify({"message": "Savings goal saved.", "savings_goal": goal.to_dict()}), 201


@user_bp.route("/savings-goals/<int:goal_id>", methods=["DELETE"])
@jwt_required()
def delete_savings_goal(goal_id: int):
    """Delete a savings goal with IDOR protection."""
    goal = db.session.get(UserSavingsGoal, goal_id)
    if not goal:
        return jsonify({"error": "Savings goal not found."}), 404

    if not verify_ownership(goal.user_id):
        return jsonify({"error": "Forbidden: You do not have permission to access or delete this resource."}), 403

    db.session.delete(goal)
    db.session.commit()
    return jsonify({"message": "Savings goal deleted."}), 200


# -------------------------------------------------------------
# Loan Scenarios CRUD (Scoped to owner)
# -------------------------------------------------------------
@user_bp.route("/loans", methods=["GET"])
@jwt_required()
def get_loans():
    """List loan scenarios belonging to the authenticated user."""
    loans = UserLoanScenario.query.filter_by(user_id=g.current_user.id).all()
    return jsonify({"loans": [l.to_dict() for l in loans]}), 200


@user_bp.route("/loans", methods=["POST"])
@jwt_required()
def save_loan():
    """Save a loan scenario for current user."""
    data = request.get_json(silent=True) or {}
    name = sanitize_text(data.get("loan_name", "My Loan"), max_length=80)

    loan = UserLoanScenario(
        user_id=g.current_user.id,
        loan_name=name,
        principal=float(data.get("principal", 10000)),
        annual_rate=float(data.get("annual_rate", 6.0)),
        term_months=int(data.get("term_months", 36)),
        monthly_payment=float(data.get("monthly_payment", 0)),
        total_interest=float(data.get("total_interest", 0)),
        total_cost=float(data.get("total_cost", 0)),
    )
    db.session.add(loan)
    db.session.commit()

    return jsonify({"message": "Loan scenario saved.", "loan": loan.to_dict()}), 201


@user_bp.route("/loans/<int:loan_id>", methods=["DELETE"])
@jwt_required()
def delete_loan(loan_id: int):
    """Delete a loan scenario with IDOR protection."""
    loan = db.session.get(UserLoanScenario, loan_id)
    if not loan:
        return jsonify({"error": "Loan scenario not found."}), 404

    if not verify_ownership(loan.user_id):
        return jsonify({"error": "Forbidden: You do not have permission to access or delete this resource."}), 403

    db.session.delete(loan)
    db.session.commit()
    return jsonify({"message": "Loan scenario deleted."}), 200
