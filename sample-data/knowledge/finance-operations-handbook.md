# Finance Operations Handbook

Owner: VP, Finance Shared Services · Effective: 1 January 2026 · Document ID: FIN-OPS-001

## Operating Model

Finance Operations runs a global shared services model covering purchase to pay, order to cash,
record to report support and master data. Work is routed through a single intake with a tiered
service model: Tier 1 automation and self-service, Tier 2 analyst resolution, Tier 3 specialist and
policy escalation.

## Roles and Responsibilities

| Role | Responsibilities |
| --- | --- |
| AP Analyst | Resolves invoice exceptions, validates extracted data, prepares invoices for approval |
| AP Supervisor | Dispositions duplicates, approves write-offs within limits, monitors service levels |
| Cash Application Analyst | Applies payments, researches unapplied cash, logs deductions |
| Collector | Executes the dunning cadence, negotiates payment plans within policy |
| Vendor Master Lead | Owns supplier record integrity and bank detail verification |
| Controller | Owns the control environment, approves exceptions above analyst limits |

## Service Level Objectives

| Process | Metric | Target |
| --- | --- | --- |
| Invoice processing | Straight-through (touchless) rate | ≥ 70% |
| Invoice processing | Average cycle time, receipt to approval | ≤ 4 days |
| Invoice processing | Exception rate | ≤ 15% |
| Cash application | Auto-match rate | ≥ 85% |
| Cash application | Unapplied cash as % of collections | ≤ 1.5% |
| Collections | DSO | ≤ 42 days |
| Period close | AP and AR sub-ledger close | Day 2 |

## Month-End Close Calendar

| Day | Activity |
| --- | --- |
| Day -2 | Final invoice intake cut-off communicated to the business |
| Day 1 | Goods receipt and invoice accruals prepared |
| Day 2 | AP and AR sub-ledgers closed and reconciled |
| Day 3 | Balance sheet reconciliations including unapplied cash |
| Day 4 | Flux analysis and management reporting |

## Working with the Finance Operations Agents

The Finance Operations Command Center provides an orchestrator agent with specialist child agents
for AP, AR, policy, vendor validation and exception resolution. Guidance for the team:

- Agents prepare and recommend; people decide. Any approval, posting, write-off or master data
  change requires an authenticated human action under control FIN-SOX-AI-01.
- Always review the agent's cited evidence before acting on a policy answer.
- Report an agent response that is wrong, unsupported or missing a citation through the
  Finance Systems intake so the prompt or grounding data can be corrected.
- Agent activity is fully logged and available to Internal Audit.

## Escalation Matrix

| Situation | Escalate to | Timeframe |
| --- | --- | --- |
| Suspected duplicate payment already released | AP Supervisor and Treasury | Immediate |
| Suspected supplier fraud or bank detail compromise | Controller, Treasury, Security | Immediate |
| Unapplied cash over 30 days | Director, Order to Cash | Weekly review |
| Invoice blocked beyond service level | Finance Director for the cost centre | Daily standup |
