import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type {
  ProcessingEventListResponse,
  ProcessingEventLevel,
  ProcessingEventStatus,
} from '@/types';

export interface ProcessingEventFilters {
  entity_type?: string;
  entity_id?: string;
  stage?: string;
  status?: ProcessingEventStatus;
  level?: ProcessingEventLevel;
  correlation_id?: string;
  q?: string;
}

export const processingApi = {
  listEvents: async (
    page: number = 1,
    limit: number = 50,
    filters?: ProcessingEventFilters
  ): Promise<ProcessingEventListResponse> => {
    const params = new URLSearchParams({
      page: String(page),
      limit: String(limit),
    });

    if (filters?.entity_type) params.set('entity_type', filters.entity_type);
    if (filters?.entity_id) params.set('entity_id', filters.entity_id);
    if (filters?.stage) params.set('stage', filters.stage);
    if (filters?.status) params.set('status', filters.status);
    if (filters?.level) params.set('level', filters.level);
    if (filters?.correlation_id) params.set('correlation_id', filters.correlation_id);
    if (filters?.q) params.set('q', filters.q);

    const response = await apiClient.get<ProcessingEventListResponse>(
      `/processing/events?${params.toString()}`
    );

    return response.data;
  },

  clearEvents: async (): Promise<{ deleted: number }> => {
    const response = await apiClient.delete<{ deleted: number }>('/processing/events');
    return response.data;
  },
};

export function useProcessingEvents(
  page: number = 1,
  limit: number = 50,
  filters?: ProcessingEventFilters
) {
  return useQuery({
    queryKey: ['processingEvents', page, limit, filters],
    queryFn: () => processingApi.listEvents(page, limit, filters),
    enabled: true,
    staleTime: 5 * 1000,
  });
}

export function useInvoiceProcessingEvents(
  invoiceId: string,
  page: number = 1,
  limit: number = 50
) {
  return useProcessingEvents(page, limit, {
    entity_type: 'invoice',
    entity_id: invoiceId,
  });
}

export function useClearProcessingEvents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => processingApi.clearEvents(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processingEvents'] });
    },
  });
}
