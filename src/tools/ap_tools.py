"""Accounts Payable tools.

Each public function in this module is exposed to the Azure AI Agent Service as
a function tool (see `infra/foundry/agents/ap-agent.agent.yaml`) and is also
called directly by the FastAPI layer. Tools return plain JSON-serialisable
dictionaries so they can be handed straight back to the model.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from src.data.store import FinanceDataStore, get_store

APPROVAL_MATRIX = [
    (2_000.00, ["Straight-through processing (exception free)", "AP Analyst"]),
    (10_000.00, ["Cost Centre Manager"]),
    (25_000.00, ["Cost Centre Manager", "Finance Director"]),
    (100_000.00, ["Finance Director", "Controller"]),
    (float("inf"), ["Controller", "Chief Financial Officer"]),
]

PRICE_TOLERANCE_PCT = 0.02
TOTAL_TOLERANCE_PCT = 0.0
STRAIGHT_THROUGH_LIMIT = 2_000.00
AUTO_APPROVE_CONFIDENCE = 0.80


def _s(store: FinanceDataStore | None) -> FinanceDataStore:
    return store or get_store()


def required_approvals(total_amount: float) -> list[str]:
    """Return the approval levels required for an invoice total (FIN-AP-001)."""

    for threshold, approvers in APPROVAL_MATRIX:
        if total_amount <= threshold:
            return list(approvers)
    return list(APPROVAL_MATRIX[-1][1])  # pragma: no cover - unreachable


def search_invoices(
    status: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    vendor_id: str | None = None,
    vendor_name: str | None = None,
    has_exceptions: bool | None = None,
    po_number: str | None = None,
    limit: int | None = None,
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """Search AP invoices by status, amount band, vendor, PO or exception state."""

    data = _s(store)
    results = []
    for invoice in data.invoices:
        if status and invoice["status"] != status:
            continue
        if min_amount is not None and invoice["total_amount"] < min_amount:
            continue
        if max_amount is not None and invoice["total_amount"] > max_amount:
            continue
        if vendor_id and invoice["vendor_id"].upper() != vendor_id.upper():
            continue
        if vendor_name and vendor_name.lower() not in invoice["vendor_name"].lower():
            continue
        if po_number and (invoice["po_number"] or "").upper() != po_number.upper():
            continue
        if has_exceptions is not None and bool(invoice["exceptions"]) is not has_exceptions:
            continue
        results.append(invoice)

    results.sort(key=lambda item: item["total_amount"], reverse=True)
    total_value = round(sum(item["total_amount"] for item in results), 2)
    if limit is not None:
        results = results[:limit]
    return {"items": results, "count": len(results), "total_value": total_value}


def get_invoice(invoice_id: str, store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Return a single invoice with its purchase order and vendor context."""

    data = _s(store)
    invoice = data.get_invoice(invoice_id)
    if invoice is None:
        return {"found": False, "invoice_id": invoice_id, "message": f"Invoice {invoice_id} was not found."}
    return {
        "found": True,
        "invoice": invoice,
        "vendor": data.get_vendor(invoice["vendor_id"]),
        "purchase_order": data.get_purchase_order(invoice["po_number"]) if invoice["po_number"] else None,
        "required_approvals": required_approvals(invoice["total_amount"]),
    }


def match_invoice_to_po(invoice_id: str, store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Perform the three-way match check for an invoice against its purchase order."""

    data = _s(store)
    invoice = data.get_invoice(invoice_id)
    if invoice is None:
        return {"invoice_id": invoice_id, "matched": False, "reason": "invoice_not_found"}

    vendor = data.get_vendor(invoice["vendor_id"])
    if not invoice["po_number"]:
        po_required = bool(vendor and vendor["po_required"])
        return {
            "invoice_id": invoice_id,
            "matched": not po_required,
            "reason": "po_missing" if po_required else "po_not_required",
            "po_number": None,
        }

    purchase_order = data.get_purchase_order(invoice["po_number"])
    if purchase_order is None:
        return {
            "invoice_id": invoice_id,
            "matched": False,
            "reason": "po_not_found",
            "po_number": invoice["po_number"],
        }

    variance = round(invoice["total_amount"] - purchase_order["remaining_amount"], 2)
    within_tolerance = variance <= round(purchase_order["remaining_amount"] * TOTAL_TOLERANCE_PCT, 2)
    return {
        "invoice_id": invoice_id,
        "po_number": purchase_order["po_number"],
        "matched": within_tolerance,
        "reason": "within_tolerance" if within_tolerance else "po_amount_mismatch",
        "invoice_total": invoice["total_amount"],
        "po_amount": purchase_order["amount"],
        "po_remaining_amount": purchase_order["remaining_amount"],
        "variance": variance,
        "goods_received_amount": purchase_order["received_amount"],
    }


def detect_duplicate_invoice(invoice_id: str, store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Score other invoices from the same vendor for duplicate risk (FIN-SOX-AP-03)."""

    data = _s(store)
    invoice = data.get_invoice(invoice_id)
    if invoice is None:
        return {"invoice_id": invoice_id, "is_duplicate": False, "candidates": []}

    candidates = []
    for other in data.invoices:
        if other["invoice_id"] == invoice["invoice_id"]:
            continue
        if other["vendor_id"] != invoice["vendor_id"]:
            continue
        signals: list[str] = []
        if other["invoice_number"] == invoice["invoice_number"]:
            signals.append("same_invoice_number")
        if abs(other["total_amount"] - invoice["total_amount"]) < 0.01:
            signals.append("same_total_amount")
        if other["po_number"] and other["po_number"] == invoice["po_number"]:
            signals.append("same_po_number")
        if abs((date.fromisoformat(other["invoice_date"]) - date.fromisoformat(invoice["invoice_date"])).days) <= 5:
            signals.append("invoice_dates_within_5_days")
        if len(signals) >= 2:
            candidates.append(
                {
                    "invoice_id": other["invoice_id"],
                    "status": other["status"],
                    "total_amount": other["total_amount"],
                    "signals": signals,
                    "confidence": round(min(0.55 + 0.15 * len(signals), 0.99), 2),
                }
            )

    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    return {
        "invoice_id": invoice["invoice_id"],
        "is_duplicate": bool(candidates),
        "candidates": candidates,
        "control": "FIN-SOX-AP-03",
    }


def validate_vendor(
    vendor_id: str | None = None,
    vendor_name: str | None = None,
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """Validate a supplier against the vendor master (FIN-SOX-AP-04)."""

    data = _s(store)
    vendor = None
    if vendor_id:
        vendor = data.get_vendor(vendor_id)
    if vendor is None and vendor_name:
        vendor = data.get_vendor_by_name(vendor_name)
        if vendor is None:
            needle = vendor_name.lower()
            vendor = next((ven for ven in data.vendors if needle in ven["name"].lower()), None)

    if vendor is None:
        return {
            "valid": False,
            "reason": "vendor_not_found",
            "message": "Supplier is not present in the vendor master.",
            "control": "FIN-SOX-AP-04",
        }

    valid = vendor["status"] == "approved"
    return {
        "valid": valid,
        "vendor": vendor,
        "reason": "approved" if valid else f"vendor_status_{vendor['status']}",
        "message": (
            f"{vendor['name']} is approved for payment."
            if valid
            else f"{vendor['name']} is in '{vendor['status']}' status and may not be paid."
        ),
        "control": "FIN-SOX-AP-04",
    }


def evaluate_invoice(invoice_id: str, store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Run the full AP validation chain and return an approval recommendation."""

    data = _s(store)
    invoice = data.get_invoice(invoice_id)
    if invoice is None:
        return {"invoice_id": invoice_id, "found": False}

    match = match_invoice_to_po(invoice_id, store=data)
    duplicate = detect_duplicate_invoice(invoice_id, store=data)
    vendor_check = validate_vendor(vendor_id=invoice["vendor_id"], store=data)

    blockers: list[str] = []
    if not match["matched"]:
        blockers.append(match["reason"])
    if duplicate["is_duplicate"]:
        blockers.append("duplicate_suspected")
    if not vendor_check["valid"]:
        blockers.append(vendor_check["reason"])
    if invoice["extraction_confidence"] < AUTO_APPROVE_CONFIDENCE:
        blockers.append("low_confidence_extraction")

    return {
        "invoice_id": invoice["invoice_id"],
        "found": True,
        "total_amount": invoice["total_amount"],
        "currency": invoice["currency"],
        "status": invoice["status"],
        "po_match": match,
        "duplicate_check": duplicate,
        "vendor_check": vendor_check,
        "exceptions": invoice["exceptions"],
        "blockers": blockers,
        "required_approvals": required_approvals(invoice["total_amount"]),
        "recommendation": "hold" if blockers else "approve",
        "straight_through_eligible": not blockers and invoice["total_amount"] <= STRAIGHT_THROUGH_LIMIT,
    }


def approve_invoice(
    invoice_id: str,
    approver: str = "demo.user@contoso.com",
    force: bool = False,
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """Record a human approval decision on an invoice (human-in-the-loop, FIN-SOX-AI-01)."""

    data = _s(store)
    invoice = data.get_invoice(invoice_id)
    if invoice is None:
        return {"invoice_id": invoice_id, "approved": False, "message": f"Invoice {invoice_id} was not found."}

    if invoice["status"] in {"approved", "posted"}:
        return {
            "invoice_id": invoice_id,
            "approved": True,
            "status": invoice["status"],
            "message": f"Invoice {invoice_id} is already {invoice['status']}.",
        }

    if invoice["exceptions"] and not force:
        codes = ", ".join(item["code"] for item in invoice["exceptions"])
        data.record_activity("AP Agent", "approval_rejected", f"{invoice_id} has open exceptions: {codes}", "failed")
        return {
            "invoice_id": invoice_id,
            "approved": False,
            "status": invoice["status"],
            "message": f"Invoice {invoice_id} has open exceptions ({codes}) and cannot be approved.",
            "exceptions": invoice["exceptions"],
        }

    history = list(invoice.get("approval_history", []))
    history.append({"approver": approver, "decision": "approved", "required": required_approvals(invoice["total_amount"])})
    data.update_invoice(invoice_id, status="approved", approver=approver, approval_history=history)
    data.record_activity(
        "AP Agent",
        "invoice_approved",
        f"{invoice_id} ({invoice['currency']} {invoice['total_amount']:,.2f}) approved by {approver}",
    )
    return {
        "invoice_id": invoice_id,
        "approved": True,
        "status": "approved",
        "approver": approver,
        "required_approvals": required_approvals(invoice["total_amount"]),
        "message": f"Invoice {invoice_id} approved by {approver}.",
    }


def bulk_approve_invoices(
    max_amount: float,
    require_no_exceptions: bool = True,
    approver: str = "demo.user@contoso.com",
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """Approve every eligible invoice below `max_amount` in a single, audited action."""

    data = _s(store)
    approved: list[str] = []
    skipped: list[dict[str, str]] = []

    for invoice in list(data.invoices):
        if invoice["total_amount"] >= max_amount:
            continue
        if invoice["status"] not in {"pending_approval", "matched", "validated"}:
            continue
        if require_no_exceptions and invoice["exceptions"]:
            skipped.append(
                {
                    "invoice_id": invoice["invoice_id"],
                    "reason": "open exceptions: " + ", ".join(item["code"] for item in invoice["exceptions"]),
                }
            )
            continue
        result = approve_invoice(invoice["invoice_id"], approver=approver, store=data)
        if result["approved"]:
            approved.append(invoice["invoice_id"])
        else:
            skipped.append({"invoice_id": invoice["invoice_id"], "reason": result["message"]})

    data.record_activity(
        "AP Agent",
        "bulk_approval",
        f"{len(approved)} invoices under {max_amount:,.2f} approved by {approver}; {len(skipped)} skipped",
    )
    return {
        "approved": approved,
        "skipped": skipped,
        "count": len(approved),
        "max_amount": max_amount,
        "approver": approver,
    }


def post_invoice_to_erp(invoice_id: str, store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Simulate posting an approved invoice to the ERP and return the AP document id."""

    data = _s(store)
    invoice = data.get_invoice(invoice_id)
    if invoice is None:
        return {"invoice_id": invoice_id, "posted": False, "message": f"Invoice {invoice_id} was not found."}
    if invoice["status"] == "posted":
        return {
            "invoice_id": invoice_id,
            "posted": True,
            "erp_document_id": invoice["erp_document_id"],
            "message": f"Invoice {invoice_id} was already posted.",
        }
    if invoice["status"] != "approved":
        return {
            "invoice_id": invoice_id,
            "posted": False,
            "message": f"Invoice {invoice_id} must be approved before posting (current status: {invoice['status']}).",
        }

    erp_document_id = f"ERP-AP-{880000 + int(invoice['invoice_id'].split('-')[1])}"
    data.update_invoice(invoice_id, status="posted", erp_document_id=erp_document_id)
    data.record_activity("AP Agent", "erp_posting", f"{invoice_id} posted to ERP as {erp_document_id}")
    return {
        "invoice_id": invoice_id,
        "posted": True,
        "erp_document_id": erp_document_id,
        "message": f"Invoice {invoice_id} posted to the ERP as {erp_document_id}.",
    }


def list_exceptions(
    severity: str | None = None,
    domain: str | None = None,
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """List open AP and AR exceptions, highest financial impact first."""

    data = _s(store)
    items: list[dict[str, Any]] = []

    if domain in (None, "ap"):
        for invoice in data.invoices:
            for exception in invoice["exceptions"]:
                items.append(
                    {
                        "domain": "ap",
                        "invoice_id": invoice["invoice_id"],
                        "document_id": None,
                        "code": exception["code"],
                        "severity": exception["severity"],
                        "message": exception["message"],
                        "amount": invoice["total_amount"],
                        "owner": invoice["approver"],
                    }
                )
    if domain in (None, "ar"):
        for remittance in data.remittances:
            for exception in remittance["exceptions"]:
                items.append(
                    {
                        "domain": "ar",
                        "invoice_id": None,
                        "document_id": remittance["remittance_id"],
                        "code": exception["code"],
                        "severity": exception["severity"],
                        "message": exception["message"],
                        "amount": remittance["unapplied_amount"] or remittance["payment_amount"],
                        "owner": remittance["customer_name"],
                    }
                )

    if severity:
        items = [item for item in items if item["severity"] == severity]
    items.sort(key=lambda item: item["amount"], reverse=True)
    return {"items": items, "count": len(items), "total_value": round(sum(item["amount"] for item in items), 2)}


def ap_metrics(store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Return the AP KPI set rendered on the command centre dashboard."""

    data = _s(store)
    invoices = data.invoices
    total = len(invoices)
    with_exceptions = [inv for inv in invoices if inv["exceptions"]]
    touchless = [
        inv
        for inv in invoices
        if not inv["exceptions"] and inv["po_number"] and inv["extraction_confidence"] >= AUTO_APPROVE_CONFIDENCE
    ]
    cycle_times = [
        (date.fromisoformat(inv["received_date"]) - date.fromisoformat(inv["invoice_date"])).days + 2
        for inv in invoices
    ]
    return {
        "total_invoices": total,
        "awaiting_approval": len([inv for inv in invoices if inv["status"] == "pending_approval"]),
        "approved": len([inv for inv in invoices if inv["status"] == "approved"]),
        "blocked": len([inv for inv in invoices if inv["status"] == "blocked"]),
        "posted": len([inv for inv in invoices if inv["status"] == "posted"]),
        "touchless_rate": round(len(touchless) / total, 4) if total else 0.0,
        "avg_cycle_time_days": round(sum(cycle_times) / total, 1) if total else 0.0,
        "exception_rate": round(len(with_exceptions) / total, 4) if total else 0.0,
        "total_spend": round(sum(inv["total_amount"] for inv in invoices), 2),
        "currency": "USD",
    }
