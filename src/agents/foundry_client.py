"""Azure AI Foundry adapter.

`local` mode (the default) needs no Azure resources. When the accelerator is
deployed, this module provisions the orchestrator and its connected child agents
on the **Azure AI Agent Service** with the ``gpt-5.4`` deployment, registering
the Python functions in :mod:`src.tools.registry` as function tools.

Authentication is always Microsoft Entra ID via ``DefaultAzureCredential`` —
no keys or connection secrets are read from code.

Provision the agents with::

    FINANCE_AGENT_MODE=foundry \\
    AZURE_AI_PROJECT_ENDPOINT=https://<project>.services.ai.azure.com/api/projects/<name> \\
    python -m src.agents.foundry_client

The declarative equivalents of the definitions produced here are checked in at
``infra/foundry/agents/*.agent.yaml``.
"""

from __future__ import annotations

import json
from typing import Any

from src.agents.orchestrator import FinanceOrchestratorAgent
from src.config import settings
from src.tools.registry import TOOL_SCHEMAS, invoke_tool


class FoundryNotConfiguredError(RuntimeError):
    """Raised when Foundry mode is requested without the required configuration."""


def build_agent_payloads(orchestrator: FinanceOrchestratorAgent | None = None) -> list[dict[str, Any]]:
    """Return the create-agent payloads for the orchestrator and its child agents.

    The payloads are plain dictionaries so they can be inspected, diffed and
    tested without any Azure dependency.
    """

    orchestrator = orchestrator or FinanceOrchestratorAgent()
    schema_by_name = {schema["function"]["name"]: schema for schema in TOOL_SCHEMAS}

    payloads: list[dict[str, Any]] = []
    for agent in orchestrator.child_agents:
        payloads.append(
            {
                "name": agent.name,
                "model": settings.model_deployment,
                "description": agent.description,
                "instructions": agent.instructions,
                "tools": [schema_by_name[tool] for tool in agent.tools if tool in schema_by_name],
                "temperature": 0.2,
                "top_p": 0.9,
            }
        )

    payloads.append(
        {
            "name": orchestrator.name,
            "model": settings.model_deployment,
            "description": orchestrator.description,
            "instructions": orchestrator.instructions,
            "tools": [],
            "connected_agents": [agent.name for agent in orchestrator.child_agents],
            "temperature": 0.2,
            "top_p": 0.9,
        }
    )
    return payloads


def execute_tool_call(name: str, arguments: str | dict[str, Any]) -> str:
    """Execute a Foundry tool call and return the JSON string the service expects."""

    parsed = json.loads(arguments) if isinstance(arguments, str) else dict(arguments)
    return json.dumps(invoke_tool(name, **parsed), default=str)


def create_agents() -> list[str]:  # pragma: no cover - requires Azure resources
    """Create or update the agents in the configured Azure AI Foundry project."""

    if not settings.project_endpoint:
        raise FoundryNotConfiguredError(
            "AZURE_AI_PROJECT_ENDPOINT is not set. Deploy infra/bicep/main.bicep and export the endpoint, "
            "or keep FINANCE_AGENT_MODE=local to run the accelerator offline."
        )

    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as error:  # pragma: no cover - optional dependency
        raise FoundryNotConfiguredError(
            "Install the Azure extras first: pip install -r requirements-azure.txt"
        ) from error

    client = AIProjectClient(endpoint=settings.project_endpoint, credential=DefaultAzureCredential())
    created: list[str] = []
    for payload in build_agent_payloads():
        agent = client.agents.create_agent(
            model=payload["model"],
            name=payload["name"],
            description=payload["description"],
            instructions=payload["instructions"],
            tools=payload["tools"],
        )
        created.append(agent.id)
    return created


if __name__ == "__main__":  # pragma: no cover - operational entry point
    for agent_id in create_agents():
        print(f"Created agent {agent_id}")
