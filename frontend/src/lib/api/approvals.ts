import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { Invoice } from '@/types';

// ============================================================================
// Types
// ============================================================================

export interface ApprovalQueueFilters {
  status?: 'PENDING' | 'APPROVED' | 'REJECTED';
  priority?: 'HIGH' | 'MEDIUM' | 'LOW';
  assignedTo?: string;
  minAmount?: number;
  maxAmount?: number;
  riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
}

export interface ApprovalAction {
  action: 'APPROVE' | 'REJECT' | 'ESCALATE' | 'REQUEST_CHANGES';
  comment?: string;
  reason?: string;
  assignTo?: string;
}

export interface ApprovalHistory {
  id: string;
  invoice_id: string;
  user_id: string;
  user_name: string;
  user_role: string;
  action: string;
  comment?: string;
  reason?: string;
  timestamp: string;
}

export interface ApprovalWorkflowStep {
  role: string;
  status: 'COMPLETED' | 'PENDING' | 'NOT_REQUIRED' | 'SKIPPED';
  user_id?: string;
  user_name?: string;
  timestamp?: string;
  comment?: string;
}

export interface ApprovalWorkflow {
  invoice_id: string;
  steps: ApprovalWorkflowStep[];
  current_step: number;
  escalation_rules?: {
    amount_threshold?: number;
    requires_auditor?: boolean;
    requires_manager?: boolean;
  };
}

export interface BulkApprovalRequest {
  invoice_ids: string[];
  comment?: string;
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get approval queue with filters
 */
async function getApprovalQueue(
  page: number = 1,
  limit: number = 20,
  filters?: ApprovalQueueFilters
): Promise<{ data: Invoice[]; total: number; page: number; limit: number }> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  });

  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, value.toString());
      }
    });
  }

  const response = await apiClient.get(`/approvals/queue?${params.toString()}`);
  return response.data;
}

/**
 * Get approval workflow for an invoice
 */
async function getApprovalWorkflow(invoiceId: string): Promise<ApprovalWorkflow> {
  const response = await apiClient.get(`/approvals/${invoiceId}/workflow`);
  return response.data;
}

/**
 * Get approval history for an invoice
 */
async function getApprovalHistory(invoiceId: string): Promise<ApprovalHistory[]> {
  const response = await apiClient.get(`/approvals/${invoiceId}/history`);
  return response.data;
}

/**
 * Perform approval action
 */
async function performApprovalAction(
  invoiceId: string,
  action: ApprovalAction
): Promise<void> {
  await apiClient.post(`/approvals/${invoiceId}/action`, action);
}

/**
 * Bulk approve invoices
 */
async function bulkApprove(request: BulkApprovalRequest): Promise<void> {
  await apiClient.post('/approvals/bulk-approve', request);
}

/**
 * Bulk reject invoices
 */
async function bulkReject(request: BulkApprovalRequest & { reason: string }): Promise<void> {
  await apiClient.post('/approvals/bulk-reject', request);
}

// ============================================================================
// React Query Hooks
// ============================================================================

/**
 * Hook to fetch approval queue
 */
export function useApprovalQueue(
  page: number = 1,
  limit: number = 20,
  filters?: ApprovalQueueFilters
) {
  return useQuery({
    queryKey: ['approval-queue', page, limit, filters],
    queryFn: () => getApprovalQueue(page, limit, filters),
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook to fetch approval workflow
 */
export function useApprovalWorkflow(invoiceId: string) {
  return useQuery({
    queryKey: ['approval-workflow', invoiceId],
    queryFn: () => getApprovalWorkflow(invoiceId),
    enabled: !!invoiceId,
    staleTime: 60000, // 1 minute
  });
}

/**
 * Hook to fetch approval history
 */
export function useApprovalHistory(invoiceId: string) {
  return useQuery({
    queryKey: ['approval-history', invoiceId],
    queryFn: () => getApprovalHistory(invoiceId),
    enabled: !!invoiceId,
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook to perform approval action
 */
export function usePerformApprovalAction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ invoiceId, action }: { invoiceId: string; action: ApprovalAction }) =>
      performApprovalAction(invoiceId, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-queue'] });
      queryClient.invalidateQueries({ queryKey: ['approval-workflow'] });
      queryClient.invalidateQueries({ queryKey: ['approval-history'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}

/**
 * Hook to bulk approve invoices
 */
export function useBulkApprove() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BulkApprovalRequest) => bulkApprove(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-queue'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}

/**
 * Hook to bulk reject invoices
 */
export function useBulkReject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BulkApprovalRequest & { reason: string }) => bulkReject(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approval-queue'] });
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}
