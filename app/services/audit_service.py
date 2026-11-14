from flask import request
from app.extensions import db
from app.models.audit import AuditLog, AuditAction, AuditStatus
from app.security.input_validator import sanitize_text

def log_audit(
    action: str,
    resource: str,
    status: str = AuditStatus.SUCCESS,
    user_id: int = None,
    username: str = None,
    details: str = None,
    ip_address: str = None,
) -> AuditLog:
    """Safely record an immutable security audit log entry.
    All inputs are sanitized; sensitive information (passwords, tokens) must never be passed here.
    """
    if not ip_address:
        try:
            ip_address = request.remote_addr or "127.0.0.1"
        except RuntimeError:
            ip_address = "system"

    # Sanitize details to avoid injection or overly verbose output
    safe_details = sanitize_text(details, max_length=500) if details else None

    audit_entry = AuditLog(
        user_id=user_id,
        username=username[:50] if username else None,
        ip_address=ip_address[:45],
        action=action[:50],
        resource=resource[:150],
        status=status[:20],
        details=safe_details,
    )

    try:
        db.session.add(audit_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Fail open for logging in test or print error, avoid crashing entire app
        print(f"[AUDIT LOG ERROR] Failed to record audit log: {e}")

    return audit_entry
