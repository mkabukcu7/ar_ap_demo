"""FastAPI application for the Finance Operations Command Center.

Serves the React dashboard in `ui/webapp` and exposes the AP, AR, knowledge and
orchestrator capabilities as a REST API. Run locally with::

    uvicorn src.api.main:app --reload --port 8000

Interactive documentation (OpenAPI) is available at ``/docs``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from src.agents.orchestrator import DEMO_PROMPTS, get_orchestrator
from src.api.schemas import (
    AgentDefinition,
    ApproveRequest,
    ApproveResponse,
    BulkApproveRequest,
    BulkApproveResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    InvoiceStatus,
    PostResponse,
)
from src.config import settings
from src.data.store import get_store
from src.tools import ap_tools, ar_tools, knowledge_tools

STATIC_DASHBOARD = Path(__file__).resolve().parents[2] / "ui" / "static-demo.html"

app = FastAPI(
    title="Finance Operations Agent Accelerator API",
    version="1.0.0",
    description=(
        "Accounts Payable, Accounts Receivable and Finance Knowledge capabilities for the "
        "Azure AI Foundry Finance Operations Command Center."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _store():
    return get_store(settings.data_dir)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the standalone dashboard without requiring a JavaScript toolchain."""

    return FileResponse(STATIC_DASHBOARD)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    if not settings.is_foundry_mode:
        raise HTTPException(status_code=503, detail="Foundry mode is required; local mode has been removed.")

    store = _store()
    return HealthResponse(
        status="ok",
        mode="foundry",
        model_deployment=settings.model_deployment,
        invoice_count=len(store.invoices),
        knowledge_documents=len({doc["document_id"] for doc in store.knowledge}),
    )


# ------------------------------------------------------------------ metrics


@app.get("/api/metrics/ap", tags=["metrics"])
def ap_metrics() -> dict[str, Any]:
    return ap_tools.ap_metrics(store=_store())


@app.get("/api/metrics/ar", tags=["metrics"])
def ar_metrics() -> dict[str, Any]:
    return ar_tools.ar_health_summary(store=_store())


@app.get("/api/pipeline", tags=["metrics"])
def pipeline() -> dict[str, Any]:
    return {"stages": _store().pipeline_counts()}


# ----------------------------------------------------------- accounts payable


@app.get("/api/invoices", tags=["accounts-payable"])
def list_invoices(
    status: InvoiceStatus | None = None,
    min_amount: float | None = Query(default=None, ge=0),
    max_amount: float | None = Query(default=None, ge=0),
    vendor_id: str | None = None,
    has_exceptions: bool | None = None,
    limit: int | None = Query(default=None, ge=1, le=500),
) -> dict[str, Any]:
    return ap_tools.search_invoices(
        status=status,
        min_amount=min_amount,
        max_amount=max_amount,
        vendor_id=vendor_id,
        has_exceptions=has_exceptions,
        limit=limit,
        store=_store(),
    )


@app.get("/api/invoices/{invoice_id}", tags=["accounts-payable"])
def get_invoice(invoice_id: str) -> dict[str, Any]:
    result = ap_tools.get_invoice(invoice_id, store=_store())
    if not result["found"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@app.get("/api/invoices/{invoice_id}/evaluation", tags=["accounts-payable"])
def evaluate_invoice(invoice_id: str) -> dict[str, Any]:
    result = ap_tools.evaluate_invoice(invoice_id, store=_store())
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} was not found.")
    return result


@app.post("/api/invoices/{invoice_id}/approve", response_model=ApproveResponse, tags=["accounts-payable"])
def approve_invoice(invoice_id: str, request: ApproveRequest | None = None) -> ApproveResponse:
    _require_write_actions()
    request = request or ApproveRequest()
    result = ap_tools.approve_invoice(
        invoice_id,
        approver=request.approver or settings.default_approver,
        force=request.force,
        store=_store(),
    )
    if "not found" in result["message"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return ApproveResponse(
        invoice_id=result["invoice_id"],
        status=result.get("status", "unknown"),
        approved=result["approved"],
        message=result["message"],
    )


@app.post("/api/approvals/bulk", response_model=BulkApproveResponse, tags=["accounts-payable"])
def bulk_approve(request: BulkApproveRequest) -> BulkApproveResponse:
    _require_write_actions()
    result = ap_tools.bulk_approve_invoices(
        max_amount=request.max_amount,
        require_no_exceptions=request.require_no_exceptions,
        approver=request.approver or settings.default_approver,
        store=_store(),
    )
    return BulkApproveResponse(**result)


@app.post("/api/invoices/{invoice_id}/post", response_model=PostResponse, tags=["accounts-payable"])
def post_invoice(invoice_id: str) -> PostResponse:
    _require_write_actions()
    result = ap_tools.post_invoice_to_erp(invoice_id, store=_store())
    if "not found" in result["message"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return PostResponse(
        invoice_id=result["invoice_id"],
        posted=result["posted"],
        erp_document_id=result.get("erp_document_id"),
        message=result["message"],
    )


@app.get("/api/vendors", tags=["accounts-payable"])
def list_vendors() -> dict[str, Any]:
    vendors = _store().vendors
    return {"items": vendors, "count": len(vendors)}


@app.get("/api/purchase-orders", tags=["accounts-payable"])
def list_purchase_orders() -> dict[str, Any]:
    orders = _store().purchase_orders
    return {"items": orders, "count": len(orders)}


# -------------------------------------------------------- accounts receivable


@app.get("/api/ar/remittances", tags=["accounts-receivable"])
def list_remittances(
    status: str | None = None,
    customer_id: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=500),
) -> dict[str, Any]:
    return ar_tools.search_remittances(status=status, customer_id=customer_id, limit=limit, store=_store())


@app.get("/api/ar/remittances/{remittance_id}", tags=["accounts-receivable"])
def get_remittance(remittance_id: str) -> dict[str, Any]:
    result = ar_tools.match_remittance(remittance_id, store=_store())
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=f"Remittance {remittance_id} was not found.")
    return result


@app.get("/api/ar/unapplied", tags=["accounts-receivable"])
def unapplied_cash(min_amount: float | None = Query(default=None, ge=0)) -> dict[str, Any]:
    return ar_tools.list_unapplied_cash(min_amount=min_amount, store=_store())


@app.get("/api/ar/collections", tags=["accounts-receivable"])
def collections(limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return ar_tools.prioritize_collections(limit=limit, store=_store())


@app.get("/api/ar/discrepancies", tags=["accounts-receivable"])
def discrepancies(limit: int = Query(default=10, ge=1, le=100)) -> dict[str, Any]:
    return ar_tools.payment_discrepancies(limit=limit, store=_store())


# ---------------------------------------------------------------- exceptions


@app.get("/api/exceptions", tags=["exceptions"])
def exceptions(severity: str | None = None, domain: str | None = None) -> dict[str, Any]:
    return ap_tools.list_exceptions(severity=severity, domain=domain, store=_store())


# ----------------------------------------------------------------- knowledge


@app.get("/api/knowledge/search", tags=["knowledge"])
def knowledge_search(q: str = Query(min_length=2), top: int = Query(default=3, ge=1, le=10)) -> dict[str, Any]:
    return knowledge_tools.search_finance_knowledge(q, top=top, store=_store())


# --------------------------------------------------------------------- agents


@app.get("/api/agents", response_model=list[AgentDefinition], tags=["agents"])
def list_agents() -> list[AgentDefinition]:
    orchestrator = get_orchestrator()
    definitions = [orchestrator.definition(), *(agent.definition() for agent in orchestrator.child_agents)]
    return [AgentDefinition(**definition) for definition in definitions]


@app.get("/api/agents/activity", tags=["agents"])
def agent_activity(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    items = _store().recent_activity(limit)
    return {"items": items, "count": len(items)}


@app.get("/api/agents/prompts", tags=["agents"])
def demo_prompts() -> dict[str, Any]:
    return {"items": DEMO_PROMPTS, "count": len(DEMO_PROMPTS)}


@app.post("/api/chat", response_model=ChatResponse, tags=["agents"])
def chat(request: ChatRequest) -> ChatResponse:
    if not settings.is_foundry_mode:
        raise HTTPException(status_code=503, detail="Foundry mode is required; local mode has been removed.")

    session_id = request.session_id or "default"
    approver = request.approver or settings.default_approver
    try:
        from src.agents.foundry_client import invoke_foundry_agent

        response = invoke_foundry_agent(request.message, approver=approver)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Foundry agent invocation failed: {error}") from error

    payload = response.to_dict()
    return ChatResponse(**payload, session_id=session_id)


def _require_write_actions() -> None:
    if not settings.enable_write_actions:
        raise HTTPException(status_code=403, detail="Write actions are disabled in this environment.")
