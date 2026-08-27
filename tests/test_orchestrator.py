"""The orchestrator must answer every scripted demo question correctly."""

from __future__ import annotations

import pytest

from src.agents.orchestrator import DEMO_PROMPTS, FinanceOrchestratorAgent, parse_amount


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Show invoices awaiting approval over $10,000", 10_000),
        ("Approve all invoices under $2,000 with no exceptions", 2_000),
        ("What approvals are required for invoices over $25,000?", 25_000),
        ("invoices over 50k", 50_000),
        ("What cash remains unapplied?", None),
    ],
)
def test_parse_amount(message: str, expected: float | None) -> None:
    assert parse_amount(message) == expected


def test_demo_1_lists_high_value_approval_queue(orchestrator: FinanceOrchestratorAgent) -> None:
    response = orchestrator.handle(DEMO_PROMPTS[0], session_id="demo1")
    assert "awaiting approval" in response.reply
    assert response.data["count"] >= 3
    assert all(item["total_amount"] >= 10_000 for item in response.data["items"])
    assert any(step.tool == "search_invoices" for step in response.trace)


def test_demo_2_explains_why_an_invoice_is_blocked(orchestrator: FinanceOrchestratorAgent) -> None:
    response = orchestrator.handle(DEMO_PROMPTS[1], session_id="demo2")
    assert "INV-1047" in response.reply
    assert "DUPLICATE_SUSPECTED" in response.reply
    assert "PO_AMOUNT_MISMATCH" in response.reply
    assert response.data["recommendation"] == "hold"


def test_demo_3_requires_human_confirmation_before_approving(orchestrator: FinanceOrchestratorAgent) -> None:
    preview = orchestrator.handle(DEMO_PROMPTS[2], session_id="demo3")
    assert preview.data["requires_confirmation"] is True
    candidate_ids = [invoice["invoice_id"] for invoice in preview.data["candidates"]]
    assert candidate_ids
    # Nothing is approved until the human confirms.
    assert all(orchestrator.store.get_invoice(i)["status"] != "approved" for i in candidate_ids)

    confirmed = orchestrator.handle("confirm", session_id="demo3", approver="controller@contoso.com")
    assert confirmed.data["count"] == len(candidate_ids)
    assert sorted(confirmed.data["approved"]) == sorted(candidate_ids)
    assert all(orchestrator.store.get_invoice(i)["status"] == "approved" for i in candidate_ids)
    assert confirmed.trace[0].tool == "human_confirmation"


def test_confirmation_is_scoped_to_a_session(orchestrator: FinanceOrchestratorAgent) -> None:
    orchestrator.handle(DEMO_PROMPTS[2], session_id="session-a")
    other = orchestrator.handle("confirm", session_id="session-b")
    assert other.data is None or "approved" not in (other.data or {})


def test_demo_4_reports_unapplied_cash(orchestrator: FinanceOrchestratorAgent) -> None:
    response = orchestrator.handle(DEMO_PROMPTS[3], session_id="demo4")
    assert "unapplied" in response.reply.lower()
    assert response.data["total_unapplied"] > 0


def test_demo_5_ranks_payment_matching_exceptions(orchestrator: FinanceOrchestratorAgent) -> None:
    response = orchestrator.handle(DEMO_PROMPTS[4], session_id="demo5")
    impacts = [item["impact"] for item in response.data["items"]]
    assert impacts == sorted(impacts, reverse=True)


def test_demo_6_combines_policy_and_live_exposure(orchestrator: FinanceOrchestratorAgent) -> None:
    response = orchestrator.handle(DEMO_PROMPTS[5], session_id="demo6")
    assert response.citations
    assert "Live exposure" in response.reply
    assert response.data["exposure"]["count"] >= 1


def test_demo_7_answers_sox_question_with_citations(orchestrator: FinanceOrchestratorAgent) -> None:
    response = orchestrator.handle(DEMO_PROMPTS[6], session_id="demo7")
    assert "FIN-SOX-AP-01" in response.reply
    assert response.citations
    assert response.citations[0].source.endswith("sox-controls-guide.md")


def test_unknown_question_returns_the_command_centre_overview(orchestrator: FinanceOrchestratorAgent) -> None:
    response = orchestrator.handle("how are we doing?", session_id="overview")
    assert "Finance Operations Command Center" in response.reply
    assert {"ap", "ar", "exceptions"} <= set(response.data)


def test_every_response_is_traced(orchestrator: FinanceOrchestratorAgent) -> None:
    for index, prompt in enumerate(DEMO_PROMPTS):
        response = orchestrator.handle(prompt, session_id=f"trace-{index}")
        assert response.trace, prompt
        assert response.reply.strip()
