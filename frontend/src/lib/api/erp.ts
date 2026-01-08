/**
 * ERP Integration API Client
 * 
 * Provides functions for interacting with the ERP integration API endpoints.
 */

import { apiClient } from './client';

export interface ERPConnection {
  id: string;
  name: string;
  system_type: 'quickbooks' | 'xero' | 'sap' | 'sage' | 'netsuite' | 'oracle' | 'dynamics';
  status: 'active' | 'inactive' | 'error' | 'pending';
  tenant_id?: string;
  company_db?: string;
  api_url?: string;
  last_connected_at?: string;
  last_sync_at?: string;
  connection_error?: string;
  auto_sync_enabled: boolean;
  sync_interval_minutes: number;
  created_at: string;
  updated_at: string;
  created_by: string;
}

export interface ERPConnectionCreate {
  name: string;
  system_type: string;
  credentials: Record<string, any>;
  tenant_id?: string;
  company_db?: string;
  api_url?: string;
  auto_sync_enabled?: boolean;
  sync_interval_minutes?: number;
}

export interface ERPConnectionUpdate {
  name?: string;
  credentials?: Record<string, any>;
  tenant_id?: string;
  company_db?: string;
  api_url?: string;
  auto_sync_enabled?: boolean;
  sync_interval_minutes?: number;
}

export interface ERPSyncLog {
  id: string;
  connection_id: string;
  entity_type: 'vendor' | 'purchase_order' | 'invoice' | 'payment' | 'account' | 'tax_code';
  sync_direction: 'import' | 'export';
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'partial';
  started_at: string;
  completed_at?: string;
  duration_seconds?: number;
  total_count: number;
  success_count: number;
  error_count: number;
  errors?: string[];
  error_message?: string;
  sync_params?: Record<string, any>;
  triggered_by: string;
}

export interface ERPFieldMapping {
  id: string;
  connection_id: string;
  entity_type: string;
  smartap_field: string;
  erp_field: string;
  transformation_rule?: string;
  default_value?: string;
  is_required: boolean;
  validation_regex?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface SyncRequest {
  since?: string;
  status_filter?: string;
  limit?: number;
}

export interface TestConnectionResponse {
  success: boolean;
  company_name?: string;
  country?: string;
  connected_at?: string;
}

export interface SyncResponse {
  sync_log_id: string;
  status: string;
  started_at: string;
}

export interface InvoiceExportRequest {
  connection_id: string;
}

export interface InvoiceExportResponse {
  success: boolean;
  external_id?: string;
  external_number?: string;
  exported_at: string;
  error_message?: string;
}

// ==================== Connection Management ====================

export const erpApi = {
  // Connections
  async listConnections(params?: { system_type?: string; status?: string }): Promise<ERPConnection[]> {
    const response = await apiClient.get('/erp/connections', { params });
    return response.data;
  },

  async getConnection(connectionId: string): Promise<ERPConnection> {
    const response = await apiClient.get(`/erp/connections/${connectionId}`);
    return response.data;
  },

  async createConnection(data: ERPConnectionCreate): Promise<ERPConnection> {
    const response = await apiClient.post('/erp/connections', data);
    return response.data;
  },

  async updateConnection(connectionId: string, data: ERPConnectionUpdate): Promise<ERPConnection> {
    const response = await apiClient.put(`/erp/connections/${connectionId}`, data);
    return response.data;
  },

  async deleteConnection(connectionId: string): Promise<void> {
    await apiClient.delete(`/erp/connections/${connectionId}`);
  },

  async testConnection(connectionId: string): Promise<TestConnectionResponse> {
    const response = await apiClient.post(`/erp/connections/${connectionId}/test`);
    return response.data;
  },

  async authenticate(connectionId: string): Promise<{ success: boolean; authenticated_at: string }> {
    const response = await apiClient.post(`/erp/connections/${connectionId}/authenticate`);
    return response.data;
  },

  // Sync Operations
  async syncVendors(connectionId: string, request?: SyncRequest): Promise<SyncResponse> {
    const response = await apiClient.post(`/erp/connections/${connectionId}/sync/vendors`, request || {});
    return response.data;
  },

  async syncPurchaseOrders(connectionId: string, request?: SyncRequest): Promise<SyncResponse> {
    const response = await apiClient.post(`/erp/connections/${connectionId}/sync/purchase-orders`, request || {});
    return response.data;
  },

  async exportInvoice(invoiceId: string, request: InvoiceExportRequest): Promise<InvoiceExportResponse> {
    const response = await apiClient.post(`/erp/invoices/${invoiceId}/export`, request);
    return response.data;
  },

  async syncInvoicePayment(invoiceId: string): Promise<{ success: boolean; payment_status: string; payment_amount: number; synced_at: string }> {
    const response = await apiClient.post(`/erp/invoices/${invoiceId}/sync-payment`);
    return response.data;
  },

  // Sync Logs
  async listSyncLogs(params?: {
    connection_id?: string;
    entity_type?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<ERPSyncLog[]> {
    const response = await apiClient.get('/erp/sync-logs', { params });
    return response.data;
  },

  async getSyncLog(logId: string): Promise<ERPSyncLog> {
    const response = await apiClient.get(`/erp/sync-logs/${logId}`);
    return response.data;
  },

  // Field Mappings
  async listFieldMappings(connectionId: string, entityType?: string): Promise<ERPFieldMapping[]> {
    const response = await apiClient.get(`/erp/connections/${connectionId}/field-mappings`, {
      params: { entity_type: entityType }
    });
    return response.data;
  },

  async createFieldMapping(connectionId: string, data: Partial<ERPFieldMapping>): Promise<ERPFieldMapping> {
    const response = await apiClient.post(`/erp/connections/${connectionId}/field-mappings`, data);
    return response.data;
  },

  async updateFieldMapping(mappingId: string, data: Partial<ERPFieldMapping>): Promise<ERPFieldMapping> {
    const response = await apiClient.put(`/erp/field-mappings/${mappingId}`, data);
    return response.data;
  },

  async deleteFieldMapping(mappingId: string): Promise<void> {
    await apiClient.delete(`/erp/field-mappings/${mappingId}`);
  },

  // Accounts & Tax Codes
  async getAccounts(connectionId: string): Promise<any[]> {
    const response = await apiClient.get(`/erp/connections/${connectionId}/accounts`);
    return response.data;
  },

  async getTaxCodes(connectionId: string): Promise<any[]> {
    const response = await apiClient.get(`/erp/connections/${connectionId}/tax-codes`);
    return response.data;
  },
};
