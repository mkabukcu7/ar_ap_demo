"""Synthetic finance operations dataset generator.

Generates a deterministic, realistic dataset for the Finance Operations Agent
Accelerator: vendors, purchase orders, AP invoices, customers, AR invoices and
customer remittances.

The generator is deterministic (fixed seed) so that the committed sample data,
the demo script and the automated tests always agree.

Usage::

    python -m src.data.generate_sample_data --output sample-data
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SEED = 20240501
BASE_DATE = date(2026, 3, 31)

CURRENCY = "USD"

VENDOR_CATALOG: list[dict[str, Any]] = [
    {"name": "Northwind Facilities Group", "category": "Facilities", "status": "approved"},
    {"name": "Contoso Cloud Services", "category": "IT & Cloud", "status": "approved"},
    {"name": "Fabrikam Logistics", "category": "Logistics", "status": "approved"},
    {"name": "Litware Professional Services", "category": "Professional Services", "status": "approved"},
    {"name": "Adventure Works Supply", "category": "Indirect Materials", "status": "approved"},
    {"name": "Tailwind Traders Hardware", "category": "Hardware", "status": "approved"},
    {"name": "Proseware Marketing", "category": "Marketing", "status": "pending_review"},
    {"name": "Wide World Importers", "category": "Indirect Materials", "status": "approved"},
    {"name": "Woodgrove Advisory LLP", "category": "Professional Services", "status": "approved"},
    {"name": "Relecloud Data Centers", "category": "IT & Cloud", "status": "approved"},
    {"name": "VanArsdel Print & Media", "category": "Marketing", "status": "blocked"},
    {"name": "Lamna Healthcare Staffing", "category": "Contingent Labor", "status": "approved"},
]

CUSTOMER_CATALOG: list[dict[str, Any]] = [
    {"name": "Alpine Ski House", "segment": "Retail", "risk": "low"},
    {"name": "Bellows College", "segment": "Education", "risk": "low"},
    {"name": "Coho Vineyard", "segment": "Hospitality", "risk": "medium"},
    {"name": "First Up Consultants", "segment": "Services", "risk": "medium"},
    {"name": "Margie's Travel", "segment": "Travel", "risk": "high"},
    {"name": "Nod Publishers", "segment": "Media", "risk": "low"},
    {"name": "Trey Research", "segment": "Life Sciences", "risk": "medium"},
    {"name": "Fourth Coffee", "segment": "Retail", "risk": "high"},
]

LINE_ITEM_CATALOG: dict[str, list[str]] = {
    "Facilities": ["Janitorial services", "HVAC maintenance", "Security services", "Landscaping"],
    "IT & Cloud": ["Cloud consumption", "Software subscription", "Managed detection & response", "Data platform support"],
    "Logistics": ["Inbound freight", "Outbound freight", "Warehouse handling", "Customs brokerage"],
    "Professional Services": ["Advisory hours", "Statutory audit fees", "Tax compliance", "Project management"],
    "Indirect Materials": ["Office supplies", "Packaging materials", "Safety equipment", "Lab consumables"],
    "Hardware": ["Laptops", "Network switches", "Monitors", "Docking stations"],
    "Marketing": ["Campaign production", "Media placement", "Event sponsorship", "Creative retainer"],
    "Contingent Labor": ["Contract nursing hours", "Temporary staffing", "Recruiting fees", "Onboarding services"],
}

EXCEPTION_LIBRARY: dict[str, dict[str, str]] = {
    "PO_MISSING": {"severity": "medium", "message": "No purchase order referenced on a PO-required invoice."},
    "PO_AMOUNT_MISMATCH": {"severity": "high", "message": "Invoice total exceeds the remaining purchase order balance."},
    "DUPLICATE_SUSPECTED": {"severity": "high", "message": "Potential duplicate of a previously submitted invoice."},
    "VENDOR_NOT_APPROVED": {"severity": "high", "message": "Vendor is not in an approved status in the vendor master."},
    "TAX_VARIANCE": {"severity": "low", "message": "Calculated tax differs from the extracted tax amount."},
    "LOW_CONFIDENCE_EXTRACTION": {"severity": "medium", "message": "Document extraction confidence is below the straight-through threshold."},
    "PRICE_VARIANCE": {"severity": "medium", "message": "Unit price exceeds the contracted price by more than tolerance."},
}

AR_EXCEPTION_LIBRARY: dict[str, dict[str, str]] = {
    "SHORT_PAYMENT": {"severity": "medium", "message": "Payment received is less than the open invoice balance."},
    "OVERPAYMENT": {"severity": "low", "message": "Payment received exceeds the referenced invoice balance."},
    "NO_REMITTANCE_REFERENCE": {"severity": "high", "message": "Remittance advice contains no usable invoice reference."},
    "INVOICE_NOT_FOUND": {"severity": "high", "message": "Referenced invoice number does not exist in the AR sub-ledger."},
    "DEDUCTION_TAKEN": {"severity": "medium", "message": "Customer deducted an unauthorised discount or claim."},
}

APPROVERS = [
    "j.rivera@contoso.com",
    "s.okafor@contoso.com",
    "m.laurent@contoso.com",
    "d.chen@contoso.com",
]


def _money(value: float) -> float:
    return round(value + 0.0, 2)


def _iso(value: date) -> str:
    return value.isoformat()


def build_vendors() -> list[dict[str, Any]]:
    vendors = []
    for index, entry in enumerate(VENDOR_CATALOG, start=1):
        vendors.append(
            {
                "vendor_id": f"VEN-{2000 + index}",
                "name": entry["name"],
                "category": entry["category"],
                "status": entry["status"],
                "tax_id": f"98-{4000000 + index * 137:07d}",
                "payment_terms": ["NET30", "NET45", "NET60"][index % 3],
                "bank_account_last4": f"{1000 + index * 7:04d}",
                "country": "US",
                "po_required": entry["category"] not in {"Professional Services", "Marketing"},
                "onboarded_on": _iso(date(2021, 1, 1) + timedelta(days=index * 53)),
            }
        )
    return vendors


def build_customers() -> list[dict[str, Any]]:
    customers = []
    for index, entry in enumerate(CUSTOMER_CATALOG, start=1):
        customers.append(
            {
                "customer_id": f"CUST-{5000 + index}",
                "name": entry["name"],
                "segment": entry["segment"],
                "credit_risk": entry["risk"],
                "payment_terms": ["NET30", "NET45", "NET60"][index % 3],
                "credit_limit": 250_000 + index * 25_000,
                "collector": APPROVERS[index % len(APPROVERS)],
            }
        )
    return customers


def _line_items(rng: random.Random, category: str, target_total: float) -> list[dict[str, Any]]:
    descriptions = LINE_ITEM_CATALOG[category]
    count = rng.randint(1, 3)
    chosen = rng.sample(descriptions, k=min(count, len(descriptions)))
    weights = [rng.uniform(0.5, 1.5) for _ in chosen]
    weight_total = sum(weights)
    items = []
    allocated = 0.0
    for position, (description, weight) in enumerate(zip(chosen, weights)):
        if position == len(chosen) - 1:
            amount = _money(target_total - allocated)
        else:
            amount = _money(target_total * weight / weight_total)
            allocated += amount
        quantity = rng.choice([1, 2, 4, 5, 10, 12])
        items.append(
            {
                "description": description,
                "quantity": quantity,
                "unit_price": _money(amount / quantity),
                "amount": amount,
            }
        )
    return items


def build_purchase_orders(rng: random.Random, vendors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    purchase_orders = []
    for index in range(1, 41):
        vendor = vendors[index % len(vendors)]
        amount = _money(rng.choice([1_800, 4_500, 9_800, 14_200, 22_500, 38_000, 61_000]) * rng.uniform(0.85, 1.2))
        po_date = BASE_DATE - timedelta(days=rng.randint(40, 200))
        purchase_orders.append(
            {
                "po_number": f"PO-{7000 + index}",
                "vendor_id": vendor["vendor_id"],
                "vendor_name": vendor["name"],
                "po_date": _iso(po_date),
                "currency": CURRENCY,
                "amount": amount,
                "received_amount": _money(amount * rng.uniform(0.6, 1.0)),
                "invoiced_amount": 0.0,
                "remaining_amount": amount,
                "status": "open",
                "cost_center": f"CC-{100 + (index % 12)}",
                "line_items": _line_items(rng, vendor["category"], amount),
            }
        )
    return purchase_orders


def _pipeline_status(rng: random.Random, exceptions: list[dict[str, Any]], total: float) -> str:
    if exceptions and any(item["severity"] == "high" for item in exceptions):
        return "blocked"
    roll = rng.random()
    if roll < 0.12:
        return "received"
    if roll < 0.22:
        return "extracted"
    if roll < 0.32:
        return "validated"
    if roll < 0.42:
        return "matched"
    if roll < 0.72:
        return "pending_approval"
    if roll < 0.88:
        return "approved"
    return "posted"


def build_invoices(
    rng: random.Random,
    vendors: list[dict[str, Any]],
    purchase_orders: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    invoices: list[dict[str, Any]] = []
    po_by_vendor: dict[str, list[dict[str, Any]]] = {}
    for order in purchase_orders:
        po_by_vendor.setdefault(order["vendor_id"], []).append(order)

    for index in range(1, 51):
        invoice_id = f"INV-{1000 + index}"
        vendor = vendors[rng.randrange(len(vendors))]
        category = vendor["category"]
        subtotal = _money(rng.choice([850, 1_450, 1_920, 3_400, 7_600, 11_500, 18_400, 26_900, 44_000]) * rng.uniform(0.8, 1.25))
        tax_amount = _money(subtotal * 0.0825)
        total_amount = _money(subtotal + tax_amount)

        invoice_date = BASE_DATE - timedelta(days=rng.randint(3, 75))
        received_date = invoice_date + timedelta(days=rng.randint(0, 5))
        terms_days = int(vendor["payment_terms"].replace("NET", ""))
        due_date = invoice_date + timedelta(days=terms_days)

        candidate_pos = po_by_vendor.get(vendor["vendor_id"], [])
        purchase_order = rng.choice(candidate_pos) if candidate_pos and rng.random() > 0.18 else None
        po_number = purchase_order["po_number"] if purchase_order else None

        extraction_confidence = round(rng.uniform(0.72, 0.99), 3)

        exceptions: list[dict[str, Any]] = []
        if po_number is None and vendor["po_required"]:
            exceptions.append(_exception("PO_MISSING"))
        if purchase_order and total_amount > purchase_order["remaining_amount"]:
            exceptions.append(_exception("PO_AMOUNT_MISMATCH"))
        if vendor["status"] != "approved":
            exceptions.append(_exception("VENDOR_NOT_APPROVED"))
        if extraction_confidence < 0.80:
            exceptions.append(_exception("LOW_CONFIDENCE_EXTRACTION"))
        if rng.random() < 0.08:
            exceptions.append(_exception("PRICE_VARIANCE"))

        status = _pipeline_status(rng, exceptions, total_amount)

        invoices.append(
            {
                "invoice_id": invoice_id,
                "vendor_id": vendor["vendor_id"],
                "vendor_name": vendor["name"],
                "invoice_number": f"{vendor['name'].split()[0].upper()[:4]}-{9000 + index}",
                "invoice_date": _iso(invoice_date),
                "received_date": _iso(received_date),
                "due_date": _iso(due_date),
                "currency": CURRENCY,
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "total_amount": total_amount,
                "po_number": po_number,
                "cost_center": purchase_order["cost_center"] if purchase_order else f"CC-{100 + (index % 12)}",
                "status": status,
                "approver": APPROVERS[index % len(APPROVERS)],
                "approval_history": [],
                "exceptions": exceptions,
                "line_items": _line_items(rng, category, subtotal),
                "source_document": f"sample-data/invoices/documents/{invoice_id}.txt",
                "extraction_confidence": extraction_confidence,
                "erp_document_id": None,
            }
        )

    _apply_demo_invariants(rng, invoices, vendors, purchase_orders)
    return invoices


def _exception(code: str) -> dict[str, Any]:
    entry = EXCEPTION_LIBRARY[code]
    return {"code": code, "severity": entry["severity"], "message": entry["message"]}


def _ar_exception(code: str) -> dict[str, Any]:
    entry = AR_EXCEPTION_LIBRARY[code]
    return {"code": code, "severity": entry["severity"], "message": entry["message"]}


def _apply_demo_invariants(
    rng: random.Random,
    invoices: list[dict[str, Any]],
    vendors: list[dict[str, Any]],
    purchase_orders: list[dict[str, Any]],
) -> None:
    """Guarantee the scripted demo questions always have a compelling answer."""

    by_id = {invoice["invoice_id"]: invoice for invoice in invoices}

    # Demo 2 — "Why is invoice INV-1047 blocked?"
    blocked = by_id["INV-1047"]
    blocked["status"] = "blocked"
    blocked["total_amount"] = 48_250.00
    blocked["subtotal"] = 44_572.98
    blocked["tax_amount"] = 3_677.02
    blocked["po_number"] = purchase_orders[0]["po_number"]
    blocked["vendor_id"] = purchase_orders[0]["vendor_id"]
    blocked["vendor_name"] = purchase_orders[0]["vendor_name"]
    blocked["exceptions"] = [_exception("PO_AMOUNT_MISMATCH"), _exception("DUPLICATE_SUSPECTED")]
    blocked["duplicate_of"] = "INV-1031"
    blocked["line_items"] = _line_items(rng, "Facilities", blocked["subtotal"])

    duplicate_source = by_id["INV-1031"]
    duplicate_source["vendor_id"] = blocked["vendor_id"]
    duplicate_source["vendor_name"] = blocked["vendor_name"]
    duplicate_source["total_amount"] = 48_250.00
    duplicate_source["subtotal"] = 44_572.98
    duplicate_source["tax_amount"] = 3_677.02
    duplicate_source["po_number"] = blocked["po_number"]
    duplicate_source["status"] = "posted"
    duplicate_source["exceptions"] = []
    duplicate_source["erp_document_id"] = "ERP-AP-880031"

    protected = {"INV-1047", "INV-1031"}

    # Demo 1 — a healthy set of invoices awaiting approval above $10,000.
    high_value = [
        inv
        for inv in invoices
        if inv["total_amount"] > 10_000 and inv["invoice_id"] not in protected
    ]
    for invoice in high_value[:6]:
        invoice["exceptions"] = []
        invoice["status"] = "pending_approval"

    # Demo 3 — at least five clean invoices below $2,000 awaiting approval.
    low_value = [inv for inv in invoices if inv["total_amount"] < 2_000 and inv["invoice_id"] not in protected]
    for invoice in low_value[:5]:
        invoice["exceptions"] = []
        invoice["status"] = "pending_approval"

    # Demo 6 — at least three invoices above $25,000 awaiting approval.
    executive = [
        inv
        for inv in invoices
        if inv["total_amount"] > 25_000 and inv["status"] != "blocked" and inv["invoice_id"] not in protected
    ]
    for invoice in executive[:4]:
        invoice["exceptions"] = []
        invoice["status"] = "pending_approval"

    # Posted invoices always carry the ERP document reference written back by posting.
    for invoice in invoices:
        if invoice["status"] == "posted" and not invoice["erp_document_id"]:
            invoice["erp_document_id"] = f"ERP-AP-{880000 + int(invoice['invoice_id'].split('-')[1])}"

    # Keep purchase order balances consistent with what has been invoiced.
    po_by_number = {order["po_number"]: order for order in purchase_orders}
    for invoice in invoices:
        order = po_by_number.get(invoice["po_number"] or "")
        if order and invoice["status"] in {"approved", "posted"}:
            order["invoiced_amount"] = _money(order["invoiced_amount"] + invoice["total_amount"])
    for order in purchase_orders:
        order["remaining_amount"] = _money(max(order["amount"] - order["invoiced_amount"], 0.0))
        if order["remaining_amount"] <= 0:
            order["status"] = "closed"


def build_ar_invoices(rng: random.Random, customers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ar_invoices = []
    for index in range(1, 41):
        customer = customers[index % len(customers)]
        amount = _money(rng.choice([4_800, 12_400, 23_900, 41_500, 68_000]) * rng.uniform(0.8, 1.2))
        issue_date = BASE_DATE - timedelta(days=rng.randint(5, 120))
        terms_days = int(customer["payment_terms"].replace("NET", ""))
        due_date = issue_date + timedelta(days=terms_days)
        days_past_due = max((BASE_DATE - due_date).days, 0)
        ar_invoices.append(
            {
                "ar_invoice_id": f"ARI-{3000 + index}",
                "customer_id": customer["customer_id"],
                "customer_name": customer["name"],
                "issue_date": _iso(issue_date),
                "due_date": _iso(due_date),
                "currency": CURRENCY,
                "amount": amount,
                "applied_amount": 0.0,
                "open_amount": amount,
                "days_past_due": days_past_due,
                "aging_bucket": _aging_bucket(days_past_due),
                "status": "open",
                "collector": customer["collector"],
            }
        )
    return ar_invoices


def _aging_bucket(days_past_due: int) -> str:
    if days_past_due <= 0:
        return "current"
    if days_past_due <= 30:
        return "1-30"
    if days_past_due <= 60:
        return "31-60"
    if days_past_due <= 90:
        return "61-90"
    return "90+"


def build_remittances(
    rng: random.Random,
    customers: list[dict[str, Any]],
    ar_invoices: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    remittances: list[dict[str, Any]] = []
    by_customer: dict[str, list[dict[str, Any]]] = {}
    for invoice in ar_invoices:
        by_customer.setdefault(invoice["customer_id"], []).append(invoice)

    for index in range(1, 26):
        customer = customers[index % len(customers)]
        open_invoices = [inv for inv in by_customer.get(customer["customer_id"], []) if inv["open_amount"] > 0]
        payment_date = BASE_DATE - timedelta(days=rng.randint(1, 45))
        exceptions: list[dict[str, Any]] = []
        matches: list[dict[str, Any]] = []

        scenario = rng.choices(
            ["full", "partial", "unapplied", "multi", "short"],
            weights=[0.28, 0.2, 0.2, 0.18, 0.14],
            k=1,
        )[0]

        if not open_invoices:
            scenario = "unapplied"

        if scenario == "unapplied":
            payment_amount = _money(rng.choice([5_200, 9_400, 18_750, 31_200]) * rng.uniform(0.9, 1.15))
            exceptions.append(_ar_exception(rng.choice(["NO_REMITTANCE_REFERENCE", "INVOICE_NOT_FOUND"])))
            applied_amount = 0.0
        elif scenario == "full":
            target = open_invoices[0]
            payment_amount = target["open_amount"]
            applied_amount = payment_amount
            matches.append(_match(target, applied_amount, 0.99))
        elif scenario == "partial":
            target = open_invoices[0]
            applied_amount = _money(target["open_amount"] * rng.uniform(0.35, 0.7))
            payment_amount = applied_amount
            matches.append(_match(target, applied_amount, 0.94))
        elif scenario == "short":
            target = open_invoices[0]
            applied_amount = _money(target["open_amount"] * rng.uniform(0.82, 0.95))
            payment_amount = applied_amount
            matches.append(_match(target, applied_amount, 0.9))
            exceptions.append(_ar_exception(rng.choice(["SHORT_PAYMENT", "DEDUCTION_TAKEN"])))
        else:  # multi-invoice payment with residual unapplied cash
            targets = open_invoices[:2]
            applied_amount = 0.0
            for target in targets:
                amount = target["open_amount"]
                matches.append(_match(target, amount, 0.97))
                applied_amount = _money(applied_amount + amount)
            payment_amount = _money(applied_amount + rng.choice([250, 1_400, 3_800]))
            exceptions.append(_ar_exception("OVERPAYMENT"))

        for match in matches:
            invoice = next(inv for inv in ar_invoices if inv["ar_invoice_id"] == match["ar_invoice_id"])
            invoice["applied_amount"] = _money(invoice["applied_amount"] + match["applied_amount"])
            invoice["open_amount"] = _money(max(invoice["amount"] - invoice["applied_amount"], 0.0))
            invoice["status"] = "paid" if invoice["open_amount"] <= 0.005 else "partially_paid"

        unapplied_amount = _money(max(payment_amount - applied_amount, 0.0))
        if unapplied_amount <= 0.005:
            status = "applied"
        elif applied_amount > 0:
            status = "partially_applied"
        else:
            status = "unapplied"

        remittance_id = f"RMT-{4000 + index}"
        remittances.append(
            {
                "remittance_id": remittance_id,
                "customer_id": customer["customer_id"],
                "customer_name": customer["name"],
                "payment_date": _iso(payment_date),
                "payment_reference": f"ACH-{600000 + index * 13}",
                "payment_method": rng.choice(["ACH", "Wire", "Check"]),
                "currency": CURRENCY,
                "payment_amount": payment_amount,
                "applied_amount": applied_amount,
                "unapplied_amount": unapplied_amount,
                "status": status,
                "matches": matches,
                "exceptions": exceptions,
                "source_document": f"sample-data/remittances/documents/{remittance_id}.txt",
            }
        )

    _apply_ar_demo_invariants(remittances)
    return remittances


def _match(invoice: dict[str, Any], applied_amount: float, confidence: float) -> dict[str, Any]:
    return {
        "ar_invoice_id": invoice["ar_invoice_id"],
        "customer_id": invoice["customer_id"],
        "applied_amount": _money(applied_amount),
        "confidence": confidence,
    }


def _apply_ar_demo_invariants(remittances: list[dict[str, Any]]) -> None:
    """Demos 4 and 5 need visible unapplied cash and a headline exception."""

    unapplied = [item for item in remittances if item["unapplied_amount"] > 0]
    if not unapplied:  # pragma: no cover - defensive, generator always creates some
        target = remittances[0]
        target["applied_amount"] = 0.0
        target["matches"] = []
        target["unapplied_amount"] = target["payment_amount"]
        target["status"] = "unapplied"
        target["exceptions"] = [_ar_exception("NO_REMITTANCE_REFERENCE")]
        unapplied = [target]

    headline = max(unapplied, key=lambda item: item["unapplied_amount"])
    headline["payment_amount"] = _money(headline["payment_amount"] + 125_000)
    headline["unapplied_amount"] = _money(headline["unapplied_amount"] + 125_000)
    headline["status"] = "partially_applied" if headline["applied_amount"] > 0 else "unapplied"
    if not headline["exceptions"]:
        headline["exceptions"] = [_ar_exception("NO_REMITTANCE_REFERENCE")]


INVOICE_DOCUMENT_TEMPLATE = """{vendor_name}
INVOICE

Invoice Number : {invoice_number}
Invoice ID     : {invoice_id}
Invoice Date   : {invoice_date}
Due Date       : {due_date}
Purchase Order : {po_number}
Bill To        : Contoso Corporation, Accounts Payable, Redmond WA

Line Items
{line_items}

Subtotal       : {subtotal:,.2f} {currency}
Tax            : {tax_amount:,.2f} {currency}
Total Due      : {total_amount:,.2f} {currency}

Remit payment per the terms agreed in the master services agreement.
"""

REMITTANCE_DOCUMENT_TEMPLATE = """{customer_name}
REMITTANCE ADVICE

Remittance ID    : {remittance_id}
Payment Date     : {payment_date}
Payment Method   : {payment_method}
Payment Reference: {payment_reference}
Payment Amount   : {payment_amount:,.2f} {currency}

Invoices Referenced
{references}

Questions regarding this payment should be directed to accounts payable.
"""


def _render_invoice_document(invoice: dict[str, Any]) -> str:
    lines = "\n".join(
        f"  {item['description']:<32} {item['quantity']:>4} x {item['unit_price']:>10,.2f} = {item['amount']:>12,.2f}"
        for item in invoice["line_items"]
    )
    return INVOICE_DOCUMENT_TEMPLATE.format(
        line_items=lines,
        po_number=invoice["po_number"] or "NOT PROVIDED",
        **{key: invoice[key] for key in (
            "vendor_name",
            "invoice_number",
            "invoice_id",
            "invoice_date",
            "due_date",
            "subtotal",
            "tax_amount",
            "total_amount",
            "currency",
        )},
    )


def _render_remittance_document(remittance: dict[str, Any]) -> str:
    if remittance["matches"]:
        references = "\n".join(
            f"  {match['ar_invoice_id']:<12} {match['applied_amount']:>12,.2f}" for match in remittance["matches"]
        )
    else:
        references = "  (no invoice references supplied on the remittance advice)"
    return REMITTANCE_DOCUMENT_TEMPLATE.format(
        references=references,
        **{key: remittance[key] for key in (
            "customer_name",
            "remittance_id",
            "payment_date",
            "payment_method",
            "payment_reference",
            "payment_amount",
            "currency",
        )},
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def generate(output_dir: Path, documents: bool = True) -> dict[str, Any]:
    rng = random.Random(SEED)

    vendors = build_vendors()
    customers = build_customers()
    purchase_orders = build_purchase_orders(rng, vendors)
    invoices = build_invoices(rng, vendors, purchase_orders)
    ar_invoices = build_ar_invoices(rng, customers)
    remittances = build_remittances(rng, customers, ar_invoices)

    _write_json(output_dir / "invoices" / "vendors.json", vendors)
    _write_json(output_dir / "invoices" / "purchase_orders.json", purchase_orders)
    _write_json(output_dir / "invoices" / "invoices.json", invoices)
    _write_json(output_dir / "remittances" / "customers.json", customers)
    _write_json(output_dir / "remittances" / "ar_invoices.json", ar_invoices)
    _write_json(output_dir / "remittances" / "remittances.json", remittances)

    if documents:
        invoice_docs = output_dir / "invoices" / "documents"
        invoice_docs.mkdir(parents=True, exist_ok=True)
        for invoice in invoices:
            (invoice_docs / f"{invoice['invoice_id']}.txt").write_text(
                _render_invoice_document(invoice), encoding="utf-8"
            )
        remittance_docs = output_dir / "remittances" / "documents"
        remittance_docs.mkdir(parents=True, exist_ok=True)
        for remittance in remittances:
            (remittance_docs / f"{remittance['remittance_id']}.txt").write_text(
                _render_remittance_document(remittance), encoding="utf-8"
            )

    return {
        "vendors": vendors,
        "purchase_orders": purchase_orders,
        "invoices": invoices,
        "customers": customers,
        "ar_invoices": ar_invoices,
        "remittances": remittances,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the finance operations sample dataset.")
    parser.add_argument("--output", default="sample-data", help="Output directory (default: sample-data)")
    parser.add_argument("--no-documents", action="store_true", help="Skip writing document facsimiles")
    args = parser.parse_args()

    dataset = generate(Path(args.output), documents=not args.no_documents)
    print(
        "Generated "
        f"{len(dataset['invoices'])} invoices, "
        f"{len(dataset['purchase_orders'])} purchase orders, "
        f"{len(dataset['vendors'])} vendors, "
        f"{len(dataset['ar_invoices'])} AR invoices, "
        f"{len(dataset['remittances'])} remittances "
        f"into {args.output}/"
    )


if __name__ == "__main__":
    main()
