"""Shared agent abstractions.

The accelerator runs in two modes:

* ``local`` (default) — deterministic Python planners call the same function
  tools that are registered with Azure AI Foundry. No Azure resources or model
  quota are required, so the demo always runs.
* ``foundry`` — the orchestrator and its child agents run on Microsoft Foundry
    with the configured model deployment; the tools in :mod:`src.tools` are
  registered as function tools and executed locally by the tool-call loop.

Both modes share the instructions in ``src/prompts`` so the demo narrative and
the deployed agents never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.data.store import FinanceDataStore, get_store

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@lru_cache(maxsize=32)
def load_instructions(prompt_file: str) -> str:
    """Load an agent instruction file from ``src/prompts``."""

    path = PROMPT_DIR / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"Prompt file '{path}' not found.")
    return path.read_text(encoding="utf-8")


@dataclass
class Citation:
    title: str
    source: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        return {"title": self.title, "source": self.source, "snippet": self.snippet}


@dataclass
class TraceStep:
    agent: str
    tool: str
    summary: str

    def to_dict(self) -> dict[str, str]:
        return {"agent": self.agent, "tool": self.tool, "summary": self.summary}


@dataclass
class AgentResponse:
    """The normalised response contract shared by every agent."""

    reply: str
    data: Any = None
    citations: list[Citation] = field(default_factory=list)
    trace: list[TraceStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reply": self.reply,
            "data": self.data,
            "citations": [
                citation.to_dict() if hasattr(citation, "to_dict") else Citation(**citation).to_dict()
                for citation in self.citations
            ],
            "agent_trace": [step.to_dict() for step in self.trace],
        }


class BaseAgent:
    """Base class for the orchestrator and every specialist child agent."""

    name: str = "agent"
    display_name: str = "Agent"
    description: str = ""
    prompt_file: str = ""
    tools: tuple[str, ...] = ()

    def __init__(self, store: FinanceDataStore | None = None) -> None:
        self._store = store

    @property
    def store(self) -> FinanceDataStore:
        return self._store or get_store()

    @property
    def instructions(self) -> str:
        return load_instructions(self.prompt_file)

    def definition(self) -> dict[str, Any]:
        """Return the agent definition used to provision the Azure AI Agent Service."""

        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "instructions": self.instructions,
            "tools": list(self.tools),
        }

    def handle(self, message: str, **kwargs: Any) -> AgentResponse:  # pragma: no cover - abstract
        raise NotImplementedError

    # ------------------------------------------------------------- utilities

    def log(self, action: str, detail: str, status: str = "succeeded") -> None:
        self.store.record_activity(self.display_name, action, detail, status)

    def step(self, tool: str, summary: str) -> TraceStep:
        return TraceStep(agent=self.display_name, tool=tool, summary=summary)


def money(amount: float, currency: str = "USD") -> str:
    """Format an amount the way finance leaders expect to read it."""

    return f"{currency} {amount:,.2f}"
