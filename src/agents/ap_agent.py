"""Accounts Payable agent (local planner)."""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResponse, BaseAgent, money
from src.tools import ap_tools


class APAgent(BaseAgent):
    name = "ap-agent"
    display_name = "AP Agent"
    description = "Processes supplier invoices: extraction, validation, matching, duplicates, approvals and ERP posting."
    prompt_file = "ap-agent.md"
    tools = (
        "search_invoices",
        "get_invoice",
        "match_invoice_to_po",
        "detect_duplicate_invoice",
        "validate_vendor",
        "evaluate_invoice",
        "approve_invoice",
        "bulk_approve_invoices",
        "post_invoice_to_erp",
        "list_exceptions",
        "ap_metrics",
    )

    # ------------------------------------------------------------- behaviours

    def list_awaiting_approval(self, min_amount: float | None = None) -> AgentResponse:
        result = ap_tools.search_invoices(status="pending_approval", min_amount=min_amount, store=self.store)
        threshold = f" over {money(min_amount)}" if min_amount else ""
        if not result["count"]:
            reply = f"No invoices are awaiting approval{threshold}."
        else:
            reply = (
                f"**{result['count']} invoices are awaiting approval{threshold}**, "
                f"totalling {money(result['total_value'])}.\n\n"
                + _invoice_table(result["items"][:10])
                + "\n\nSelect a row in the Approval Queue to review the evidence pack, or ask me to "
                "approve a specific invoice."
            )
        self.log("search_invoices", f"{result['count']} invoices awaiting approval{threshold}")
        return AgentResponse(
            reply=reply,
            data=result,
            trace=[self.step("search_invoices", f"status=pending_approval, min_amount={min_amount}")],
        )

    def explain_invoice(self, invoice_id: str) -> AgentResponse:
        evaluation = ap_tools.evaluate_invoice(invoice_id, store=self.store)
        if not evaluation.get("found"):
            return AgentResponse(
                reply=f"I could not find invoice {invoice_id} in the AP sub-ledger.",
                data=evaluation,
                trace=[self.step("evaluate_invoice", f"{invoice_id} not found")],
            )

        detail = ap_tools.get_invoice(invoice_id, store=self.store)
        invoice = detail["invoice"]
        lines = [
            f"**Invoice {invoice['invoice_id']} — {invoice['vendor_name']} — {money(invoice['total_amount'])}** "
            f"is currently `{invoice['status']}`.",
            "",
        ]

        if invoice["exceptions"]:
            lines.append(f"It is blocked by {len(invoice['exceptions'])} exception(s):")
            lines.append("")
            for exception in invoice["exceptions"]:
                lines.append(f"- **{exception['code']}** ({exception['severity']}) — {exception['message']}")
        else:
            lines.append("There are no open exceptions on this invoice.")

        po_match = evaluation["po_match"]
        if po_match.get("po_number"):
            lines += [
                "",
                f"Three-way match against **{po_match['po_number']}**: invoice {money(po_match['invoice_total'])} "
                f"versus remaining PO balance {money(po_match['po_remaining_amount'])} "
                f"(variance {money(po_match['variance'])}).",
            ]
        duplicates = evaluation["duplicate_check"]["candidates"]
        if duplicates:
            top = duplicates[0]
            lines += [
                "",
                f"Duplicate risk: **{top['invoice_id']}** ({top['status']}, {money(top['total_amount'])}) matches on "
                + ", ".join(signal.replace("_", " ") for signal in top["signals"])
                + f" — confidence {top['confidence']:.0%} (control FIN-SOX-AP-03).",
            ]

        lines += [
            "",
            f"Required approvals at this value: {', '.join(evaluation['required_approvals'])}.",
            "",
            "**Recommended next action:** "
            + (
                "confirm the duplicate disposition with the AP Supervisor, then either cancel the invoice or "
                "release it with a documented reason."
                if duplicates
                else "resolve the open exceptions, then route for approval."
                if invoice["exceptions"]
                else "route for approval."
            ),
        ]
        self.log("evaluate_invoice", f"{invoice_id}: {len(evaluation['blockers'])} blocker(s)")
        return AgentResponse(
            reply="\n".join(lines),
            data=evaluation,
            trace=[
                self.step("get_invoice", invoice_id),
                self.step("match_invoice_to_po", po_match.get("reason", "n/a")),
                self.step("detect_duplicate_invoice", f"{len(duplicates)} candidate(s)"),
                self.step("validate_vendor", evaluation["vendor_check"]["reason"]),
            ],
        )

    def bulk_approve(self, max_amount: float, require_no_exceptions: bool = True, approver: str = "demo.user@contoso.com") -> AgentResponse:
        result = ap_tools.bulk_approve_invoices(
            max_amount=max_amount,
            require_no_exceptions=require_no_exceptions,
            approver=approver,
            store=self.store,
        )
        lines = [
            f"**Approved {result['count']} invoices under {money(max_amount)}** as {approver}.",
        ]
        if result["approved"]:
            lines += ["", "Approved: " + ", ".join(result["approved"])]
        if result["skipped"]:
            lines += ["", f"Held back {len(result['skipped'])} invoice(s) with open exceptions:"]
            lines += [f"- {item['invoice_id']} — {item['reason']}" for item in result["skipped"][:5]]
        lines += [
            "",
            "Every approval is recorded with the approver identity and timestamp under control FIN-SOX-AI-01.",
        ]
        return AgentResponse(
            reply="\n".join(lines),
            data=result,
            trace=[self.step("bulk_approve_invoices", f"max_amount={max_amount}, approver={approver}")],
        )

    def approve(self, invoice_id: str, approver: str = "demo.user@contoso.com") -> AgentResponse:
        result = ap_tools.approve_invoice(invoice_id, approver=approver, store=self.store)
        return AgentResponse(
            reply=result["message"],
            data=result,
            trace=[self.step("approve_invoice", f"{invoice_id} approved={result['approved']}")],
        )

    def metrics_summary(self) -> AgentResponse:
        metrics = ap_tools.ap_metrics(store=self.store)
        reply = (
            f"**Accounts payable**: {metrics['total_invoices']} invoices worth "
            f"{money(metrics['total_spend'])}. {metrics['awaiting_approval']} awaiting approval, "
            f"{metrics['blocked']} blocked. Touchless rate {metrics['touchless_rate']:.0%} "
            f"(target ≥ 70%), exception rate {metrics['exception_rate']:.0%} (target ≤ 15%), "
            f"average cycle time {metrics['avg_cycle_time_days']} days (target ≤ 4)."
        )
        return AgentResponse(reply=reply, data=metrics, trace=[self.step("ap_metrics", "AP KPI snapshot")])

    def handle(self, message: str, **kwargs: Any) -> AgentResponse:
        return self.metrics_summary()


def _invoice_table(invoices: list[dict[str, Any]]) -> str:
    header = "| Invoice | Vendor | Amount | PO | Approver | Exceptions |\n| --- | --- | ---: | --- | --- | --- |"
    rows = [
        "| {invoice_id} | {vendor} | {amount} | {po} | {approver} | {exceptions} |".format(
            invoice_id=invoice["invoice_id"],
            vendor=invoice["vendor_name"],
            amount=money(invoice["total_amount"]),
            po=invoice["po_number"] or "—",
            approver=invoice["approver"],
            exceptions=", ".join(item["code"] for item in invoice["exceptions"]) or "none",
        )
        for invoice in invoices
    ]
    return "\n".join([header, *rows])
