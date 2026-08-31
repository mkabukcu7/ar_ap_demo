"""Tests for the Microsoft Foundry Prompt Agent adapter."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.agents.foundry_client import build_prompt_agent_definition, invoke_foundry_agent


class FakeResponses:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            call = SimpleNamespace(
                type="function_call",
                name="ap_metrics",
                arguments="{}",
                call_id="call-1",
            )
            return SimpleNamespace(id="response-1", output=[call], output_text="")
        return SimpleNamespace(id="response-2", output=[], output_text="AP metrics are ready.")


def test_prompt_agent_definition_contains_non_strict_registry_tools() -> None:
    definition = build_prompt_agent_definition()

    assert definition["model"] == "gpt-5-mini"
    assert len(definition["tools"]) == 19
    assert all(tool["strict"] is False for tool in definition["tools"])
    assert {tool["name"] for tool in definition["tools"]} >= {"ap_metrics", "ar_health_summary"}


def test_foundry_agent_executes_and_returns_function_output() -> None:
    responses = FakeResponses()
    client = SimpleNamespace(responses=responses)

    result = invoke_foundry_agent("Show AP metrics", client=client)

    assert result.reply == "AP metrics are ready."
    assert result.data["total_invoices"] == 50
    assert result.trace[0].tool == "ap_metrics"


class FakeKnowledgeResponses:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.requests.append(kwargs)
        if len(self.requests) == 1:
            call = SimpleNamespace(
                type="function_call",
                name="search_finance_knowledge",
                arguments=json.dumps({"query": "SOX control invoice approvals"}),
                call_id="call-1",
            )
            return SimpleNamespace(id="response-1", output=[call], output_text="")
        return SimpleNamespace(id="response-2", output=[], output_text="FIN-SOX-AP-01 governs invoice approvals.")


def test_foundry_agent_returns_citations_from_knowledge_tool_calls(monkeypatch) -> None:
    from src.agents import foundry_client

    def fake_execute_tool_call(name: str, arguments: str, *, approver: str | None = None) -> str:
        assert name == "search_finance_knowledge"
        return json.dumps(
            {
                "query": "SOX control invoice approvals",
                "results": [
                    {
                        "title": "SOX Controls Guide",
                        "section": "Purchase to Pay Controls",
                        "source": "sample-data/knowledge/sox-controls-guide.md",
                        "document_id": "sox-controls-guide",
                        "score": 1.0,
                        "snippet": "FIN-SOX-AP-01 requires documented approval.",
                    }
                ],
                "count": 1,
            }
        )

    monkeypatch.setattr(foundry_client, "execute_tool_call", fake_execute_tool_call)
    responses = FakeKnowledgeResponses()
    client = SimpleNamespace(responses=responses)

    result = invoke_foundry_agent("What SOX control governs invoice approvals?", client=client)

    assert result.reply == "FIN-SOX-AP-01 governs invoice approvals."
    assert len(result.citations) == 1
    assert result.citations[0].title == "SOX Controls Guide"
    assert result.citations[0].source == "sample-data/knowledge/sox-controls-guide.md"
    follow_up = responses.requests[1]
    assert follow_up["previous_response_id"] == "response-1"
    tool_output = follow_up["input"][0]
    assert tool_output["type"] == "function_call_output"
    assert tool_output["call_id"] == "call-1"


def test_foundry_agent_returns_citations_from_answer_with_citations_shape(monkeypatch) -> None:
    from src.agents import foundry_client

    class FakeAnswerWithCitationsResponses:
        def __init__(self) -> None:
            self.requests: list[dict[str, object]] = []

        def create(self, **kwargs: object) -> SimpleNamespace:
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                call = SimpleNamespace(
                    type="function_call",
                    name="answer_with_citations",
                    arguments=json.dumps({"query": "SOX control invoice approvals"}),
                    call_id="call-1",
                )
                return SimpleNamespace(id="response-1", output=[call], output_text="")
            return SimpleNamespace(id="response-2", output=[], output_text="FIN-SOX-AP-01 governs invoice approvals.")

    def fake_execute_tool_call(name: str, arguments: str, *, approver: str | None = None) -> str:
        assert name == "answer_with_citations"
        return json.dumps(
            {
                "answer": "FIN-SOX-AP-01 requires documented approval.",
                "citations": [
                    {
                        "title": "SOX Controls Guide — Purchase to Pay Controls",
                        "source": "sample-data/knowledge/sox-controls-guide.md",
                        "snippet": "FIN-SOX-AP-01 requires documented approval.",
                    }
                ],
                "control": "FIN-SOX-AI-03",
            }
        )

    monkeypatch.setattr(foundry_client, "execute_tool_call", fake_execute_tool_call)
    client = SimpleNamespace(responses=FakeAnswerWithCitationsResponses())

    result = invoke_foundry_agent("What SOX control governs invoice approvals?", client=client)

    assert len(result.citations) == 1
    assert result.citations[0].source == "sample-data/knowledge/sox-controls-guide.md"


def test_foundry_agent_skips_non_dict_citation_entries(monkeypatch) -> None:
    from src.agents import foundry_client

    class FakeMalformedCitationResponses:
        def __init__(self) -> None:
            self.requests: list[dict[str, object]] = []

        def create(self, **kwargs: object) -> SimpleNamespace:
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                call = SimpleNamespace(
                    type="function_call",
                    name="search_finance_knowledge",
                    arguments=json.dumps({"query": "SOX control invoice approvals"}),
                    call_id="call-1",
                )
                return SimpleNamespace(id="response-1", output=[call], output_text="")
            return SimpleNamespace(id="response-2", output=[], output_text="FIN-SOX-AP-01 governs invoice approvals.")

    def fake_execute_tool_call(name: str, arguments: str, *, approver: str | None = None) -> str:
        assert name == "search_finance_knowledge"
        return json.dumps(
            {
                "query": "SOX control invoice approvals",
                "results": [
                    "not-a-dict-entry",
                    {
                        "title": "SOX Controls Guide",
                        "source": "sample-data/knowledge/sox-controls-guide.md",
                        "snippet": "FIN-SOX-AP-01 requires documented approval.",
                    },
                ],
                "count": 2,
            }
        )

    monkeypatch.setattr(foundry_client, "execute_tool_call", fake_execute_tool_call)
    client = SimpleNamespace(responses=FakeMalformedCitationResponses())

    result = invoke_foundry_agent("What SOX control governs invoice approvals?", client=client)

    assert result.reply == "FIN-SOX-AP-01 governs invoice approvals."
    assert len(result.citations) == 1
    assert result.citations[0].title == "SOX Controls Guide"