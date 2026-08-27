# Finance Knowledge — Azure AI Search Index Setup

This directory contains all Azure AI Search resource definitions for the **finance-knowledge** index used by the Finance Policy Agent for RAG (Retrieval-Augmented Generation).

## Files

| File | Purpose |
|------|---------|
| `index-finance-knowledge.json` | Index schema: text fields + 3072-dim vector field with HNSW + semantic ranker |
| `datasource-finance-knowledge.json` | Blob Storage data source pointing at the `knowledge` container |
| `skillset-finance-knowledge.json` | AI skillset: document extraction → text splitting → OpenAI embedding |
| `indexer-finance-knowledge.json` | Indexer: scheduled every 2 hours, maps blobs → index documents |

## Prerequisites

- Azure AI Search service deployed (Standard SKU for semantic ranker)
- `text-embedding-3-large` model deployed in the Azure AI Services / Foundry account
- Finance knowledge documents uploaded to the `knowledge` blob container
- Azure CLI authenticated: `az login`

## Step 1 — Set Environment Variables

```bash
export SEARCH_ENDPOINT="https://<search-service-name>.search.windows.net"
export AI_SERVICES_NAME="<foundry-ai-services-name>"
export SUBSCRIPTION_ID="<subscription-id>"
export RESOURCE_GROUP="<resource-group>"
export STORAGE_ACCOUNT="<storage-account-name>"

# Substitute placeholders in the JSON files
sed -i "s/<<AI_SERVICES_NAME>>/$AI_SERVICES_NAME/g" \
  infra/search/index-finance-knowledge.json \
  infra/search/skillset-finance-knowledge.json

sed -i "s/<<SUBSCRIPTION_ID>>/$SUBSCRIPTION_ID/g" infra/search/datasource-finance-knowledge.json
sed -i "s/<<RESOURCE_GROUP>>/$RESOURCE_GROUP/g"   infra/search/datasource-finance-knowledge.json
sed -i "s/<<STORAGE_ACCOUNT_NAME>>/$STORAGE_ACCOUNT/g" infra/search/datasource-finance-knowledge.json
```

## Step 2 — Get a ******

```bash
TOKEN=$(az account get-access-token \
  --resource "https://search.azure.com" \
  --query accessToken -o tsv)
```

## Step 3 — Create the Index

```bash
curl -X PUT "${SEARCH_ENDPOINT}/indexes/finance-knowledge?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: ******" \
  -d @infra/search/index-finance-knowledge.json
```

## Step 4 — Create the Data Source

```bash
curl -X PUT "${SEARCH_ENDPOINT}/datasources/finance-knowledge-datasource?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: ******" \
  -d @infra/search/datasource-finance-knowledge.json
```

## Step 5 — Create the Skillset

```bash
curl -X PUT "${SEARCH_ENDPOINT}/skillsets/finance-knowledge-skillset?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: ******" \
  -d @infra/search/skillset-finance-knowledge.json
```

## Step 6 — Create the Indexer

```bash
curl -X PUT "${SEARCH_ENDPOINT}/indexers/finance-knowledge-indexer?api-version=2024-05-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: ******" \
  -d @infra/search/indexer-finance-knowledge.json
```

## Step 7 — Run the Indexer Immediately

```bash
curl -X POST "${SEARCH_ENDPOINT}/indexers/finance-knowledge-indexer/run?api-version=2024-05-01-preview" \
  -H "Authorization: ******"
```

## Step 8 — Check Indexer Status

```bash
curl "${SEARCH_ENDPOINT}/indexers/finance-knowledge-indexer/status?api-version=2024-05-01-preview" \
  -H "Authorization: ******" | python3 -m json.tool
```

## Alternative: Azure CLI (az rest)

```bash
az rest --method PUT \
  --uri "${SEARCH_ENDPOINT}/indexes/finance-knowledge?api-version=2024-05-01-preview" \
  --body @infra/search/index-finance-knowledge.json \
  --resource "https://search.azure.com"
```

## Semantic Ranker

The index is configured with semantic configuration `finance-semantic-config`.  
Query using `queryType=semantic` and `semanticConfiguration=finance-semantic-config` for re-ranked, caption-extracted results.

## Vector Search

The `content_vector` field uses HNSW (cosine similarity, 3072 dimensions for `text-embedding-3-large`).  
The vectorizer is configured to call the Azure OpenAI endpoint automatically at query time — no client-side embedding required.
