"""Finance Policy agent — retrieval-grounded answers with citations."""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentResponse, BaseAgent, Citation
from src.tools import knowledge_tools


class FinancePolicyAgent(BaseAgent):
    name = "policy-agent"
    display_name = "Finance Policy Agent"
    description = "Answers AP, AR, treasury, SOX and audit questions from approved finance documentation, with citations."
    prompt_file = "policy-agent.md"
    tools = ("search_finance_knowledge", "answer_with_citations")

    def answer(self, question: str, top: int = 3) -> AgentResponse:
        result = knowledge_tools.answer_with_citations(question, top=top, store=self.store)
        citations = [Citation(**citation) for citation in result["citations"]]
        self.log(
            "search_finance_knowledge",
            f"'{question[:60]}' → {len(citations)} citation(s)",
            "succeeded" if citations else "failed",
        )
        return AgentResponse(
            reply=result["answer"],
            data={"citations": result["citations"]},
            citations=citations,
            trace=[self.step("search_finance_knowledge", f"top={top}")],
        )

    def handle(self, message: str, **kwargs: Any) -> AgentResponse:
        return self.answer(message, top=int(kwargs.get("top", 3)))
