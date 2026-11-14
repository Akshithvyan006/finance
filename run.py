import os
from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.finance import UserBudget, UserSavingsGoal, UserLoanScenario
from app.services.analyst_service import seed_analyst_datasets_if_needed
from app.services.audit_service import log_audit
from app.models.audit import AuditAction, AuditStatus

app = create_app(os.getenv("FLASK_ENV", "development"))


def seed_database():
    """Seed initial development-only user accounts and demo financial records."""
    with app.app_context():
        db.create_all()

        # Seed safe development sample accounts
        demo_accounts = [
            {
                "username": "admin_sec",
                "email": "admin@finsec.local",
                "password": "AdminPassword!2026",
                "role": UserRole.ADMIN,
            },
            {
                "username": "analyst_jane",
                "email": "analyst@finsec.local",
                "password": "AnalystSecure!2026",
                "role": UserRole.ANALYST,
            },
            {
                "username": "user_john",
                "email": "john@finsec.local",
                "password": "UserPassword!2026",
                "role": UserRole.USER,
            },
        ]

        for acc in demo_accounts:
            existing = User.query.filter_by(username=acc["username"]).first()
            if not existing:
                u = User(
                    username=acc["username"],
                    email=acc["email"],
                    role=acc["role"],
                    is_active=True,
                )
                u.set_password(acc["password"])
                db.session.add(u)
                db.session.commit()
                print(f"[SEED] Created demo account: {acc['username']} ({acc['role']})")

        # Seed sample financial records for user_john
        john = User.query.filter_by(username="user_john").first()
        if john:
            # Seed budget
            if not UserBudget.query.filter_by(user_id=john.id).first():
                b = UserBudget(
                    user_id=john.id,
                    monthly_income=5000.0,
                    needs_amount=2500.0,
                    wants_amount=1500.0,
                    savings_amount=1000.0,
                    notes="Baseline 50/30/20 monthly budget plan"
                )
                db.session.add(b)

            # Seed savings goal
            if not UserSavingsGoal.query.filter_by(user_id=john.id).first():
                s = UserSavingsGoal(
                    user_id=john.id,
                    title="Emergency Fund & High Yield Savings",
                    target_amount=15000.0,
                    initial_deposit=3000.0,
                    monthly_contribution=500.0,
                    annual_interest_rate=5.0,
                    time_horizon_years=2,
                    projected_total=16124.50,
                    total_interest_earned=1124.50,
                )
                db.session.add(s)

            # Seed loan scenario
            if not UserLoanScenario.query.filter_by(user_id=john.id).first():
                l = UserLoanScenario(
                    user_id=john.id,
                    loan_name="Auto Loan Refinance",
                    principal=18000.0,
                    annual_rate=5.5,
                    term_months=48,
                    monthly_payment=418.66,
                    total_interest=2095.68,
                    total_cost=20095.68,
                )
                db.session.add(l)

            db.session.commit()

        # Seed analyst datasets
        seed_analyst_datasets_if_needed()

        # Record initial system startup audit log
        log_audit(
            action="SYSTEM_INITIALIZE",
            resource="database",
            status=AuditStatus.SUCCESS,
            details="Database schema initialized and demo seed accounts validated"
        )
        print("[SEED] Database initialized successfully.")


if __name__ == "__main__":
    seed_database()
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", 5000))
    print(f"==================================================")
    print(f" SECURE FINANCIAL ANALYSIS CHATBOT (RBAC PROTOTYPE)")
    print(f" Server running at: http://{host}:{port}")
    print(f"==================================================")
    app.run(host=host, port=port, debug=True)
