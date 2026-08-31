# Finance Operations Agent Accelerator — Deployment Guide

## Overview

This guide walks through deploying the Finance Operations Agent Accelerator to Azure, provisioning
the AI agents, indexing the knowledge base, and running the application. Runtime reasoning and
orchestration require Azure AI Foundry; the committed sample data is used by trusted function tools.

---

## Prerequisites

### Tools

| Tool | Minimum Version | Install |
|------|----------------|---------|
| Azure CLI | 2.60 | `winget install Microsoft.AzureCLI` / [docs.microsoft.com](https://docs.microsoft.com/cli/azure/install-azure-cli) |
| Azure CLI `ml` extension | latest | `az extension add -n ml` |
| Bicep CLI | 0.28 | Bundled with Azure CLI; or `az bicep install` |
| Python | 3.11+ | [python.org](https://python.org) |
| Git | 2.x | [git-scm.com](https://git-scm.com) |

> The demo path in this guide runs the FastAPI backend directly with Python against the deployed
> Azure resources — Docker and Node.js are **not required**. Container Apps hosting is documented
> separately in [Appendix A](#appendix-a--future-container-apps-hosting-optional) for when you are
> ready to move beyond a local demo.

### Azure Requirements

- Azure subscription with **Contributor** role on the target resource group
- **Quota** for `gpt-5.4` model in the chosen region (default: `eastus2`)
  - Request quota at: Azure Portal → Azure OpenAI → Quotas
- **Quota** for Azure AI Search Standard SKU in the chosen region

---

## Part 1 — Azure Infrastructure Deployment

### Step 1 — Authenticate

```bash
az login
az account set --subscription "<your-subscription-id>"
```

### Step 2 — Create Resource Group

```bash
RESOURCE_GROUP="rg-finance-ops-dev"
LOCATION="eastus2"

az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION"
```

### Step 3 — Retrieve Your Entra Object ID

```bash
DEPLOYER_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
echo "Deployer Object ID: $DEPLOYER_OBJECT_ID"
```

### Step 4 — Customize Parameters

Edit `infra/bicep/main.parameters.json` or pass parameters inline:

```json
{
  "environmentName":    { "value": "dev" },
  "location":           { "value": "eastus2" },
  "modelDeploymentName":{ "value": "gpt-5.4" },
  "modelName":          { "value": "gpt-5.4" },
  "modelCapacity":      { "value": 10 },
  "deployerObjectId":   { "value": "<your-object-id>" }
}
```

### Step 5 — Deploy Infrastructure

```bash
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/bicep/main.bicep \
  --parameters @infra/bicep/main.parameters.json \
  --parameters deployerObjectId="$DEPLOYER_OBJECT_ID" \
  --name "finance-ops-deploy" \
  --verbose
```

Deployment typically takes **8–12 minutes**.

### Step 6 — Capture Deployment Outputs

```bash
PROJECT_ENDPOINT=$(az deployment group show \
  -g "$RESOURCE_GROUP" -n finance-ops-deploy \
  --query properties.outputs.projectEndpoint.value -o tsv)

SEARCH_ENDPOINT=$(az deployment group show \
  -g "$RESOURCE_GROUP" -n finance-ops-deploy \
  --query properties.outputs.searchEndpoint.value -o tsv)

STORAGE_ACCOUNT=$(az deployment group show \
  -g "$RESOURCE_GROUP" -n finance-ops-deploy \
  --query properties.outputs.storageAccountName.value -o tsv)

APPI_CONNECTION_STRING=$(az deployment group show \
  -g "$RESOURCE_GROUP" -n finance-ops-deploy \
  --query properties.outputs.appInsightsConnectionString.value -o tsv)

FRONTEND_URL=$(az deployment group show \
  -g "$RESOURCE_GROUP" -n finance-ops-deploy \
  --query properties.outputs.frontendUrl.value -o tsv)

BACKEND_URL=$(az deployment group show \
  -g "$RESOURCE_GROUP" -n finance-ops-deploy \
  --query properties.outputs.backendUrl.value -o tsv)

echo "Project Endpoint:  $PROJECT_ENDPOINT"
echo "Search Endpoint:   $SEARCH_ENDPOINT"
echo "Storage Account:   $STORAGE_ACCOUNT"
echo "Frontend URL:      $FRONTEND_URL"
echo "Backend URL:       $BACKEND_URL"
```

---

## Part 2 — Azure AI Search Index Setup

### Step 7 — Substitute Placeholders

```bash
AI_SERVICES_NAME=$(az cognitiveservices account list \
  -g "$RESOURCE_GROUP" \
  --query "[?kind=='AIServices'].name" -o tsv | head -1)

sed -i "s/<<AI_SERVICES_NAME>>/$AI_SERVICES_NAME/g" \
  infra/search/index-finance-knowledge.json \
  infra/search/skillset-finance-knowledge.json

SUBSCRIPTION_ID=$(az account show --query id -o tsv)
sed -i "s/<<SUBSCRIPTION_ID>>/$SUBSCRIPTION_ID/g"   infra/search/datasource-finance-knowledge.json
sed -i "s/<<RESOURCE_GROUP>>/$RESOURCE_GROUP/g"      infra/search/datasource-finance-knowledge.json
sed -i "s/<<STORAGE_ACCOUNT_NAME>>/$STORAGE_ACCOUNT/g" infra/search/datasource-finance-knowledge.json
```

### Step 8 — Create Search Resources

```bash
TOKEN=$(az account get-access-token \
  --resource "https://search.azure.com" \
  --query accessToken -o tsv)

# Create index
curl -s -X PUT "${SEARCH_ENDPOINT}/indexes/finance-knowledge?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d @infra/search/index-finance-knowledge.json | python3 -m json.tool

# Create data source
curl -s -X PUT "${SEARCH_ENDPOINT}/datasources/finance-knowledge-datasource?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d @infra/search/datasource-finance-knowledge.json | python3 -m json.tool

# Create skillset
curl -s -X PUT "${SEARCH_ENDPOINT}/skillsets/finance-knowledge-skillset?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d @infra/search/skillset-finance-knowledge.json | python3 -m json.tool

# Create indexer
curl -s -X PUT "${SEARCH_ENDPOINT}/indexers/finance-knowledge-indexer?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d @infra/search/indexer-finance-knowledge.json | python3 -m json.tool

# Run indexer immediately
curl -s -X POST "${SEARCH_ENDPOINT}/indexers/finance-knowledge-indexer/run?api-version=2024-05-01-preview" \
  -H "Authorization: Bearer ${TOKEN}"
```

---

## Part 3 — Upload Sample Data

### Step 9 — Upload Sample Knowledge Documents

```bash
az storage blob upload-batch \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  --destination knowledge \
  --source sample-data/knowledge/

az storage blob upload-batch \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  --destination invoices \
  --source sample-data/invoices/

az storage blob upload-batch \
  --account-name "$STORAGE_ACCOUNT" \
  --auth-mode login \
  --destination remittances \
  --source sample-data/remittances/
```

---

## Part 4 — Azure AI Foundry Agent Provisioning

### Step 10 — Configure Connections

```bash
DI_NAME=$(az cognitiveservices account list \
  -g "$RESOURCE_GROUP" \
  --query "[?kind=='FormRecognizer'].name" -o tsv | head -1)

sed -i "s/<<SEARCH_SERVICE_NAME>>/$(echo $SEARCH_ENDPOINT | sed 's|https://||;s|.search.*||')/g" \
  infra/foundry/connections.yaml
sed -i "s/<<STORAGE_ACCOUNT_NAME>>/$STORAGE_ACCOUNT/g" infra/foundry/connections.yaml
sed -i "s|<<APPLICATIONINSIGHTS_CONNECTION_STRING>>|$APPI_CONNECTION_STRING|g" infra/foundry/connections.yaml
sed -i "s/<<DOCUMENT_INTELLIGENCE_NAME>>/$DI_NAME/g" infra/foundry/connections.yaml
```

### Step 11 — Register Agents

Agent registration is an explicit deployment step; the backend does not register agents on startup.
To register manually:

```bash
pip install -r requirements.txt -r requirements-azure.txt

FINANCE_AGENT_MODE=foundry \
AZURE_AI_PROJECT_ENDPOINT="$PROJECT_ENDPOINT" \
python -m src.agents.foundry_client
```

`src/agents/foundry_client.py` builds the orchestrator from the same instructions in `src/prompts/`
and the same function-tool schemas in `src/tools/registry.py`, so the deployed agent and the demo
do not drift apart. The declarative equivalents are checked in at
`infra/foundry/agents/*.agent.yaml`.

---

## Part 5 — Environment Variables Reference

Create a `.env` file in the repository root (never commit this file — it is `.gitignore`d):

```bash
# Required for the Foundry runtime
AZURE_AI_PROJECT_ENDPOINT=<from Step 6>
AZURE_AI_MODEL_DEPLOYMENT=gpt-5.4
AZURE_SEARCH_ENDPOINT=<from Step 6>
AZURE_SEARCH_INDEX=finance-knowledge
AZURE_STORAGE_ACCOUNT=<from Step 6>
APPLICATIONINSIGHTS_CONNECTION_STRING=<from Step 6>

# Runtime mode: Foundry is required
FINANCE_AGENT_MODE=foundry

# Optional
FINANCE_DATA_DIR=./sample-data                     # trusted tool data location
FINANCE_DEFAULT_APPROVER=approver@example.com      # temporary demo identity only
FINANCE_CORS_ORIGINS=http://localhost:5173         # allowed dashboard origins
FINANCE_ENABLE_WRITE_ACTIONS=true                  # set false for a read-only demo
```

> **Security Note:** Never commit `.env` to source control. In production, these values are injected as Container Apps environment variables from Key Vault references.

---

## Part 6 — Running the Demo Locally (recommended, no Docker required)

This is the primary supported path for demos: the FastAPI backend and the bundled static dashboard
run directly with Python on your machine and connect to the Azure resources deployed in Part 1–4.
No Container Apps hosting, Docker, or Node.js toolchain is required.

### Step 12 — Install Python Dependencies

```bash
pip install -r requirements.txt -r requirements-azure.txt   # runtime + Foundry extras
pip install -r requirements-dev.txt                          # + pytest, for running the test suite
```

### Step 13 — Start the Backend API

```bash
# Load environment variables
set -a && source ../.env && set +a

# Start FastAPI server (port 8000, hot-reload)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Open the dashboard at `http://localhost:8000` — it is served directly by FastAPI, so no separate
frontend process is needed. Interactive API docs: `http://localhost:8000/docs`.

## Part 7 — Verifying the Deployment

### Check Backend Health

```bash
# Local demo run (Part 6)
curl http://localhost:8000/api/health

# Or, if you have deployed Container Apps hosting (Appendix A)
curl https://<backend-url>/api/health
```

Expected: `{"status":"ok","mode":"foundry","model_deployment":"gpt-5.4","invoice_count":50,"knowledge_documents":5}`

### Check Search Index

```bash
TOKEN=$(az account get-access-token --resource "https://search.azure.com" --query accessToken -o tsv)
curl "${SEARCH_ENDPOINT}/indexes/finance-knowledge/docs/\$count?api-version=2024-05-01-preview" \
  -H "Authorization: Bearer ${TOKEN}"
# Expected: {"@odata.context": "...", "value": <document-count>}
```

### Run a Test Agent Query

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Why is invoice INV-1047 blocked?", "session_id": "test-001"}'
```

---

## Part 8 — Cleanup

To remove all deployed resources:

```bash
az group delete \
  --name "$RESOURCE_GROUP" \
  --yes \
  --no-wait
```

> **Warning:** This deletes all data including uploaded invoices and indexed knowledge documents. Ensure any ERP postings are reconciled before cleanup.

To selectively remove only the Container Apps (keep data):

```bash
az containerapp delete \
  --resource-group "$RESOURCE_GROUP" \
  --name "ca-api-<suffix>" --yes

az containerapp delete \
  --resource-group "$RESOURCE_GROUP" \
  --name "ca-ui-<suffix>" --yes
```

---

## Appendix A — Future: Container Apps Hosting (optional)

> **Not required for the demo.** The recommended path is Part 6 (local Python run). Use this
> appendix only when you are ready to host the backend/frontend as always-on Container Apps
> instead of running them locally.

Container Apps needs real images instead of the `main.bicep` placeholder
(`mcr.microsoft.com/azuredocs/containerapps-helloworld:latest`). Build them in Azure Container
Registry — this avoids installing Docker Desktop locally:

```bash
ACR_NAME="<container-registry-name>"

az acr build \
  --registry "$ACR_NAME" \
  --image finance-api:latest \
  --file Dockerfile.backend .

az acr build \
  --registry "$ACR_NAME" \
  --image finance-ui:latest \
  --file ui/webapp/Dockerfile ui/webapp
```

Then redeploy `main.bicep`, passing the built image URIs as `backendImage` / `frontendImage`
parameters. A `Dockerfile.backend` for the FastAPI service does not exist yet in this repository —
add one before using this path.

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| `401 Unauthorized` on Search | Managed identity not yet propagated | Wait 2 minutes and retry; check RBAC assignments |
| Model deployment not found | `gpt-5.4` quota not approved | Request quota in Azure Portal → Azure OpenAI → Quotas |
| Indexer status `transientFailure` | Embedding skill can't reach AI Services | Verify `text-embedding-3-large` is deployed; check MI RBAC |
| `FINANCE_AGENT_MODE` not respected | Env var not loaded | Verify `.env` is loaded or Container App env vars are set |
| Container App cold start > 30s | Scale-to-zero | Set `minReplicas: 1` in Container Apps configuration |
| Document Intelligence low confidence | Poor scan quality | Use 300 DPI+ scans; enable `imageAction` in skillset |
