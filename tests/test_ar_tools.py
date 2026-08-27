"""Accounts Receivable tool behaviour."""

from __future__ import annotations

from src.data.store import FinanceDataStore
from src.tools import ar_tools


def test_unapplied_cash_is_reported_largest_first(store: FinanceDataStore) -> None:
    result = ar_tools.list_unapplied_cash(store=store)
    assert result["count"] >= 1
    amounts = [item["unapplied_amount"] for item in result["items"]]
    assert amounts == sorted(amounts, reverse=True)
    assert round(sum(amounts), 2) == result["total_unapplied"]
    assert result["control"] == "FIN-SOX-AR-02"


def test_unapplied_cash_respects_a_minimum_threshold(store: FinanceDataStore) -> None:
    result = ar_tools.list_unapplied_cash(min_amount=5_000, store=store)
    assert all(item["unapplied_amount"] >= 5_000 for item in result["items"])


def test_match_remittance_explains_the_application(store: FinanceDataStore) -> None:
    remittance = next(rem for rem in store.remittances if rem["matches"])
    result = ar_tools.match_remittance(remittance["remittance_id"], store=store)
    assert result["found"] is True
    assert result["matches"]
    assert all("auto_applied" in match for match in result["matches"])
    assert ar_tools.match_remittance("RMT-0000", store=store)["found"] is False


def test_payment_discrepancies_rank_by_impact(store: FinanceDataStore) -> None:
    result = ar_tools.payment_discrepancies(limit=5, store=store)
    impacts = [item["impact"] for item in result["items"]]
    assert impacts == sorted(impacts, reverse=True)
    assert len(result["items"]) <= 5


def test_ar_health_summary_metrics(store: FinanceDataStore) -> None:
    metrics = ar_tools.ar_health_summary(store=store)
    assert metrics["open_ar_amount"] > 0
    assert 0 <= metrics["past_due_rate"] <= 1
    assert metrics["dso_days"] > 0
    assert sum(metrics["aging"].values()) > 0


def test_collections_are_prioritised_by_score(store: FinanceDataStore) -> None:
    result = ar_tools.prioritize_collections(limit=5, store=store)
    scores = [item["priority_score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)
    assert all(item["recommended_action"] for item in result["items"])
