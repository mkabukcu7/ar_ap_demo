# Finance Operations Agent Accelerator — Security and Governance

## Overview

This document describes the identity model, access controls, network security, data governance, SOX control mappings, and audit capabilities for the Finance Operations Agent Accelerator. All design decisions prioritize **zero-trust, RBAC-based, keyless authentication** with comprehensive audit trails suitable for SOX-regulated environments.

---

## 1. Microsoft Entra ID Identity Model

### 1.1 Managed Identities

All Azure services use **system-assigned managed identities**. No credentials, connection strings, or API keys are stored in application code, configuration files, or Key Vault (except ERP integration credentials which must be stored in Key Vault as a last resort with tight RBAC scope).

| Service | Identity Type | Purpose |
|---------|--------------|---------|
| Backend Container App | System-assigned MI | Calls Storage, Search, AI Services, Key Vault |
| Frontend Container App | System-assigned MI | Calls backend API only |
| Azure AI Foundry Hub | System-assigned MI | Accesses Storage, Key Vault, App Insights |
| Azure AI Foundry Project | System-assigned MI | Calls AI Services model deployments |
| Azure AI Search | System-assigned MI | Reads blob storage for indexing, calls AI Services for embeddings |
| Document Intelligence | System-assigned MI | Reads blobs for extraction |

### 1.2 RBAC Role Assignments

```
Backend Container App (MI)
├── Storage Blob Data Contributor     → Azure Blob Storage
├── Search Index Data Contributor     → Azure AI Search
├── Search Service Contributor        → Azure AI Search (indexer management)
├── Cognitive Services User           → Document Intelligence
└── Key Vault Secrets User            → Azure Key Vault

Azure AI Search (MI)
├── Storage Blob Data Reader          → Azure Blob Storage (indexer source)
└── Cognitive Services User           → Azure AI Services (embedding calls)

Azure AI Foundry Hub (MI)
├── Storage Blob Data Contributor     → Azure Blob Storage
└── Key Vault Secrets User            → Azure Key Vault

Deploying Principal (human / SPN)
└── Key Vault Administrator           → Azure Key Vault (provisioning only, time-limited)
```

### 1.3 Authentication Flow (Runtime)

```
React UI
  │  Azure Entra ID (MSAL / PKCE flow)
  ↓
FastAPI Backend
  │  DefaultAzureCredential → ManagedIdentityCredential
  ↓
Azure AI Agent Service SDK   →  AI Foundry Project
Storage SDK (BlobServiceClient) →  Azure Blob Storage
SearchClient                    →  Azure AI Search
DocumentAnalysisClient          →  Document Intelligence
SecretClient                    →  Key Vault
```

No secrets pass through any application layer. Token acquisition and renewal is handled by the Azure Identity SDK.

---

## 2. Network Security

> **Note:** Default deployment uses public endpoints for demo accessibility. Production hardening steps are noted for each layer.

| Layer | Demo Configuration | Production Hardening |
|-------|-------------------|---------------------|
| Container Apps | Public HTTPS ingress | VNet integration + internal ingress + Application Gateway WAF |
| Azure Blob Storage | Public endpoint (Azure services bypass) | Private endpoint in VNet subnet; storage firewall IP allowlist |
| Azure AI Search | Public endpoint | Private endpoint; IP restriction to Container Apps outbound |
| Azure AI Foundry | Public endpoint | Managed VNet (workspace isolation mode) |
| Document Intelligence | Public endpoint | Private endpoint |
| Key Vault | Public endpoint (Azure services bypass) | Private endpoint; IP allowlist |

### 2.1 Transport Security

- All endpoints enforce **TLS 1.2 minimum** (`minimumTlsVersion: TLS1_2`)
- All Container Apps ingress configured with `allowInsecure: false`
- Storage accounts configured with `supportsHttpsTrafficOnly: true`
- HSTS headers enforced by Container Apps platform

### 2.2 Shared Key / Local Auth Disabled

| Resource | Setting | Effect |
|----------|---------|--------|
| Azure Blob Storage | `allowSharedKeyAccess: false` | No storage account keys usable; RBAC-only |
| Azure AI Search | `disableLocalAuth: true` | No admin/query keys; RBAC-only |
| Azure AI Services | `disableLocalAuth: true` | No subscription keys; RBAC-only |
| Azure Key Vault | `enableRbacAuthorization: true` | No access policies; RBAC-only |

---

## 3. Data Residency and Classification

### 3.1 Data Residency

All resources are deployed to a single Azure region (default: `eastus2`). Finance documents, extracted structured data, search index content, and agent conversation logs remain within that region boundary. Cross-region replication is disabled by default.

### 3.2 Microsoft Purview Integration

Microsoft Purview provides data catalog, classification, and lineage for the accelerator:

| Capability | Implementation |
|-----------|---------------|
| Data Classification | Purview built-in classifiers scan the `invoices`, `remittances`, and `knowledge` blob containers for PII (tax IDs, bank accounts), financial data, and sensitive documents |
| Sensitivity Labels | Documents classified as `Finance-Confidential` or `Finance-Restricted` based on content patterns |
| Data Lineage | Purview tracks data movement from blob ingest → Document Intelligence extraction → Search index → Agent responses |
| Access Governance | Purview Data Policy integration with Entra ID for attribute-based access control (ABAC) on high-sensitivity documents |
| Compliance Reporting | Purview Compliance Manager integration for SOX and financial services regulation tracking |

### 3.3 Data Retention

| Data Type | Retention | Enforcement |
|-----------|-----------|-------------|
| Invoice blobs | 7 years (SOX) | Blob lifecycle policy + soft-delete 30 days |
| Agent conversation logs (App Insights) | 90 days | Log Analytics workspace retention policy |
| Audit logs (Azure Monitor) | 1 year | Diagnostic settings → Log Analytics |
| Search index | Until re-indexed | Governed by knowledge document retention |
| Key Vault secrets | Soft-delete 90 days + purge protection | Key Vault configuration |

---

## 4. SOX Control Mapping

The accelerator is designed to support the following SOX IT General Controls (ITGCs) and Application Controls:

| SOX Control | Control Description | Accelerator Implementation |
|-------------|--------------------|-----------------------------|
| **AC-01** | Invoice approval requires appropriate authorization | Human-in-loop approval step in AP workflow; approval threshold enforced by AP Agent |
| **AC-02** | Segregation of duties — AP processing vs. approval | Agent roles enforce separation; approval action requires explicit user confirmation in UI |
| **AC-03** | 3-way PO matching before payment | `match_invoice_to_po()` enforces PO match before `approve_invoice()` can be called |
| **AC-04** | Duplicate invoice prevention | `detect_duplicate_invoice()` runs on every invoice before processing; duplicates blocked |
| **AC-05** | Vendor master validation | `validate_vendor()` required before invoice approval; blocked on invalid vendor |
| **IT-01** | Access to financial systems is restricted and authorized | Entra ID RBAC; managed identity; no shared credentials |
| **IT-02** | Changes to financial systems are logged and reviewed | All agent actions logged to Application Insights with user principal, action, and outcome |
| **IT-03** | Financial data is protected from unauthorized modification | RBAC on blob storage; no direct DB writes by UI layer; all writes via API + agent |
| **IT-04** | Audit trail for all financial transactions | Application Insights custom events + structured logging for every AP/AR action |
| **IT-05** | System availability and backup | Azure Container Apps auto-restart; Blob soft-delete; Log Analytics 90-day retention |
| **IT-06** | Data classification and access controls | Microsoft Purview classification + sensitivity labels on financial documents |

---

## 5. Human-in-the-Loop (HITL) Approvals

The accelerator implements mandatory human approval gates for high-risk financial actions:

### 5.1 AP Invoice Approval Thresholds

| Invoice Amount | Approval Type | Approver |
|---------------|--------------|---------|
| ≤ $5,000 | Auto-approved (agent) | None required |
| $5,001 – $25,000 | Single human approval | AP Manager |
| $25,001 – $100,000 | Single human approval | Controller |
| > $100,000 | Dual approval required | Controller + CFO |

> Thresholds are configurable via the `APPROVAL_THRESHOLD_*` environment variables.

### 5.2 HITL Implementation

- The AP Agent calls `approve_invoice()` directly only for auto-approval amounts
- For amounts exceeding the threshold, the agent returns an `approval_required` structured response
- The React UI renders an **Approval Action Card** requiring explicit user confirmation
- The confirmation triggers `POST /api/invoices/{id}/approve` with the user's Entra ID claim attached
- The approval event is logged to Application Insights with the approver's identity

### 5.3 Exception Escalation

- The Exception Resolution Agent tracks SLA timers on open exceptions
- Exceptions open > 24h are escalated to the assigned owner's manager
- Exceptions open > 72h trigger an Application Insights alert and appear in the CFO dashboard

---

## 6. Audit Logging

All security-relevant events are logged as structured Application Insights custom events:

| Event Name | Properties Logged |
|-----------|------------------|
| `invoice.uploaded` | user_id, invoice_id, vendor_id, amount, blob_uri |
| `invoice.duplicate_detected` | invoice_id, duplicate_of, user_id |
| `invoice.approved` | invoice_id, approved_by, amount, approval_type (auto/human) |
| `invoice.rejected` | invoice_id, rejected_by, reason |
| `invoice.posted_to_erp` | invoice_id, erp_reference, amount, vendor_id |
| `remittance.matched` | remittance_id, customer_id, matched_invoices[], applied_amount |
| `exception.raised` | exception_id, type, invoice_id, severity |
| `exception.resolved` | exception_id, resolved_by, resolution_action |
| `agent.tool_call` | agent_name, tool_name, duration_ms, success |
| `agent.response` | agent_name, intent, latency_ms, token_count |
| `auth.access_denied` | resource, principal_id, action |

Logs are queryable via Log Analytics KQL and integrated with Azure Monitor alerts for anomaly detection.

---

## 7. Responsible AI

The accelerator follows Microsoft's Responsible AI principles:

- **Transparency:** All agent responses include source citations and confidence indicators. The UI clearly identifies AI-generated content.
- **Human oversight:** No autonomous financial action exceeds configured approval thresholds without human confirmation.
- **Fairness:** Vendor risk scoring uses objective, auditable criteria.
- **Reliability:** Agent tool calls are wrapped with retry logic and fallback responses.
- **Privacy:** PII in documents is classified by Purview; agent conversation logs are retained only for 90 days.
- **Security:** All identity and access controls described in this document prevent unauthorized agent action.
