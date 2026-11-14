import uuid
from datetime import datetime, timezone, timedelta
import jwt
from flask import current_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.token_blocklist import RevokedToken
from app.models.audit import AuditAction, AuditStatus
from app.services.audit_service import log_audit
from app.security.input_validator import (
    validate_username,
    validate_email,
    validate_password_strength,
)


def generate_jwt_token(user: User) -> dict:
    """Generate cryptographically signed JWT with jti and claims."""
    now = datetime.now(timezone.utc)
    expires_in = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", timedelta(hours=1))
    exp = now + expires_in
    jti = str(uuid.uuid4())

    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }

    secret = current_app.config["JWT_SECRET_KEY"]
    algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
    token = jwt.encode(payload, secret, algorithm=algorithm)

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in_seconds": int(expires_in.total_seconds()),
        "expires_at": exp.isoformat(),
        "jti": jti,
    }


def register_user(
    username: str,
    email: str,
    password: str,
    role: str = UserRole.USER,
    created_by_admin: bool = False
) -> dict:
    """Validate and register a new user account with secure defaults."""
    # Input validation
    valid_u, u_err = validate_username(username)
    if not valid_u:
        return {"success": False, "error": u_err, "status_code": 400}

    valid_e, e_err = validate_email(email)
    if not valid_e:
        return {"success": False, "error": e_err, "status_code": 400}

    valid_p, p_err = validate_password_strength(password)
    if not valid_p:
        return {"success": False, "error": p_err, "status_code": 400}

    # Only Admins can assign privileged roles (Admin, Financial Analyst)
    if role not in UserRole.ALL_ROLES:
        role = UserRole.USER
    elif role in [UserRole.ADMIN, UserRole.ANALYST] and not created_by_admin:
        # Default self-registered users to standard User role to prevent privilege escalation
        role = UserRole.USER

    # Check for uniqueness
    if User.query.filter_by(username=username).first():
        return {"success": False, "error": "Username is already registered.", "status_code": 409}

    if User.query.filter_by(email=email).first():
        return {"success": False, "error": "Email is already registered.", "status_code": 409}

    # Create user
    new_user = User(
        username=username.strip(),
        email=email.strip().lower(),
        role=role,
        is_active=True,
    )
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": "Database error while creating user.", "status_code": 500}

    log_audit(
        action=AuditAction.AUTH_REGISTER,
        resource="/api/v1/auth/register",
        status=AuditStatus.SUCCESS,
        user_id=new_user.id,
        username=new_user.username,
        details=f"User registered with role '{role}'"
    )

    return {"success": True, "user": new_user.to_dict(), "status_code": 201}


def authenticate_user(username_or_email: str, password: str) -> dict:
    """Authenticate credentials and issue JWT tokens."""
    if not username_or_email or not password:
        return {"success": False, "error": "Username/email and password are required.", "status_code": 400}

    user = User.query.filter(
        (User.username == username_or_email.strip()) | (User.email == username_or_email.strip().lower())
    ).first()

    if not user or not user.check_password(password):
        log_audit(
            action=AuditAction.AUTH_LOGIN_FAILED,
            resource="/api/v1/auth/login",
            status=AuditStatus.FAILED,
            username=username_or_email[:50],
            details="Invalid username or password supplied"
        )
        return {"success": False, "error": "Invalid credentials provided.", "status_code": 401}

    if not user.is_active:
        log_audit(
            action=AuditAction.AUTH_LOGIN_FAILED,
            resource="/api/v1/auth/login",
            status=AuditStatus.DENIED,
            user_id=user.id,
            username=user.username,
            details="Login attempted for deactivated account"
        )
        return {"success": False, "error": "Account is deactivated. Contact an administrator.", "status_code": 403}

    # Record last login
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    token_data = generate_jwt_token(user)

    log_audit(
        action=AuditAction.AUTH_LOGIN,
        resource="/api/v1/auth/login",
        status=AuditStatus.SUCCESS,
        user_id=user.id,
        username=user.username,
        details=f"Successful login for role '{user.role}'"
    )

    return {
        "success": True,
        "token_data": token_data,
        "user": user.to_dict(),
        "status_code": 200,
    }


def revoke_user_token(jti: str, user_id: int, exp_timestamp: int) -> bool:
    """Store token in revocation blocklist."""
    if not jti:
        return False

    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    revocation = RevokedToken(
        jti=jti,
        user_id=user_id,
        expires_at=expires_at,
    )

    try:
        db.session.add(revocation)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return False
