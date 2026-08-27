"""Runtime configuration for the Finance Operations Agent Accelerator.

Every setting is read from the environment so the same code runs locally with
the committed sample data and in Azure against Foundry, AI Search and Fabric.
No secrets are stored in code: Azure access uses Microsoft Entra ID managed
identity via ``DefaultAzureCredential``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    """Load local project settings from a .env file if present."""
    dotenv_path = REPO_ROOT / ".env"
    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if not key or key.startswith("#"):
            continue
        os.environ.setdefault(key, value.strip('"\''))


def _flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Effective settings for the running process."""

    mode: str = os.getenv("FINANCE_AGENT_MODE", "foundry").strip().lower()
    data_dir: str = os.getenv("FINANCE_DATA_DIR", str(REPO_ROOT / "sample-data"))
    default_approver: str = os.getenv("FINANCE_DEFAULT_APPROVER", "demo.user@contoso.com")

    # Azure AI Foundry
    project_endpoint: str | None = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model_deployment: str = os.getenv("AZURE_AI_MODEL_DEPLOYMENT", "gpt-5-mini")

    # Azure AI Search (grounding for the Finance Policy Agent)
    search_endpoint: str | None = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_index: str = os.getenv("AZURE_SEARCH_INDEX", "finance-knowledge")

    # Storage / observability
    storage_account: str | None = os.getenv("AZURE_STORAGE_ACCOUNT")
    app_insights_connection_string: str | None = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    cors_origins: str = os.getenv("FINANCE_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    enable_write_actions: bool = _flag("FINANCE_ENABLE_WRITE_ACTIONS", True)

    @property
    def is_foundry_mode(self) -> bool:
        return self.mode == "foundry" and bool(self.project_endpoint)

    @property
    def requires_foundry(self) -> bool:
        return True

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
