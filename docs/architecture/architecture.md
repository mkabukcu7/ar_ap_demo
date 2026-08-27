# Finance Operations Agent Accelerator — Solution Architecture

## Overview

The Finance Operations Agent Accelerator is a **multi-agent AI system** built on Azure AI Foundry that automates and augments Accounts Payable (AP), Accounts Receivable (AR), and Finance Knowledge Management for enterprise finance teams. It targets CFOs, controllers, and shared-services leaders who need to reduce manual processing time, improve working capital visibility, and maintain SOX-compliant controls.

---

## Diagram A — End-to-End Solution Architecture

```mermaid
graph TB
    subgraph Users["👤 Finance Users"]
        CFO["CFO / Controller"]
        AP_Staff["AP Processor"]
        AR_Staff["AR Analyst"]
        Auditor["Auditor / Compliance"]
    end

    subgraph Frontend["🖥️ Frontend Layer (Azure Container Apps)"]
        UI["React SPA\n(Finance Command Center)"]
    end

    subgraph Backend["⚙️ Backend Layer (Azure Container Apps)"]
        API["FastAPI\nREST + WebSocket API"]
    end

    subgraph Foundry["🤖 Azure AI Foundry / Agent Service"]
        Orch["Finance Orchestrator Agent\n(Connected Agents)"]
        AP_A["AP Agent"]
        AR_A["AR Agent"]
        Pol_A["Finance Policy Agent"]
        Vend_A["Vendor Validation Agent"]
        Exc_A["Exception Resolution Agent"]
    end

    subgraph AI["🧠 AI Services"]
        GPT["gpt-5.4\n(Azure AI Services)"]
        DI["Azure AI Document Intelligence\n(Invoice / Remittance Extraction)"]
        Embed["text-embedding-3-large\n(RAG Embedding)"]
    end

    subgraph Search["🔍 Azure AI Search"]
        Idx["finance-knowledge Index\n(Semantic + Vector)"]
    end

    subgraph Data["🗄️ Data Layer"]
        Storage["Azure Blob Storage\n(invoices / remittances / knowledge)"]
        Fabric["Microsoft Fabric\n+ OneLake (Analytics)"]
        KV["Azure Key Vault\n(Secrets / Config)"]
    end

    subgraph Governance["🛡️ Governance & Observability"]
        Purview["Microsoft Purview\n(Data Classification / Lineage)"]
        APPI["Application Insights\n+ Log Analytics"]
        Entra["Microsoft Entra ID\n(Managed Identity / RBAC)"]
    end

    CFO & AP_Staff & AR_Staff & Auditor --> UI
    UI -->|HTTPS REST / WebSocket| API
    API -->|Azure AI Agent Service SDK| Orch
    Orch --> AP_A & AR_A & Pol_A & Vend_A & Exc_A
    AP_A & AR_A & Vend_A & Exc_A --> GPT
    Pol_A --> GPT
    Pol_A --> Idx
    AP_A --> DI
    Idx -->|Semantic + Vector Query| GPT
    Storage -->|Document Ingestion| DI
    Storage --> Idx
    Embed --> Idx
    AP_A & AR_A --> Storage
    API --> Storage
    Fabric --> Storage
    Storage --> Purview
    Fabric --> Purview
    API --> APPI
    Orch --> APPI
    Entra -->|Managed Identity| API
    Entra -->|RBAC| Storage
    Entra -->|RBAC| Idx
    API --> KV
```

---

## Diagram B — Multi-Agent Orchestration Graph

```mermaid
graph TD
    User(["User Request"])
    Orch["🎯 Finance Orchestrator Agent\n─────────────────────\nIntent Classification\nRequest Routing\nResponse Aggregation\nMulti-turn Conversation"]

    AP["📄 AP Agent\n─────────────────────\nInvoice Ingestion\nDuplicate Detection\n3-Way PO Matching\nApproval Workflow\nERP Posting"]

    AR["💰 AR Agent\n─────────────────────\nRemittance Matching\nCash Application\nUnapplied Cash\nCollections Scoring\nAR Health Summary"]

    Policy["📚 Finance Policy Agent\n─────────────────────\nRAG over Knowledge Base\nPolicy Q&A\nSOX Control Guidance\nApproval Thresholds"]

    Vendor["🏢 Vendor Validation Agent\n─────────────────────\nVendor Master Check\nTax ID Validation\nBank Detail Verify\nSanction Screening"]

    Exception["⚠️ Exception Resolution Agent\n─────────────────────\nException Triage\nOwner Assignment\nSLA Tracking\nEscalation Management"]

    Tools[("🔧 Function Tools\n─────────────────────\nsearch_invoices\nget_invoice\nmatch_invoice_to_po\ndetect_duplicate_invoice\nvalidate_vendor\napprove_invoice\nbulk_approve_invoices\nlist_exceptions\npost_invoice_to_erp\nsearch_remittances\nmatch_remittance\nlist_unapplied_cash\nar_health_summary\nprioritize_collections\nsearch_finance_knowledge")]

    User --> Orch
    Orch -->|AP intent| AP
    Orch -->|AR intent| AR
    Orch -->|Policy query| Policy
    Orch -->|Vendor check| Vendor
    Orch -->|Exception mgmt| Exception
    AP --> Tools
    AR --> Tools
    Policy --> Tools
    Vendor --> Tools
    Exception --> Tools
    AP -.->|Validation needed| Vendor
    AP -.->|Exception raised| Exception
    AR -.->|Policy clarification| Policy
    AP & AR & Policy & Vendor & Exception -->|Result| Orch
    Orch -->|Unified Response| User
```

---

## Diagram C — AP Invoice Processing Sequence

```mermaid
sequenceDiagram
    actor User as AP Processor
    participant UI as React UI
    participant API as FastAPI Backend
    participant Orch as Finance Orchestrator
    participant AP as AP Agent
    participant DI as Document Intelligence
    participant VV as Vendor Validation Agent
    participant ERP as ERP System (Mock)
    participant Storage as Azure Blob Storage
    participant APPI as App Insights

    User->>UI: Upload invoice PDF
    UI->>API: POST /api/invoices/upload
    API->>Storage: Store PDF in invoices/
    API->>DI: Extract invoice fields
    DI-->>API: {vendor_id, amount, po_number, line_items, ...}
    API->>Orch: Process invoice (structured data)
    Orch->>AP: Route to AP Agent
    AP->>AP: detect_duplicate_invoice()
    alt Duplicate detected
        AP-->>Orch: Duplicate exception raised
        Orch-->>API: Exception response
        API-->>UI: Show duplicate warning
    else Not duplicate
        AP->>VV: validate_vendor(vendor_id)
        VV-->>AP: Vendor valid / risk flags
        AP->>AP: match_invoice_to_po(invoice_id, po_number)
        alt Match within tolerance (±5%)
            AP->>AP: approve_invoice(invoice_id)
            AP->>ERP: post_invoice_to_erp(invoice_id)
            ERP-->>AP: ERP posting reference
            AP-->>Orch: Invoice approved & posted
            Orch-->>API: Success response
            API->>APPI: Log approval event
            API-->>UI: Show confirmation + ERP ref
        else Match exception
            AP-->>Orch: PO mismatch exception
            Orch-->>API: Exception for review
            API-->>UI: Show exception details + resolution options
        end
    end
    User->>UI: Review & confirm (if human-in-loop required)
```

---

## Diagram D — AR Cash Application Sequence

```mermaid
sequenceDiagram
    actor User as AR Analyst
    participant UI as React UI
    participant API as FastAPI Backend
    participant Orch as Finance Orchestrator
    participant AR as AR Agent
    participant DI as Document Intelligence
    participant Storage as Azure Blob Storage

    User->>UI: Upload remittance advice
    UI->>API: POST /api/remittances/upload
    API->>Storage: Store in remittances/
    API->>DI: Extract remittance fields
    DI-->>API: {customer_id, payment_ref, amount, invoice_refs[]}
    API->>Orch: Match remittance (structured data)
    Orch->>AR: Route to AR Agent
    AR->>AR: search_remittances(payment_ref)
    AR->>AR: match_remittance(remittance_id)
    alt Full match
        AR-->>Orch: Matched — apply cash to invoices
        Orch-->>API: Cash application result
        API-->>UI: Show matched invoices + applied amounts
    else Partial match
        AR->>AR: list_unapplied_cash()
        AR-->>Orch: Partial match + unapplied remainder
        Orch-->>API: Partial match — human review required
        API-->>UI: Show partial match + unapplied items
        User->>UI: Manually assign remainder
        UI->>API: PATCH /api/remittances/{id}/apply
    else No match
        AR-->>Orch: Unapplied cash exception
        Orch-->>API: Exception response
        API-->>UI: Add to unapplied cash queue
    end
    AR->>AR: ar_health_summary()
    AR-->>API: Updated AR metrics
    API-->>UI: Refresh AR dashboard KPIs
```

---

## Component Responsibility Table

| Component | Technology | Primary Responsibility |
|-----------|-----------|------------------------|
| React SPA | React 18 + TypeScript (Azure Container Apps) | Finance Command Center UI — AP/AR dashboards, agent chat, approvals |
| FastAPI Backend | Python 3.12 + FastAPI (Azure Container Apps) | REST API, agent orchestration, tool function implementations, auth middleware |
| Finance Orchestrator | Azure AI Agent Service (gpt-5.4) | Intent classification, child-agent routing, multi-turn conversation state |
| AP Agent | Azure AI Agent Service (gpt-5.4) | Invoice processing, 3-way matching, approvals, ERP posting |
| AR Agent | Azure AI Agent Service (gpt-5.4) | Remittance matching, cash application, collections, AR analytics |
| Finance Policy Agent | Azure AI Agent Service (gpt-5.4) | RAG-powered policy Q&A, SOX/GAAP guidance |
| Vendor Validation Agent | Azure AI Agent Service (gpt-5.4) | Vendor master validation, sanction screening |
| Exception Resolution Agent | Azure AI Agent Service (gpt-5.4) | Exception triage, assignment, SLA tracking, escalation |
| Azure AI Search | Standard SKU + Semantic Ranker | Vector + semantic search over finance knowledge base |
| Azure AI Document Intelligence | FormRecognizer (S0) | Invoice and remittance field extraction |
| Azure Blob Storage | StorageV2 (LRS) | Document storage: invoices, remittances, knowledge |
| Microsoft Fabric + OneLake | Fabric Lakehouse | Finance analytics, historical reporting, reconciliation |
| Microsoft Purview | Data catalog | Data classification, lineage, compliance scanning |
| Application Insights | Workspace-based | Agent telemetry, latency tracing, error alerting |
| Key Vault | Standard SKU | Secrets management (ERP credentials, API keys) |
| Microsoft Entra ID | Managed Identity + RBAC | Zero-credential identity for all service-to-service calls |

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | Azure AI Agent Service (connected agents) | Native Foundry integration; built-in tool execution, tracing, and state management |
| Model | gpt-5.4 | Latest Azure OpenAI reasoning model; strong structured-output and function-calling performance |
| Auth strategy | System-assigned managed identity + RBAC | No secrets or connection strings in code; auditable; automatic rotation |
| Document extraction | Azure AI Document Intelligence | Pre-built invoice model handles varied layouts without custom training |
| RAG embedding model | text-embedding-3-large (3072 dims) | Best-in-class semantic accuracy for financial terminology |
| Deployment target | Azure Container Apps | Serverless scale-to-zero; handles variable demo and production workloads |
| Offline mode | `FINANCE_AGENT_MODE=local` | Enables fully offline demo against JSON sample data with no Azure dependency |
| Human-in-loop | Approval step in AP/AR workflow | Maintains SOX control requirement for human authorization above threshold |
