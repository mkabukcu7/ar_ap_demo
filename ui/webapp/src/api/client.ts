import type {
  HealthResponse,
  APMetrics,
  ARMetrics,
  InvoicesResponse,
  PipelineResponse,
  ExceptionsResponse,
  RemittancesResponse,
  UnappliedResponse,
  AgentActivityResponse,
  ApproveResponse,
  BulkApproveResponse,
  ChatResponse,
} from './types';

const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => fetchJSON<HealthResponse>('/api/health'),

  apMetrics: () => fetchJSON<APMetrics>('/api/metrics/ap'),
  arMetrics: () => fetchJSON<ARMetrics>('/api/metrics/ar'),

  invoices: (params?: {
    status?: string;
    min_amount?: number;
    max_amount?: number;
    vendor_id?: string;
  }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set('status', params.status);
    if (params?.min_amount != null) qs.set('min_amount', String(params.min_amount));
    if (params?.max_amount != null) qs.set('max_amount', String(params.max_amount));
    if (params?.vendor_id) qs.set('vendor_id', params.vendor_id);
    const q = qs.toString();
    return fetchJSON<InvoicesResponse>(`/api/invoices${q ? `?${q}` : ''}`);
  },

  invoice: (id: string) => fetchJSON<InvoicesResponse['items'][0]>(`/api/invoices/${id}`),

  approveInvoice: (invoice_id: string, approver?: string) =>
    fetchJSON<ApproveResponse>(`/api/invoices/${invoice_id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approver }),
    }),

  bulkApprove: (payload: {
    max_amount: number;
    require_no_exceptions: boolean;
    approver?: string;
  }) =>
    fetchJSON<BulkApproveResponse>('/api/approvals/bulk', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  pipeline: () => fetchJSON<PipelineResponse>('/api/pipeline'),

  exceptions: () => fetchJSON<ExceptionsResponse>('/api/exceptions'),

  remittances: () => fetchJSON<RemittancesResponse>('/api/ar/remittances'),

  unapplied: () => fetchJSON<UnappliedResponse>('/api/ar/unapplied'),

  agentActivity: (limit = 50) =>
    fetchJSON<AgentActivityResponse>(`/api/agents/activity?limit=${limit}`),

  chat: (message: string, session_id?: string) =>
    fetchJSON<ChatResponse>('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id }),
    }),
};
