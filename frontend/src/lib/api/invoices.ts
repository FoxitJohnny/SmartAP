import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  Invoice,
  InvoiceFilters,
  InvoiceUploadResponse,
  PaginatedResponse,
  ApiResponse,
} from '@/types';

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

    const response = await apiClient.get<PaginatedResponse<Invoice>>(
      `/invoices?${params.toString()}`
    );
    return response.data;
  },

  // Get single invoice by ID
  getInvoice: async (id: string): Promise<Invoice> => {
    const response = await apiClient.get<Invoice>(`/invoices/${id}`);
    return response.data;
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
          'Content-Type': 'multipart/form-data',
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
  });
}

export function useInvoice(id: string) {
  return useQuery({
    queryKey: ['invoice', id],
    queryFn: () => invoiceApi.getInvoice(id),
    enabled: !!id,
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
