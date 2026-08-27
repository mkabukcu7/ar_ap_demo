"""Vendor Validation agent — protects supplier master and payment file integrity."""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResponse, BaseAgent
from src.tools import ap_tools


class VendorValidationAgent(BaseAgent):
    name = "vendor-validation-agent"
    display_name = "Vendor Validation Agent"
    description = "Validates suppliers against the vendor master, including status, tax identifier and bank detail controls."
    prompt_file = "vendor-validation-agent.md"
    tools = ("validate_vendor", "search_invoices", "search_finance_knowledge")

    def validate(self, vendor_id: str | None = None, vendor_name: str | None = None) -> AgentResponse:
        result = ap_tools.validate_vendor(vendor_id=vendor_id, vendor_name=vendor_name, store=self.store)
        vendor = result.get("vendor")
        if vendor is None:
            reply = (
                f"**Not approved** — {vendor_name or vendor_id} is not present in the vendor master. "
                "Raise a supplier onboarding request; payment cannot proceed (control FIN-SOX-AP-04)."
            )
        elif result["valid"]:
            exposure = ap_tools.search_invoices(vendor_id=vendor["vendor_id"], store=self.store)
            reply = (
                f"**Approved for payment** — {vendor['name']} ({vendor['vendor_id']}) is in `approved` status, "
                f"terms {vendor['payment_terms']}, tax id {vendor['tax_id']}, bank account ****{vendor['bank_account_last4']}. "
                f"Purchase order required: {'yes' if vendor['po_required'] else 'no'}. "
                f"Current open exposure: {exposure['count']} invoices worth USD {exposure['total_value']:,.2f}."
            )
        else:
            reply = (
                f"**Not approved** — {vendor['name']} ({vendor['vendor_id']}) is in `{vendor['status']}` status. "
                "Invoices from this supplier raise a VENDOR_NOT_APPROVED exception and may not be paid until the "
                "Vendor Master Lead completes verification (control FIN-SOX-AP-04)."
            )
        self.log("validate_vendor", f"{vendor_name or vendor_id}: {result['reason']}", "succeeded" if result["valid"] else "failed")
        return AgentResponse(
            reply=reply,
            data=result,
            trace=[self.step("validate_vendor", result["reason"])],
        )

    def handle(self, message: str, **kwargs: Any) -> AgentResponse:
        return self.validate(vendor_id=kwargs.get("vendor_id"), vendor_name=kwargs.get("vendor_name") or message)
