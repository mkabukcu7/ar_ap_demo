import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import {
  mockAPMetrics,
  mockARMetrics,
  mockInvoices,
  mockPipeline,
  mockExceptions,
  mockRemittances,
  mockUnapplied,
  mockAgentActivity,
} from './mockData';
import type {
  APMetrics,
  ARMetrics,
  InvoicesResponse,
  PipelineResponse,
  ExceptionsResponse,
  RemittancesResponse,
  UnappliedResponse,
  AgentActivityResponse,
} from './types';

// Re-export a flag so the UI knows which mode it's in
export let usingMockData = false;

function withFallback<T>(apiFn: () => Promise<T>, fallback: T) {
  return async (): Promise<{ data: T; mock: boolean }> => {
    try {
      const data = await apiFn();
      usingMockData = false;
      return { data, mock: false };
    } catch {
      usingMockData = true;
      return { data: fallback, mock: true };
    }
  };
}

export function useAPMetrics() {
  return useQuery({
    queryKey: ['apMetrics'],
    queryFn: withFallback<APMetrics>(api.apMetrics, mockAPMetrics),
    refetchInterval: 30_000,
  });
}

export function useARMetrics() {
  return useQuery({
    queryKey: ['arMetrics'],
    queryFn: withFallback<ARMetrics>(api.arMetrics, mockARMetrics),
    refetchInterval: 30_000,
  });
}

export function useInvoices(params?: Parameters<typeof api.invoices>[0]) {
  return useQuery({
    queryKey: ['invoices', params],
    queryFn: withFallback<InvoicesResponse>(
      () => api.invoices(params),
      { items: mockInvoices, count: mockInvoices.length },
    ),
    refetchInterval: 15_000,
  });
}

export function usePipeline() {
  return useQuery({
    queryKey: ['pipeline'],
    queryFn: withFallback<PipelineResponse>(api.pipeline, mockPipeline),
    refetchInterval: 15_000,
  });
}

export function useExceptions() {
  return useQuery({
    queryKey: ['exceptions'],
    queryFn: withFallback<ExceptionsResponse>(api.exceptions, mockExceptions),
    refetchInterval: 15_000,
  });
}

export function useRemittances() {
  return useQuery({
    queryKey: ['remittances'],
    queryFn: withFallback<RemittancesResponse>(api.remittances, mockRemittances),
    refetchInterval: 30_000,
  });
}

export function useUnapplied() {
  return useQuery({
    queryKey: ['unapplied'],
    queryFn: withFallback<UnappliedResponse>(api.unapplied, mockUnapplied),
    refetchInterval: 15_000,
  });
}

export function useAgentActivity() {
  return useQuery({
    queryKey: ['agentActivity'],
    queryFn: withFallback<AgentActivityResponse>(
      () => api.agentActivity(50),
      mockAgentActivity,
    ),
    refetchInterval: 5_000,
  });
}

export function useApproveInvoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ invoice_id, approver }: { invoice_id: string; approver?: string }) =>
      api.approveInvoice(invoice_id, approver),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['invoices'] });
      void qc.invalidateQueries({ queryKey: ['apMetrics'] });
      void qc.invalidateQueries({ queryKey: ['pipeline'] });
    },
  });
}

export function useBulkApprove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.bulkApprove,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['invoices'] });
      void qc.invalidateQueries({ queryKey: ['apMetrics'] });
      void qc.invalidateQueries({ queryKey: ['pipeline'] });
    },
  });
}
