import os
from flask import Flask, render_template, jsonify
from app.config import config_by_name
from app.extensions import db, limiter
from app.routes import (
    auth_bp,
    chatbot_bp,
    calculator_bp,
    user_bp,
    analyst_bp,
    admin_bp,
)


def create_app(config_name=None):
    """Application factory for the Secure Financial Analysis Chatbot."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    # Initialize extensions
    db.init_app(app)
    limiter.init_app(app)

    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(calculator_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(analyst_bp)
    app.register_blueprint(admin_bp)

    # Single-page web app entrypoint
    @app.route("/")
    def index():
        return render_template("index.html")

    # Health check endpoint
    @app.route("/api/v1/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "Secure Financial Analysis Chatbot",
            "environment": config_name,
            "rbac_enabled": True,
        }), 200

    # -------------------------------------------------------------
    # Cybersecurity: Defensive HTTP Response Headers
    # -------------------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Prevent reflected XSS in legacy browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Restrict referrer leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Disable risky hardware permissions
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # Strict Content Security Policy (allows local assets, Google Fonts, and Chart.js CDN)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response

    # -------------------------------------------------------------
    # Centralized Error Handlers (No traceback leakage)
    # -------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad Request", "message": "Malformed request syntax or validation error."}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden", "message": "Insufficient permissions to access this resource."}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not Found", "message": "Requested endpoint does not exist."}), 404

    @app.errorhandler(429)
    def ratelimit_handler(error):
        return jsonify({
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please wait before making further requests.",
            "retry_after": error.description if hasattr(error, "description") else "60 seconds"
        }), 429

    @app.errorhandler(500)
    def internal_server_error(error):
        # Log securely on server; return sanitized generic message to client to prevent information disclosure
        app.logger.error(f"Internal server error: {error}")
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. The incident has been logged for security review."
        }), 500

    return app
