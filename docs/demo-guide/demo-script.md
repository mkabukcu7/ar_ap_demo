# Finance Operations Command Center — End-to-End Demo Script

**Duration:** 20 minutes · **Audience:** CFO, Finance Transformation Leader, Controller, Shared
Services Leader, Finance Operations team · **Mode:** runs fully offline (`FINANCE_AGENT_MODE=local`)
against the committed sample data, or on Azure AI Foundry with `gpt-5.4`.

## Before you start

```bash
pip install -r requirements-dev.txt
python -m src.data.generate_sample_data --output sample-data   # optional, data is committed
uvicorn src.api.main:app --reload --port 8000

cd ui/webapp && npm install && npm run dev                     # http://localhost:5173
```

Sanity check: `curl http://localhost:8000/api/health` returns 50 invoices and 5 knowledge documents.

You can run every demo from the **Finance Copilot** chat panel in the dashboard, or from the API:

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Why is invoice INV-1047 blocked?","session_id":"demo"}' | jq -r .reply
```

## Opening (2 minutes)

> "This is the Finance Operations Command Center. One orchestrator agent, five specialists, and a
> single pane of glass over accounts payable, accounts receivable and finance policy. Everything you
> see is grounded in the finance data and the approved policy set — and every action that moves
> money stays behind a human approval."

Point at the dashboard: **Invoice Pipeline**, **AP Metrics**, **AR Metrics**, **Cash Application
Status**, **Exception Queue**, **Agent Activity Feed**.

Talking points: 50 invoices in flight, touchless rate versus the 70% target, the exception queue
value at risk, and DSO against the 42-day target.

---

## Demo 1 — Working the approval queue

**Ask:** `Show invoices awaiting approval over $10,000`

**What happens:** the orchestrator routes to the **AP Agent**, which calls `search_invoices`
(`status=pending_approval`, `min_amount=10000`) and returns the queue ranked by value with vendor,
PO, approver and exception state.

**Say:** "Highest exposure first. Each row is match-complete with an identified approver, so the
controller can work the queue by value rather than by arrival order."

---

## Demo 2 — Explaining a blocked invoice

**Ask:** `Why is invoice INV-1047 blocked?`

**What happens:** the AP Agent runs the full evidence chain — `get_invoice`, `match_invoice_to_po`,
`detect_duplicate_invoice`, `validate_vendor` — and explains both blockers: the invoice total exceeds
the remaining PO balance, and it is a suspected duplicate of the already-posted **INV-1031** (same
vendor, same amount, same PO).

**Say:** "This is a five-figure duplicate payment that would have been caught late, if at all. The
agent names the control — FIN-SOX-AP-03 — and the exact next action for the AP supervisor."

---

## Demo 3 — Human-in-the-loop bulk approval

**Ask:** `Approve all invoices under $2,000 with no exceptions`

**What happens:** the orchestrator returns a **proposal**, not an action: the eligible invoices, the
total value, and a request for confirmation under control FIN-SOX-AI-01.

**Then type:** `confirm`

The AP Agent approves each invoice, records the approver identity and timestamp, and reports the
invoices it deliberately held back because they carry open exceptions.

**Say:** "The agent prepares; the human decides. Nothing was approved until you confirmed, and the
approval log is the audit evidence."

---

## Demo 4 — Where is our cash?

**Ask:** `What cash remains unapplied?`

**What happens:** the **AR Agent** calls `list_unapplied_cash` and returns every payment with a
residual, largest first, with the root cause (`NO_REMITTANCE_REFERENCE`, `INVOICE_NOT_FOUND`,
`OVERPAYMENT`, `SHORT_PAYMENT`, `DEDUCTION_TAKEN`) and the policy clearing timeline.

**Say:** "That is real working capital sitting in a suspense account. Policy says research in two
days and clear in ten; the agent shows exactly which payments breach that."

---

## Demo 5 — Cash application exceptions by impact

**Ask:** `Show the largest payment matching exceptions`

**What happens:** `payment_discrepancies` ranks the exceptions by cash impact, flags which residuals
are small-balance write-off eligible, and recommends the next action.

**Say:** "The team works the top of this list. One customer here accounts for most of the exposure."

---

## Demo 6 — Policy plus live exposure

**Ask:** `What approvals are required for invoices over $25,000?`

**What happens:** two agents in one answer. The **Finance Policy Agent** retrieves the delegation of
authority matrix from the Accounts Payable Policy with a citation; the **AP Agent** adds the live
exposure — how many invoices above that threshold are waiting and for how much.

**Say:** "Policy and position in a single answer. This is what removes the email round trip between
the controller and the shared services team."

---

## Demo 7 — Audit-ready policy answer

**Ask:** `What SOX control governs invoice approvals?`

**What happens:** the Finance Policy Agent returns **FIN-SOX-AP-01** — objective, description,
frequency and control owner — with a citation to the SOX Controls Guide. Open the **Citations**
section in the chat panel to show the source path and section.

**Say:** "Grounded, cited, and reproducible. Control FIN-SOX-AI-03 requires that an answer used as
audit evidence names its source; an ungrounded answer is refused, not guessed."

---

## Closing (2 minutes)

Show the **Agent Activity Feed**: every extraction, validation, exception, approval and posting is
logged with agent, action, timestamp and status — the same telemetry that flows to Application
Insights in the deployed architecture.

**Value framing**

| Metric | Baseline | With the accelerator |
| --- | --- | --- |
| Touchless invoice rate | 40–55% | 70%+ target, exceptions routed automatically |
| Invoice cycle time | 8–12 days | ≤ 4 days |
| Duplicate payment leakage | 0.05–0.1% of spend | Blocked pre-payment (FIN-SOX-AP-03) |
| Unapplied cash | 3–5% of collections | ≤ 1.5% target with daily agent triage |
| Policy question turnaround | Hours to days | Seconds, with citations |

**Close:** "Every agent instruction, prompt, tool and infrastructure template in this demo is in the
repository. The same code runs offline for a demo and on Azure AI Foundry with Entra ID, Purview and
Application Insights for a production pilot."

## Recovery notes

| Situation | Action |
| --- | --- |
| The dashboard shows a **Demo Data** badge | The API is not running; start `uvicorn src.api.main:app --port 8000`. |
| Demo 3 shows nothing to approve | You already ran it in this session; restart the API to reload the dataset. |
| Data looks stale after several demos | `python -m src.data.generate_sample_data --output sample-data`, then restart the API. |
| No network | Nothing to do — `FINANCE_AGENT_MODE=local` is the default and needs no Azure connectivity. |
