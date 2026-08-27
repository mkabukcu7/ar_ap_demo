"""API contract tests — these mirror the contract the React dashboard consumes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.agents.base import AgentResponse, Citation, TraceStep
from src.agents.orchestrator import reset_orchestrator
from src.api import main as main_module
from src.data.store import reset_store


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    reset_store()
    reset_orchestrator()
    monkeypatch.setattr(
        main_module,
        "settings",
        SimpleNamespace(
            is_foundry_mode=True,
            data_dir="sample-data",
            default_approver="demo.user@contoso.com",
            model_deployment="gpt-5-mini",
            enable_write_actions=True,
        ),
    )
    return TestClient(main_module.app)


def test_health(client: TestClient) -> None:
    payload = client.get("/api/health").json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "foundry"
    assert payload["invoice_count"] == 50


def test_dashboard_is_served_without_vite(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Finance Operations Command Center" in response.text
    assert "/api/metrics/ap" in response.text


def test_metrics_endpoints(client: TestClient) -> None:
    ap = client.get("/api/metrics/ap").json()
    ar = client.get("/api/metrics/ar").json()
    assert ap["total_invoices"] == 50
    assert {"open_ar_amount", "dso_days", "unapplied_cash"} <= set(ar)
    stages = client.get("/api/pipeline").json()["stages"]
    assert sum(stage["count"] for stage in stages) == 50


def test_invoice_endpoints(client: TestClient) -> None:
    listed = client.get("/api/invoices", params={"status": "pending_approval", "min_amount": 10000}).json()
    assert listed["count"] >= 1
    detail = client.get("/api/invoices/INV-1047")
    assert detail.status_code == 200
    assert detail.json()["invoice"]["status"] == "blocked"
    assert client.get("/api/invoices/INV-9999").status_code == 404
    assert client.get("/api/invoices/INV-1047/evaluation").json()["recommendation"] == "hold"


def test_invalid_status_is_rejected(client: TestClient) -> None:
    assert client.get("/api/invoices", params={"status": "not-a-status"}).status_code == 422


def test_approval_flow(client: TestClient) -> None:
    candidates = client.get("/api/invoices", params={"status": "pending_approval", "max_amount": 5000}).json()["items"]
    invoice = next(item for item in candidates if not item["exceptions"])
    approved = client.post(f"/api/invoices/{invoice['invoice_id']}/approve", json={"approver": "cfo@contoso.com"}).json()
    assert approved["approved"] is True
    posted = client.post(f"/api/invoices/{invoice['invoice_id']}/post").json()
    assert posted["posted"] is True and posted["erp_document_id"]


def test_blocked_invoice_cannot_be_approved(client: TestClient) -> None:
    response = client.post("/api/invoices/INV-1047/approve", json={}).json()
    assert response["approved"] is False


def test_bulk_approval(client: TestClient) -> None:
    response = client.post("/api/approvals/bulk", json={"max_amount": 2000, "require_no_exceptions": True}).json()
    assert response["count"] >= 1
    assert all(item["reason"] for item in response["skipped"])
    assert client.post("/api/approvals/bulk", json={"max_amount": -5}).status_code == 422


def test_ar_endpoints(client: TestClient) -> None:
    assert client.get("/api/ar/remittances").json()["count"] == 25
    unapplied = client.get("/api/ar/unapplied").json()
    assert unapplied["total_unapplied"] > 0
    assert client.get("/api/ar/collections", params={"limit": 5}).json()["count"] == 5
    remittance_id = unapplied["items"][0]["remittance_id"]
    assert client.get(f"/api/ar/remittances/{remittance_id}").json()["found"] is True
    assert client.get("/api/ar/remittances/RMT-0000").status_code == 404


def test_exception_and_knowledge_endpoints(client: TestClient) -> None:
    exceptions = client.get("/api/exceptions").json()
    assert exceptions["count"] >= 1
    knowledge = client.get("/api/knowledge/search", params={"q": "duplicate invoice", "top": 2}).json()
    assert 1 <= knowledge["count"] <= 2


def test_agent_endpoints(client: TestClient) -> None:
    agents = client.get("/api/agents").json()
    names = {agent["name"] for agent in agents}
    assert {
        "finance-orchestrator",
        "ap-agent",
        "ar-agent",
        "policy-agent",
        "vendor-validation-agent",
        "exception-resolution-agent",
    } == names
    orchestrator = next(agent for agent in agents if agent["name"] == "finance-orchestrator")
    assert len(orchestrator["connected_agents"]) == 5
    assert client.get("/api/agents/prompts").json()["count"] == 7
    assert client.get("/api/agents/activity").json()["count"] >= 1


def test_chat_endpoint_returns_citations_and_trace(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.agents import foundry_client

    monkeypatch.setattr(
        foundry_client,
        "invoke_foundry_agent",
        lambda message, approver=None: AgentResponse(
            reply="The relevant control is FIN-SOX-AP-01: invoice approvals require independent review and evidence retention.",
            citations=[
                Citation(
                    title="AP policy control",
                    source="src/prompts/ap-agent.md",
                    snippet="FIN-SOX-AP-01 requires documented approval and evidence retention.",
                )
            ],
            trace=[TraceStep(agent="Finance Orchestrator", tool="knowledge_search", summary="Completed")],
        ),
    )

    payload = client.post("/api/chat", json={"message": "What SOX control governs invoice approvals?"}).json()
    assert "FIN-SOX-AP-01" in payload["reply"]
    assert payload["citations"]
    assert payload["agent_trace"]
    assert payload["session_id"] == "default"


def test_chat_rejects_empty_messages(client: TestClient) -> None:
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_chat_requires_foundry_mode(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.api import main

    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(is_foundry_mode=False, default_approver="demo.user@contoso.com"),
    )

    response = client.post("/api/chat", json={"message": "Show AP metrics", "session_id": "local-fallback"})
    assert response.status_code == 503
    assert "Foundry mode is required" in response.json()["detail"]


def test_chat_uses_foundry_agent_in_foundry_mode(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.agents import foundry_client
    from src.api import main

    monkeypatch.setattr(
        main,
        "settings",
        SimpleNamespace(is_foundry_mode=True, default_approver="demo.user@contoso.com"),
    )
    monkeypatch.setattr(
        foundry_client,
        "invoke_foundry_agent",
        lambda message, approver: AgentResponse(
            reply=f"Foundry: {message}",
            trace=[TraceStep(agent="Finance Orchestrator", tool="ap_metrics", summary="Completed")],
        ),
    )

    payload = client.post("/api/chat", json={"message": "Show AP metrics", "session_id": "remote"}).json()

    assert payload["reply"] == "Foundry: Show AP metrics"
    assert payload["agent_trace"][0]["tool"] == "ap_metrics"
    assert payload["session_id"] == "remote"


def test_chat_does_not_expose_foundry_exception_details(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.agents import foundry_client

    def fail_to_invoke(message: str, approver: str) -> AgentResponse:
        raise RuntimeError("credential-token-secret")

    monkeypatch.setattr(foundry_client, "invoke_foundry_agent", fail_to_invoke)

    response = client.post("/api/chat", json={"message": "Show AP metrics"})

    assert response.status_code == 502
    assert response.json()["detail"] == "Foundry agent invocation failed."
    assert "credential-token-secret" not in response.text
