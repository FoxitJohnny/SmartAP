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
  department?: string;
  created_at?: string;
  updated_at?: string;
}

export type UserRole = 'admin' | 'finance_manager' | 'accountant' | 'viewer' | 'AP_CLERK' | 'MANAGER' | 'AUDITOR' | 'ADMIN';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    email: string;
    full_name: string;
    role: string;
    department?: string;
    is_active: boolean;
  };
}

// ============================================================================
// Invoice Types
// ============================================================================

export type InvoiceStatus = 
  | 'INGESTED' 
  | 'EXTRACTED' 
  | 'MATCHED' 
  | 'PENDING_APPROVAL'
  | 'RISK_REVIEW' 
  | 'APPROVED' 
  | 'REJECTED'
  | 'READY_FOR_PAYMENT' 
  | 'ARCHIVED'
  | 'FAILED';

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
  risk_score?: number;
  risk_level?: RiskLevel;
  risk_flags?: RiskFlag[];
  risk_assessment?: RiskAssessment;
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
// Matching Types
// ============================================================================

export type MatchType =
  | 'exact'
  | 'fuzzy'
  | 'partial'
  | 'line_item'
  | 'manual'
  | 'no_match'
  | 'none';

export type DiscrepancySeverity = 'low' | 'medium' | 'high' | 'critical';

export interface MatchingDiscrepancy {
  discrepancy_type: string;
  severity: DiscrepancySeverity;
  description: string;
  line_number?: number | null;
  item_description?: string | null;
  invoice_value?: string | null;
  po_value?: string | null;
  difference?: string | null;
  difference_percentage?: number | null;
  requires_approval?: boolean;
  resolution_notes?: string | null;
}

export interface MatchingResult {
  matching_id: string;
  invoice_id: string;
  po_id?: string | null;
  po_number?: string | null;
  match_type: MatchType;
  match_score: number;
  matched: boolean;

  vendor_match_score: number;
  amount_match_score: number;
  date_match_score: number;
  line_items_match_score: number;

  discrepancies: MatchingDiscrepancy[];
  has_discrepancies: boolean;
  critical_discrepancies: number;

  requires_approval: boolean;
  approval_reason?: string | null;

  matched_at?: string;
  matched_by?: string | null;
  ai_evaluation?: any;
}

export interface MatchingSettings {
  id: number;
  name: string;

  vendor_fuzzy_threshold: number;
  vendor_match_weight: number;

  amount_tolerance_percent: number;
  amount_match_tolerance: number;
  amount_match_weight: number;

  date_tolerance_days: number;
  date_match_weight: number;

  line_items_match_weight: number;
  line_item_description_threshold: number;
  line_item_amount_tolerance: number;

  exact_match_threshold: number;
  good_match_threshold: number;
  acceptable_match_threshold: number;
  review_threshold: number;

  use_ai_for_ambiguous: boolean;
  ai_confidence_threshold: number;

  max_amount_discrepancy_for_auto_approve: number;
  critical_discrepancy_blocks_approval: boolean;
}

// ============================================================================
// Risk Settings Types
// ============================================================================

export interface RiskSettings {
  id: number;
  name: string;

  // Component weights
  weight_duplicate: number;
  weight_vendor: number;
  weight_price: number;
  weight_amount: number;
  weight_matching: number;
  weight_pattern: number;

  // Price anomaly detection
  price_std_dev_threshold: number;
  price_min_historical_invoices: number;
  price_significant_amount: number;
  price_minor_increase: number;
  price_major_increase: number;
  price_critical_increase: number;

  // Duplicate detection
  duplicate_exact_days: number;
  duplicate_fuzzy_days: number;
  duplicate_amount_tolerance: number;

  // Vendor risk
  vendor_low_risk_threshold: number;
  vendor_medium_risk_threshold: number;
  vendor_high_risk_threshold: number;
  vendor_good_payment_reliability: number;
  vendor_acceptable_payment_reliability: number;
  vendor_inactive_days: number;
  vendor_new_vendor_days: number;
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
  | 'duplicate_exact'
  | 'duplicate_near'
  | 'duplicate_fuzzy'
  | 'vendor_spoofing'
  | 'vendor_new'
  | 'vendor_blocked'
  | 'price_anomaly'
  | 'amount_anomaly'
  | 'matching_no_match'
  | 'matching_low_score'
  | 'matching_discrepancy'
  | 'suspicious_pattern';

export interface RiskFlag {
  flag_type: RiskType;
  severity: string;          // lowercase: low | medium | high | critical
  description: string;
  confidence?: number;
  evidence?: string;
  expected_value?: string;
  actual_value?: string;
  deviation?: string;
  suggested_action?: string;
  related_invoice_id?: string;
  details?: any;
}

export interface RiskAssessment {
  invoice_id?: string;
  assessment_id: string;
  risk_level: RiskLevel;
  risk_score: number;
  duplicate_risk_score?: number;
  vendor_risk_score?: number;
  price_risk_score?: number;
  amount_risk_score?: number;
  matching_risk_score?: number;
  pattern_risk_score?: number;
  risk_flags: RiskFlag[];
  critical_flags?: number;
  high_flags?: number;
  duplicate_info?: any;
  vendor_risk_info?: any;
  price_anomaly_info?: any;
  recommended_action: string;
  action_reason?: string;
  requires_manual_review?: boolean;
  assessed_at?: string;
  assessed_by?: string;
  assessment_version?: string;
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
// Processing Events (Workflow Logs)
// ============================================================================

export type ProcessingEventLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
export type ProcessingEventStatus = 'started' | 'succeeded' | 'failed';

export interface ProcessingEvent {
  id: number;
  entity_type: string;
  entity_id: string;
  stage: string;
  status: ProcessingEventStatus;
  level: ProcessingEventLevel;
  message: string;
  details?: Record<string, unknown> | null;
  correlation_id?: string | null;
  created_at: string;
}

export interface ProcessingEventListResponse {
  items: ProcessingEvent[];
  total: number;
  page: number;
  limit: number;
  pages: number;
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
