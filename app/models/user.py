from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db

class UserRole:
    ADMIN = "Admin"
    ANALYST = "Financial Analyst"
    USER = "User"
    
    ALL_ROLES = [ADMIN, ANALYST, USER]


class User(db.Model):
    """User account model with RBAC role and secure credential storage."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default=UserRole.USER, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    budgets = db.relationship("UserBudget", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    savings_goals = db.relationship("UserSavingsGoal", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")
    loan_scenarios = db.relationship("UserLoanScenario", back_populates="user", cascade="all, delete-orphan", lazy="dynamic")

    def set_password(self, password: str) -> None:
        """Hash password using scrypt or pbkdf2_sha256 with strong work factor."""
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password: str) -> bool:
        """Verify password against stored cryptographic hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """Safe dictionary representation (never returns password_hash)."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' role='{self.role}'>"
