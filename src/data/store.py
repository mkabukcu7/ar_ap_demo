"""In-memory finance data store backed by the JSON sample dataset.

In `local` mode the accelerator runs entirely offline against the committed
sample data. In `foundry` mode the same interface would be backed by Microsoft
Fabric / OneLake and the ERP system of record; the tool layer is intentionally
decoupled from the storage implementation so only this module changes.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "sample-data"

PIPELINE_STAGES = [
    "received",
    "extracted",
    "validated",
    "matched",
    "pending_approval",
    "approved",
    "posted",
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class FinanceDataStore:
    """Loads the sample dataset and serves reads/writes for the tool layer."""

    def __init__(self, data_dir: Path | str | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self._lock = threading.RLock()
        self.reload()

    # ------------------------------------------------------------------ load

    def reload(self) -> None:
        with self._lock:
            self.vendors = self._load("invoices/vendors.json")
            self.purchase_orders = self._load("invoices/purchase_orders.json")
            self.invoices = self._load("invoices/invoices.json")
            self.customers = self._load("remittances/customers.json")
            self.ar_invoices = self._load("remittances/ar_invoices.json")
            self.remittances = self._load("remittances/remittances.json")
            self.knowledge = self._load_knowledge()
            self.activity: list[dict[str, Any]] = []
            self._seed_activity()

    def _seed_activity(self) -> None:
        """Seed the activity feed so the dashboard has history on first load."""

        blocked = [inv for inv in self.invoices if inv["status"] == "blocked"][:2]
        unapplied = [rem for rem in self.remittances if rem["unapplied_amount"] > 0][:1]
        posted = [inv for inv in self.invoices if inv["status"] == "posted"][:1]

        self.record_activity("AP Agent", "document_extracted", f"{len(self.invoices)} invoices extracted with Content Understanding")
        self.record_activity("Vendor Validation Agent", "vendor_master_check", f"{len(self.vendors)} suppliers validated against the vendor master")
        for invoice in blocked:
            codes = ", ".join(item["code"] for item in invoice["exceptions"]) or "policy review"
            self.record_activity("Exception Resolution Agent", "exception_raised", f"{invoice['invoice_id']} blocked: {codes}", "failed")
        for invoice in posted:
            self.record_activity("AP Agent", "erp_posting", f"{invoice['invoice_id']} posted to ERP as {invoice['erp_document_id']}")
        for remittance in unapplied:
            self.record_activity(
                "AR Agent",
                "cash_application",
                f"{remittance['remittance_id']} has {remittance['unapplied_amount']:,.2f} USD unapplied",
                "failed",
            )
        self.record_activity("Finance Policy Agent", "knowledge_indexed", f"{len(self.knowledge)} policy passages indexed for retrieval")

    def _load(self, relative: str) -> list[dict[str, Any]]:
        path = self.data_dir / relative
        if not path.exists():
            raise FileNotFoundError(
                f"Sample data file '{path}' is missing. Run: python -m src.data.generate_sample_data"
            )
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_knowledge(self) -> list[dict[str, Any]]:
        knowledge_dir = self.data_dir / "knowledge"
        documents: list[dict[str, Any]] = []
        for path in sorted(knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), path.stem)
            for section in _split_sections(text):
                documents.append(
                    {
                        "document_id": path.stem,
                        "title": title,
                        "section": section["heading"],
                        "content": section["content"],
                        "source": f"sample-data/knowledge/{path.name}",
                    }
                )
        return documents

    # --------------------------------------------------------------- lookups

    def get_invoice(self, invoice_id: str) -> dict[str, Any] | None:
        return next((inv for inv in self.invoices if inv["invoice_id"].upper() == invoice_id.upper()), None)

    def get_vendor(self, vendor_id: str) -> dict[str, Any] | None:
        return next((ven for ven in self.vendors if ven["vendor_id"].upper() == vendor_id.upper()), None)

    def get_vendor_by_name(self, name: str) -> dict[str, Any] | None:
        needle = name.strip().lower()
        return next((ven for ven in self.vendors if ven["name"].lower() == needle), None)

    def get_purchase_order(self, po_number: str) -> dict[str, Any] | None:
        return next((po for po in self.purchase_orders if po["po_number"].upper() == po_number.upper()), None)

    def get_remittance(self, remittance_id: str) -> dict[str, Any] | None:
        return next(
            (rem for rem in self.remittances if rem["remittance_id"].upper() == remittance_id.upper()),
            None,
        )

    def get_ar_invoice(self, ar_invoice_id: str) -> dict[str, Any] | None:
        return next(
            (inv for inv in self.ar_invoices if inv["ar_invoice_id"].upper() == ar_invoice_id.upper()),
            None,
        )

    def get_customer(self, customer_id: str) -> dict[str, Any] | None:
        return next((cus for cus in self.customers if cus["customer_id"].upper() == customer_id.upper()), None)

    # --------------------------------------------------------------- updates

    def update_invoice(self, invoice_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            invoice = self.get_invoice(invoice_id)
            if invoice is None:
                raise KeyError(invoice_id)
            invoice.update(changes)
            return invoice

    def record_activity(self, agent: str, action: str, detail: str, status: str = "succeeded") -> dict[str, Any]:
        with self._lock:
            entry = {
                "timestamp": _utcnow(),
                "agent": agent,
                "action": action,
                "detail": detail,
                "status": status,
            }
            self.activity.append(entry)
            return entry

    def recent_activity(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(reversed(self.activity))[:limit]

    # ------------------------------------------------------------ aggregates

    def pipeline_counts(self) -> list[dict[str, Any]]:
        counts = {stage: 0 for stage in PIPELINE_STAGES}
        counts["blocked"] = 0
        for invoice in self.invoices:
            counts[invoice["status"]] = counts.get(invoice["status"], 0) + 1
        stages = [{"stage": stage, "count": counts[stage]} for stage in PIPELINE_STAGES]
        stages.append({"stage": "blocked", "count": counts["blocked"]})
        return stages


def _split_sections(text: str) -> Iterable[dict[str, str]]:
    """Split a markdown knowledge document into `##` sections for retrieval."""

    heading = "Overview"
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if buffer and any(item.strip() for item in buffer):
                yield {"heading": heading, "content": "\n".join(buffer).strip()}
            heading = line[3:].strip()
            buffer = []
        elif not line.startswith("# "):
            buffer.append(line)
    if buffer and any(item.strip() for item in buffer):
        yield {"heading": heading, "content": "\n".join(buffer).strip()}


_STORE: FinanceDataStore | None = None


def get_store(data_dir: Path | str | None = None) -> FinanceDataStore:
    """Return the process-wide data store (created on first use)."""

    global _STORE
    requested = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
    if _STORE is None or _STORE.data_dir != requested:
        _STORE = FinanceDataStore(requested)
    return _STORE


def reset_store() -> None:
    """Drop the cached store — used by tests to guarantee isolation."""

    global _STORE
    _STORE = None
