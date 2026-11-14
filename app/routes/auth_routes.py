from flask import Blueprint, request, jsonify, g
from app.services.auth_service import register_user, authenticate_user, revoke_user_token
from app.services.audit_service import log_audit
from app.models.audit import AuditAction, AuditStatus
from app.security.decorators import jwt_required
from app.extensions import limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("15 per minute")
def register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    email = data.get("email", "")
    password = data.get("password", "")
    role = data.get("role", "User")

    result = register_user(
        username=username,
        email=email,
        password=password,
        role=role,
        created_by_admin=False
    )

    if not result["success"]:
        return jsonify({"error": result["error"]}), result["status_code"]

    return jsonify({
        "message": "User registered successfully.",
        "user": result["user"]
    }), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("15 per minute")
def login():
    """Authenticate credentials and return JWT access token."""
    data = request.get_json(silent=True) or {}
    username_or_email = data.get("username_or_email", "")
    password = data.get("password", "")

    result = authenticate_user(username_or_email, password)

    if not result["success"]:
        return jsonify({"error": result["error"]}), result["status_code"]

    response = jsonify({
        "message": "Login successful.",
        "token": result["token_data"]["access_token"],
        "token_data": result["token_data"],
        "user": result["user"],
    })

    # Also set secure HttpOnly cookie for defense-in-depth
    response.set_cookie(
        "access_token",
        result["token_data"]["access_token"],
        max_age=result["token_data"]["expires_in_seconds"],
        httponly=True,
        samesite="Lax",
        secure=False  # Switch to True in production HTTPS
    )

    return response, 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Revoke JWT and clear session cookie."""
    claims = getattr(g, "jwt_claims", {})
    user = getattr(g, "current_user", None)
    jti = claims.get("jti")
    exp = claims.get("exp", 0)

    if jti:
        revoke_user_token(jti, user.id if user else None, exp)

    if user:
        log_audit(
            action=AuditAction.AUTH_LOGOUT,
            resource="/api/v1/auth/logout",
            status=AuditStatus.SUCCESS,
            user_id=user.id,
            username=user.username,
            details="User logged out and token invalidated"
        )

    response = jsonify({"message": "Successfully logged out. Token has been revoked."})
    response.delete_cookie("access_token")
    return response, 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return currently authenticated user profile and permissions."""
    user = g.current_user
    return jsonify({
        "user": user.to_dict(),
        "permissions": {
            "is_admin": user.role == "Admin",
            "is_analyst": user.role in ["Financial Analyst", "Admin"],
            "can_manage_users": user.role == "Admin",
            "can_view_audit_logs": user.role == "Admin",
            "can_access_analyst_tools": user.role in ["Financial Analyst", "Admin"],
            "can_use_calculators": True,
            "can_use_chatbot": True,
        }
    }), 200
