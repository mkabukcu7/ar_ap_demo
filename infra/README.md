# Finance Operations Agent Accelerator — Infrastructure

This directory contains all infrastructure-as-code for the Finance Operations Agent Accelerator.

## Structure

```
infra/
├── bicep/                          # Azure Bicep templates (resource-group scope)
│   ├── main.bicep                  # Root template — orchestrates all modules
│   ├── main.parameters.json        # Default parameter values
│   └── modules/
│       ├── storage.bicep           # Storage account + invoices/remittances/knowledge containers
│       ├── search.bicep            # Azure AI Search (Standard, semantic ranker enabled)
│       ├── keyvault.bicep          # Key Vault (RBAC model, soft-delete, purge protection)
│       ├── loganalytics.bicep      # Log Analytics workspace + Application Insights
│       ├── documentintelligence.bicep  # Azure AI Document Intelligence (FormRecognizer)
│       ├── foundry.bicep           # AI Foundry Hub + Project + gpt-5.4 deployment
│       ├── containerapps.bicep     # Container Apps environment + backend + frontend apps
│       └── roleassignments.bicep   # RBAC role assignments (managed identity, keyless)
│
├── foundry/                        # Azure AI Foundry declarative configuration
│   ├── project.yaml                # Foundry project + model deployments
│   ├── connections.yaml            # Service connections (search, storage, etc.)
│   ├── agents/                     # Agent definitions (YAML)
│   │   ├── orchestrator.agent.yaml
│   │   ├── ap-agent.agent.yaml
│   │   ├── ar-agent.agent.yaml
│   │   ├── policy-agent.agent.yaml
│   │   ├── vendor-validation-agent.agent.yaml
│   │   └── exception-resolution-agent.agent.yaml
│   └── README.md
│
├── search/                         # Azure AI Search index definitions
│   ├── index-finance-knowledge.json    # Index schema (text + vector + semantic)
│   ├── datasource-finance-knowledge.json
│   ├── skillset-finance-knowledge.json # Split + embed skillset
│   ├── indexer-finance-knowledge.json  # Scheduled indexer
│   └── README.md
│
└── README.md                       # This file
```

## Quick Start

See **[docs/deployment.md](../docs/deployment.md)** for the full step-by-step deployment guide.

```bash
# 1. Create resource group
az group create --name rg-finance-ops-dev --location eastus2

# 2. Deploy infrastructure
az deployment group create \
  --resource-group rg-finance-ops-dev \
  --template-file infra/bicep/main.bicep \
  --parameters @infra/bicep/main.parameters.json \
  --parameters deployerObjectId=$(az ad signed-in-user show --query id -o tsv)
```

## Security Principles

- **No secrets in code** — all service-to-service authentication uses managed identity + RBAC
- **Shared keys disabled** — Storage (`allowSharedKeyAccess: false`), Search (`disableLocalAuth: true`), AI Services (`disableLocalAuth: true`)
- **RBAC-only Key Vault** — `enableRbacAuthorization: true`; no legacy access policies
- **TLS 1.2 minimum** on all endpoints
- **Public blob access disabled** on all containers
- **Soft-delete + purge protection** on Key Vault; **blob soft-delete** (30 days) on Storage
