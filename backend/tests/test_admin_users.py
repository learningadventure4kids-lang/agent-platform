"""Platform-operator management of customer plans (app/api/admin_users.py).
No payment processor exists yet, so this is the only way a customer moves
off the free tier today."""
from __future__ import annotations

from app.billing.plans import PLAN_FREE, PLAN_PLUS

ADMIN_HEADERS = {"X-Admin-Key": "test-admin-secret"}


def _signup(client, email="admin-users-test@example.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "correct horse battery staple", "name": "Founder"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_admin_users_requires_platform_admin_key(client):
    assert client.get("/api/admin/users").status_code == 401
    assert client.patch("/api/admin/users/1/plan", json={"plan": PLAN_PLUS}).status_code == 401


def test_a_customer_session_cannot_reach_admin_users(client):
    auth = _signup(client, email="not-an-admin@example.com")
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {auth['session_token']}"})
    assert resp.status_code == 401


def test_admin_can_list_users_and_upgrade_a_plan(client):
    auth = _signup(client, email="upgrade-me@example.com")
    user_id = auth["user"]["id"]
    assert auth["user"]["plan"] == PLAN_FREE

    listed = client.get("/api/admin/users", headers=ADMIN_HEADERS)
    assert listed.status_code == 200
    row = next(u for u in listed.json() if u["id"] == user_id)
    assert row["plan"] == PLAN_FREE

    upgraded = client.patch(
        f"/api/admin/users/{user_id}/plan", json={"plan": PLAN_PLUS}, headers=ADMIN_HEADERS
    )
    assert upgraded.status_code == 200
    assert upgraded.json()["plan"] == PLAN_PLUS

    # The user's own session reflects it immediately -- not cached anywhere.
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth['session_token']}"})
    assert me.json()["plan"] == PLAN_PLUS


def test_admin_rejects_an_unknown_plan_name(client):
    auth = _signup(client, email="bad-plan@example.com")
    resp = client.patch(
        f"/api/admin/users/{auth['user']['id']}/plan",
        json={"plan": "ultra-mega-plan"},
        headers=ADMIN_HEADERS,
    )
    assert resp.status_code == 400


def test_admin_update_plan_404s_for_unknown_user(client):
    resp = client.patch("/api/admin/users/999999/plan", json={"plan": PLAN_PLUS}, headers=ADMIN_HEADERS)
    assert resp.status_code == 404
