/**
 * TypeScript Type Definitions
 * 
 * Shared types used across the frontend application.
 * These should match the backend API schemas.
 */

// ============================================================================
// Authentication Types
// ============================================================================

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  created_at: string;
  updated_at: string;
}

export type UserRole = 'AP_CLERK' | 'MANAGER' | 'AUDITOR' | 'ADMIN';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: User;
}

// ============================================================================
// Invoice Types
// ============================================================================

export type InvoiceStatus = 
  | 'INGESTED' 
  | 'EXTRACTED' 
  | 'MATCHED' 
  | 'RISK_REVIEW' 
  | 'APPROVED' 
  | 'REJECTED'
  | 'READY_FOR_PAYMENT' 
  | 'ARCHIVED';

export interface Invoice {
  id: string;
  document_id: string;
  invoice_number: string;
  vendor_id?: string;
  vendor_name?: string;
  invoice_date?: string;
  due_date?: string;
  total_amount?: number;
  tax_amount?: number;
  subtotal?: number;
  currency?: string;
  po_number?: string;
  status: InvoiceStatus;
  confidence_score?: number;
  matched_po_id?: string;
  risk_level?: RiskLevel;
  risk_flags?: RiskFlag[];
  line_items?: InvoiceLineItem[];
  ocr_data?: any;
  file_path: string;
  file_hash: string;
  created_at: string;
  updated_at: string;
}

export interface InvoiceLineItem {
  id: string;
  invoice_id: string;
  line_number: number;
  description?: string;
  quantity?: number;
  unit_price?: number;
  line_total?: number;
  tax_amount?: number;
  confidence_score?: number;
}

export interface InvoiceUploadResponse {
  invoice_id: string;
  document_id: string;
  filename: string;
  status: InvoiceStatus;
  message: string;
}

export interface InvoiceFilters {
  status?: InvoiceStatus;
  vendor_id?: string;
  vendor_name?: string;
  date_from?: string;
  date_to?: string;
  start_date?: string;
  end_date?: string;
  amount_min?: number;
  amount_max?: number;
  min_amount?: number;
  max_amount?: number;
  risk_level?: RiskLevel[];
  has_risk_flags?: boolean;
  search?: string;
}

// ============================================================================
// Purchase Order Types
// ============================================================================

export type POStatus = 'OPEN' | 'PARTIALLY_MATCHED' | 'FULLY_MATCHED' | 'CLOSED';

export interface PurchaseOrder {
  id: string;
  po_number: string;
  vendor_id: string;
  vendor_name?: string;
  po_date: string;
  total_amount: number;
  currency: string;
  status: POStatus;
  created_at: string;
  updated_at: string;
}

export interface POLineItem {
  id: string;
  po_id: string;
  line_number: number;
  description: string;
  quantity: number;
  unit_price: number;
  line_total: number;
}

export interface POMatchResult {
  matched: boolean;
  po_number?: string;
  match_score: number;
  match_details?: {
    vendor_match: boolean;
    amount_match: boolean;
    line_items_match: boolean;
  };
}

// ============================================================================
// Vendor Types
// ============================================================================

export interface Vendor {
  id: string;
  vendor_id: string;
  vendor_name: string;
  vendor_code?: string;
  address?: string;
  phone?: string;
  email?: string;
  payment_terms?: string;
  risk_score: number;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Risk Assessment Types
// ============================================================================

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type RiskType = 
  | 'DUPLICATE_INVOICE' 
  | 'VENDOR_MISMATCH' 
  | 'AMOUNT_ANOMALY' 
  | 'PRICE_SPIKE'
  | 'SUSPICIOUS_PATTERN';

export interface RiskFlag {
  type: RiskType;
  severity: RiskLevel;
  description: string;
  confidence: number;
  details?: any;
}

export interface RiskAssessment {
  invoice_id: string;
  risk_level: RiskLevel;
  risk_score: number;
  flags: RiskFlag[];
  recommended_action: string;
  created_at: string;
}

// ============================================================================
// Approval Workflow Types
// ============================================================================

export type ApprovalAction = 'APPROVE' | 'REJECT' | 'REQUEST_REVIEW';

export interface ApprovalRequest {
  invoice_id: string;
  action: ApprovalAction;
  comment?: string;
  reason?: string;
}

export interface ApprovalHistory {
  id: string;
  invoice_id: string;
  user_id: string;
  user_name: string;
  user_role: UserRole;
  action: ApprovalAction;
  comment?: string;
  created_at: string;
}

// ============================================================================
// Dashboard & Analytics Types
// ============================================================================

export interface DashboardMetrics {
  total_invoices: MetricValue;
  stp_rate: MetricValue;
  avg_processing_time: MetricValue;
  pending_approvals: MetricValue;
  risk_flags: MetricValue;
  total_value: MetricValue;
}

export interface MetricValue {
  value: number | string;
  change?: number; // Percentage change
  trend?: 'up' | 'down' | 'neutral';
}

export interface ChartDataPoint {
  date: string;
  value: number;
  label?: string;
}

export interface StatusDistribution {
  status: InvoiceStatus;
  count: number;
  percentage: number;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

// ============================================================================
// Form Types
// ============================================================================

export interface InvoiceUploadForm {
  files: File[];
}

export interface POCreateForm {
  po_number: string;
  vendor_id: string;
  po_date: string;
  total_amount: number;
  currency: string;
  line_items: POLineItem[];
}

export interface VendorForm {
  vendor_name: string;
  vendor_code?: string;
  address?: string;
  phone?: string;
  email?: string;
  payment_terms?: string;
}
