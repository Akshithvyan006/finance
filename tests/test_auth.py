import json
import pytest

def test_login_success(client):
    """Test successful login returns valid JWT token and correct user metadata."""
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "user1_test",
        "password": "User1SecurePass!123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert "token" in data
    assert data["user"]["username"] == "user1_test"
    assert data["user"]["role"] == "User"
    assert "password_hash" not in data["user"]


def test_login_failed_invalid_password(client):
    """Test login fails with incorrect password."""
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "user1_test",
        "password": "WrongPassword!999"
    })
    assert res.status_code == 401
    data = res.get_json()
    assert "error" in data


def test_login_failed_nonexistent_user(client):
    """Test login fails when username does not exist."""
    res = client.post("/api/v1/auth/login", json={
        "username_or_email": "ghost_user",
        "password": "SomePassword!123"
    })
    assert res.status_code == 401


def test_password_strength_validation(client):
    """Test NIST password strength policy rejects weak passwords during registration."""
    # Too short (< 10 chars)
    res = client.post("/api/v1/auth/register", json={
        "username": "new_user_1",
        "email": "new1@test.local",
        "password": "Short!1"
    })
    assert res.status_code == 400
    assert "at least 10 characters" in res.get_json()["error"]

    # Missing special character
    res = client.post("/api/v1/auth/register", json={
        "username": "new_user_2",
        "email": "new2@test.local",
        "password": "NoSpecialCharacter123"
    })
    assert res.status_code == 400
    assert "special character" in res.get_json()["error"]


def test_registration_privilege_escalation_defense(client):
    """Test public self-registration cannot elevate role to Admin or Financial Analyst."""
    res = client.post("/api/v1/auth/register", json={
        "username": "sneaky_admin_attempt",
        "email": "sneaky@test.local",
        "password": "ValidStrongPassword!2026",
        "role": "Admin"  # Attempt to self-register as Admin
    })
    assert res.status_code == 201
    data = res.get_json()
    # Backend must force role to User
    assert data["user"]["role"] == "User"


def test_logout_and_token_revocation(client, user1_token):
    """Test that after logout, the token is revoked and cannot access protected endpoints."""
    # Check token works first
    headers = {"Authorization": f"Bearer {user1_token}"}
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Attempt to reuse revoked token
    res_after = client.get("/api/v1/auth/me", headers=headers)
    assert res_after.status_code == 401
    assert "revoked" in res_after.get_json()["message"]
