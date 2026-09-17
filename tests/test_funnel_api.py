"""Tests for the protected Funnel Architect API endpoint."""

from fastapi.testclient import TestClient

import forage.infra.dashboard as dashboard


VALID_KEY = "test-funnel-api-key"


def _client(config, monkeypatch):
    dashboard._config = config
    monkeypatch.setenv("FORAGE_API_KEY", VALID_KEY)
    return TestClient(dashboard.app)


def test_funnel_analyze_rejects_missing_api_key(config, monkeypatch):
    client = _client(config, monkeypatch)

    response = client.post(
        "/api/funnel/analyze",
        json={"description": "Welcome -> offer -> checkout"},
    )

    assert response.status_code == 401


def test_funnel_analyze_rejects_wrong_api_key(config, monkeypatch):
    client = _client(config, monkeypatch)

    response = client.post(
        "/api/funnel/analyze",
        headers={"X-API-Key": "wrong-key"},
        json={"description": "Welcome -> offer -> checkout"},
    )

    assert response.status_code == 401


def test_funnel_analyze_returns_flowspec(config, monkeypatch):
    client = _client(config, monkeypatch)
    config.capabilities.funnel_architect = True

    expected_flowspec = {
        "name": "Example Funnel",
        "objective": "Convert qualified leads",
        "nodes": [],
        "connections": [],
        "conditions": [],
        "delays": [],
        "tags": [],
        "metrics": [],
        "integrations": [],
    }

    def fake_execute(description):
        assert description == "Welcome -> offer -> checkout"
        return {
            "success": True,
            "cost": 0.0001,
            "revenue": 0,
            "description": "FlowSpec criado pelo Funnel Architect.",
            "artifacts": {"flowspec": expected_flowspec},
        }

    monkeypatch.setattr(dashboard, "_execute_funnel_architect", fake_execute)

    response = client.post(
        "/api/funnel/analyze",
        headers={"X-API-Key": VALID_KEY},
        json={"description": "Welcome -> offer -> checkout"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["cost"] == 0.0001
    assert body["flowspec"] == expected_flowspec


def test_funnel_analyze_requires_enabled_capability(config, monkeypatch):
    client = _client(config, monkeypatch)
    config.capabilities.funnel_architect = False

    response = client.post(
        "/api/funnel/analyze",
        headers={"X-API-Key": VALID_KEY},
        json={"description": "Welcome -> offer -> checkout"},
    )

    assert response.status_code == 403
