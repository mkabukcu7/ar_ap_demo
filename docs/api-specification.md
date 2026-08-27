# Finance Operations API Specification

Base URL (local): `http://localhost:8000` · Interactive OpenAPI: `http://localhost:8000/docs` ·
Machine-readable schema: `http://localhost:8000/openapi.json`

All responses are JSON. Amounts are numbers in the currency of the record (`USD` in the sample
dataset). In Azure deployments the API sits behind Microsoft Entra ID; the authenticated user
identity is what is recorded as the approver on any write action.

## System

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Liveness plus the active mode (`local` / `foundry`), model deployment and dataset size |

```json
{"status":"ok","mode":"local","model_deployment":"gpt-5.4","invoice_count":50,"knowledge_documents":5}
```

## Metrics

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/metrics/ap` | Invoice counts, touchless rate, exception rate, average cycle time, total spend |
| GET | `/api/metrics/ar` | Open AR, aging, DSO, past due rate, unapplied cash, collections at risk |
| GET | `/api/pipeline` | Invoice counts by pipeline stage (received → posted, plus blocked) |

## Accounts Payable

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/invoices` | Search invoices. Query: `status`, `min_amount`, `max_amount`, `vendor_id`, `has_exceptions`, `limit` |
| GET | `/api/invoices/{invoice_id}` | Invoice with vendor, purchase order and required approvals. `404` if unknown |
| GET | `/api/invoices/{invoice_id}/evaluation` | Full validation chain: PO match, duplicate check, vendor check, blockers, recommendation |
| POST | `/api/invoices/{invoice_id}/approve` | Record a human approval. Body: `{"approver": "...", "force": false}` |
| POST | `/api/approvals/bulk` | Body: `{"max_amount": 2000, "require_no_exceptions": true, "approver": "..."}` |
| POST | `/api/invoices/{invoice_id}/post` | Simulate ERP posting; requires `approved` status |
| GET | `/api/vendors` | Vendor master |
| GET | `/api/purchase-orders` | Purchase orders with remaining balances |

`status` is one of `received`, `extracted`, `validated`, `matched`, `pending_approval`, `approved`,
`posted`, `blocked`. An unknown value returns `422`.

**Invoice object**

```json
{
  "invoice_id": "INV-1047",
  "vendor_id": "VEN-2002",
  "vendor_name": "Contoso Cloud Services",
  "invoice_number": "CONT-9047",
  "invoice_date": "2026-02-14",
  "received_date": "2026-02-16",
  "due_date": "2026-03-16",
  "currency": "USD",
  "subtotal": 44572.98,
  "tax_amount": 3677.02,
  "total_amount": 48250.0,
  "po_number": "PO-7001",
  "cost_center": "CC-101",
  "status": "blocked",
  "approver": "j.rivera@contoso.com",
  "approval_history": [],
  "exceptions": [{"code": "PO_AMOUNT_MISMATCH", "severity": "high", "message": "…"}],
  "line_items": [{"description": "…", "quantity": 4, "unit_price": 1234.56, "amount": 4938.24}],
  "source_document": "sample-data/invoices/documents/INV-1047.txt",
  "extraction_confidence": 0.93,
  "erp_document_id": null
}
```

**Approval semantics (control FIN-SOX-AI-01)**

- An invoice with open exceptions is **not** approved unless `force: true` is supplied with a
  documented reason.
- Approval records the approver identity and the approval levels the policy requires for the value.
- Posting requires `approved` status and returns the ERP document id.

## Accounts Receivable

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/ar/remittances` | Search remittances. Query: `status`, `customer_id`, `limit` |
| GET | `/api/ar/remittances/{remittance_id}` | Match explanation, applied invoices, residual and candidate invoices |
| GET | `/api/ar/unapplied` | Unapplied cash, largest first, with `total_unapplied` |
| GET | `/api/ar/collections` | Prioritised collection worklist with recommended dunning action |
| GET | `/api/ar/discrepancies` | Payment matching exceptions ranked by cash impact |

`status` is `applied`, `partially_applied` or `unapplied`.

## Exceptions

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/exceptions` | Combined AP and AR exception queue. Query: `severity` (`low`/`medium`/`high`), `domain` (`ap`/`ar`) |

## Finance knowledge

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/knowledge/search` | Grounded retrieval over the policy corpus. Query: `q` (required, ≥ 2 chars), `top` (1–10) |

## Agents

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/agents` | Orchestrator and child agent definitions with their registered tools |
| GET | `/api/agents/activity` | Agent activity feed (most recent first). Query: `limit` (1–200) |
| GET | `/api/agents/prompts` | The seven scripted demo prompts |
| POST | `/api/chat` | Ask the Finance Orchestrator a question |

**Chat request**

```json
{"message": "Why is invoice INV-1047 blocked?", "session_id": "demo", "approver": "cfo@contoso.com"}
```

**Chat response**

```json
{
  "reply": "**Invoice INV-1047 …**",
  "citations": [{"title": "SOX Controls Guide — Purchase to Pay Controls", "source": "sample-data/knowledge/sox-controls-guide.md", "snippet": "…"}],
  "agent_trace": [{"agent": "Finance Orchestrator", "tool": "plan", "summary": "Routed to AP Agent"}],
  "data": {"…": "tool output for the dashboard to render"},
  "session_id": "demo"
}
```

Actions that move money are two-step: the orchestrator returns a proposal with
`data.requires_confirmation = true`, and the caller sends `confirm` on the **same** `session_id` to
execute it. Pending confirmations are scoped per session.

## Errors

| Status | Meaning |
| --- | --- |
| 404 | Unknown invoice, remittance or document id |
| 422 | Request validation failure (bad enum, negative amount, empty chat message) |
| 403 | Write actions disabled (`FINANCE_ENABLE_WRITE_ACTIONS=false`) |

## Function-tool contract

The API and the Azure AI Foundry agents call the same 19 tools registered in
`src/tools/registry.py`. `TOOL_SCHEMAS` is the JSON schema list registered with the Azure AI Agent
Service, so `infra/foundry/agents/*.agent.yaml` and the Python implementations never diverge.
