"""Accounts Payable tool behaviour."""

from __future__ import annotations

from src.data.store import FinanceDataStore
from src.tools import ap_tools


def test_required_approvals_follow_the_policy_matrix() -> None:
    assert ap_tools.required_approvals(1_500) == [
        "Straight-through processing (exception free)",
        "AP Analyst",
    ]
    assert ap_tools.required_approvals(9_999) == ["Cost Centre Manager"]
    assert ap_tools.required_approvals(25_000) == ["Cost Centre Manager", "Finance Director"]
    assert ap_tools.required_approvals(30_000) == ["Finance Director", "Controller"]
    assert ap_tools.required_approvals(250_000) == ["Controller", "Chief Financial Officer"]


def test_search_invoices_filters(store: FinanceDataStore) -> None:
    result = ap_tools.search_invoices(status="pending_approval", min_amount=10_000, store=store)
    assert result["count"] >= 3
    assert all(item["status"] == "pending_approval" for item in result["items"])
    assert all(item["total_amount"] >= 10_000 for item in result["items"])
    # Results are ordered by value so the biggest exposure is presented first.
    amounts = [item["total_amount"] for item in result["items"]]
    assert amounts == sorted(amounts, reverse=True)


def test_evaluate_invoice_explains_blockers(store: FinanceDataStore) -> None:
    evaluation = ap_tools.evaluate_invoice("INV-1047", store=store)
    assert evaluation["found"] is True
    assert evaluation["recommendation"] == "hold"
    assert "duplicate_suspected" in evaluation["blockers"]
    assert evaluation["duplicate_check"]["candidates"][0]["invoice_id"] == "INV-1031"


def test_duplicate_detection_requires_two_signals(store: FinanceDataStore) -> None:
    result = ap_tools.detect_duplicate_invoice("INV-1047", store=store)
    assert result["is_duplicate"] is True
    assert all(len(candidate["signals"]) >= 2 for candidate in result["candidates"])
    assert result["control"] == "FIN-SOX-AP-03"


def test_approve_invoice_blocks_when_exceptions_are_open(store: FinanceDataStore) -> None:
    result = ap_tools.approve_invoice("INV-1047", approver="cfo@contoso.com", store=store)
    assert result["approved"] is False
    assert store.get_invoice("INV-1047")["status"] == "blocked"


def test_approve_invoice_records_the_human_approver(store: FinanceDataStore) -> None:
    invoice = next(inv for inv in store.invoices if inv["status"] == "pending_approval" and not inv["exceptions"])
    result = ap_tools.approve_invoice(invoice["invoice_id"], approver="controller@contoso.com", store=store)
    assert result["approved"] is True
    updated = store.get_invoice(invoice["invoice_id"])
    assert updated["status"] == "approved"
    assert updated["approver"] == "controller@contoso.com"
    assert updated["approval_history"][-1]["decision"] == "approved"


def test_bulk_approve_skips_invoices_with_exceptions(store: FinanceDataStore) -> None:
    result = ap_tools.bulk_approve_invoices(max_amount=2_000, store=store)
    assert result["count"] >= 1
    for invoice_id in result["approved"]:
        invoice = store.get_invoice(invoice_id)
        assert invoice["status"] == "approved"
        assert invoice["total_amount"] < 2_000
        assert not invoice["exceptions"]
    for skipped in result["skipped"]:
        assert store.get_invoice(skipped["invoice_id"])["status"] != "approved"


def test_posting_requires_approval_first(store: FinanceDataStore) -> None:
    invoice = next(inv for inv in store.invoices if inv["status"] == "pending_approval" and not inv["exceptions"])
    assert ap_tools.post_invoice_to_erp(invoice["invoice_id"], store=store)["posted"] is False
    ap_tools.approve_invoice(invoice["invoice_id"], store=store)
    posted = ap_tools.post_invoice_to_erp(invoice["invoice_id"], store=store)
    assert posted["posted"] is True
    assert posted["erp_document_id"].startswith("ERP-AP-")


def test_validate_vendor_rejects_non_approved_suppliers(store: FinanceDataStore) -> None:
    blocked_vendor = next(vendor for vendor in store.vendors if vendor["status"] != "approved")
    result = ap_tools.validate_vendor(vendor_id=blocked_vendor["vendor_id"], store=store)
    assert result["valid"] is False
    assert ap_tools.validate_vendor(vendor_name="Not A Real Vendor", store=store)["reason"] == "vendor_not_found"


def test_ap_metrics_are_internally_consistent(store: FinanceDataStore) -> None:
    metrics = ap_tools.ap_metrics(store=store)
    assert metrics["total_invoices"] == len(store.invoices)
    assert 0 <= metrics["touchless_rate"] <= 1
    assert 0 <= metrics["exception_rate"] <= 1
    assert metrics["total_spend"] > 0
