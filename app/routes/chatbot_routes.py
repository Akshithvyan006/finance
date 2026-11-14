from flask import Blueprint, request, jsonify, g
from app.services.chatbot_service import process_chat_query, SUGGESTED_PROMPTS
from app.services.audit_service import log_audit
from app.models.audit import AuditAction, AuditStatus
from app.security.decorators import jwt_required
from app.extensions import limiter

chatbot_bp = Blueprint("chatbot", __name__, url_prefix="/api/v1/chatbot")


@chatbot_bp.route("/message", methods=["POST"])
@jwt_required()
@limiter.limit("45 per minute")
def send_message():
    """Send an interactive financial inquiry to the chatbot."""
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "")

    result = process_chat_query(prompt)

    user = g.current_user

    # If prompt injection detected, log high-priority security event
    if result.get("is_security_violation"):
        log_audit(
            action=AuditAction.CHATBOT_PROMPT_INJECTION_DETECTED,
            resource="/api/v1/chatbot/message",
            status=AuditStatus.WARNING,
            user_id=user.id,
            username=user.username,
            details=f"Prompt injection attempt detected: {result.get('violation_reason')}"
        )
        return jsonify(result), 400

    return jsonify(result), 200


@chatbot_bp.route("/suggested-prompts", methods=["GET"])
def suggested_prompts():
    """Retrieve sample educational prompts for interactive chatbot."""
    return jsonify({
        "suggested_prompts": SUGGESTED_PROMPTS,
        "categories": [
            "Savings & Emergency Reserves",
            "50/30/20 Budgeting Rule",
            "Debt Snowball vs Avalanche",
            "Inflation Purchasing Power Impact",
            "Index Funds & Diversification"
        ]
    }), 200
