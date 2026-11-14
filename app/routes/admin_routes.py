from flask import Blueprint, request, jsonify, g, current_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.audit import AuditLog, AuditAction, AuditStatus
from app.services.audit_service import log_audit
from app.security.decorators import jwt_required, roles_required
from app.security.input_validator import sanitize_text

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")


@admin_bp.route("/users", methods=["GET"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def list_users():
    """List all registered users with their roles and status."""
    users = User.query.order_by(User.id.asc()).all()
    return jsonify({
        "users": [u.to_dict() for u in users],
        "total": len(users)
    }), 200


@admin_bp.route("/users/<int:user_id>/role", methods=["PUT"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def update_user_role(user_id: int):
    """Assign or modify user role (Protected against self-demotion)."""
    target_user = db.session.get(User, user_id)
    if not target_user:
        return jsonify({"error": "User not found."}), 404

    data = request.get_json(silent=True) or {}
    new_role = data.get("role")

    if new_role not in UserRole.ALL_ROLES:
        return jsonify({
            "error": f"Invalid role '{new_role}'. Allowed roles: {UserRole.ALL_ROLES}"
        }), 400

    # Prevent Admin from self-demoting to avoid administrative lockout
    if target_user.id == g.current_user.id and new_role != UserRole.ADMIN:
        return jsonify({
            "error": "Self-demotion prohibited. An administrator cannot revoke their own admin role."
        }), 400

    old_role = target_user.role
    target_user.role = new_role
    db.session.commit()

    log_audit(
        action=AuditAction.USER_ROLE_CHANGE,
        resource=f"/api/v1/admin/users/{user_id}/role",
        status=AuditStatus.SUCCESS,
        user_id=g.current_user.id,
        username=g.current_user.username,
        details=f"Changed role for user '{target_user.username}' (ID {target_user.id}) from '{old_role}' to '{new_role}'"
    )

    return jsonify({
        "message": f"Role for user '{target_user.username}' updated to '{new_role}'.",
        "user": target_user.to_dict()
    }), 200


@admin_bp.route("/users/<int:user_id>/status", methods=["PUT"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def toggle_user_status(user_id: int):
    """Activate or deactivate user account (Cannot deactivate own account)."""
    target_user = db.session.get(User, user_id)
    if not target_user:
        return jsonify({"error": "User not found."}), 404

    if target_user.id == g.current_user.id:
        return jsonify({"error": "Self-deactivation prohibited."}), 400

    data = request.get_json(silent=True) or {}
    is_active = data.get("is_active")
    if is_active is None or not isinstance(is_active, bool):
        return jsonify({"error": "Field 'is_active' must be a boolean (true/false)."}), 400

    target_user.is_active = is_active
    db.session.commit()

    status_str = "activated" if is_active else "deactivated"
    log_audit(
        action=AuditAction.USER_STATUS_CHANGE,
        resource=f"/api/v1/admin/users/{user_id}/status",
        status=AuditStatus.SUCCESS,
        user_id=g.current_user.id,
        username=g.current_user.username,
        details=f"User '{target_user.username}' {status_str}"
    )

    return jsonify({
        "message": f"User '{target_user.username}' has been {status_str}.",
        "user": target_user.to_dict()
    }), 200


@admin_bp.route("/audit-logs", methods=["GET"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def get_audit_logs():
    """Retrieve security audit logs with filtering and pagination."""
    action = request.args.get("action")
    status = request.args.get("status")
    username = request.args.get("username")
    limit = min(int(request.args.get("limit", 100)), 500)
    offset = int(request.args.get("offset", 0))

    query = AuditLog.query

    if action:
        query = query.filter_by(action=action)
    if status:
        query = query.filter_by(status=status)
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))

    total = query.count()
    logs = query.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()

    return jsonify({
        "audit_logs": [log.to_dict() for log in logs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@admin_bp.route("/system-stats", methods=["GET"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def system_stats():
    """Administrative dashboard metrics and health check."""
    total_users = User.query.count()
    admin_count = User.query.filter_by(role=UserRole.ADMIN).count()
    analyst_count = User.query.filter_by(role=UserRole.ANALYST).count()
    user_count = User.query.filter_by(role=UserRole.USER).count()
    deactivated_count = User.query.filter_by(is_active=False).count()

    total_audits = AuditLog.query.count()
    failed_logins = AuditLog.query.filter_by(action=AuditAction.AUTH_LOGIN_FAILED).count()
    security_violations = AuditLog.query.filter(
        (AuditLog.action == AuditAction.ACCESS_CONTROL_VIOLATION) |
        (AuditLog.action == AuditAction.CHATBOT_PROMPT_INJECTION_DETECTED) |
        (AuditLog.action == AuditAction.IDOR_ATTEMPT)
    ).count()

    recent_security_events = AuditLog.query.filter(
        (AuditLog.status.in_([AuditStatus.DENIED, AuditStatus.WARNING, AuditStatus.FAILED]))
    ).order_by(AuditLog.id.desc()).limit(10).all()

    return jsonify({
        "users": {
            "total": total_users,
            "admins": admin_count,
            "analysts": analyst_count,
            "standard_users": user_count,
            "deactivated": deactivated_count,
        },
        "security": {
            "total_audit_events": total_audits,
            "failed_logins_recorded": failed_logins,
            "security_violations_flagged": security_violations,
            "strict_prompt_guard_active": current_app.config.get("ENABLE_STRICT_PROMPT_GUARD", True),
        },
        "recent_alerts": [ev.to_dict() for ev in recent_security_events]
    }), 200


@admin_bp.route("/config", methods=["POST"])
@jwt_required()
@roles_required(UserRole.ADMIN)
def update_config():
    """Configure runtime application security options."""
    data = request.get_json(silent=True) or {}

    if "enable_strict_prompt_guard" in data:
        val = bool(data["enable_strict_prompt_guard"])
        current_app.config["ENABLE_STRICT_PROMPT_GUARD"] = val

        log_audit(
            action=AuditAction.CONFIG_UPDATE,
            resource="/api/v1/admin/config",
            status=AuditStatus.SUCCESS,
            user_id=g.current_user.id,
            username=g.current_user.username,
            details=f"Set enable_strict_prompt_guard={val}"
        )

    return jsonify({
        "message": "Configuration updated successfully.",
        "current_config": {
            "enable_strict_prompt_guard": current_app.config.get("ENABLE_STRICT_PROMPT_GUARD", True),
            "max_chat_input_length": current_app.config.get("MAX_CHAT_INPUT_LENGTH", 500),
        }
    }), 200
