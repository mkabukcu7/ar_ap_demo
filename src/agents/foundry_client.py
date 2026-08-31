"""Invoke the deployed Microsoft Foundry finance orchestrator.

Foundry performs the reasoning while this process executes the trusted finance
functions requested by the Prompt Agent. Authentication uses Microsoft Entra ID
through ``DefaultAzureCredential``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Protocol

from src.agents.base import AgentResponse, Citation, TraceStep, load_instructions
from src.config import settings
from src.tools.registry import TOOL_SCHEMAS, invoke_tool

ORCHESTRATOR_NAME = "finance-orchestrator"
MAX_TOOL_ROUNDS = 8
WRITE_TOOLS = {"approve_invoice", "bulk_approve_invoices", "post_invoice_to_erp"}
APPROVAL_TOOLS = {"approve_invoice", "bulk_approve_invoices"}


class FoundryNotConfiguredError(RuntimeError):
    """Raised when Foundry mode is requested without the required configuration."""


class ResponsesClient(Protocol):
    responses: Any


def build_prompt_agent_definition() -> dict[str, Any]:
    """Build the deployed Prompt Agent definition from local prompts and tools."""

    tools = []
    for schema in TOOL_SCHEMAS:
        function = schema["function"]
        tools.append(
            {
                "type": "function",
                "name": function["name"],
                "description": function["description"],
                "parameters": function["parameters"],
                "strict": False,
            }
        )
    return {
        "kind": "prompt",
        "model": settings.model_deployment,
        "instructions": load_instructions("orchestrator.md"),
        "tools": tools,
    }


def execute_tool_call(
    name: str,
    arguments: str | dict[str, Any],
    *,
    approver: str | None = None,
) -> str:
    """Execute a Foundry tool call and return the JSON string the service expects."""

    parsed = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
    if name in WRITE_TOOLS and not settings.enable_write_actions:
        raise PermissionError("Write actions are disabled in this environment.")
    if name in APPROVAL_TOOLS and approver:
        parsed.setdefault("approver", approver)
    return json.dumps(invoke_tool(name, **parsed), default=str)


@lru_cache(maxsize=1)
def get_foundry_client() -> ResponsesClient:  # pragma: no cover - requires Azure resources
    """Create the OpenAI-compatible client for the deployed Prompt Agent."""
    if not settings.project_endpoint:
        raise FoundryNotConfiguredError(
            "AZURE_AI_PROJECT_ENDPOINT is required when FINANCE_AGENT_MODE=foundry."
        )

    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as error:  # pragma: no cover - optional dependency
        raise FoundryNotConfiguredError(
            "Install the Azure extras first: pip install -r requirements-azure.txt"
        ) from error

    project = AIProjectClient(endpoint=settings.project_endpoint, credential=DefaultAzureCredential())
    return project.get_openai_client(agent_name=ORCHESTRATOR_NAME)


def sync_foundry_agent() -> str:  # pragma: no cover - requires Azure resources
    """Publish a new Prompt Agent version from the repository definition."""

    if not settings.project_endpoint:
        raise FoundryNotConfiguredError("AZURE_AI_PROJECT_ENDPOINT is required to sync the agent.")
    try:
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
        from azure.identity import DefaultAzureCredential
    except ImportError as error:
        raise FoundryNotConfiguredError(
            "Install the Azure extras first: pip install -r requirements-azure.txt"
        ) from error

    payload = build_prompt_agent_definition()
    definition = PromptAgentDefinition(
        model=payload["model"],
        instructions=payload["instructions"],
        tools=[FunctionTool(**tool) for tool in payload["tools"]],
    )
    project = AIProjectClient(endpoint=settings.project_endpoint, credential=DefaultAzureCredential())
    try:
        version = project.agents.create_version(
            ORCHESTRATOR_NAME,
            definition=definition,
            description="Finance orchestrator with trusted client-side tools.",
        )
        return version.id
    finally:
        project.close()


KNOWLEDGE_TOOLS = {"search_finance_knowledge", "answer_with_citations"}


def invoke_foundry_agent(
    message: str,
    *,
    approver: str | None = None,
    client: ResponsesClient | None = None,
) -> AgentResponse:
    """Run one Prompt Agent turn, satisfying any local function calls."""

    openai_client = client or get_foundry_client()
    response = openai_client.responses.create(input=message)
    trace: list[TraceStep] = []
    tool_data: list[Any] = []
    citations: list[Citation] = []

    for _ in range(MAX_TOOL_ROUNDS):
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            if not response.output_text:
                raise RuntimeError("The Foundry agent completed without a text response.")
            data: Any = tool_data[-1] if len(tool_data) == 1 else tool_data or None
            return AgentResponse(reply=response.output_text, data=data, citations=citations, trace=trace)

        outputs: list[dict[str, str]] = []
        for call in calls:
            try:
                result = execute_tool_call(call.name, call.arguments, approver=approver)
                parsed = json.loads(result)
                tool_data.append(parsed)
                if call.name in KNOWLEDGE_TOOLS and isinstance(parsed, dict):
                    # answer_with_citations already formats "citations"; search_finance_knowledge
                    # returns raw "results" with the same title/source/snippet fields.
                    entries = parsed.get("citations") or parsed.get("results") or []
                    citations.extend(
                        Citation(title=entry.get("title", ""), source=entry.get("source", ""), snippet=entry.get("snippet", ""))
                        for entry in entries
                    )
                summary = "Completed trusted local function call."
            except (KeyError, TypeError, ValueError, PermissionError) as error:
                result = json.dumps({"error": str(error)})
                summary = f"Tool call failed: {error}"
            trace.append(TraceStep(agent="Finance Orchestrator", tool=call.name, summary=summary))
            outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": result})

        response = openai_client.responses.create(
            input=outputs,
            previous_response_id=response.id,
        )


    raise RuntimeError(f"The Foundry agent exceeded {MAX_TOOL_ROUNDS} tool-call rounds.")


if __name__ == "__main__":  # pragma: no cover - manual deployment step
    # `python -m src.agents.foundry_client` registers/updates the orchestrator in Foundry.
    print(f"Publishing '{ORCHESTRATOR_NAME}' to {settings.project_endpoint} ...")
    version_id = sync_foundry_agent()
    print(f"Published version: {version_id}")
