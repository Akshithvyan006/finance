import pytest
from app import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.finance import UserBudget, UserSavingsGoal, UserLoanScenario
from app.services.auth_service import generate_jwt_token
from app.services.analyst_service import seed_analyst_datasets_if_needed


@pytest.fixture(scope="session")
def app():
    """Create and configure a testing Flask application."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        yield test_app
        db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Test HTTP client with clean database tables for each test."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_analyst_datasets_if_needed()

        # Seed standard users
        admin = User(username="admin_test", email="admin@test.local", role=UserRole.ADMIN, is_active=True)
        admin.set_password("AdminSecurePass!123")

        analyst = User(username="analyst_test", email="analyst@test.local", role=UserRole.ANALYST, is_active=True)
        analyst.set_password("AnalystSecurePass!123")

        user1 = User(username="user1_test", email="user1@test.local", role=UserRole.USER, is_active=True)
        user1.set_password("User1SecurePass!123")

        user2 = User(username="user2_test", email="user2@test.local", role=UserRole.USER, is_active=True)
        user2.set_password("User2SecurePass!123")

        db.session.add_all([admin, analyst, user1, user2])
        db.session.commit()

        # Seed a budget for user1 to test IDOR
        b1 = UserBudget(user_id=user1.id, monthly_income=4000.0, needs_amount=2000.0, wants_amount=1200.0, savings_amount=800.0)
        db.session.add(b1)
        db.session.commit()

        test_app_client = app.test_client()
        yield test_app_client


@pytest.fixture
def admin_token(app, client):
    with app.app_context():
        admin = User.query.filter_by(username="admin_test").first()
        return generate_jwt_token(admin)["access_token"]


@pytest.fixture
def analyst_token(app, client):
    with app.app_context():
        analyst = User.query.filter_by(username="analyst_test").first()
        return generate_jwt_token(analyst)["access_token"]


@pytest.fixture
def user1_token(app, client):
    with app.app_context():
        user1 = User.query.filter_by(username="user1_test").first()
        return generate_jwt_token(user1)["access_token"]


@pytest.fixture
def user2_token(app, client):
    with app.app_context():
        user2 = User.query.filter_by(username="user2_test").first()
        return generate_jwt_token(user2)["access_token"]
