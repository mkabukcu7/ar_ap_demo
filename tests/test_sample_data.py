"""The committed dataset must satisfy the invariants the demo script relies on."""

from __future__ import annotations

from src.data.store import FinanceDataStore

VALID_STATUSES = {
    "received", "extracted", "validated", "matched", "pending_approval", "approved", "posted", "blocked",
}


def test_dataset_shape(store: FinanceDataStore) -> None:
    assert len(store.invoices) == 50
    assert len(store.purchase_orders) == 40
    assert len(store.vendors) == 12
    assert len(store.remittances) == 25
    assert len({doc["document_id"] for doc in store.knowledge}) == 5


def test_invoice_records_are_well_formed(store: FinanceDataStore) -> None:
    ids = {invoice["invoice_id"] for invoice in store.invoices}
    assert len(ids) == 50
    for invoice in store.invoices:
        assert invoice["status"] in VALID_STATUSES
        assert invoice["total_amount"] > 0
        assert round(invoice["subtotal"] + invoice["tax_amount"], 2) == invoice["total_amount"]
        if invoice["po_number"]:
            assert store.get_purchase_order(invoice["po_number"]) is not None
        assert store.get_vendor(invoice["vendor_id"]) is not None


def test_posted_invoices_have_erp_reference(store: FinanceDataStore) -> None:
    posted = [invoice for invoice in store.invoices if invoice["status"] == "posted"]
    assert posted
    assert all(invoice["erp_document_id"] for invoice in posted)


def test_demo_invariants(store: FinanceDataStore) -> None:
    # Demo 1 — invoices awaiting approval over $10,000.
    assert len([i for i in store.invoices if i["status"] == "pending_approval" and i["total_amount"] > 10_000]) >= 3
    # Demo 2 — INV-1047 is blocked with explainable exceptions.
    blocked = store.get_invoice("INV-1047")
    assert blocked is not None and blocked["status"] == "blocked"
    assert {exc["code"] for exc in blocked["exceptions"]} >= {"DUPLICATE_SUSPECTED", "PO_AMOUNT_MISMATCH"}
    # Demo 3 — clean invoices under $2,000 available for bulk approval.
    assert len([i for i in store.invoices if i["total_amount"] < 2_000 and not i["exceptions"]]) >= 5
    # Demo 6 — invoices above the $25,000 executive threshold.
    assert len([i for i in store.invoices if i["total_amount"] > 25_000]) >= 3
    # Demos 4 and 5 — unapplied cash and payment exceptions exist.
    assert sum(rem["unapplied_amount"] for rem in store.remittances) > 0
    assert any(rem["exceptions"] for rem in store.remittances)


def test_remittance_amounts_reconcile(store: FinanceDataStore) -> None:
    for remittance in store.remittances:
        applied = round(sum(match["applied_amount"] for match in remittance["matches"]), 2)
        assert applied == round(remittance["applied_amount"], 2)
        assert round(remittance["applied_amount"] + remittance["unapplied_amount"], 2) == round(
            remittance["payment_amount"], 2
        )
