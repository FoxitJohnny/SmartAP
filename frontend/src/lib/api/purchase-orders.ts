import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from './client';

// Types
export interface PurchaseOrderLineItem {
  id: string;
  line_number: number;
  description: string;
  quantity: number;
  unit_price: number;
  total_amount: number;
  received_quantity: number;
  matched_quantity: number;
}

export interface PurchaseOrder {
  id: string;
  po_number: string;
  vendor_id: string;
  vendor_name: string;
  status: 'OPEN' | 'PARTIALLY_MATCHED' | 'CLOSED' | 'CANCELLED';
  created_date: string;
  expected_delivery_date?: string;
  total_amount: number;
  matched_amount: number;
  matched_invoices_count: number;
  line_items: PurchaseOrderLineItem[];
  notes?: string;
  created_by: string;
  last_updated: string;
}

export interface PurchaseOrderListItem {
  id: string;
  po_number: string;
  vendor_id: string;
  vendor_name: string;
  status: 'OPEN' | 'PARTIALLY_MATCHED' | 'CLOSED' | 'CANCELLED';
  created_date: string;
  expected_delivery_date?: string;
  total_amount: number;
  matched_amount: number;
  matched_invoices_count: number;
}

export interface PurchaseOrderFilters {
  search?: string;
  status?: string;
  vendor_id?: string;
  start_date?: string;
  end_date?: string;
  min_amount?: number;
  max_amount?: number;
}

export interface CreatePurchaseOrderRequest {
  po_number: string;
  vendor_id: string;
  total_amount: number;
  currency?: string;
  status?: 'open' | 'partial' | 'partially_received' | 'closed' | 'cancelled';
  order_date?: string; // YYYY-MM-DD
  expected_date?: string; // YYYY-MM-DD
}

export interface UpdatePurchaseOrderRequest {
  expected_delivery_date?: string;
  notes?: string;
  line_items?: Array<{
    id?: string;
    line_number: number;
    description: string;
    quantity: number;
    unit_price: number;
  }>;
}

export interface POMatchedInvoiceLineItem {
  line_number: number;
  description: string;
  quantity: number;
  unit_price: number;
  amount: number;
  sku?: string;
}

export interface POMatchedInvoice {
  id: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: number;
  matched_amount: number;
  status: string;
  matched_date: string;
  match_score?: number;
  vendor_name?: string;
  po_number?: string;
  line_items?: POMatchedInvoiceLineItem[];
}

export interface POMatchingHistory {
  id: string;
  invoice_id: string;
  invoice_number: string;
  matched_amount: number;
  matched_date: string;
  matched_by: string;
  line_items_matched: number;
}

// Transform API response to match frontend expected format
function transformPurchaseOrderListItem(item: Record<string, unknown>): PurchaseOrderListItem {
  return {
    id: String(item.id),
    po_number: String(item.po_number || ''),
    vendor_id: String(item.vendor_id || ''),
    vendor_name: String(item.vendor_name || ''),
    status: (String(item.status || 'open').toUpperCase()) as PurchaseOrderListItem['status'],
    created_date: String(item.order_date || item.created_at || ''),
    expected_delivery_date: item.expected_date ? String(item.expected_date) : undefined,
    total_amount: Number(item.amount || item.total_amount || 0),
    matched_amount: Number(item.received_amount || item.matched_amount || 0),
    matched_invoices_count: Number(item.matched_invoices_count || 0),
  };
}

function transformPurchaseOrderLineItem(item: Record<string, unknown>, index: number): PurchaseOrderLineItem {
  const quantity = Number(item.quantity || 0);
  const unitPrice = Number(item.unit_price || item.unitPrice || 0);

  return {
    id: String(item.id ?? `line-${index}`),
    line_number: Number(item.line_number ?? item.lineNumber ?? index + 1),
    description: String(item.description || ''),
    quantity,
    unit_price: unitPrice,
    total_amount: Number(item.total_amount ?? item.totalAmount ?? quantity * unitPrice),
    received_quantity: Number(item.received_quantity ?? item.receivedQuantity ?? 0),
    matched_quantity: Number(item.matched_quantity ?? item.matchedQuantity ?? 0),
  };
}

function transformPurchaseOrder(item: Record<string, unknown>): PurchaseOrder {
  const lineItemsRaw = (item.line_items || item.items || []) as unknown[];
  const line_items = Array.isArray(lineItemsRaw)
    ? lineItemsRaw.map((li, idx) => transformPurchaseOrderLineItem((li || {}) as Record<string, unknown>, idx))
    : [];

  const createdDate = String(item.order_date || item.created_at || item.created_date || '');
  const lastUpdated = String(item.updated_at || item.last_updated || item.created_at || createdDate);

  return {
    id: String(item.id),
    po_number: String(item.po_number || ''),
    vendor_id: String(item.vendor_id || ''),
    vendor_name: String(item.vendor_name || ''),
    status: (String(item.status || 'open').toUpperCase()) as PurchaseOrder['status'],
    created_date: createdDate,
    expected_delivery_date: item.expected_date
      ? String(item.expected_date)
      : item.expected_delivery_date
        ? String(item.expected_delivery_date)
        : undefined,
    total_amount: Number(item.amount || item.total_amount || 0),
    matched_amount: Number(item.received_amount || item.matched_amount || 0),
    matched_invoices_count: Number(item.matched_invoices_count || 0),
    line_items,
    notes: item.notes ? String(item.notes) : undefined,
    created_by: String(item.created_by || 'System'),
    last_updated: lastUpdated,
  };
}

// API Functions
export const getPurchaseOrders = async (
  page: number = 1,
  filters?: PurchaseOrderFilters
): Promise<{ data: PurchaseOrderListItem[]; total: number; page: number; per_page: number }> => {
  const { data } = await apiClient.get('/purchase-orders', {
    params: { page, ...filters },
  });
  // Transform API response (items -> data, and map fields)
  const items = data.items || data.data || [];
  return {
    data: items.map(transformPurchaseOrderListItem),
    total: data.total || 0,
    page: data.page || 1,
    per_page: data.limit || data.per_page || 20,
  };
};

export const getPurchaseOrder = async (id: string): Promise<PurchaseOrder> => {
  const { data } = await apiClient.get(`/purchase-orders/${id}`);
  return transformPurchaseOrder(data);
};

export const createPurchaseOrder = async (
  request: CreatePurchaseOrderRequest
): Promise<PurchaseOrder> => {
  const { data } = await apiClient.post('/purchase-orders', request);
  return transformPurchaseOrder(data);
};

export const updatePurchaseOrder = async (
  id: string,
  request: UpdatePurchaseOrderRequest
): Promise<PurchaseOrder> => {
  const { data } = await apiClient.put(`/purchase-orders/${id}`, request);
  return transformPurchaseOrder(data);
};

export const closePurchaseOrder = async (id: string): Promise<PurchaseOrder> => {
  const { data } = await apiClient.post(`/purchase-orders/${id}/close`);
  return transformPurchaseOrder(data);
};

export const cancelPurchaseOrder = async (id: string): Promise<PurchaseOrder> => {
  const { data } = await apiClient.post(`/purchase-orders/${id}/cancel`);
  return transformPurchaseOrder(data);
};

export const importPurchaseOrdersFromERP = async (
  erpSystem: string
): Promise<{ imported: number; errors: string[] }> => {
  const { data } = await apiClient.post('/purchase-orders/import', { erp_system: erpSystem });
  return data;
};

export const getPOMatchedInvoices = async (poId: string): Promise<POMatchedInvoice[]> => {
  const { data } = await apiClient.get(`/purchase-orders/${poId}/invoices`);
  const items = data.items || [];
  return items.map((item: Record<string, unknown>) => ({
    id: String(item.id || ''),
    invoice_number: String(item.invoice_number || ''),
    invoice_date: String(item.invoice_date || ''),
    total_amount: Number(item.total_amount || item.amount || 0),
    matched_amount: Number(item.matched_amount || 0),
    status: String(item.status || ''),
    matched_date: String(item.matched_date || ''),
    match_score: item.match_score != null ? Number(item.match_score) : undefined,
    vendor_name: item.vendor_name ? String(item.vendor_name) : undefined,
    po_number: item.po_number ? String(item.po_number) : undefined,
    line_items: Array.isArray(item.line_items)
      ? (item.line_items as Record<string, unknown>[]).map((li, idx) => ({
          line_number: Number(li.line_number ?? idx + 1),
          description: String(li.description || ''),
          quantity: Number(li.quantity || 0),
          unit_price: Number(li.unit_price || 0),
          amount: Number(li.amount || 0),
          sku: li.sku ? String(li.sku) : undefined,
        }))
      : undefined,
  }));
};

export const getPOMatchingHistory = async (poId: string): Promise<POMatchingHistory[]> => {
  const { data } = await apiClient.get(`/purchase-orders/${poId}/matching-history`);
  return data.items || [];
};

// React Query Hooks
export const usePurchaseOrders = (page: number = 1, filters?: PurchaseOrderFilters) => {
  return useQuery({
    queryKey: ['purchase-orders', page, filters],
    queryFn: () => getPurchaseOrders(page, filters),
    staleTime: 0, // Always refetch
  });
};

export const usePurchaseOrder = (id: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ['purchase-order', id],
    queryFn: () => getPurchaseOrder(id),
    enabled: enabled && !!id,
    staleTime: 60000, // 1 minute
  });
};

export const usePOMatchedInvoices = (poId: string) => {
  return useQuery({
    queryKey: ['po-matched-invoices', poId],
    queryFn: () => getPOMatchedInvoices(poId),
    staleTime: 60000,
  });
};

export const usePOMatchingHistory = (poId: string) => {
  return useQuery({
    queryKey: ['po-matching-history', poId],
    queryFn: () => getPOMatchingHistory(poId),
    staleTime: 60000,
  });
};

export const useCreatePurchaseOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createPurchaseOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });
};

export const useUpdatePurchaseOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: UpdatePurchaseOrderRequest }) =>
      updatePurchaseOrder(id, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['purchase-order', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });
};

export const useClosePurchaseOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: closePurchaseOrder,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['purchase-order', id] });
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });
};

export const useCancelPurchaseOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: cancelPurchaseOrder,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['purchase-order', id] });
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });
};

export const useImportPurchaseOrders = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: importPurchaseOrdersFromERP,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
    },
  });
};
