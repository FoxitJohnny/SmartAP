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
  expected_delivery_date?: string;
  notes?: string;
  line_items: Array<{
    line_number: number;
    description: string;
    quantity: number;
    unit_price: number;
  }>;
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

export interface POMatchedInvoice {
  id: string;
  invoice_number: string;
  invoice_date: string;
  total_amount: number;
  matched_amount: number;
  status: string;
  matched_date: string;
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

// API Functions
export const getPurchaseOrders = async (
  page: number = 1,
  filters?: PurchaseOrderFilters
): Promise<{ data: PurchaseOrderListItem[]; total: number; page: number; per_page: number }> => {
  const { data } = await apiClient.get('/purchase-orders', {
    params: { page, ...filters },
  });
  return data;
};

export const getPurchaseOrder = async (id: string): Promise<PurchaseOrder> => {
  const { data } = await apiClient.get(`/purchase-orders/${id}`);
  return data;
};

export const createPurchaseOrder = async (
  request: CreatePurchaseOrderRequest
): Promise<PurchaseOrder> => {
  const { data } = await apiClient.post('/purchase-orders', request);
  return data;
};

export const updatePurchaseOrder = async (
  id: string,
  request: UpdatePurchaseOrderRequest
): Promise<PurchaseOrder> => {
  const { data } = await apiClient.put(`/purchase-orders/${id}`, request);
  return data;
};

export const closePurchaseOrder = async (id: string): Promise<PurchaseOrder> => {
  const { data } = await apiClient.post(`/purchase-orders/${id}/close`);
  return data;
};

export const cancelPurchaseOrder = async (id: string): Promise<PurchaseOrder> => {
  const { data } = await apiClient.post(`/purchase-orders/${id}/cancel`);
  return data;
};

export const importPurchaseOrdersFromERP = async (
  erpSystem: string
): Promise<{ imported: number; errors: string[] }> => {
  const { data } = await apiClient.post('/purchase-orders/import', { erp_system: erpSystem });
  return data;
};

export const getPOMatchedInvoices = async (poId: string): Promise<POMatchedInvoice[]> => {
  const { data } = await apiClient.get(`/purchase-orders/${poId}/invoices`);
  return data;
};

export const getPOMatchingHistory = async (poId: string): Promise<POMatchingHistory[]> => {
  const { data } = await apiClient.get(`/purchase-orders/${poId}/matching-history`);
  return data;
};

// React Query Hooks
export const usePurchaseOrders = (page: number = 1, filters?: PurchaseOrderFilters) => {
  return useQuery({
    queryKey: ['purchase-orders', page, filters],
    queryFn: () => getPurchaseOrders(page, filters),
    staleTime: 30000, // 30 seconds
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
