# Accounts Receivable and Cash Application Policy

Owner: Director, Order to Cash · Effective: 1 January 2026 · Review cycle: annual · Document ID: FIN-AR-001

## Purpose and Scope

This policy governs customer invoicing, cash application, deduction management and collections for
all Contoso Corporation entities.

## Cash Application Standards

Incoming payments are matched to open receivables using the remittance advice, the payment
reference and the payment amount. The cash application hierarchy is:

1. Exact match on a referenced invoice number and amount.
2. Multi-invoice match where the payment equals the sum of referenced open invoices.
3. Fuzzy match on customer, amount and payment date within a five day window.
4. Manual research by the cash application analyst.

A match is applied automatically only when the confidence score is at or above 0.90 and the residual
is zero. Payments applied below that threshold are queued for analyst confirmation.

## Unapplied Cash

Cash that cannot be matched within the hierarchy above is recorded as unapplied and reported daily.
Unapplied cash must be researched within two business days and cleared within ten business days.
Unapplied balances older than 30 days are escalated to the Director, Order to Cash and reviewed in
the monthly balance sheet review. Unapplied cash is never netted against an unrelated customer
balance.

Common root causes tracked as exceptions are:

- `NO_REMITTANCE_REFERENCE` — the remittance advice contains no usable invoice reference.
- `INVOICE_NOT_FOUND` — the referenced invoice does not exist in the sub-ledger.
- `OVERPAYMENT` — the payment exceeds the referenced invoice balance.
- `SHORT_PAYMENT` — the payment is less than the open balance.
- `DEDUCTION_TAKEN` — the customer applied an unauthorised discount or claim.

## Short Payments and Deductions

Short payments below USD 250 or 1% of the invoice value, whichever is lower, may be written off by
the cash application analyst. Larger short payments are logged as deductions, assigned to the
responsible business owner and must have a documented root cause before write-off. Deduction
write-offs above USD 10,000 require Controller approval.

## Collections Prioritisation

Collection activity is prioritised using a weighted score of open balance, days past due, customer
credit risk and disputed status. The standard dunning cadence is:

| Aging bucket | Action |
| --- | --- |
| Current | Statement only |
| 1–30 days | Automated reminder |
| 31–60 days | Collector call and email |
| 61–90 days | Escalation to account executive, credit hold review |
| 90+ days | Credit hold, escalation to Controller, potential third-party placement |

## Key Metrics

Days Sales Outstanding (DSO) is measured monthly on a countback basis. Targets are DSO at or below
42 days, unapplied cash at or below 1.5% of monthly collections, and past-due receivables at or
below 12% of the open ledger.
