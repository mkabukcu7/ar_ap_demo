# SOX Controls Guide — Finance Operations

Owner: Director, Internal Controls · Effective: 1 January 2026 · Document ID: FIN-SOX-001

## Control Framework

Contoso operates a COSO-aligned internal control framework. Every control below is tested at least
annually by Internal Audit and, where automated, evidenced through system logs retained for seven
years. Agent-assisted automation does not change control ownership: the accountable control owner
remains a named human.

## Purchase to Pay Controls

| Control ID | Control objective | Description | Frequency | Owner |
| --- | --- | --- | --- | --- |
| FIN-SOX-AP-01 | Invoice approval authority | All supplier invoices are approved in the AP workflow in line with the delegation of authority matrix in the Accounts Payable Policy before payment is released. Approvals above USD 25,000 require two distinct human approvers and system-enforced segregation of duties. Evidence: workflow approval log. | Each transaction | Corporate Controller |
| FIN-SOX-AP-02 | Three-way match | Invoices for goods and non-exempt services are matched to the purchase order and goods receipt within documented tolerances before posting. | Each transaction | AP Manager |
| FIN-SOX-AP-03 | Duplicate payment prevention | Automated duplicate detection blocks candidate duplicate invoices from posting; a supervisor documents the disposition of every blocked item. | Each transaction | AP Manager |
| FIN-SOX-AP-04 | Vendor master integrity | Creation of, and bank detail changes to, vendor master records are independently verified by callback and approved by a second person. | Each change | Vendor Master Lead |
| FIN-SOX-AP-05 | AP sub-ledger reconciliation | The AP sub-ledger is reconciled to the general ledger with reconciling items aged and cleared. | Monthly | Controller |

## Order to Cash Controls

| Control ID | Control objective | Description | Frequency | Owner |
| --- | --- | --- | --- | --- |
| FIN-SOX-AR-01 | Cash application accuracy | Cash receipts are applied to customer accounts accurately and completely; automated matches below 0.90 confidence require analyst confirmation. | Each transaction | Cash Application Manager |
| FIN-SOX-AR-02 | Unapplied cash review | Unapplied cash is reviewed daily, aged, and cleared within policy; balances over 30 days are escalated. | Daily / Monthly | Director, Order to Cash |
| FIN-SOX-AR-03 | Credit memo and write-off approval | Credit memos and deduction write-offs are approved within the delegation of authority. | Each transaction | Controller |
| FIN-SOX-AR-04 | Allowance for credit losses | The allowance calculation is reviewed and approved with documented assumptions. | Quarterly | CFO |

## Controls over Agent-Assisted Automation

| Control ID | Control objective | Description |
| --- | --- | --- |
| FIN-SOX-AI-01 | Human in the loop | AI agents may recommend, summarise and prepare transactions. Financially significant actions — approval, posting, write-off, master data change — require an authenticated human decision recorded with the approver identity and timestamp. |
| FIN-SOX-AI-02 | Traceability | Every agent action is logged with the invoking user, agent name, tool called, inputs, outputs and correlation identifier, and is retained in Application Insights and the audit store. |
| FIN-SOX-AI-03 | Grounding and citation | Responses to policy questions must cite the underlying source document and section; ungrounded answers are not acceptable audit evidence. |
| FIN-SOX-AI-04 | Model and prompt change management | Model deployments, agent instructions and prompt templates are version controlled, peer reviewed and released through the standard change process. |

## Evidence and Audit Requests

Standard audit requests are served from the finance audit workspace. For a sampled invoice the
evidence pack contains: the source document, extracted fields with confidence scores, match result,
exception history, approval record with approver identity and timestamp, and the ERP posting
reference.
