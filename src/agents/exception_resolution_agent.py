"""Exception Resolution agent — explains blockers and drives them to resolution."""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResponse, BaseAgent, money
from src.tools import ap_tools

SLA_DAYS = {"high": 1, "medium": 3, "low": 5}


class ExceptionResolutionAgent(BaseAgent):
    name = "exception-resolution-agent"
    display_name = "Exception Resolution Agent"
    description = "Explains why AP and AR transactions are blocked, ranks them by impact and recommends the fastest resolution."
    prompt_file = "exception-resolution-agent.md"
    tools = (
        "list_exceptions",
        "evaluate_invoice",
        "get_invoice",
        "match_invoice_to_po",
        "detect_duplicate_invoice",
        "match_remittance",
        "payment_discrepancies",
        "search_finance_knowledge",
    )

    def summarize(self, severity: str | None = None, domain: str | None = None, limit: int = 8) -> AgentResponse:
        result = ap_tools.list_exceptions(severity=severity, domain=domain, store=self.store)
        if not result["count"]:
            return AgentResponse(
                reply="The exception queue is clear.",
                data=result,
                trace=[self.step("list_exceptions", "queue empty")],
            )

        by_code: dict[str, dict[str, Any]] = {}
        for item in result["items"]:
            entry = by_code.setdefault(item["code"], {"count": 0, "value": 0.0, "severity": item["severity"]})
            entry["count"] += 1
            entry["value"] = round(entry["value"] + item["amount"], 2)

        lines = [
            f"**{result['count']} open exceptions** covering {money(result['total_value'])} of transaction value.",
            "",
            "| Code | Severity | Count | Value | Resolution SLA |",
            "| --- | --- | ---: | ---: | --- |",
        ]
        for code, entry in sorted(by_code.items(), key=lambda item: item[1]["value"], reverse=True):
            lines.append(
                f"| {code} | {entry['severity']} | {entry['count']} | {money(entry['value'])} | "
                f"{SLA_DAYS[entry['severity']]} business day(s) |"
            )

        lines += ["", "Largest individual items:"]
        for item in result["items"][:limit]:
            reference = item["invoice_id"] or item["document_id"]
            lines.append(
                f"- **{reference}** ({item['domain'].upper()}) · {money(item['amount'])} · {item['code']} — {item['message']}"
            )
        lines += ["", "Ask me *why is invoice INV-1047 blocked?* for the full evidence pack on any single item."]

        self.log("list_exceptions", f"{result['count']} exceptions, {money(result['total_value'])} at risk")
        return AgentResponse(
            reply="\n".join(lines),
            data=result,
            trace=[self.step("list_exceptions", f"severity={severity}, domain={domain}")],
        )

    def handle(self, message: str, **kwargs: Any) -> AgentResponse:
        return self.summarize(severity=kwargs.get("severity"), domain=kwargs.get("domain"))
