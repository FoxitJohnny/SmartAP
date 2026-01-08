import { useQuery } from '@tanstack/react-query';
import apiClient from './client';

// Types
export interface DashboardMetric {
  value: number | string;
  change: number; // Percentage change
  trend: 'up' | 'down' | 'neutral';
}

export interface DashboardMetrics {
  totalInvoices: DashboardMetric;
  stpRate: DashboardMetric;
  avgProcessingTime: DashboardMetric;
  pendingApprovals: DashboardMetric;
  riskFlags: DashboardMetric;
  totalValue: DashboardMetric;
}

export interface InvoiceVolumeData {
  date: string;
  count: number;
  value: number;
}

export interface StatusDistribution {
  status: string;
  count: number;
  percentage: number;
}

export interface ProcessingTimeData {
  date: string;
  avgTime: number;
  minTime: number;
  maxTime: number;
}

export interface RiskDistribution {
  riskLevel: string;
  count: number;
  percentage: number;
}

export interface VendorVolume {
  vendorName: string;
  invoiceCount: number;
  totalAmount: number;
}

export interface STPRateData {
  week: string;
  rate: number;
  processed: number;
  touchless: number;
}

export interface RecentActivity {
  id: string;
  type: 'upload' | 'approval' | 'risk' | 'payment' | 'comment';
  invoiceNumber: string;
  description: string;
  user: string;
  timestamp: string;
  status?: string;
}

export interface AnalyticsFilters {
  startDate?: string;
  endDate?: string;
  vendorId?: string;
  riskLevel?: string;
}

// API Functions
export const getDashboardMetrics = async (
  filters?: AnalyticsFilters
): Promise<DashboardMetrics> => {
  const { data } = await apiClient.get('/analytics/metrics', { params: filters });
  return data;
};

export const getInvoiceVolume = async (
  filters?: AnalyticsFilters
): Promise<InvoiceVolumeData[]> => {
  const { data } = await apiClient.get('/analytics/invoice-volume', { params: filters });
  return data;
};

export const getStatusDistribution = async (
  filters?: AnalyticsFilters
): Promise<StatusDistribution[]> => {
  const { data } = await apiClient.get('/analytics/status-distribution', { params: filters });
  return data;
};

export const getProcessingTimeData = async (
  filters?: AnalyticsFilters
): Promise<ProcessingTimeData[]> => {
  const { data } = await apiClient.get('/analytics/processing-time', { params: filters });
  return data;
};

export const getRiskDistribution = async (
  filters?: AnalyticsFilters
): Promise<RiskDistribution[]> => {
  const { data } = await apiClient.get('/analytics/risk-distribution', { params: filters });
  return data;
};

export const getTopVendors = async (
  limit: number = 10,
  filters?: AnalyticsFilters
): Promise<VendorVolume[]> => {
  const { data } = await apiClient.get('/analytics/top-vendors', {
    params: { ...filters, limit },
  });
  return data;
};

export const getSTPRateData = async (
  filters?: AnalyticsFilters
): Promise<STPRateData[]> => {
  const { data } = await apiClient.get('/analytics/stp-rate', { params: filters });
  return data;
};

export const getRecentActivity = async (
  limit: number = 20
): Promise<RecentActivity[]> => {
  const { data } = await apiClient.get('/analytics/recent-activity', {
    params: { limit },
  });
  return data;
};

// React Query Hooks
export const useDashboardMetrics = (filters?: AnalyticsFilters) => {
  return useQuery({
    queryKey: ['dashboard-metrics', filters],
    queryFn: () => getDashboardMetrics(filters),
    staleTime: 30000, // 30 seconds
  });
};

export const useInvoiceVolume = (filters?: AnalyticsFilters) => {
  return useQuery({
    queryKey: ['invoice-volume', filters],
    queryFn: () => getInvoiceVolume(filters),
    staleTime: 60000, // 1 minute
  });
};

export const useStatusDistribution = (filters?: AnalyticsFilters) => {
  return useQuery({
    queryKey: ['status-distribution', filters],
    queryFn: () => getStatusDistribution(filters),
    staleTime: 60000,
  });
};

export const useProcessingTimeData = (filters?: AnalyticsFilters) => {
  return useQuery({
    queryKey: ['processing-time', filters],
    queryFn: () => getProcessingTimeData(filters),
    staleTime: 60000,
  });
};

export const useRiskDistribution = (filters?: AnalyticsFilters) => {
  return useQuery({
    queryKey: ['risk-distribution', filters],
    queryFn: () => getRiskDistribution(filters),
    staleTime: 60000,
  });
};

export const useTopVendors = (limit: number = 10, filters?: AnalyticsFilters) => {
  return useQuery({
    queryKey: ['top-vendors', limit, filters],
    queryFn: () => getTopVendors(limit, filters),
    staleTime: 60000,
  });
};

export const useSTPRateData = (filters?: AnalyticsFilters) => {
  return useQuery({
    queryKey: ['stp-rate', filters],
    queryFn: () => getSTPRateData(filters),
    staleTime: 60000,
  });
};

export const useRecentActivity = (limit: number = 20) => {
  return useQuery({
    queryKey: ['recent-activity', limit],
    queryFn: () => getRecentActivity(limit),
    staleTime: 30000, // More frequent updates for activity
  });
};
