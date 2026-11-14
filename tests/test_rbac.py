import pytest

def test_admin_can_access_admin_endpoints(client, admin_token):
    """Test Admin has access to administrative endpoints."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Access user list
    res = client.get("/api/v1/admin/users", headers=headers)
    assert res.status_code == 200
    assert "users" in res.get_json()

    # Access audit logs
    res_audit = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 200
    assert "audit_logs" in res_audit.get_json()

    # Access system stats
    res_stats = client.get("/api/v1/admin/system-stats", headers=headers)
    assert res_stats.status_code == 200
    assert "security" in res_stats.get_json()


def test_user_cannot_access_admin_endpoints(client, user1_token):
    """Test standard User is denied access to Admin endpoints (HTTP 403 Forbidden)."""
    headers = {"Authorization": f"Bearer {user1_token}"}

    res_users = client.get("/api/v1/admin/users", headers=headers)
    assert res_users.status_code == 403
    assert "Access denied" in res_users.get_json()["message"]

    res_audit = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 403

    res_stats = client.get("/api/v1/admin/system-stats", headers=headers)
    assert res_stats.status_code == 403


def test_analyst_cannot_access_admin_endpoints(client, analyst_token):
    """Test Financial Analyst is denied access to Admin user management (HTTP 403 Forbidden)."""
    headers = {"Authorization": f"Bearer {analyst_token}"}

    res = client.get("/api/v1/admin/users", headers=headers)
    assert res.status_code == 403

    res_audit = client.get("/api/v1/admin/audit-logs", headers=headers)
    assert res_audit.status_code == 403


def test_analyst_can_access_analysis_features(client, analyst_token):
    """Test Financial Analyst can access authorized datasets and risk tools."""
    headers = {"Authorization": f"Bearer {analyst_token}"}

    # Get datasets
    res = client.get("/api/v1/analyst/datasets", headers=headers)
    assert res.status_code == 200
    assert "authorized_datasets" in res.get_json()

    # Run stress test
    res_stress = client.post("/api/v1/analyst/stress-test", headers=headers, json={
        "equity_pct": 50,
        "bond_pct": 40,
        "cash_pct": 10
    })
    assert res_stress.status_code == 200
    assert "simulated_impact" in res_stress.get_json()


def test_user_cannot_access_analyst_datasets(client, user1_token):
    """Test standard User cannot access Financial Analyst tools (HTTP 403 Forbidden)."""
    headers = {"Authorization": f"Bearer {user1_token}"}

    res = client.get("/api/v1/analyst/datasets", headers=headers)
    assert res.status_code == 403

    res_stress = client.post("/api/v1/analyst/stress-test", headers=headers, json={
        "equity_pct": 60,
        "bond_pct": 30,
        "cash_pct": 10
    })
    assert res_stress.status_code == 403


def test_admin_can_change_user_role(client, admin_token):
    """Test Admin can assign and modify user roles."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Fetch user list to get target user ID
    users = client.get("/api/v1/admin/users", headers=headers).get_json()["users"]
    user1 = next(u for u in users if u["username"] == "user1_test")

    # Promote to Financial Analyst
    res = client.put(f"/api/v1/admin/users/{user1['id']}/role", headers=headers, json={
        "role": "Financial Analyst"
    })
    assert res.status_code == 200
    assert res.get_json()["user"]["role"] == "Financial Analyst"


def test_admin_cannot_self_demote(client, admin_token):
    """Test Admin cannot revoke their own admin role (prevents administrative lockout)."""
    headers = {"Authorization": f"Bearer {admin_token}"}

    users = client.get("/api/v1/admin/users", headers=headers).get_json()["users"]
    admin = next(u for u in users if u["username"] == "admin_test")

    res = client.put(f"/api/v1/admin/users/{admin['id']}/role", headers=headers, json={
        "role": "User"
    })
    assert res.status_code == 400
    assert "Self-demotion prohibited" in res.get_json()["error"]
