import functools
import jwt
from flask import request, jsonify, g, current_app
from app.models.user import User, UserRole
from app.models.token_blocklist import RevokedToken
from app.models.audit import AuditLog, AuditAction, AuditStatus
from app.extensions import db


def get_token_from_request():
    """Extract token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()

    # Fallback to HttpOnly cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token.strip()

    return None


def jwt_required(optional=False):
    """Decorator to enforce and decode valid JWT tokens with revocation checks."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            token = get_token_from_request()

            if not token:
                if optional:
                    g.current_user = None
                    g.jwt_claims = None
                    return fn(*args, **kwargs)
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Authentication token is missing. Please log in."
                }), 401

            try:
                secret = current_app.config["JWT_SECRET_KEY"]
                algorithm = current_app.config.get("JWT_ALGORITHM", "HS256")
                payload = jwt.decode(token, secret, algorithms=[algorithm])

                jti = payload.get("jti")
                if jti and RevokedToken.is_token_revoked(jti):
                    return jsonify({
                        "error": "Unauthorized",
                        "message": "Token has been revoked. Please log in again."
                    }), 401

                raw_sub = payload.get("sub")
                user_id = int(raw_sub) if raw_sub is not None else None
                user = db.session.get(User, user_id) if user_id else None
                if not user or not user.is_active:
                    return jsonify({
                        "error": "Unauthorized",
                        "message": "User account is invalid or deactivated."
                    }), 401

                g.current_user = user
                g.jwt_claims = payload

            except jwt.ExpiredSignatureError:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Token has expired. Please re-authenticate."
                }), 401
            except jwt.InvalidTokenError as e:
                return jsonify({
                    "error": "Unauthorized",
                    "message": f"Invalid token: {str(e)}"
                }), 401
            except Exception as e:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Token verification failed."
                }), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def roles_required(*allowed_roles):
    """Decorator to enforce Role-Based Access Control (RBAC) on endpoints."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Authentication required before accessing this protected endpoint."
                }), 401

            if user.role not in allowed_roles:
                # Log security access violation
                try:
                    audit = AuditLog(
                        user_id=user.id,
                        username=user.username,
                        ip_address=request.remote_addr or "unknown",
                        action=AuditAction.ACCESS_CONTROL_VIOLATION,
                        resource=request.path,
                        status=AuditStatus.DENIED,
                        details=f"Role '{user.role}' attempted unauthorized access. Required: {list(allowed_roles)}"
                    )
                    db.session.add(audit)
                    db.session.commit()
                except Exception:
                    db.session.rollback()

                return jsonify({
                    "error": "Forbidden",
                    "message": f"Access denied. Role '{user.role}' lacks sufficient privileges for this resource.",
                    "required_roles": list(allowed_roles)
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def verify_ownership(resource_user_id: int):
    """Prevent Insecure Direct Object References (IDOR).
    Admins are permitted administrative override; others can only access own data.
    """
    user = getattr(g, "current_user", None)
    if not user:
        return False

    if user.id != resource_user_id and user.role != UserRole.ADMIN:
        # Record IDOR attempt in audit log
        try:
            audit = AuditLog(
                user_id=user.id,
                username=user.username,
                ip_address=request.remote_addr or "unknown",
                action=AuditAction.IDOR_ATTEMPT,
                resource=request.path,
                status=AuditStatus.DENIED,
                details=f"User {user.id} ({user.username}) attempted unauthorized access to resource belonging to user {resource_user_id}."
            )
            db.session.add(audit)
            db.session.commit()
        except Exception:
            db.session.rollback()

        return False

    return True
