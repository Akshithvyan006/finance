from app.routes.auth_routes import auth_bp
from app.routes.chatbot_routes import chatbot_bp
from app.routes.calculator_routes import calculator_bp
from app.routes.user_routes import user_bp
from app.routes.analyst_routes import analyst_bp
from app.routes.admin_routes import admin_bp

__all__ = [
    "auth_bp",
    "chatbot_bp",
    "calculator_bp",
    "user_bp",
    "analyst_bp",
    "admin_bp",
]
