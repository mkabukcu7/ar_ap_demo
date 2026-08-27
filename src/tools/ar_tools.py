"""Accounts Receivable and cash application tools."""

from __future__ import annotations

from typing import Any

from src.data.store import FinanceDataStore, get_store

AUTO_APPLY_CONFIDENCE = 0.90
SMALL_BALANCE_WRITE_OFF = 250.00
RISK_WEIGHTS = {"low": 1.0, "medium": 1.25, "high": 1.6}


def _s(store: FinanceDataStore | None) -> FinanceDataStore:
    return store or get_store()


def search_remittances(
    status: str | None = None,
    customer_id: str | None = None,
    customer_name: str | None = None,
    min_amount: float | None = None,
    has_exceptions: bool | None = None,
    limit: int | None = None,
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """Search customer remittances by status, customer, amount or exception state."""

    data = _s(store)
    results = []
    for remittance in data.remittances:
        if status and remittance["status"] != status:
            continue
        if customer_id and remittance["customer_id"].upper() != customer_id.upper():
            continue
        if customer_name and customer_name.lower() not in remittance["customer_name"].lower():
            continue
        if min_amount is not None and remittance["payment_amount"] < min_amount:
            continue
        if has_exceptions is not None and bool(remittance["exceptions"]) is not has_exceptions:
            continue
        results.append(remittance)

    results.sort(key=lambda item: item["payment_amount"], reverse=True)
    if limit is not None:
        results = results[:limit]
    return {
        "items": results,
        "count": len(results),
        "total_value": round(sum(item["payment_amount"] for item in results), 2),
    }


def match_remittance(remittance_id: str, store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Explain how a payment was matched to open receivables and what remains unapplied."""

    data = _s(store)
    remittance = data.get_remittance(remittance_id)
    if remittance is None:
        return {"remittance_id": remittance_id, "found": False}

    matches = []
    for match in remittance["matches"]:
        ar_invoice = data.get_ar_invoice(match["ar_invoice_id"])
        matches.append(
            {
                **match,
                "customer_name": remittance["customer_name"],
                "invoice_amount": ar_invoice["amount"] if ar_invoice else None,
                "open_amount": ar_invoice["open_amount"] if ar_invoice else None,
                "auto_applied": match["confidence"] >= AUTO_APPLY_CONFIDENCE,
            }
        )

    open_candidates = [
        inv
        for inv in data.ar_invoices
        if inv["customer_id"] == remittance["customer_id"] and inv["open_amount"] > 0
    ]
    open_candidates.sort(
        key=lambda inv: abs(inv["open_amount"] - remittance["unapplied_amount"]),
    )

    return {
        "remittance_id": remittance["remittance_id"],
        "found": True,
        "customer_id": remittance["customer_id"],
        "customer_name": remittance["customer_name"],
        "payment_amount": remittance["payment_amount"],
        "applied_amount": remittance["applied_amount"],
        "unapplied_amount": remittance["unapplied_amount"],
        "status": remittance["status"],
        "matches": matches,
        "exceptions": remittance["exceptions"],
        "suggested_candidates": open_candidates[:3],
        "control": "FIN-SOX-AR-01",
    }


def list_unapplied_cash(
    min_amount: float | None = None,
    store: FinanceDataStore | None = None,
) -> dict[str, Any]:
    """List payments with cash that has not been applied to a receivable (FIN-SOX-AR-02)."""

    data = _s(store)
    items = [rem for rem in data.remittances if rem["unapplied_amount"] > 0.005]
    if min_amount is not None:
        items = [rem for rem in items if rem["unapplied_amount"] >= min_amount]
    items.sort(key=lambda item: item["unapplied_amount"], reverse=True)
    total_unapplied = round(sum(item["unapplied_amount"] for item in items), 2)
    return {
        "items": items,
        "count": len(items),
        "total_unapplied": total_unapplied,
        "currency": "USD",
        "control": "FIN-SOX-AR-02",
    }


def ar_health_summary(store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Return the AR KPI set: open balance, aging, DSO, unapplied cash and risk."""

    data = _s(store)
    open_invoices = [inv for inv in data.ar_invoices if inv["open_amount"] > 0.005]
    open_ar_amount = round(sum(inv["open_amount"] for inv in open_invoices), 2)
    past_due = [inv for inv in open_invoices if inv["days_past_due"] > 0]
    past_due_amount = round(sum(inv["open_amount"] for inv in past_due), 2)
    collections = round(sum(rem["payment_amount"] for rem in data.remittances), 2)
    unapplied = round(sum(rem["unapplied_amount"] for rem in data.remittances), 2)

    aging: dict[str, float] = {}
    for invoice in open_invoices:
        aging[invoice["aging_bucket"]] = round(aging.get(invoice["aging_bucket"], 0.0) + invoice["open_amount"], 2)

    at_risk = round(
        sum(
            inv["open_amount"]
            for inv in open_invoices
            if inv["days_past_due"] > 60
            or (data.get_customer(inv["customer_id"]) or {}).get("credit_risk") == "high"
        ),
        2,
    )

    billed = round(sum(inv["amount"] for inv in data.ar_invoices), 2)
    dso = round((open_ar_amount / billed) * 90, 1) if billed else 0.0

    return {
        "open_invoices": len(open_invoices),
        "open_ar_amount": open_ar_amount,
        "past_due_amount": past_due_amount,
        "past_due_rate": round(past_due_amount / open_ar_amount, 4) if open_ar_amount else 0.0,
        "dso_days": dso,
        "unapplied_cash": unapplied,
        "unapplied_rate": round(unapplied / collections, 4) if collections else 0.0,
        "collections_at_risk": at_risk,
        "aging": aging,
        "currency": "USD",
    }


def prioritize_collections(limit: int = 10, store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Rank open receivables for collection using balance, aging and credit risk."""

    data = _s(store)
    ranked = []
    for invoice in data.ar_invoices:
        if invoice["open_amount"] <= 0.005:
            continue
        customer = data.get_customer(invoice["customer_id"]) or {}
        risk_weight = RISK_WEIGHTS.get(customer.get("credit_risk", "low"), 1.0)
        score = round(invoice["open_amount"] * risk_weight * (1 + invoice["days_past_due"] / 30), 2)
        ranked.append(
            {
                "ar_invoice_id": invoice["ar_invoice_id"],
                "customer_id": invoice["customer_id"],
                "customer_name": invoice["customer_name"],
                "open_amount": invoice["open_amount"],
                "days_past_due": invoice["days_past_due"],
                "aging_bucket": invoice["aging_bucket"],
                "credit_risk": customer.get("credit_risk", "low"),
                "collector": invoice["collector"],
                "priority_score": score,
                "recommended_action": _dunning_action(invoice["days_past_due"]),
            }
        )

    ranked.sort(key=lambda item: item["priority_score"], reverse=True)
    return {"items": ranked[:limit], "count": min(limit, len(ranked)), "total_open": len(ranked)}


def _dunning_action(days_past_due: int) -> str:
    if days_past_due <= 0:
        return "Statement only"
    if days_past_due <= 30:
        return "Automated reminder"
    if days_past_due <= 60:
        return "Collector call and email"
    if days_past_due <= 90:
        return "Escalate to account executive, review credit hold"
    return "Credit hold and Controller escalation"


def payment_discrepancies(limit: int | None = None, store: FinanceDataStore | None = None) -> dict[str, Any]:
    """Return payment matching exceptions ranked by financial impact."""

    data = _s(store)
    items = []
    for remittance in data.remittances:
        if not remittance["exceptions"]:
            continue
        impact = remittance["unapplied_amount"] or remittance["payment_amount"]
        items.append(
            {
                "remittance_id": remittance["remittance_id"],
                "customer_id": remittance["customer_id"],
                "customer_name": remittance["customer_name"],
                "payment_date": remittance["payment_date"],
                "payment_amount": remittance["payment_amount"],
                "applied_amount": remittance["applied_amount"],
                "unapplied_amount": remittance["unapplied_amount"],
                "status": remittance["status"],
                "exceptions": remittance["exceptions"],
                "impact": round(impact, 2),
                "write_off_eligible": impact <= SMALL_BALANCE_WRITE_OFF,
            }
        )

    items.sort(key=lambda item: item["impact"], reverse=True)
    if limit is not None:
        items = items[:limit]
    return {"items": items, "count": len(items), "total_impact": round(sum(i["impact"] for i in items), 2)}
