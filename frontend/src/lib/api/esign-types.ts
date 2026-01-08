/**
 * eSign Types and Interfaces
 * Phase 4.2: Electronic Signature Integration
 */

export enum ESignStatus {
  PENDING = 'pending_signature',
  PARTIALLY_SIGNED = 'partially_signed',
  FULLY_SIGNED = 'fully_signed',
  REJECTED = 'rejected',
  EXPIRED = 'expired',
  CANCELLED = 'cancelled',
}

export enum SignerStatus {
  PENDING = 'pending',
  SIGNED = 'signed',
  DECLINED = 'declined',
  EXPIRED = 'expired',
}

export enum SignerRole {
  MANAGER = 'manager',
  SENIOR_MANAGER = 'senior_manager',
  CFO = 'cfo',
  CONTROLLER = 'controller',
}

export interface Signer {
  id?: string;
  name: string;
  email: string;
  role: SignerRole;
  order: number;
  status?: SignerStatus;
  signed_at?: string;
  declined_at?: string;
  decline_reason?: string;
  signer_url?: string;
}

export interface ESignRequest {
  id: string;
  foxit_request_id: string;
  invoice_id: string;
  invoice_number: string;
  invoice_amount: number;
  vendor_name: string;
  status: ESignStatus;
  signers: Signer[];
  created_at: string;
  expires_at: string;
  completed_at?: string;
  cancelled_at?: string;
  title: string;
  message?: string;
  cancellation_reason?: string;
  signed_document_url?: string;
}

export interface CreateESignRequestParams {
  invoice_id: string;
  signers: Omit<Signer, 'id' | 'status' | 'order'>[];
}

export interface ESignThreshold {
  range: string;
  required_approvers: string[];
  requires_esign: boolean;
}

export interface ESignThresholdConfig {
  thresholds: {
    manager: number;
    senior_manager: number;
    cfo: number;
    cfo_and_controller: number;
  };
  rules: ESignThreshold[];
}

export interface ThresholdCheckResult {
  invoice_amount: number;
  requires_esign: boolean;
  required_signers: string[];
  signer_count: number;
}

export interface ESignAuditEvent {
  id: string;
  event_type: string;
  event_timestamp: string;
  actor_email?: string;
  actor_name?: string;
  actor_role?: string;
  event_data: Record<string, unknown>;
}

export interface ESignWebhookEvent {
  event: string;
  request_id: string;
  signer?: Signer;
  signed_at?: string;
  declined_at?: string;
  reason?: string;
  completed_at?: string;
}
