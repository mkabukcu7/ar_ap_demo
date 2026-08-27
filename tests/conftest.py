"""Shared pytest fixtures.

Every test runs against a freshly loaded copy of the committed sample dataset so
that write actions (approvals, ERP posting) cannot leak between tests.
"""

from __future__ import annotations

import pytest

from src.agents.orchestrator import FinanceOrchestratorAgent
from src.data.store import FinanceDataStore, reset_store


@pytest.fixture()
def store() -> FinanceDataStore:
    reset_store()
    return FinanceDataStore()


@pytest.fixture()
def orchestrator(store: FinanceDataStore) -> FinanceOrchestratorAgent:
    return FinanceOrchestratorAgent(store)
