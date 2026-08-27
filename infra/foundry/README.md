# Finance Operations Agent Accelerator — Azure AI Foundry Configuration

This directory contains declarative YAML definitions for the Azure AI Foundry project, connections, and all six agents.

## Directory Structure

```
infra/foundry/
├── project.yaml                          # Foundry project + model deployments
├── connections.yaml                      # Service connections (search, storage, etc.)
├── agents/
│   ├── orchestrator.agent.yaml           # Finance Orchestrator (entry-point)
│   ├── ap-agent.agent.yaml               # Accounts Payable specialist
│   ├── ar-agent.agent.yaml               # Accounts Receivable specialist
│   ├── policy-agent.agent.yaml           # Finance Policy RAG agent
│   ├── vendor-validation-agent.yaml      # Vendor Validation specialist
│   └── exception-resolution-agent.yaml   # Exception Resolution specialist
└── README.md                             # This file
```

## Prerequisites

- Azure CLI ≥ 2.60 with the `ml` extension: `az extension add -n ml`
- Azure AI Foundry hub and project already deployed via `infra/bicep/main.bicep`
- Bicep deployment outputs captured (see `docs/deployment.md`)

## Step 1 — Populate connections.yaml

After the Bicep deployment, substitute the `<<PLACEHOLDER>>` values in `connections.yaml`:

```bash
SEARCH_NAME=$(az deployment group show -g <rg> -n main --query properties.outputs.searchEndpoint.value -o tsv | sed 's|https://||;s|.search.*||')
STORAGE_NAME=$(az deployment group show -g <rg> -n main --query properties.outputs.storageAccountName.value -o tsv)
APPI_CS=$(az deployment group show -g <rg> -n main --query properties.outputs.appInsightsConnectionString.value -o tsv)
DI_NAME=<document-intelligence-name-from-portal>

sed -i "s/<<SEARCH_SERVICE_NAME>>/$SEARCH_NAME/g" infra/foundry/connections.yaml
sed -i "s/<<STORAGE_ACCOUNT_NAME>>/$STORAGE_NAME/g" infra/foundry/connections.yaml
sed -i "s|<<APPLICATIONINSIGHTS_CONNECTION_STRING>>|$APPI_CS|g" infra/foundry/connections.yaml
sed -i "s/<<DOCUMENT_INTELLIGENCE_NAME>>/$DI_NAME/g" infra/foundry/connections.yaml
```

## Step 2 — Create / update the Foundry project

```bash
az ml workspace create \
  --file infra/foundry/project.yaml \
  --resource-group <resource-group> \
  --subscription <subscription-id>
```

## Step 3 — Create connections

Use the Azure AI Foundry portal or CLI to create each connection defined in `connections.yaml`. With the CLI:

```bash
az ml connection create \
  --file infra/foundry/connections.yaml \
  --resource-group <resource-group> \
  --workspace-name <project-name>
```

## Step 4 — Register agents

Each agent YAML can be registered via the Azure AI Agent Service SDK or portal. Using the Python SDK:

```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import yaml, pathlib

client = AIProjectClient(
    endpoint=os.environ["AZURE_AI_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential()
)

for agent_file in pathlib.Path("infra/foundry/agents").glob("*.yaml"):
    spec = yaml.safe_load(agent_file.read_text())
    client.agents.create_agent(
        model=spec["model"],
        name=spec["name"],
        instructions=pathlib.Path(spec["instructions_file"]).read_text(),
        # tools and connected_agents wired by the backend at startup
    )
    print(f"Registered agent: {spec['name']}")
```

> **Note:** The backend (`src/api/agents/`) reads these YAML files at startup and registers or updates agents automatically when `FINANCE_AGENT_MODE=foundry`.

## Model Deployment

The `gpt-5.4` model is deployed via the Bicep template. Verify:

```bash
az cognitiveservices account deployment list \
  --name <ai-services-name> \
  --resource-group <resource-group> \
  --query "[].{name:name, model:properties.model.name, status:properties.provisioningState}" \
  -o table
```

## Local / Offline Mode

Set `FINANCE_AGENT_MODE=local` to run the backend entirely against the JSON sample data in `/sample-data` without any Azure services. This is ideal for demos without internet access.
