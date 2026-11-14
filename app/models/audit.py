from datetime import datetime, timezone
from app.extensions import db

class AuditStatus:
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    FAILED = "FAILED"
    WARNING = "WARNING"


class AuditAction:
    AUTH_LOGIN = "AUTH_LOGIN"
    AUTH_LOGIN_FAILED = "AUTH_LOGIN_FAILED"
    AUTH_LOGOUT = "AUTH_LOGOUT"
    AUTH_REGISTER = "AUTH_REGISTER"
    USER_ROLE_CHANGE = "USER_ROLE_CHANGE"
    USER_STATUS_CHANGE = "USER_STATUS_CHANGE"
    CHATBOT_PROMPT_INJECTION_DETECTED = "CHATBOT_PROMPT_INJECTION_DETECTED"
    ACCESS_CONTROL_VIOLATION = "ACCESS_CONTROL_VIOLATION"
    IDOR_ATTEMPT = "IDOR_ATTEMPT"
    FINANCE_DATA_ACCESS = "FINANCE_DATA_ACCESS"
    FINANCE_DATA_MUTATION = "FINANCE_DATA_MUTATION"
    ANALYST_REPORT_GENERATE = "ANALYST_REPORT_GENERATE"
    CONFIG_UPDATE = "CONFIG_UPDATE"


class AuditLog(db.Model):
    """Immutable security audit log model."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    username = db.Column(db.String(50), nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=False, default="unknown")
    action = db.Column(db.String(50), nullable=False, index=True)
    resource = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)  # Strictly sanitized, no passwords, keys or tokens

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "username": self.username or "Anonymous",
            "ip_address": self.ip_address,
            "action": self.action,
            "resource": self.resource,
            "status": self.status,
            "details": self.details,
        }

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action='{self.action}' status='{self.status}' user='{self.username}'>"
