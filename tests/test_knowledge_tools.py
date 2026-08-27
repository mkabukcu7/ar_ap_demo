"""Retrieval grounding for the Finance Policy Agent."""

from __future__ import annotations

from src.data.store import FinanceDataStore
from src.tools import knowledge_tools


def test_sox_question_retrieves_the_controls_guide(store: FinanceDataStore) -> None:
    result = knowledge_tools.search_finance_knowledge("What SOX control governs invoice approvals?", store=store)
    assert result["count"] >= 1
    assert result["results"][0]["document_id"] == "sox-controls-guide"
    assert "FIN-SOX-AP-01" in result["results"][0]["content"]


def test_approval_threshold_question_retrieves_the_ap_policy(store: FinanceDataStore) -> None:
    result = knowledge_tools.search_finance_knowledge(
        "What approvals are required for invoices over $25,000?", store=store
    )
    sources = {item["document_id"] for item in result["results"]}
    assert "ap-policy" in sources


def test_answers_always_carry_citations(store: FinanceDataStore) -> None:
    answer = knowledge_tools.answer_with_citations("How is unapplied cash cleared?", store=store)
    assert answer["citations"]
    assert all(citation["source"].startswith("sample-data/knowledge/") for citation in answer["citations"])
    assert answer["control"] == "FIN-SOX-AI-03"


def test_unknown_topic_is_not_answered_from_general_knowledge(store: FinanceDataStore) -> None:
    answer = knowledge_tools.answer_with_citations("zzzz nonexistent topic qqq", store=store)
    assert answer["citations"] == []
    assert "could not find" in answer["answer"].lower()
