"""Accounts Receivable agent (local planner)."""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResponse, BaseAgent, money
from src.tools import ar_tools


class ARAgent(BaseAgent):
    name = "ar-agent"
    display_name = "AR Agent"
    description = "Applies customer payments, clears unapplied cash, surfaces discrepancies and prioritises collections."
    prompt_file = "ar-agent.md"
    tools = (
        "search_remittances",
        "match_remittance",
        "list_unapplied_cash",
        "ar_health_summary",
        "prioritize_collections",
        "payment_discrepancies",
    )

    def unapplied_cash(self, min_amount: float | None = None) -> AgentResponse:
        result = ar_tools.list_unapplied_cash(min_amount=min_amount, store=self.store)
        if not result["count"]:
            reply = "There is no unapplied cash. Every payment received has been applied to a receivable."
        else:
            lines = [
                f"**{money(result['total_unapplied'])} of cash remains unapplied** across "
                f"{result['count']} payments.",
                "",
                "| Payment | Customer | Received | Applied | Unapplied | Root cause |",
                "| --- | --- | ---: | ---: | ---: | --- |",
            ]
            for item in result["items"][:8]:
                cause = ", ".join(exc["code"] for exc in item["exceptions"]) or "pending research"
                lines.append(
                    f"| {item['remittance_id']} | {item['customer_name']} | {money(item['payment_amount'])} | "
                    f"{money(item['applied_amount'])} | {money(item['unapplied_amount'])} | {cause} |"
                )
            lines += [
                "",
                "Policy (FIN-AR-001): unapplied cash is researched within two business days and cleared "
                "within ten; balances over 30 days escalate to the Director, Order to Cash (FIN-SOX-AR-02).",
            ]
            reply = "\n".join(lines)
        self.log("list_unapplied_cash", f"{result['count']} payments, {money(result['total_unapplied'])} unapplied")
        return AgentResponse(
            reply=reply,
            data=result,
            trace=[self.step("list_unapplied_cash", f"min_amount={min_amount}")],
        )

    def discrepancies(self, limit: int = 5) -> AgentResponse:
        result = ar_tools.payment_discrepancies(limit=limit, store=self.store)
        if not result["count"]:
            return AgentResponse(
                reply="There are no open payment matching exceptions.",
                data=result,
                trace=[self.step("payment_discrepancies", "no exceptions")],
            )
        lines = [
            f"**Top {result['count']} payment matching exceptions**, "
            f"{money(result['total_impact'])} of cash at stake.",
            "",
        ]
        for item in result["items"]:
            codes = ", ".join(exc["code"] for exc in item["exceptions"])
            lines.append(
                f"- **{item['remittance_id']} — {item['customer_name']}** · received "
                f"{money(item['payment_amount'])}, applied {money(item['applied_amount'])}, "
                f"unapplied {money(item['unapplied_amount'])} · {codes}"
                + (" · eligible for small-balance write-off" if item["write_off_eligible"] else "")
            )
        lines += [
            "",
            "Recommended action: request remittance detail from the customer for the largest item and "
            "confirm the deduction root cause before any write-off (write-offs above USD 10,000 need "
            "Controller approval).",
        ]
        self.log("payment_discrepancies", f"{result['count']} exceptions, {money(result['total_impact'])} impact")
        return AgentResponse(
            reply="\n".join(lines),
            data=result,
            trace=[self.step("payment_discrepancies", f"limit={limit}")],
        )

    def health_summary(self) -> AgentResponse:
        metrics = ar_tools.ar_health_summary(store=self.store)
        collections = ar_tools.prioritize_collections(limit=5, store=self.store)
        lines = [
            f"**Accounts receivable health** — open AR {money(metrics['open_ar_amount'])} across "
            f"{metrics['open_invoices']} invoices. DSO {metrics['dso_days']} days (target ≤ 42), "
            f"past due {metrics['past_due_rate']:.0%} of the ledger (target ≤ 12%), unapplied cash "
            f"{money(metrics['unapplied_cash'])} ({metrics['unapplied_rate']:.1%} of collections, target ≤ 1.5%).",
            "",
            f"Collections at risk: {money(metrics['collections_at_risk'])}.",
            "",
            "Top collection priorities:",
        ]
        for item in collections["items"]:
            lines.append(
                f"- {item['customer_name']} · {item['ar_invoice_id']} · {money(item['open_amount'])} · "
                f"{item['days_past_due']} days past due ({item['aging_bucket']}) · {item['recommended_action']}"
            )
        return AgentResponse(
            reply="\n".join(lines),
            data={"metrics": metrics, "collections": collections},
            trace=[
                self.step("ar_health_summary", "AR KPI snapshot"),
                self.step("prioritize_collections", "top 5 priorities"),
            ],
        )

    def explain_remittance(self, remittance_id: str) -> AgentResponse:
        result = ar_tools.match_remittance(remittance_id, store=self.store)
        if not result.get("found"):
            return AgentResponse(
                reply=f"I could not find remittance {remittance_id}.",
                data=result,
                trace=[self.step("match_remittance", f"{remittance_id} not found")],
            )
        lines = [
            f"**{result['remittance_id']} — {result['customer_name']}**: received "
            f"{money(result['payment_amount'])}, applied {money(result['applied_amount'])}, "
            f"unapplied {money(result['unapplied_amount'])} (status `{result['status']}`).",
        ]
        if result["matches"]:
            lines += ["", "Applied to:"]
            for match in result["matches"]:
                lines.append(
                    f"- {match['ar_invoice_id']} · {money(match['applied_amount'])} · "
                    f"confidence {match['confidence']:.0%}"
                    + (" · auto-applied" if match["auto_applied"] else " · analyst confirmation required")
                )
        if result["exceptions"]:
            lines += ["", "Exceptions: " + ", ".join(f"{exc['code']} ({exc['severity']})" for exc in result["exceptions"])]
        if result["suggested_candidates"]:
            lines += ["", "Closest open invoices for the residual:"]
            for candidate in result["suggested_candidates"]:
                lines.append(
                    f"- {candidate['ar_invoice_id']} · {money(candidate['open_amount'])} · "
                    f"{candidate['days_past_due']} days past due"
                )
        return AgentResponse(
            reply="\n".join(lines),
            data=result,
            trace=[self.step("match_remittance", remittance_id)],
        )

    def handle(self, message: str, **kwargs: Any) -> AgentResponse:
        return self.health_summary()
