# Accounts Payable Policy

Owner: Corporate Controller · Effective: 1 January 2026 · Review cycle: annual · Document ID: FIN-AP-001

## Purpose and Scope

This policy governs the receipt, validation, approval and payment of supplier invoices for all
Contoso Corporation entities. It applies to every invoice processed through the Accounts Payable
shared service centre, whether received by email, supplier portal, EDI or paper scan.

## Invoice Intake and Document Extraction

All invoices must be routed to the central AP intake channel. Invoices received directly by a
business owner must be forwarded to intake within two business days; direct payment outside the AP
process is prohibited.

Invoice documents are digitised and the following fields are extracted automatically: supplier name,
supplier tax identifier, invoice number, invoice date, purchase order number, currency, line item
detail, subtotal, tax and invoice total. Any field extracted with a confidence score below 0.80 must
be reviewed by an AP analyst before the invoice advances; this is recorded as a
`LOW_CONFIDENCE_EXTRACTION` exception.

## Three-Way Match Requirements

Invoices for goods and non-exempt services require a three-way match between the invoice, the
purchase order and the goods receipt. Matching tolerances are:

- Price tolerance: 2% of the purchase order unit price, capped at USD 500 per line.
- Quantity tolerance: 5% of the received quantity.
- Total tolerance: the invoice total may not exceed the remaining purchase order balance.

Invoices that breach a tolerance are raised as a `PO_AMOUNT_MISMATCH` or `PRICE_VARIANCE` exception
and routed to the requisitioner for disposition. Invoices without a purchase order for a
PO-required supplier are raised as `PO_MISSING` and cannot be paid until a retroactive purchase
order is created and approved.

## Approval Authority Matrix

Approval is required from the following levels, based on the gross invoice total in USD:

| Invoice total | Required approvals |
| --- | --- |
| Up to USD 2,000 | Straight-through processing when the invoice is fully matched and exception free; otherwise AP Analyst |
| USD 2,000.01 – USD 10,000 | Cost Centre Manager |
| USD 10,000.01 – USD 25,000 | Cost Centre Manager and Finance Director |
| USD 25,000.01 – USD 100,000 | Finance Director and Controller |
| Above USD 100,000 | Controller and Chief Financial Officer |

Invoices above USD 25,000 always require two distinct human approvers; agent-assisted approval is
advisory only and never replaces a human approval at these thresholds. No approver may approve an
invoice for which they are the requisitioner (segregation of duties).

## Duplicate Invoice Prevention

Candidate duplicates are identified when two invoices share a supplier and any two of: identical
invoice number, identical invoice total, invoice dates within five days, or the same purchase order
reference. Suspected duplicates are raised as a `DUPLICATE_SUSPECTED` exception, blocked from
payment and reviewed by an AP supervisor. Confirmed duplicates are cancelled with a documented
reason code and are never posted to the ERP.

## Vendor Validation

An invoice may only be paid to a supplier in `approved` status in the vendor master with a validated
tax identifier and validated bank details. Suppliers in `pending_review` or `blocked` status generate
a `VENDOR_NOT_APPROVED` exception. Bank detail changes require callback verification to a previously
known contact and are subject to control FIN-SOX-AP-04.

## Exception Handling and Service Levels

| Severity | Example | Resolution target |
| --- | --- | --- |
| High | Duplicate suspected, vendor not approved, PO amount mismatch | 1 business day |
| Medium | PO missing, price variance, low confidence extraction | 3 business days |
| Low | Tax variance | 5 business days |

## ERP Posting and Payment

Only approved, exception-free invoices are posted to the ERP. Posting creates an AP document number
which is written back to the invoice record. Payment runs execute twice weekly and honour the
supplier payment terms recorded in the vendor master. Early payment discounts are captured where the
discount exceeds the corporate cost of capital defined in the Treasury Policy.
