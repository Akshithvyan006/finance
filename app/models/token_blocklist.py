from datetime import datetime, timezone
from app.extensions import db

class RevokedToken(db.Model):
    """Stores revoked JWT unique identifiers (jti) for true logout and token invalidation."""
    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, nullable=True, index=True)
    revoked_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)

    @classmethod
    def is_token_revoked(cls, jti: str) -> bool:
        """Check if a JWT identifier has been revoked."""
        token = cls.query.filter_by(jti=jti).first()
        return token is not None

    def __repr__(self) -> str:
        return f"<RevokedToken jti='{self.jti}' user_id={self.user_id}>"
