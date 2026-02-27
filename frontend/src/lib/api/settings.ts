import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { MatchingSettings, RiskSettings } from '@/types';

export type MatchingSettingsUpdate = Partial<Omit<MatchingSettings, 'id' | 'name'>> & {
  updated_by?: string;
};

export type RiskSettingsUpdate = Partial<Omit<RiskSettings, 'id' | 'name'>> & {
  updated_by?: string;
};

export const settingsApi = {
  getMatchingSettings: async (): Promise<MatchingSettings> => {
    const res = await apiClient.get<MatchingSettings>('/settings/matching');
    return res.data;
  },

  updateMatchingSettings: async (data: MatchingSettingsUpdate): Promise<MatchingSettings> => {
    const res = await apiClient.put<MatchingSettings>('/settings/matching', data);
    return res.data;
  },

  resetMatchingSettings: async (): Promise<MatchingSettings> => {
    const res = await apiClient.post<MatchingSettings>('/settings/matching/reset');
    return res.data;
  },
};

export function useMatchingSettings() {
  return useQuery({
    queryKey: ['settings', 'matching'],
    queryFn: () => settingsApi.getMatchingSettings(),
    staleTime: 60 * 1000,
  });
}

export function useUpdateMatchingSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: MatchingSettingsUpdate) => settingsApi.updateMatchingSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'matching'] });
    },
  });
}

export function useResetMatchingSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => settingsApi.resetMatchingSettings(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'matching'] });
    },
  });
}

// ============================================================================
// Risk Settings
// ============================================================================

export const riskSettingsApi = {
  getRiskSettings: async (): Promise<RiskSettings> => {
    const res = await apiClient.get<RiskSettings>('/settings/risk');
    return res.data;
  },

  updateRiskSettings: async (data: RiskSettingsUpdate): Promise<RiskSettings> => {
    const res = await apiClient.put<RiskSettings>('/settings/risk', data);
    return res.data;
  },

  resetRiskSettings: async (): Promise<RiskSettings> => {
    const res = await apiClient.post<RiskSettings>('/settings/risk/reset');
    return res.data;
  },
};

export function useRiskSettings() {
  return useQuery({
    queryKey: ['settings', 'risk'],
    queryFn: () => riskSettingsApi.getRiskSettings(),
    staleTime: 60 * 1000,
  });
}

export function useUpdateRiskSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: RiskSettingsUpdate) => riskSettingsApi.updateRiskSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'risk'] });
    },
  });
}

export function useResetRiskSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => riskSettingsApi.resetRiskSettings(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings', 'risk'] });
    },
  });
}
