"""Tool registry.

Maps the function-tool names declared in the Azure AI Foundry agent definitions
(`infra/foundry/agents/*.agent.yaml`) to their Python implementations, together
with the JSON schema that is registered with the Azure AI Agent Service.
"""

from __future__ import annotations

from typing import Any, Callable

from src.tools import ap_tools, ar_tools, knowledge_tools

ToolFunction = Callable[..., dict[str, Any]]

TOOL_FUNCTIONS: dict[str, ToolFunction] = {
    "search_invoices": ap_tools.search_invoices,
    "get_invoice": ap_tools.get_invoice,
    "match_invoice_to_po": ap_tools.match_invoice_to_po,
    "detect_duplicate_invoice": ap_tools.detect_duplicate_invoice,
    "validate_vendor": ap_tools.validate_vendor,
    "evaluate_invoice": ap_tools.evaluate_invoice,
    "approve_invoice": ap_tools.approve_invoice,
    "bulk_approve_invoices": ap_tools.bulk_approve_invoices,
    "post_invoice_to_erp": ap_tools.post_invoice_to_erp,
    "list_exceptions": ap_tools.list_exceptions,
    "ap_metrics": ap_tools.ap_metrics,
    "search_remittances": ar_tools.search_remittances,
    "match_remittance": ar_tools.match_remittance,
    "list_unapplied_cash": ar_tools.list_unapplied_cash,
    "ar_health_summary": ar_tools.ar_health_summary,
    "prioritize_collections": ar_tools.prioritize_collections,
    "payment_discrepancies": ar_tools.payment_discrepancies,
    "search_finance_knowledge": knowledge_tools.search_finance_knowledge,
    "answer_with_citations": knowledge_tools.answer_with_citations,
}


def _tool(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


_STRING = {"type": "string"}
_NUMBER = {"type": "number"}
_INTEGER = {"type": "integer"}
_BOOLEAN = {"type": "boolean"}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    _tool(
        "search_invoices",
        "Search accounts payable invoices by status, amount band, vendor, purchase order or exception state.",
        {
            "status": {**_STRING, "enum": [
                "received", "extracted", "validated", "matched", "pending_approval", "approved", "posted", "blocked",
            ]},
            "min_amount": _NUMBER,
            "max_amount": _NUMBER,
            "vendor_id": _STRING,
            "vendor_name": _STRING,
            "has_exceptions": _BOOLEAN,
            "po_number": _STRING,
            "limit": _INTEGER,
        },
    ),
    _tool("get_invoice", "Retrieve one invoice with vendor, purchase order and approval context.", {"invoice_id": _STRING}, ["invoice_id"]),
    _tool("match_invoice_to_po", "Run the three-way match check for an invoice against its purchase order.", {"invoice_id": _STRING}, ["invoice_id"]),
    _tool("detect_duplicate_invoice", "Score other invoices from the same vendor for duplicate risk.", {"invoice_id": _STRING}, ["invoice_id"]),
    _tool("validate_vendor", "Validate a supplier against the vendor master.", {"vendor_id": _STRING, "vendor_name": _STRING}),
    _tool("evaluate_invoice", "Run the full AP validation chain and return an approval recommendation.", {"invoice_id": _STRING}, ["invoice_id"]),
    _tool(
        "approve_invoice",
        "Record a human approval decision on an invoice. Requires an authenticated approver (FIN-SOX-AI-01).",
        {"invoice_id": _STRING, "approver": _STRING, "force": _BOOLEAN},
        ["invoice_id"],
    ),
    _tool(
        "bulk_approve_invoices",
        "Approve every eligible invoice below a threshold in one audited action.",
        {"max_amount": _NUMBER, "require_no_exceptions": _BOOLEAN, "approver": _STRING},
        ["max_amount"],
    ),
    _tool("post_invoice_to_erp", "Post an approved invoice to the ERP and return the AP document id.", {"invoice_id": _STRING}, ["invoice_id"]),
    _tool(
        "list_exceptions",
        "List open AP and AR exceptions ranked by financial impact.",
        {"severity": {**_STRING, "enum": ["low", "medium", "high"]}, "domain": {**_STRING, "enum": ["ap", "ar"]}},
    ),
    _tool("ap_metrics", "Return accounts payable KPIs for the command centre dashboard.", {}),
    _tool(
        "search_remittances",
        "Search customer remittances by status, customer, amount or exception state.",
        {
            "status": {**_STRING, "enum": ["applied", "partially_applied", "unapplied"]},
            "customer_id": _STRING,
            "customer_name": _STRING,
            "min_amount": _NUMBER,
            "has_exceptions": _BOOLEAN,
            "limit": _INTEGER,
        },
    ),
    _tool("match_remittance", "Explain how a payment was matched to open receivables.", {"remittance_id": _STRING}, ["remittance_id"]),
    _tool("list_unapplied_cash", "List payments with cash that has not been applied to a receivable.", {"min_amount": _NUMBER}),
    _tool("ar_health_summary", "Return accounts receivable KPIs: open balance, aging, DSO and unapplied cash.", {}),
    _tool("prioritize_collections", "Rank open receivables for collection activity.", {"limit": _INTEGER}),
    _tool("payment_discrepancies", "Return payment matching exceptions ranked by financial impact.", {"limit": _INTEGER}),
    _tool(
        "search_finance_knowledge",
        "Retrieve grounded passages from AP, AR, treasury, SOX and finance operations documentation.",
        {"query": _STRING, "top": _INTEGER, "document_type": _STRING},
        ["query"],
    ),
    _tool("answer_with_citations", "Answer a finance policy question with citations to the source documents.", {"query": _STRING, "top": _INTEGER}, ["query"]),
]


def get_tool(name: str) -> ToolFunction:
    """Return the callable registered under `name`."""

    if name not in TOOL_FUNCTIONS:
        raise KeyError(f"Unknown tool '{name}'. Registered tools: {sorted(TOOL_FUNCTIONS)}")
    return TOOL_FUNCTIONS[name]


def invoke_tool(name: str, **arguments: Any) -> dict[str, Any]:
    """Invoke a registered tool by name with keyword arguments."""

    return get_tool(name)(**arguments)


def schema_for(name: str) -> dict[str, Any]:
    """Return the JSON schema registered for `name`."""

    for schema in TOOL_SCHEMAS:
        if schema["function"]["name"] == name:
            return schema
    raise KeyError(f"No schema registered for tool '{name}'.")
