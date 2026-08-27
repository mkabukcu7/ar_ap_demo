"""Pydantic schemas for the Finance Operations API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

InvoiceStatus = Literal[
    "received", "extracted", "validated", "matched", "pending_approval", "approved", "posted", "blocked"
]


class HealthResponse(BaseModel):
    status: str
    mode: Literal["local", "foundry"]
    model_deployment: str
    invoice_count: int
    knowledge_documents: int


class ApproveRequest(BaseModel):
    approver: str | None = Field(default=None, description="Authenticated approver identity (Entra ID UPN).")
    force: bool = Field(default=False, description="Override open exceptions; requires a documented reason.")


class ApproveResponse(BaseModel):
    invoice_id: str
    status: str
    approved: bool
    message: str


class BulkApproveRequest(BaseModel):
    max_amount: float = Field(gt=0, description="Approve invoices strictly below this amount.")
    require_no_exceptions: bool = True
    approver: str | None = None


class SkippedInvoice(BaseModel):
    invoice_id: str
    reason: str


class BulkApproveResponse(BaseModel):
    approved: list[str]
    skipped: list[SkippedInvoice]
    count: int
    max_amount: float
    approver: str


class PostResponse(BaseModel):
    invoice_id: str
    posted: bool
    erp_document_id: str | None = None
    message: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None
    approver: str | None = None


class Citation(BaseModel):
    title: str
    source: str
    snippet: str


class TraceStep(BaseModel):
    agent: str
    tool: str
    summary: str


class ChatResponse(BaseModel):
    reply: str
    citations: list[Citation] = []
    agent_trace: list[TraceStep] = []
    data: Any | None = None
    session_id: str


class CollectionItem(BaseModel):
    ar_invoice_id: str
    customer_id: str
    customer_name: str
    open_amount: float
    days_past_due: int
    aging_bucket: str
    credit_risk: str
    collector: str
    priority_score: float
    recommended_action: str


class AgentDefinition(BaseModel):
    name: str
    display_name: str
    description: str
    tools: list[str]
    connected_agents: list[str] = []
