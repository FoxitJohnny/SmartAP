/**
 * eSign API Client
 * Phase 4.2: Electronic Signature Integration
 */

import { apiClient } from './client';
import type {
  ESignRequest,
  CreateESignRequestParams,
  ESignThresholdConfig,
  ThresholdCheckResult,
} from './esign-types';

const ESIGN_BASE = '/esign';

/**
 * Create a new eSign request
 */
export async function createESignRequest(
  params: CreateESignRequestParams
): Promise<ESignRequest> {
  const response = await apiClient.post<ESignRequest>(
    `${ESIGN_BASE}/requests`,
    params
  );
  return response.data;
}

/**
 * Get eSign request details by ID
 */
export async function getESignRequest(requestId: string): Promise<ESignRequest> {
  const response = await apiClient.get<ESignRequest>(
    `${ESIGN_BASE}/requests/${requestId}`
  );
  return response.data;
}

/**
 * Cancel an eSign request
 */
export async function cancelESignRequest(
  requestId: string,
  reason: string
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post(
    `${ESIGN_BASE}/requests/${requestId}/cancel`,
    { reason }
  );
  return response.data;
}

/**
 * Send reminder to a signer
 */
export async function sendSignerReminder(
  requestId: string,
  signerEmail: string
): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.post(
    `${ESIGN_BASE}/requests/${requestId}/remind`,
    { signer_email: signerEmail }
  );
  return response.data;
}

/**
 * Get eSign threshold configuration
 */
export async function getESignThresholds(): Promise<ESignThresholdConfig> {
  const response = await apiClient.get<ESignThresholdConfig>(
    `${ESIGN_BASE}/thresholds`
  );
  return response.data;
}

/**
 * Check if eSign is required for an invoice amount
 */
export async function checkESignThreshold(
  invoiceAmount: number
): Promise<ThresholdCheckResult> {
  const response = await apiClient.post<ThresholdCheckResult>(
    `${ESIGN_BASE}/check-threshold`,
    { invoice_amount: invoiceAmount }
  );
  return response.data;
}

/**
 * Poll eSign request status until completion or timeout
 * @param requestId - The eSign request ID
 * @param onUpdate - Callback for status updates
 * @param intervalMs - Polling interval (default: 5000ms)
 * @param timeoutMs - Maximum polling time (default: 300000ms = 5 minutes)
 */
export async function pollESignStatus(
  requestId: string,
  onUpdate: (request: ESignRequest) => void,
  intervalMs: number = 5000,
  timeoutMs: number = 300000
): Promise<ESignRequest> {
  const startTime = Date.now();
  
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const request = await getESignRequest(requestId);
        onUpdate(request);

        // Check if completed
        if (
          request.status === 'fully_signed' ||
          request.status === 'rejected' ||
          request.status === 'expired' ||
          request.status === 'cancelled'
        ) {
          resolve(request);
          return;
        }

        // Check timeout
        if (Date.now() - startTime > timeoutMs) {
          reject(new Error('Polling timeout exceeded'));
          return;
        }

        // Continue polling
        setTimeout(poll, intervalMs);
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
}

/**
 * Format signer name for display
 */
export function formatSignerName(signer: { name: string }): string {
  return signer.name;
}

/**
 * Format signer role for display
 */
export function formatSignerRole(role: string): string {
  const roleMap: Record<string, string> = {
    manager: 'Manager',
    senior_manager: 'Senior Manager',
    cfo: 'Chief Financial Officer',
    controller: 'Controller',
  };
  return roleMap[role] || role;
}

/**
 * Get status badge color
 */
export function getStatusColor(
  status: string
): 'default' | 'success' | 'warning' | 'destructive' {
  switch (status) {
    case 'fully_signed':
      return 'success';
    case 'pending_signature':
    case 'partially_signed':
      return 'warning';
    case 'rejected':
    case 'expired':
    case 'cancelled':
      return 'destructive';
    default:
      return 'default';
  }
}

/**
 * Get signer status badge color
 */
export function getSignerStatusColor(
  status: string
): 'default' | 'success' | 'warning' | 'destructive' {
  switch (status) {
    case 'signed':
      return 'success';
    case 'pending':
      return 'warning';
    case 'declined':
    case 'expired':
      return 'destructive';
    default:
      return 'default';
  }
}

/**
 * Format status for display
 */
export function formatStatus(status: string): string {
  const statusMap: Record<string, string> = {
    pending_signature: 'Pending Signature',
    partially_signed: 'Partially Signed',
    fully_signed: 'Fully Signed',
    rejected: 'Rejected',
    expired: 'Expired',
    cancelled: 'Cancelled',
  };
  return statusMap[status] || status;
}

/**
 * Format signer status for display
 */
export function formatSignerStatus(status: string): string {
  const statusMap: Record<string, string> = {
    pending: 'Pending',
    signed: 'Signed',
    declined: 'Declined',
    expired: 'Expired',
  };
  return statusMap[status] || status;
}

/**
 * Calculate progress percentage
 */
export function calculateSigningProgress(signers: Array<{ status?: string }>): number {
  if (signers.length === 0) return 0;
  const signed = signers.filter((s) => s.status === 'signed').length;
  return Math.round((signed / signers.length) * 100);
}

/**
 * Check if reminder can be sent
 */
export function canSendReminder(signer: {
  status?: string;
  last_reminder_at?: string;
}): boolean {
  // Can only remind pending signers
  if (signer.status !== 'pending') return false;

  // Check if enough time passed since last reminder (1 hour)
  if (signer.last_reminder_at) {
    const lastReminder = new Date(signer.last_reminder_at);
    const hoursSince = (Date.now() - lastReminder.getTime()) / (1000 * 60 * 60);
    return hoursSince >= 1;
  }

  return true;
}

/**
 * Check if request can be cancelled
 */
export function canCancelRequest(status: string): boolean {
  return status === 'pending_signature' || status === 'partially_signed';
}

/**
 * Get next pending signer
 */
export function getNextPendingSigner(signers: Array<{
  order: number;
  status?: string;
  name: string;
  email: string;
  last_reminder_at?: string;
}>): { name: string; email: string; status?: string; last_reminder_at?: string } | null {
  const pending = signers
    .filter((s) => s.status === 'pending')
    .sort((a, b) => a.order - b.order);
  
  return pending.length > 0 ? pending[0] : null;
}
