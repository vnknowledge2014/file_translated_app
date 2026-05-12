"""Integration Tests — Admin Dashboard Routes with RBAC.

Tests:
- Only superadmin can access admin routes (RBAC enforcement)
- Platform stats, user management, job monitor, billing analytics, system health
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


# ── Test constants ──

SUPERADMIN_USER = {
    "id": "user:admin_001",
    "username": "superadmin",
    "wallet_address": "SUPERADMIN_WALLET_ADDRESS",
    "role": "superadmin",
    "is_active": True,
}

REGULAR_USER = {
    "id": "user:regular_001",
    "username": "alice",
    "wallet_address": "ALICE_WALLET_ADDRESS",
    "role": "user",
    "is_active": True,
}


def _create_admin_test_app():
    """Create test app with admin routes."""
    from app.routes.admin import router as admin_router
    from app.routes.auth import router as auth_router

    test_app = FastAPI()
    test_app.include_router(auth_router, tags=["Auth"])
    test_app.include_router(admin_router, tags=["Admin"])
    return test_app


@pytest.fixture
def admin_app_and_client():
    """Test app + client with admin routing."""
    import app.database as db_mod

    mock_db = MagicMock()

    async def mock_query(query_str, params=None):
        if params is None:
            params = {}
        # User lookup for JWT
        if "FROM user WHERE username" in query_str:
            username = params.get("username", "")
            if username == "superadmin":
                return [{"result": [SUPERADMIN_USER]}]
            elif username == "alice":
                return [{"result": [REGULAR_USER]}]
            return [{"result": []}]
        # Count queries
        if "count()" in query_str.lower() and "GROUP ALL" in query_str:
            return [{"result": [{"count": 42}]}]
        # Generic list
        if "FROM user" in query_str:
            return [{"result": [SUPERADMIN_USER, REGULAR_USER]}]
        if "FROM jobs" in query_str:
            return [{"result": []}]
        if "FROM payment" in query_str:
            return [{"result": []}]
        if "FROM api_key" in query_str:
            return [{"result": []}]
        if "math::sum" in query_str:
            return [{"result": [{"total": 1250}]}]
        if "INFO FOR DB" in query_str:
            return [{"result": {}}]
        # Update queries (user edit, disable)
        if "UPDATE" in query_str:
            return [{"result": []}]
        if "DELETE" in query_str:
            return [{"result": []}]
        return [{"result": []}]

    mock_db.query = AsyncMock(side_effect=mock_query)
    mock_db.select = AsyncMock(return_value=None)
    mock_db.delete = AsyncMock()
    mock_db.create = AsyncMock(return_value=[{}])
    mock_db.merge = AsyncMock()

    with (
        patch.object(db_mod, "db", mock_db),
        patch("app.auth.SUPERADMIN_WALLET", "SUPERADMIN_WALLET_ADDRESS"),
        patch(
            "app.routes.admin._get_storage_stats",
            return_value={"uploads_bytes": 0, "outputs_bytes": 0, "total_bytes": 0},
        ),
    ):
        test_app = _create_admin_test_app()
        client = TestClient(test_app, raise_server_exceptions=False)
        yield test_app, client, mock_db


@pytest.fixture
def superadmin_headers():
    from app.auth import create_access_token
    from datetime import timedelta

    token = create_access_token(
        data={"sub": "superadmin"}, expires_delta=timedelta(hours=1)
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def regular_headers():
    from app.auth import create_access_token
    from datetime import timedelta

    token = create_access_token(data={"sub": "alice"}, expires_delta=timedelta(hours=1))
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════
#  RBAC Enforcement
# ══════════════════════════════════════════════════════


class TestAdminRBAC:
    """Only superadmin can access admin routes."""

    def test_unauthenticated_denied(self, admin_app_and_client):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/stats")
        assert resp.status_code in (401, 403)

    def test_regular_user_denied(self, admin_app_and_client, regular_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/stats", headers=regular_headers)
        assert resp.status_code == 403
        assert "Insufficient role" in resp.json()["detail"]

    def test_superadmin_allowed(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/stats", headers=superadmin_headers)
        assert resp.status_code == 200

    def test_regular_user_denied_users(self, admin_app_and_client, regular_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/users", headers=regular_headers)
        assert resp.status_code == 403

    def test_regular_user_denied_jobs(self, admin_app_and_client, regular_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/jobs", headers=regular_headers)
        assert resp.status_code == 403

    def test_regular_user_denied_system(self, admin_app_and_client, regular_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/system/config", headers=regular_headers)
        assert resp.status_code == 403

    def test_regular_user_denied_billing(self, admin_app_and_client, regular_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/billing/revenue", headers=regular_headers)
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════
#  Platform Stats
# ══════════════════════════════════════════════════════


class TestAdminStats:
    """Admin stats endpoint returns structured platform data."""

    def test_stats_structure(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/stats", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "jobs" in data
        assert "revenue" in data
        assert "storage" in data
        assert "recent_jobs" in data

    def test_stats_users_section(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        data = client.get("/api/admin/stats", headers=superadmin_headers).json()
        assert "total" in data["users"]
        assert "active" in data["users"]

    def test_stats_revenue_section(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        data = client.get("/api/admin/stats", headers=superadmin_headers).json()
        assert "total_usdc" in data["revenue"]
        assert "this_month_usdc" in data["revenue"]


# ══════════════════════════════════════════════════════
#  User Management
# ══════════════════════════════════════════════════════


class TestAdminUserManagement:
    """Admin user CRUD operations."""

    def test_list_all_users(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/users", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data

    def test_list_users_pagination(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/users?page=1&limit=5", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["limit"] == 5

    def test_list_users_search(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/users?search=alice", headers=superadmin_headers)
        assert resp.status_code == 200

    def test_list_users_filter_by_plan(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/users?plan=pro", headers=superadmin_headers)
        assert resp.status_code == 200

    def test_update_user_role(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.put(
            "/api/admin/users/admin_001",
            headers=superadmin_headers,
            json={"role": "admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "role" in data.get("updated_fields", [])

    def test_update_user_plan(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.put(
            "/api/admin/users/admin_001",
            headers=superadmin_headers,
            json={"plan": "pro"},
        )
        assert resp.status_code == 200

    def test_update_user_invalid_role(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.put(
            "/api/admin/users/admin_001",
            headers=superadmin_headers,
            json={"role": "godmode"},
        )
        assert resp.status_code == 400

    def test_update_user_no_fields(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.put(
            "/api/admin/users/admin_001",
            headers=superadmin_headers,
            json={},
        )
        assert resp.status_code == 400

    def test_disable_user(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.post(
            "/api/admin/users/regular_001/disable",
            headers=superadmin_headers,
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert "disabled" in resp.json()["message"]

    def test_enable_user(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.post(
            "/api/admin/users/regular_001/disable",
            headers=superadmin_headers,
            json={"is_active": True},
        )
        assert resp.status_code == 200
        assert "enabled" in resp.json()["message"]


# ══════════════════════════════════════════════════════
#  Job Monitor
# ══════════════════════════════════════════════════════


class TestAdminJobMonitor:
    """Admin job monitoring operations."""

    def test_list_all_jobs(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/jobs", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data
        assert "total" in data

    def test_list_jobs_filter_status(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get(
            "/api/admin/jobs?status=completed", headers=superadmin_headers
        )
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════
#  Billing
# ══════════════════════════════════════════════════════


class TestAdminBilling:
    """Admin revenue analytics."""

    def test_revenue_analytics(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/billing/revenue", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_usdc" in data
        assert "period" in data

    def test_revenue_analytics_period(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get(
            "/api/admin/billing/revenue?period=7d", headers=superadmin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["period"] == "7d"

    def test_all_payments_list(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/billing/payments", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "payments" in data
        assert "total" in data


# ══════════════════════════════════════════════════════
#  System Health & Config
# ══════════════════════════════════════════════════════


class TestAdminSystem:
    """Admin system health and config."""

    def test_get_platform_config(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.get("/api/admin/system/config", headers=superadmin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "llm" in data
        assert "translation" in data
        assert "security" in data

    def test_update_config(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.put(
            "/api/admin/system/config",
            headers=superadmin_headers,
            json={"registration_enabled": False},
        )
        assert resp.status_code == 200
        assert "changes" in resp.json()

    def test_update_config_no_changes(self, admin_app_and_client, superadmin_headers):
        _, client, _ = admin_app_and_client
        resp = client.put(
            "/api/admin/system/config",
            headers=superadmin_headers,
            json={},
        )
        assert resp.status_code == 400

    def test_update_config_invalid_workers(
        self, admin_app_and_client, superadmin_headers
    ):
        _, client, _ = admin_app_and_client
        resp = client.put(
            "/api/admin/system/config",
            headers=superadmin_headers,
            json={"max_workers": 0},
        )
        assert resp.status_code == 400
