// ─── Domain Types ────────────────────────────────────────────────────────────

export interface Exception {
  code: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
}

export type InvoiceStatus =
  | 'received'
  | 'extracted'
  | 'validated'
  | 'matched'
  | 'pending_approval'
  | 'approved'
  | 'posted'
  | 'blocked';

export interface Invoice {
  invoice_id: string;
  vendor_id: string;
  vendor_name: string;
  invoice_date: string;
  due_date: string;
  received_date: string;
  currency: string;
  subtotal: number;
  tax_amount: number;
  total_amount: number;
  po_number: string | null;
  status: InvoiceStatus;
  approver: string;
  exceptions: Exception[];
  line_items: LineItem[];
  source_document: string;
  extraction_confidence: number;
}

export interface Remittance {
  remittance_id: string;
  customer_id: string;
  customer_name: string;
  payment_date: string;
  payment_amount: number;
  currency: string;
  applied_amount: number;
  unapplied_amount: number;
  status: 'applied' | 'partially_applied' | 'unapplied';
  matches: { ar_invoice_id: string; applied_amount: number; confidence: number }[];
  source_document: string;
}

// ─── API Response Types ───────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  mode: 'local' | 'foundry';
}

export interface APMetrics {
  total_invoices: number;
  awaiting_approval: number;
  approved: number;
  blocked: number;
  posted: number;
  touchless_rate: number;
  avg_cycle_time_days: number;
  exception_rate: number;
  total_spend: number;
  currency: string;
}

export interface ARMetrics {
  open_invoices: number;
  open_ar_amount: number;
  past_due_amount: number;
  past_due_rate: number;
  dso_days: number;
  unapplied_cash: number;
  collections_at_risk: number;
  currency: string;
}

export interface InvoicesResponse {
  items: Invoice[];
  count: number;
}

export interface PipelineStage {
  stage: string;
  count: number;
}

export interface PipelineResponse {
  stages: PipelineStage[];
}

export interface ExceptionItem {
  invoice_id: string | null;
  document_id: string | null;
  code: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  domain: 'ap' | 'ar';
  amount: number;
}

export interface ExceptionsResponse {
  items: ExceptionItem[];
  count: number;
}

export interface RemittancesResponse {
  items: Remittance[];
  count: number;
}

export interface UnappliedResponse {
  items: Remittance[];
  total_unapplied: number;
  count: number;
}

export interface AgentActivity {
  timestamp: string;
  agent: string;
  action: string;
  detail: string;
  status: 'succeeded' | 'failed' | 'running';
}

export interface AgentActivityResponse {
  items: AgentActivity[];
  count: number;
}

export interface ApproveResponse {
  invoice_id: string;
  status: string;
  message: string;
}

export interface BulkApproveResponse {
  approved: string[];
  skipped: { invoice_id: string; reason: string }[];
  count: number;
}

export interface ChatCitation {
  title: string;
  source: string;
  snippet: string;
}

export interface AgentTraceStep {
  agent: string;
  tool: string;
  summary: string;
}

export interface ChatResponse {
  reply: string;
  citations: ChatCitation[];
  agent_trace: AgentTraceStep[];
  data: unknown | null;
  session_id: string;
}
