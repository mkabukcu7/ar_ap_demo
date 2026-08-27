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
    follow_up = responses.requests[1]
    assert follow_up["previous_response_id"] == "response-1"
    tool_output = follow_up["input"][0]
    assert tool_output["type"] == "function_call_output"
    assert tool_output["call_id"] == "call-1"
    assert json.loads(tool_output["output"])["total_invoices"] == 50