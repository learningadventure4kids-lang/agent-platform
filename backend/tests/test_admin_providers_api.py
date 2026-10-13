import app.api.admin_providers as admin_providers_module
from app.ai.base import TestResult


def test_providers_require_admin_auth(client):
    assert client.get("/api/admin/providers").status_code == 401


def test_create_provider_and_key_never_returned(client, admin_headers):
    resp = client.post(
        "/api/admin/providers",
        json={
            "provider_type": "groq",
            "display_name": "Groq Test",
            "model_name": "llama-3.1-8b-instant",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": "sk-super-secret-value",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["api_key_configured"] is True
    assert "api_key" not in body
    assert "encrypted_api_key" not in body
    assert "sk-super-secret-value" not in resp.text


def test_list_providers_never_include_keys(client, admin_headers):
    client.post(
        "/api/admin/providers",
        json={
            "provider_type": "openai",
            "display_name": "OpenAI Test",
            "model_name": "gpt-4o-mini",
            "api_key": "sk-another-secret",
        },
        headers=admin_headers,
    )
    resp = client.get("/api/admin/providers", headers=admin_headers)
    assert resp.status_code == 200
    assert "sk-another-secret" not in resp.text


def test_ollama_provider_does_not_require_api_key(client, admin_headers):
    resp = client.post(
        "/api/admin/providers",
        json={
            "provider_type": "ollama",
            "display_name": "My Ollama",
            "model_name": "qwen3:8b",
            "base_url": "http://localhost:11434",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["api_key_configured"] is False


def test_update_provider_rotates_key(client, admin_headers):
    created = client.post(
        "/api/admin/providers",
        json={"provider_type": "groq", "display_name": "Rotate Test", "model_name": "m", "api_key": "sk-old"},
        headers=admin_headers,
    ).json()

    updated = client.put(
        f"/api/admin/providers/{created['id']}",
        json={"api_key": "sk-new"},
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["api_key_configured"] is True
    assert "sk-old" not in updated.text
    assert "sk-new" not in updated.text


def test_set_default_clears_other_defaults(client, admin_headers):
    a = client.post(
        "/api/admin/providers",
        json={"provider_type": "ollama", "display_name": "A", "model_name": "m", "is_default": True},
        headers=admin_headers,
    ).json()
    b = client.post(
        "/api/admin/providers",
        json={"provider_type": "ollama", "display_name": "B", "model_name": "m"},
        headers=admin_headers,
    ).json()

    client.post(f"/api/admin/providers/{b['id']}/set-default", headers=admin_headers)

    a_after = client.get(f"/api/admin/providers/{a['id']}", headers=admin_headers).json()
    b_after = client.get(f"/api/admin/providers/{b['id']}", headers=admin_headers).json()
    assert a_after["is_default"] is False
    assert b_after["is_default"] is True


def test_cannot_set_disabled_provider_as_default(client, admin_headers):
    p = client.post(
        "/api/admin/providers",
        json={"provider_type": "ollama", "display_name": "Disabled", "model_name": "m", "enabled": False},
        headers=admin_headers,
    ).json()
    resp = client.post(f"/api/admin/providers/{p['id']}/set-default", headers=admin_headers)
    assert resp.status_code == 400


def test_delete_provider_blocked_when_in_use(client, admin_headers, agent_tokens):
    provider = client.post(
        "/api/admin/providers",
        json={"provider_type": "ollama", "display_name": "In Use", "model_name": "m"},
        headers=admin_headers,
    ).json()
    agent_id = agent_tokens["kaur-jewellery"]["id"]
    client.put(f"/api/admin/agents/{agent_id}", json={"provider_id": provider["id"]}, headers=admin_headers)

    resp = client.delete(f"/api/admin/providers/{provider['id']}", headers=admin_headers)
    assert resp.status_code == 409

    # release it, then deletion should succeed
    client.put(f"/api/admin/agents/{agent_id}", json={"provider_id": None}, headers=admin_headers)
    resp2 = client.delete(f"/api/admin/providers/{provider['id']}", headers=admin_headers)
    assert resp2.status_code == 200


def test_provider_test_connection_endpoint(client, admin_headers, monkeypatch):
    p = client.post(
        "/api/admin/providers",
        json={"provider_type": "groq", "display_name": "Test Conn", "model_name": "m", "api_key": "sk-x"},
        headers=admin_headers,
    ).json()

    class FakeProvider:
        def test_connection(self):
            return TestResult(success=True, provider="groq", model="m", latency_ms=123)

    monkeypatch.setattr(admin_providers_module.AIProviderFactory, "create", lambda config: FakeProvider())

    resp = client.post(f"/api/admin/providers/{p['id']}/test", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["latency_ms"] == 123
    assert "sk-x" not in resp.text


def test_provider_test_connection_reports_failure_without_leaking_details(client, admin_headers, monkeypatch):
    p = client.post(
        "/api/admin/providers",
        json={"provider_type": "groq", "display_name": "Test Conn Fail", "model_name": "m", "api_key": "sk-y"},
        headers=admin_headers,
    ).json()

    class FakeProvider:
        def test_connection(self):
            return TestResult(
                success=False, provider="groq", error_code="INVALID_API_KEY",
                message="The provider rejected the API key.",
            )

    monkeypatch.setattr(admin_providers_module.AIProviderFactory, "create", lambda config: FakeProvider())

    resp = client.post(f"/api/admin/providers/{p['id']}/test", headers=admin_headers)
    body = resp.json()
    assert body["success"] is False
    assert body["error_code"] == "INVALID_API_KEY"
    assert "sk-y" not in resp.text


def test_model_discovery_when_supported(client, admin_headers, monkeypatch):
    p = client.post(
        "/api/admin/providers",
        json={"provider_type": "groq", "display_name": "Discover", "model_name": "m", "api_key": "sk-z"},
        headers=admin_headers,
    ).json()

    class FakeProvider:
        def list_models(self):
            return ["llama-3.1-8b-instant", "llama-3.1-70b-versatile"]

    monkeypatch.setattr(admin_providers_module.AIProviderFactory, "create", lambda config: FakeProvider())

    resp = client.get(f"/api/admin/providers/{p['id']}/models", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["supported"] is True
    assert "llama-3.1-8b-instant" in body["models"]


def test_model_discovery_when_not_supported(client, admin_headers, monkeypatch):
    p = client.post(
        "/api/admin/providers",
        json={"provider_type": "ollama", "display_name": "No Discovery", "model_name": "m"},
        headers=admin_headers,
    ).json()

    class FakeProvider:
        def list_models(self):
            return None

    monkeypatch.setattr(admin_providers_module.AIProviderFactory, "create", lambda config: FakeProvider())

    resp = client.get(f"/api/admin/providers/{p['id']}/models", headers=admin_headers)
    assert resp.json()["supported"] is False


def test_list_provider_types_includes_not_yet_implemented(client, admin_headers):
    resp = client.get("/api/admin/providers/types", headers=admin_headers)
    body = resp.json()
    assert "groq" in body["implemented"]
    assert "ollama" in body["implemented"]
    assert "anthropic" in body["all"]
    assert "anthropic" not in body["implemented"]
