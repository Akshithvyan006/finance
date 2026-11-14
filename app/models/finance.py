from datetime import datetime, timezone
from app.extensions import db

class UserBudget(db.Model):
    """Stores user monthly budget allocations based on 50/30/20 or custom rules."""
    __tablename__ = "user_budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    monthly_income = db.Column(db.Float, nullable=False)
    needs_amount = db.Column(db.Float, nullable=False)
    wants_amount = db.Column(db.Float, nullable=False)
    savings_amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="budgets")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "monthly_income": self.monthly_income,
            "needs_amount": self.needs_amount,
            "wants_amount": self.wants_amount,
            "savings_amount": self.savings_amount,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSavingsGoal(db.Model):
    """Stores user compound interest & target savings scenarios."""
    __tablename__ = "user_savings_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    initial_deposit = db.Column(db.Float, default=0.0, nullable=False)
    monthly_contribution = db.Column(db.Float, nullable=False)
    annual_interest_rate = db.Column(db.Float, nullable=False)  # in percent, e.g. 5.5
    time_horizon_years = db.Column(db.Integer, nullable=False)
    projected_total = db.Column(db.Float, nullable=False)
    total_interest_earned = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="savings_goals")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "target_amount": self.target_amount,
            "initial_deposit": self.initial_deposit,
            "monthly_contribution": self.monthly_contribution,
            "annual_interest_rate": self.annual_interest_rate,
            "time_horizon_years": self.time_horizon_years,
            "projected_total": round(self.projected_total, 2),
            "total_interest_earned": round(self.total_interest_earned, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserLoanScenario(db.Model):
    """Stores loan repayment calculations and amortization scenarios."""
    __tablename__ = "user_loan_scenarios"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    loan_name = db.Column(db.String(100), nullable=False)
    principal = db.Column(db.Float, nullable=False)
    annual_rate = db.Column(db.Float, nullable=False)  # in percent, e.g. 6.5
    term_months = db.Column(db.Integer, nullable=False)
    monthly_payment = db.Column(db.Float, nullable=False)
    total_interest = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship("User", back_populates="loan_scenarios")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "loan_name": self.loan_name,
            "principal": self.principal,
            "annual_rate": self.annual_rate,
            "term_months": self.term_months,
            "monthly_payment": round(self.monthly_payment, 2),
            "total_interest": round(self.total_interest, 2),
            "total_cost": round(self.total_cost, 2),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AnalystDataset(db.Model):
    """Authorized macroeconomic, cohort, and market datasets for Financial Analysts."""
    __tablename__ = "analyst_datasets"

    id = db.Column(db.Integer, primary_key=True)
    dataset_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # 'macro', 'benchmarks', 'portfolio'
    description = db.Column(db.Text, nullable=False)
    payload_json = db.Column(db.Text, nullable=False)  # JSON-encoded array or object
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "dataset_code": self.dataset_code,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "data": json.loads(self.payload_json) if self.payload_json else {},
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
