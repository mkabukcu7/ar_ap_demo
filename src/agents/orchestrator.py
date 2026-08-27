"""Finance Orchestrator agent.

Routes a natural-language finance question to the right specialist child agent,
merges their responses and enforces human-in-the-loop confirmation before any
financially significant action (control FIN-SOX-AI-01).

In ``local`` mode routing is deterministic keyword/pattern planning so the demo
runs with no Azure dependency. In ``foundry`` mode the same child agents are
provisioned as connected agents on the Azure AI Agent Service and the model
performs the routing using the instructions in ``src/prompts/orchestrator.md``.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from src.agents.ap_agent import APAgent
from src.agents.ar_agent import ARAgent
from src.agents.base import AgentResponse, BaseAgent, TraceStep, money
from src.agents.exception_resolution_agent import ExceptionResolutionAgent
from src.agents.policy_agent import FinancePolicyAgent
from src.agents.vendor_validation_agent import VendorValidationAgent
from src.data.store import FinanceDataStore
from src.tools import ap_tools

INVOICE_ID_PATTERN = re.compile(r"\b(inv[-\s]?\d{3,})\b", re.IGNORECASE)
REMITTANCE_ID_PATTERN = re.compile(r"\b(rmt[-\s]?\d{3,})\b", re.IGNORECASE)
AMOUNT_PATTERN = re.compile(r"\$?\s*([\d,]+(?:\.\d{1,2})?)\s*(k|thousand|m|million)?", re.IGNORECASE)
CONFIRMATION_PATTERN = re.compile(r"\b(confirm|confirmed|yes[, ]*approve|go ahead|proceed|approve them)\b", re.IGNORECASE)

DEMO_PROMPTS = [
    "Show invoices awaiting approval over $10,000",
    "Why is invoice INV-1047 blocked?",
    "Approve all invoices under $2,000 with no exceptions",
    "What cash remains unapplied?",
    "Show the largest payment matching exceptions",
    "What approvals are required for invoices over $25,000?",
    "What SOX control governs invoice approvals?",
]


def parse_amount(message: str) -> float | None:
    """Extract the first monetary threshold mentioned in a message."""

    for match in AMOUNT_PATTERN.finditer(message):
        raw, suffix = match.group(1), (match.group(2) or "").lower()
        if raw.strip(",") in {"", "0"}:
            continue
        try:
            value = float(raw.replace(",", ""))
        except ValueError:  # pragma: no cover - defensive
            continue
        if suffix in {"k", "thousand"}:
            value *= 1_000
        elif suffix in {"m", "million"}:
            value *= 1_000_000
        elif value < 100 and "$" not in message:
            # Ignore incidental small numbers such as "top 5".
            continue
        return value
    return None


def normalize_document_id(raw: str) -> str:
    return re.sub(r"\s+", "-", raw.strip()).upper().replace("--", "-")


class FinanceOrchestratorAgent(BaseAgent):
    name = "finance-orchestrator"
    display_name = "Finance Orchestrator"
    description = "Single entry point for the Finance Operations Command Center; delegates to AP, AR, policy, vendor and exception agents."
    prompt_file = "orchestrator.md"
    tools = ()

    def __init__(self, store: FinanceDataStore | None = None) -> None:
        super().__init__(store)
        self.ap_agent = APAgent(store)
        self.ar_agent = ARAgent(store)
        self.policy_agent = FinancePolicyAgent(store)
        self.vendor_agent = VendorValidationAgent(store)
        self.exception_agent = ExceptionResolutionAgent(store)
        self._pending: dict[str, dict[str, Any]] = {}

    @property
    def child_agents(self) -> list[BaseAgent]:
        return [self.ap_agent, self.ar_agent, self.policy_agent, self.vendor_agent, self.exception_agent]

    def definition(self) -> dict[str, Any]:
        definition = super().definition()
        definition["connected_agents"] = [agent.name for agent in self.child_agents]
        return definition

    # --------------------------------------------------------------- routing

    def handle(self, message: str, session_id: str | None = None, approver: str = "demo.user@contoso.com", **kwargs: Any) -> AgentResponse:
        session_id = session_id or str(uuid.uuid4())
        text = message.strip()
        lowered = text.lower()
        self.log("route_request", text[:120])

        pending = self._pending.get(session_id)
        if pending and CONFIRMATION_PATTERN.search(lowered):
            return self._execute_pending(session_id, pending, approver)

        response = self._route(text, lowered, session_id, approver)
        response.trace.insert(0, TraceStep(self.display_name, "plan", f"Routed to {response.trace[0].agent if response.trace else 'orchestrator'}"))
        return response

    def _route(self, text: str, lowered: str, session_id: str, approver: str) -> AgentResponse:
        invoice_match = INVOICE_ID_PATTERN.search(text)
        remittance_match = REMITTANCE_ID_PATTERN.search(text)
        amount = parse_amount(text)

        # Demo 3 — bulk approval, gated by human confirmation.
        if re.search(r"\bapprove\b", lowered) and re.search(r"\ball\b|\bevery\b|\bbulk\b", lowered):
            require_no_exceptions = not re.search(r"including exception|even with exception|ignore exception", lowered)
            return self._propose_bulk_approval(session_id, amount, require_no_exceptions)

        # Single invoice approval, also gated.
        if re.search(r"\bapprove\b", lowered) and invoice_match:
            return self._propose_single_approval(session_id, normalize_document_id(invoice_match.group(1)))

        # Demo 2 — why is an invoice blocked / invoice deep dive.
        if invoice_match:
            return self.ap_agent.explain_invoice(normalize_document_id(invoice_match.group(1)))

        if remittance_match:
            return self.ar_agent.explain_remittance(normalize_document_id(remittance_match.group(1)))

        # Demo 7 — SOX / policy / procedure questions.
        if re.search(r"\bsox\b|\bcontrol\b|\bpolicy\b|\bpolicies\b|\bprocedure\b|\btreasury\b|\baudit\b|\bhandbook\b", lowered):
            return self._policy_answer(text, amount)

        # Demo 6 — approval authority questions (policy + live AP exposure).
        if re.search(r"approval|approver|authority|delegation|sign[- ]?off", lowered) and not re.search(r"awaiting|queue|pending", lowered):
            return self._policy_answer(text, amount)

        # Demo 1 — approval queue.
        if re.search(r"awaiting approval|pending approval|approval queue|waiting for approval|to approve", lowered):
            return self.ap_agent.list_awaiting_approval(min_amount=amount)

        # Demo 4 — unapplied cash.
        if re.search(r"unapplied|on account|unmatched cash|cash remain", lowered):
            return self.ar_agent.unapplied_cash(min_amount=amount)

        # Demo 5 — payment matching exceptions.
        if re.search(r"payment (matching )?(exception|discrepanc)|remittance exception|short pay|deduction|overpayment", lowered):
            return self.ar_agent.discrepancies(limit=5)

        if re.search(r"\bexception|\bblocked\b|\bstuck\b|\bon hold\b", lowered):
            severity = "high" if "high" in lowered else None
            domain = "ar" if "receivable" in lowered else "ap" if "payable" in lowered else None
            return self.exception_agent.summarize(severity=severity, domain=domain)

        if re.search(r"\bvendor\b|\bsupplier\b", lowered):
            vendor_name = re.sub(r".*\b(vendor|supplier)\b", "", text, flags=re.IGNORECASE).strip(" ?.")
            return self.vendor_agent.validate(vendor_name=vendor_name or None)

        if re.search(r"\bdso\b|receivable|collection|customer payment|aging|ar health", lowered):
            return self.ar_agent.health_summary()

        if re.search(r"\binvoice|payable|\bap\b|spend|touchless", lowered):
            return self.ap_agent.metrics_summary()

        return self._overview()

    # ------------------------------------------------------------ behaviours

    def _policy_answer(self, question: str, amount: float | None) -> AgentResponse:
        response = self.policy_agent.answer(question)
        if amount is not None and re.search(r"invoice|approval", question, re.IGNORECASE):
            exposure = ap_tools.search_invoices(min_amount=amount, status="pending_approval", store=self.store)
            response.reply += (
                f"\n\n**Live exposure:** {exposure['count']} invoices above {money(amount)} are awaiting approval, "
                f"totalling {money(exposure['total_value'])}."
            )
            response.data = {"policy": response.data, "exposure": exposure}
            response.trace.append(self.ap_agent.step("search_invoices", f"pending_approval, min_amount={amount}"))
        return response

    def _propose_bulk_approval(self, session_id: str, amount: float | None, require_no_exceptions: bool) -> AgentResponse:
        threshold = amount or 2_000.0
        candidates = [
            invoice
            for invoice in ap_tools.search_invoices(max_amount=threshold, store=self.store)["items"]
            if invoice["total_amount"] < threshold
            and invoice["status"] in ap_tools.APPROVABLE_STATUSES
            and (not require_no_exceptions or not invoice["exceptions"])
        ]
        total = round(sum(invoice["total_amount"] for invoice in candidates), 2)
        self._pending[session_id] = {
            "action": "bulk_approve_invoices",
            "max_amount": threshold,
            "require_no_exceptions": require_no_exceptions,
            "invoice_ids": [invoice["invoice_id"] for invoice in candidates],
        }
        if not candidates:
            reply = f"No exception-free invoices under {money(threshold)} are awaiting approval."
            self._pending.pop(session_id, None)
        else:
            reply = (
                f"**{len(candidates)} invoices under {money(threshold)} are exception free and ready to approve**, "
                f"totalling {money(total)}:\n\n"
                + "\n".join(
                    f"- {invoice['invoice_id']} · {invoice['vendor_name']} · {money(invoice['total_amount'])}"
                    for invoice in candidates
                )
                + "\n\nUnder the Accounts Payable Policy these are within straight-through processing limits. "
                "Approval is a financially significant action, so I need your confirmation "
                "(control FIN-SOX-AI-01). **Reply `confirm` to approve all of them.**"
            )
        return AgentResponse(
            reply=reply,
            data={"requires_confirmation": bool(candidates), "candidates": candidates, "max_amount": threshold},
            trace=[self.ap_agent.step("search_invoices", f"max_amount={threshold}, exception free")],
        )

    def _propose_single_approval(self, session_id: str, invoice_id: str) -> AgentResponse:
        evaluation = ap_tools.evaluate_invoice(invoice_id, store=self.store)
        if not evaluation.get("found"):
            return AgentResponse(
                reply=f"I could not find invoice {invoice_id}.",
                data=evaluation,
                trace=[self.ap_agent.step("evaluate_invoice", f"{invoice_id} not found")],
            )
        self._pending[session_id] = {"action": "approve_invoice", "invoice_id": invoice_id}
        blockers = ", ".join(evaluation["blockers"]) or "none"
        reply = (
            f"Invoice {invoice_id} is {money(evaluation['total_amount'])} with blockers: {blockers}. "
            f"Required approvals: {', '.join(evaluation['required_approvals'])}. "
            "**Reply `confirm` to record your approval** (control FIN-SOX-AI-01)."
        )
        return AgentResponse(
            reply=reply,
            data={"requires_confirmation": True, "evaluation": evaluation},
            trace=[self.ap_agent.step("evaluate_invoice", invoice_id)],
        )

    def _execute_pending(self, session_id: str, pending: dict[str, Any], approver: str) -> AgentResponse:
        self._pending.pop(session_id, None)
        if pending["action"] == "bulk_approve_invoices":
            response = self.ap_agent.bulk_approve(
                max_amount=pending["max_amount"],
                require_no_exceptions=pending["require_no_exceptions"],
                approver=approver,
            )
        else:
            response = self.ap_agent.approve(pending["invoice_id"], approver=approver)
        response.trace.insert(0, TraceStep(self.display_name, "human_confirmation", f"Confirmed by {approver}"))
        return response

    def _overview(self) -> AgentResponse:
        ap_response = self.ap_agent.metrics_summary()
        ar_response = self.ar_agent.health_summary()
        exceptions = ap_tools.list_exceptions(store=self.store)
        reply = "\n\n".join(
            [
                "**Finance Operations Command Center — current position**",
                ap_response.reply,
                ar_response.reply.split("\n\nTop collection priorities:")[0],
                f"**Exception queue:** {exceptions['count']} open items covering {money(exceptions['total_value'])}.",
                "Try: " + " · ".join(f"*{prompt}*" for prompt in DEMO_PROMPTS[:3]),
            ]
        )
        return AgentResponse(
            reply=reply,
            data={"ap": ap_response.data, "ar": ar_response.data, "exceptions": exceptions},
            trace=[*ap_response.trace, *ar_response.trace],
        )


_ORCHESTRATOR: FinanceOrchestratorAgent | None = None


def get_orchestrator(store: FinanceDataStore | None = None) -> FinanceOrchestratorAgent:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None or store is not None:
        _ORCHESTRATOR = FinanceOrchestratorAgent(store)
    return _ORCHESTRATOR


def reset_orchestrator() -> None:
    global _ORCHESTRATOR
    _ORCHESTRATOR = None
