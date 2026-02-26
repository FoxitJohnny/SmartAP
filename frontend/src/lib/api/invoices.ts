import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  Invoice,
  InvoiceFilters,
  InvoiceUploadResponse,
  PaginatedResponse,
  ApiResponse,
  MatchingResult,
} from '@/types';

// Helper function to transform API response to frontend Invoice type
function transformInvoiceResponse(data: any): Invoice {
  // Handle nested invoice object from extraction API
  const invoiceData = data.invoice || {};
  
  // Transform line items to map 'amount' to 'line_total'
  const transformedLineItems = (invoiceData.line_items || data.line_items || []).map((item: any) => ({
    ...item,
    line_total: parseFloat(String(item.line_total || item.amount || 0)),
    unit_price: parseFloat(String(item.unit_price || 0)),
    quantity: parseFloat(String(item.quantity || 0)),
  }));
  
  return {
    id: data.document_id || data.id,
    document_id: data.document_id || data.id,
    invoice_number: invoiceData.invoice_number || data.invoice_number || 'N/A',
    vendor_id: invoiceData.vendor_id || data.vendor_id,
    vendor_name: invoiceData.vendor_name || data.vendor_name || 'Unknown',
    invoice_date: invoiceData.invoice_date || data.invoice_date,
    due_date: invoiceData.due_date || data.due_date,
    total_amount: parseFloat(invoiceData.total || data.total_amount || data.amount || '0'),
    tax_amount: parseFloat(invoiceData.tax || data.tax_amount || '0'),
    subtotal: parseFloat(invoiceData.subtotal || data.subtotal || '0'),
    currency: invoiceData.currency || data.currency || 'USD',
    po_number: invoiceData.po_number || data.po_number,
    status: data.status?.toUpperCase?.() || data.status || 'PENDING',
    confidence_score: data.confidence?.total || data.confidence_score,
    risk_score: data.risk_assessment?.risk_score ?? data.risk_score,
    risk_level: (data.risk_assessment?.risk_level || data.risk_level || '').toUpperCase() as any || undefined,
    risk_flags: data.risk_assessment?.risk_flags ?? data.risk_flags,
    risk_assessment: data.risk_assessment,
    line_items: transformedLineItems,
    ocr_data: data.ocr_data,
    file_path: data.file_path || `/api/v1/invoices/${data.document_id}/pdf`,
    file_hash: data.file_hash || '',
    created_at: data.created_at,
    updated_at: data.updated_at,
  };
}

// API functions
export const invoiceApi = {
  // List invoices with pagination and filtering
  getInvoices: async (
    page: number = 1,
    limit: number = 20,
    filters?: InvoiceFilters
  ): Promise<PaginatedResponse<Invoice>> => {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: limit.toString(),
    });

    if (filters?.status) params.append('status', filters.status);
    if (filters?.vendor_name) params.append('vendor_name', filters.vendor_name);
    if (filters?.min_amount) params.append('min_amount', filters.min_amount.toString());
    if (filters?.max_amount) params.append('max_amount', filters.max_amount.toString());
    if (filters?.start_date) params.append('start_date', filters.start_date);
    if (filters?.end_date) params.append('end_date', filters.end_date);
    if (filters?.has_risk_flags !== undefined) {
      params.append('has_risk_flags', filters.has_risk_flags.toString());
    }
    if (filters?.search) params.append('search', filters.search);

    const response = await apiClient.get<PaginatedResponse<any>>(
      `/invoices?${params.toString()}`
    );
    
    // Transform items to normalize the response structure
    const transformedItems = response.data.items?.map((item: any) => ({
      ...item,
      total_amount: item.total_amount ?? item.amount ?? 0,
      status: item.status?.toUpperCase?.() || item.status,
    })) || [];
    
    return {
      ...response.data,
      items: transformedItems,
    };
  },

  // Get single invoice by ID
  getInvoice: async (id: string): Promise<Invoice> => {
    const response = await apiClient.get(`/invoices/${id}`);
    return transformInvoiceResponse(response.data);
  },

  // Upload invoice file
  uploadInvoice: async (
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<InvoiceUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<InvoiceUploadResponse>(
      '/invoices/upload',
      formData,
      {
        headers: {
          'Content-Type': undefined, // Let axios set multipart/form-data with boundary
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total && onProgress) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        },
      }
    );
    return response.data;
  },

  // Update invoice
  updateInvoice: async (id: string, data: Partial<Invoice>): Promise<Invoice> => {
    const response = await apiClient.put<Invoice>(`/invoices/${id}`, data);
    return response.data;
  },

  // Delete invoice
  deleteInvoice: async (id: string): Promise<void> => {
    await apiClient.delete(`/invoices/${id}`);
  },

  // Approve invoice
  approveInvoice: async (id: string, comment?: string): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(`/invoices/${id}/approve`, {
      comment,
    });
    return response.data;
  },

  // Reject invoice
  rejectInvoice: async (id: string, reason: string): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(`/invoices/${id}/reject`, {
      reason,
    });
    return response.data;
  },

  // Retry OCR processing
  retryOCR: async (id: string): Promise<Invoice> => {
    const response = await apiClient.post<Invoice>(`/invoices/${id}/retry-ocr`);
    return response.data;
  },

  // Get latest matching result (null if none)
  getMatchingResult: async (id: string): Promise<MatchingResult | null> => {
    try {
      const response = await apiClient.get<MatchingResult>(`/invoices/${id}/matching-result`);
      return response.data;
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 404) return null;
      throw err;
    }
  },
};

// React Query hooks
export function useInvoices(
  page: number = 1,
  limit: number = 20,
  filters?: InvoiceFilters
) {
  return useQuery({
    queryKey: ['invoices', page, limit, filters],
    queryFn: () => invoiceApi.getInvoices(page, limit, filters),
    staleTime: 30 * 1000, // 30 seconds
    refetchOnMount: 'always', // Always refetch when component mounts
  });
}

export function useInvoice(id: string) {
  return useQuery({
    queryKey: ['invoice', id],
    queryFn: () => invoiceApi.getInvoice(id),
    enabled: !!id,
  });
}

export function useInvoiceMatchingResult(id: string) {
  return useQuery({
    queryKey: ['invoice', id, 'matchingResult'],
    queryFn: () => invoiceApi.getMatchingResult(id),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}

export function useUploadInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ file, onProgress }: { file: File; onProgress?: (progress: number) => void }) =>
      invoiceApi.uploadInvoice(file, onProgress),
    onSuccess: () => {
      // Invalidate invoice list to refetch
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}

export function useUpdateInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Invoice> }) =>
      invoiceApi.updateInvoice(id, data),
    onSuccess: (_, variables) => {
      // Invalidate both list and detail views
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['invoice', variables.id] });
    },
  });
}

export function useDeleteInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => invoiceApi.deleteInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
    },
  });
}

export function useApproveInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, comment }: { id: string; comment?: string }) =>
      invoiceApi.approveInvoice(id, comment),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['invoice', variables.id] });
    },
  });
}

export function useRejectInvoice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      invoiceApi.rejectInvoice(id, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['invoices'] });
      queryClient.invalidateQueries({ queryKey: ['invoice', variables.id] });
    },
  });
}

export function useRetryOCR() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => invoiceApi.retryOCR(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['invoice', id] });
    },
  });
}
