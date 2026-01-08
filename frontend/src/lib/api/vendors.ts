import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from './client';

// Types
export interface Vendor {
  id: string;
  name: string;
  vendor_code: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  tax_id?: string;
  payment_terms?: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  total_invoices: number;
  total_amount: number;
  avg_invoice_amount: number;
  on_time_payment_rate: number;
  duplicate_attempts: number;
  price_variance_rate: number;
  active: boolean;
  created_date: string;
  last_invoice_date?: string;
  notes?: string;
}

export interface VendorListItem {
  id: string;
  name: string;
  vendor_code: string;
  email?: string;
  phone?: string;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  total_invoices: number;
  total_amount: number;
  on_time_payment_rate: number;
  active: boolean;
  last_invoice_date?: string;
}

export interface VendorFilters {
  search?: string;
  risk_level?: string;
  active?: boolean;
  min_risk_score?: number;
  max_risk_score?: number;
}

export interface CreateVendorRequest {
  name: string;
  vendor_code: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  tax_id?: string;
  payment_terms?: string;
  notes?: string;
}

export interface UpdateVendorRequest {
  name?: string;
  email?: string;
  phone?: string;
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
  country?: string;
  tax_id?: string;
  payment_terms?: string;
  active?: boolean;
  notes?: string;
}

export interface VendorInvoiceHistory {
  id: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  total_amount: number;
  status: string;
  risk_level: string;
  payment_date?: string;
  days_to_pay?: number;
}

export interface VendorRiskEvent {
  id: string;
  event_type: 'DUPLICATE' | 'PRICE_VARIANCE' | 'PAYMENT_DELAY' | 'MISSING_PO' | 'OTHER';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  invoice_id?: string;
  invoice_number?: string;
  detected_date: string;
  resolved: boolean;
  resolved_date?: string;
}

export interface VendorRiskHistory {
  date: string;
  risk_score: number;
  risk_level: string;
  reason?: string;
}

export interface VendorPerformanceMetrics {
  total_invoices: number;
  total_amount: number;
  avg_invoice_amount: number;
  avg_processing_time: number;
  on_time_payment_rate: number;
  duplicate_attempts: number;
  price_variance_rate: number;
  rejection_rate: number;
  avg_days_to_pay: number;
  invoices_by_month: Array<{ month: string; count: number; amount: number }>;
  risk_events_by_type: Array<{ type: string; count: number }>;
}

// API Functions
export const getVendors = async (
  page: number = 1,
  filters?: VendorFilters
): Promise<{ data: VendorListItem[]; total: number; page: number; per_page: number }> => {
  const { data } = await apiClient.get('/vendors', {
    params: { page, ...filters },
  });
  return data;
};

export const getVendor = async (id: string): Promise<Vendor> => {
  const { data } = await apiClient.get(`/vendors/${id}`);
  return data;
};

export const createVendor = async (request: CreateVendorRequest): Promise<Vendor> => {
  const { data } = await apiClient.post('/vendors', request);
  return data;
};

export const updateVendor = async (id: string, request: UpdateVendorRequest): Promise<Vendor> => {
  const { data } = await apiClient.put(`/vendors/${id}`, request);
  return data;
};

export const deactivateVendor = async (id: string): Promise<Vendor> => {
  const { data } = await apiClient.post(`/vendors/${id}/deactivate`);
  return data;
};

export const activateVendor = async (id: string): Promise<Vendor> => {
  const { data } = await apiClient.post(`/vendors/${id}/activate`);
  return data;
};

export const getVendorInvoiceHistory = async (
  vendorId: string,
  page: number = 1
): Promise<{ data: VendorInvoiceHistory[]; total: number }> => {
  const { data } = await apiClient.get(`/vendors/${vendorId}/invoices`, {
    params: { page },
  });
  return data;
};

export const getVendorRiskEvents = async (
  vendorId: string
): Promise<VendorRiskEvent[]> => {
  const { data } = await apiClient.get(`/vendors/${vendorId}/risk-events`);
  return data;
};

export const getVendorRiskHistory = async (
  vendorId: string
): Promise<VendorRiskHistory[]> => {
  const { data } = await apiClient.get(`/vendors/${vendorId}/risk-history`);
  return data;
};

export const getVendorPerformanceMetrics = async (
  vendorId: string
): Promise<VendorPerformanceMetrics> => {
  const { data } = await apiClient.get(`/vendors/${vendorId}/performance`);
  return data;
};

// React Query Hooks
export const useVendors = (page: number = 1, filters?: VendorFilters) => {
  return useQuery({
    queryKey: ['vendors', page, filters],
    queryFn: () => getVendors(page, filters),
    staleTime: 30000, // 30 seconds
  });
};

export const useVendor = (id: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ['vendor', id],
    queryFn: () => getVendor(id),
    enabled: enabled && !!id,
    staleTime: 60000, // 1 minute
  });
};

export const useVendorInvoiceHistory = (vendorId: string, page: number = 1) => {
  return useQuery({
    queryKey: ['vendor-invoice-history', vendorId, page],
    queryFn: () => getVendorInvoiceHistory(vendorId, page),
    staleTime: 60000,
  });
};

export const useVendorRiskEvents = (vendorId: string) => {
  return useQuery({
    queryKey: ['vendor-risk-events', vendorId],
    queryFn: () => getVendorRiskEvents(vendorId),
    staleTime: 60000,
  });
};

export const useVendorRiskHistory = (vendorId: string) => {
  return useQuery({
    queryKey: ['vendor-risk-history', vendorId],
    queryFn: () => getVendorRiskHistory(vendorId),
    staleTime: 60000,
  });
};

export const useVendorPerformanceMetrics = (vendorId: string) => {
  return useQuery({
    queryKey: ['vendor-performance', vendorId],
    queryFn: () => getVendorPerformanceMetrics(vendorId),
    staleTime: 60000,
  });
};

export const useCreateVendor = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createVendor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
    },
  });
};

export const useUpdateVendor = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, request }: { id: string; request: UpdateVendorRequest }) =>
      updateVendor(id, request),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['vendor', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
    },
  });
};

export const useDeactivateVendor = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deactivateVendor,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['vendor', id] });
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
    },
  });
};

export const useActivateVendor = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: activateVendor,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['vendor', id] });
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
    },
  });
};
